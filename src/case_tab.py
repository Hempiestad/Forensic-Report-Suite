# case_tab.py
# FuDog Labs Forensic Report Suite - Case Tab with Report Editor, Evidence & Legal Tracking
import os
import shutil
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import enchant
except ImportError as e:
    logger.warning(f"Failed to import enchant: {e}")
    enchant = None

try:
    import html2text
except ImportError as e:
    logger.warning(f"Failed to import html2text: {e}")
    html2text = None

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QToolBar, QAction, QFileDialog, QMessageBox, QListWidget,
    QInputDialog, QDialog, QFormLayout, QComboBox, QLineEdit, QDialogButtonBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QSplitter, QDateTimeEdit, QHeaderView,
    QCheckBox, QMenuBar, QTimeEdit, QDateEdit, QSpacerItem, QSizePolicy, QAbstractItemView
)
from PyQt5.QtGui import QKeySequence, QTextCursor, QTextCharFormat, QColor, QIcon, QTextListFormat, QFont, QPalette
from PyQt5.QtCore import Qt, QDate, QDateTime

from security import compute_sha256
from glossary_assist import GlossaryAssist
from audit_log import AuditLogger
from templates import TemplateManager


def _contrast_text(bg: QColor) -> QColor:
    """Return white or black text that contrasts best against *bg*."""
    lum = 0.299 * bg.red() + 0.587 * bg.green() + 0.114 * bg.blue()
    return QColor('#ffffff') if lum < 140 else QColor('#000000')
from peer_review import PeerReview
from notes_tab import NotesWindow
from reports_tab import ReportsWindow

# Note: current_user will be passed as parameter to avoid circular import

