# archived_cases_dialog.py
# Dialog for viewing, searching, and restoring archived cases

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QMessageBox, QHeaderView,
    QAbstractItemView, QTextEdit, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

logger = logging.getLogger(__name__)


class ArchivedCasesDialog(QDialog):
    """Dialog for viewing and managing archived cases"""
    
    def __init__(self, db_manager, current_user: str, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.current_user = current_user
        self.archived_cases: List[Dict[str, Any]] = []
        self.selected_case_number: Optional[str] = None
        
        self.setWindowTitle("Archived Cases")
        self.setMinimumSize(1000, 600)
        self.setup_ui()
        self.load_archived_cases()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Header with filters
        header_layout = QHBoxLayout()
        
        header_layout.addWidget(QLabel("Search:"))
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Case number or suspect name...")
        self.search_input.returnPressed.connect(self.load_archived_cases)
        header_layout.addWidget(self.search_input, 2)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(self.load_archived_cases)
        header_layout.addWidget(search_btn)
        
        header_layout.addWidget(QLabel("Year:"))
        
        self.year_filter = QComboBox()
        self.year_filter.addItem("All")
        current_year = datetime.now().year
        for year in range(current_year, current_year - 10, -1):
            self.year_filter.addItem(str(year))
        self.year_filter.currentTextChanged.connect(self.load_archived_cases)
        header_layout.addWidget(self.year_filter)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_archived_cases)
        header_layout.addWidget(refresh_btn)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Archived cases table
        self.cases_table = QTableWidget()
        self.cases_table.setColumnCount(7)
        self.cases_table.setHorizontalHeaderLabels([
            "Case Number", "Suspect", "Assigned To", "Agency", 
            "Archived Date", "Archived By", "Reason"
        ])
        header = self.cases_table.horizontalHeader()
        if header:
            for i in range(7):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(6, QHeaderView.Stretch)
        self.cases_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cases_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cases_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cases_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.cases_table.doubleClicked.connect(self.view_case_details)
        
        layout.addWidget(self.cases_table, 3)
        
        # Case details panel
        details_group = QGroupBox("Selected Case Details")
        details_layout = QFormLayout()
        
        self.detail_case_number = QLabel("-")
        details_layout.addRow("Case Number:", self.detail_case_number)
        
        self.detail_suspect = QLabel("-")
        details_layout.addRow("Suspect:", self.detail_suspect)
        
        self.detail_archived_date = QLabel("-")
        details_layout.addRow("Archived Date:", self.detail_archived_date)
        
        self.detail_archived_by = QLabel("-")
        details_layout.addRow("Archived By:", self.detail_archived_by)
        
        self.detail_reason = QTextEdit()
        self.detail_reason.setMaximumHeight(60)
        self.detail_reason.setReadOnly(True)
        details_layout.addRow("Reason:", self.detail_reason)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group, 1)
        
        # Status label
        self.status_label = QLabel("No archived cases")
        layout.addWidget(self.status_label)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.view_btn = QPushButton("📄 View Details")
        self.view_btn.clicked.connect(self.view_case_details)
        self.view_btn.setEnabled(False)
        button_layout.addWidget(self.view_btn)
        
        self.restore_btn = QPushButton("↩️ Restore Case")
        self.restore_btn.clicked.connect(self.restore_case)
        self.restore_btn.setEnabled(False)
        button_layout.addWidget(self.restore_btn)
        
        self.export_btn = QPushButton("💾 Export List")
        self.export_btn.clicked.connect(self.export_list)
        button_layout.addWidget(self.export_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(lambda: self.accept())
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def load_archived_cases(self):
        """Load archived cases from database with filters"""
        try:
            filters = {}
            
            # Apply search filter
            search_term = self.search_input.text().strip()
            if search_term:
                filters['search_term'] = search_term
            
            # Apply year filter
            year_text = self.year_filter.currentText()
            if year_text != "All":
                filters['year'] = year_text
            
            # Get archived cases from database
            self.archived_cases = self.db.get_archived_cases(filters)
            
            # Populate table
            self.cases_table.setRowCount(0)
            
            for case in self.archived_cases:
                row = self.cases_table.rowCount()
                self.cases_table.insertRow(row)
                
                # Case number
                self.cases_table.setItem(row, 0, QTableWidgetItem(case['case_number']))
                
                # Suspect
                suspect = case.get('suspect', 'N/A')
                self.cases_table.setItem(row, 1, QTableWidgetItem(suspect))
                
                # Assigned to
                self.cases_table.setItem(row, 2, QTableWidgetItem(case.get('assigned_to', 'N/A')))
                
                # Agency
                agency = case.get('agency', 'N/A')
                self.cases_table.setItem(row, 3, QTableWidgetItem(agency))
                
                # Archived date
                archived_date = case.get('archived_date', '')
                if archived_date:
                    try:
                        dt = datetime.fromisoformat(archived_date)
                        archived_date = dt.strftime('%Y-%m-%d %H:%M')
                    except ValueError as e:
                        logger.debug(f"Invalid date format '{archived_date}': {e}")
                self.cases_table.setItem(row, 4, QTableWidgetItem(archived_date))
                
                # Archived by
                self.cases_table.setItem(row, 5, QTableWidgetItem(case.get('archived_by', 'N/A')))
                
                # Reason
                reason = case.get('archive_reason', '') or ''
                self.cases_table.setItem(row, 6, QTableWidgetItem(reason))
            
            # Update status
            count = len(self.archived_cases)
            if count == 0:
                self.status_label.setText("No archived cases found")
            elif count == 1:
                self.status_label.setText("1 archived case")
            else:
                self.status_label.setText(f"{count} archived cases")
            
            logger.info(f"Loaded {count} archived cases")
            
        except Exception as e:
            logger.error(f"Failed to load archived cases: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load archived cases:\n{str(e)}")
    
    def on_selection_changed(self):
        """Handle selection change in the table"""
        selection_model = self.cases_table.selectionModel()
        if not selection_model:
            return
            
        selected_rows = selection_model.selectedRows()
        
        if selected_rows:
            row = selected_rows[0].row()
            item = self.cases_table.item(row, 0)
            if item:
                self.selected_case_number = item.text()
            else:
                self.selected_case_number = None
            
            # Find the case data
            case_data = next((c for c in self.archived_cases if c['case_number'] == self.selected_case_number), None)
            
            if case_data:
                self.detail_case_number.setText(case_data['case_number'])
                self.detail_suspect.setText(case_data.get('suspect', 'N/A'))
                
                archived_date = case_data.get('archived_date', '')
                if archived_date:
                    try:
                        dt = datetime.fromisoformat(archived_date)
                        archived_date = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except (ValueError, AttributeError, TypeError) as e:
                        logger.debug(f"Failed to format archived date: {e}")
                self.detail_archived_date.setText(archived_date)
                
                self.detail_archived_by.setText(case_data.get('archived_by', 'N/A'))
                self.detail_reason.setPlainText(case_data.get('archive_reason', '') or 'No reason provided')
            
            self.view_btn.setEnabled(True)
            self.restore_btn.setEnabled(True)
        else:
            self.selected_case_number = None
            self.view_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            
            self.detail_case_number.setText("-")
            self.detail_suspect.setText("-")
            self.detail_archived_date.setText("-")
            self.detail_archived_by.setText("-")
            self.detail_reason.setPlainText("")
    
    def view_case_details(self):
        """Open the case in read-only view"""
        if not self.selected_case_number:
            return
        
        QMessageBox.information(
            self,
            "View Case",
            f"Opening case {self.selected_case_number} in view-only mode.\n\n"
            "Note: Full case viewing will be implemented in the main application."
        )
        # TODO: Integrate with main window to open case tab in read-only mode
    
    def restore_case(self):
        """Restore the selected archived case"""
        if not self.selected_case_number:
            return
        
        reply = QMessageBox.question(
            self,
            "Restore Case",
            f"Are you sure you want to restore case {self.selected_case_number}?\n\n"
            "This will return the case to the active dashboard.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                success = self.db.restore_case(self.selected_case_number, self.current_user)
                
                if success:
                    QMessageBox.information(
                        self,
                        "Success",
                        f"Case {self.selected_case_number} has been restored to active status."
                    )
                    # Reload the list
                    self.load_archived_cases()
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to restore case {self.selected_case_number}.\n\n"
                        "Check the logs for details."
                    )
                    
            except Exception as e:
                logger.error(f"Failed to restore case: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"An error occurred while restoring the case:\n{str(e)}"
                )
    
    def export_list(self):
        """Export the archived cases list to CSV"""
        if not self.archived_cases:
            QMessageBox.information(self, "Export", "No archived cases to export.")
            return
        
        from PyQt5.QtWidgets import QFileDialog
        import csv
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Archived Cases",
            f"archived_cases_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Case Number", "Suspect", "Assigned To", "Agency",
                        "Archived Date", "Archived By", "Reason"
                    ])
                    
                    for case in self.archived_cases:
                        writer.writerow([
                            case['case_number'],
                            case.get('suspect', 'N/A'),
                            case.get('assigned_to', 'N/A'),
                            case.get('agency', 'N/A'),
                            case.get('archived_date', ''),
                            case.get('archived_by', 'N/A'),
                            case.get('archive_reason', '') or ''
                        ])
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Exported {len(self.archived_cases)} archived cases to:\n{filename}"
                )
                
            except Exception as e:
                logger.error(f"Failed to export archived cases: {e}")
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to export archived cases:\n{str(e)}"
                )
