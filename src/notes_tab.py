# notes_tab.py
import os
import shutil
import json
import hashlib
import logging
from datetime import datetime
try:
    import speech_recognition as sr
except ImportError:
    sr = None

# Initialize logger
logger = logging.getLogger(__name__)
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None
try:
    from dateutil import parser as dateutil_parser
    from dateutil import tz as dateutil_tz
except ImportError:
    dateutil_parser = None
    dateutil_tz = None
try:
    import pandas as pd
except ImportError:
    pd = None
try:
    from geopy.geocoders import Nominatim
    from geopy.extra.rate_limiter import RateLimiter
except ImportError:
    Nominatim = None
    RateLimiter = None
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QToolBar, QAction, QTreeWidget, QTreeWidgetItem,
    QTableWidget, QTableWidgetItem, QLineEdit, QListWidget, QListWidgetItem, QScrollArea,
    QFileDialog, QMessageBox, QInputDialog, QCheckBox, QMainWindow, QComboBox, QColorDialog, QFontComboBox, QSpinBox,
    QDialog, QFormLayout, QDialogButtonBox, QSplitter, QFrame, QToolButton, QMenu, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QTextCharFormat, QTextListFormat, QFont, QKeySequence, QColor, QTextBlockFormat, QTextCursor
from PyQt5.QtCore import Qt
try:
    import networkx as nx
except ImportError:
    nx = None
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None
from templates import TemplateManager
from security import compute_sha256
from base_editor import BaseEditor
from word_processor import WordProcessor