class CaseTab(QWidget):
    def __init__(self, case_data, db_manager, current_user, parent=None, review_mode=False, status_colors=None):
        super().__init__(parent)
        self.case_data = case_data
        self.db = db_manager
        self.current_user = current_user
        self.parent_window = parent
        self.review_mode = review_mode
        self.status_colors = status_colors or {}

        self.case_dir = os.path.join("cases", case_data["case_number"])
        os.makedirs(self.case_dir, exist_ok=True)

        self.appendices = []
        self.saved_pdf_hash = ""

        self.audit = AuditLogger(self.case_dir, case_data["case_number"])

        self.setup_ui()
        self.load_report()
        self.update_dashboard_metrics()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(6)

        # Dashboard strip — fixed height, expands horizontally
        self.dashboard = QWidget()
        self.dashboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        dashboard_layout = QHBoxLayout(self.dashboard)
        dashboard_layout.setContentsMargins(6, 4, 6, 4)
        dashboard_layout.setSpacing(12)

        self.case_status_label = QLabel("Case Status: Draft")
        self.case_status_label.setObjectName("statusInfo")
        self.case_status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.evidence_metrics_label = QLabel("Evidence: 0 items")
        self.evidence_metrics_label.setObjectName("statusInfo")
        self.evidence_metrics_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.legal_metrics_label = QLabel("Legal: 0 processes")
        self.legal_metrics_label.setObjectName("statusInfo")
        self.legal_metrics_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        dashboard_layout.addWidget(self.case_status_label)
        dashboard_layout.addWidget(self.evidence_metrics_label)
        dashboard_layout.addWidget(self.legal_metrics_label)
        dashboard_layout.addStretch()

        # Open Notes and Reports buttons
        self.open_notes_btn = QPushButton("Open Notes")
        self.open_notes_btn.clicked.connect(self.open_notes)
        dashboard_layout.addWidget(self.open_notes_btn)

        self.open_reports_btn = QPushButton("Open Reports")
        self.open_reports_btn.clicked.connect(self.open_reports)
        dashboard_layout.addWidget(self.open_reports_btn)

        main_layout.addWidget(self.dashboard)

        # Sub-tabs — expanding to fill remaining space
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.sub_tabs, stretch=1)

        self.setup_evidence_tab()
        self.setup_legal_tab()
        self.setup_leads_tab()

        # Workflow buttons (role-based)
        workflow_layout = QHBoxLayout()
        if not self.review_mode and self.current_user['role'] == 'writer':
            self.submit_btn = QPushButton("Submit for Approval")
            self.submit_btn.clicked.connect(self.submit_for_approval)
            workflow_layout.addWidget(self.submit_btn)

        if self.db.conn is None and (self.review_mode or self.current_user['role'] in ['admin', 'supervisor']):
            self.approve_btn = QPushButton("Approve Report")
            self.approve_btn.clicked.connect(self.approve_case)
            workflow_layout.addWidget(self.approve_btn)

            self.reject_btn = QPushButton("Reject with Comments")
            self.reject_btn.clicked.connect(self.reject_case)
            workflow_layout.addWidget(self.reject_btn)

            self.close_btn = QPushButton("Close Case")
            self.close_btn.clicked.connect(self.close_case)
            workflow_layout.addWidget(self.close_btn)

        workflow_layout.addStretch()
        main_layout.addLayout(workflow_layout)

        # Status label
        self.hash_label = QLabel("Final PDF Hash: Not generated")
        main_layout.addWidget(self.hash_label)

    def setup_notes_widget(self):
        notes_widget = QWidget()
        notes_layout = QVBoxLayout(notes_widget)

        # Toolbar for notes
        self.notes_toolbar = QToolBar()
        notes_layout.addWidget(self.notes_toolbar)

        # Bold, Italic, Underline
        self.notes_bold_act = QAction("Bold", self)
        self.notes_bold_act.setCheckable(True)
        self.notes_bold_act.setShortcut(QKeySequence.Bold)
        self.notes_bold_act.triggered.connect(self.toggle_notes_bold)
        self.notes_toolbar.addAction(self.notes_bold_act)

        self.notes_italic_act = QAction("Italic", self)
        self.notes_italic_act.setCheckable(True)
        self.notes_italic_act.setShortcut(QKeySequence.Italic)
        self.notes_italic_act.triggered.connect(self.toggle_notes_italic)
        self.notes_toolbar.addAction(self.notes_italic_act)

        self.notes_underline_act = QAction("Underline", self)
        self.notes_underline_act.setCheckable(True)
        self.notes_underline_act.setShortcut(QKeySequence.Underline)
        self.notes_underline_act.triggered.connect(self.toggle_notes_underline)
        self.notes_toolbar.addAction(self.notes_underline_act)

        self.notes_toolbar.addSeparator()

        # Bullet / Numbered List
        notes_bullet_act = QAction("Bullet List", self)
        notes_bullet_act.triggered.connect(self.insert_notes_bullet_list)
        self.notes_toolbar.addAction(notes_bullet_act)

        notes_numbered_act = QAction("Numbered List", self)
        notes_numbered_act.triggered.connect(self.insert_notes_numbered_list)
        self.notes_toolbar.addAction(notes_numbered_act)

        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Enter your notes here...")
        notes_layout.addWidget(self.notes_editor)

        return notes_widget

    def setup_report_widget(self):
        report_tab = QWidget()
        report_layout = QVBoxLayout(report_tab)

        # Toolbar
        self.toolbar = QToolBar()
        report_layout.addWidget(self.toolbar)

        # Bold, Italic, Underline
        self.bold_act = QAction("Bold", self)
        self.bold_act.setCheckable(True)
        self.bold_act.setShortcut(QKeySequence.Bold)
        self.bold_act.triggered.connect(self.toggle_bold)
        self.toolbar.addAction(self.bold_act)

        self.italic_act = QAction("Italic", self)
        self.italic_act.setCheckable(True)
        self.italic_act.setShortcut(QKeySequence.Italic)
        self.italic_act.triggered.connect(self.toggle_italic)
        self.toolbar.addAction(self.italic_act)

        self.underline_act = QAction("Underline", self)
        self.underline_act.setCheckable(True)
        self.underline_act.setShortcut(QKeySequence.Underline)
        self.underline_act.triggered.connect(self.toggle_underline)
        self.toolbar.addAction(self.underline_act)

        self.toolbar.addSeparator()

        # Bullet / Numbered List
        bullet_act = QAction("Bullet List", self)
        bullet_act.triggered.connect(self.insert_bullet_list)
        self.toolbar.addAction(bullet_act)

        numbered_act = QAction("Numbered List", self)
        numbered_act.triggered.connect(self.insert_numbered_list)
        self.toolbar.addAction(numbered_act)

        self.toolbar.addSeparator()

        # Template
        template_act = QAction("Load Template", self)
        template_act.triggered.connect(self.load_template)
        self.toolbar.addAction(template_act)

        # Main editor
        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.on_text_changed)
        report_layout.addWidget(self.editor)

        # Peer Review (enabled in review mode) - moved to top menu
        self.peer_review = PeerReview(self.editor, self.audit, self.toolbar)

        # Glossary Assist - moved to top menu
        self.glossary_assist = GlossaryAssist(self.editor, self)

        return report_tab

    def setup_evidence_tab(self):
        evidence_tab = QWidget()
        evidence_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        evidence_layout = QVBoxLayout(evidence_tab)
        evidence_layout.setContentsMargins(4, 4, 4, 4)
        evidence_layout.setSpacing(4)

        # Toolbar for evidence with visible buttons
        self.evidence_toolbar = QToolBar()
        self.evidence_toolbar.setMovable(False)
        self.evidence_toolbar.setIconSize(self.evidence_toolbar.iconSize())
        evidence_layout.addWidget(self.evidence_toolbar)

        add_evidence_act = QAction("Add Evidence Item", self)
        add_evidence_act.triggered.connect(self.add_evidence_item)
        self.evidence_toolbar.addAction(add_evidence_act)

        update_evidence_act = QAction("Update Selected Item", self)
        update_evidence_act.triggered.connect(self.update_evidence_item)
        self.evidence_toolbar.addAction(update_evidence_act)

        delete_evidence_act = QAction("Delete Selected Item", self)
        delete_evidence_act.triggered.connect(self.delete_evidence_item)
        self.evidence_toolbar.addAction(delete_evidence_act)

        self.evidence_table = QTableWidget(0, 11)
        self.evidence_table.setHorizontalHeaderLabels([
            "ID", "Item Number", "Type", "Details", "Make", "Model", "Digital Type", "SN#", "Storage Size", "Password", "Status"
        ])
        self.evidence_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.evidence_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.evidence_table.setAlternatingRowColors(True)
        self.evidence_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # Connect cell change signal for editing
        self.evidence_table.cellChanged.connect(self.on_evidence_cell_changed)
        evidence_layout.addWidget(self.evidence_table, stretch=1)

        # Pagination controls
        self._evidence_page = 0
        self._evidence_page_size = 50
        pagination_bar = QHBoxLayout()
        self._evidence_prev_btn = QPushButton("\u25c4 Prev")
        self._evidence_prev_btn.setFixedWidth(70)
        self._evidence_prev_btn.clicked.connect(self._evidence_prev_page)
        self._evidence_next_btn = QPushButton("Next \u25ba")
        self._evidence_next_btn.setFixedWidth(70)
        self._evidence_next_btn.clicked.connect(self._evidence_next_page)
        self._evidence_page_label = QLabel("Page 1")
        self._evidence_page_label.setAlignment(Qt.AlignCenter)
        pagination_bar.addWidget(self._evidence_prev_btn)
        pagination_bar.addWidget(self._evidence_page_label)
        pagination_bar.addWidget(self._evidence_next_btn)
        pagination_bar.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        evidence_layout.addLayout(pagination_bar)

        self.sub_tabs.addTab(evidence_tab, "Evidence")
        self.load_evidence()

    def setup_legal_tab(self):
        legal_tab = QWidget()
        legal_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        legal_layout = QVBoxLayout(legal_tab)
        legal_layout.setContentsMargins(4, 4, 4, 4)
        legal_layout.setSpacing(4)

        # Toolbar for legal with visible buttons
        self.legal_toolbar = QToolBar()
        self.legal_toolbar.setMovable(False)
        self.legal_toolbar.setIconSize(self.legal_toolbar.iconSize())
        legal_layout.addWidget(self.legal_toolbar)

        add_legal_act = QAction("Add Legal Process", self)
        add_legal_act.triggered.connect(self.add_legal_process)
        self.legal_toolbar.addAction(add_legal_act)

        update_legal_act = QAction("Update Selected Process", self)
        update_legal_act.triggered.connect(self.update_legal_process)
        self.legal_toolbar.addAction(update_legal_act)

        delete_legal_act = QAction("Delete Selected Process", self)
        delete_legal_act.triggered.connect(self.delete_legal_process)
        self.legal_toolbar.addAction(delete_legal_act)

        self.legal_table = QTableWidget(0, 9)
        self.legal_table.setHorizontalHeaderLabels([
            "ID", "Type", "Provider", "Submitted", "Due/Expires", "Received", "Analyzing", "Completed", "Status"
        ])
        self.legal_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.legal_table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.legal_table.setAlternatingRowColors(True)
        self.legal_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        legal_layout.addWidget(self.legal_table, stretch=1)

        self.sub_tabs.addTab(legal_tab, "Legal Processes")
        self.load_legal()

    def setup_leads_tab(self):
        leads_tab = QWidget()
        leads_layout = QVBoxLayout(leads_tab)

        # Toolbar for leads with visible buttons
        self.leads_toolbar = QToolBar()
        self.leads_toolbar.setMovable(False)
        self.leads_toolbar.setIconSize(self.leads_toolbar.iconSize())
        leads_layout.addWidget(self.leads_toolbar)

        add_lead_act = QAction("Add Lead", self)
        add_lead_act.triggered.connect(self.add_lead)
        self.leads_toolbar.addAction(add_lead_act)

        update_lead_act = QAction("Update Selected Lead", self)
        update_lead_act.triggered.connect(self.update_lead)
        self.leads_toolbar.addAction(update_lead_act)

        delete_lead_act = QAction("Delete Selected Lead", self)
        delete_lead_act.triggered.connect(self.delete_lead)
        self.leads_toolbar.addAction(delete_lead_act)

        self.leads_table = QTableWidget(0, 5)
        self.leads_table.setHorizontalHeaderLabels([
            "ID", "Name", "Description", "Source", "Completed"
        ])
        self.leads_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        leads_layout.addWidget(self.leads_table)

        self.sub_tabs.addTab(leads_tab, "Lead Tracker")
        self.load_leads()

    def load_report(self):
        html, appendices, pdf_hash = self.db.load_report(self.case_data['case_number'])
        # Note: Report content is now loaded in the separate ReportsWindow
        self.appendices = appendices
        if pdf_hash:
            self.hash_label.setText(f"Final PDF Hash (SHA-256):\n{pdf_hash}")
            self.saved_pdf_hash = pdf_hash

    def on_text_changed(self):
        # Simple audit on change
        self.audit.log_text_changed()

    def toggle_bold(self):
        cursor = self.editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontWeight(QFont.Bold if not fmt.fontWeight() == QFont.Bold else QFont.Normal)
        cursor.mergeCharFormat(fmt)
        self.editor.mergeCurrentCharFormat(fmt)

    def toggle_italic(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.editor.setCurrentCharFormat(fmt)

    def toggle_underline(self):
        fmt = self.editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.editor.setCurrentCharFormat(fmt)

    def insert_bullet_list(self):
        cursor = self.editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDisc)
        cursor.createList(list_format)

    def insert_numbered_list(self):
        cursor = self.editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDecimal)
        cursor.createList(list_format)

    def toggle_notes_bold(self):
        cursor = self.notes_editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontWeight(QFont.Bold if not fmt.fontWeight() == QFont.Bold else QFont.Normal)
        cursor.mergeCharFormat(fmt)
        self.notes_editor.mergeCurrentCharFormat(fmt)

    def toggle_notes_italic(self):
        fmt = self.notes_editor.currentCharFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        self.notes_editor.setCurrentCharFormat(fmt)

    def toggle_notes_underline(self):
        fmt = self.notes_editor.currentCharFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        self.notes_editor.setCurrentCharFormat(fmt)

    def insert_notes_bullet_list(self):
        cursor = self.notes_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDisc)
        cursor.createList(list_format)

    def insert_notes_numbered_list(self):
        cursor = self.notes_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.ListDecimal)
        cursor.createList(list_format)

    def load_template(self):
        TemplateManager(self).exec_()

    def export_pdf(self, finalize=False, markdown=False, pdf=True):
        # Existing PDF export logic (from original code)
        html_template = f"""
        <html>
        <head><meta charset="utf-8"></head>
        <body>
            {self.editor.toHtml()}
        </body>
        </html>
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"Report_{self.case_data['case_number']}_{timestamp}"
        pdf_path = os.path.join(self.case_dir, f"{base_name}.pdf")

        if pdf:
            try:
                if WEASYPRINT_AVAILABLE:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        HTML(string=html_template).write_pdf(pdf_path, presentational_hints=True)
                    pdf_hash = compute_sha256(pdf_path)
                else:
                    QMessageBox.warning(self, "PDF Export Disabled", "WeasyPrint is not available. PDF export features are disabled.")
                    return
                self.hash_label.setText(f"Final PDF Hash (SHA-256):\n{pdf_hash}")
                self.saved_pdf_hash = pdf_hash

                if finalize:
                    self.db.save_report(self.case_data, self.editor.toHtml(), self.appendices, pdf_hash)
                    self.audit.log_pdf_finalized(pdf_path, pdf_hash)

                QMessageBox.information(self, "Success", f"PDF saved: {pdf_path}\nHash: {pdf_hash}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"PDF generation failed:\n{str(e)}")

    def add_evidence_item(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Evidence Item")
        form = QFormLayout(dlg)

        evidence_item_number_edit = QLineEdit()
        evidence_item_number_edit.setPlaceholderText("e.g., E001")
        form.addRow("Evidence Item Number:", evidence_item_number_edit)

        type_combo = QComboBox()
        type_combo.addItems(["physical", "digital"])
        form.addRow("Type:", type_combo)

        # Physical fields
        physical_description_edit = QTextEdit()
        physical_description_edit.setMaximumHeight(60)
        physical_description_edit.setPlaceholderText("Describe the physical evidence...")
        form.addRow("Physical Description:", physical_description_edit)

        # Password field
        password_edit = QLineEdit()
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setPlaceholderText("Password (if applicable)")
        form.addRow("Password:", password_edit)

        # Digital fields
        digital_make_edit = QLineEdit()
        digital_make_edit.setPlaceholderText("e.g., Samsung")
        form.addRow("Make:", digital_make_edit)

        digital_model_edit = QLineEdit()
        digital_model_edit.setPlaceholderText("e.g., Galaxy S21")
        form.addRow("Model:", digital_model_edit)

        digital_type_combo = QComboBox()
        digital_type_combo.addItems(["hard drive", "computer", "laptop", "SD card", "USB Drive", "DVD/CD", "Mobile Phone/Tablet", "IOT", "Other"])
        form.addRow("Type:", digital_type_combo)

        digital_sn_edit = QLineEdit()
        digital_sn_edit.setPlaceholderText("Serial Number")
        form.addRow("SN#:", digital_sn_edit)

        digital_storage_size_edit = QLineEdit()
        digital_storage_size_edit.setPlaceholderText("e.g., 256GB")
        form.addRow("Storage Size:", digital_storage_size_edit)

        # Initially hide digital fields, show physical and password
        digital_make_edit.setVisible(False)
        digital_model_edit.setVisible(False)
        digital_type_combo.setVisible(False)
        digital_sn_edit.setVisible(False)
        digital_storage_size_edit.setVisible(False)
        physical_description_edit.setVisible(True)
        password_edit.setVisible(True)

        def on_type_changed():
            is_digital = type_combo.currentText() == "digital"
            digital_make_edit.setVisible(is_digital)
            digital_model_edit.setVisible(is_digital)
            digital_type_combo.setVisible(is_digital)
            digital_sn_edit.setVisible(is_digital)
            digital_storage_size_edit.setVisible(is_digital)
            physical_description_edit.setVisible(True)  # Always visible

        type_combo.currentTextChanged.connect(on_type_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            evidence_item_number = evidence_item_number_edit.text().strip()
            item_type = type_combo.currentText()
            password = password_edit.text().strip()
            if not evidence_item_number:
                QMessageBox.warning(self, "Error", "Evidence Item Number is required!")
                return

            if item_type == "physical":
                physical_description = physical_description_edit.toPlainText().strip()
                success = self.db.add_evidence(
                    self.case_data['case_number'],
                    evidence_item_number,
                    item_type,
                    physical_description=physical_description,
                    password=password
                )
            else:  # digital
                digital_make = digital_make_edit.text().strip()
                digital_model = digital_model_edit.text().strip()
                digital_type = digital_type_combo.currentText()
                digital_sn = digital_sn_edit.text().strip()
                digital_storage_size = digital_storage_size_edit.text().strip()
                success = self.db.add_evidence(
                    self.case_data['case_number'],
                    evidence_item_number,
                    item_type,
                    digital_make=digital_make,
                    digital_model=digital_model,
                    digital_type=digital_type,
                    digital_sn=digital_sn,
                    digital_storage_size=digital_storage_size,
                    password=password
                )

            if success:
                self.load_evidence()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_evidence_added(evidence_item_number, item_type)
                QMessageBox.information(self, "Success", f"Evidence item {evidence_item_number} added!")
            else:
                QMessageBox.critical(self, "Error", "Failed to add evidence item.")

    def _evidence_prev_page(self):
        if self._evidence_page > 0:
            self._evidence_page -= 1
            self.load_evidence()

    def _evidence_next_page(self):
        self._evidence_page += 1
        self.load_evidence()

    def load_evidence(self):
        self.evidence_table.setRowCount(0)
        if not self.db.conn:
            # Server mode - placeholder
            return
        else:
            page_size = self._evidence_page_size
            offset = self._evidence_page * page_size
            cursor = self.db.conn.execute('''
                SELECT id, evidence_item_number, item_type, physical_description, digital_make, digital_model, digital_type, digital_sn, digital_storage_size, password, imaging_status
                FROM evidence_items WHERE case_number = ?
                LIMIT ? OFFSET ?
            ''', (self.case_data['case_number'], page_size, offset))
            rows = cursor.fetchall()
            # Update pagination controls
            total_cursor = self.db.conn.execute(
                'SELECT COUNT(*) FROM evidence_items WHERE case_number = ?',
                (self.case_data['case_number'],)
            )
            total = total_cursor.fetchone()[0]
            total_pages = max(1, (total + page_size - 1) // page_size)
            if self._evidence_page >= total_pages:
                self._evidence_page = max(0, total_pages - 1)
                offset = self._evidence_page * page_size
                cursor = self.db.conn.execute('''
                    SELECT id, evidence_item_number, item_type, physical_description, digital_make, digital_model, digital_type, digital_sn, digital_storage_size, password, imaging_status
                    FROM evidence_items WHERE case_number = ?
                    LIMIT ? OFFSET ?
                ''', (self.case_data['case_number'], page_size, offset))
                rows = cursor.fetchall()
            self._evidence_page_label.setText(f"Page {self._evidence_page + 1} / {total_pages}")
            self._evidence_prev_btn.setEnabled(self._evidence_page > 0)
            self._evidence_next_btn.setEnabled(self._evidence_page < total_pages - 1)
            for row in rows:
                row_position = self.evidence_table.rowCount()
                self.evidence_table.insertRow(row_position)
                self.evidence_table.setItem(row_position, 0, QTableWidgetItem(str(row['id'])))
                self.evidence_table.setItem(row_position, 1, QTableWidgetItem(row['evidence_item_number'] or ''))
                self.evidence_table.setItem(row_position, 2, QTableWidgetItem(row['item_type'] or ''))
                # Details: physical_description for physical, empty for digital
                details = row['physical_description'] if row['item_type'] == 'physical' else ''
                self.evidence_table.setItem(row_position, 3, QTableWidgetItem(details))
                self.evidence_table.setItem(row_position, 4, QTableWidgetItem(row['digital_make'] or ''))
                self.evidence_table.setItem(row_position, 5, QTableWidgetItem(row['digital_model'] or ''))
                self.evidence_table.setItem(row_position, 6, QTableWidgetItem(row['digital_type'] or ''))
                self.evidence_table.setItem(row_position, 7, QTableWidgetItem(row['digital_sn'] or ''))
                self.evidence_table.setItem(row_position, 8, QTableWidgetItem(row['digital_storage_size'] or ''))
                self.evidence_table.setItem(row_position, 9, QTableWidgetItem(row['password'] or ''))
                status_item = QTableWidgetItem(row['imaging_status'] or '')
                self.evidence_table.setItem(row_position, 10, status_item)

                # Apply custom colors
                status_key = f"evidence_{row['imaging_status']}" if row['imaging_status'] else "default_status"
                color_config = self.status_colors.get(status_key, {})
                if color_config:
                    bg_color = QColor(color_config.get('bg', '#f7f8fa'))
                    text_color = _contrast_text(bg_color)
                    bold = color_config.get('bold', False)
                else:
                    # Default color coding for evidence
                    if row['imaging_status'] == 'imaged':
                        bg_color = QColor('#28a745')  # green
                    elif row['imaging_status'] == 'not_imaged':
                        bg_color = QColor('#ffc107')  # yellow
                    else:
                        bg_color = QColor('#6c757d')  # grey
                    text_color = _contrast_text(bg_color)
                    bold = False

                for col in range(11):
                    item = self.evidence_table.item(row_position, col)
                    if item:
                        item.setBackground(bg_color)
                        item.setForeground(text_color)
                        font = item.font()
                        font.setBold(bold)
                        item.setFont(font)
            self.evidence_table.update()

    def add_legal_process(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Legal Process")
        form = QFormLayout(dlg)

        type_combo = QComboBox()
        type_combo.addItems(["preservation", "subpoena", "warrant"])
        provider_edit = QLineEdit()
        submission_date_edit = QDateTimeEdit()
        submission_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        submission_date_edit.setCalendarPopup(True)
        due_date_edit = QDateTimeEdit()
        due_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        due_date_edit.setCalendarPopup(True)
        expiration_date_edit = QDateTimeEdit()
        expiration_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        expiration_date_edit.setCalendarPopup(True)
        received_date_edit = QDateTimeEdit()
        received_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        received_date_edit.setCalendarPopup(True)
        analysis_start_date_edit = QDateTimeEdit()
        analysis_start_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        analysis_start_date_edit.setCalendarPopup(True)
        completed_date_edit = QDateTimeEdit()
        completed_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        completed_date_edit.setCalendarPopup(True)
        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(100)
        ndr_checkbox = QCheckBox("Non-Disclosure Request - for Search Warrants")

        form.addRow("Type:", type_combo)
        form.addRow("Provider:", provider_edit)
        form.addRow("Submission Date:", submission_date_edit)
        form.addRow("Due Date:", due_date_edit)
        form.addRow("Expiration Date:", expiration_date_edit)
        form.addRow("Received Date:", received_date_edit)
        form.addRow("Analysis Start Date:", analysis_start_date_edit)
        form.addRow("Completed Date:", completed_date_edit)
        form.addRow("Notes:", notes_edit)
        form.addRow(ndr_checkbox)

        # Hide fields initially
        due_date_edit.setVisible(False)
        expiration_date_edit.setVisible(False)
        received_date_edit.setVisible(False)
        analysis_start_date_edit.setVisible(False)
        completed_date_edit.setVisible(False)
        ndr_checkbox.setVisible(False)

        # Show/hide fields based on process type
        def on_type_changed():
            process_type = type_combo.currentText()
            # Hide all optional fields first
            due_date_edit.setVisible(False)
            expiration_date_edit.setVisible(False)
            received_date_edit.setVisible(False)
            analysis_start_date_edit.setVisible(False)
            completed_date_edit.setVisible(False)
            ndr_checkbox.setVisible(False)

            if process_type == "preservation":
                expiration_date_edit.setVisible(True)
            elif process_type == "subpoena":
                due_date_edit.setVisible(True)
                analysis_start_date_edit.setVisible(True)
                completed_date_edit.setVisible(True)
            elif process_type == "warrant":
                received_date_edit.setVisible(True)
                analysis_start_date_edit.setVisible(True)
                due_date_edit.setVisible(True)
                ndr_checkbox.setVisible(True)

        type_combo.currentTextChanged.connect(on_type_changed)
        on_type_changed()  # Initial call to set visibility

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            process_type = type_combo.currentText()
            provider = provider_edit.text().strip()
            submission_date = submission_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if submission_date_edit.dateTime().isValid() else None
            due_date = due_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if due_date_edit.dateTime().isValid() else None
            expiration_date = expiration_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if expiration_date_edit.dateTime().isValid() else None
            received_date = received_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if received_date_edit.dateTime().isValid() else None
            analysis_start_date = analysis_start_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if analysis_start_date_edit.dateTime().isValid() else None
            completed_date = completed_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if completed_date_edit.dateTime().isValid() else None
            notes = notes_edit.toPlainText().strip()
            ndr = ndr_checkbox.isChecked() if type_combo.currentText() == "warrant" else False

            if not provider:
                QMessageBox.warning(self, "Error", "Provider is required!")
                return

            success = self.db.add_legal_process(
                self.case_data['case_number'],
                process_type,
                provider,
                submission_date,
                due_date,
                expiration_date,
                received_date,
                analysis_start_date,
                completed_date,
                notes,
                ndr
            )
            if success:
                QMessageBox.information(self, "Success", f"{process_type.capitalize()} process added!")
                self.load_legal()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_legal_process_added(process_type, provider)
            else:
                QMessageBox.critical(self, "Error", "Failed to add legal process.")

    def load_legal(self):
        self.legal_table.setRowCount(0)
        if not self.db.conn:
            # Server mode - placeholder
            return
        else:
            cursor = self.db.conn.execute('''
                SELECT id, process_type, provider, submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, status, ndr
                FROM legal_processes WHERE case_number = ?
            ''', (self.case_data['case_number'],))
            rows = cursor.fetchall()
            today = datetime.now()
            for row in rows:
                row_position = self.legal_table.rowCount()
                self.legal_table.insertRow(row_position)

                # ID
                self.legal_table.setItem(row_position, 0, QTableWidgetItem(str(row['id'])))

                # Type
                type_item = QTableWidgetItem(row['process_type'] or '')
                self.legal_table.setItem(row_position, 1, type_item)

                # Provider
                provider_item = QTableWidgetItem(row['provider'] or '')
                self.legal_table.setItem(row_position, 2, provider_item)

                # Submitted
                submitted_item = QTableWidgetItem(row['submission_date'] or '')
                self.legal_table.setItem(row_position, 3, submitted_item)

                # Due/Expires
                due_exp = ''
                if row['process_type'] == 'preservation':
                    due_exp = row['expiration_date'] or ''
                else:
                    due_exp = row['due_date'] or ''
                due_exp_item = QTableWidgetItem(due_exp)
                self.legal_table.setItem(row_position, 4, due_exp_item)

                # Received
                received_item = QTableWidgetItem(row['received_date'] or '')
                self.legal_table.setItem(row_position, 5, received_item)

                # Analyzing
                analyzing_item = QTableWidgetItem(row['analysis_start_date'] or '')
                self.legal_table.setItem(row_position, 6, analyzing_item)

                # Completed
                completed_item = QTableWidgetItem(row['completed_date'] or '')
                self.legal_table.setItem(row_position, 7, completed_item)

                # Status
                status_item = QTableWidgetItem(row['status'] or '')
                self.legal_table.setItem(row_position, 8, status_item)

                # Apply custom colors
                status_key = f"legal_{row['status']}" if row['status'] else "default_status"
                color_config = self.status_colors.get(status_key, {})
                bold = color_config.get('bold', False)

                # Default color coding if no custom colors
                if not color_config:
                    color = QColor('#28a745') if row['status'] in ['completed', 'no_longer_needed'] else QColor('#ffc107')
                    if row['process_type'] == 'preservation' and row['expiration_date']:
                        exp = datetime.fromisoformat(row['expiration_date'])
                        days_left = (exp - today).days
                        if days_left <= 0:
                            color = QColor('#dc3545')
                        elif days_left <= 10:
                            color = QColor('#fd7e14')
                    elif row['process_type'] in ['subpoena', 'warrant'] and row['due_date']:
                        due = datetime.fromisoformat(row['due_date'])
                        if due < today and row['status'] != 'completed':
                            color = QColor('#dc3545')
                    bg_color = color
                else:
                    bg_color = QColor(color_config.get('bg', '#f7f8fa'))
                text_color = _contrast_text(bg_color)

                for col in range(9):
                    item = self.legal_table.item(row_position, col)
                    if item:
                        item.setBackground(bg_color)
                        item.setForeground(text_color)
                        font = item.font()
                        font.setBold(bold)
                        item.setFont(font)

    def update_dashboard_metrics(self):
        # Update case status from database
        if not self.db.conn:
            # Server mode - placeholder, assume status is in case_data
            status = self.case_data.get('status', 'draft').capitalize()
        else:
            cursor = self.db.conn.execute('SELECT status FROM reports WHERE case_number = ?', (self.case_data['case_number'],))
            row = cursor.fetchone()
            status = row['status'].capitalize() if row else 'Draft'
        self.case_status_label.setText(f"Case Status: {status}")

        # Get evidence metrics
        if not self.db.conn:
            # Server mode - assume API provides details
            evidence_details = []  # Placeholder
            legal_details = []  # Placeholder
        else:
            evidence_details = self.db._local_get_evidence_details(self.case_data['case_number'])
            legal_details = self.db._local_get_legal_details(self.case_data['case_number'])

        # Evidence metrics
        total_evidence = len(evidence_details)
        imaged_count = sum(1 for e in evidence_details if e.get('imaged_date'))
        analyzed_count = sum(1 for e in evidence_details if e.get('analyzed_date'))
        self.evidence_metrics_label.setText(f"Evidence: {total_evidence} items ({imaged_count} imaged, {analyzed_count} analyzed)")

        # Legal metrics
        total_legal = len(legal_details)
        completed_count = sum(1 for l in legal_details if l.get('status') == 'completed')
        self.legal_metrics_label.setText(f"Legal: {total_legal} processes ({completed_count} completed)")

    def submit_for_approval(self):
        reply = QMessageBox.question(self, "Submit", "Submit report for supervisor approval?")
        if reply == QMessageBox.Yes:
            self.db.submit_case(self.case_data['case_number'])
            QMessageBox.information(self, "Submitted", "Report submitted for review.")
            self.submit_btn.setEnabled(False)
            self.update_dashboard_metrics()

    def approve_case(self):
        reply = QMessageBox.question(self, "Approve", "Approve this report?")
        if reply == QMessageBox.Yes:
            self.db.approve_case(self.case_data['case_number'])
            QMessageBox.information(self, "Approved", "Report approved.")
            self.update_dashboard_metrics()

    def reject_case(self):
        comments, ok = QInputDialog.getMultiLineText(self, "Reject", "Enter rejection comments:")
        if ok and comments:
            self.db.reject_case(self.case_data['case_number'], comments)
            QMessageBox.information(self, "Rejected", "Report rejected with comments.")
            self.update_dashboard_metrics()

    def close_case(self):
        reply = QMessageBox.question(self, "Close Case", "Are you sure you want to close this case? This action cannot be undone.")
        if reply == QMessageBox.Yes:
            self.db.close_case(self.case_data['case_number'])
            QMessageBox.information(self, "Closed", "Case closed successfully.")
            self.update_dashboard_metrics()

    def open_notes(self):
        notes_window = NotesWindow(self.case_data, self.db, self.audit, self.current_user)
        notes_window.show()

    def open_reports(self):
        try:
            reports_window = ReportsWindow(self.case_data, self.db, self.audit, self.current_user)
            reports_window.show()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open reports window:\n{str(e)}")

    def add_lead(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Investigative Lead")
        form = QFormLayout(dlg)

        name_edit = QLineEdit()
        name_edit.setPlaceholderText("e.g., Check suspect's social media")
        form.addRow("Lead Name:", name_edit)

        description_edit = QTextEdit()
        description_edit.setMaximumHeight(100)
        description_edit.setPlaceholderText("Detailed description of the lead...")
        form.addRow("Description:", description_edit)

        source_edit = QLineEdit()
        source_edit.setPlaceholderText("e.g., Evidence analysis, witness statement")
        form.addRow("Source:", source_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            description = description_edit.toPlainText().strip()
            source = source_edit.text().strip()

            if not name:
                QMessageBox.warning(self, "Error", "Lead name is required!")
                return

            success = self.db.add_investigative_lead(
                self.case_data['case_number'],
                name,
                description,
                source
            )
            if success:
                QMessageBox.information(self, "Success", f"Lead '{name}' added!")
                self.load_leads()
                self.audit.log_lead_added(name, source)
            else:
                QMessageBox.critical(self, "Error", "Failed to add lead.")

    def load_leads(self):
        self.leads_table.setRowCount(0)
        if not self.db.conn:
            # Server mode - placeholder
            return
        else:
            leads = self.db.load_investigative_leads(self.case_data['case_number'])
            for lead in leads:
                row_position = self.leads_table.rowCount()
                self.leads_table.insertRow(row_position)

                # ID
                id_item = QTableWidgetItem(str(lead['id']))
                self.leads_table.setItem(row_position, 0, id_item)

                # Name
                name_item = QTableWidgetItem(lead['name'])
                self.leads_table.setItem(row_position, 1, name_item)

                # Description
                desc_item = QTableWidgetItem(lead['description'])
                self.leads_table.setItem(row_position, 2, desc_item)

                # Source
                source_item = QTableWidgetItem(lead['source'])
                self.leads_table.setItem(row_position, 3, source_item)

                # Completed checkbox
                completed_checkbox = QCheckBox()
                completed_checkbox.setChecked(lead['completed'])
                completed_checkbox.stateChanged.connect(lambda state, lid=lead['id']: self.toggle_lead_completion(lid, state == 2))
                self.leads_table.setCellWidget(row_position, 4, completed_checkbox)

                # Apply custom colors
                status_key = "leads_completed" if lead['completed'] else "leads_pending"
                color_config = self.status_colors.get(status_key, {})
                bold = color_config.get('bold', False)

                # Default color coding if no custom colors
                if not color_config:
                    if lead['completed']:
                        bg_color = QColor('#9e9e9e')
                    else:
                        bg_color = QColor('#f7f8fa')
                else:
                    bg_color = QColor(color_config.get('bg', '#f7f8fa'))
                text_color = _contrast_text(bg_color)

                for col in range(4):  # Set color for columns 0-3, skip the checkbox column
                    item = self.leads_table.item(row_position, col)
                    if item:
                        item.setBackground(bg_color)
                        item.setForeground(text_color)
                        font = item.font()
                        font.setBold(bold)
                        item.setFont(font)
            self.leads_table.update()

    def toggle_lead_completion(self, lead_id, completed):
        success = self.db.update_lead_completion(lead_id, completed)
        if success:
            self.audit.log_lead_completion_updated(lead_id, completed)
            self.load_leads()  # Reload to update color coding
        else:
            QMessageBox.critical(self, "Error", "Failed to update lead completion status.")

    def add_court_date(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Court Date")
        form = QFormLayout(dlg)

        date_type_combo = QComboBox()
        date_type_combo.addItems(["hearing", "trial", "sentencing"])
        form.addRow("Date Type:", date_type_combo)

        court_date_edit = QDateEdit()
        court_date_edit.setDate(QDate.currentDate())  # Default to today
        court_date_edit.setCalendarPopup(True)
        
        # Add "Today" button for quick entry
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: court_date_edit.setDate(QDate.currentDate()))
        date_layout = QHBoxLayout()
        date_layout.addWidget(court_date_edit)
        date_layout.addWidget(today_btn)
        form.addRow("Court Date:", date_layout)

        event_time_edit = QTimeEdit()
        form.addRow("Event Time:", event_time_edit)

        location_edit = QLineEdit()
        location_edit.setPlaceholderText("e.g., Courtroom 5, Downtown Courthouse")
        form.addRow("Location:", location_edit)

        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(100)
        notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            date_type = date_type_combo.currentText()
            court_date = court_date_edit.date().toString("yyyy-MM-dd") if court_date_edit.date().isValid() else None
            event_time = event_time_edit.time().toString("HH:mm") if event_time_edit.time().isValid() else None
            location = location_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not court_date:
                QMessageBox.warning(self, "Error", "Court date is required!")
                return

            success = self.db.add_court_date(
                self.case_data['case_number'],
                date_type,
                court_date,
                notes,
                event_time,
                location
            )
            if success:
                QMessageBox.information(self, "Success", f"{date_type.capitalize()} date added!")
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_court_date_added(date_type, court_date)
            else:
                QMessageBox.critical(self, "Error", "Failed to add court date.")

    def add_deposition_date(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Deposition Date")
        form = QFormLayout(dlg)

        deposition_date_edit = QDateEdit()
        deposition_date_edit.setDate(QDate.currentDate())  # Default to today
        deposition_date_edit.setCalendarPopup(True)
        
        # Add "Today" button for quick entry
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: deposition_date_edit.setDate(QDate.currentDate()))
        date_layout = QHBoxLayout()
        date_layout.addWidget(deposition_date_edit)
        date_layout.addWidget(today_btn)
        form.addRow("Deposition Date:", date_layout)

        event_time_edit = QTimeEdit()
        form.addRow("Event Time:", event_time_edit)

        location_edit = QLineEdit()
        location_edit.setPlaceholderText("e.g., Attorney's Office, Conference Room A")
        form.addRow("Location:", location_edit)

        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(100)
        notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            deposition_date = deposition_date_edit.date().toString("yyyy-MM-dd") if deposition_date_edit.date().isValid() else None
            event_time = event_time_edit.time().toString("HH:mm") if event_time_edit.time().isValid() else None
            location = location_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not deposition_date:
                QMessageBox.warning(self, "Error", "Deposition date is required!")
                return

            success = self.db.add_court_date(
                self.case_data['case_number'],
                "deposition",
                deposition_date,
                notes,
                event_time,
                location
            )
            if success:
                QMessageBox.information(self, "Success", "Deposition date added!")
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_court_date_added("deposition", deposition_date)
            else:
                QMessageBox.critical(self, "Error", "Failed to add deposition date.")

    def add_prosecution_visit(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Prosecution/Defense Visit")
        form = QFormLayout(dlg)

        visit_date_edit = QDateEdit()
        visit_date_edit.setDate(QDate.currentDate())  # Default to today
        visit_date_edit.setCalendarPopup(True)
        
        # Add "Today" button for quick entry
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: visit_date_edit.setDate(QDate.currentDate()))
        date_layout = QHBoxLayout()
        date_layout.addWidget(visit_date_edit)
        date_layout.addWidget(today_btn)
        form.addRow("Visit Date:", date_layout)

        event_time_edit = QTimeEdit()
        form.addRow("Event Time:", event_time_edit)

        location_edit = QLineEdit()
        location_edit.setPlaceholderText("e.g., Prosecutor's Office, Meeting Room 3")
        form.addRow("Location:", location_edit)

        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(100)
        notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            visit_date = visit_date_edit.date().toString("yyyy-MM-dd") if visit_date_edit.date().isValid() else None
            event_time = event_time_edit.time().toString("HH:mm") if event_time_edit.time().isValid() else None
            location = location_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not visit_date:
                QMessageBox.warning(self, "Error", "Visit date is required!")
                return

            success = self.db.add_court_date(
                self.case_data['case_number'],
                "prosecution_visit",
                visit_date,
                notes,
                event_time,
                location
            )
            if success:
                QMessageBox.information(self, "Success", "Prosecution/defense visit added!")
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_court_date_added("prosecution_visit", visit_date)
            else:
                QMessageBox.critical(self, "Error", "Failed to add prosecution/defense visit.")

    def add_case_date(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Case Date")
        form = QFormLayout(dlg)

        date_type_combo = QComboBox()
        date_type_combo.addItems(["hearing", "trial", "sentencing", "deposition", "legal visit"])
        form.addRow("Date Type:", date_type_combo)

        event_date_edit = QDateEdit()
        event_date_edit.setDate(QDate.currentDate())  # Default to today
        event_date_edit.setCalendarPopup(True)
        
        # Add "Today" button for quick entry
        today_btn = QPushButton("Today")
        today_btn.clicked.connect(lambda: event_date_edit.setDate(QDate.currentDate()))
        date_layout = QHBoxLayout()
        date_layout.addWidget(event_date_edit)
        date_layout.addWidget(today_btn)
        form.addRow("Event Date:", date_layout)

        event_time_edit = QTimeEdit()
        form.addRow("Event Time:", event_time_edit)

        location_edit = QLineEdit()
        location_edit.setPlaceholderText("e.g., Courtroom 5, Downtown Courthouse")
        form.addRow("Location:", location_edit)

        notes_edit = QTextEdit()
        notes_edit.setMaximumHeight(100)
        notes_edit.setPlaceholderText("Optional notes...")
        form.addRow("Notes:", notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            date_type = date_type_combo.currentText()
            event_date = event_date_edit.date().toString("yyyy-MM-dd") if event_date_edit.date().isValid() else None
            event_time = event_time_edit.time().toString("HH:mm") if event_time_edit.time().isValid() else None
            location = location_edit.text().strip()
            notes = notes_edit.toPlainText().strip()

            if not event_date:
                QMessageBox.warning(self, "Error", "Event date is required!")
                return

            # Map "legal visit" to "prosecution_visit" for database compatibility
            db_date_type = "prosecution_visit" if date_type == "legal visit" else date_type

            success = self.db.add_court_date(
                self.case_data['case_number'],
                db_date_type,
                event_date,
                notes,
                event_time,
                location
            )
            if success:
                QMessageBox.information(self, "Success", f"{date_type.capitalize()} date added!")
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_court_date_added(db_date_type, event_date)
            else:
                QMessageBox.critical(self, "Error", f"Failed to add {date_type} date.")

    def on_evidence_cell_changed(self, row, column):
        """Handle cell changes in the evidence table for inline editing"""
        if column == 0:  # ID column - don't allow editing
            return

        item = self.evidence_table.item(row, column)
        if not item:
            return

        new_value = item.text().strip()
        evidence_id = int(self.evidence_table.item(row, 0).text())

        # Map column to database field
        column_map = {
            1: 'evidence_item_number',
            2: 'item_type',
            3: 'physical_description',
            4: 'digital_make',
            5: 'digital_model',
            6: 'digital_type',
            7: 'digital_sn',
            8: 'digital_storage_size',
            9: 'password',
            10: 'imaging_status'
        }

        field = column_map.get(column)
        if not field:
            return

        # Update database
        success = self.db.update_evidence_field(evidence_id, field, new_value)
        if success:
            self.audit.log_evidence_updated(evidence_id, field, new_value)
            self.update_dashboard_metrics()
            if self.parent_window:
                self.parent_window.refresh_dashboard()
        else:
            QMessageBox.critical(self, "Error", f"Failed to update {field}.")
            # Reload to revert changes
            self.load_evidence()

    def update_evidence_item(self):
        """Update the selected evidence item with a dialog"""
        current_row = self.evidence_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an evidence item to update.")
            return

        evidence_id = int(self.evidence_table.item(current_row, 0).text())

        # Get current values
        cursor = self.db.conn.execute('''
            SELECT * FROM evidence_items WHERE id = ?
        ''', (evidence_id,))
        row = cursor.fetchone()
        if not row:
            QMessageBox.critical(self, "Error", "Evidence item not found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Update Evidence Item")
        form = QFormLayout(dlg)

        evidence_item_number_edit = QLineEdit(row['evidence_item_number'] or '')
        evidence_item_number_edit.setPlaceholderText("e.g., E001")
        form.addRow("Evidence Item Number:", evidence_item_number_edit)

        type_combo = QComboBox()
        type_combo.addItems(["physical", "digital"])
        type_combo.setCurrentText(row['item_type'] or 'physical')
        form.addRow("Type:", type_combo)

        # Physical fields
        physical_description_edit = QTextEdit(row['physical_description'] or '')
        physical_description_edit.setMaximumHeight(60)
        physical_description_edit.setPlaceholderText("Describe the physical evidence...")
        form.addRow("Physical Description:", physical_description_edit)

        # Password field
        password_edit = QLineEdit(row['password'] or '')
        password_edit.setEchoMode(QLineEdit.Password)
        password_edit.setPlaceholderText("Password (if applicable)")
        form.addRow("Password:", password_edit)

        # Digital fields
        digital_make_edit = QLineEdit(row['digital_make'] or '')
        digital_make_edit.setPlaceholderText("e.g., Samsung")
        form.addRow("Make:", digital_make_edit)

        digital_model_edit = QLineEdit(row['digital_model'] or '')
        digital_model_edit.setPlaceholderText("e.g., Galaxy S21")
        form.addRow("Model:", digital_model_edit)

        digital_type_combo = QComboBox()
        digital_type_combo.addItems(["hard drive", "computer", "laptop", "SD card", "USB Drive", "DVD/CD", "Mobile Phone/Tablet", "IOT", "Other"])
        digital_type_combo.setCurrentText(row['digital_type'] or '')
        form.addRow("Type:", digital_type_combo)

        digital_sn_edit = QLineEdit(row['digital_sn'] or '')
        digital_sn_edit.setPlaceholderText("Serial Number")
        form.addRow("SN#:", digital_sn_edit)

        digital_storage_size_edit = QLineEdit(row['digital_storage_size'] or '')
        digital_storage_size_edit.setPlaceholderText("e.g., 256GB")
        form.addRow("Storage Size:", digital_storage_size_edit)

        # Status combo
        status_combo = QComboBox()
        status_combo.addItems(["not_imaged", "imaged", "analyzed", "other"])
        status_combo.setCurrentText(row['imaging_status'] or 'not_imaged')
        form.addRow("Status:", status_combo)

        # Initially hide digital fields, show physical and password
        is_digital = row['item_type'] == 'digital'
        digital_make_edit.setVisible(is_digital)
        digital_model_edit.setVisible(is_digital)
        digital_type_combo.setVisible(is_digital)
        digital_sn_edit.setVisible(is_digital)
        digital_storage_size_edit.setVisible(is_digital)
        physical_description_edit.setVisible(True)  # Always visible
        password_edit.setVisible(True)

        def on_type_changed():
            is_digital = type_combo.currentText() == "digital"
            digital_make_edit.setVisible(is_digital)
            digital_model_edit.setVisible(is_digital)
            digital_type_combo.setVisible(is_digital)
            digital_sn_edit.setVisible(is_digital)
            digital_storage_size_edit.setVisible(is_digital)
            physical_description_edit.setVisible(True)  # Always visible

        type_combo.currentTextChanged.connect(on_type_changed)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            evidence_item_number = evidence_item_number_edit.text().strip()
            item_type = type_combo.currentText()
            password = password_edit.text().strip()
            imaging_status = status_combo.currentText()

            if not evidence_item_number:
                QMessageBox.warning(self, "Error", "Evidence Item Number is required!")
                return

            success = self.db.update_evidence_item(
                evidence_id,
                evidence_item_number=evidence_item_number,
                item_type=item_type,
                physical_description=physical_description_edit.toPlainText().strip() if item_type == "physical" else None,
                password=password,
                digital_make=digital_make_edit.text().strip() if item_type == "digital" else None,
                digital_model=digital_model_edit.text().strip() if item_type == "digital" else None,
                digital_type=digital_type_combo.currentText() if item_type == "digital" else None,
                digital_sn=digital_sn_edit.text().strip() if item_type == "digital" else None,
                digital_storage_size=digital_storage_size_edit.text().strip() if item_type == "digital" else None,
                imaging_status=imaging_status
            )

            if success:
                QMessageBox.information(self, "Success", f"Evidence item {evidence_item_number} updated!")
                self.load_evidence()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_evidence_updated(evidence_id, "full_update", evidence_item_number)
            else:
                QMessageBox.critical(self, "Error", "Failed to update evidence item.")

    def delete_evidence_item(self):
        """Delete the selected evidence item"""
        current_row = self.evidence_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select an evidence item to delete.")
            return

        evidence_id = int(self.evidence_table.item(current_row, 0).text())
        evidence_item_number = self.evidence_table.item(current_row, 1).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete evidence item '{evidence_item_number}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.db.delete_evidence_item(evidence_id)
            if success:
                QMessageBox.information(self, "Success", f"Evidence item {evidence_item_number} deleted!")
                self.load_evidence()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_evidence_deleted(evidence_id, evidence_item_number)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete evidence item.")

    def update_legal_process(self):
        """Update the selected legal process with a dialog"""
        current_row = self.legal_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a legal process to update.")
            return

        legal_id = int(self.legal_table.item(current_row, 0).text())

        # Get current values
        cursor = self.db.conn.execute('''
            SELECT * FROM legal_processes WHERE id = ?
        ''', (legal_id,))
        row = cursor.fetchone()
        if not row:
            QMessageBox.critical(self, "Error", "Legal process not found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Update Legal Process")
        form = QFormLayout(dlg)

        type_combo = QComboBox()
        type_combo.addItems(["preservation", "subpoena", "warrant"])
        type_combo.setCurrentText(row['process_type'] or 'preservation')
        form.addRow("Type:", type_combo)

        provider_edit = QLineEdit(row['provider'] or '')
        form.addRow("Provider:", provider_edit)

        submission_date_edit = QDateTimeEdit()
        submission_date_edit.setCalendarPopup(True)
        if row['submission_date']:
            try:
                dt = datetime.fromisoformat(row['submission_date'])
                submission_date_edit.setDateTime(dt)
            except ValueError:
                submission_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            submission_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Submission Date:", submission_date_edit)

        due_date_edit = QDateTimeEdit()
        due_date_edit.setCalendarPopup(True)
        if row['due_date']:
            try:
                dt = datetime.fromisoformat(row['due_date'])
                due_date_edit.setDateTime(dt)
            except ValueError:
                due_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            due_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Due Date:", due_date_edit)

        expiration_date_edit = QDateTimeEdit()
        expiration_date_edit.setCalendarPopup(True)
        if row['expiration_date']:
            try:
                dt = datetime.fromisoformat(row['expiration_date'])
                expiration_date_edit.setDateTime(dt)
            except ValueError:
                expiration_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            expiration_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Expiration Date:", expiration_date_edit)

        received_date_edit = QDateTimeEdit()
        received_date_edit.setCalendarPopup(True)
        if row['received_date']:
            try:
                dt = datetime.fromisoformat(row['received_date'])
                received_date_edit.setDateTime(dt)
            except ValueError:
                received_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            received_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Received Date:", received_date_edit)

        analysis_start_date_edit = QDateTimeEdit()
        analysis_start_date_edit.setCalendarPopup(True)
        if row['analysis_start_date']:
            try:
                dt = datetime.fromisoformat(row['analysis_start_date'])
                analysis_start_date_edit.setDateTime(dt)
            except ValueError:
                analysis_start_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            analysis_start_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Analysis Start Date:", analysis_start_date_edit)

        completed_date_edit = QDateTimeEdit()
        completed_date_edit.setCalendarPopup(True)
        if row['completed_date']:
            try:
                dt = datetime.fromisoformat(row['completed_date'])
                completed_date_edit.setDateTime(dt)
            except ValueError:
                completed_date_edit.setDateTime(QDateTime.currentDateTime())
        else:
            completed_date_edit.setDateTime(QDateTime.currentDateTime())  # Default to now
        form.addRow("Completed Date:", completed_date_edit)

        status_combo = QComboBox()
        status_combo.addItems(["pending", "in_progress", "completed", "no_longer_needed", "cancelled"])
        status_combo.setCurrentText(row['status'] or 'pending')
        form.addRow("Status:", status_combo)

        notes_edit = QTextEdit(row['notes'] or '')
        notes_edit.setMaximumHeight(100)
        form.addRow("Notes:", notes_edit)

        ndr_checkbox = QCheckBox("Non-Disclosure Request - for Search Warrants")
        ndr_checkbox.setChecked(row['ndr'] or False)
        form.addRow(ndr_checkbox)

        # Hide fields initially
        due_date_edit.setVisible(False)
        expiration_date_edit.setVisible(False)
        received_date_edit.setVisible(False)
        analysis_start_date_edit.setVisible(False)
        completed_date_edit.setVisible(False)
        ndr_checkbox.setVisible(False)

        # Show/hide fields based on process type
        def on_type_changed():
            process_type = type_combo.currentText()
            # Hide all optional fields first
            due_date_edit.setVisible(False)
            expiration_date_edit.setVisible(False)
            received_date_edit.setVisible(False)
            analysis_start_date_edit.setVisible(False)
            completed_date_edit.setVisible(False)
            ndr_checkbox.setVisible(False)

            if process_type == "preservation":
                expiration_date_edit.setVisible(True)
            elif process_type == "subpoena":
                due_date_edit.setVisible(True)
                analysis_start_date_edit.setVisible(True)
                completed_date_edit.setVisible(True)
            elif process_type == "warrant":
                received_date_edit.setVisible(True)
                analysis_start_date_edit.setVisible(True)
                due_date_edit.setVisible(True)
                ndr_checkbox.setVisible(True)

        type_combo.currentTextChanged.connect(on_type_changed)
        on_type_changed()  # Initial call to set visibility

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            process_type = type_combo.currentText()
            provider = provider_edit.text().strip()
            submission_date = submission_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if submission_date_edit.dateTime().isValid() else None
            due_date = due_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if due_date_edit.dateTime().isValid() else None
            expiration_date = expiration_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if expiration_date_edit.dateTime().isValid() else None
            received_date = received_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if received_date_edit.dateTime().isValid() else None
            analysis_start_date = analysis_start_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if analysis_start_date_edit.dateTime().isValid() else None
            completed_date = completed_date_edit.dateTime().toString("yyyy-MM-ddTHH:mm:ss") if completed_date_edit.dateTime().isValid() else None
            status = status_combo.currentText()
            notes = notes_edit.toPlainText().strip()
            ndr = ndr_checkbox.isChecked() if type_combo.currentText() == "warrant" else False

            if not provider:
                QMessageBox.warning(self, "Error", "Provider is required!")
                return

            success = self.db.update_legal_process(
                legal_id,
                process_type=process_type,
                provider=provider,
                submission_date=submission_date,
                due_date=due_date,
                expiration_date=expiration_date,
                received_date=received_date,
                analysis_start_date=analysis_start_date,
                completed_date=completed_date,
                status=status,
                notes=notes,
                ndr=ndr
            )
            if success:
                QMessageBox.information(self, "Success", f"Legal process updated!")
                self.load_legal()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_legal_process_updated(legal_id, process_type, provider)
            else:
                QMessageBox.critical(self, "Error", "Failed to update legal process.")

    def delete_legal_process(self):
        """Delete the selected legal process"""
        current_row = self.legal_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a legal process to delete.")
            return

        legal_id = int(self.legal_table.item(current_row, 0).text())
        provider = self.legal_table.item(current_row, 2).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete legal process for '{provider}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.db.delete_legal_process(legal_id)
            if success:
                QMessageBox.information(self, "Success", f"Legal process for {provider} deleted!")
                self.load_legal()
                self.update_dashboard_metrics()
                if self.parent_window:
                    self.parent_window.refresh_dashboard()
                self.audit.log_legal_process_deleted(legal_id, provider)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete legal process.")

    def update_lead(self):
        """Update the selected lead with a dialog"""
        current_row = self.leads_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a lead to update.")
            return

        lead_id = int(self.leads_table.item(current_row, 0).text())

        # Get current values
        cursor = self.db.conn.execute('''
            SELECT * FROM investigative_leads WHERE id = ?
        ''', (lead_id,))
        row = cursor.fetchone()
        if not row:
            QMessageBox.critical(self, "Error", "Lead not found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Update Investigative Lead")
        form = QFormLayout(dlg)

        name_edit = QLineEdit(row['name'] or '')
        name_edit.setPlaceholderText("e.g., Check suspect's social media")
        form.addRow("Lead Name:", name_edit)

        description_edit = QTextEdit(row['description'] or '')
        description_edit.setMaximumHeight(100)
        description_edit.setPlaceholderText("Detailed description of the lead...")
        form.addRow("Description:", description_edit)

        source_edit = QLineEdit(row['source'] or '')
        source_edit.setPlaceholderText("e.g., Evidence analysis, witness statement")
        form.addRow("Source:", source_edit)

        completed_checkbox = QCheckBox("Completed")
        completed_checkbox.setChecked(row['completed'] or False)
        form.addRow(completed_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            description = description_edit.toPlainText().strip()
            source = source_edit.text().strip()
            completed = completed_checkbox.isChecked()

            if not name:
                QMessageBox.warning(self, "Error", "Lead name is required!")
                return

            success = self.db.update_investigative_lead(
                lead_id,
                name=name,
                description=description,
                source=source,
                completed=completed
            )
            if success:
                QMessageBox.information(self, "Success", f"Lead '{name}' updated!")
                self.load_leads()
                self.audit.log_lead_updated(lead_id, name, completed)
            else:
                QMessageBox.critical(self, "Error", "Failed to update lead.")

    def delete_lead(self):
        """Delete the selected lead"""
        current_row = self.leads_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a lead to delete.")
            return

        lead_id = int(self.leads_table.item(current_row, 0).text())
        lead_name = self.leads_table.item(current_row, 1).text()

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete lead '{lead_name}'?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success = self.db.delete_investigative_lead(lead_id)
            if success:
                QMessageBox.information(self, "Success", f"Lead '{lead_name}' deleted!")
                self.load_leads()
                self.audit.log_lead_deleted(lead_id, lead_name)
            else:
                QMessageBox.critical(self, "Error", "Failed to delete lead.")

    def switch_to_evidence_tab(self):
        self.sub_tabs.setCurrentIndex(0)

    def switch_to_legal_tab(self):
        self.sub_tabs.setCurrentIndex(1)

    def switch_to_leads_tab(self):
        self.sub_tabs.setCurrentIndex(2)

    def update_view(self, view):
        # Hide legal tab if Examiner view
        for i in range(self.sub_tabs.count()):
            if self.sub_tabs.tabText(i) == "Legal Processes":
                self.sub_tabs.setTabVisible(i, view == "Investigator")
                break

        # Hide leads tab if Examiner view
        for i in range(self.sub_tabs.count()):
            if self.sub_tabs.tabText(i) == "Lead Tracker":
                self.sub_tabs.setTabVisible(i, view == "Investigator")
                break

        # Hide legal metrics label if Examiner view
        self.legal_metrics_label.setVisible(view == "Investigator")
