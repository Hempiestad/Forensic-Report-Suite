# main.py
# FuDog Labs Forensic Report Suite - Main Application (Version 1.3 - February 05, 2026)

import sys
import os

# Add src/ to path so all client modules (moved from root) remain importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

import re
import json
import hashlib
import logging
import socket
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from urllib import error as urllib_error
from urllib import request as urllib_request
import pandas as pd

# Import new stability modules
try:
    from diagnostics import SystemDiagnostics, validate_dependencies, detect_safe_mode
except ImportError:
    SystemDiagnostics = None
    validate_dependencies = None
    detect_safe_mode = lambda: False

try:
    from resource_loader import ResourceLoader, resource_path as loader_resource_path
except ImportError:
    ResourceLoader = None
    loader_resource_path = None

try:
    from logging_config import log_performance_baseline, PerformanceMonitor
except ImportError:
    log_performance_baseline = None
    PerformanceMonitor = None


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # Running in normal Python environment
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(base_path, relative_path)


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QAction, QDialog, QFormLayout,
    QLineEdit, QDialogButtonBox, QMessageBox, QFileDialog, QLabel,
    QHBoxLayout, QVBoxLayout, QWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QComboBox, QStyledItemDelegate, QAbstractItemView,
    QTableView, QTreeView, QToolTip, QWidgetAction, QSpinBox, QCheckBox, QMenu, QDateEdit, QCalendarWidget, QListWidget, QListWidgetItem, QTextEdit, QProgressBar, QSizePolicy, QInputDialog, QTreeWidget, QTreeWidgetItem
)
from PyQt5.QtGui import QKeySequence, QPainter, QColor, QStandardItemModel, QStandardItem, QPixmap, QFont
from PyQt5.QtCore import Qt, QRectF, QEvent, QSortFilterProxyModel, QDate, QTimer

logger = logging.getLogger(__name__)

try:
    import pyqtgraph as pg
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False

# ------------------------------------------------------------------
# Chart Cache Class
# ------------------------------------------------------------------

class ChartCache:
    """Cache for dashboard charts to avoid regenerating on every refresh"""
    def __init__(self) -> None:
        self.cache: Dict[str, Any] = {}
        self.last_refresh: float = 0
        self.refresh_interval: int = 30  # seconds
        self._last_data_hash: str = ""

    def get_cache_key(self, data: Any, chart_type: str) -> str:
        """Generate cache key from data hash"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(f"{chart_type}:{data_str}".encode()).hexdigest()

    def _compute_data_hash(self, data: Any) -> str:
        """Return an MD5 of the full data payload to detect changes."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()

    def should_refresh(self, data: Any = None) -> bool:
        """Return True only when data has changed OR the time interval has elapsed.

        If *data* is supplied the check is data-driven: the cache is considered
        stale only when the data hash differs from the last render, regardless of
        elapsed time.  The time-based fallback still fires when no data is given
        (e.g. a manual forced refresh).
        """
        import time
        current_time = time.time()
        if data is not None:
            new_hash = self._compute_data_hash(data)
            if new_hash != self._last_data_hash:
                self._last_data_hash = new_hash
                self.last_refresh = current_time
                return True
            return False
        # Fallback: time-based
        if current_time - self.last_refresh > self.refresh_interval:
            self.last_refresh = current_time
            return True
        return False

    def get(self, data: Any, chart_type: str) -> Optional[Any]:
        """Get cached chart if available and data hasn't changed"""
        cache_key = self.get_cache_key(data, chart_type)
        if cache_key in self.cache:
            return self.cache[cache_key]
        return None

    def set(self, data: Any, chart_type: str, chart: Any) -> None:
        """Cache the chart"""
        cache_key = self.get_cache_key(data, chart_type)
        self.cache[cache_key] = chart

    def clear(self) -> None:
        """Clear all cached charts"""
        self.cache.clear()
        self._last_data_hash = ""

from database import DatabaseManager
from case_tab import CaseTab
from notes_tab import NotesTab, NotesWindow
from reports_tab import ReportsTab, ReportsWindow
from glossary import GlossaryDialog
from accessibility import ThemeManager, THEME_COLOR_TOKENS
from auth import authenticate, load_config
from status_color_dialog import StatusColorDialog
from bug_report import BugReportDialog
from feature_request import FeatureRequestDialog
from logging_config import setup_logging
from legal_workflow_dialogs import (
    InvestigatorApprovalDialog, StateAttorneyApprovalDialog, JudicialApprovalDialog,
    SendToProviderDialog, ProviderAcknowledgedDialog, MarkSLABreachDialog
)
from legal_workflow_helpers import (
    mark_investigator_approved, mark_state_attorney_approved, mark_judicial_approval,
    mark_sent_to_provider, mark_provider_acknowledged, calculate_legal_sla_breach
)

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

LOG_DIR = os.path.join(os.path.expanduser("~"), ".forensic_app", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("forensic_app")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    log_path = os.path.join(LOG_DIR, "app.log")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=5)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)

# Global current user (set after authentication)
current_user = None
APP_VERSION = "1.3"


class SettingsDialog(QDialog):
    """Application settings dialog: timezone, theme, status colors, dashboard charts."""
    def __init__(self, parent: Optional[QWidget], theme_manager: Any, status_colors: Dict[str, str]) -> None:
        super().__init__(parent)
        self.setWindowTitle('Settings')
        self.parent = parent
        self.theme_manager = theme_manager
        self.status_colors = status_colors or {}
        self.resize(750, 650)  # Larger dialog for tabs
        
        # Ensure minimum font size for readability
        font = self.font()
        if font.pointSize() < 9:
            font.setPointSize(9)
            self.setFont(font)
        
        main_layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # General Settings Tab
        general_tab = self._create_general_tab()
        self.tab_widget.addTab(general_tab, "General")
        
        # Dashboard Charts Tab
        from dashboard_chart_settings import DashboardChartSettings
        from auth import load_config
        cfg = load_config()
        current_chart_settings = cfg.get('dashboard_charts', DashboardChartSettings.get_default_settings())
        self.chart_settings_widget = DashboardChartSettings(self, current_chart_settings)
        self.tab_widget.addTab(self.chart_settings_widget, "Dashboard Charts")
        
        # Notifications Tab
        from notification_settings import NotificationSettings
        current_notification_settings = cfg.get('notifications', NotificationSettings.get_default_settings())
        self.notification_settings_widget = NotificationSettings(self)
        self.notification_settings_widget.load_settings(current_notification_settings)
        self.tab_widget.addTab(self.notification_settings_widget, "Notifications")
        
        # Context Menus Tab
        context_tab = self._create_context_menu_tab()
        self.tab_widget.addTab(context_tab, "Context Menus")
        
        main_layout.addWidget(self.tab_widget)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        main_layout.addWidget(buttons)
        
        # Apply minimum sizes to all buttons in this dialog
        self._apply_button_minimum_sizes()
    
    def _apply_button_minimum_sizes(self):
        """Ensure all buttons in the settings dialog have readable text"""
        min_height = 24  # Minimum button height
        min_width = 80   # Minimum button width
        
        for button in self.findChildren(QPushButton):
            if button.minimumHeight() < min_height:
                button.setMinimumHeight(min_height)
            if button.minimumWidth() < min_width:
                button.setMinimumWidth(min_width)
            
            # Ensure text is readable
            font = button.font()
            if font.pointSize() < 9:
                font.setPointSize(9)
                button.setFont(font)
    
    def _create_general_tab(self) -> QWidget:
        """Create the general settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form = QFormLayout()

        # Timezone preference: System Local / UTC / Custom offset
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(['System Local', 'UTC', 'Custom Offset'])
        form.addRow('Time Zone Preference:', self.tz_combo)

        self.offset_spin = QSpinBox()
        self.offset_spin.setRange(-12, 14)
        self.offset_spin.setValue(0)
        form.addRow('Custom Offset (hours):', self.offset_spin)

        # Theme selection
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Light', 'Dark', 'High Contrast'])
        current = self.theme_manager.current_theme if hasattr(self.theme_manager, 'current_theme') else 'dark'
        theme_map = {'light': 'Light', 'dark': 'Dark', 'high_contrast': 'High Contrast'}
        self.theme_combo.setCurrentText(theme_map.get(current, 'Dark'))
        form.addRow('Theme:', self.theme_combo)

        # Status colors button
        self.status_colors_btn = QPushButton('Customize Status Colors...')
        self.status_colors_btn.clicked.connect(self.parent.show_status_color_dialog)
        form.addRow('', self.status_colors_btn)

        layout.addLayout(form)

        # Preview area: theme sample + status color legend
        self.preview_widget = QWidget()
        pv_layout = QVBoxLayout(self.preview_widget)
        pv_layout.setContentsMargins(6, 6, 6, 6)

        self.preview_label = QLabel('Preview: Theme and Status Colors')
        self.preview_label.setStyleSheet('font-weight: bold;')
        pv_layout.addWidget(self.preview_label)

        # Theme sample text
        self.theme_sample = QLabel('The quick brown fox jumps over the lazy dog')
        self.theme_sample.setMargin(6)
        pv_layout.addWidget(self.theme_sample)

        # Status legend (horizontal)
        self.legend_layout = QHBoxLayout()
        pv_layout.addLayout(self.legend_layout)

        layout.addWidget(self.preview_widget)

        # Wire preview updates
        try:
            self.theme_combo.currentTextChanged.connect(self.update_preview)
        except Exception as e:
            logger.debug(f"Could not connect theme preview: {e}")
        try:
            self.update_preview()
        except Exception as e:
            logger.debug(f"Could not run initial preview update: {e}")
        
        layout.addStretch()
        return widget
    
    def _create_context_menu_tab(self) -> QWidget:
        """Create the context menu settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Context-menu feature toggles (Notes / Reports)
        from auth import load_config
        cfg = load_config()
        ctx_cfg = cfg.get('context_menu', {})
        notes_cfg = ctx_cfg.get('notes', {})
        reports_cfg = ctx_cfg.get('reports', {})

        self.ctx_group_widget = QWidget()
        ctx_layout = QHBoxLayout(self.ctx_group_widget)
        ctx_layout.setContentsMargins(0, 0, 0, 0)

        notes_box = QVBoxLayout()
        notes_box.addWidget(QLabel('Notes Context Menu:'))
        self.notes_checks = {}
        for key, label in [
            ('insert_timestamp', 'Insert Timestamp'),
            ('convert_timestamp', 'Convert Timestamp'),
            ('insert_template', 'Insert Template'),
            ('create_task', 'Create Task'),
            ('tag', 'Tag / Label'),
            ('redact', 'Redact Selection'),
            ('create_calendar_event', 'Create Calendar Event'),
            ('export_selection', 'Export Selection')
        ]:
            cb = QCheckBox(label)
            cb.setChecked(bool(notes_cfg.get(key, True)))
            notes_box.addWidget(cb)
            self.notes_checks[key] = cb

        reports_box = QVBoxLayout()
        reports_box.addWidget(QLabel('Reports Context Menu:'))
        self.reports_checks = {}
        for key, label in [
            ('insert_timestamp', 'Insert Timestamp'),
            ('convert_timestamp', 'Convert Timestamp'),
            ('insert_template', 'Insert Template'),
            ('validate_section', 'Validate Section'),
            ('export_pdf', 'Export Selection as PDF'),
            ('embed_evidence', 'Embed Evidence Reference')
        ]:
            cb = QCheckBox(label)
            cb.setChecked(bool(reports_cfg.get(key, True)))
            reports_box.addWidget(cb)
            self.reports_checks[key] = cb

        ctx_layout.addLayout(notes_box)
        ctx_layout.addLayout(reports_box)
        layout.addWidget(self.ctx_group_widget)
        
        layout.addStretch()
        return widget

    def update_preview(self):
        """Update the theme sample and status color legend preview."""
        try:
            theme = self.theme_combo.currentText()
            if theme == 'Dark':
                self.theme_sample.setStyleSheet('color: #ffffff; background: #222; padding:4px;')
            elif theme == 'High Contrast':
                self.theme_sample.setStyleSheet('color: #000000; background: #ffff00; padding:4px;')
            else:
                self.theme_sample.setStyleSheet('color: #000000; background: #ffffff; padding:4px;')
        except Exception as e:
            logger.debug(f"Could not apply theme sample style: {e}")

        # Clear existing legend widgets
        try:
            while self.legend_layout.count():
                item = self.legend_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
        except Exception as e:
            logger.debug(f"Could not clear legend layout: {e}")

        # Build legend from status_colors
        default = {'Open': '#28a745', 'Pending': '#ffc107', 'Overdue': '#dc3545', 'Closed': '#6c757d'}
        colors = self.status_colors if self.status_colors else default
        for name, col in colors.items():
            sw = QLabel()
            sw.setFixedSize(18, 12)
            sw.setStyleSheet(f'background:{col}; border:1px solid #333;')
            lbl = QLabel(name)
            lbl.setContentsMargins(6, 0, 12, 0)
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(2, 2, 2, 2)
            h.addWidget(sw)
            h.addWidget(lbl)
            self.legend_layout.addWidget(container)
    
    def apply_settings(self) -> None:
        """Apply settings without closing dialog"""
        self._save_settings()
        QMessageBox.information(self, "Settings Applied", "Settings have been applied successfully.")
    
    def accept(self) -> None:
        """Save settings and close dialog"""
        self._save_settings()
        super().accept()
    
    def _save_settings(self) -> None:
        """Persist settings to config.json"""
        try:
            try:
                cfg = config
            except NameError:
                from auth import load_config
                cfg = load_config()
            # Timezone
            tz_choice = self.tz_combo.currentText()
            if tz_choice == 'System Local':
                cfg['timezone'] = 'local'
            elif tz_choice == 'UTC':
                cfg['timezone'] = 'UTC'
            else:
                cfg['timezone'] = f"UTC{self.offset_spin.value():+d}"

            # Theme
            theme_text = self.theme_combo.currentText()
            theme_map_rev = {'Light': 'light', 'Dark': 'dark', 'High Contrast': 'high_contrast'}
            cfg['theme'] = theme_map_rev.get(theme_text, 'dark')

            # Context menu configuration
            ctx = cfg.get('context_menu', {})
            notes_cfg = {}
            for k, cb in getattr(self, 'notes_checks', {}).items():
                notes_cfg[k] = bool(cb.isChecked())
            reports_cfg = {}
            for k, cb in getattr(self, 'reports_checks', {}).items():
                reports_cfg[k] = bool(cb.isChecked())
            ctx['notes'] = notes_cfg
            ctx['reports'] = reports_cfg
            cfg['context_menu'] = ctx
            
            # Save dashboard chart settings
            if hasattr(self, 'chart_settings_widget'):
                cfg['dashboard_charts'] = self.chart_settings_widget.get_current_settings()
            
            # Save notification settings
            if hasattr(self, 'notification_settings_widget'):
                cfg['notifications'] = self.notification_settings_widget.get_current_settings()

            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=4)

            # Apply theme immediately
            self.theme_manager.apply_theme(cfg['theme'])
            
            # Refresh charts if settings changed
            if hasattr(self.parent, 'chart_cache'):
                self.parent.chart_cache.clear()
            if hasattr(self.parent, 'refresh_dashboard'):
                self.parent.refresh_dashboard()
            
            # Notify parent to refresh context menus/toolbars in open editors
            try:
                if hasattr(self.parent, 'refresh_context_menus'):
                    self.parent.refresh_context_menus()
            except Exception as e:
                logger.debug(f"Could not refresh context menus: {e}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save settings: {e}")



# ------------------------------------------------------------------
# Chart Generation Functions
# ------------------------------------------------------------------

CHART_RENDER_VERSION = "2026.04.28-r6"


def _chart_target_size(chart_settings: Dict[str, Any]) -> Tuple[int, int]:
    """Return chart target size using simple fixed presets."""
    size_key = chart_settings.get('size', 'medium') if isinstance(chart_settings, dict) else 'medium'
    size_map = {
        'small': (320, 230),
        'medium': (420, 300),
        'large': (560, 400),
    }
    return size_map.get(size_key, (420, 300))



def _figure_to_hq_pixmap(fig, target_size: Tuple[int, int], render_dpi: int = 260, pad_inches: float = 0.32) -> Optional[QPixmap]:
    """Render a matplotlib figure at high DPI, then downsample smoothly for crisp Qt display."""
    try:
        import io
    except ImportError:
        return None

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format='png',
        dpi=render_dpi,
        bbox_inches='tight',
        pad_inches=pad_inches,
        facecolor=fig.get_facecolor(),
        edgecolor='none',
    )
    buf.seek(0)

    pixmap = QPixmap()
    if not pixmap.loadFromData(buf.getvalue()):
        return None

    target_w, target_h = target_size
    if target_w > 0 and target_h > 0:
        pixmap = pixmap.scaled(target_w, target_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return pixmap

def generate_pie_chart(data, title, figsize=(4, 3), bgcolor='white'):
    """Generate a pie chart as QPixmap from data dict with specified background color"""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    except ImportError:
        return None

    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bgcolor)
    labels = list(data.keys())
    sizes = list(data.values())

    # Filter out zero values
    filtered_labels = []
    filtered_sizes = []
    for label, size in zip(labels, sizes):
        if size > 0:
            filtered_labels.append(label)
            filtered_sizes.append(size)

    if not filtered_sizes:
        plt.close(fig)
        return None

    colors = ['#28a745', '#ffc107', '#dc3545', '#6c757d', '#007bff', '#17a2b8', '#fd7e14']
    ax.pie(
        filtered_sizes,
        labels=filtered_labels,
        colors=colors[:len(filtered_sizes)],
        autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
        startangle=90,
        labeldistance=1.08,
        pctdistance=0.72,
    )
    ax.axis('equal')
    ax.set_title(title, fontsize=10)
    fig.subplots_adjust(left=0.08, right=0.92, top=0.88, bottom=0.12)

    # Convert to high-quality QPixmap (supersample + smooth downscale)
    target_size = _chart_target_size({'size': 'medium'})
    pixmap = _figure_to_hq_pixmap(fig, target_size, render_dpi=220, pad_inches=0.25)
    plt.close(fig)
    return pixmap


def get_chart_colors(chart_settings: Dict[str, Any], num_colors: int) -> List[str]:
    """Get color palette based on settings"""
    color_schemes = {
        'professional': ['#28a745', '#ffc107', '#dc3545', '#6c757d', '#007bff', '#17a2b8', '#fd7e14'],
        'colorblind_friendly': ['#0173B2', '#DE8F05', '#029E73', '#CC78BC', '#CA9161', '#949494', '#ECE133'],
        'monochrome': ['#1a1a1a', '#4d4d4d', '#808080', '#b3b3b3', '#e6e6e6', '#f0f0f0'],
        'custom': chart_settings.get('custom_colors', [])
    }
    
    scheme = chart_settings.get('color_scheme', 'professional')
    colors = color_schemes.get(scheme, color_schemes['professional'])
    
    # Extend colors if needed
    while len(colors) < num_colors:
        colors.extend(colors)
    
    return colors[:num_colors]


def generate_chart(data: Dict[str, int], title: str, chart_settings: Dict[str, Any], bgcolor: str = 'white') -> Optional[QPixmap]:
    """
    Universal chart generator that respects user preferences.
    
    Args:
        data: Dictionary of labels to values
        title: Chart title
        chart_settings: Dictionary from config.json['dashboard_charts']
        bgcolor: Background color
    
    Returns:
        QPixmap or None
    """
    chart_type = chart_settings.get('chart_type', 'pie')
    
    if chart_type == 'pie':
        return generate_pie_chart_enhanced(data, title, chart_settings, bgcolor)
    elif chart_type == 'bar':
        return generate_bar_chart(data, title, chart_settings, bgcolor)
    elif chart_type == 'donut':
        return generate_donut_chart(data, title, chart_settings, bgcolor)
    elif chart_type == 'horizontal_bar':
        return generate_horizontal_bar_chart(data, title, chart_settings, bgcolor)
    else:
        return generate_pie_chart_enhanced(data, title, chart_settings, bgcolor)


def generate_pie_chart_enhanced(data: Dict[str, int], title: str, chart_settings: Dict[str, Any], bgcolor: str = 'white') -> Optional[QPixmap]:
    """Enhanced pie chart with customization options"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    
    # Get size from settings
    size_map = {
        'small': (3, 2.5),
        'medium': (4, 3),
        'large': (6, 4)
    }
    figsize = size_map.get(chart_settings.get('size', 'medium'), (4, 3))
    
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bgcolor)
    
    labels = list(data.keys())
    sizes = list(data.values())
    
    # Filter out zero values
    filtered_labels = []
    filtered_sizes = []
    for label, size in zip(labels, sizes):
        if size > 0:
            filtered_labels.append(label)
            filtered_sizes.append(size)
    
    if not filtered_sizes:
        plt.close(fig)
        return None
    
    # Get colors from settings
    colors = get_chart_colors(chart_settings, len(filtered_sizes))
    
    # Determine if percentages should be shown
    autopct = None
    if chart_settings.get('show_percentages', True):
        autopct = lambda pct: f'{pct:.1f}%' if pct > 5 else ''
    
    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        filtered_sizes,
        labels=filtered_labels if chart_settings.get('show_labels', True) else None,
        colors=colors,
        autopct=autopct,
        startangle=90,
        labeldistance=1.02,
        pctdistance=0.72,
    )

    # Nudge bottom labels down slightly for specific dashboard charts.
    if title in {'Evidence Status', 'Legal Processes', 'Leads'}:
        for txt in texts:
            x, y = txt.get_position()
            if y < -0.05:
                txt.set_position((x, y - 0.05))
    
    ax.axis('equal')
    ax.set_title(title, fontsize=11, fontweight='bold')
    
    # Add legend only when labels are hidden
    if chart_settings.get('show_legend', True) and not chart_settings.get('show_labels', True):
        legend_position = chart_settings.get('legend_position', 'right')
        loc_map = {
            'right': 'center left',
            'left': 'center right',
            'top': 'upper center',
            'bottom': 'lower center'
        }
        bbox_map = {
            'right': (1.1, 0.5),
            'left': (-0.1, 0.5),
            'top': (0.5, 1.1),
            'bottom': (0.5, -0.1)
        }
        ax.legend(
            filtered_labels,
            loc=loc_map.get(legend_position, 'center left'),
            bbox_to_anchor=bbox_map.get(legend_position, (1.1, 0.5)),
            fontsize=9
        )
    
    fig.subplots_adjust(left=0.08, right=0.92, top=0.88, bottom=0.12)

    # Convert to high-quality QPixmap (supersample + smooth downscale)
    target_size = _chart_target_size(chart_settings)
    pixmap = _figure_to_hq_pixmap(fig, target_size, render_dpi=260, pad_inches=0.32)
    plt.close(fig)
    return pixmap


def generate_bar_chart(data: Dict[str, int], title: str, chart_settings: Dict[str, Any], bgcolor: str = 'white') -> Optional[QPixmap]:
    """Generate vertical bar chart"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    
    size_map = {
        'small': (3, 2.5),
        'medium': (4, 3),
        'large': (6, 4)
    }
    figsize = size_map.get(chart_settings.get('size', 'medium'), (4, 3))
    
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bgcolor)
    
    # Filter out zero values
    labels = [k for k, v in data.items() if v > 0]
    values = [v for v in data.values() if v > 0]
    
    if not values:
        plt.close(fig)
        return None
    
    colors = get_chart_colors(chart_settings, len(values))
    bars = ax.bar(labels, values, color=colors)
    
    # Add value labels on bars if percentages enabled
    if chart_settings.get('show_percentages', True):
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=9)

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_ylabel('Count')
    plt.xticks(rotation=35, ha='right')
    fig.tight_layout(pad=1.2)
    
    # Convert to high-quality QPixmap (supersample + smooth downscale)
    target_size = _chart_target_size(chart_settings)
    pixmap = _figure_to_hq_pixmap(fig, target_size, render_dpi=260, pad_inches=0.28)
    plt.close(fig)
    return pixmap