class NotesTab(BaseEditor):
    def __init__(self, case_data, db_manager, audit_logger, parent=None):
        super().__init__(case_data, db_manager, audit_logger, parent)
        self.case_dir = os.path.join("cases", case_data["case_number"], "notes")
        os.makedirs(self.case_dir, exist_ok=True)

        # Data structures
        self.notes = {}  # note_id -> {'content': str, 'timestamp': str, 'hash': str, 'tags': list, 'links': list}
        self.entities = []  # {'name': str, 'type': str, 'notes_linked': list}
        self.tasks = []  # {'task': str, 'status': str, 'due': str}
        self.attachments = []  # paths

        # Geocoder setup (offline with rate limit)
        if Nominatim and RateLimiter:
            self.geolocator = Nominatim(user_agent="forensic_notes_app")
            self.reverse = RateLimiter(self.geolocator.reverse, min_delay_seconds=1.0)  # Nominatim limit
        else:
            self.geolocator = None
            self.reverse = None

        # Initialize advanced word processor
        self.word_processor = WordProcessor(self.note_editor)

        # Load saved data
        self.load_notes()

    def setup_ui(self):
        """Override parent's setup_ui with Office-style layout"""
        # Initialize parent class attributes that might be referenced
        self.toolbar = None
        self.splitter = None
        self.editor_frame = None

        # Create main layout (no margins — toolbar and canvas fill edge-to-edge)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Office-style toolbar from base class ─────────────────────────
        # editor must be set before create_toolbar() signals can fire
        self.note_editor = QTextEdit()
        self.note_editor.setObjectName("documentPage")
        self.note_editor.setAcceptRichText(True)
        self.note_editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.note_editor.customContextMenuRequested.connect(self.on_note_context_menu)
        self.note_editor.textChanged.connect(self.auto_timestamp_note)
        self.note_editor.document().setDocumentMargin(48)
        self.note_editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Set reference BEFORE create_toolbar() so signal guards work
        self.editor = self.note_editor

        self.toolbar = self.create_toolbar()
        layout.addWidget(self.toolbar)

        # ── Splitter: Notes tree (left) │ Document canvas (right) ────────
        splitter = QSplitter(Qt.Horizontal)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Notes tree panel
        self.notes_tree = QTreeWidget()
        self.notes_tree.setColumnCount(1)
        self.notes_tree.setHeaderLabel("Note History")
        self.notes_tree.itemClicked.connect(self.load_note)
        self.notes_tree.setMinimumWidth(160)
        self.notes_tree.setMaximumWidth(280)
        self.notes_tree.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        splitter.addWidget(self.notes_tree)

        # Right side: gray canvas with the white document page
        canvas = QScrollArea()
        canvas.setObjectName("documentCanvas")
        canvas.setWidgetResizable(True)

        wrapper = QWidget()
        wrapper.setObjectName("documentWrapper")
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(16, 16, 16, 16)
        wrapper_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        wrapper_layout.addWidget(self.note_editor)

        canvas.setWidget(wrapper)
        splitter.addWidget(canvas)
        splitter.setSizes([200, 800])

        layout.addWidget(splitter, stretch=1)

        # ── Compact timestamp insert bar ─────────────────────────────────
        tb_layout = QHBoxLayout()
        tb_layout.setContentsMargins(6, 2, 6, 2)

        self.insert_ts_btn = QToolButton()
        self.insert_ts_btn.setText('\u23f0 Timestamp \u25be')
        self.insert_ts_btn.setToolTip('Insert timestamp at cursor')

        self.insert_ts_local_act = QAction('Insert Date/Time (Local)', self)
        self.insert_ts_local_act.setShortcut(QKeySequence('Ctrl+Shift+T'))
        self.insert_ts_local_act.triggered.connect(lambda: self.insert_timestamp_at_cursor(fmt='local'))

        self.insert_ts_iso_act = QAction('Insert ISO Date/Time (with TZ)', self)
        self.insert_ts_iso_act.setShortcut(QKeySequence('Ctrl+Alt+Shift+T'))
        self.insert_ts_iso_act.triggered.connect(lambda: self.insert_timestamp_at_cursor(fmt='iso'))

        self.convert_ts_act = QAction('Convert Selected Timestamp', self)
        self.convert_ts_act.setShortcut(QKeySequence('Ctrl+Shift+C'))
        self.convert_ts_act.triggered.connect(self.convert_selected_timestamp)

        ts_menu = QMenu(self)
        ts_menu.addAction(self.insert_ts_local_act)
        ts_menu.addAction(self.insert_ts_iso_act)
        ts_menu.addSeparator()
        ts_menu.addAction(self.convert_ts_act)
        self.insert_ts_btn.setMenu(ts_menu)
        self.insert_ts_btn.setPopupMode(QToolButton.InstantPopup)
        self.insert_ts_btn.clicked.connect(lambda: self.insert_timestamp_at_cursor(fmt='local'))
        tb_layout.addWidget(self.insert_ts_btn)
        tb_layout.addStretch()
        layout.addLayout(tb_layout)

        # ── Status bar ────────────────────────────────────────────────────
        from base_editor import StatusBar
        self.status_bar = StatusBar()
        self.status_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.status_bar)

    def add_note(self):
        name, ok = QInputDialog.getText(self, "New Note", "Note Name:")
        if ok:
            note_id = str(len(self.notes) + 1)
            self.notes[note_id] = {
                'content': '',
                'timestamp': datetime.now().isoformat(),
                'hash': '',
                'tags': [],
                'links': []
            }
            item = QTreeWidgetItem(self.notes_tree, [name])
            item.setData(0, Qt.UserRole, note_id)
            self.save_notes()
            self.audit.log("NOTE_ADDED", {"note_id": note_id, "name": name})

    def load_note(self, item):
        note_id = item.data(0, Qt.UserRole)
        if note_id:
            note = self.notes[note_id]
            self.note_editor.setHtml(note['content'])

    def auto_timestamp_note(self):
        if self.note_editor.hasFocus():
            cursor = self.note_editor.textCursor()
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole) if self.notes_tree.currentItem() else None
            if not note_id:
                # Create a new note if none selected and editor has content
                content = self.note_editor.toHtml()
                if content.strip():  # Only create if there's actual content
                    note_id = str(len(self.notes) + 1)
                    name = f"Untitled Note {note_id}"
                    self.notes[note_id] = {
                        'name': name,
                        'content': content,
                        'timestamp': datetime.now().isoformat(),
                        'hash': '',
                        'tags': [],
                        'links': []
                    }
                    item = QTreeWidgetItem(self.notes_tree, [name])
                    item.setData(0, Qt.UserRole, note_id)
                    self.notes_tree.setCurrentItem(item)
                    self.audit.log("NOTE_AUTO_CREATED", {"note_id": note_id, "name": name})
            if note_id:
                content = self.note_editor.toHtml()
                note = self.notes[note_id]
                note['content'] = content
                note['timestamp'] = datetime.now().isoformat()
                note['hash'] = hashlib.sha256(content.encode()).hexdigest()
                self.save_notes()
                self.audit.log("NOTE_EDITED", {"note_id": note_id, "hash": note['hash']})

    def add_tag(self):
        tag, ok = QInputDialog.getText(self, "Add Tag", "Tag:")
        if ok:
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole)
            if note_id:
                self.notes[note_id]['tags'].append(tag)
                self.save_notes()
                self.audit.log("TAG_ADDED", {"note_id": note_id, "tag": tag})

    def on_note_context_menu(self, pos):
        """Show a context menu for the note editor. Features enabled from config.json."""
        try:
            from auth import load_config
            cfg = load_config()
        except Exception as e:
            logger.warning(f"Could not load config for context menu: {e}")
            cfg = {}

        notes_cfg = cfg.get('context_menu', {}).get('notes', {}) if cfg else {}

        menu = self.note_editor.createStandardContextMenu()
        menu.addSeparator()

        # Insert timestamp actions
        if notes_cfg.get('insert_timestamp', True):
            menu.addAction(self.insert_ts_local_act)
            menu.addAction(self.insert_ts_iso_act)

        # Convert timestamp
        if notes_cfg.get('convert_timestamp', True):
            menu.addAction(self.convert_ts_act)

        # Insert template
        if notes_cfg.get('insert_template', True):
            insert_template_act = QAction('Insert Template', self)
            insert_template_act.triggered.connect(self.insert_template_from_context)
            menu.addAction(insert_template_act)

        # Create Task
        if notes_cfg.get('create_task', True):
            create_task_act = QAction('Create Task from Selection', self)
            create_task_act.triggered.connect(self.create_task_from_selection)
            menu.addAction(create_task_act)

        # Tag / Label
        if notes_cfg.get('tag', True):
            tag_act = QAction('Tag / Label Selection', self)
            tag_act.triggered.connect(self.tag_selection)
            menu.addAction(tag_act)

        # Redact
        if notes_cfg.get('redact', True):
            redact_act = QAction('Redact Selection', self)
            redact_act.triggered.connect(self.redact_selection)
            menu.addAction(redact_act)

        # Create calendar event from selection
        if notes_cfg.get('create_calendar_event', True):
            cal_act = QAction('Create Calendar Event from Selection', self)
            cal_act.triggered.connect(self.create_calendar_event_from_selection)
            menu.addAction(cal_act)

        # Export selection
        if notes_cfg.get('export_selection', True):
            export_act = QAction('Export Selection...', self)
            export_act.triggered.connect(self.export_selection_pdf)
            menu.addAction(export_act)

        menu.exec_(self.note_editor.mapToGlobal(pos))

    # ---------------------- Context menu helper stubs ----------------------
    def insert_template_from_context(self):
        try:
            tm = TemplateManager()
            template_names = tm.list_templates()
            tpl, ok = QInputDialog.getItem(self, 'Insert Template', 'Choose template:', template_names, 0, False)
            if ok and tpl:
                content = tm.render(tpl)
                cursor = self.note_editor.textCursor()
                cursor.insertHtml(content)
                self.audit.log('NOTE_TEMPLATE_INSERTED', {'template': tpl})
        except Exception as e:
            logger.error(f"Failed to insert template: {e}")
            QMessageBox.information(self, 'Insert Template', 'Template insertion not available.')

    def create_task_from_selection(self):
        cursor = self.note_editor.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else ''
        task, ok = QInputDialog.getText(self, 'Create Task', 'Task description:', text=text)
        if ok and task:
            due, ok2 = QInputDialog.getText(self, 'Due Date', 'Due date (YYYY-MM-DD):')
            self.tasks.append({'task': task, 'status': 'open', 'due': due or ''})
            self.save_notes()
            self.audit.log('NOTE_TASK_CREATED', {'task': task, 'due': due})
            QMessageBox.information(self, 'Create Task', 'Task created and linked to note.')

    def tag_selection(self):
        cursor = self.note_editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, 'Tag', 'Please select text to tag.')
            return
        tag, ok = QInputDialog.getText(self, 'Add Tag', 'Tag name:')
        if ok and tag:
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole) if self.notes_tree.currentItem() else None
            if note_id:
                self.notes[note_id].setdefault('tags', []).append(tag)
                self.save_notes()
                self.audit.log('NOTE_TAG_ADDED', {'note_id': note_id, 'tag': tag})
                QMessageBox.information(self, 'Tag', f'Tag "{tag}" added.')

    def redact_selection(self):
        cursor = self.note_editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, 'Redact', 'Please select text to redact.')
            return
        reply = QMessageBox.question(self, 'Redact', 'Redact selected text? This action will replace selection with [REDACTED].', QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            cursor.insertText('[REDACTED]')
            self.audit.log('NOTE_REDACTED', {'case': self.case_dir})

    def create_calendar_event_from_selection(self):
        cursor = self.note_editor.textCursor()
        text = cursor.selectedText() if cursor.hasSelection() else ''
        dt, _, _ = self._parse_timestamp(text)
        if dt is None:
            date_str, ok = QInputDialog.getText(self, 'Create Calendar Event', 'Event date (YYYY-MM-DD):')
            if not ok:
                return
        else:
            date_str = dt.date().isoformat()
        etype, ok2 = QInputDialog.getItem(self, 'Event Type', 'Type:', ['hearing', 'trial', 'deposition', 'sentencing'], 0, False)
        if ok2:
            self.audit.log('NOTE_CREATE_CAL_EVENT', {'date': date_str, 'type': etype})
            QMessageBox.information(self, 'Calendar Event', f'Event created: {etype} on {date_str} (manual step may be required).')

    def export_selection_pdf(self):
        cursor = self.note_editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, 'Export', 'Please select text to export.')
            return
        text = cursor.selectedText()
        path, _ = QFileDialog.getSaveFileName(self, 'Export Selection as HTML', '', 'HTML Files (*.html)')
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.audit.log('NOTE_SELECTION_EXPORTED', {'path': path})
            QMessageBox.information(self, 'Export', f'Selection exported to {path}.')

    def refresh_context_menu_settings(self):
        """Reload context-menu related settings from config and update toolbar/actions."""
        try:
            from auth import load_config
            cfg = load_config()
        except Exception as e:
            logger.warning(f"Could not load config for context menu refresh: {e}")
            cfg = {}
        notes_cfg = cfg.get('context_menu', {}).get('notes', {}) if cfg else {}
        # Enable/disable timestamp actions
        try:
            enabled = bool(notes_cfg.get('insert_timestamp', True))
            if hasattr(self, 'insert_ts_local_act'):
                self.insert_ts_local_act.setEnabled(enabled)
            if hasattr(self, 'insert_ts_iso_act'):
                self.insert_ts_iso_act.setEnabled(enabled)
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not update timestamp action state: {e}")
        try:
            conv_enabled = bool(notes_cfg.get('convert_timestamp', True))
            if hasattr(self, 'convert_ts_act'):
                self.convert_ts_act.setEnabled(conv_enabled)
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Could not update convert_ts_act state: {e}")

    # ---------------------- Timestamp Conversion Helpers ----------------------
    def _detect_tz_from_abbrev(self, text):
        """Detect common US timezone abbreviations and return tz database name."""
        if not text:
            return None
        import re
        m = re.search(r"\b([A-Z]{2,4}|UTC|GMT)\b", text)
        if not m:
            return None
        abb = m.group(1).upper()
        # Mapping can include multiple plausible zones for ambiguous abbreviations
        mapping = {
            'PST': ['America/Los_Angeles'], 'PDT': ['America/Los_Angeles'],
            'MST': ['America/Denver'], 'MDT': ['America/Denver'],
            'CST': ['America/Chicago', 'Asia/Shanghai'], 'CDT': ['America/Chicago'],
            'EST': ['America/New_York'], 'EDT': ['America/New_York'],
            'AKST': ['America/Anchorage'], 'AKDT': ['America/Anchorage'],
            'HST': ['Pacific/Honolulu'], 'UTC': ['UTC'], 'GMT': ['Etc/GMT']
        }
        vals = mapping.get(abb)
        if not vals:
            return None
        # Return the primary candidate for backwards compatibility
        return vals[0]

    def _detect_tz_choices(self, text):
        """Return list of possible tz database names for an abbreviation found in text."""
        if not text:
            return None
        import re
        m = re.search(r"\b([A-Z]{2,4}|UTC|GMT)\b", text)
        if not m:
            return None
        abb = m.group(1).upper()
        mapping = {
            'PST': ['America/Los_Angeles'], 'PDT': ['America/Los_Angeles'],
            'MST': ['America/Denver'], 'MDT': ['America/Denver'],
            'CST': ['America/Chicago', 'Asia/Shanghai'], 'CDT': ['America/Chicago'],
            'EST': ['America/New_York'], 'EDT': ['America/New_York'],
            'AKST': ['America/Anchorage'], 'AKDT': ['America/Anchorage'],
            'HST': ['Pacific/Honolulu'], 'UTC': ['UTC'], 'GMT': ['Etc/GMT']
        }
        return mapping.get(abb)

    def _parse_timestamp(self, text):
        """Parse a timestamp string into an aware datetime when possible.

        Returns (dt, detected_tzname or None, used_parser_str)
        """
        if not text or not text.strip():
            return None, None, None
        # Try dateutil first for flexibility
        try:
            if dateutil_parser:
                dt = dateutil_parser.parse(text, fuzzy=True)
                # if dt is naive, try to detect tz abbrev
                tzname = None
                if dt.tzinfo is None:
                    tzname = self._detect_tz_from_abbrev(text)
                    if tzname:
                        if ZoneInfo:
                            dt = dt.replace(tzinfo=ZoneInfo(tzname))
                        else:
                            dt = dt.replace(tzinfo=dateutil_tz.gettz(tzname))
                else:
                    # capture tz name if available
                    try:
                        tzname = dt.tzname()
                    except Exception as e:
                        logger.debug(f"Failed to get tzname: {e}")
                        tzname = None
            return dt, tzname, 'dateutil'
        except Exception as e:
            logger.debug(f"Dateutil parse failed: {e}")

        # Fallback to fromisoformat for ISO strings
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                tzname = self._detect_tz_from_abbrev(text)
                if tzname:
                    if ZoneInfo:
                        dt = dt.replace(tzinfo=ZoneInfo(tzname))
                    else:
                        dt = dt.replace(tzinfo=dateutil_tz.gettz(tzname) if dateutil_tz else None)
            return dt, tzname, 'iso'
        except Exception as e:
            logger.debug(f"ISO parse failed: {e}")

        return None, None, None

    def _format_converted(self, dt, original_text):
        """Format converted datetime preserving a reasonable style.

        If original looks ISO, return ISO; else return 'YYYY-MM-DD HH:MM:SS ±HH:MM (TZ)'
        """
        try:
            import re
            if re.match(r"^\d{4}-\d{2}-\d{2}T", original_text):
                return dt.isoformat()
        except (TypeError, AttributeError) as e:
            logger.debug(f"ISO format detection failed: {e}")
        # default readable
        try:
            tz = dt.tzinfo.tzname(dt) if dt.tzinfo else ''
        except Exception as e:
            logger.debug(f"Failed to get timezone name: {e}")
            tz = ''
        return dt.strftime(f"%Y-%m-%d %H:%M:%S") + (f" {tz}" if tz else "")

    # ---------------------- Conversion UI & Integration ----------------------
    def convert_selected_timestamp(self):
        cursor = self.note_editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.information(self, "Convert Timestamp", "Please highlight a timestamp to convert.")
            return
        selected = cursor.selectedText()
        dt, detected_tz, used = self._parse_timestamp(selected)
        if dt is None:
            QMessageBox.warning(self, "Convert Timestamp", "Could not parse the selected text as a timestamp.")
            return

        # Build dialog
        dlg = QDialog(self)
        dlg.setWindowTitle("Convert Timestamp")
        fl = QFormLayout(dlg)
        src_lbl = QLabel(selected)
        fl.addRow("Original:", src_lbl)

        # Detected source tz
        src_tz_lbl = QLabel(detected_tz or "(not detected)")
        fl.addRow("Detected TZ:", src_tz_lbl)
        # If abbreviation is ambiguous, allow user to select the source TZ
        choices = self._detect_tz_choices(selected)
        src_tz_selector = None
        if choices and len(choices) > 1:
            src_tz_selector = QComboBox()
            src_tz_selector.addItems(choices)
            try:
                if detected_tz in choices:
                    src_tz_selector.setCurrentText(detected_tz)
            except (ValueError, RuntimeError) as e:
                logger.debug(f"Could not set source TZ selector: {e}")
            fl.addRow('Assumed Source TZ:', src_tz_selector)

        # Target timezone options
        tz_combo = QComboBox()
        cfg_tz = None
        try:
            from auth import load_config
            cfg = load_config()
            cfg_tz = cfg.get('timezone')
        except Exception as e:
            logger.warning(f"Could not load config for timezone: {e}")
            cfg_tz = None
        choices = ['UTC', 'System Local']
        if cfg_tz and cfg_tz not in ['local', 'UTC']:
            choices.insert(0, cfg_tz)
        # include a few common US zones
        for z in ['America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles']:
            if z not in choices:
                choices.append(z)
        tz_combo.addItems(choices)
        # Select user's configured timezone if available
        try:
            if cfg_tz:
                if cfg_tz == 'local':
                    tz_combo.setCurrentText('System Local')
                elif cfg_tz == 'UTC' or (isinstance(cfg_tz, str) and cfg_tz.startswith('UTC')):
                    tz_combo.setCurrentText('UTC')
                else:
                    tz_combo.setCurrentText(cfg_tz)
        except (ValueError, RuntimeError) as e:
            logger.debug(f"Could not set target TZ combo: {e}")
        fl.addRow("Target TZ:", tz_combo)

        # Format option
        fmt_combo = QComboBox()
        fmt_combo.addItems(['ISO 8601 (with TZ)', 'Readable (YYYY-MM-DD HH:MM:SS TZ)'])
        fl.addRow('Output Format:', fmt_combo)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        fl.addRow(btns)
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)

        if dlg.exec_() != QDialog.Accepted:
            return

        target_tz_text = tz_combo.currentText()
        if target_tz_text == 'System Local':
            target_tz = None
        else:
            target_tz = target_tz_text

        # Perform conversion
        try:
            if target_tz is None:
                # system local
                if dateutil_tz:
                    tgt = dateutil_tz.tzlocal()
                else:
                    tgt = None
            else:
                if ZoneInfo:
                    tgt = ZoneInfo(target_tz)
                else:
                    tgt = dateutil_tz.gettz(target_tz) if dateutil_tz else None

            # If dt is naive, assume chosen source TZ (if provided), else detected_tz or cfg_tz or system local
            if dt.tzinfo is None:
                chosen_src = None
                if src_tz_selector is not None:
                    try:
                        chosen_src = src_tz_selector.currentText()
                    except Exception as e:
                        logger.debug(f"Failed to get source timezone: {e}")
                        chosen_src = None
                if chosen_src:
                    if ZoneInfo:
                        dt = dt.replace(tzinfo=ZoneInfo(chosen_src))
                    elif dateutil_tz:
                        dt = dt.replace(tzinfo=dateutil_tz.gettz(chosen_src))
                elif detected_tz:
                    if ZoneInfo and isinstance(detected_tz, str):
                        dt = dt.replace(tzinfo=ZoneInfo(detected_tz))
                    elif dateutil_tz:
                        dt = dt.replace(tzinfo=dateutil_tz.gettz(detected_tz))
                else:
                    # try config tz
                    if cfg_tz and cfg_tz not in ['local', 'UTC']:
                        if ZoneInfo:
                            dt = dt.replace(tzinfo=ZoneInfo(cfg_tz))
                        elif dateutil_tz:
                            dt = dt.replace(tzinfo=dateutil_tz.gettz(cfg_tz))
                    elif cfg_tz == 'UTC':
                        if ZoneInfo:
                            dt = dt.replace(tzinfo=ZoneInfo('UTC'))
                        else:
                            dt = dt.replace(tzinfo=dateutil_tz.gettz('UTC') if dateutil_tz else None)

            # Convert
            if tgt is not None:
                converted = dt.astimezone(tgt)
            else:
                # to system local
                if dateutil_tz:
                    converted = dt.astimezone(dateutil_tz.tzlocal())
                else:
                    converted = dt

            # Format result
            if fmt_combo.currentText().startswith('ISO'):
                out = converted.isoformat()
            else:
                try:
                    tzname = converted.tzname() or ''
                except Exception as e:
                    logger.debug(f"Failed to get converted timezone name: {e}")
                    tzname = ''
                out = converted.strftime('%Y-%m-%d %H:%M:%S') + (f' {tzname}' if tzname else '')

            # Replace selection
            cursor.insertText(out)
            # Save note state
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole) if self.notes_tree.currentItem() else None
            if note_id:
                content = self.note_editor.toHtml()
                self.notes[note_id]['content'] = content
                self.notes[note_id]['timestamp'] = datetime.now().isoformat()
                self.notes[note_id]['hash'] = hashlib.sha256(content.encode()).hexdigest()
                self.save_notes()
                self.audit.log('NOTE_TIMESTAMP_CONVERTED', {'note_id': note_id, 'original': selected, 'converted': out})
        except Exception as e:
            QMessageBox.warning(self, 'Convert Timestamp', f'Error converting timestamp: {e}')

    def insert_timestamp_at_cursor(self, fmt='local'):
        """Insert the current date/time at the cursor position.

        fmt: 'local' -> human readable local datetime
             'iso'   -> ISO 8601 with timezone
        """
        try:
            if fmt == 'iso':
                ts = datetime.now().astimezone().isoformat()
            else:
                ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor = self.note_editor.textCursor()
            cursor.insertText(ts)
            # Ensure editor keeps focus after insertion
            self.note_editor.setFocus()
            # After manual insertion, update the current note timestamp and save
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole) if self.notes_tree.currentItem() else None
            if note_id:
                content = self.note_editor.toHtml()
                self.notes[note_id]['content'] = content
                self.notes[note_id]['timestamp'] = datetime.now().isoformat()
                self.notes[note_id]['hash'] = hashlib.sha256(content.encode()).hexdigest()
                self.save_notes()
                self.audit.log("NOTE_TIMESTAMP_INSERTED", {"note_id": note_id, "timestamp": self.notes[note_id]['timestamp'], 'format': fmt})
        except Exception as e:
            logger.warning(f"Failed to insert timestamp: {e}")

    def add_link(self):
        link, ok = QInputDialog.getText(self, "Add Link", "Link to Note ID or Entity:")
        if ok:
            note_id = self.notes_tree.currentItem().data(0, Qt.UserRole)
            if note_id:
                self.notes[note_id]['links'].append(link)
                self.save_notes()
                self.audit.log("LINK_ADDED", {"note_id": note_id, "link": link})

    def search_notes(self, query):
        for i in range(self.notes_tree.topLevelItemCount()):
            item = self.notes_tree.topLevelItem(i)
            note_id = item.data(0, Qt.UserRole)
            if note_id and query.lower() in self.notes[note_id]['content'].lower():
                item.setSelected(True)
            else:
                item.setSelected(False)

    def geo_lookup(self):
        mode, ok = QInputDialog.getItem(self, "Geo Lookup", "Single or Bulk?", ["Single", "Bulk"], 0, False)
        if ok:
            if mode == "Single":
                lat, ok1 = QInputDialog.getText(self, "Latitude", "Latitude:")
                long, ok2 = QInputDialog.getText(self, "Longitude", "Longitude:")
                if ok1 and ok2:
                    try:
                        coords = (float(lat), float(long))
                        location = self.reverse(coords, language='en')
                        address = location.address if location else "No address found"
                        self.audit.log("GEO_LOOKUP_SINGLE", {"coords": coords, "address": address})
                        reply = QMessageBox.question(self, "Geo Result", f"Address: {address}\nInsert into note?")
                        if reply == QMessageBox.Yes:
                            cursor = self.note_editor.textCursor()
                            cursor.insertText(f"Geo Lookup ({coords}): {address}\n")
                    except ValueError:
                        QMessageBox.warning(self, "Error", "Invalid lat/long format.")

            else:  # Bulk
                file, _ = QFileDialog.getOpenFileName(self, "Select CSV", "", "CSV Files (*.csv)")
                if file:
                    df = pd.read_csv(file)
                    unique_locations = df[['latitude', 'longitude']].drop_duplicates().reset_index(drop=True)
                    unique_locations['address'] = None

                    def get_address(row):
                        try:
                            coords = (row['latitude'], row['longitude'])
                            location = self.reverse(coords, language='en')
                            return location.address if location else "No address"
                        except Exception as e:
                            logger.warning(f"Geo lookup error: {e}")
                            return "Error"

                    unique_locations['address'] = unique_locations.apply(get_address, axis=1)
                    results_df = df.merge(unique_locations, on=['latitude', 'longitude'], how='left')

                    # Show results in table
                    dlg = QDialog(self)
                    dlg.setWindowTitle("Bulk Geo Results")
                    dlg_layout = QVBoxLayout(dlg)

                    table = QTableWidget(len(results_df), 3)
                    table.setHorizontalHeaderLabels(["Latitude", "Longitude", "Address"])
                    for i, row in results_df.iterrows():
                        table.setItem(i, 0, QTableWidgetItem(str(row['latitude'])))
                        table.setItem(i, 1, QTableWidgetItem(str(row['longitude'])))
                        table.setItem(i, 2, QTableWidgetItem(row['address']))

                    dlg_layout.addWidget(table)

                    insert_btn = QPushButton("Insert Selected as Table")
                    insert_btn.clicked.connect(lambda: self.insert_geo_table(table, dlg))
                    dlg_layout.addWidget(insert_btn)

                    self.audit.log("GEO_LOOKUP_BULK", {"file": os.path.basename(file), "rows": len(results_df)})
                    dlg.exec_()

    def insert_geo_table(self, table, dlg):
        selected = table.selectedItems()
        if not selected:
            QMessageBox.warning(dlg, "Selection", "No rows selected.")
            return

        cursor = self.note_editor.textCursor()
        cursor.insertHtml("<h3>Geo Lookup Results</h3><table border='1'><tr><th>Latitude</th><th>Longitude</th><th>Address</th></tr>")
        rows = set(item.row() for item in selected)
        for row in sorted(rows):
            cursor.insertHtml(f"<tr><td>{table.item(row, 0).text()}</td><td>{table.item(row, 1).text()}</td><td>{table.item(row, 2).text()}</td></tr>")
        cursor.insertHtml("</table>")
        dlg.accept()

    def voice_to_text(self):
        if sr is None:
            QMessageBox.warning(self, "Voice to Text", "Speech recognition module not available. Please install SpeechRecognition.")
            return
        r = sr.Recognizer()
        with sr.Microphone() as source:
            audio = r.listen(source)
            try:
                text = r.recognize_sphinx(audio)  # Offline
                cursor = self.note_editor.textCursor()
                cursor.insertText(text)
                self.audit.log("VOICE_TO_TEXT", {"text": text})
            except sr.UnknownValueError:
                QMessageBox.warning(self, "Voice to Text", "Could not understand audio")
            except sr.RequestError as e:
                QMessageBox.warning(self, "Voice to Text", f"Offline STT error: {e}")

    def add_attachment(self):
        file, _ = QFileDialog.getOpenFileName(self, "Add Attachment")
        if file:
            dest = os.path.join(self.case_dir, os.path.basename(file))
            shutil.copy(file, dest)
            self.attachments.append(dest)
            hash_value = compute_sha256(dest)
            self.audit.log("ATTACHMENT_ADDED", {"file": os.path.basename(dest), "hash": hash_value})
            pixmap = QPixmap(dest)
            if not pixmap.isNull():
                self.preview_label.setPixmap(pixmap.scaled(300, 300, Qt.KeepAspectRatio))
            else:
                self.preview_label.setText("Attachment added (non-image)")

    def generate_timeline(self):
        if not self.notes:
            QMessageBox.warning(self, "Timeline", "No notes available.")
            return

        times = [datetime.fromisoformat(note['timestamp']) for note in self.notes.values()]
        labels = [f"Note {note_id}" for note_id in self.notes]

        fig, ax = plt.subplots()
        ax.eventplot(times, orientation='horizontal', colors='b')
        ax.set_yticklabels(labels)
        ax.set_title("Case Timeline")
        timeline_path = os.path.join(self.case_dir, "timeline.png")
        fig.savefig(timeline_path)
        plt.close(fig)

        pixmap = QPixmap(timeline_path)
        self.preview_label.setPixmap(pixmap.scaled(600, 400, Qt.KeepAspectRatio))
        self.audit.log("TIMELINE_GENERATED", {"path": timeline_path})

    def export_to_report(self):
        export_html = "<h2>Exported Notes</h2>"
        for note_id, note in self.notes.items():
            export_html += f"<h3>Note {note_id} ({note['timestamp']})</h3>{note['content']}<p>Hash: {note['hash']}</p>"

        export_html += "<h2>Entities</h2><table><tr><th>Name</th><th>Type</th><th>Linked Notes</th></tr>"
        for entity in self.entities:
            export_html += f"<tr><td>{entity['name']}</td><td>{entity['type']}</td><td>{', '.join(entity['notes_linked'])}</td></tr>"
        export_html += "</table>"

        export_html += "<h2>Tasks</h2><ul>"
        for task in self.tasks:
            export_html += f"<li>{task['task']} - Due: {task['due']} ({task['status']})</li>"
        export_html += "</ul>"

        export_html += "<h2>Attachments</h2><ul>"
        for attach in self.attachments:
            export_html += f"<li>{os.path.basename(attach)} (Hash: {compute_sha256(attach)})</li>"
        export_html += "</ul>"

        # Insert into report editor (assume parent is CaseTab)
        if hasattr(self.parent(), 'editor'):
            cursor = self.parent().editor.textCursor()
            cursor.insertHtml(export_html)
            self.close()
        else:
            # Fallback save
            export_path = os.path.join(self.case_dir, "notes_export.html")
            with open(export_path, "w") as f:
                f.write(export_html)
            self.audit.log("NOTES_EXPORTED", {"path": export_path})
            QMessageBox.information(self, "Export", f"Notes exported to {export_path}.")

    def save_notes(self):
        data = {
            'notes': self.notes,
            'entities': self.entities,
            'tasks': self.tasks,
            'attachments': self.attachments
        }
        save_path = os.path.join(self.case_dir, "notes_data.json")
        with open(save_path, "w") as f:
            json.dump(data, f)
        hash_value = compute_sha256(save_path)
        self.audit.log("NOTES_SAVED", {"hash": hash_value})

    def load_notes(self):
        save_path = os.path.join(self.case_dir, "notes_data.json")
        if os.path.exists(save_path):
            with open(save_path, "r") as f:
                data = json.load(f)
            self.notes = data['notes']
            self.entities = data['entities']
            self.tasks = data['tasks']
            self.attachments = data['attachments']

            # Rebuild tree
            for note_id in self.notes:
                item = QTreeWidgetItem(self.notes_tree, [f"Note {note_id}"])
                item.setData(0, Qt.UserRole, note_id)

    def toggle_bold(self, checked):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
            cursor.setCharFormat(fmt)
        fmt = self.note_editor.currentCharFormat()
        fmt.setFontWeight(QFont.Bold if checked else QFont.Normal)
        self.note_editor.setCurrentCharFormat(fmt)

    def toggle_italic(self):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            cursor.setCharFormat(fmt)
            self.note_editor.setCurrentCharFormat(fmt)
        else:
            fmt = self.note_editor.currentCharFormat()
            fmt.setFontItalic(not fmt.fontItalic())
            self.note_editor.setCurrentCharFormat(fmt)

    def toggle_underline(self):
        cursor = self.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontUnderline(not fmt.fontUnderline())
            cursor.setCharFormat(fmt)
            self.note_editor.setCurrentCharFormat(fmt)
        else:
            fmt = self.note_editor.currentCharFormat()
            fmt.setFontUnderline(not fmt.fontUnderline())
            self.note_editor.setCurrentCharFormat(fmt)

    def insert_bullet_list(self):
        cursor = self.note_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDisc)
        cursor.createList(list_format)

    def insert_numbered_list(self):
        cursor = self.note_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDecimal)
        cursor.createList(list_format)




