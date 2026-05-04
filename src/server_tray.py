"""
FuDog Labs Forensic Suite — Server Status Tray Indicator
=========================================================
Run this script to show a system tray icon that monitors the Forensic Case Server.
  Green  = server is reachable and healthy
  Yellow = server is starting / last check pending
  Red    = server is unreachable

Usage:
    python server_tray.py
    python server_tray.py --server-url http://127.0.0.1:5000

The tray icon context menu lets you start/stop the server process and
open the desktop client.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import threading
from typing import Optional

import requests
from PyQt5.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QDialog,
    QVBoxLayout,
    QTextEdit,
    QDialogButtonBox,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger('server_tray')

POLL_INTERVAL_MS = 10_000          # 10 seconds
HEALTH_TIMEOUT_S = 4               # HTTP timeout for /health requests
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), 'Forensic Server', 'server.py')
CLIENT_SCRIPT = os.path.join(os.path.dirname(__file__), 'main.py')
PYTHON = sys.executable


# ---------------------------------------------------------------------------
# Icon helpers
# ---------------------------------------------------------------------------

def _make_icon(color: str) -> QIcon:
    """Create a simple 22×22 coloured circle icon."""
    px = QPixmap(22, 22)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(QColor('#444444'))
    painter.drawEllipse(2, 2, 18, 18)
    painter.end()
    return QIcon(px)


ICON_GREEN  = None
ICON_YELLOW = None
ICON_RED    = None


def _icons():
    global ICON_GREEN, ICON_YELLOW, ICON_RED
    if ICON_GREEN is None:
        ICON_GREEN  = _make_icon('#28a745')
        ICON_YELLOW = _make_icon('#ffc107')
        ICON_RED    = _make_icon('#dc3545')


# ---------------------------------------------------------------------------
# Background health-check worker
# ---------------------------------------------------------------------------

class HealthChecker(QObject):
    status_changed = pyqtSignal(str, str)   # (status: 'up'|'down'|'pending', detail: str)

    def __init__(self, server_url: str) -> None:
        super().__init__()
        self.server_url = server_url.rstrip('/')
        self._running = True

    def check(self) -> None:
        if not self._running:
            return
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self) -> None:
        url = f'{self.server_url}/health'
        try:
            resp = requests.get(url, timeout=HEALTH_TIMEOUT_S)
            if resp.status_code == 200:
                data = resp.json()
                version = data.get('version', '')
                detail = f'Server up  •  v{version}  •  {self.server_url}' if version else f'Server up  •  {self.server_url}'
                self.status_changed.emit('up', detail)
            else:
                self.status_changed.emit('down', f'HTTP {resp.status_code} from {self.server_url}')
        except requests.exceptions.ConnectionError:
            self.status_changed.emit('down', f'Cannot reach {self.server_url}')
        except requests.exceptions.Timeout:
            self.status_changed.emit('down', f'Timeout  •  {self.server_url}')
        except Exception as exc:
            self.status_changed.emit('down', str(exc))

    def stop(self) -> None:
        self._running = False


# ---------------------------------------------------------------------------
# Log viewer dialog
# ---------------------------------------------------------------------------

class LogViewerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Server Log')
        self.resize(800, 500)
        layout = QVBoxLayout(self)
        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        self.text.setFontFamily('Courier New')
        layout.addWidget(self.text)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._load()

    def _load(self) -> None:
        log_candidates = [
            os.path.join(os.path.dirname(__file__), 'Forensic Server', 'logs', 'server.log'),
            os.path.join(os.path.expanduser('~'), '.forensic_app', 'logs', 'server.log'),
        ]
        for path in log_candidates:
            if os.path.exists(path):
                try:
                    with open(path, encoding='utf-8', errors='replace') as fh:
                        content = fh.read()
                    # Show last 200 lines
                    lines = content.splitlines()
                    self.text.setPlainText('\n'.join(lines[-200:]))
                    return
                except OSError:
                    pass
        self.text.setPlainText('No server log file found.\n\nExpected path: Forensic Server/logs/server.log')


# ---------------------------------------------------------------------------
# Tray application
# ---------------------------------------------------------------------------

class ServerTrayApp:
    def __init__(self, server_url: str) -> None:
        _icons()
        self.server_url = server_url
        self._server_proc: Optional[subprocess.Popen] = None
        self._status = 'pending'

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(ICON_YELLOW)
        self.tray.setToolTip('Forensic Suite — checking server…')
        self.tray.activated.connect(self._on_activated)

        self._build_menu()

        self.checker = HealthChecker(server_url)
        self.checker.status_changed.connect(self._on_status)

        self.timer = QTimer()
        self.timer.setInterval(POLL_INTERVAL_MS)
        self.timer.timeout.connect(self.checker.check)
        self.timer.start()

        # Immediate first check
        self.checker.check()

        self.tray.show()

    # ------------------------------------------------------------------
    def _build_menu(self) -> None:
        self.menu = QMenu()

        self.status_act = QAction('Status: checking…')
        self.status_act.setEnabled(False)
        self.menu.addAction(self.status_act)
        self.menu.addSeparator()

        self.start_act = QAction('Start Server')
        self.start_act.triggered.connect(self.start_server)
        self.menu.addAction(self.start_act)

        self.stop_act = QAction('Stop Server')
        self.stop_act.triggered.connect(self.stop_server)
        self.stop_act.setEnabled(False)
        self.menu.addAction(self.stop_act)

        self.menu.addSeparator()

        logs_act = QAction('View Server Log…')
        logs_act.triggered.connect(self.view_logs)
        self.menu.addAction(logs_act)

        client_act = QAction('Open Desktop Client')
        client_act.triggered.connect(self.open_client)
        self.menu.addAction(client_act)

        self.menu.addSeparator()

        quit_act = QAction('Exit Tray')
        quit_act.triggered.connect(self.quit)
        self.menu.addAction(quit_act)

        self.tray.setContextMenu(self.menu)

    # ------------------------------------------------------------------
    def _on_status(self, status: str, detail: str) -> None:
        self._status = status
        if status == 'up':
            self.tray.setIcon(ICON_GREEN)
            self.tray.setToolTip(detail)
            self.status_act.setText(f'● {detail}')
        else:
            self.tray.setIcon(ICON_RED)
            self.tray.setToolTip(f'Server unreachable  •  {self.server_url}')
            self.status_act.setText(f'● Server unreachable')
        logger.info('Health check: %s — %s', status, detail)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.tray.showMessage(
                'Forensic Suite Server',
                self.tray.toolTip(),
                QSystemTrayIcon.Information,
                3000,
            )

    # ------------------------------------------------------------------
    def start_server(self) -> None:
        if self._server_proc and self._server_proc.poll() is None:
            QMessageBox.information(None, 'Server Already Running', 'The server process is already running.')
            return

        server_dir = os.path.join(os.path.dirname(__file__), 'Forensic Server')
        if not os.path.exists(SERVER_SCRIPT):
            QMessageBox.warning(None, 'Script Not Found', f'server.py not found at:\n{SERVER_SCRIPT}')
            return

        try:
            self._server_proc = subprocess.Popen(
                [PYTHON, SERVER_SCRIPT],
                cwd=server_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.start_act.setEnabled(False)
            self.stop_act.setEnabled(True)
            self.tray.setIcon(ICON_YELLOW)
            self.tray.setToolTip('Server starting…')
            self.status_act.setText('● Server starting…')
            # Check health after a short delay
            QTimer.singleShot(3000, self.checker.check)
            logger.info('Server process started (PID %s)', self._server_proc.pid)
        except Exception as exc:
            QMessageBox.critical(None, 'Start Failed', f'Could not start server:\n{exc}')

    def stop_server(self) -> None:
        if self._server_proc and self._server_proc.poll() is None:
            self._server_proc.terminate()
            self._server_proc = None
            self.start_act.setEnabled(True)
            self.stop_act.setEnabled(False)
            self.tray.setIcon(ICON_RED)
            self.tray.setToolTip('Server stopped')
            self.status_act.setText('● Server stopped')
            logger.info('Server process terminated by user')
        else:
            QMessageBox.information(None, 'Not Running', 'No managed server process is running.')

    def view_logs(self) -> None:
        dlg = LogViewerDialog()
        dlg.exec_()

    def open_client(self) -> None:
        if not os.path.exists(CLIENT_SCRIPT):
            QMessageBox.warning(None, 'Script Not Found', f'main.py not found at:\n{CLIENT_SCRIPT}')
            return
        subprocess.Popen([PYTHON, CLIENT_SCRIPT], cwd=os.path.dirname(__file__))
        logger.info('Desktop client launched')

    def quit(self) -> None:
        self.timer.stop()
        self.checker.stop()
        if self._server_proc and self._server_proc.poll() is None:
            reply = QMessageBox.question(
                None,
                'Stop Server?',
                'The server is running. Stop it before exiting?',
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if reply == QMessageBox.Cancel:
                return
            if reply == QMessageBox.Yes:
                self._server_proc.terminate()
        QApplication.quit()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description='Forensic Suite Server Status Tray')
    parser.add_argument(
        '--server-url',
        default=None,
        help='Server URL to monitor (default: reads from config.json or http://127.0.0.1:5000)',
    )
    args = parser.parse_args()

    # Resolve server URL: CLI arg > config.json > fallback
    server_url = args.server_url
    if not server_url:
        try:
            import json
            cfg_path = os.path.join(os.path.dirname(__file__), 'config.json')
            with open(cfg_path, encoding='utf-8') as fh:
                cfg = json.load(fh)
            server_url = cfg.get('server_url', '').rstrip('/')
        except Exception:
            server_url = ''
    if not server_url:
        server_url = 'http://127.0.0.1:5000'

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, 'System Tray Unavailable', 'Your desktop environment does not support a system tray.')
        sys.exit(1)

    tray_app = ServerTrayApp(server_url)  # noqa: F841 — keep reference alive
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