def generate_donut_chart(data: Dict[str, int], title: str, chart_settings: Dict[str, Any], bgcolor: str = 'white') -> Optional[QPixmap]:
    """Generate donut chart (pie with center hole)"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    
    size_map = {
        'small': (3, 2.5),
        'medium': (4, 3),
        'large': (6, 4)
    }
    figsize = size_map.get(chart_settings.get('size', 'medium'), (4, 3))
    
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bgcolor)
    
    # Filter out zero values
    labels = [k for k, v in data.items() if v > 0]
    values = [v for v in data.values() if v > 0]
    
    if not values:
        plt.close(fig)
        return None
    
    colors = get_chart_colors(chart_settings, len(values))
    
    autopct = None
    if chart_settings.get('show_percentages', True):
        autopct = lambda pct: f'{pct:.1f}%' if pct > 5 else ''
    
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels if chart_settings.get('show_labels', True) else None,
        colors=colors,
        autopct=autopct,
        startangle=90,
        labeldistance=1.02,
        pctdistance=0.72,
        wedgeprops=dict(width=0.5)  # Creates the donut hole
    )

    # Nudge bottom labels down slightly for specific dashboard charts.
    if title in {'Evidence Status', 'Legal Processes', 'Leads'}:
        for txt in texts:
            x, y = txt.get_position()
            if y < -0.05:
                txt.set_position((x, y - 0.05))

    if chart_settings.get('show_legend', True) and not chart_settings.get('show_labels', True):
        ax.legend(labels, loc='center left', bbox_to_anchor=(1.1, 0.5), fontsize=9)
    
    ax.axis('equal')
    ax.set_title(title, fontsize=11, fontweight='bold')
    
    fig.subplots_adjust(left=0.08, right=0.92, top=0.88, bottom=0.12)

    # Convert to high-quality QPixmap (supersample + smooth downscale)
    target_size = _chart_target_size(chart_settings)
    pixmap = _figure_to_hq_pixmap(fig, target_size, render_dpi=260, pad_inches=0.32)
    plt.close(fig)
    return pixmap


def generate_horizontal_bar_chart(data: Dict[str, int], title: str, chart_settings: Dict[str, Any], bgcolor: str = 'white') -> Optional[QPixmap]:
    """Generate horizontal bar chart"""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    
    size_map = {
        'small': (3, 2.5),
        'medium': (4, 3),
        'large': (6, 4)
    }
    figsize = size_map.get(chart_settings.get('size', 'medium'), (4, 3))
    
    fig, ax = plt.subplots(figsize=figsize)
    fig.patch.set_facecolor(bgcolor)
    
    # Filter out zero values
    labels = [k for k, v in data.items() if v > 0]
    values = [v for v in data.values() if v > 0]
    
    if not values:
        plt.close(fig)
        return None
    
    colors = get_chart_colors(chart_settings, len(values))
    bars = ax.barh(labels, values, color=colors)
    
    # Add value labels on bars if percentages enabled
    if chart_settings.get('show_percentages', True):
        for bar in bars:
            width = bar.get_width()
            ax.text(width, bar.get_y() + bar.get_height()/2.,
                    f'{int(width)}',
                    ha='left', va='center', fontsize=9)

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('Count')
    fig.tight_layout(pad=1.2)
    
    # Convert to high-quality QPixmap (supersample + smooth downscale)
    target_size = _chart_target_size(chart_settings)
    pixmap = _figure_to_hq_pixmap(fig, target_size, render_dpi=260, pad_inches=0.28)
    plt.close(fig)
    return pixmap


class _TemplateEditorAudit:
    def log(self, *_args, **_kwargs) -> None:
        return


class _TemplateEditorDBAdapter:
    """Small adapter so ReportsTab can be reused as a report-writer template editor."""

    def __init__(self, html: str) -> None:
        self._html = html or ''

    def load_report(self, _case_number: str):
        return self._html, [], ''

    def save_report(self, _case_data, report_html, _appendices, _pdf_hash, **_kwargs):
        self._html = report_html or ''
        return True


class TemplateReportWriterDialog(QDialog):
    """Edit template content using the same report writer UI stack."""

    def __init__(self, parent: Optional[QWidget], initial_html: str, user: Dict[str, Any]) -> None:
        super().__init__(parent)
        self.setWindowTitle('Template Report Writer')
        self.resize(1200, 800)

        import uuid
        self._adapter = _TemplateEditorDBAdapter(initial_html)
        case_data = {'case_number': f'_template_editor_{uuid.uuid4().hex[:8]}'}
        self._reports_tab = ReportsTab(case_data, self._adapter, _TemplateEditorAudit(), user or {}, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._reports_tab)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_html(self) -> str:
        try:
            return self._reports_tab.report_editor.toHtml()
        except Exception:
            return self._adapter._html


class LegalTemplateLibraryDialog(QDialog):
    """Hierarchical legal template library dialog with vendor/type folders."""

    TEMPLATE_TYPES = [
        ('preservation_letter', 'Preservation Letter'),
        ('subpoena', 'Subpoena'),
        ('search_warrant', 'Search Warrant'),
        ('other', 'Other'),
    ]

    def __init__(self, parent: Optional[QWidget], db: DatabaseManager, user: Dict[str, Any]) -> None:
        super().__init__(parent)
        self.db = db
        self.user = user or {}
        self.username = str(self.user.get('username') or 'unknown')
        self.role = str(self.user.get('role') or 'writer').lower()
        self.templates: List[Dict[str, Any]] = []
        self.selected_template_id: Optional[int] = None

        self.setWindowTitle('Legal Template Library')
        self.resize(1050, 680)

        self._build_ui()
        self.refresh_templates()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info = QLabel('Build and share reusable legal process templates across your investigator network.')
        info.setWordWrap(True)
        layout.addWidget(info)

        content_layout = QHBoxLayout()

        left = QVBoxLayout()
        self.template_tree = QTreeWidget()
        self.template_tree.setHeaderLabels(['Vendor', 'Type', 'Template', 'Owner', 'Access', 'Updated'])
        self.template_tree.itemSelectionChanged.connect(self.on_tree_selection_changed)
        self.template_tree.setAlternatingRowColors(True)
        self.template_tree.setUniformRowHeights(True)
        self.template_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        left.addWidget(self.template_tree)

        left_controls = QHBoxLayout()
        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.refresh_templates)
        clear_btn = QPushButton('New Template')
        clear_btn.clicked.connect(self.clear_editor)
        import_btn = QPushButton('Import...')
        import_btn.clicked.connect(self.import_templates)
        export_btn = QPushButton('Export...')
        export_btn.clicked.connect(self.export_templates)
        left_controls.addWidget(refresh_btn)
        left_controls.addWidget(clear_btn)
        left_controls.addWidget(import_btn)
        left_controls.addWidget(export_btn)
        left_controls.addStretch()
        left.addLayout(left_controls)

        right = QVBoxLayout()
        form = QFormLayout()

        self.template_type_combo = QComboBox()
        for key, label in self.TEMPLATE_TYPES:
            self.template_type_combo.addItem(label, key)
        form.addRow('Template Type', self.template_type_combo)

        self.vendor_edit = QLineEdit()
        self.vendor_edit.setPlaceholderText('Example: Google, Apple, Microsoft, ISP')
        form.addRow('Vendor', self.vendor_edit)

        self.title_edit = QLineEdit()
        form.addRow('Title', self.title_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText('comma,separated,tags')
        form.addRow('Tags', self.tags_edit)

        self.content_edit = QTextEdit()
        self.content_edit.setPlaceholderText('Write your preservation letter, subpoena, or search warrant template...')
        form.addRow('Template Body', self.content_edit)
        right.addLayout(form)

        right_buttons = QHBoxLayout()
        save_btn = QPushButton('Save Template')
        save_btn.clicked.connect(self.save_template)
        delete_btn = QPushButton('Delete Template')
        delete_btn.clicked.connect(self.delete_template)
        writer_btn = QPushButton('Open In Report Writer')
        writer_btn.clicked.connect(self.open_in_report_writer)
        share_btn = QPushButton('Share Selected')
        share_btn.clicked.connect(self.share_selected_template)
        share_folder_btn = QPushButton('Share Folder')
        share_folder_btn.clicked.connect(self.share_selected_folder)
        share_library_btn = QPushButton('Share Entire Library')
        share_library_btn.clicked.connect(self.share_library)
        right_buttons.addWidget(save_btn)
        right_buttons.addWidget(delete_btn)
        right_buttons.addWidget(writer_btn)
        right_buttons.addWidget(share_btn)
        right_buttons.addWidget(share_folder_btn)
        right_buttons.addWidget(share_library_btn)
        right.addLayout(right_buttons)

        content_layout.addLayout(left, 3)
        content_layout.addLayout(right, 4)
        layout.addLayout(content_layout)

        close_buttons = QDialogButtonBox(QDialogButtonBox.Close)
        close_buttons.rejected.connect(self.reject)
        layout.addWidget(close_buttons)

    def refresh_templates(self) -> None:
        self.templates = self.db.list_legal_template_library(self.username, self.role)
        self.template_tree.clear()

        grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for item in self.templates:
            vendor = str(item.get('vendor_name') or 'General Vendor').strip() or 'General Vendor'
            ttype = str(item.get('template_type') or 'other').strip() or 'other'
            grouped.setdefault(vendor, {}).setdefault(ttype, []).append(item)

        selected_item: Optional[QTreeWidgetItem] = None
        for vendor in sorted(grouped.keys(), key=lambda s: s.lower()):
            vendor_node = QTreeWidgetItem([vendor, '', '', '', '', ''])
            self.template_tree.addTopLevelItem(vendor_node)
            for ttype in sorted(grouped[vendor].keys(), key=lambda s: s.lower()):
                type_node = QTreeWidgetItem(['', ttype, '', '', '', ''])
                vendor_node.addChild(type_node)
                templates = sorted(grouped[vendor][ttype], key=lambda t: str(t.get('title') or '').lower())
                type_node.setData(0, Qt.UserRole + 1, vendor)
                type_node.setData(0, Qt.UserRole + 2, ttype)
                for tpl in templates:
                    access = 'Owned' if tpl.get('is_owned') else 'Shared'
                    leaf = QTreeWidgetItem([
                        '',
                        '',
                        str(tpl.get('title') or ''),
                        str(tpl.get('owner_username') or ''),
                        access,
                        str(tpl.get('updated_at') or ''),
                    ])
                    leaf.setData(0, Qt.UserRole, int(tpl.get('id') or 0))
                    leaf.setData(0, Qt.UserRole + 1, vendor)
                    leaf.setData(0, Qt.UserRole + 2, ttype)
                    type_node.addChild(leaf)
                    if self.selected_template_id is not None and int(tpl.get('id', -1)) == int(self.selected_template_id):
                        selected_item = leaf

        self.template_tree.expandAll()
        for col in range(6):
            self.template_tree.resizeColumnToContents(col)
        if selected_item is not None:
            self.template_tree.setCurrentItem(selected_item)

    def on_tree_selection_changed(self) -> None:
        items = self.template_tree.selectedItems()
        if not items:
            return
        node = items[0]
        template_id = node.data(0, Qt.UserRole)
        if not template_id:
            return
        item = next((t for t in self.templates if int(t.get('id', -1)) == int(template_id)), None)
        if not item:
            return
        self.selected_template_id = int(item.get('id'))

        template_type = str(item.get('template_type') or 'other')
        combo_idx = self.template_type_combo.findData(template_type)
        self.template_type_combo.setCurrentIndex(combo_idx if combo_idx >= 0 else self.template_type_combo.findData('other'))
        self.vendor_edit.setText(str(item.get('vendor_name') or 'General Vendor'))
        self.title_edit.setText(str(item.get('title') or ''))
        self.tags_edit.setText(', '.join(item.get('tags') or []))
        self.content_edit.setPlainText(str(item.get('template_content') or ''))

    def clear_editor(self) -> None:
        self.selected_template_id = None
        self.template_type_combo.setCurrentIndex(0)
        self.vendor_edit.setText('')
        self.title_edit.clear()
        self.tags_edit.clear()
        self.content_edit.clear()
        self.template_tree.clearSelection()

    def save_template(self) -> None:
        vendor_name = self.vendor_edit.text().strip() or 'General Vendor'
        template_type = str(self.template_type_combo.currentData() or 'other')
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        tags = [tag.strip() for tag in self.tags_edit.text().split(',') if tag.strip()]

        if not title or not content:
            QMessageBox.warning(self, 'Missing Data', 'Title and template body are required.')
            return

        selected = next((t for t in self.templates if int(t.get('id', -1)) == int(self.selected_template_id or -1)), None)
        if selected and selected.get('is_owned'):
            ok = self.db.update_legal_template(
                template_id=int(selected['id']),
                actor_username=self.username,
                actor_role=self.role,
                vendor_name=vendor_name,
                template_type=template_type,
                title=title,
                template_content=content,
                tags=tags,
            )
            if not ok:
                QMessageBox.warning(self, 'Update Failed', 'Could not update template.')
                return
            QMessageBox.information(self, 'Saved', 'Template updated successfully.')
        else:
            created = self.db.create_legal_template(
                owner_username=self.username,
                vendor_name=vendor_name,
                template_type=template_type,
                title=title,
                template_content=content,
                tags=tags,
            )
            if not created:
                QMessageBox.warning(self, 'Create Failed', 'Could not create template.')
                return
            self.selected_template_id = int(created.get('id'))
            QMessageBox.information(self, 'Saved', 'Template created successfully.')

        self.refresh_templates()

    def delete_template(self) -> None:
        selected = next((t for t in self.templates if int(t.get('id', -1)) == int(self.selected_template_id or -1)), None)
        if not selected:
            QMessageBox.warning(self, 'No Selection', 'Select a template to delete.')
            return
        if not selected.get('is_owned') and self.role != 'admin':
            QMessageBox.warning(self, 'Access Denied', 'Only owner templates can be deleted.')
            return

        reply = QMessageBox.question(
            self,
            'Delete Template',
            f"Delete template '{selected.get('title', '')}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok = self.db.delete_legal_template(int(selected['id']), self.username, self.role)
        if not ok:
            QMessageBox.warning(self, 'Delete Failed', 'Could not delete template.')
            return

        self.clear_editor()
        self.refresh_templates()
        QMessageBox.information(self, 'Deleted', 'Template deleted.')

    def open_in_report_writer(self) -> None:
        current_html = self.content_edit.toHtml() if self.content_edit.toPlainText().strip() else self.content_edit.toPlainText()
        dialog = TemplateReportWriterDialog(self, current_html, self.user)
        if dialog.exec_() == QDialog.Accepted:
            self.content_edit.setHtml(dialog.get_html())

    def share_selected_template(self) -> None:
        selected = next((t for t in self.templates if int(t.get('id', -1)) == int(self.selected_template_id or -1)), None)
        if not selected:
            QMessageBox.warning(self, 'No Selection', 'Select a template to share.')
            return
        if not selected.get('is_owned') and self.role != 'admin':
            QMessageBox.warning(self, 'Access Denied', 'Only owner templates can be shared.')
            return

        target, ok = QInputDialog.getText(self, 'Share Template', 'Share with username:')
        if not ok:
            return
        target = target.strip()
        if not target:
            QMessageBox.warning(self, 'Missing User', 'Enter a valid username.')
            return

        shared = self.db.share_legal_template(int(selected['id']), target, self.username)
        if not shared:
            QMessageBox.warning(self, 'Share Failed', 'Could not share template with that user.')
            return
        QMessageBox.information(self, 'Shared', f"Template shared with '{target}'.")

    def share_library(self) -> None:
        target, ok = QInputDialog.getText(self, 'Share Legal Library', 'Share entire library with username:')
        if not ok:
            return
        target = target.strip()
        if not target:
            QMessageBox.warning(self, 'Missing User', 'Enter a valid username.')
            return

        count = self.db.share_legal_template_library(self.username, target)
        QMessageBox.information(self, 'Library Shared', f'Shared {count} templates with {target}.')

    def share_selected_folder(self) -> None:
        items = self.template_tree.selectedItems()
        if not items:
            QMessageBox.warning(self, 'No Selection', 'Select a vendor or process-type folder to share.')
            return

        node = items[0]
        vendor = str(node.data(0, Qt.UserRole + 1) or '').strip()
        template_type = str(node.data(0, Qt.UserRole + 2) or '').strip()

        # Vendor node has text in column 0 and no explicit metadata.
        if not vendor:
            vendor = str(node.text(0) or '').strip()
            template_type = ''

        # Leaf selected: still allow sharing its folder scope.
        if not vendor and node.parent() is not None:
            type_node = node.parent()
            vendor_node = type_node.parent()
            vendor = str(vendor_node.text(0) or '').strip() if vendor_node is not None else ''
            template_type = str(type_node.text(1) or '').strip()

        if not vendor:
            QMessageBox.warning(self, 'Invalid Selection', 'Please select a vendor or process-type folder.')
            return

        target, ok = QInputDialog.getText(self, 'Share Folder', 'Share selected folder with username:')
        if not ok:
            return
        target = target.strip()
        if not target:
            QMessageBox.warning(self, 'Missing User', 'Enter a valid username.')
            return

        count = self.db.share_legal_template_library_scoped(
            owner_username=self.username,
            shared_with=target,
            vendor_name=vendor,
            template_type=template_type or None,
        )
        if template_type:
            QMessageBox.information(self, 'Folder Shared', f'Shared {count} templates from {vendor} / {template_type} with {target}.')
        else:
            QMessageBox.information(self, 'Folder Shared', f'Shared {count} templates from vendor {vendor} with {target}.')

    def export_templates(self) -> None:
        payload = self.db.export_legal_template_library(self.username, self.role)
        path, _ = QFileDialog.getSaveFileName(self, 'Export Template Library', 'legal_template_library.json', 'JSON Files (*.json)')
        if not path:
            return
        try:
            with open(path, 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, indent=2)
            QMessageBox.information(self, 'Export Complete', f'Template library exported to:\n{path}')
        except Exception as exc:
            QMessageBox.warning(self, 'Export Failed', f'Could not export template library:\n{exc}')

    def import_templates(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'Import Template Library', '', 'JSON Files (*.json)')
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                payload = json.load(handle)
        except Exception as exc:
            QMessageBox.warning(self, 'Import Failed', f'Could not read import file:\n{exc}')
            return

        mode_label, ok = QInputDialog.getItem(self, 'Import Mode', 'Choose import mode:', ['Append', 'Replace Existing'], 0, False)
        if not ok:
            return
        mode = 'replace' if mode_label == 'Replace Existing' else 'append'
        result = self.db.import_legal_template_library(self.username, payload, mode=mode, role=self.role)
        self.refresh_templates()
        QMessageBox.information(
            self,
            'Import Complete',
            f"Imported: {int(result.get('imported', 0))}\nSkipped: {int(result.get('skipped', 0))}\nMode: {mode}",
        )


# ------------------------------------------------------------------
# Supervisor Case Dashboard Dialog
# ------------------------------------------------------------------

class SupervisorDashboardDialog(QDialog):
    """Supervisor view: browse cases assigned to their investigators/examiners.

    Supervisors can filter by investigator username, examiner username, or
    case number.  Double-clicking a row opens read-only case detail.
    """

    COLUMNS = ['Case #', 'Title', 'Investigator', 'Examiner', 'Status', 'Trial Date']

    def __init__(self, parent, db, user: Dict[str, Any]) -> None:
        super().__init__(parent)
        self.db = db
        self.user = user or {}
        self.username = str(self.user.get('username') or '')
        self.role = str(self.user.get('role') or 'supervisor').lower()
        self.setWindowTitle('Supervisor — Case Dashboard')
        self.resize(950, 600)
        self._build_ui()
        self._load()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Filter bar
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel('Investigator:'))
        self.investigator_edit = QLineEdit()
        self.investigator_edit.setPlaceholderText('username filter…')
        self.investigator_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.investigator_edit)

        filter_row.addWidget(QLabel('Examiner:'))
        self.examiner_edit = QLineEdit()
        self.examiner_edit.setPlaceholderText('username filter…')
        self.examiner_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.examiner_edit)

        filter_row.addWidget(QLabel('Case #:'))
        self.case_edit = QLineEdit()
        self.case_edit.setPlaceholderText('case number filter…')
        self.case_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self.case_edit)

        filter_row.addWidget(QLabel('Status:'))
        self.status_combo = QComboBox()
        self.status_combo.addItem('All statuses', '')
        for s in ('draft', 'submitted', 'in_peer_review', 'revisions_needed', 'approved', 'closed'):
            self.status_combo.addItem(s, s)
        self.status_combo.currentIndexChanged.connect(self._apply_filter)
        filter_row.addWidget(self.status_combo)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._load)
        filter_row.addWidget(refresh_btn)
        layout.addLayout(filter_row)

        # Cases table
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # Status bar
        self.info_label = QLabel('')
        layout.addWidget(self.info_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load(self) -> None:
        self._all_cases = self.db.load_all_cases(self.username, self.role)
        self._apply_filter()

    def _apply_filter(self) -> None:
        inv_f = self.investigator_edit.text().strip().lower()
        ex_f = self.examiner_edit.text().strip().lower()
        case_f = self.case_edit.text().strip().lower()
        status_f = self.status_combo.currentData() or ''

        filtered = []
        for c in self._all_cases:
            if inv_f and inv_f not in str(c.get('assigned_to') or '').lower():
                continue
            if ex_f and ex_f not in str(c.get('examiner_id') or '').lower():
                continue
            if case_f and case_f not in str(c.get('case_number') or '').lower():
                continue
            if status_f and c.get('status') != status_f:
                continue
            filtered.append(c)

        self.table.setRowCount(0)
        for row_idx, c in enumerate(filtered):
            self.table.insertRow(row_idx)
            for col, val in enumerate([
                str(c.get('case_number') or ''),
                str(c.get('title') or ''),
                str(c.get('assigned_to') or ''),
                str(c.get('examiner_id') or ''),
                str(c.get('status') or ''),
                str(c.get('trial_date') or ''),
            ]):
                item = QTableWidgetItem(val)
                item.setData(Qt.UserRole, c)
                self.table.setItem(row_idx, col, item)

        self.info_label.setText(f'{len(filtered)} case(s) shown  |  {len(self._all_cases)} total accessible')

    def _on_double_click(self, index) -> None:
        row = index.row()
        case_data = self.table.item(row, 0).data(Qt.UserRole)
        if not case_data:
            return
        # Show a read-only summary popup
        dlg = QDialog(self)
        dlg.setWindowTitle(f"Case {case_data.get('case_number', '')} — Details")
        dlg.resize(500, 350)
        layout = QVBoxLayout(dlg)
        text = QTextEdit()
        text.setReadOnly(True)
        lines = []
        for field in ('case_number', 'title', 'assigned_to', 'examiner_id', 'status',
                      'trial_date', 'sentencing_date', 'review_comments'):
            val = case_data.get(field)
            if val:
                label = field.replace('_', ' ').title()
                lines.append(f'<b>{label}:</b> {val}')
        text.setHtml('<br>'.join(lines) or 'No details available.')
        layout.addWidget(text)
        btn = QDialogButtonBox(QDialogButtonBox.Close)
        btn.rejected.connect(dlg.reject)
        layout.addWidget(btn)
        dlg.exec_()


# ------------------------------------------------------------------
# Admin User Management Dialog
# ------------------------------------------------------------------

class AdminUsersDialog(QDialog):
    """Admin view: manage user accounts and supervisor assignments.

    Tab 1 — Users: list, add, change role, activate/deactivate.
    Tab 2 — Supervisor Assignments: view and create/remove assignments.
    """

    USER_ROLES = ['writer', 'examiner', 'supervisor', 'admin']

    def __init__(self, parent, db, user: Dict[str, Any]) -> None:
        super().__init__(parent)
        self.db = db
        self.user = user or {}
        self.username = str(self.user.get('username') or '')
        self.setWindowTitle('Admin - User & Assignment Management')
        self.resize(900, 580)
        self._build_ui()
        self._load_users()
        self._load_assignments()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_users_tab(), 'Users')
        self.tabs.addTab(self._build_assignments_tab(), 'Supervisor Assignments')
        layout.addWidget(self.tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ---- Users tab -------------------------------------------------------

    def _build_users_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Filter + active-only toggle
        top = QHBoxLayout()
        top.addWidget(QLabel('Filter:'))
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText('username…')
        self.user_filter.textChanged.connect(self._apply_user_filter)
        top.addWidget(self.user_filter)
        self.active_only_cb = QCheckBox('Active only')
        self.active_only_cb.setChecked(True)
        self.active_only_cb.stateChanged.connect(lambda _: self._load_users())
        top.addWidget(self.active_only_cb)
        top.addStretch()
        layout.addLayout(top)

        # Users table
        self.users_table = QTableWidget(0, 4)
        self.users_table.setHorizontalHeaderLabels(['Username', 'Role', 'Active', 'Created'])
        self.users_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.users_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.users_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.users_table.setAlternatingRowColors(True)
        layout.addWidget(self.users_table)

        # Action buttons
        btns = QHBoxLayout()
        add_btn = QPushButton('Add User…')
        add_btn.clicked.connect(self._add_user)
        btns.addWidget(add_btn)

        change_role_btn = QPushButton('Change Role…')
        change_role_btn.clicked.connect(self._change_role)
        btns.addWidget(change_role_btn)

        toggle_active_btn = QPushButton('Toggle Active')
        toggle_active_btn.clicked.connect(self._toggle_active)
        btns.addWidget(toggle_active_btn)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self._load_users)
        btns.addWidget(refresh_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.users_info = QLabel('')
        layout.addWidget(self.users_info)
        return w

    # ---- Assignments tab -------------------------------------------------

    def _build_assignments_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        self.assign_table = QTableWidget(0, 5)
        self.assign_table.setHorizontalHeaderLabels(['ID', 'Supervisor', 'Investigator', 'Examiner', 'Assigned By'])
        self.assign_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.assign_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.assign_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.assign_table.setAlternatingRowColors(True)
        layout.addWidget(self.assign_table)

        btns = QHBoxLayout()
        add_a_btn = QPushButton('Add Assignment…')
        add_a_btn.clicked.connect(self._add_assignment)
        btns.addWidget(add_a_btn)

        remove_a_btn = QPushButton('Remove Selected')
        remove_a_btn.clicked.connect(self._remove_assignment)
        btns.addWidget(remove_a_btn)

        refresh_a_btn = QPushButton('Refresh')
        refresh_a_btn.clicked.connect(self._load_assignments)
        btns.addWidget(refresh_a_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.assign_info = QLabel('')
        layout.addWidget(self.assign_info)
        return w

    # ---- Data loading ----------------------------------------------------

    def _load_users(self) -> None:
        active_only = self.active_only_cb.isChecked()
        self._all_users = self.db.list_users(active_only=active_only)
        self._apply_user_filter()

    def _apply_user_filter(self) -> None:
        f = self.user_filter.text().strip().lower()
        rows = [u for u in self._all_users if not f or f in u['username'].lower()]
        self.users_table.setRowCount(0)
        for i, u in enumerate(rows):
            self.users_table.insertRow(i)
            self.users_table.setItem(i, 0, QTableWidgetItem(u['username']))
            self.users_table.setItem(i, 1, QTableWidgetItem(u['role']))
            self.users_table.setItem(i, 2, QTableWidgetItem('Yes' if u['is_active'] else 'No'))
            self.users_table.setItem(i, 3, QTableWidgetItem(str(u.get('created_at') or '')[:10]))
            self.users_table.item(i, 0).setData(Qt.UserRole, u)
        self.users_info.setText(f'{len(rows)} user(s)  |  server mode required for user management')

    def _load_assignments(self) -> None:
        self._all_assignments = self.db.list_supervisor_assignments()
        self.assign_table.setRowCount(0)
        for i, a in enumerate(self._all_assignments):
            self.assign_table.insertRow(i)
            self.assign_table.setItem(i, 0, QTableWidgetItem(str(a.get('id') or '')))
            self.assign_table.setItem(i, 1, QTableWidgetItem(str(a.get('supervisor') or '')))
            self.assign_table.setItem(i, 2, QTableWidgetItem(str(a.get('investigator') or '')))
            self.assign_table.setItem(i, 3, QTableWidgetItem(str(a.get('examiner') or '')))
            self.assign_table.setItem(i, 4, QTableWidgetItem(str(a.get('assigned_by') or '')))
            self.assign_table.item(i, 0).setData(Qt.UserRole, a)
        self.assign_info.setText(f'{len(self._all_assignments)} active assignment(s)')

    # ---- Actions ---------------------------------------------------------

    def _selected_user(self) -> Optional[Dict[str, Any]]:
        rows = self.users_table.selectedItems()
        if not rows:
            QMessageBox.warning(self, 'No Selection', 'Select a user first.')
            return None
        return self.users_table.item(rows[0].row(), 0).data(Qt.UserRole)

    def _add_user(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle('Add User')
        form = QFormLayout(dlg)
        username_edit = QLineEdit()
        username_edit.setPlaceholderText('lowercase username')
        form.addRow('Username:', username_edit)
        role_combo = QComboBox()
        role_combo.addItems(self.USER_ROLES)
        form.addRow('Role:', role_combo)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QDialog.Accepted:
            return
        username = username_edit.text().strip().lower()
        role = role_combo.currentText()
        if not username:
            QMessageBox.warning(self, 'Missing Data', 'Username is required.')
            return
        result = self.db.create_user(username, role)
        if result:
            QMessageBox.information(self, 'Created', f"User '{username}' created with role '{role}'.")
            self._load_users()
        else:
            QMessageBox.warning(self, 'Failed', 'Could not create user. Check server connection and that you have admin privileges.')

    def _change_role(self) -> None:
        u = self._selected_user()
        if not u:
            return
        role, ok = QInputDialog.getItem(
            self, 'Change Role', f"New role for '{u['username']}':",
            self.USER_ROLES, self.USER_ROLES.index(u['role']) if u['role'] in self.USER_ROLES else 0,
            False,
        )
        if not ok:
            return
        result = self.db.update_user(u['username'], role=role)
        if result:
            QMessageBox.information(self, 'Updated', f"Role changed to '{role}'.")
            self._load_users()
        else:
            QMessageBox.warning(self, 'Failed', 'Could not update user role.')

    def _toggle_active(self) -> None:
        u = self._selected_user()
        if not u:
            return
        new_state = not u['is_active']
        action = 'activate' if new_state else 'deactivate'
        reply = QMessageBox.question(
            self, 'Confirm',
            f"{action.title()} user '{u['username']}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        if new_state:
            result = self.db.update_user(u['username'], is_active=True)
        else:
            result = self.db.deactivate_user(u['username'])
        if result:
            QMessageBox.information(self, 'Done', f"User '{u['username']}' {action}d.")
            self._load_users()
        else:
            QMessageBox.warning(self, 'Failed', f'Could not {action} user.')

    def _add_assignment(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle('Add Supervisor Assignment')
        form = QFormLayout(dlg)
        sup_edit = QLineEdit()
        sup_edit.setPlaceholderText('supervisor username')
        form.addRow('Supervisor:', sup_edit)
        inv_edit = QLineEdit()
        inv_edit.setPlaceholderText('investigator username')
        form.addRow('Investigator:', inv_edit)
        ex_edit = QLineEdit()
        ex_edit.setPlaceholderText('examiner username (optional)')
        form.addRow('Examiner:', ex_edit)
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)
        if dlg.exec_() != QDialog.Accepted:
            return
        supervisor = sup_edit.text().strip().lower()
        investigator = inv_edit.text().strip().lower()
        examiner = ex_edit.text().strip().lower()
        if not supervisor or not investigator:
            QMessageBox.warning(self, 'Missing Data', 'Supervisor and investigator are required.')
            return
        result = self.db.create_supervisor_assignment(supervisor, investigator, examiner)
        if result:
            QMessageBox.information(self, 'Created', 'Supervisor assignment created.')
            self._load_assignments()
        else:
            QMessageBox.warning(self, 'Failed', 'Could not create assignment. Check that the supervisor has a supervisor or admin role.')

    def _remove_assignment(self) -> None:
        rows = self.assign_table.selectedItems()
        if not rows:
            QMessageBox.warning(self, 'No Selection', 'Select an assignment to remove.')
            return
        a = self.assign_table.item(rows[0].row(), 0).data(Qt.UserRole)
        if not a:
            return
        reply = QMessageBox.question(
            self, 'Confirm',
            f"Remove assignment: {a.get('supervisor')} → {a.get('investigator')}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        ok = self.db.delete_supervisor_assignment(int(a['id']))
        if ok:
            QMessageBox.information(self, 'Removed', 'Assignment removed.')
            self._load_assignments()
        else:
            QMessageBox.warning(self, 'Failed', 'Could not remove assignment.')


# ------------------------------------------------------------------
# Custom Calendar Widget with Event Highlighting
# ------------------------------------------------------------------

class EventCalendarWidget(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Map of date string 'YYYY-MM-DD' -> set/list of event types present on that date
        self.event_dates = {}

    def set_event_dates(self, mapping):
        """Set the mapping of dates to event types.

        mapping: dict where key is 'YYYY-MM-DD' and value is iterable of event type strings
        """
        self.event_dates = {}
        for k, v in (mapping.items() if isinstance(mapping, dict) else ((d, ['event']) for d in mapping)):
            try:
                self.event_dates[str(k)] = set(v) if v is not None else set()
            except Exception as e:
                self.event_dates[str(k)] = {str(v)}
        self.updateCells()

    def paintCell(self, painter, rect, date):
        """Override to highlight dates with events"""
        # First call the parent paint method
        super().paintCell(painter, rect, date)

        # Check if this date has events
        date_str = date.toString('yyyy-MM-dd')
        types = self.event_dates.get(date_str)
        if types:
            # Draw small colored badges for each event type at bottom-right
            painter.save()
            # Draw the date number normally first
            painter.setPen(self.palette().color(self.palette().Text))
            painter.setFont(self.font())
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))

            # Define colors for event types
            color_map = {
                'trial': QColor('#dc3545'),
                'sentencing': QColor('#6f42c1'),
                'hearing': QColor('#007bff'),
                'deposition': QColor('#fd7e14'),
                'case_created': QColor('#28a745'),
                'legal_due': QColor('#ffc107'),
                'legal_investigator_approved': QColor('#20c997'),
                'legal_state_attorney_approved': QColor('#0dcaf0'),
                'legal_judicial_approval': QColor('#6f42c1'),
                'legal_sent_to_provider': QColor('#fd7e14'),
                'legal_provider_acknowledged': QColor('#0d6efd'),
                'legal_sla_due': QColor('#ffc107'),
                'legal_sla_breach': QColor('#dc3545'),
                'prosecution_visit': QColor('#17a2b8'),
                'evidence_not_imaged': QColor('#6c757d'),
                'evidence_imaged': QColor('#28a745'),
                'evidence_analyzed': QColor('#20c997'),
                'evidence_other': QColor('#6f42c1'),
                'evidence_status': QColor('#0dcaf0')
            }

            # Draw up to 4 small dots to represent event types
            max_badges = 4
            badge_radius = max(3, min(rect.width(), rect.height()) // 12)
            spacing = badge_radius + 2
            start_x = rect.right() - spacing - 2
            y = rect.bottom() - spacing - 2
            drawn = 0
            for et in sorted(types):
                if drawn >= max_badges:
                    break
                c = color_map.get(et, QColor('#6c757d'))
                painter.setPen(Qt.NoPen)
                painter.setBrush(c)
                cx = start_x - drawn * (spacing)
                cy = y
                painter.drawEllipse(cx - badge_radius, cy - badge_radius, badge_radius * 2, badge_radius * 2)
                drawn += 1

            # If more events than badges, draw a small number indicator
            if len(types) > max_badges:
                more_text = f"+{len(types) - max_badges}"
                painter.setPen(QColor('#ffffff'))
                painter.setFont(QFont(self.font().family(), max(6, badge_radius)))
                painter.drawText(rect.adjusted(rect.width() - 40, rect.height() - 20, -4, -4), Qt.AlignRight | Qt.AlignBottom, more_text)

            painter.restore()
        else:
            # For non-event dates, just draw the date normally
            painter.save()
            painter.setPen(self.palette().color(self.palette().Text))
            painter.drawText(rect, Qt.AlignCenter, str(date.day()))
            painter.restore()

# ------------------------------------------------------------------
# Custom Delegate for Colored Status Blocks + Hover Tooltips
# ------------------------------------------------------------------

class StatusBlockDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if index.column() not in [2, 3]:  # Evidence & Legal columns
            super(StatusBlockDelegate, self).paint(painter, option, index)
            painter.restore()
            return

        statuses = index.data(Qt.UserRole)
        # Only process if statuses is a list (not a bool or other type from child rows)
        if not isinstance(statuses, list) or not statuses:
            super(StatusBlockDelegate, self).paint(painter, option, index)
            painter.restore()
            return

        # Improved padding for better visibility
        rect = option.rect.adjusted(6, 4, -6, -4)

        color_map = {
            'green': QColor('#28a745'),
            'yellow': QColor('#ffc107'),
            'red': QColor('#dc3545'),
            'grey': QColor('#6c757d'),
            'gray': QColor('#6c757d')
        }

        # If there's only a single summary status, fill the cell background
        # with the status color and draw the label in contrasting text for
        # readability across themes.
        if len(statuses) == 1:
            label, color_name, _ = statuses[0]
            color = color_map.get(color_name.lower(), QColor('#6c757d'))
            # Draw rounded rectangle for better appearance
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 4, 4)

            # pick text color based on luminance for contrast
            cr, cg, cb = color.red(), color.green(), color.blue()
            luminance = 0.299 * cr + 0.587 * cg + 0.114 * cb
            text_color = QColor('#ffffff') if luminance <= 128 else QColor('#000000')
            painter.setPen(text_color)
            painter.setFont(QFont(painter.font().family(), painter.font().pointSize(), QFont.Bold))
            text_rect = rect.adjusted(8, 0, -8, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)
            painter.restore()
            return

        # Count items by status for summary display
        status_counts = {}
        for label, color_name, _ in statuses:
            status_key = label.lower().replace(' ', '_')
            status_counts[status_key] = status_counts.get(status_key, 0) + 1

        # Determine overall cell color based on priority (red > yellow > green > grey)
        overall_color = QColor('#6c757d')  # Default grey
        if any('not_imaged' in k or 'pending' in k or 'overdue' in k for k in status_counts.keys()):
            overall_color = QColor('#ffc107')  # Yellow for pending/not complete
        if any('overdue' in k for k in status_counts.keys()):
            overall_color = QColor('#dc3545')  # Red for overdue
        if all('imaged' in k or 'completed' in k for k in status_counts.keys()):
            overall_color = QColor('#28a745')  # Green if all complete

        # Fill cell background with overall status color - use rounded rectangle
        painter.setPen(Qt.NoPen)
        painter.setBrush(overall_color)
        painter.drawRoundedRect(rect, 4, 4)

        # Create summary text showing counts
        summary_parts = []
        for status, count in status_counts.items():
            display_status = status.replace('_', ' ').title()
            summary_parts.append(f"{count} {display_status}")

        summary_text = ', '.join(summary_parts)

        # Choose text color for contrast
        cr, cg, cb = overall_color.red(), overall_color.green(), overall_color.blue()
        luminance = 0.299 * cr + 0.587 * cg + 0.114 * cb
        text_color = QColor('#ffffff') if luminance <= 128 else QColor('#000000')
        painter.setPen(text_color)
        painter.setFont(QFont(painter.font().family(), painter.font().pointSize(), QFont.Bold))

        # Draw summary text, truncated if too long
        font_metrics = painter.fontMetrics()
        available_width = rect.width() - 12  # Small margin
        elided_text = font_metrics.elidedText(summary_text, Qt.ElideRight, available_width)
        painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, elided_text)

        painter.restore()

    def helpEvent(self, helpEvent, view, option, index):
        if helpEvent.type() == QEvent.ToolTip and index.column() in [2, 3]:
            statuses = index.data(Qt.UserRole) or []
            if not statuses:
                return False

            # Get case information for enhanced tooltips
            source_index = view.model().mapToSource(index) if hasattr(view.model(), 'mapToSource') else index
            row = source_index.row()
            case_number = view.model().item(row, 0).text() if hasattr(view.model(), 'item') else "Unknown"

            # Separate summary from detailed statuses
            summary_status = None
            detailed_statuses = []

            for status in statuses:
                if len(status) >= 3:
                    label, color, tooltip = status
                    if "evidence items pending" in tooltip or "legal processes pending" in tooltip:
                        summary_status = (label, color, tooltip)
                    else:
                        detailed_statuses.append((label, color, tooltip))

            tooltip_parts = []

            # Add summary information
            if summary_status:
                label, color, tooltip = summary_status
                tooltip_parts.append(f"<div style='margin-bottom:8px;'><b>Summary:</b> {tooltip}</div>")

            # Add detailed breakdown
            if detailed_statuses:
                tooltip_parts.append("<b>Detailed Status:</b>")
                status_counts = {}
                urgent_items = []

                for label, color, tooltip in detailed_statuses:
                    # Count by status type
                    status_key = label.lower().replace(' ', '_')
                    status_counts[status_key] = status_counts.get(status_key, 0) + 1

                    # Check for urgent items (overdue dates, etc.)
                    if 'overdue' in tooltip.lower() or 'was' in tooltip.lower():
                        urgent_items.append(tooltip)

                # Show status breakdown
                breakdown_items = []
                for status, count in status_counts.items():
                    display_status = status.replace('_', ' ').title()
                    breakdown_items.append(f"{display_status}: {count}")
                tooltip_parts.append(f"<div style='margin-left:10px; margin-bottom:8px;'>• {'<br>• '.join(breakdown_items)}</div>")

                # Show urgent items
                if urgent_items:
                    tooltip_parts.append("<b style='color:#dc3545;'>⚠ Urgent Items:</b>")
                    for item in urgent_items[:3]:  # Limit to 3 most urgent
                        tooltip_parts.append(f"<div style='margin-left:10px; color:#dc3545;'>• {item}</div>")

            # Add actionable hints
            tooltip_parts.append("<div style='margin-top:8px; padding-top:8px; border-top:1px solid #dee2e6;'>")
            tooltip_parts.append("<b>Actions:</b>")
            tooltip_parts.append("• <i>Click</i> to view detailed breakdown")
            tooltip_parts.append("• <i>Double-click case</i> to open case details")
            tooltip_parts.append("</div>")

            full_tooltip = f"""
            <div style="background:#ffffff; border:1px solid #dee2e6; border-radius:8px; padding:12px; max-width:450px; font-family:'Segoe UI'; box-shadow:0 4px 12px rgba(0,0,0,0.15);">
                <div style="font-size:11px; color:#6c757d; margin-bottom:8px;">Case {case_number}</div>
                {"".join(tooltip_parts)}
            </div>
            """

            QToolTip.showText(helpEvent.globalPos(), full_tooltip)
            return True
        return super(StatusBlockDelegate, self).helpEvent(helpEvent, view, option, index)


class DateDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QDateEdit(parent)
        editor.setDisplayFormat('yyyy-MM-dd')
        editor.setCalendarPopup(True)
        return editor

    def setEditorData(self, editor, index):
        val = index.data(Qt.DisplayRole) or ''
        try:
            if val:
                d = datetime.fromisoformat(val)
                editor.setDate(QDate(d.year, d.month, d.day))
        except ValueError:
            pass

    def setModelData(self, editor, model, index):
        qd = editor.date()
        iso = f"{qd.year():04d}-{qd.month():02d}-{qd.day():02d}"
        model.setData(index, iso)

# ------------------------------------------------------------------
# Sort & Filter Proxy Model
# ------------------------------------------------------------------

class ForensicSortFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filters = {}
        self.global_filter = ""
        self.current_view = "Investigator"  # Default
        self.setDynamicSortFilter(True)
        self.upcoming_days = 14
        self.upcoming_only = False

    def setGlobalFilter(self, text):
        self.global_filter = text.lower()
        self.invalidateFilter()

    def setColumnFilter(self, column, value):
        self.filters[column] = value.lower() if value else ""
        self.invalidateFilter()

    def setUpcomingFilter(self, days:int):
        self.upcoming_days = int(days)
        self.invalidateFilter()

    def setUpcomingOnly(self, enabled:bool):
        self.upcoming_only = bool(enabled)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()

        if self.global_filter:
            matched = False
            # Check columns based on view: Case # (0), Assigned To (1), Status (4 for Investigator, 3 for Examiner)
            status_col = 4 if self.current_view == "Investigator" else 3
            for col in [0, 1, status_col]:
                item = model.item(source_row, col)
                if item and self.global_filter in item.text().lower():
                    matched = True
                    break
            if not matched:
                return False

        for column, filter_text in self.filters.items():
            if filter_text:
                item = model.item(source_row, column)
                if not item or filter_text not in item.text().lower():
                    return False
        # Upcoming-only filter: check trial date column
        if self.upcoming_only:
            # trial column index depends on view
            trial_col = 5 if self.current_view == "Investigator" else 4
            item = model.item(source_row, trial_col)
            if not item:
                return False
            trial_iso = item.data(Qt.UserRole + 2) or item.text()
            if not trial_iso:
                return False
            try:
                trial_dt = datetime.fromisoformat(trial_iso)
                days_left = (trial_dt.date() - datetime.now(timezone.utc).date()).days
                return days_left <= self.upcoming_days
            except ValueError:
                return False

        return True

    def lessThan(self, left, right):
        left_data = left.data(Qt.UserRole)
        right_data = right.data(Qt.UserRole)
        column = left.column()

        if column == 2:
            # Evidence column (same in both views)
            left_green = sum(1 for s in left_data if 'green' in str(s).lower())
            right_green = sum(1 for s in right_data if 'green' in str(s).lower())
            return left_green > right_green
        elif column == 3:
            if self.current_view == "Investigator":
                # Legal column in Investigator view
                left_red = sum(1 for s in left_data if 'red' in str(s).lower())
                right_red = sum(1 for s in right_data if 'red' in str(s).lower())
                if left_red != right_red:
                    return left_red > right_red
                left_yellow = sum(1 for s in left_data if 'yellow' in str(s).lower())
                right_yellow = sum(1 for s in right_data if 'yellow' in str(s).lower())
                return left_yellow > right_yellow
            else:
                # Report Status column in Examiner view
                priority = {'closed': 6, 'approved': 5, 'submitted': 4, 'in_peer_review': 3, 'revisions_needed': 2, 'draft': 1}
                return priority.get(str(left_data).lower(), 0) > priority.get(str(right_data).lower(), 0)
        elif column == 4:
            # Report Status column in Investigator view only
            priority = {'closed': 6, 'approved': 5, 'submitted': 4, 'in_peer_review': 3, 'revisions_needed': 2, 'draft': 1}
            return priority.get(str(left_data).lower(), 0) > priority.get(str(right_data).lower(), 0)

        # Trial Date comparison
        # Investigator view: trial date column index 5, Examiner view: 4
        trial_col = 5 if self.current_view == "Investigator" else 4
        if column == trial_col:
            try:
                from datetime import datetime
                left_date = left.data(Qt.UserRole + 2)
                right_date = right.data(Qt.UserRole + 2)
                if not left_date and not right_date:
                    return False
                if not left_date:
                    return False
                if not right_date:
                    return True
                ld = datetime.fromisoformat(left_date)
                rd = datetime.fromisoformat(right_date)
                return ld < rd
            except ValueError:
                return super().lessThan(left, right)

        return super().lessThan(left, right)

# ------------------------------------------------------------------
# Main Window
# ------------------------------------------------------------------

class MainWindow(QMainWindow):
    def __init__(self, safe_mode: bool = False) -> None:
        """Initialize the main application window

        Sets up UI components including tabs, menu bar, and connects to database.
        
        Args:
            safe_mode: If True, pass safe mode flag to database manager
        """
        # Call parent class constructor first
        super().__init__()
        
        self.safe_mode = safe_mode
        
        # Initialize logging (call once at startup)
        logger = setup_logging("forensic_app")

        self.setWindowTitle("FuDog Labs Forensic Report Suite")
        self.setMinimumSize(1400, 900)

        os.makedirs("cases", exist_ok=True)
        self.db = DatabaseManager(safe_mode=self.safe_mode)
        if isinstance(current_user, dict) and current_user.get('token'):
            self.db.token = current_user.get('token')
        
        # Log database status
        db_status = self.db.get_database_status()
        if db_status.get('readonly_mode'):
            logger.warning("Database is operating in READ-ONLY mode. Changes will not persist.")
        
        self.current_view = "Investigator"  # Default view
        self.chart_cache = ChartCache()  # Initialize chart cache
        self.case_hashes = {}  # Track case data hashes for incremental updates
        self.case_row_map = {}  # Map case IDs to row indices
        self._adaptive_layout_config = {
            'enabled': True,
            'density': 'balanced',
            'breakpoints': {'narrow': 1280, 'medium': 1700},
        }
        self._chart_width_bucket = 'wide'
        self._chart_resize_timer = QTimer(self)
        self._chart_resize_timer.setSingleShot(True)
        self._chart_resize_timer.timeout.connect(self._on_chart_resize_timeout)

        # Discovery heartbeat (desktop -> server) state
        self._heartbeat_timer: Optional[QTimer] = None
        self._heartbeat_inflight = False
        self._heartbeat_endpoints: List[str] = []
        self._heartbeat_client_id = str(uuid.uuid4())
        self._discovery_probe_server: Optional[ThreadingHTTPServer] = None
        self._discovery_probe_thread: Optional[threading.Thread] = None
        self._discovery_probe_port: int = 0
        
        # Initialize notification manager
        from notification_manager import NotificationManager
        self.notification_manager = NotificationManager(self.db, config, self)
        
        # Connect notification signals
        self.notification_manager.notification_created.connect(self.on_notification_created)
        self.notification_manager.badge_count_changed.connect(self.update_notification_badge)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.tabs.removeTab)
        self.setCentralWidget(self.tabs)

        self.theme_manager = ThemeManager(app, self)
        self.theme_manager.set_theme_changed_callback(self.refresh_dashboard)

        self.status_colors = config.get("status_colors", {})
        
        # =====================================================================
        # DPI and Screen Change Handling
        # Monitor for screen changes (laptop <-> external monitor switching)
        # Ensures fonts and UI elements scale correctly
        # =====================================================================
        self._current_screen = None
        self._setup_screen_change_monitoring()
        
        # Set minimum size policy for all buttons to prevent tiny unreadable text
        self._apply_minimum_button_sizes()

        self.setup_menu()
        self.load_existing_cases()
        self._setup_discovery_heartbeat()

    def _setup_discovery_heartbeat(self) -> None:
        """Start periodic, non-blocking heartbeat registration with server discovery."""
        hb_cfg = (config.get('discovery_heartbeat') or {}) if isinstance(config, dict) else {}
        enabled = bool(hb_cfg.get('enabled', True))
        if not enabled:
            logger.info("Discovery heartbeat disabled by configuration")
            return

        # Start local probe endpoint first so scanner verification can succeed.
        self._setup_discovery_probe_endpoint()

        self._heartbeat_endpoints = self._resolve_discovery_heartbeat_endpoints()
        if not self._heartbeat_endpoints:
            # No server configured; standalone mode should remain quiet.
            return

        interval_seconds = int(hb_cfg.get('interval_seconds', 60) or 60)
        interval_seconds = max(15, interval_seconds)

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(interval_seconds * 1000)
        self._heartbeat_timer.timeout.connect(self._send_discovery_heartbeat_async)
        self._heartbeat_timer.start()

        # Send startup heartbeat immediately so instance appears right away.
        self._send_discovery_heartbeat_async()

    def _resolve_discovery_heartbeat_endpoints(self) -> List[str]:
        """Build one or more discovery heartbeat URLs from configured server_url."""
        server_url = str((config or {}).get('server_url', '') or '').strip().rstrip('/')
        if not server_url:
            return []

        endpoints: List[str] = []

        # Existing clients typically use /api/v1 base in server_url.
        if server_url.endswith('/api/v1'):
            endpoints.append(f"{server_url}/discovery/heartbeat")
        else:
            endpoints.append(f"{server_url}/api/v1/discovery/heartbeat")
            endpoints.append(f"{server_url}/discovery/heartbeat")

        # Preserve order and remove duplicates.
        unique: List[str] = []
        seen = set()
        for url in endpoints:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique

    def _setup_discovery_probe_endpoint(self) -> None:
        """Expose a lightweight local endpoint used by server active-scan verification."""
        hb_cfg = (config.get('discovery_heartbeat') or {}) if isinstance(config, dict) else {}
        probe_enabled = bool(hb_cfg.get('probe_enabled', True))
        if not probe_enabled:
            return

        desired_port = int(hb_cfg.get('probe_port', 8765) or 8765)
        desired_port = max(1024, min(65535, desired_port))

        parent_window = self

        class DiscoveryProbeHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                path = (self.path or '').split('?', 1)[0]
                if path != '/api/v1/client/discovery':
                    self.send_response(404)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(b'{"error":"not found"}')
                    return

                payload = parent_window._build_discovery_probe_payload()
                body = json.dumps(payload).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format, *args):
                # Keep this endpoint quiet in normal app logs.
                return

        try:
            server = ThreadingHTTPServer(('0.0.0.0', desired_port), DiscoveryProbeHandler)
            server.daemon_threads = True
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()
            self._discovery_probe_server = server
            self._discovery_probe_thread = server_thread
            self._discovery_probe_port = desired_port
            logger.info(f"Discovery probe endpoint listening on port {desired_port}")
        except Exception as error:
            self._discovery_probe_server = None
            self._discovery_probe_thread = None
            self._discovery_probe_port = 0
            logger.warning(f"Discovery probe endpoint unavailable on port {desired_port}: {error}")

    def _build_discovery_probe_payload(self) -> Dict[str, Any]:
        """Response payload for server discovery scan verification endpoint."""
        username = 'unknown'
        role = 'unknown'
        if isinstance(current_user, dict):
            username = str(current_user.get('username') or 'unknown')
            role = str(current_user.get('role') or 'unknown')

        try:
            hostname = socket.gethostname() or 'unknown-host'
            ip_addr = socket.gethostbyname(hostname)
        except Exception:
            hostname = 'unknown-host'
            ip_addr = ''

        return {
            'service': 'forensic-main-app',
            'product': 'FuDog Labs Forensic Report Suite',
            'app_id': self._heartbeat_client_id,
            'hostname': hostname,
            'ip': ip_addr,
            'port': self._discovery_probe_port,
            'username': username,
            'role': role,
            'version': APP_VERSION,
        }

    def _build_discovery_heartbeat_payload(self) -> Dict[str, Any]:
        """Build heartbeat payload to auto-register this desktop instance."""
        username = 'unknown'
        if isinstance(current_user, dict):
            username = str(current_user.get('username') or 'unknown')

        try:
            hostname = socket.gethostname() or 'unknown-host'
            ip_addr = socket.gethostbyname(hostname)
        except Exception:
            hostname = 'unknown-host'
            ip_addr = ''

        return {
            'app_id': self._heartbeat_client_id,
            'hostname': hostname,
            'ip': ip_addr,
            'port': self._discovery_probe_port,
            'username': username,
            'version': APP_VERSION,
            'trust_state': 'pending',
            'client_type': 'desktop-main-app',
        }

    def _send_discovery_heartbeat_async(self) -> None:
        """Send heartbeat without blocking the UI thread."""
        if self._heartbeat_inflight or not self._heartbeat_endpoints:
            return

        payload = self._build_discovery_heartbeat_payload()
        hb_cfg = (config.get('discovery_heartbeat') or {}) if isinstance(config, dict) else {}
        shared_token = str(hb_cfg.get('shared_token', '') or '').strip()

        self._heartbeat_inflight = True

        def _worker() -> None:
            try:
                body = json.dumps(payload).encode('utf-8')
                headers = {
                    'Content-Type': 'application/json',
                    'User-Agent': 'forensic-main-app/heartbeat',
                }
                if shared_token:
                    headers['X-Discovery-Token'] = shared_token

                for endpoint in self._heartbeat_endpoints:
                    req = urllib_request.Request(endpoint, data=body, headers=headers, method='POST')
                    try:
                        with urllib_request.urlopen(req, timeout=3) as resp:
                            if 200 <= resp.status < 300:
                                return
                    except urllib_error.URLError:
                        continue
                    except Exception:
                        continue
            finally:
                self._heartbeat_inflight = False

        threading.Thread(target=_worker, daemon=True).start()
    
    def _setup_screen_change_monitoring(self):
        """Setup monitoring for screen/DPI changes when window moves between displays"""
        # Connect to screen changed signal
        app = QApplication.instance()
        if app:
            # Track which screen the window is on
            self._current_screen = app.primaryScreen()
            
            # Monitor screen changes
            if hasattr(app, 'screenAdded'):
                app.screenAdded.connect(self._on_screen_changed)
            if hasattr(app, 'screenRemoved'):
                app.screenRemoved.connect(self._on_screen_changed)
            
            # Also monitor for window moving between screens
            self.installEventFilter(self)
    
    def _on_screen_changed(self, screen=None):
        """Handle screen/DPI changes"""
        app = QApplication.instance()
        if not app:
            return
        
        # Check if we actually changed screens
        current_screen = app.screenAt(self.geometry().center())
        if current_screen and current_screen != self._current_screen:
            self._current_screen = current_screen
            logger.info(f"Screen changed. New DPI: {current_screen.logicalDotsPerInch()}")
            
            # Refresh UI to adapt to new DPI
            self._refresh_fonts_for_dpi()
    
    def _refresh_fonts_for_dpi(self):
        """Refresh fonts and UI elements for current DPI"""
        app = QApplication.instance()
        if not app:
            return
        
        # Get current screen DPI
        screen = app.screenAt(self.geometry().center()) or app.primaryScreen()
        dpi = screen.logicalDotsPerInch()
        
        # Adjust minimum font size based on DPI
        # Base: 96 DPI (standard) -> 9pt minimum
        # Scale proportionally for higher DPI
        base_dpi = 96.0
        base_font_size = 9
        scaled_font_size = max(base_font_size, int(base_font_size * (dpi / base_dpi)))
        
        # Update application font
        font = app.font()
        if font.pointSize() < scaled_font_size:
            font.setPointSize(scaled_font_size)
            app.setFont(font)
        
        # Re-apply minimum button sizes
        self._apply_minimum_button_sizes()
        
        # Force update
        self.update()
    
    def _apply_minimum_button_sizes(self):
        """Apply minimum size constraints to all buttons to prevent tiny text"""
        # Set a minimum height for buttons to ensure text is readable
        min_height = 24  # Minimum button height in pixels
        
        # Find all buttons in the window
        for button in self.findChildren(QPushButton):
            # Set minimum height
            if button.minimumHeight() < min_height:
                button.setMinimumHeight(min_height)
            
            # Ensure text isn't elided (cut off)
            button.setSizePolicy(
                button.sizePolicy().horizontalPolicy(),
                button.sizePolicy().verticalPolicy()
            )
        
        # Also apply to menu items
        menu_bar = self.menuBar()
        if menu_bar:
            font = menu_bar.font()
            if font.pointSize() < 9:
                font.setPointSize(9)
                menu_bar.setFont(font)
    
    def eventFilter(self, obj, event):
        """Monitor for screen changes when window is moved"""
        if obj == self and event.type() == QEvent.Move:
            # Window moved - check if we're on a different screen
            self._on_screen_changed()
        return super().eventFilter(obj, event)

    def resizeEvent(self, event):
        """Debounce dashboard chart relayout when main window size changes."""
        super().resizeEvent(event)
        # Only reflow charts when dashboard exists.
        if hasattr(self, 'charts_layout'):
            self._chart_resize_timer.start(140)

    def _get_dashboard_width_bucket(self) -> str:
        """Bucketize available dashboard width to drive adaptive chart sizing."""
        adaptive_cfg = getattr(self, '_adaptive_layout_config', {})
        if not adaptive_cfg.get('enabled', True):
            return 'wide'

        if hasattr(self, 'charts_layout') and self.charts_layout.parentWidget():
            width = self.charts_layout.parentWidget().width()
        else:
            width = self.width()

        bps = adaptive_cfg.get('breakpoints', {})
        narrow_bp = int(bps.get('narrow', 1280))
        medium_bp = int(bps.get('medium', 1700))
        if medium_bp <= narrow_bp:
            medium_bp = narrow_bp + 120

        if width < narrow_bp:
            return 'narrow'
        if width < medium_bp:
            return 'medium'
        return 'wide'

    def _on_chart_resize_timeout(self):
        """Refresh dashboard only when width bucket actually changed."""
        if not hasattr(self, 'charts_layout'):
            return
        new_bucket = self._get_dashboard_width_bucket()
        if new_bucket == getattr(self, '_chart_width_bucket', 'wide'):
            return
        self._chart_width_bucket = new_bucket
        self.chart_cache.clear()
        self.refresh_dashboard()

    def setup_menu(self) -> None:
        """Setup application menu bar with file, view, and help menus"""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        new_case_act = QAction("New Case", self)
        new_case_act.setShortcut(QKeySequence.New)
        new_case_act.triggered.connect(self.new_case)
        file_menu.addAction(new_case_act)

        export_csv_act = QAction("Export CSV", self)
        export_csv_act.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_csv_act)

        export_pdf_act = QAction("Export PDF", self)
        export_pdf_act.triggered.connect(self.export_to_pdf)
        file_menu.addAction(export_pdf_act)

        export_excel_act = QAction("Export Excel", self)
        export_excel_act.triggered.connect(self.export_to_excel)
        file_menu.addAction(export_excel_act)

        import_cases_act = QAction("Import Cases (Bulk Excel/CSV)", self)
        import_cases_act.triggered.connect(self.bulk_import_cases)
        file_menu.addAction(import_cases_act)

        import_template_act = QAction("Download Case Import Template", self)
        import_template_act.triggered.connect(self.download_case_import_template)
        file_menu.addAction(import_template_act)

        feature_request_act = QAction("Request Feature", self)
        feature_request_act.triggered.connect(self.show_feature_request)
        file_menu.addAction(feature_request_act)

        bug_report_file_act = QAction("Report Bug", self)
        bug_report_file_act.triggered.connect(self.show_bug_report)
        file_menu.addAction(bug_report_file_act)

        # Documentation submenu
        doc_menu = file_menu.addMenu("Documentation")
        
        main_guide_act = QAction("Main User Guide", self)
        main_guide_act.triggered.connect(lambda: self.open_documentation("MAIN_USER_GUIDE.md"))
        doc_menu.addAction(main_guide_act)
        
        notes_guide_act = QAction("Notes User Guide", self)
        notes_guide_act.triggered.connect(lambda: self.open_documentation("NOTES_USER_GUIDE.md"))
        doc_menu.addAction(notes_guide_act)
        
        reports_guide_act = QAction("Reports User Guide", self)
        reports_guide_act.triggered.connect(lambda: self.open_documentation("REPORTS_USER_GUIDE.md"))
        doc_menu.addAction(reports_guide_act)
        
        archive_guide_act = QAction("Archive Cases User Guide", self)
        archive_guide_act.triggered.connect(lambda: self.open_documentation("ARCHIVE_CASES_USER_GUIDE.md"))
        doc_menu.addAction(archive_guide_act)
        
        server_guide_act = QAction("Server User Guide", self)
        server_guide_act.triggered.connect(lambda: self.open_documentation("SERVER_USER_GUIDE.md"))
        doc_menu.addAction(server_guide_act)
        
        doc_menu.addSeparator()
        
        install_guide_act = QAction("Installation Guide", self)
        install_guide_act.triggered.connect(lambda: self.open_documentation("INSTALLATION_GUIDE.md"))
        doc_menu.addAction(install_guide_act)

        # Settings
        settings_act = QAction("Settings", self)
        settings_act.triggered.connect(self.show_settings_dialog)
        file_menu.addAction(settings_act)

        tools_menu = menu_bar.addMenu("Tools")
        export_pdf_act = QAction("Export PDF", self)
        export_pdf_act.triggered.connect(self.export_pdf_from_menu)
        tools_menu.addAction(export_pdf_act)

        audit_log_act = QAction("Audit Log", self)
        audit_log_act.triggered.connect(self.show_audit_log)
        tools_menu.addAction(audit_log_act)

        peer_review_act = QAction("Peer Review Mode", self)
        peer_review_act.triggered.connect(self.toggle_peer_review)
        tools_menu.addAction(peer_review_act)

        glossary_act = QAction("SWGDE Glossary Search", self)
        glossary_act.setShortcut(QKeySequence("Ctrl+G"))
        glossary_act.triggered.connect(lambda: GlossaryDialog(self).exec_())
        tools_menu.addAction(glossary_act)

        glossary_assist_act = QAction("Glossary Assist", self)
        glossary_assist_act.triggered.connect(self.show_glossary_assist)
        tools_menu.addAction(glossary_assist_act)

        bug_report_act = QAction("Report Bug", self)
        bug_report_act.triggered.connect(self.show_bug_report)
        tools_menu.addAction(bug_report_act)

        case_calendar_act = QAction("Case Calendar", self)
        case_calendar_act.triggered.connect(self.show_case_calendar_dialog)
        tools_menu.addAction(case_calendar_act)

        view_menu = menu_bar.addMenu("View")

        # Add archived cases action
        archived_cases_act = QAction("Archived Cases", self)
        archived_cases_act.setShortcut(QKeySequence("Ctrl+Shift+A"))
        archived_cases_act.triggered.connect(self.show_archived_cases)
        view_menu.addAction(archived_cases_act)

        view_menu.addSeparator()

        supervisor_act = QAction("Supervisor Dashboard...", self)
        supervisor_act.triggered.connect(self.show_supervisor_dashboard)
        view_menu.addAction(supervisor_act)

        admin_users_act = QAction("Admin - User Management...", self)
        admin_users_act.triggered.connect(self.show_admin_users)
        view_menu.addAction(admin_users_act)

        # Add theme submenu (Light / Dark / High Contrast)
        if hasattr(self, 'theme_manager') and hasattr(self.theme_manager, 'theme_menu'):
            view_menu.addSeparator()
            view_menu.addMenu(self.theme_manager.theme_menu)

        # Add user view submenu to match theme menu style
        view_menu.addSeparator()
        user_view_menu = view_menu.addMenu("User View")
        self.investigator_act = QAction("Investigator", self)
        self.investigator_act.setCheckable(True)
        self.investigator_act.setChecked(self.current_view == "Investigator")
        self.investigator_act.triggered.connect(lambda: self.on_view_changed("Investigator"))
        user_view_menu.addAction(self.investigator_act)

        self.examiner_act = QAction("Examiner", self)
        self.examiner_act.setCheckable(True)
        self.examiner_act.setChecked(self.current_view == "Examiner")
        self.examiner_act.triggered.connect(lambda: self.on_view_changed("Examiner"))
        user_view_menu.addAction(self.examiner_act)

        # Settings moved to File->Settings

        # Add Tracker menu
        tracker_menu = menu_bar.addMenu("Tracker")
        add_evidence_act = QAction("Add Evidence Item", self)
        add_evidence_act.triggered.connect(self.add_evidence_item_from_menu)
        tracker_menu.addAction(add_evidence_act)

        import_evidence_act = QAction("Import Evidence (Bulk Excel/CSV)", self)
        import_evidence_act.triggered.connect(self.bulk_import_evidence)
        tracker_menu.addAction(import_evidence_act)

        evidence_template_act = QAction("Download Evidence Import Template", self)
        evidence_template_act.triggered.connect(self.download_evidence_import_template)
        tracker_menu.addAction(evidence_template_act)

        add_legal_act = QAction("Add Legal Process", self)
        add_legal_act.triggered.connect(self.add_legal_process_from_menu)
        tracker_menu.addAction(add_legal_act)

        legal_library_act = QAction("Legal Template Library", self)
        legal_library_act.triggered.connect(self.open_legal_template_library)
        tracker_menu.addAction(legal_library_act)
        
        # Add Legal Workflow submenu
        workflow_menu = tracker_menu.addMenu("⚖️ Legal Workflow")
        workflow_menu.setToolTip("Manage legal process approval stages")
        
        investigator_approval_act = QAction("1️⃣ Mark Investigator Approved", self)
        investigator_approval_act.triggered.connect(self.mark_investigator_approved_from_menu)
        workflow_menu.addAction(investigator_approval_act)
        
        attorney_approval_act = QAction("2️⃣ Mark State Attorney Approved", self)
        attorney_approval_act.triggered.connect(self.mark_state_attorney_approved_from_menu)
        workflow_menu.addAction(attorney_approval_act)
        
        judge_approval_act = QAction("3️⃣ Mark Judicial Approval", self)
        judge_approval_act.triggered.connect(self.mark_judicial_approval_from_menu)
        workflow_menu.addAction(judge_approval_act)
        
        workflow_menu.addSeparator()
        
        send_provider_act = QAction("4️⃣ Send to Provider (⏱️ SLA Starts)", self)
        send_provider_act.triggered.connect(self.mark_sent_to_provider_from_menu)
        send_provider_act.setToolTip("SLA clock starts here")
        workflow_menu.addAction(send_provider_act)
        
        provider_ack_act = QAction("5️⃣ Provider Acknowledged", self)
        provider_ack_act.triggered.connect(self.mark_provider_acknowledged_from_menu)
        workflow_menu.addAction(provider_ack_act)
        
        workflow_menu.addSeparator()
        
        sla_breach_act = QAction("🚨 Record SLA Breach", self)
        sla_breach_act.triggered.connect(self.mark_sla_breach_from_menu)
        workflow_menu.addAction(sla_breach_act)

        add_lead_act = QAction("Add Lead", self)
        add_lead_act.triggered.connect(self.add_lead_from_menu)
        tracker_menu.addAction(add_lead_act)
        
        # Add Notifications menu
        notifications_menu = menu_bar.addMenu("Notifications")
        
        view_notifications_act = QAction("View Notifications", self)
        view_notifications_act.setShortcut(QKeySequence("Ctrl+Shift+N"))
        view_notifications_act.triggered.connect(self.show_notifications_panel)
        notifications_menu.addAction(view_notifications_act)
        
        check_now_act = QAction("Check Now", self)
        check_now_act.triggered.connect(self.notification_manager.trigger_manual_check)
        notifications_menu.addAction(check_now_act)
        
        notifications_menu.addSeparator()
        
        dismiss_all_act = QAction("Dismiss All", self)
        dismiss_all_act.triggered.connect(self.notification_manager.dismiss_all)
        notifications_menu.addAction(dismiss_all_act)

        add_case_date_act = QAction("Add Case Date", self)
        add_case_date_act.triggered.connect(self.add_case_date_from_menu)
        tracker_menu.addAction(add_case_date_act)

    def show_settings_dialog(self):
        dlg = SettingsDialog(self, self.theme_manager, self.status_colors)
        dlg.exec_()

    def show_supervisor_dashboard(self) -> None:
        role = current_user.get('role', '') if current_user else ''
        if role not in ('admin', 'supervisor'):
            QMessageBox.warning(self, 'Access Denied', 'Supervisor Dashboard is only available to supervisors and admins.')
            return
        dlg = SupervisorDashboardDialog(self, self.db, current_user)
        dlg.exec_()

    def show_admin_users(self) -> None:
        role = current_user.get('role', '') if current_user else ''
        if role != 'admin':
            QMessageBox.warning(self, 'Access Denied', 'User management is only available to admins.')
            return
        dlg = AdminUsersDialog(self, self.db, current_user)
        dlg.exec_()
    
    def show_notifications_panel(self):
        """Show the notifications panel dialog"""
        self.notification_manager.show_notifications_panel(self)
    
    def on_notification_created(self, notification_data):
        """Handle new notification creation"""
        logger.info(f"New notification: {notification_data['title']}")
    
    def update_notification_badge(self, count: int):
        """Update notification badge count"""
        # This method updates a notification badge if you add one to the UI
        # For now, just log the count
        logger.info(f"Unread notifications: {count}")

    def load_existing_cases(self) -> None:
        """Load all existing cases from database and populate tabs"""
        while self.tabs.count() > 0:
            self.tabs.removeTab(0)

        # Always show a dashboard - "My Dashboard" for writers, full for supervisors/admins
        self.setup_dashboard()

        # Load case tabs (all own cases for writers, all for admin/supervisor)
        cases = self.db.load_all_cases(current_user["username"], current_user["role"])
        for case in cases:
            tab = CaseTab(case, self.db, current_user, self, self.status_colors)
            self.tabs.addTab(tab, f"Case {case['case_number']}")

        if self.tabs.count() == 1:  # Only dashboard
            reply = QMessageBox.question(self, "No Cases", "No cases found.\nWould you like to create a new case?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.new_case()

    def _populate_case_row(self, case: Dict[str, Any]) -> List[QStandardItem]:
        """Populate a case row for dashboard display
        
        Args:
            case: Case dictionary with case data
            
        Returns:
            List of QStandardItem objects for the row
        """
        # Initialize row list
        row = []
        
        # Case #
        case_item = QStandardItem(case['id'])
        case_item.setFont(QFont(case_item.font().family(), case_item.font().pointSize(), QFont.Bold))
        row.append(case_item)

        # Assigned To
        assigned_item = QStandardItem(case.get('assigned_to', 'N/A'))
        assigned_item.setFont(QFont(assigned_item.font().family(), assigned_item.font().pointSize(), QFont.Bold))
        row.append(assigned_item)

        # Evidence
        evidence_statuses = []
        total_evidence = len(case['evidence_details'])
        completed_evidence = sum(1 for ev in case['evidence_details'] if ev.get('imaging_status', 'not_imaged') == 'imaged')
        pending_count = total_evidence - completed_evidence

        # Calculate completion percentage
        completion_pct = int((completed_evidence / total_evidence * 100)) if total_evidence > 0 else 0

        for ev in case['evidence_details']:
            status = ev.get('imaging_status', 'not_imaged')
            if status == 'not_imaged':
                color = 'yellow'
                label = 'Not Imaged'
                tooltip = f"Evidence {ev['id']}: Not imaged"
            elif status == 'imaged':
                color = 'green'
                label = 'Imaged'
                tooltip = f"Evidence {ev['id']}: Imaged on {ev.get('imaged_date', 'N/A')}"
            else:
                color = 'grey'
                label = status.capitalize()
                tooltip = f"Evidence {ev['id']}: {status}"
            evidence_statuses.append((label, color, tooltip))

        # Enhanced summary badge with completion percentage
        if completion_pct == 100:
            summary_color = 'green'
            summary_text = f"✓ {completion_pct}% Complete"
        elif pending_count <= 2:
            summary_color = 'yellow'
            summary_text = f"⚠ {completion_pct}% ({pending_count} pending)"
        else:
            summary_color = 'red'
            summary_text = f"✗ {completion_pct}% ({pending_count} pending)"

        evidence_summary = (summary_text, summary_color, f"Evidence: {completed_evidence}/{total_evidence} complete ({completion_pct}%). {pending_count} items pending processing")
        evidence_statuses.insert(0, evidence_summary)
        evidence_item = QStandardItem()
        evidence_item.setData(evidence_statuses, Qt.UserRole)
        evidence_item.setToolTip("Click to expand evidence details")
        row.append(evidence_item)

        # Legal (only for Investigator view)
        if self.current_view == "Investigator":
            legal_statuses = []
            for leg in case['legal_details']:
                status = leg.get('status', 'pending')
                color = leg.get('suggested_color', 'yellow')
                label = status.capitalize()
                tooltip = f"Legal {leg['id']}: {leg['type']} - {status}"
                legal_statuses.append((label, color, tooltip))
            # Summary badge for legal processes
            pending_legal = sum(1 for l in case['legal_details'] if l.get('status') not in ['completed', 'no_longer_needed'])
            overdue_legal = 0
            try:
                for l in case['legal_details']:
                    due = l.get('due_date')
                    if due:
                        due_dt = datetime.fromisoformat(due)
                        if due_dt.date() < datetime.now(timezone.utc).date() and l.get('status') not in ['completed', 'no_longer_needed']:
                            overdue_legal += 1
            except Exception as e:
                logger.debug(f"Could not compute legal overdue count: {e}")
                overdue_legal = 0

            if overdue_legal > 0:
                legal_color = 'red'
            elif pending_legal > 0:
                legal_color = 'yellow'
            else:
                legal_color = 'green'
            legal_summary = (f"Pending {pending_legal}", legal_color, f"{pending_legal} legal processes pending; {overdue_legal} overdue")
            legal_statuses.insert(0, legal_summary)
            legal_item = QStandardItem()
            legal_item.setData(legal_statuses, Qt.UserRole)
            legal_item.setToolTip("Click to expand legal process details")
            row.append(legal_item)

        # Report Status
        status = case.get('status', 'draft')
        status_item = QStandardItem(status.capitalize())
        status_item.setData(status.lower(), Qt.UserRole)  # for sorting
        row.append(status_item)

        # Trial / Sentencing dates
        trial_item = QStandardItem(case.get('trial_date') or '')
        sentencing_item = QStandardItem(case.get('sentencing_date') or '')
        # Set user role data for sorting (ISO strings)
        trial_iso = case.get('trial_date')
        if trial_iso:
            trial_item.setData(trial_iso, Qt.UserRole + 2)
        else:
            trial_item.setData('', Qt.UserRole + 2)
        row.append(trial_item)
        row.append(sentencing_item)

        return row, case_item

    def _add_child_rows(self, case_item, case):
        colors = self.get_theme_colors()
        child_label_color = QColor(colors['child_text'])
        child_secondary_color = QColor(colors['child_text_secondary'])
        child_bg = QColor(colors['child_bg'])

        # Add child rows for evidence details
        for ev_index, ev in enumerate(case['evidence_details']):
            child_row = []
            # Evidence # with indentation and icon
            case_child = QStandardItem(f"  📄 Evidence {ev['id']}")  
            case_child.setForeground(child_label_color)
            case_child.setFont(QFont(case_child.font().family(), case_child.font().pointSize(), QFont.Bold))
            case_child.setBackground(child_bg)
            case_child.setData(True, Qt.UserRole)  # Mark as child row
            child_row.append(case_child)
            
            # Item number
            assigned_child = QStandardItem(ev.get('evidence_item_number', ''))
            assigned_child.setForeground(child_secondary_color)
            assigned_child.setFont(QFont(assigned_child.font().family(), case_child.font().pointSize()))
            assigned_child.setBackground(child_bg)
            assigned_child.setData(True, Qt.UserRole)
            child_row.append(assigned_child)
            
            # Evidence details
            evidence_child = QStandardItem(f"{ev.get('type', '')} - {ev.get('imaging_status', '').capitalize()}")
            evidence_child.setForeground(child_secondary_color)
            evidence_child.setFont(QFont(evidence_child.font().family(), case_child.font().pointSize()))
            evidence_child.setBackground(child_bg)
            evidence_child.setData(True, Qt.UserRole)
            child_row.append(evidence_child)
            
            if self.current_view == "Investigator":
                legal_child = QStandardItem("")
                legal_child.setBackground(child_bg)
                legal_child.setData(True, Qt.UserRole)
                child_row.append(legal_child)
            
            # Imaged date
            status_child = QStandardItem(ev.get('imaged_date', 'N/A'))
            status_child.setForeground(child_secondary_color)
            status_child.setFont(QFont(status_child.font().family(), case_child.font().pointSize()))
            status_child.setBackground(child_bg)
            status_child.setData(True, Qt.UserRole)
            child_row.append(status_child)
            
            # Placeholders for trial/sentencing on child rows
            trial_child = QStandardItem('')
            trial_child.setBackground(child_bg)
            trial_child.setData(True, Qt.UserRole)
            child_row.append(trial_child)
            
            sentencing_child = QStandardItem('')
            sentencing_child.setBackground(child_bg)
            sentencing_child.setData(True, Qt.UserRole)
            child_row.append(sentencing_child)

            # Add as child of the main case row
            case_item.appendRow(child_row)

        # Add child rows for legal details (initially hidden, only for Investigator view)
        if self.current_view == "Investigator":
            for leg_index, leg in enumerate(case['legal_details']):
                child_row = []
                # Legal # with indentation and icon
                legal_label = QStandardItem(f"  ⚖️ Legal {leg['id']}")
                legal_label.setForeground(child_label_color)
                legal_label.setFont(QFont(legal_label.font().family(), legal_label.font().pointSize(), QFont.Bold))
                legal_label.setBackground(child_bg)
                legal_label.setData(True, Qt.UserRole)
                child_row.append(legal_label)
                
                # Provider
                provider_child = QStandardItem(leg.get('provider', ''))
                provider_child.setForeground(child_secondary_color)
                provider_child.setFont(QFont(provider_child.font().family(), legal_label.font().pointSize()))
                provider_child.setBackground(child_bg)
                provider_child.setData(True, Qt.UserRole)
                child_row.append(provider_child)
                
                # Empty for Evidence column
                evidence_placeholder = QStandardItem("")
                evidence_placeholder.setBackground(child_bg)
                evidence_placeholder.setData(True, Qt.UserRole)
                child_row.append(evidence_placeholder)
                
                # Legal type and status
                legal_details = QStandardItem(f"{leg.get('type', '')} - {leg.get('status', '').capitalize()}")
                legal_details.setForeground(child_secondary_color)
                legal_details.setFont(QFont(legal_details.font().family(), legal_label.font().pointSize()))
                legal_details.setBackground(child_bg)
                legal_details.setData(True, Qt.UserRole)
                child_row.append(legal_details)
                
                # Empty for Report Status
                status_placeholder = QStandardItem("")
                status_placeholder.setBackground(child_bg)
                status_placeholder.setData(True, Qt.UserRole)
                child_row.append(status_placeholder)
                
                # Placeholders for trial/sentencing
                trial_placeholder = QStandardItem('')
                trial_placeholder.setBackground(child_bg)
                trial_placeholder.setData(True, Qt.UserRole)
                child_row.append(trial_placeholder)
                
                sentencing_placeholder = QStandardItem('')
                sentencing_placeholder.setBackground(child_bg)
                sentencing_placeholder.setData(True, Qt.UserRole)
                child_row.append(sentencing_placeholder)

                # Add as child of the main case row
                case_item.appendRow(child_row)

    def setup_dashboard(self):
        dashboard_tab = QWidget()
        layout = QVBoxLayout(dashboard_tab)

        title_label = QLabel("My Cases Dashboard")
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold; margin: 10px; color: #007bff;")
        layout.addWidget(title_label)

        # Filter bar
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Search:"))
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("Case #, Assigned, Status...")
        self.global_search.textChanged.connect(lambda t: self.sort_proxy.setGlobalFilter(t))
        filter_layout.addWidget(self.global_search)

        filter_layout.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["All", "Draft", "Submitted", "In Peer Review", "Revisions Needed", "Approved", "Closed"])
        self.status_combo.currentTextChanged.connect(lambda t: self.sort_proxy.setColumnFilter(4 if self.current_view == "Investigator" else 3, t if t != "All" else ""))
        filter_layout.addWidget(self.status_combo)

        filter_layout.addWidget(QLabel("Assigned To:"))
        self.assigned_combo = QComboBox()
        self.assigned_combo.addItem("All")
        filter_layout.addWidget(self.assigned_combo)



        # Removed "Upcoming Trials (days):" counter as it's not useful

        # Removed "Highlight upcoming trials" and "Show only upcoming trials" checkboxes as they are not useful

        # Add button to view court dates
        view_court_dates_btn = QPushButton("View Court Dates")
        view_court_dates_btn.clicked.connect(self.show_court_dates_dialog)
        filter_layout.addWidget(view_court_dates_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Charts section
        charts_label = QLabel("Case Overview")
        charts_label.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px 0 5px 0;")
        layout.addWidget(charts_label)

        self.charts_layout = QHBoxLayout()
        self.charts_layout.setSpacing(12)
        self.charts_layout.setContentsMargins(0, 0, 0, 8)
        layout.addLayout(self.charts_layout)



        # Model & Proxy
        self.cases_model = QStandardItemModel()
        headers = ['Case #', 'Assigned To', 'Evidence']
        if self.current_view == "Investigator":
            headers.append('Legal')
        # Standard columns
        headers.extend(['Report Status', 'Trial Date', 'Sentencing'])
        self.cases_model.setHorizontalHeaderLabels(headers)

        self.sort_proxy = ForensicSortFilterProxy()
        self.sort_proxy.setSourceModel(self.cases_model)

        # Use QTreeView for expandable rows
        self.dashboard_table = QTreeView()
        self.dashboard_table.setModel(self.sort_proxy)
        self.dashboard_table.setSortingEnabled(True)
        self.dashboard_table.sortByColumn(len(headers) - 1, Qt.DescendingOrder)
        # Persist and restore sort preference
        try:
            saved_sort = config.get('dashboard_sort', {})
            col = saved_sort.get('column')
            order = saved_sort.get('order', 'desc')
            if col is not None:
                self.dashboard_table.sortByColumn(int(col), Qt.DescendingOrder if order == 'desc' else Qt.AscendingOrder)
        except Exception as e:
            logger.debug(f"Could not restore saved sort: {e}")
        self.dashboard_table.clicked.connect(self.on_dashboard_clicked)
        self.dashboard_table.selectionModel().selectionChanged.connect(self.on_dashboard_selection_changed)
        self.dashboard_table.setAlternatingRowColors(False)
        self.dashboard_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dashboard_table.setExpandsOnDoubleClick(False)
        # Improve readability with better spacing
        self.dashboard_table.setItemsExpandable(True)
        self.dashboard_table.setRootIsDecorated(True)
        self.dashboard_table.setAnimated(True)
        # Context menu for editing dates
        self.dashboard_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.dashboard_table.customContextMenuRequested.connect(self.on_dashboard_context_menu)
        # Allow in-place editing for trial/sentencing cells; commit on itemChanged
        self.cases_model.itemChanged.connect(self.on_dashboard_item_changed)

        # Delegate for colored blocks
        self.status_delegate = StatusBlockDelegate(self.dashboard_table)
        self.dashboard_table.setItemDelegateForColumn(2, self.status_delegate)
        if self.current_view == "Investigator":
            self.dashboard_table.setItemDelegateForColumn(3, self.status_delegate)

        # Styling - Enhanced table UI for better readability
        self.dashboard_table.setAlternatingRowColors(False)
        self.dashboard_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dashboard_table.header().setStretchLastSection(True)
        # Set column width hints for better readability
        self.dashboard_table.setColumnWidth(0, 100)
        self.dashboard_table.setColumnWidth(1, 120)
        # Apply theme-aware styling
        self.apply_dashboard_table_theme()
        # Date delegates for trial/sentencing columns (ensure editable calendar popups)
        try:
            trial_col = 5 if self.current_view == "Investigator" else 4
            sentencing_col = 6 if self.current_view == "Investigator" else 5
            self.dashboard_table.setItemDelegateForColumn(trial_col, DateDelegate(self.dashboard_table))
            self.dashboard_table.setItemDelegateForColumn(sentencing_col, DateDelegate(self.dashboard_table))
        except Exception as e:
            logger.debug(f"Could not set date delegates: {e}")

        # Persist sort preference when user changes sort
        try:
            self.dashboard_table.header().sortIndicatorChanged.connect(self.on_dashboard_sort_changed)
        except Exception as e:
            logger.debug(f"Could not connect sort indicator: {e}")

        layout.addWidget(self.dashboard_table)
        self.tabs.addTab(dashboard_tab, "Dashboard")
        self.refresh_dashboard()

    def _compute_case_hash(self, case):
        data = {
            'id': case['id'],
            'assigned_to': case.get('assigned_to'),
            'status': case.get('status'),
            'trial_date': case.get('trial_date'),
            'sentencing_date': case.get('sentencing_date'),
            'evidence_details': [{'id': e['id'], 'imaging_status': e.get('imaging_status'), 'imaged_date': e.get('imaged_date')} for e in case['evidence_details']],
            'legal_details': [{'id': l['id'], 'status': l.get('status'), 'due_date': l.get('due_date')} for l in case['legal_details']] if self.current_view == "Investigator" else [],
            'leads_details': [{'id': ld['id'], 'completed': ld.get('completed')} for ld in case['leads_details']] if self.current_view == "Investigator" else []
        }
        return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def apply_dashboard_table_theme(self):
        """Apply theme-aware styling to the dashboard table"""
        current_theme = self.theme_manager.current_theme if hasattr(self.theme_manager, 'current_theme') else 'dark'
        theme_key = current_theme if current_theme in THEME_COLOR_TOKENS else 'dark'
        table_colors = THEME_COLOR_TOKENS[theme_key]['table']

        bg_color = table_colors['bg']
        alt_bg_color = table_colors['alt_bg']
        text_color = table_colors['text']
        border_color = table_colors['border']
        header_bg = table_colors['header_bg']
        header_text = table_colors['header_text']
        header_border = table_colors['header_border']
        hover_bg = table_colors['hover_bg']
        hover_border = table_colors['hover_border']
        selected_bg = table_colors['selected_bg']
        selected_border = table_colors['selected_border']
        child_bg = table_colors['child_bg']
        child_text = table_colors['child_text']

        stylesheet = f"""
            QTreeView {{
                font-size: 11px;
                background-color: {bg_color};
                alternate-background-color: {alt_bg_color};
            }}
            QTreeView::item {{
                border: 1px solid {border_color};
                padding: 4px 2px;
                margin: 0px;
                height: 32px;
                background-color: {bg_color};
                color: {text_color};
            }}
            QTreeView::item:hover {{
                background-color: {hover_bg};
                border: 1px solid {hover_border};
            }}
            QTreeView::item:selected {{
                background-color: {selected_bg};
                border: 1px solid {selected_border};
                color: {text_color};
            }}
            QTreeView::item:has-children:!item:open {{
                background-color: {bg_color};
            }}
            /* Style for child rows */
            QTreeView::item:open > QTreeView::item {{
                background-color: {child_bg};
                border: 1px solid {border_color};
                color: {child_text};
                padding: 3px 2px;
            }}
            /* Header styling */
            QHeaderView::section {{
                background-color: {header_bg};
                padding: 6px;
                border: 1px solid {header_border};
                font-weight: bold;
                color: {header_text};
            }}
            /* Vertical lines between columns */
            QTreeView::item {{
                border-right: 1px solid {border_color};
            }}
        """
        self.dashboard_table.setStyleSheet(stylesheet)
        
        # Also update child row colors in the model
        self._update_child_row_colors()
    
    def get_theme_colors(self):
        """Get theme-aware colors for UI elements"""
        current_theme = self.theme_manager.current_theme if hasattr(self.theme_manager, 'current_theme') else 'dark'
        theme_key = current_theme if current_theme in THEME_COLOR_TOKENS else 'dark'
        child_colors = THEME_COLOR_TOKENS[theme_key]['child_row']
        return {
            'child_text': child_colors['label'],
            'child_text_secondary': child_colors['secondary'],
            'child_bg': child_colors['bg']
        }
    
    def _update_child_row_colors(self):
        """Update the colors of child rows in the table model"""
        colors = self.get_theme_colors()
        child_text_color = QColor(colors['child_text'])
        child_text_secondary = QColor(colors['child_text_secondary'])
        child_bg = QColor(colors['child_bg'])
        
        try:
            for row in range(self.cases_model.rowCount()):
                parent_item = self.cases_model.item(row, 0)
                if parent_item and parent_item.hasChildren():
                    for child_row in range(parent_item.rowCount()):
                        for col in range(self.cases_model.columnCount()):
                            child_item = parent_item.child(child_row, col)
                            if child_item:  # Check if child_item exists
                                child_item.setBackground(child_bg)
                                # Set different colors for different columns
                                if col == 0:  # First column (Evidence/Legal label)
                                    child_item.setForeground(child_text_color)
                                    child_item.setFont(QFont(child_item.font().family(), child_item.font().pointSize(), QFont.Bold))
                                else:
                                    child_item.setForeground(child_text_secondary)
                                    child_item.setFont(QFont(child_item.font().family(), child_item.font().pointSize()))
        except Exception as e:
            # Silently handle any errors during child row color updates
            pass

    def refresh_dashboard(self) -> None:
        """Refresh dashboard with latest case details from database"""
        cases = self.db.get_cases_with_details()
        new_case_ids = set(c['id'] for c in cases)
        current_case_ids = set(self.case_hashes.keys())

        to_add = new_case_ids - current_case_ids
        to_remove = current_case_ids - new_case_ids
        to_check = current_case_ids & new_case_ids

        # Remove rows for to_remove
        for case_id in sorted(to_remove, key=lambda cid: self.case_row_map[cid], reverse=True):
            row = self.case_row_map[case_id]
            self.cases_model.removeRow(row)
            del self.case_row_map[case_id]
            del self.case_hashes[case_id]
            # Adjust row indices
            for cid in list(self.case_row_map.keys()):
                if self.case_row_map[cid] > row:
                    self.case_row_map[cid] -= 1

        # Check and update for to_check
        for case_id in to_check:
            case = next(c for c in cases if c['id'] == case_id)
            new_hash = self._compute_case_hash(case)
            if new_hash != self.case_hashes[case_id]:
                row = self.case_row_map[case_id]
                # Remove old row
                self.cases_model.removeRow(row)
                # Insert new row
                row_items, case_item = self._populate_case_row(case)
                self.cases_model.insertRow(row, row_items)
                self._add_child_rows(case_item, case)
                self.case_hashes[case_id] = new_hash
                # Row indices above remain the same since insert at same position

        # Add new rows for to_add
        for case_id in to_add:
            case = next(c for c in cases if c['id'] == case_id)
            row_items, case_item = self._populate_case_row(case)
            row = self.cases_model.rowCount()
            self.cases_model.appendRow(row_items)
            self._add_child_rows(case_item, case)
            self.case_row_map[case_id] = row
            self.case_hashes[case_id] = self._compute_case_hash(case)

        # Update assigned combo
        assigned_users = sorted(set(c.get('assigned_to', 'N/A') for c in cases))
        self.assigned_combo.blockSignals(True)
        self.assigned_combo.clear()
        self.assigned_combo.addItem("All")
        self.assigned_combo.addItems(assigned_users)
        self.assigned_combo.blockSignals(False)
        self.assigned_combo.currentTextChanged.connect(lambda t: self.sort_proxy.setColumnFilter(1, t if t != "All" else ""))

        # Update charts
        self.update_dashboard_charts(cases)
        
        # Apply theme-aware styling to the table
        self.apply_dashboard_table_theme()

    def on_dashboard_clicked(self, index):
        """Handle clicks on the dashboard table"""
        source_index = self.sort_proxy.mapToSource(index)
        col = source_index.column()

        if col in [2, 3]:  # Evidence or Legal columns
            self.show_details_dialog(index)
        else:
            self.open_case_from_dashboard(index)

    def show_details_dialog(self, index):
        """Show a dialog with detailed evidence or legal process information"""
        source_index = self.sort_proxy.mapToSource(index)
        row = source_index.row()
        col = source_index.column()

        case_number = self.cases_model.item(row, 0).text()
        cases = self.db.get_cases_with_details()
        case = next((c for c in cases if c['id'] == case_number), None)
        if not case:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(f"Details for Case {case_number}")
        dialog.setWindowIcon(self.windowIcon())
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(10, 10, 10, 10)

        table = QTableWidget()
        # Style the table with theme-aware colors
        current_theme = self.theme_manager.current_theme if hasattr(self.theme_manager, 'current_theme') else 'dark'
        theme_key = current_theme if current_theme in THEME_COLOR_TOKENS else 'dark'
        dialog_colors = THEME_COLOR_TOKENS[theme_key]['dialog_table']

        table_bg = dialog_colors['bg']
        grid_color = dialog_colors['grid']
        header_bg = dialog_colors['header_bg']
        header_text = dialog_colors['header_text']
        border_color = dialog_colors['border']
        item_text = dialog_colors['item_text']
        
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {table_bg};
                gridline-color: {grid_color};
                border: 1px solid {border_color};
                color: {item_text};
            }}
            QTableWidget::item {{
                padding: 6px;
                border: 1px solid {border_color};
                color: {item_text};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                padding: 8px;
                border: 1px solid {border_color};
                font-weight: bold;
                color: {header_text};
                height: 32px;
            }}
        """)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setDefaultSectionSize(32)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        # Color mapping for status cells
        color_map = {
            'imaged': QColor('#28a745'),      # Green
            'completed': QColor('#28a745'),   # Green
            'not_imaged': QColor('#ffc107'),  # Yellow
            'pending': QColor('#ffc107'),     # Yellow
            'not_needed': QColor('#6c757d'),  # Grey
            'no_longer_needed': QColor('#6c757d'),  # Grey
            'overdue': QColor('#dc3545'),     # Red
            'cancelled': QColor('#6c757d'),   # Grey
        }

        if col == 2:  # Evidence column
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(['ID', 'Item Number', 'Type', 'Imaging Status', 'Imaged Date'])
            table.setRowCount(len(case['evidence_details']))
            for i, ev in enumerate(case['evidence_details']):
                # Set ID
                id_item = QTableWidgetItem(str(ev['id']))
                id_item.setFont(QFont(id_item.font().family(), id_item.font().pointSize(), QFont.Bold))
                table.setItem(i, 0, id_item)
                
                # Set Item Number
                table.setItem(i, 1, QTableWidgetItem(ev.get('evidence_item_number', '')))
                
                # Set Type
                table.setItem(i, 2, QTableWidgetItem(ev.get('type', '')))

                # Status cell with color coding
                status_item = QTableWidgetItem(ev.get('imaging_status', '').capitalize())
                status_item.setFont(QFont(status_item.font().family(), status_item.font().pointSize(), QFont.Bold))
                status = ev.get('imaging_status', '').lower()
                if status in color_map:
                    status_item.setBackground(color_map[status])
                    # Set text color for contrast
                    if status in ['imaged', 'completed']:
                        status_item.setForeground(QColor('#ffffff'))
                    else:
                        status_item.setForeground(QColor('#000000'))
                table.setItem(i, 3, status_item)

                # Set Imaged Date
                date_item = QTableWidgetItem(ev.get('imaged_date', ''))
                table.setItem(i, 4, date_item)

        elif col == 3 and self.current_view == "Investigator":  # Legal column
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(['ID', 'Type', 'Provider', 'Status', 'Due Date'])
            table.setRowCount(len(case['legal_details']))
            for i, leg in enumerate(case['legal_details']):
                # Set ID
                id_item = QTableWidgetItem(str(leg['id']))
                id_item.setFont(QFont(id_item.font().family(), id_item.font().pointSize(), QFont.Bold))
                table.setItem(i, 0, id_item)
                
                # Set Type
                table.setItem(i, 1, QTableWidgetItem(leg.get('type', '')))
                
                # Set Provider
                table.setItem(i, 2, QTableWidgetItem(leg.get('provider', '')))

                # Status cell with color coding and overdue detection
                status = leg.get('status', '').lower()
                status_item = QTableWidgetItem(leg.get('status', '').capitalize())
                status_item.setFont(QFont(status_item.font().family(), status_item.font().pointSize(), QFont.Bold))

                # Check for overdue items
                is_overdue = False
                due_date = leg.get('due_date')
                if due_date and status not in ['completed', 'no_longer_needed', 'cancelled']:
                    try:
                        due_dt = datetime.fromisoformat(due_date)
                        if due_dt.date() < datetime.now(timezone.utc).date():
                            is_overdue = True
                            status_item = QTableWidgetItem("⚠ Overdue")
                            status_item.setFont(QFont(status_item.font().family(), status_item.font().pointSize(), QFont.Bold))
                            status_item.setBackground(QColor('#dc3545'))
                            status_item.setForeground(QColor('#ffffff'))
                        else:
                            if status in color_map:
                                status_item.setBackground(color_map[status])
                                if status in ['completed']:
                                    status_item.setForeground(QColor('#ffffff'))
                                else:
                                    status_item.setForeground(QColor('#000000'))
                    except Exception as e:
                        logger.debug(f"Could not apply status color: {e}")
                        if status in color_map:
                            status_item.setBackground(color_map[status])
                            if status in ['completed']:
                                status_item.setForeground(QColor('#ffffff'))
                            else:
                                status_item.setForeground(QColor('#000000'))
                else:
                    if status in color_map:
                        status_item.setBackground(color_map[status])
                        if status in ['completed']:
                            status_item.setForeground(QColor('#ffffff'))
                        else:
                            status_item.setForeground(QColor('#000000'))

                table.setItem(i, 3, status_item)
                table.setItem(i, 4, QTableWidgetItem(due_date or ''))

        table.resizeColumnsToContents()
        dialog.resize(700, 400)
        dialog.exec_()

    def on_dashboard_context_menu(self, pos):
        index = self.dashboard_table.indexAt(pos)
        if not index.isValid():
            return
        source_index = self.sort_proxy.mapToSource(index)
        row = source_index.row()
        case_number = self.cases_model.item(row, 0).text()

        menu = QMenu(self)
        edit_dates_act = QAction("Edit Dates...", self)
        edit_dates_act.triggered.connect(lambda: self.show_edit_dates_dialog(case_number, row))
        menu.addAction(edit_dates_act)
        
        menu.addSeparator()
        
        # Check if case is in closed status
        cases = self.db.get_cases_with_details()
        case = next((c for c in cases if c['id'] == case_number), None)
        if case and case.get('status') == 'Closed':
            archive_act = QAction("📦 Archive Case...", self)
            archive_act.triggered.connect(lambda: self.archive_case_from_dashboard(case_number))
            menu.addAction(archive_act)
        
        menu.exec_(self.dashboard_table.viewport().mapToGlobal(pos))

    def show_edit_dates_dialog(self, case_number, row):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Dates for {case_number}")
        layout = QFormLayout(dialog)

        trial_edit = QDateEdit()
        trial_edit.setDisplayFormat('yyyy-MM-dd')
        trial_edit.setCalendarPopup(True)
        sentencing_edit = QDateEdit()
        sentencing_edit.setDisplayFormat('yyyy-MM-dd')
        sentencing_edit.setCalendarPopup(True)

        # Pre-fill from model if present
        trial_item = self.cases_model.item(row, 5 if self.current_view == "Investigator" else 4)
        sentencing_item = self.cases_model.item(row, 6 if self.current_view == "Investigator" else 5)
        if trial_item and trial_item.text():
            try:
                d = datetime.fromisoformat(trial_item.text())
                trial_edit.setDate(QDate(d.year, d.month, d.day))
            except ValueError as e:
                logger.debug(f"Could not parse trial date: {e}")
        if sentencing_item and sentencing_item.text():
            try:
                d2 = datetime.fromisoformat(sentencing_item.text())
                sentencing_edit.setDate(QDate(d2.year, d2.month, d2.day))
            except ValueError as e:
                logger.debug(f"Could not parse sentencing date: {e}")

        layout.addRow("Trial Date (YYYY-MM-DD)", trial_edit)
        layout.addRow("Sentencing Date (YYYY-MM-DD)", sentencing_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            # Read ISO strings from QDateEdit
            trial_val = trial_edit.date().toString('yyyy-MM-dd') if trial_edit.date() else None
            sentencing_val = sentencing_edit.date().toString('yyyy-MM-dd') if sentencing_edit.date() else None
            # Update DB (local or server mode)
            try:
                self.db.update_case_dates(case_number, trial_date=trial_val, sentencing_date=sentencing_val)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update dates: {e}")
                return
            # Refresh dashboard to show changes
            self.refresh_dashboard()

    def show_court_dates_dialog(self):
        """Show a dialog with a table of case numbers and their court-related dates"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Court Dates Overview")
        layout = QVBoxLayout(dialog)

        table = QTableWidget()
        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        # Get cases with court-related dates
        cases = self.db.get_cases_with_details()
        court_dates = []

        for case in cases:
            case_id = case['id']

            # Trial date
            if case.get('trial_date'):
                court_dates.append((case_id, 'Trial', case.get('trial_date'), 'Trial scheduled'))

            # Sentencing date
            if case.get('sentencing_date'):
                court_dates.append((case_id, 'Sentencing', case.get('sentencing_date'), 'Sentencing scheduled'))

            # Court dates (hearings, depositions, etc.)
            court_dates_list = self.db.load_court_dates(case_id)
            for court_date in court_dates_list:
                date_type = court_date.get('date_type', 'court').replace('_', ' ').title()
                date = court_date.get('court_date')
                notes = court_date.get('notes', 'No description')
                if date:
                    court_dates.append((case_id, date_type, date, notes))

            # Legal due dates (only for Investigator view)
            if self.current_view == "Investigator":
                for leg in case['legal_details']:
                    if leg.get('due_date'):
                        court_dates.append((case_id, 'Legal Due', leg.get('due_date'), f"{leg.get('type', 'Unknown')} due"))

        # Sort by date
        court_dates.sort(key=lambda x: x[2] or '9999-99-99')

        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Case #', 'Date Type', 'Date', 'Description'])
        table.setRowCount(len(court_dates))

        for i, (case_id, date_type, date, description) in enumerate(court_dates):
            table.setItem(i, 0, QTableWidgetItem(case_id))
            table.setItem(i, 1, QTableWidgetItem(date_type))
            table.setItem(i, 2, QTableWidgetItem(date or ''))
            table.setItem(i, 3, QTableWidgetItem(description))

        table.resizeColumnsToContents()
        dialog.resize(800, 400)
        dialog.exec_()

    def show_calendar_events(self, date):
        """Show events for the selected date in a dialog"""
        selected_date = date.toString('yyyy-MM-dd')
        cases = self.db.get_cases_with_details()

        events = []

        # Check for case creation dates
        for case in cases:
            # Get case creation date from metadata
            case_data = self.db.load_report_with_dates(case['id'])
            if case_data and len(case_data) >= 6:
                creation_date = case_data[5]  # date_created is the 6th element
                if creation_date:
                    try:
                        # Extract date part from ISO string
                        creation_date_only = creation_date.split('T')[0] if 'T' in creation_date else creation_date
                        if creation_date_only == selected_date:
                            events.append({
                                'type': 'case_created',
                                'text': f"Case Created: Case {case['id']}",
                                'case_number': case['id'],
                                'details': f"Case {case['id']} was created on {creation_date_only}"
                            })
                    except Exception as e:
                        logger.debug(f"Could not parse case creation date: {e}")
                        pass
        for case in cases:
            if case.get('trial_date') == selected_date:
                events.append({
                    'type': 'trial',
                    'text': f"Trial: Case {case['id']}",
                    'case_number': case['id'],
                    'details': f"Trial scheduled for Case {case['id']} on {selected_date}"
                })

        # Check for sentencing dates
        for case in cases:
            if case.get('sentencing_date') == selected_date:
                events.append({
                    'type': 'sentencing',
                    'text': f"Sentencing: Case {case['id']}",
                    'case_number': case['id'],
                    'details': f"Sentencing scheduled for Case {case['id']} on {selected_date}"
                })

        # Check for court dates (hearings, depositions, etc.)
        for case in cases:
            court_dates = self.db.load_court_dates(case['id'])
            for court_date in court_dates:
                if court_date.get('court_date') == selected_date:
                    date_type = court_date.get('date_type', 'court')
                    display_type = date_type.replace('_', ' ').title()
                    # Use the fields stored by DatabaseManager: notes, event_time, location
                    notes = court_date.get('notes', 'No description available')
                    location = court_date.get('location', 'Not specified')
                    event_time = court_date.get('event_time', 'Not specified')
                    events.append({
                        'type': 'court_date',
                        'text': f"{display_type}: Case {case['id']}",
                        'case_number': case['id'],
                        'details': f"{display_type} for Case {case['id']} on {selected_date}\n\nDescription: {notes}\nLocation: {location}\nTime: {event_time}",
                        'raw': court_date
                    })

        # Check for legal process due dates (only for Investigator view)
        if self.current_view == "Investigator":
            for case in cases:
                for leg in case['legal_details']:
                    if leg.get('due_date') == selected_date:
                        events.append({
                            'type': 'legal_due',
                            'text': f"Legal Due: Case {case['id']} - {leg.get('type', 'Unknown')}",
                            'case_number': case['id'],
                            'details': f"Legal process '{leg.get('type', 'Unknown')}' due for Case {case['id']} on {selected_date}\n\nStatus: {leg.get('status', 'Unknown')}\nProvider: {leg.get('provider', 'Not specified')}"
                        })

        # Add case events (evidence status milestones, SLA events, etc.)
        for ev in self.db.get_case_events_on_date(selected_date):
            events.append({
                'type': ev.get('event_type', 'event'),
                'text': ev.get('title', 'Case Event'),
                'case_number': ev.get('case_number', ''),
                'details': ev.get('details', '')
            })

        if events:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Events on {selected_date}")
            layout = QVBoxLayout(dialog)

            # Create a scroll area for events
            scroll_area = QWidget()
            scroll_layout = QVBoxLayout(scroll_area)

            for event in events:
                # Create a group box for each event
                event_group = QWidget()
                event_layout = QHBoxLayout(event_group)

                # Event text
                event_label = QLabel(event['text'])
                event_label.setStyleSheet("font-weight: bold; color: #007bff;")
                event_layout.addWidget(event_label)

                # Details button
                details_btn = QPushButton("Details")
                details_btn.clicked.connect(lambda checked, e=event: self.show_event_details(e))
                event_layout.addWidget(details_btn)

                # Open case button (for case-related events)
                if event['type'] in ['case_created', 'trial', 'sentencing', 'court_date', 'legal_due']:
                    open_btn = QPushButton("Open Case")
                    open_btn.clicked.connect(lambda checked, cn=event['case_number']: self.open_case_by_number(cn))
                    event_layout.addWidget(open_btn)

                event_layout.addStretch()
                scroll_layout.addWidget(event_group)

            scroll_area.setLayout(scroll_layout)

            # Add scroll area to main layout
            from PyQt5.QtWidgets import QScrollArea
            scroll = QScrollArea()
            scroll.setWidget(scroll_area)
            scroll.setWidgetResizable(True)
            scroll.setMinimumHeight(200)
            layout.addWidget(scroll)

            buttons = QDialogButtonBox(QDialogButtonBox.Ok)
            buttons.accepted.connect(dialog.accept)
            layout.addWidget(buttons)

            dialog.resize(600, 400)
            dialog.exec_()
        else:
            QMessageBox.information(self, "No Events", f"No events scheduled for {selected_date}")

    def show_case_calendar_dialog(self):
        """Show a dialog with a calendar widget for viewing case events"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Case Calendar")
        layout = QVBoxLayout(dialog)

        # Use custom calendar widget with event highlighting
        calendar = EventCalendarWidget()
        calendar.setSelectedDate(QDate.currentDate())  # Default to today
        calendar.clicked.connect(self.show_calendar_events)

        # Add "Today" button for quick navigation
        today_button = QPushButton("Jump to Today")
        today_button.clicked.connect(lambda: calendar.setSelectedDate(QDate.currentDate()))
        layout.addWidget(today_button)

        # Collect event mapping: date -> list of event types
        event_map = {}
        cases = self.db.get_cases_with_details()

        def add_event_date(d, etype):
            if not d:
                return
            event_map.setdefault(d, set()).add(etype)

        for case in cases:
            # Case creation dates
            case_data = self.db.load_report_with_dates(case['id'])
            if case_data and len(case_data) >= 6:
                creation_date = case_data[5]
                if creation_date:
                    try:
                        creation_date_only = creation_date.split('T')[0] if 'T' in creation_date else creation_date
                        add_event_date(creation_date_only, 'case_created')
                    except Exception as e:
                        logger.debug(f"Could not add case creation event: {e}")

            # Trial dates
            if case.get('trial_date'):
                add_event_date(case.get('trial_date'), 'trial')

            # Sentencing dates
            if case.get('sentencing_date'):
                add_event_date(case.get('sentencing_date'), 'sentencing')

            # Court dates
            court_dates = self.db.load_court_dates(case['id'])
            for court_date in court_dates:
                cd = court_date.get('court_date')
                if cd:
                    add_event_date(cd, court_date.get('date_type', 'court'))

            # Legal due dates (only for Investigator view)
            if self.current_view == "Investigator":
                for leg in case['legal_details']:
                    if leg.get('due_date'):
                        add_event_date(leg.get('due_date'), 'legal_due')

        # Merge in case events (evidence milestones, SLA events, etc.)
        case_event_map = self.db.get_case_event_map()
        for date_key, types in case_event_map.items():
            if not date_key:
                continue
            if date_key not in event_map:
                event_map[date_key] = set()
            event_map[date_key].update(types)

        # Set event mapping on calendar
        calendar.set_event_dates(event_map)

        layout.addWidget(calendar)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.resize(400, 300)
        dialog.exec_()

    def on_dashboard_item_changed(self, item):
        # Persist in-place edits for trial/sentencing
        try:
            row = item.row()
            col = item.column()
            
            # Skip if this is a child row (marked with UserRole = True)
            if item.data(Qt.UserRole) is True:
                return
            
            # Column mapping: Case # (0), Assigned (1), Evidence (2), [Legal (3)], Report Status, Trial Date, Sentencing
            trial_col = 5 if self.current_view == "Investigator" else 4
            sentencing_col = 6 if self.current_view == "Investigator" else 5

            if col not in (trial_col, sentencing_col):
                return

            case_item = self.cases_model.item(row, 0)
            if not case_item:
                return
            
            case_number = case_item.text()
            if not case_number:
                return
                
            trial_item = self.cases_model.item(row, trial_col)
            sentencing_item = self.cases_model.item(row, sentencing_col)
            trial_val = trial_item.text().strip() if trial_item else None
            sentencing_val = sentencing_item.text().strip() if sentencing_item else None

            # Basic client-side validation: empty or ISO YYYY-MM-DD
            def valid_iso(s):
                if not s:
                    return True
                try:
                    from datetime import datetime
                    datetime.fromisoformat(s)
                    return True
                except ValueError:
                    return False

            if not valid_iso(trial_val) or not valid_iso(sentencing_val):
                QMessageBox.warning(self, "Invalid Date", "Please enter dates in ISO format: YYYY-MM-DD")
                return

            # Call DB updater
            self.db.update_case_dates(case_number, trial_date=trial_val or None, sentencing_date=sentencing_val or None)
        except Exception as e:
            logger.exception('Error persisting dashboard edit')

    def on_dashboard_sort_changed(self, column, order):
        """Persist dashboard sort preferences to config.json"""
        try:
            config['dashboard_sort'] = {'column': int(column), 'order': 'desc' if order == Qt.DescendingOrder else 'asc'}
            with open('config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logger.exception('Failed to save dashboard sort preference')

    def open_case_from_dashboard(self, index):
        source_index = self.sort_proxy.mapToSource(index)
        row = source_index.row()
        status_col = 4 if self.current_view == "Investigator" else 3
        status_item = self.cases_model.item(row, status_col)
        if status_item and status_item.data(Qt.UserRole) == 'closed':
            return  # Do not open tab for closed cases
        case_number = self.cases_model.item(row, 0).text()

        # Check if a tab for this case is already open
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, CaseTab) and tab.case_data.get('case_number') == case_number:
                self.tabs.setCurrentWidget(tab)
                return

        case_data = {"case_number": case_number}
        tab = CaseTab(case_data, self.db, current_user, self)
        self.tabs.addTab(tab, f"Case {case_number}")
        self.tabs.setCurrentWidget(tab)

    def new_case(self) -> None:
        """Create a new case dialog and add case tab"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Case")
        layout = QFormLayout(dialog)

        case_number_edit = QLineEdit()
        suspect_edit = QLineEdit()
        investigator_edit = QLineEdit()
        agency_edit = QLineEdit()
        
        trial_date_edit = QDateEdit()
        trial_date_edit.setDisplayFormat('yyyy-MM-dd')
        trial_date_edit.setCalendarPopup(True)
        trial_date_edit.setDate(QDate.currentDate())  # Default to today
        
        sentencing_date_edit = QDateEdit()
        sentencing_date_edit.setDisplayFormat('yyyy-MM-dd')
        sentencing_date_edit.setCalendarPopup(True)
        sentencing_date_edit.setDate(QDate.currentDate())  # Default to today

        layout.addRow("Case Number*", case_number_edit)
        layout.addRow("Suspect", suspect_edit)
        layout.addRow("Investigator", investigator_edit)
        layout.addRow("Agency", agency_edit)
        
        # Trial date with today button
        trial_layout = QHBoxLayout()
        trial_layout.addWidget(trial_date_edit)
        trial_today_btn = QPushButton("Today")
        trial_today_btn.clicked.connect(lambda: trial_date_edit.setDate(QDate.currentDate()))
        trial_layout.addWidget(trial_today_btn)
        layout.addRow("Trial Date (YYYY-MM-DD)", trial_layout)
        
        # Sentencing date with today button
        sentencing_layout = QHBoxLayout()
        sentencing_layout.addWidget(sentencing_date_edit)
        sentencing_today_btn = QPushButton("Today")
        sentencing_today_btn.clicked.connect(lambda: sentencing_date_edit.setDate(QDate.currentDate()))
        sentencing_layout.addWidget(sentencing_today_btn)
        layout.addRow("Sentencing Date (YYYY-MM-DD)", sentencing_layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            case_number = case_number_edit.text().strip()
            if not case_number:
                QMessageBox.warning(self, "Error", "Case number is required!")
                return

            case_data = {
                "case_number": case_number,
                "suspect": suspect_edit.text().strip(),
                "investigator": investigator_edit.text().strip(),
                "agency": agency_edit.text().strip(),
                "date_created": datetime.now().isoformat()
            }

            # Save to database (local in standalone)
            trial_date_val = trial_date_edit.date().toString('yyyy-MM-dd')
            sentencing_date_val = sentencing_date_edit.date().toString('yyyy-MM-dd')
            success = self.db.save_report(case_data, "<h1>New Report</h1><p>Start writing...</p>", [], assigned_to="anonymous", trial_date=trial_date_val, sentencing_date=sentencing_date_val)
            if success:
                QMessageBox.information(self, "Success", f"Case {case_number} created!")

                # Open new case tab
                tab = CaseTab(case_data, self.db, current_user, self)
                self.tabs.addTab(tab, f"Case {case_number}")
                self.tabs.setCurrentWidget(tab)

                # Refresh dashboard
                self.refresh_dashboard()

                # Refresh calendar if it's open (this would require tracking open dialogs)
                # For now, the calendar will be refreshed when reopened
            else:
                QMessageBox.critical(self, "Error", "Failed to create case.")

    def export_to_csv(self) -> None:
        """Export case data to CSV file"""
        # Extract data from the cases model
        data = []
        headers = ['Case #', 'Assigned To', 'Evidence']
        if self.current_view == "Investigator":
            headers.append('Legal')
        headers.append('Report Status')
        headers.append('Trial Date')
        headers.append('Sentencing')
        for row in range(self.cases_model.rowCount()):
            row_data = []
            for col in range(self.cases_model.columnCount()):
                item = self.cases_model.item(row, col)
                if item:
                    if col in [2, 3 if self.current_view == "Investigator" else 2]:  # Evidence and Legal/Status columns with statuses
                        statuses = item.data(Qt.UserRole) or []
                        status_labels = [label for label, _, _ in statuses]
                        row_data.append(', '.join(status_labels))
                    else:
                        row_data.append(item.text())
                else:
                    row_data.append('')
            data.append(row_data)

        # Create DataFrame
        df = pd.DataFrame(data, columns=headers)

        # File dialog for save path
        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "", "CSV Files (*.csv)")
        if file_path:
            df.to_csv(file_path, index=False)
            QMessageBox.information(self, "Export Successful", f"Data exported to {file_path}")

    def export_to_pdf(self) -> None:
        """Export case data to PDF file"""
        # Extract data from the cases model
        data = []
        headers = ['Case #', 'Assigned To', 'Evidence']
        if self.current_view == "Investigator":
            headers.append('Legal')
        headers.append('Report Status')
        headers.append('Trial Date')
        headers.append('Sentencing')
        for row in range(self.cases_model.rowCount()):
            row_data = []
            for col in range(self.cases_model.columnCount()):
                item = self.cases_model.item(row, col)
                if item:
                    if col in [2, 3 if self.current_view == "Investigator" else 2]:  # Evidence and Legal/Status columns with statuses
                        statuses = item.data(Qt.UserRole) or []
                        status_labels = [label for label, _, _ in statuses]
                        row_data.append(', '.join(status_labels))
                    else:
                        row_data.append(item.text())
                else:
                    row_data.append('')
            data.append(row_data)

        # Generate HTML table
        html = f"""
        <html>
        <head>
            <style>
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                h1 {{ color: #007bff; }}
            </style>
        </head>
        <body>
            <h1>Cases Dashboard Export</h1>
            <table>
                <tr>
                    {"".join(f"<th>{header}</th>" for header in headers)}
                </tr>
                {"".join(f"<tr>{''.join(f'<td>{cell}</td>' for cell in row)}</tr>" for row in data)}
            </table>
        </body>
        </html>
        """

        # File dialog for save path
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "", "PDF Files (*.pdf)")
        if file_path:
            try:
                from weasyprint import HTML
                from PyQt5.QtWidgets import QProgressDialog
                progress = QProgressDialog("Generating PDF export…", None, 0, 0, self)
                progress.setWindowTitle("Exporting")
                progress.setWindowModality(Qt.WindowModal)
                progress.setCancelButton(None)
                progress.show()
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    HTML(string=html).write_pdf(file_path)
                progress.close()
                QMessageBox.information(self, "Export Successful", f"Data exported to {file_path}")
            except ImportError:
                QMessageBox.warning(self, "PDF Export Disabled", "WeasyPrint is not available. PDF export features are disabled.")

    def export_to_excel(self) -> None:
        # Extract data from the cases model
        data = []
        headers = ['Case #', 'Assigned To', 'Evidence']
        if self.current_view == "Investigator":
            headers.append('Legal')
        headers.append('Report Status')
        for row in range(self.cases_model.rowCount()):
            row_data = []
            for col in range(self.cases_model.columnCount()):
                item = self.cases_model.item(row, col)
                if item:
                    if col in [2, 3 if self.current_view == "Investigator" else 2]:  # Evidence and Legal/Status columns with statuses
                        statuses = item.data(Qt.UserRole) or []
                        status_labels = [label for label, _, _ in statuses]
                        row_data.append(', '.join(status_labels))
                    else:
                        row_data.append(item.text())
                else:
                    row_data.append('')
            data.append(row_data)

        # Create DataFrame
        df = pd.DataFrame(data, columns=headers)

        # File dialog for save path
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "Export Successful", f"Data exported to {file_path}")

    def download_case_import_template(self) -> None:
        """Create a bulk import template for case import (Excel or CSV)."""
        template_columns = [
            "case_number",
            "suspect",
            "investigator",
            "agency",
            "assigned_to",
            "trial_date",
            "sentencing_date",
            "status",
            "report_html",
        ]
        sample_row = {
            "case_number": "C-2026-0001",
            "suspect": "John Doe",
            "investigator": "Det. Smith",
            "agency": "Metro PD",
            "assigned_to": "anonymous",
            "trial_date": "2026-06-01",
            "sentencing_date": "2026-09-15",
            "status": "draft",
            "report_html": "<h1>Imported Report</h1><p>Initial imported case report body.</p>",
        }
        template_df = pd.DataFrame([sample_row], columns=template_columns)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Case Import Template",
            "case_import_template.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in {".xlsx", ".csv"}:
                if "CSV" in selected_filter:
                    file_path += ".csv"
                    ext = ".csv"
                else:
                    file_path += ".xlsx"
                    ext = ".xlsx"

            if ext == ".csv":
                template_df.to_csv(file_path, index=False)
            else:
                instructions_df = pd.DataFrame(
                    [
                        {
                            "field": "case_number",
                            "required": "yes",
                            "example": "C-2026-0001",
                            "notes": "Unique case identifier. Must not already exist in database.",
                        },
                        {
                            "field": "trial_date / sentencing_date",
                            "required": "no",
                            "example": "2026-06-01",
                            "notes": "Use ISO date format YYYY-MM-DD.",
                        },
                        {
                            "field": "status",
                            "required": "no",
                            "example": "draft",
                            "notes": "Defaults to draft when omitted.",
                        },
                        {
                            "field": "report_html",
                            "required": "no",
                            "example": "<h1>Imported Report</h1><p>...</p>",
                            "notes": "Optional HTML report body. A default report body is used when omitted.",
                        },
                    ]
                )
                with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                    template_df.to_excel(writer, index=False, sheet_name="cases_import")
                    instructions_df.to_excel(writer, index=False, sheet_name="instructions")

            QMessageBox.information(
                self,
                "Template Created",
                f"Case import template created successfully:\n{file_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Template Creation Failed",
                f"Failed to create case import template:\n{exc}",
            )

    def _parse_optional_import_date(self, raw_value: Any, field_name: str, row_number: int) -> Optional[str]:
        """Parse date cell to ISO yyyy-mm-dd or raise ValueError with row context."""
        if pd.isna(raw_value):
            return None

        if isinstance(raw_value, datetime):
            return raw_value.date().isoformat()

        raw_text = str(raw_value).strip()
        if not raw_text:
            return None

        parsed = pd.to_datetime(raw_text, errors="coerce")
        if pd.isna(parsed):
            raise ValueError(
                f"Row {row_number}: Invalid {field_name} '{raw_text}'. Expected YYYY-MM-DD format."
            )
        return parsed.date().isoformat()

    def _show_case_import_preview(self, df: pd.DataFrame, display_columns: List[str]) -> bool:
        """Show a pre-import preview dialog and return True only when user confirms import."""
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Preview Bulk Case Import")
        preview_dialog.resize(980, 620)

        layout = QVBoxLayout(preview_dialog)
        summary = QLabel(
            f"File contains {len(df)} rows. Showing first {min(len(df), 20)} rows for preview.\n"
            "Click Import to continue or Cancel to stop."
        )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        table = QTableWidget(min(len(df), 20), len(display_columns))
        table.setHorizontalHeaderLabels(display_columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)

        preview_df = df.head(20)
        for row_idx, (_, row) in enumerate(preview_df.iterrows()):
            for col_idx, col_name in enumerate(display_columns):
                value = row.get(col_name, "")
                text = "" if pd.isna(value) else str(value)
                table.setItem(row_idx, col_idx, QTableWidgetItem(text))

        layout.addWidget(table)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        if ok_button:
            ok_button.setText("Import")
        buttons.accepted.connect(preview_dialog.accept)
        buttons.rejected.connect(preview_dialog.reject)
        layout.addWidget(buttons)

        return preview_dialog.exec_() == QDialog.Accepted

    def bulk_import_cases(self) -> None:
        """Bulk import multiple cases from Excel/CSV with row-level validation and error reporting."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Case Import File",
            "",
            "Import Files (*.xlsx *.csv)",
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext == ".xlsx":
                df = pd.read_excel(file_path, sheet_name=0)
            else:
                QMessageBox.warning(self, "Unsupported File", "Please choose a .xlsx or .csv file.")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Could not read import file:\n{exc}")
            return

        if df.empty:
            QMessageBox.warning(self, "Import Failed", "The selected import file is empty.")
            return

        normalized_columns = {
            re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_"): col
            for col in df.columns
        }
        case_col = normalized_columns.get("case_number") or normalized_columns.get("case")
        if not case_col:
            QMessageBox.critical(
                self,
                "Import Failed",
                "Required column 'case_number' not found. Use the provided template.",
            )
            return

        suspect_col = normalized_columns.get("suspect")
        investigator_col = normalized_columns.get("investigator")
        agency_col = normalized_columns.get("agency")
        assigned_to_col = normalized_columns.get("assigned_to")
        trial_date_col = normalized_columns.get("trial_date")
        sentencing_date_col = normalized_columns.get("sentencing_date")
        status_col = normalized_columns.get("status")
        report_html_col = normalized_columns.get("report_html")

        preview_columns = [
            col
            for col in [
                case_col,
                suspect_col,
                investigator_col,
                agency_col,
                assigned_to_col,
                trial_date_col,
                sentencing_date_col,
                status_col,
            ]
            if col
        ]
        if not self._show_case_import_preview(df, preview_columns):
            return

        existing_cases = {
            str(c.get("case_number", "")).strip()
            for c in self.db.load_all_cases(current_user["username"], current_user["role"])
            if c.get("case_number")
        }

        imported_count = 0
        failed_rows: List[Dict[str, Any]] = []
        seen_in_file = set()

        for idx, row in df.iterrows():
            row_number = idx + 2  # Header is row 1 in spreadsheet
            row_case_number = str(row.get(case_col, "")).strip()

            try:
                if not row_case_number:
                    raise ValueError(f"Row {row_number}: case_number is required.")

                if row_case_number in seen_in_file:
                    raise ValueError(f"Row {row_number}: Duplicate case_number in file: {row_case_number}")
                seen_in_file.add(row_case_number)

                if row_case_number in existing_cases:
                    raise ValueError(f"Row {row_number}: case_number already exists: {row_case_number}")

                trial_date_val = self._parse_optional_import_date(
                    row.get(trial_date_col) if trial_date_col else None,
                    "trial_date",
                    row_number,
                )
                sentencing_date_val = self._parse_optional_import_date(
                    row.get(sentencing_date_col) if sentencing_date_col else None,
                    "sentencing_date",
                    row_number,
                )

                assigned_to = (
                    str(row.get(assigned_to_col, "")).strip()
                    if assigned_to_col and not pd.isna(row.get(assigned_to_col))
                    else "anonymous"
                )
                status = (
                    str(row.get(status_col, "")).strip().lower()
                    if status_col and not pd.isna(row.get(status_col))
                    else "draft"
                )
                report_html = (
                    str(row.get(report_html_col, "")).strip()
                    if report_html_col and not pd.isna(row.get(report_html_col))
                    else ""
                )
                if not report_html:
                    report_html = "<h1>Imported Report</h1><p>Imported via bulk case import.</p>"

                case_data = {
                    "case_number": row_case_number,
                    "suspect": str(row.get(suspect_col, "")).strip() if suspect_col and not pd.isna(row.get(suspect_col)) else "",
                    "investigator": str(row.get(investigator_col, "")).strip() if investigator_col and not pd.isna(row.get(investigator_col)) else "",
                    "agency": str(row.get(agency_col, "")).strip() if agency_col and not pd.isna(row.get(agency_col)) else "",
                    "date_created": datetime.now().isoformat(),
                }

                success = self.db.save_report(
                    case_data,
                    report_html,
                    [],
                    assigned_to=assigned_to,
                    status=status,
                    trial_date=trial_date_val,
                    sentencing_date=sentencing_date_val,
                )
                if not success:
                    raise ValueError(f"Row {row_number}: Database rejected case '{row_case_number}'.")

                existing_cases.add(row_case_number)
                imported_count += 1
            except Exception as exc:
                failed_rows.append(
                    {
                        "row": row_number,
                        "case_number": row_case_number,
                        "error": str(exc),
                    }
                )

        if imported_count > 0:
            self.refresh_dashboard()

        summary = f"Import complete.\n\nImported: {imported_count}\nFailed: {len(failed_rows)}"
        if not failed_rows:
            QMessageBox.information(self, "Bulk Import Complete", summary)
            return

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Bulk Import Complete With Errors")
        message.setText(summary)
        message.setInformativeText("Would you like to save a CSV error report for correction?")
        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message.setDefaultButton(QMessageBox.Yes)
        if message.exec_() == QMessageBox.Yes:
            report_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Import Error Report",
                "case_import_errors.csv",
                "CSV Files (*.csv)",
            )
            if report_path:
                try:
                    pd.DataFrame(failed_rows).to_csv(report_path, index=False)
                    QMessageBox.information(
                        self,
                        "Error Report Saved",
                        f"Error report saved to:\n{report_path}",
                    )
                except Exception as exc:
                    QMessageBox.critical(self, "Save Failed", f"Could not save error report:\n{exc}")

    def download_evidence_import_template(self) -> None:
        """Create a bulk evidence import template for Excel or CSV."""
        template_columns = [
            "case_number",
            "evidence_item_number",
            "item_type",
            "physical_description",
            "digital_make",
            "digital_model",
            "digital_type",
            "digital_sn",
            "digital_storage_size",
            "password",
            "imaging_status",
            "imaged_date",
            "analyzed_date",
            "completed_date",
            "evidence_found",
        ]
        sample_rows = [
            {
                "case_number": "DEMO-HOMICIDE-001",
                "evidence_item_number": "H-001",
                "item_type": "Digital",
                "physical_description": "Black smartphone recovered at scene",
                "digital_make": "Apple",
                "digital_model": "iPhone 13",
                "digital_type": "Phone",
                "digital_sn": "IMEI-990000000111",
                "digital_storage_size": "128GB",
                "password": "",
                "imaging_status": "analyzed",
                "imaged_date": "2026-04-10",
                "analyzed_date": "2026-04-12",
                "completed_date": "",
                "evidence_found": "Deleted call logs and location artifacts",
            },
            {
                "case_number": "DEMO-ICAC-001",
                "evidence_item_number": "I-001",
                "item_type": "Digital",
                "physical_description": "Gaming laptop",
                "digital_make": "Dell",
                "digital_model": "XPS",
                "digital_type": "Laptop",
                "digital_sn": "DLXPS-31313",
                "digital_storage_size": "1TB",
                "password": "",
                "imaging_status": "imaged",
                "imaged_date": "2026-04-11",
                "analyzed_date": "",
                "completed_date": "",
                "evidence_found": "Pending artifact review",
            },
        ]
        template_df = pd.DataFrame(sample_rows, columns=template_columns)

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Evidence Import Template",
            "evidence_import_template.xlsx",
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in {".xlsx", ".csv"}:
                if "CSV" in selected_filter:
                    file_path += ".csv"
                    ext = ".csv"
                else:
                    file_path += ".xlsx"
                    ext = ".xlsx"

            if ext == ".csv":
                template_df.to_csv(file_path, index=False)
            else:
                instructions_df = pd.DataFrame(
                    [
                        {
                            "field": "case_number",
                            "required": "yes",
                            "example": "DEMO-HOMICIDE-001",
                            "notes": "Must exist as a case in the system before importing evidence.",
                        },
                        {
                            "field": "evidence_item_number",
                            "required": "yes",
                            "example": "H-001",
                            "notes": "Unique evidence label per case.",
                        },
                        {
                            "field": "item_type",
                            "required": "yes",
                            "example": "Digital",
                            "notes": "Free text category shown in tracker.",
                        },
                        {
                            "field": "imaging_status",
                            "required": "no",
                            "example": "not_imaged",
                            "notes": "Allowed: not_imaged, imaged, analyzed, other.",
                        },
                        {
                            "field": "imaged_date / analyzed_date / completed_date",
                            "required": "no",
                            "example": "2026-04-12",
                            "notes": "Use ISO format YYYY-MM-DD.",
                        },
                    ]
                )
                with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                    template_df.to_excel(writer, index=False, sheet_name="evidence_import")
                    instructions_df.to_excel(writer, index=False, sheet_name="instructions")

            QMessageBox.information(
                self,
                "Template Created",
                f"Evidence import template created successfully:\n{file_path}",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Template Creation Failed",
                f"Failed to create evidence import template:\n{exc}",
            )

    def bulk_import_evidence(self) -> None:
        """Bulk import evidence items from Excel/CSV with preview and row-level error reporting."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Evidence Import File",
            "",
            "Import Files (*.xlsx *.csv)",
        )
        if not file_path:
            return

        try:
            ext = os.path.splitext(file_path)[1].lower()
            if ext == ".csv":
                df = pd.read_csv(file_path)
            elif ext == ".xlsx":
                df = pd.read_excel(file_path, sheet_name=0)
            else:
                QMessageBox.warning(self, "Unsupported File", "Please choose a .xlsx or .csv file.")
                return
        except Exception as exc:
            QMessageBox.critical(self, "Import Failed", f"Could not read import file:\n{exc}")
            return

        if df.empty:
            QMessageBox.warning(self, "Import Failed", "The selected import file is empty.")
            return

        normalized_columns = {
            re.sub(r"[^a-z0-9]+", "_", str(col).strip().lower()).strip("_"): col
            for col in df.columns
        }
        case_col = normalized_columns.get("case_number") or normalized_columns.get("case")
        evidence_num_col = normalized_columns.get("evidence_item_number") or normalized_columns.get("evidence_number")
        item_type_col = normalized_columns.get("item_type")

        if not case_col or not evidence_num_col or not item_type_col:
            QMessageBox.critical(
                self,
                "Import Failed",
                "Required columns missing. Required: case_number, evidence_item_number, item_type.",
            )
            return

        physical_col = normalized_columns.get("physical_description")
        digital_make_col = normalized_columns.get("digital_make")
        digital_model_col = normalized_columns.get("digital_model")
        digital_type_col = normalized_columns.get("digital_type")
        digital_sn_col = normalized_columns.get("digital_sn")
        digital_storage_col = normalized_columns.get("digital_storage_size")
        password_col = normalized_columns.get("password")
        imaging_status_col = normalized_columns.get("imaging_status")
        imaged_date_col = normalized_columns.get("imaged_date")
        analyzed_date_col = normalized_columns.get("analyzed_date")
        completed_date_col = normalized_columns.get("completed_date")
        found_col = normalized_columns.get("evidence_found")

        preview_columns = [
            col
            for col in [
                case_col,
                evidence_num_col,
                item_type_col,
                physical_col,
                imaging_status_col,
                imaged_date_col,
                analyzed_date_col,
                completed_date_col,
            ]
            if col
        ]
        if not self._show_case_import_preview(df, preview_columns):
            return

        valid_statuses = {"not_imaged", "imaged", "analyzed", "other"}

        existing_cases = {
            str(c.get("case_number", "")).strip()
            for c in self.db.load_all_cases(current_user["username"], current_user["role"])
            if c.get("case_number")
        }

        imported_count = 0
        failed_rows: List[Dict[str, Any]] = []
        seen_in_file = set()

        def _lookup_evidence_id(case_number: str, evidence_item_number: str) -> Optional[int]:
            if not getattr(self.db, "conn", None):
                return None
            cursor = self.db.conn.execute(
                "SELECT id FROM evidence_items WHERE case_number = ? AND evidence_item_number = ? ORDER BY id DESC LIMIT 1",
                (case_number, evidence_item_number),
            )
            row = cursor.fetchone()
            return int(row["id"]) if row else None

        for idx, row in df.iterrows():
            row_number = idx + 2
            row_case_number = str(row.get(case_col, "")).strip()
            row_evidence_number = str(row.get(evidence_num_col, "")).strip()
            row_item_type = str(row.get(item_type_col, "")).strip()

            try:
                if not row_case_number:
                    raise ValueError(f"Row {row_number}: case_number is required.")
                if row_case_number not in existing_cases:
                    raise ValueError(f"Row {row_number}: case_number does not exist: {row_case_number}")
                if not row_evidence_number:
                    raise ValueError(f"Row {row_number}: evidence_item_number is required.")
                if not row_item_type:
                    raise ValueError(f"Row {row_number}: item_type is required.")

                composite_key = f"{row_case_number}::{row_evidence_number}"
                if composite_key in seen_in_file:
                    raise ValueError(
                        f"Row {row_number}: Duplicate evidence_item_number '{row_evidence_number}' for case '{row_case_number}' in file."
                    )
                seen_in_file.add(composite_key)

                imaging_status = (
                    str(row.get(imaging_status_col, "")).strip().lower()
                    if imaging_status_col and not pd.isna(row.get(imaging_status_col))
                    else "not_imaged"
                )
                if imaging_status not in valid_statuses:
                    raise ValueError(
                        f"Row {row_number}: Invalid imaging_status '{imaging_status}'. Allowed: {', '.join(sorted(valid_statuses))}"
                    )

                imaged_date_val = self._parse_optional_import_date(
                    row.get(imaged_date_col) if imaged_date_col else None,
                    "imaged_date",
                    row_number,
                )
                analyzed_date_val = self._parse_optional_import_date(
                    row.get(analyzed_date_col) if analyzed_date_col else None,
                    "analyzed_date",
                    row_number,
                )
                completed_date_val = self._parse_optional_import_date(
                    row.get(completed_date_col) if completed_date_col else None,
                    "completed_date",
                    row_number,
                )

                success = self.db.add_evidence(
                    row_case_number,
                    row_evidence_number,
                    row_item_type,
                    physical_description=(
                        str(row.get(physical_col, "")).strip()
                        if physical_col and not pd.isna(row.get(physical_col))
                        else None
                    ),
                    digital_make=(
                        str(row.get(digital_make_col, "")).strip()
                        if digital_make_col and not pd.isna(row.get(digital_make_col))
                        else None
                    ),
                    digital_model=(
                        str(row.get(digital_model_col, "")).strip()
                        if digital_model_col and not pd.isna(row.get(digital_model_col))
                        else None
                    ),
                    digital_type=(
                        str(row.get(digital_type_col, "")).strip()
                        if digital_type_col and not pd.isna(row.get(digital_type_col))
                        else None
                    ),
                    digital_sn=(
                        str(row.get(digital_sn_col, "")).strip()
                        if digital_sn_col and not pd.isna(row.get(digital_sn_col))
                        else None
                    ),
                    digital_storage_size=(
                        str(row.get(digital_storage_col, "")).strip()
                        if digital_storage_col and not pd.isna(row.get(digital_storage_col))
                        else None
                    ),
                    password=(
                        str(row.get(password_col, "")).strip()
                        if password_col and not pd.isna(row.get(password_col))
                        else None
                    ),
                )
                if not success:
                    raise ValueError(
                        f"Row {row_number}: Database rejected evidence '{row_evidence_number}' for case '{row_case_number}'."
                    )

                evidence_id = _lookup_evidence_id(row_case_number, row_evidence_number)
                if evidence_id is not None:
                    self.db.update_evidence_field(evidence_id, "imaging_status", imaging_status)
                    if imaged_date_val:
                        self.db.update_evidence_field(evidence_id, "imaged_date", imaged_date_val)
                    if analyzed_date_val:
                        self.db.update_evidence_field(evidence_id, "analyzed_date", analyzed_date_val)
                    if completed_date_val:
                        self.db.update_evidence_field(evidence_id, "completed_date", completed_date_val)
                    if found_col and not pd.isna(row.get(found_col)):
                        evidence_found_val = str(row.get(found_col)).strip()
                        if evidence_found_val:
                            self.db.update_evidence_field(evidence_id, "evidence_found", evidence_found_val)

                imported_count += 1
            except Exception as exc:
                failed_rows.append(
                    {
                        "row": row_number,
                        "case_number": row_case_number,
                        "evidence_item_number": row_evidence_number,
                        "error": str(exc),
                    }
                )

        if imported_count > 0:
            self.refresh_dashboard()
            # Refresh any open CaseTab whose case received new evidence
            imported_cases = {key.split("::")[0] for key in seen_in_file}
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, CaseTab) and tab.case_data.get('case_number') in imported_cases:
                    tab.load_evidence()
                    tab.update_dashboard_metrics()

        summary = f"Evidence import complete.\n\nImported: {imported_count}\nFailed: {len(failed_rows)}"
        if not failed_rows:
            QMessageBox.information(self, "Bulk Evidence Import Complete", summary)
            return

        message = QMessageBox(self)
        message.setIcon(QMessageBox.Warning)
        message.setWindowTitle("Bulk Evidence Import Complete With Errors")
        message.setText(summary)
        message.setInformativeText("Would you like to save a CSV error report for correction?")
        message.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message.setDefaultButton(QMessageBox.Yes)
        if message.exec_() == QMessageBox.Yes:
            report_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Evidence Import Error Report",
                "evidence_import_errors.csv",
                "CSV Files (*.csv)",
            )
            if report_path:
                try:
                    pd.DataFrame(failed_rows).to_csv(report_path, index=False)
                    QMessageBox.information(
                        self,
                        "Error Report Saved",
                        f"Error report saved to:\n{report_path}",
                    )
                except Exception as exc:
                    QMessageBox.critical(self, "Save Failed", f"Could not save error report:\n{exc}")

    def export_pdf_from_menu(self):
        # Get current case tab
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            current_tab.export_pdf(finalize=True)
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to export PDF.")

    def show_audit_log(self):
        # Get current case tab
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            current_tab.audit.show_log()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to view audit log.")

    def toggle_peer_review(self):
        # Get current case tab
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            current_tab.peer_review.toggle_mode()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to toggle peer review mode.")

    def show_glossary_assist(self):
        # Get current case tab
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            current_tab.glossary_assist.show()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to show glossary assist.")

    def show_bug_report(self):
        dialog = BugReportDialog(self, current_user, self.db)
        dialog.exec_()

    def show_feature_request(self):
        dialog = FeatureRequestDialog(self, current_user, self.db)
        dialog.exec_()

    def open_documentation(self, doc_file: str):
        """Open a documentation file in a built-in Markdown viewer dialog."""
        from PyQt5.QtWidgets import QTextBrowser, QDialogButtonBox
        import re

        app_dir = os.path.dirname(os.path.abspath(__file__))
        doc_path = os.path.join(app_dir, doc_file)

        if not os.path.exists(doc_path):
            QMessageBox.warning(
                self,
                "Documentation Not Found",
                f"The documentation file '{doc_file}' was not found.\n\nPath: {doc_path}"
            )
            logger.warning(f"Documentation file not found: {doc_path}")
            return

        try:
            with open(doc_path, "r", encoding="utf-8") as fh:
                md_text = fh.read()
        except OSError as e:
            QMessageBox.critical(self, "Error Opening Documentation",
                                 f"Could not read {doc_file}:\n{e}")
            logger.error(f"Failed to read documentation {doc_file}: {e}")
            return

        # Minimal Markdown → HTML conversion (headings, bold, inline code, lists)
        def md_to_html(text: str) -> str:
            lines = text.split("\n")
            html_lines = []
            in_code_block = False
            for line in lines:
                if line.startswith("```"):
                    if in_code_block:
                        html_lines.append("</pre>")
                        in_code_block = False
                    else:
                        html_lines.append("<pre style='background:#f4f4f4;padding:6px;'>")
                        in_code_block = True
                    continue
                if in_code_block:
                    html_lines.append(line.replace("&", "&amp;").replace("<", "&lt;"))
                    continue
                # ATX headings
                m = re.match(r'^(#{1,6})\s+(.*)', line)
                if m:
                    level = len(m.group(1))
                    html_lines.append(f"<h{level}>{m.group(2)}</h{level}>")
                    continue
                # Horizontal rule
                if re.match(r'^---+$', line.strip()):
                    html_lines.append("<hr/>")
                    continue
                # Unordered list
                m = re.match(r'^[-*]\s+(.*)', line)
                if m:
                    content = m.group(1)
                    content = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', content)
                    content = re.sub(r'`(.*?)`', r'<code>\1</code>', content)
                    html_lines.append(f"<li>{content}</li>")
                    continue
                # Inline formatting on plain lines
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                line = re.sub(r'`(.*?)`', r'<code style="background:#f0f0f0;padding:1px 3px;">\1</code>', line)
                if line.strip():
                    html_lines.append(f"<p style='margin:2px 0'>{line}</p>")
                else:
                    html_lines.append("<br/>")
            return "\n".join(html_lines)

        html_body = md_to_html(md_text)
        full_html = f"""<html><head><style>
            body {{ font-family: Segoe UI, Arial, sans-serif; font-size: 13px; padding: 12px; }}
            h1,h2,h3 {{ color: #2c5282; }} code {{ font-family: Consolas, monospace; }}
        </style></head><body>{html_body}</body></html>"""

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Documentation — {doc_file}")
        dlg.resize(820, 600)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(full_html)
        layout.addWidget(browser)
        close_btn = QDialogButtonBox(QDialogButtonBox.Close)
        close_btn.rejected.connect(dlg.reject)
        layout.addWidget(close_btn)
        dlg.exec_()
        logger.info(f"Opened documentation: {doc_file}")

    def show_archived_cases(self):
        """Show the archived cases dialog"""
        from archived_cases_dialog import ArchivedCasesDialog
        dialog = ArchivedCasesDialog(self.db, current_user["username"], self)
        dialog.exec_()
        # Refresh dashboard in case any cases were restored
        self.refresh_dashboard()

    def archive_case_from_dashboard(self, case_number: str):
        """Archive a case from the dashboard context menu"""
        from archive_case_dialog import ArchiveCaseDialog
        
        # Get case info for dialog
        cases = self.db.get_cases_with_details()
        case = next((c for c in cases if c['id'] == case_number), None)
        
        if not case:
            QMessageBox.warning(self, "Error", f"Could not find case {case_number}")
            return
        
        # Check if case is closed
        if case.get('status') != 'Closed':
            QMessageBox.warning(
                self,
                "Cannot Archive",
                f"Case {case_number} must be in 'Closed' status before archiving.\n\n"
                f"Current status: {case.get('status', 'Unknown')}"
            )
            return
        
        # Get suspect name for display
        try:
            suspect_name = self.db.get_case(case_number).get('suspect', 'Unknown')
        except Exception as e:
            logger.warning(f"Could not get suspect name for case {case_number}: {e}")
            suspect_name = 'Unknown'
        
        # Show archive dialog
        dialog = ArchiveCaseDialog(case_number, suspect_name, self)
        if dialog.exec_() == QDialog.Accepted:
            archive_data = dialog.get_archive_data()
            
            try:
                success = self.db.archive_case(
                    case_number,
                    current_user["username"],
                    archive_data['archive_reason'],
                    archive_data['archive_date']
                )
                
                if success:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Case {case_number} has been archived.\n\n"
                        f"You can view archived cases from View > Archived Cases."
                    )
                    # Refresh dashboard to remove archived case
                    self.refresh_dashboard()
                    
                    # Close the case tab if it's open
                    for i in range(self.tabs.count()):
                        tab = self.tabs.widget(i)
                        if isinstance(tab, CaseTab) and tab.case_data['case_number'] == case_number:
                            self.tabs.removeTab(i)
                            break
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to archive case {case_number}.\n\nCheck the logs for details."
                    )
            except Exception as e:
                logger.error(f"Failed to archive case: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while archiving the case:\n{str(e)}"
                )

    def on_dashboard_selection_changed(self, selected, deselected):
        # Handle selection changes in dashboard table
        # For now, just pass - can add logic later if needed
        pass

    def on_view_changed(self, view):
        self.current_view = view
        self.sort_proxy.current_view = view  # Update proxy's view
        # Clear chart cache when view changes to ensure charts are regenerated for the new view
        self.chart_cache.clear()
        # Update the existing dashboard in place to keep the user on the dashboard view
        if self.tabs.count() > 0 and self.tabs.tabText(0) == "Dashboard":
            # Update headers based on new view
            headers = ['Case #', 'Assigned To', 'Evidence']
            if self.current_view == "Investigator":
                headers.append('Legal')
            headers.append('Report Status')
            self.cases_model.setHorizontalHeaderLabels(headers)

            # Update delegate for legal column
            if self.current_view == "Investigator":
                self.dashboard_table.setItemDelegateForColumn(3, self.status_delegate)
            else:
                self.dashboard_table.setItemDelegateForColumn(3, None)  # Remove delegate if not investigator

            # Update status combo filter column
            self.status_combo.currentTextChanged.disconnect()
            self.status_combo.currentTextChanged.connect(lambda t: self.sort_proxy.setColumnFilter(4 if self.current_view == "Investigator" else 3, t if t != "All" else ""))

            # Refresh dashboard data
            self.refresh_dashboard()
        else:
            # If no dashboard, set it up (fallback)
            self.setup_dashboard()

        # Update all open case tabs
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, CaseTab):
                tab.update_view(view)

    def update_dashboard_charts(self, cases):
        """Update the dashboard charts with current case data using user preferences"""
        if not hasattr(self, 'charts_layout'):
            return

        # Load chart settings from config
        from auth import load_config
        cfg = load_config()
        chart_settings = cfg.get('dashboard_charts', {})
        self._adaptive_layout_config = {
            'enabled': chart_settings.get('adaptive_layout_enabled', True),
            'density': chart_settings.get('adaptive_density', 'balanced'),
            'breakpoints': chart_settings.get('adaptive_breakpoints', {'narrow': 1280, 'medium': 1700}),
        }

        # Invalidate cache and force refresh when renderer/config/theme signature changes.
        render_signature = json.dumps(
            {
                'render_version': CHART_RENDER_VERSION,
                'theme': getattr(self.theme_manager, 'current_theme', 'dark'),
                'chart_settings': chart_settings,
                'width_bucket': self._get_dashboard_width_bucket(),
            },
            sort_keys=True,
        )
        force_refresh = render_signature != getattr(self, '_last_chart_render_signature', '')
        if force_refresh:
            self._last_chart_render_signature = render_signature
            self.chart_cache.clear()
        
        # Check if we should refresh based on data changes or interval
        refresh_interval = chart_settings.get('auto_refresh_interval', 30)
        if refresh_interval > 0:
            self.chart_cache.refresh_interval = refresh_interval
            if not force_refresh and not self.chart_cache.should_refresh(data=cases):
                return  # Skip updating — data hasn't changed

        # Determine background color based on current theme
        theme_bg_colors = {
            'light': '#f8f9fa',
            'dark': '#2d3748',
            'high_contrast': '#000000'
        }
        current_theme = self.theme_manager.current_theme
        bgcolor = theme_bg_colors.get(current_theme, '#ffffff')

        # Clear existing charts from the layout
        while self.charts_layout.count() > 0:
            item = self.charts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get visible charts setting
        visible_charts = chart_settings.get('visible_charts', {})

        # Tune chart sizing by active dashboard composition.
        chart_count = 0
        if visible_charts.get('case_status', True):
            chart_count += 1
        if visible_charts.get('evidence_status', True):
            chart_count += 1
        if self.current_view == "Investigator" and visible_charts.get('legal_processes', True):
            chart_count += 1
        if self.current_view == "Investigator" and visible_charts.get('leads_status', True):
            chart_count += 1

        render_chart_settings = dict(chart_settings)
        render_chart_settings['_layout_chart_count'] = chart_count
        render_chart_settings['_layout_view'] = self.current_view
        render_chart_settings['_layout_width_bucket'] = self._get_dashboard_width_bucket()
        render_chart_settings['_layout_density'] = self._adaptive_layout_config.get('density', 'balanced')

        # Generate Case Status chart (if visible)
        if visible_charts.get('case_status', True):
            status_counts = {}
            for case in cases:
                status = case.get('status', 'draft').capitalize()
                status_counts[status] = status_counts.get(status, 0) + 1

            chart = self._generate_cached_chart_with_settings(
                status_counts, "Case Status", render_chart_settings, bgcolor, chart_count
            )
            if chart:
                self.charts_layout.addWidget(chart)

        # Generate Evidence Status chart (if visible)
        if visible_charts.get('evidence_status', True):
            evidence_counts = {'Imaged': 0, 'Not Imaged': 0, 'Other': 0}
            for case in cases:
                for ev in case['evidence_details']:
                    status = ev.get('imaging_status', 'not_imaged')
                    if status == 'imaged':
                        evidence_counts['Imaged'] += 1
                    elif status == 'not_imaged':
                        evidence_counts['Not Imaged'] += 1
                    else:
                        evidence_counts['Other'] += 1

            chart = self._generate_cached_chart_with_settings(
                evidence_counts, "Evidence Status", render_chart_settings, bgcolor, chart_count
            )
            if chart:
                self.charts_layout.addWidget(chart)

        # Generate Legal Processes chart (only for Investigator view, if visible)
        if self.current_view == "Investigator" and visible_charts.get('legal_processes', True):
            legal_counts = {'Completed': 0, 'Pending': 0, 'Overdue': 0, 'Other': 0}
            for case in cases:
                for leg in case['legal_details']:
                    status = leg.get('status', 'pending').lower()
                    if status in ['completed', 'no_longer_needed']:
                        legal_counts['Completed'] += 1
                    elif status == 'pending':
                        # Check if overdue
                        due_date = leg.get('due_date')
                        if due_date:
                            try:
                                due_dt = datetime.fromisoformat(due_date)
                                if due_dt.date() < datetime.now(timezone.utc).date():
                                    legal_counts['Overdue'] += 1
                                else:
                                    legal_counts['Pending'] += 1
                            except ValueError:
                                legal_counts['Pending'] += 1
                        else:
                            legal_counts['Pending'] += 1
                    else:
                        legal_counts['Other'] += 1

            chart = self._generate_cached_chart_with_settings(
                legal_counts, "Legal Processes", render_chart_settings, bgcolor, chart_count
            )
            if chart:
                self.charts_layout.addWidget(chart)

        # Generate Leads Status chart (only for Investigator view, if visible)
        if self.current_view == "Investigator" and visible_charts.get('leads_status', True):
            leads_counts = {'Completed': 0, 'Pending': 0}
            for case in cases:
                for lead in case['leads_details']:
                    if lead.get('completed', False):
                        leads_counts['Completed'] += 1
                    else:
                        leads_counts['Pending'] += 1

            chart = self._generate_cached_chart_with_settings(
                leads_counts, "Leads", render_chart_settings, bgcolor, chart_count
            )
            if chart:
                self.charts_layout.addWidget(chart)

        # Keep charts aligned to the left in original row layout.
        self.charts_layout.addStretch()

        # Force update to ensure proper layout
        self.tabs.widget(0).update()
    
    def _generate_cached_chart_with_settings(self, data: Dict[str, int], title: str,
                                            chart_settings: Dict[str, Any], bgcolor: str,
                                            layout_chart_count: int = 2) -> Optional[QLabel]:
        """Generate chart with caching and user settings"""
        cache_payload = {
            'data': data,
            'settings': chart_settings,
            'bgcolor': bgcolor,
            'render_version': CHART_RENDER_VERSION,
        }
        # Check cache if enabled
        if chart_settings.get('enable_caching', True):
            cached = self.chart_cache.get(cache_payload, title)
            if cached:
                return self._pixmap_to_label(cached)
        
        # Generate new chart
        pixmap = generate_chart(data, title, chart_settings, bgcolor)
        
        # Cache if enabled
        if chart_settings.get('enable_caching', True) and pixmap:
            self.chart_cache.set(cache_payload, title, pixmap)
        
        if pixmap:
            return self._pixmap_to_label(pixmap)
        return None
    
    def _pixmap_to_label(self, pixmap: QPixmap) -> QLabel:
        """Convert QPixmap to QLabel widget"""
        label = QLabel()
        label.setObjectName("dashboardChartCard")
        label.setPixmap(pixmap)
        # Preserve aspect ratio to avoid stretched-looking charts.
        label.setScaledContents(False)

        label.setMinimumSize(240, 180)
        label.setMaximumHeight(380)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        label.setAlignment(Qt.AlignCenter)
        label.setContentsMargins(8, 8, 8, 8)
        return label

    def _generate_cached_chart(self, data, title, bgcolor):
        """Generate a chart using cache and pyqtgraph for better performance"""
        # Try to get cached chart first
        cached_chart = self.chart_cache.get(data, title)
        if cached_chart:
            return cached_chart

        # Generate new chart
        if PYQTGRAPH_AVAILABLE:
            chart = self._generate_pyqtgraph_chart(data, title, bgcolor)
        else:
            # Fallback to matplotlib
            chart = self._generate_matplotlib_chart(data, title, bgcolor)

        # Cache the chart
        self.chart_cache.set(data, title, chart)
        return chart

    def _generate_pyqtgraph_chart(self, data, title, bgcolor):
        """Generate pie chart using matplotlib since pyqtgraph doesn't have native pie charts"""
        return self._generate_matplotlib_chart(data, title, bgcolor)

    def _generate_matplotlib_chart(self, data, title, bgcolor):
        """Fallback to matplotlib chart generation"""
        pixmap = generate_pie_chart(data, title, bgcolor=bgcolor)
        if pixmap:
            label = QLabel()
            label.setPixmap(pixmap)
            label.setFixedSize(pixmap.size())
            return label
        return None

    def show_status_color_dialog(self):
        dialog = StatusColorDialog(self.status_colors, self)
        if dialog.exec_() == QDialog.Accepted:
            self.status_colors = dialog.get_colors()
            # Update config
            config["status_colors"] = self.status_colors
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
            # Propagate new colors to all currently open CaseTab instances immediately
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, CaseTab):
                    tab.status_colors = self.status_colors
                    tab.load_evidence()
                    tab.load_legal()

    def add_evidence_item_from_menu(self):
        if current_user['role'] not in ['admin', 'supervisor']:
            QMessageBox.warning(self, "Access Denied", "Only supervisors and admins can add evidence items from the server side.")
            return
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add evidence item to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_evidence_item()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add evidence item.")

    def add_legal_process_from_menu(self):
        if current_user['role'] not in ['admin', 'supervisor']:
            QMessageBox.warning(self, "Access Denied", "Only supervisors and admins can add legal processes from the server side.")
            return
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add legal process to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_legal_process()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add legal process.")

    def open_legal_template_library(self):
        if self.current_view != "Investigator":
            QMessageBox.warning(self, "Investigator View Required", "Switch to Investigator view to manage legal template libraries.")
            return

        dialog = LegalTemplateLibraryDialog(self, self.db, current_user or {})
        dialog.exec_()

    def add_lead_from_menu(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add lead to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_lead()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add lead.")

    def add_court_date_from_menu(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add court date to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_court_date()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add court date.")

    def add_deposition_date_from_menu(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add deposition date to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_deposition_date()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add deposition date.")

    def add_prosecution_visit_from_menu(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add prosecution/defense visit to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_prosecution_visit()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add prosecution/defense visit.")

    def add_case_date_from_menu(self):
        current_tab = self.tabs.currentWidget()
        if isinstance(current_tab, CaseTab):
            case_number = current_tab.case_data['case_number']
            reply = QMessageBox.question(self, "Confirm Case", f"Add case date to Case {case_number}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                current_tab.add_case_date()
        else:
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to add case date.")

    # ================================================================
    # Legal Workflow Menu Handlers
    # ================================================================
    
    def mark_investigator_approved_from_menu(self):
        """Show dialog to mark investigator approval"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        # Get list of active legal processes for this case
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.\n\nCreate one first from Tracker > Add Legal Process")
            return
        
        # If there's only one process, use it directly
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
        else:
            # Show selection dialog for multiple processes
            process_id = self._select_legal_process(legal_processes, "Select Process for Investigator Approval")
            if not process_id:
                return
        
        # Show approval dialog
        dialog = InvestigatorApprovalDialog(str(process_id), self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                mark_investigator_approved(
                    self.db, process_id, data['approval_date'], data['investigator_name']
                )
                QMessageBox.information(self, "Success", f"Investigator approval recorded.\n\nCalendar event created.")
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to mark investigator approval: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record approval:\n{str(e)}")
    
    def mark_state_attorney_approved_from_menu(self):
        """Show dialog to mark state attorney approval"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.")
            return
        
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
        else:
            process_id = self._select_legal_process(legal_processes, "Select Process for State Attorney Approval")
            if not process_id:
                return
        
        dialog = StateAttorneyApprovalDialog(str(process_id), self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                mark_state_attorney_approved(
                    self.db, process_id, data['approval_date'], data['attorney_name']
                )
                QMessageBox.information(self, "Success", f"State attorney approval recorded.\n\nCalendar event created.")
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to mark state attorney approval: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record approval:\n{str(e)}")
    
    def mark_judicial_approval_from_menu(self):
        """Show dialog to mark judicial approval"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.")
            return
        
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
        else:
            process_id = self._select_legal_process(legal_processes, "Select Process for Judicial Approval")
            if not process_id:
                return
        
        dialog = JudicialApprovalDialog(str(process_id), self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                mark_judicial_approval(
                    self.db, process_id, data['approval_date'], data['court_name'], data['judge_name']
                )
                QMessageBox.information(self, "Success", f"Judicial approval recorded.\n\nCalendar event created.")
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to mark judicial approval: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record approval:\n{str(e)}")
    
    def mark_sent_to_provider_from_menu(self):
        """Show dialog to mark transmission to provider (SLA clock starts)"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.")
            return
        
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
            process_info = legal_processes[0]
        else:
            process_id = self._select_legal_process(legal_processes, "Select Process to Send to Provider")
            if not process_id:
                return
            process_info = next((p for p in legal_processes if p['id'] == process_id), None)
        
        provider_name = process_info.get('provider', '') if process_info else ''
        dialog = SendToProviderDialog(str(process_id), provider_name, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                mark_sent_to_provider(
                    self.db, process_id, data['sent_date'], data['transmission_method'], 
                    data['expected_response_days']
                )
                QMessageBox.information(
                    self, "Success", 
                    f"Transmission recorded. ⏱️ SLA CLOCK STARTED\n\n"
                    f"Due Date: {(data['sent_date'] + __import__('datetime').timedelta(days=data['expected_response_days'])).strftime('%B %d, %Y')}\n\n"
                    f"Calendar events created."
                )
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to mark sent to provider: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record transmission:\n{str(e)}")
    
    def mark_provider_acknowledged_from_menu(self):
        """Show dialog to mark provider acknowledgment of receipt"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.")
            return
        
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
            process_info = legal_processes[0]
        else:
            process_id = self._select_legal_process(legal_processes, "Select Process to Acknowledge")
            if not process_id:
                return
            process_info = next((p for p in legal_processes if p['id'] == process_id), None)
        
        provider_name = process_info.get('provider', '') if process_info else ''
        dialog = ProviderAcknowledgedDialog(str(process_id), provider_name, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                mark_provider_acknowledged(self.db, process_id, data['acknowledged_date'])
                QMessageBox.information(self, "Success", f"Provider acknowledgment recorded.\n\nCalendar event created.")
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to mark provider acknowledged: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record acknowledgment:\n{str(e)}")
    
    def mark_sla_breach_from_menu(self):
        """Show dialog to record SLA breach"""
        current_tab = self.tabs.currentWidget()
        if not isinstance(current_tab, CaseTab):
            QMessageBox.warning(self, "No Case Selected", "Please select a case tab to manage legal workflow.")
            return
        
        case_number = current_tab.case_data['case_number']
        
        legal_processes = self.db.load_legal_processes(case_number)
        if not legal_processes:
            QMessageBox.information(self, "No Processes", f"No legal processes found for Case {case_number}.")
            return
        
        if len(legal_processes) == 1:
            process_id = legal_processes[0]['id']
            process_info = legal_processes[0]
        else:
            # Filter for processes with SLA due dates
            processes_with_sla = [p for p in legal_processes if p.get('sla_due_date')]
            if not processes_with_sla:
                QMessageBox.information(self, "No SLA Processes", f"No legal processes with SLA due dates found for Case {case_number}.")
                return
            process_id = self._select_legal_process(processes_with_sla, "Select Process with SLA Breach")
            if not process_id:
                return
            process_info = next((p for p in legal_processes if p['id'] == process_id), None)
        
        sla_due_date = process_info.get('sla_due_date') if process_info else None
        if not sla_due_date:
            QMessageBox.warning(self, "No SLA Due Date", f"Selected process does not have an SLA due date.")
            return
        
        try:
            from datetime import datetime
            sla_due_dt = datetime.fromisoformat(sla_due_date)
        except Exception as e:
            logger.error(f"Invalid SLA due date: {sla_due_date}")
            QMessageBox.warning(self, "Invalid Date", f"Could not parse SLA due date: {sla_due_date}")
            return
        
        provider_name = process_info.get('provider', '') if process_info else ''
        dialog = MarkSLABreachDialog(str(process_id), sla_due_dt, provider_name, self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                calculate_legal_sla_breach(self.db, process_id, data['received_date'])
                days_late = data['days_late']
                message = f"SLA Breach recorded!\n\nDays Late: {days_late}\n\n"
                message += f"Critical notification and red calendar event created.\n"
                if data['breach_reason']:
                    message += f"\nReason documented in database."
                QMessageBox.critical(self, "SLA Breach Recorded", message)
                current_tab.refresh_legal_processes()
                self.refresh_dashboard()
            except Exception as e:
                logger.error(f"Failed to record SLA breach: {e}")
                QMessageBox.critical(self, "Error", f"Failed to record breach:\n{str(e)}")
    
    def _select_legal_process(self, processes, title="Select Legal Process"):
        """Show a dialog to select from multiple legal processes"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        
        label = QLabel("Select a legal process:")
        layout.addWidget(label)
        
        combo = QComboBox()
        for proc in processes:
            display_text = f"ID {proc['id']}: {proc.get('type', 'Unknown')} - {proc.get('provider', 'N/A')}"
            combo.addItem(display_text, proc['id'])
        layout.addWidget(combo)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            return combo.currentData()
        return None

    def open_case_from_calendar(self, item):
        """Open a case from the calendar events list"""
        if not item:
            return
        text = item.text()
        if text.startswith("Case Created: Case "):
            case_number = text.split("Case ")[-1]
            # Check if a tab for this case is already open
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if isinstance(tab, CaseTab) and tab.case_data.get('case_number') == case_number:
                    self.tabs.setCurrentWidget(tab)
                    return

            case_data = {"case_number": case_number}
            tab = CaseTab(case_data, self.db, current_user, self)
            self.tabs.addTab(tab, f"Case {case_number}")
            self.tabs.setCurrentWidget(tab)

    def show_event_details(self, event):
        """Show detailed information for a specific event"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Event Details - {event['text']}")
        layout = QVBoxLayout(dialog)

        details_text = QTextEdit()
        details_text.setPlainText(event['details'])
        details_text.setReadOnly(True)
        layout.addWidget(details_text)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)

        dialog.resize(500, 300)
        dialog.exec_()

    def open_case_by_number(self, case_number):
        """Open a case tab by case number"""
        # Check if a tab for this case is already open
        for i in range(self.tabs.count()):
            tab = self.tabs.widget(i)
            if isinstance(tab, CaseTab) and tab.case_data.get('case_number') == case_number:
                self.tabs.setCurrentWidget(tab)
                return

        case_data = {"case_number": case_number}
        tab = CaseTab(case_data, self.db, current_user, self)
        self.tabs.addTab(tab, f"Case {case_number}")
        self.tabs.setCurrentWidget(tab)

    def closeEvent(self, event):
        if self._heartbeat_timer is not None:
            self._heartbeat_timer.stop()
        if self._discovery_probe_server is not None:
            try:
                self._discovery_probe_server.shutdown()
                self._discovery_probe_server.server_close()
            except Exception:
                pass
        self.db.close()
        super().closeEvent(event)

# ------------------------------------------------------------------
# Splash Screen
# ------------------------------------------------------------------

def show_splash_screen(app: QApplication):
    splash = QDialog()
    splash.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
    splash.setWindowFlag(Qt.WindowType.Dialog, True)
    splash.setModal(False)
    splash.setFixedSize(420, 420)

    layout = QVBoxLayout(splash)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(10)

    logo_label = QLabel()
    logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # Use resource_path to find logo in both dev and compiled modes
    logo_path = resource_path(os.path.join("assets", "FuDog Labs.png"))
    logo_pixmap = QPixmap(logo_path)
    if not logo_pixmap.isNull():
        # Constrain both width AND height so a tall logo never overflows the dialog
        logo_label.setPixmap(
            logo_pixmap.scaled(
                340, 300,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
    else:
        # Fallback to text if logo not found
        logo_label.setText("FuDog Labs")
        logo_label.setFont(QFont("Arial", 16, QFont.Bold))
        logger.warning(f"Logo not found at: {logo_path}")

    status_label = QLabel("Starting...")
    status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(5)
    progress.setTextVisible(True)

    layout.addWidget(logo_label)
    layout.addWidget(status_label)
    layout.addWidget(progress)

    splash.show()
    app.processEvents()
    return splash, progress, status_label

# ------------------------------------------------------------------
# Application Launch - QApplication created FIRST
# ------------------------------------------------------------------

if __name__ == "__main__":
    # =========================================================================
    # COMMAND-LINE ARGUMENT PROCESSING
    # =========================================================================
    safe_mode = '--safe-mode' in sys.argv
    run_diagnostics = '--diagnostics' in sys.argv
    
    # Run diagnostics if requested
    if run_diagnostics:
        if SystemDiagnostics:
            print("\n=== FORENSIC REPORT SUITE - SYSTEM DIAGNOSTICS ===\n")
            diag = SystemDiagnostics()
            diag.gather_all()
            diag.log_diagnostics()
            output_file = diag.save_to_file()
            if output_file:
                print(f"\n✓ Diagnostics saved to: {output_file}\n")
        else:
            print("ERROR: diagnostics module not available")
        sys.exit(0)
    
    # Check dependencies
    if validate_dependencies:
        valid, msg = validate_dependencies()
        if not valid:
            print(f"ERROR: {msg}")
            sys.exit(1)
    
    # =========================================================================
    # CRITICAL: Enable High DPI scaling BEFORE QApplication is created
    # This fixes issues when switching between displays with different DPI
    # (e.g., laptop screen vs external monitor)
    # =========================================================================
    
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    
    # Use high DPI pixmaps (sharper icons and images on high DPI displays)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set high DPI scale factor rounding policy (Qt 5.14+)
    # This ensures consistent scaling across different DPI displays
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        # Qt version < 5.14, attribute doesn't exist - safe to ignore
        pass
    
    app = QApplication(sys.argv)
    app.setApplicationName("FuDog Labs Forensic Report Suite")
    app.setOrganizationName("FuDog Labs")
    
    # Set minimum font size to prevent unreadable text on any display
    min_font = QFont()
    min_font.setPointSize(9)  # Minimum readable font size
    app.setFont(min_font)

    splash, progress, status_label = show_splash_screen(app)

    def update_splash(value: int, text: str):
        progress.setValue(value)
        status_label.setText(text)
        app.processEvents()

    # Initialize logging
    update_splash(10, "Initializing logging...")
    logger = setup_logging("forensic_app")
    
    # Log safe mode status if enabled
    if safe_mode:
        logger.warning("SAFE MODE ENABLED - Application running in degraded mode")
    
    # Log performance baseline
    update_splash(15, "Collecting system information...")
    if log_performance_baseline:
        try:
            baseline = log_performance_baseline(logger)
        except Exception as e:
            logger.debug(f"Could not log performance baseline: {e}")
    
    # Initialize diagnostics (early for troubleshooting)
    if SystemDiagnostics:
        try:
            diag = SystemDiagnostics()
            diag.gather_all()
            logger.debug(f"System diagnostics: {json.dumps(diag.to_dict(), indent=2, default=str)}")
        except Exception as e:
            logger.debug(f"Could not gather system diagnostics: {e}")

    update_splash(25, "Loading configuration...")
    config = load_config()

    update_splash(40, "Authenticating user...")
    if config.get("use_ad") or config.get("server_url"):
        current_user = authenticate()
    else:
        current_user = {"username": "anonymous", "role": "admin"}

    if not current_user:
        logger.warning("Authentication failed or cancelled.")
        splash.close()
        sys.exit(1)

    update_splash(75, "Starting application...")
    
    # Pass safe_mode flag to MainWindow
    window = MainWindow(safe_mode=safe_mode)
    if safe_mode:
        window.setWindowTitle(window.windowTitle() + " [SAFE MODE]")
    window.show()

    update_splash(100, "Ready")
    splash.close()
    
    logger.info("Application started successfully")

    sys.exit(app.exec_())