class NotesWindow(QMainWindow):
    def __init__(self, case_data, db_manager, audit_logger, current_user):
        super().__init__()
        self.setWindowTitle(f"Notes - Case {case_data['case_number']}")
        self.setMinimumSize(1200, 800)

        self.notes_tab = NotesTab(case_data, db_manager, audit_logger, self)
        self.setCentralWidget(self.notes_tab)

        self.setup_menu()
        self.setup_search_toolbar()
        self.setup_toolbar()

    def setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("File")
        add_note_act = QAction("Add New Note", self)
        add_note_act.setShortcut(QKeySequence("Ctrl+N"))
        add_note_act.triggered.connect(self.notes_tab.add_note)
        file_menu.addAction(add_note_act)

        save_act = QAction("Save", self)
        save_act.setShortcut(QKeySequence.Save)
        save_act.triggered.connect(self.notes_tab.save_notes)
        file_menu.addAction(save_act)

        export_act = QAction("Export to Report", self)
        export_act.triggered.connect(self.notes_tab.export_to_report)
        file_menu.addAction(export_act)

        close_act = QAction("Close", self)
        close_act.setShortcut(QKeySequence.Close)
        close_act.triggered.connect(self.close)
        file_menu.addAction(close_act)

        edit_menu = menu.addMenu("Edit")
        undo_act = QAction("Undo", self)
        undo_act.setShortcut(QKeySequence.Undo)
        undo_act.triggered.connect(self.notes_tab.note_editor.undo)
        edit_menu.addAction(undo_act)

        redo_act = QAction("Redo", self)
        redo_act.setShortcut(QKeySequence.Redo)
        redo_act.triggered.connect(self.notes_tab.note_editor.redo)
        edit_menu.addAction(redo_act)

        template_act = QAction("Load Template", self)
        template_act.setShortcut(QKeySequence("Ctrl+T"))
        template_act.triggered.connect(lambda: TemplateManager(self.notes_tab, self.notes_tab.note_editor).exec_())
        edit_menu.addAction(template_act)

        add_tag_act = QAction("Add Tag", self)
        add_tag_act.setShortcut(QKeySequence("Ctrl+G"))
        add_tag_act.triggered.connect(self.notes_tab.add_tag)
        edit_menu.addAction(add_tag_act)

        add_link_act = QAction("Add Link", self)
        add_link_act.setShortcut(QKeySequence("Ctrl+L"))
        add_link_act.triggered.connect(self.notes_tab.add_link)
        edit_menu.addAction(add_link_act)

        add_attachment_act = QAction("Add Attachment", self)
        add_attachment_act.triggered.connect(self.notes_tab.add_attachment)
        edit_menu.addAction(add_attachment_act)

        tools_menu = menu.addMenu("Tools")
        find_replace_act = QAction("Find and Replace", self)
        find_replace_act.setShortcut(QKeySequence.Find)
        find_replace_act.triggered.connect(self.notes_tab.word_processor.show_find_replace)
        tools_menu.addAction(find_replace_act)

        tools_menu.addSeparator()

        voice_act = QAction("Voice to Text", self)
        voice_act.setShortcut(QKeySequence("Ctrl+V"))
        voice_act.triggered.connect(self.notes_tab.voice_to_text)
        tools_menu.addAction(voice_act)

        geo_act = QAction("Geo Lookup", self)
        geo_act.setShortcut(QKeySequence("Ctrl+Shift+G"))
        geo_act.triggered.connect(self.notes_tab.geo_lookup)
        tools_menu.addAction(geo_act)

        generate_timeline_act = QAction("Generate Timeline", self)
        generate_timeline_act.triggered.connect(self.notes_tab.generate_timeline)
        tools_menu.addAction(generate_timeline_act)

        insert_menu = menu.addMenu("Insert")
        image_act = QAction("Image", self)
        image_act.triggered.connect(self.insert_image)
        insert_menu.addAction(image_act)

        table_act = QAction("Table", self)
        table_act.triggered.connect(self.insert_table)
        insert_menu.addAction(table_act)

        page_break_act = QAction("Page Break", self)
        page_break_act.triggered.connect(self.insert_page_break)
        insert_menu.addAction(page_break_act)

        format_menu = menu.addMenu("Format")
        font_act = QAction("Font...", self)
        font_act.triggered.connect(self.change_font)
        format_menu.addAction(font_act)

        color_act = QAction("Text Color...", self)
        color_act.triggered.connect(self.change_text_color)
        format_menu.addAction(color_act)

        bg_color_act = QAction("Background Color...", self)
        bg_color_act.triggered.connect(self.change_bg_color)
        format_menu.addAction(bg_color_act)

        align_left_act = QAction("Align Left", self)
        align_left_act.triggered.connect(lambda: self.align_text(Qt.AlignLeft))
        format_menu.addAction(align_left_act)

        align_center_act = QAction("Align Center", self)
        align_center_act.triggered.connect(lambda: self.align_text(Qt.AlignCenter))
        format_menu.addAction(align_center_act)

        align_right_act = QAction("Align Right", self)
        align_right_act.triggered.connect(lambda: self.align_text(Qt.AlignRight))
        format_menu.addAction(align_right_act)

        align_justify_act = QAction("Justify", self)
        align_justify_act.triggered.connect(lambda: self.align_text(Qt.AlignJustify))
        format_menu.addAction(align_justify_act)

        format_menu.addSeparator()

        # Line spacing submenu
        line_spacing_menu = format_menu.addMenu("Line Spacing")
        single_spacing_act = QAction("Single", self)
        single_spacing_act.triggered.connect(lambda: self.notes_tab.word_processor.set_line_spacing("single"))
        line_spacing_menu.addAction(single_spacing_act)

        one_half_spacing_act = QAction("1.5 Lines", self)
        one_half_spacing_act.triggered.connect(lambda: self.notes_tab.word_processor.set_line_spacing("1.5"))
        line_spacing_menu.addAction(one_half_spacing_act)

        double_spacing_act = QAction("Double", self)
        double_spacing_act.triggered.connect(lambda: self.notes_tab.word_processor.set_line_spacing("double"))
        line_spacing_menu.addAction(double_spacing_act)

        # Paragraph spacing submenu
        para_spacing_menu = format_menu.addMenu("Paragraph Spacing")
        para_none_act = QAction("No Spacing", self)
        para_none_act.triggered.connect(lambda: self.notes_tab.word_processor.set_paragraph_spacing("none"))
        para_spacing_menu.addAction(para_none_act)

        para_small_act = QAction("Small", self)
        para_small_act.triggered.connect(lambda: self.notes_tab.word_processor.set_paragraph_spacing("small"))
        para_spacing_menu.addAction(para_small_act)

        para_medium_act = QAction("Medium", self)
        para_medium_act.triggered.connect(lambda: self.notes_tab.word_processor.set_paragraph_spacing("medium"))
        para_spacing_menu.addAction(para_medium_act)

        para_large_act = QAction("Large", self)
        para_large_act.triggered.connect(lambda: self.notes_tab.word_processor.set_paragraph_spacing("large"))
        para_spacing_menu.addAction(para_large_act)

        format_menu.addSeparator()

        copy_format_act = QAction("Copy Formatting", self)
        copy_format_act.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copy_format_act.triggered.connect(self.notes_tab.word_processor.copy_format)
        format_menu.addAction(copy_format_act)

        paste_format_act = QAction("Paste Formatting", self)
        paste_format_act.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_format_act.triggered.connect(self.notes_tab.word_processor.paste_format)
        format_menu.addAction(paste_format_act)

        clear_format_act = QAction("Clear Formatting", self)
        clear_format_act.triggered.connect(self.notes_tab.word_processor.clear_formatting)
        format_menu.addAction(clear_format_act)

    def setup_search_toolbar(self):
        toolbar = self.addToolBar("Search")

        # Search
        search_edit = QLineEdit()
        search_edit.setPlaceholderText("Search notes...")
        search_edit.setToolTip("Search Notes")
        search_edit.textChanged.connect(self.notes_tab.search_notes)
        toolbar.addWidget(search_edit)

    def setup_toolbar(self):
        toolbar = self.addToolBar("Formatting")

        # Font family
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        toolbar.addWidget(self.font_combo)

        # Font size
        self.size_combo = QComboBox()
        self.size_combo.addItems([str(i) for i in range(8, 72, 2)])
        self.size_combo.setCurrentText("12")
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        toolbar.addWidget(self.size_combo)

        toolbar.addSeparator()

        # Style dropdown
        style_btn = QToolButton(self)
        style_btn.setText("Style")
        style_btn.setPopupMode(QToolButton.InstantPopup)
        style_menu = QMenu(self)
        style_btn.setMenu(style_menu)

        bold_act = QAction("Bold", self)
        bold_act.setCheckable(True)
        bold_act.triggered.connect(self.notes_tab.toggle_bold)
        style_menu.addAction(bold_act)

        italic_act = QAction("Italic", self)
        italic_act.setCheckable(True)
        italic_act.triggered.connect(self.notes_tab.toggle_italic)
        style_menu.addAction(italic_act)

        underline_act = QAction("Underline", self)
        underline_act.setCheckable(True)
        underline_act.triggered.connect(self.notes_tab.toggle_underline)
        style_menu.addAction(underline_act)

        strikethrough_act = QAction("Strikethrough", self)
        strikethrough_act.triggered.connect(self.notes_tab.word_processor.apply_strikethrough)
        style_menu.addAction(strikethrough_act)

        style_menu.addSeparator()

        subscript_act = QAction("Subscript", self)
        subscript_act.triggered.connect(self.notes_tab.word_processor.apply_subscript)
        style_menu.addAction(subscript_act)

        superscript_act = QAction("Superscript", self)
        superscript_act.triggered.connect(self.notes_tab.word_processor.apply_superscript)
        style_menu.addAction(superscript_act)

        toolbar.addWidget(style_btn)

        toolbar.addSeparator()

        # Color dropdown
        color_btn = QToolButton(self)
        color_btn.setText("Color")
        color_btn.setPopupMode(QToolButton.InstantPopup)
        color_menu = QMenu(self)
        color_btn.setMenu(color_menu)

        color_act = QAction("Text Color", self)
        color_act.triggered.connect(self.change_text_color)
        color_menu.addAction(color_act)

        bg_color_act = QAction("Background Color", self)
        bg_color_act.triggered.connect(self.change_bg_color)
        color_menu.addAction(bg_color_act)

        toolbar.addWidget(color_btn)

        toolbar.addSeparator()

        # Alignment dropdown
        align_btn = QToolButton(self)
        align_btn.setText("Align")
        align_btn.setPopupMode(QToolButton.InstantPopup)
        align_menu = QMenu(self)
        align_btn.setMenu(align_menu)

        align_left_act = QAction("Align Left", self)
        align_left_act.triggered.connect(lambda: self.align_text(Qt.AlignLeft))
        align_menu.addAction(align_left_act)

        align_center_act = QAction("Align Center", self)
        align_center_act.triggered.connect(lambda: self.align_text(Qt.AlignCenter))
        align_menu.addAction(align_center_act)

        align_right_act = QAction("Align Right", self)
        align_right_act.triggered.connect(lambda: self.align_text(Qt.AlignRight))
        align_menu.addAction(align_right_act)

        align_justify_act = QAction("Justify", self)
        align_justify_act.triggered.connect(lambda: self.align_text(Qt.AlignJustify))
        align_menu.addAction(align_justify_act)

        toolbar.addWidget(align_btn)

        toolbar.addSeparator()

        # Lists dropdown
        list_btn = QToolButton(self)
        list_btn.setText("Lists")
        list_btn.setPopupMode(QToolButton.InstantPopup)
        list_menu = QMenu(self)
        list_btn.setMenu(list_menu)

        bullet_act = QAction("Bullet List", self)
        bullet_act.triggered.connect(self.notes_tab.insert_bullet_list)
        list_menu.addAction(bullet_act)

        number_act = QAction("Numbered List", self)
        number_act.triggered.connect(self.notes_tab.insert_numbered_list)
        list_menu.addAction(number_act)

        toolbar.addWidget(list_btn)

        toolbar.addSeparator()

        # Indent dropdown
        indent_btn = QToolButton(self)
        indent_btn.setText("Indent")
        indent_btn.setPopupMode(QToolButton.InstantPopup)
        indent_menu = QMenu(self)
        indent_btn.setMenu(indent_menu)

        indent_act = QAction("Increase Indent", self)
        indent_act.triggered.connect(self.increase_indent)
        indent_menu.addAction(indent_act)

        outdent_act = QAction("Decrease Indent", self)
        outdent_act.triggered.connect(self.decrease_indent)
        indent_menu.addAction(outdent_act)

        toolbar.addWidget(indent_btn)

    def change_font_family(self, font):
        cursor = self.notes_tab.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontFamily(font.family())
            cursor.setCharFormat(fmt)
        else:
            fmt = self.notes_tab.note_editor.currentCharFormat()
            fmt.setFontFamily(font.family())
            self.notes_tab.note_editor.setCurrentCharFormat(fmt)

    def change_font_size(self, size):
        cursor = self.notes_tab.note_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontPointSize(int(size))
            cursor.setCharFormat(fmt)
        else:
            fmt = self.notes_tab.note_editor.currentCharFormat()
            fmt.setFontPointSize(int(size))
            self.notes_tab.note_editor.setCurrentCharFormat(fmt)

    def change_font(self):
        from PyQt5.QtWidgets import QFontDialog
        font, ok = QFontDialog.getFont()
        if ok:
            cursor = self.notes_tab.note_editor.textCursor()
            if cursor.hasSelection():
                fmt = cursor.charFormat()
                fmt.setFont(font)
                cursor.setCharFormat(fmt)
            else:
                fmt = self.notes_tab.note_editor.currentCharFormat()
                fmt.setFont(font)
                self.notes_tab.note_editor.setCurrentCharFormat(fmt)

    def change_text_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            cursor = self.notes_tab.note_editor.textCursor()
            if cursor.hasSelection():
                fmt = cursor.charFormat()
                fmt.setForeground(color)
                cursor.setCharFormat(fmt)
            else:
                fmt = self.notes_tab.note_editor.currentCharFormat()
                fmt.setForeground(color)
                self.notes_tab.note_editor.setCurrentCharFormat(fmt)

    def change_bg_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            cursor = self.notes_tab.note_editor.textCursor()
            if cursor.hasSelection():
                fmt = cursor.charFormat()
                fmt.setBackground(color)
                cursor.setCharFormat(fmt)
            else:
                fmt = self.notes_tab.note_editor.currentCharFormat()
                fmt.setBackground(color)
                self.notes_tab.note_editor.setCurrentCharFormat(fmt)

    def align_text(self, alignment):
        cursor = self.notes_tab.note_editor.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setAlignment(alignment)
        cursor.setBlockFormat(block_fmt)

    def increase_indent(self):
        cursor = self.notes_tab.note_editor.textCursor()
        block_fmt = cursor.blockFormat()
        block_fmt.setIndent(block_fmt.indent() + 1)
        cursor.setBlockFormat(block_fmt)

    def decrease_indent(self):
        cursor = self.notes_tab.note_editor.textCursor()
        block_fmt = cursor.blockFormat()
        indent = max(0, block_fmt.indent() - 1)
        block_fmt.setIndent(indent)
        cursor.setBlockFormat(block_fmt)

    def insert_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file:
            cursor = self.notes_tab.note_editor.textCursor()
            cursor.insertHtml(f'<img src="{file}" />')

    def insert_table(self):
        self.notes_tab.word_processor.insert_advanced_table()

    def insert_page_break(self):
        cursor = self.notes_tab.note_editor.textCursor()
        cursor.insertHtml('<div style="page-break-before: always;"></div>')

    def closeEvent(self, event):
        self.notes_tab.save_notes()
        super().closeEvent(event)
