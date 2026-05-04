# notification_settings.py
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, 
    QSpinBox, QLabel, QComboBox, QTimeEdit, QFormLayout, QPushButton,
    QDialog, QLineEdit, QDialogButtonBox, QMessageBox
)
from PyQt5.QtCore import pyqtSignal, QTime
from typing import Dict, Any


class NotificationSettings(QWidget):
    """Widget for configuring notification settings"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the notification settings UI"""
        layout = QVBoxLayout(self)
        
        # Global settings
        global_group = QGroupBox("Global Notification Settings")
        global_layout = QFormLayout()
        
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        self.enabled_check.stateChanged.connect(self.on_settings_changed)
        global_layout.addRow("Enable Notifications:", self.enabled_check)
        
        self.check_interval = QSpinBox()
        self.check_interval.setRange(60, 3600)
        self.check_interval.setValue(300)
        self.check_interval.setSuffix(" seconds")
        self.check_interval.valueChanged.connect(self.on_settings_changed)
        global_layout.addRow("Check Interval:", self.check_interval)
        
        self.show_system_tray = QCheckBox()
        self.show_system_tray.setChecked(False)
        self.show_system_tray.stateChanged.connect(self.on_settings_changed)
        global_layout.addRow("Show System Tray Icon:", self.show_system_tray)
        
        self.sound_enabled = QCheckBox()
        self.sound_enabled.setChecked(False)
        self.sound_enabled.stateChanged.connect(self.on_settings_changed)
        global_layout.addRow("Enable Sound:", self.sound_enabled)
        
        global_group.setLayout(global_layout)
        layout.addWidget(global_group)
        
        # Display settings
        display_group = QGroupBox("Display Settings")
        display_layout = QFormLayout()
        
        self.show_badge = QCheckBox()
        self.show_badge.setChecked(True)
        self.show_badge.stateChanged.connect(self.on_settings_changed)
        display_layout.addRow("Show Badge Count:", self.show_badge)
        
        self.popup_duration = QSpinBox()
        self.popup_duration.setRange(3, 60)
        self.popup_duration.setValue(10)
        self.popup_duration.setSuffix(" seconds")
        self.popup_duration.valueChanged.connect(self.on_settings_changed)
        display_layout.addRow("Popup Duration:", self.popup_duration)
        
        self.max_popups = QSpinBox()
        self.max_popups.setRange(1, 10)
        self.max_popups.setValue(3)
        self.max_popups.valueChanged.connect(self.on_settings_changed)
        display_layout.addRow("Max Simultaneous Popups:", self.max_popups)
        
        self.position_combo = QComboBox()
        self.position_combo.addItems(["Top Right", "Top Left", "Bottom Right", "Bottom Left"])
        self.position_combo.currentTextChanged.connect(self.on_settings_changed)
        display_layout.addRow("Popup Position:", self.position_combo)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        # Legal process notifications
        legal_group = QGroupBox("Legal Process Notifications")
        legal_layout = QVBoxLayout()
        
        self.legal_enabled = QCheckBox("Enable Legal Process Notifications")
        self.legal_enabled.setChecked(True)
        self.legal_enabled.stateChanged.connect(self.on_settings_changed)
        legal_layout.addWidget(self.legal_enabled)
        
        legal_form = QFormLayout()
        
        self.legal_due_date_days = QLabel("7, 3, 1")
        due_date_btn = QPushButton("Configure...")
        due_date_btn.clicked.connect(lambda: self.configure_warning_days('legal_due_date'))
        due_date_layout = QHBoxLayout()
        due_date_layout.addWidget(self.legal_due_date_days)
        due_date_layout.addWidget(due_date_btn)
        due_date_layout.addStretch()
        legal_form.addRow("Due Date Warning Days:", due_date_layout)
        
        self.legal_expiration_days = QLabel("30, 14, 7, 1")
        expiration_btn = QPushButton("Configure...")
        expiration_btn.clicked.connect(lambda: self.configure_warning_days('legal_expiration'))
        expiration_layout = QHBoxLayout()
        expiration_layout.addWidget(self.legal_expiration_days)
        expiration_layout.addWidget(expiration_btn)
        expiration_layout.addStretch()
        legal_form.addRow("Expiration Warning Days:", expiration_layout)
        
        self.legal_status_changes = QCheckBox()
        self.legal_status_changes.setChecked(True)
        self.legal_status_changes.stateChanged.connect(self.on_settings_changed)
        legal_form.addRow("Status Change Alerts:", self.legal_status_changes)
        
        self.legal_overdue = QCheckBox()
        self.legal_overdue.setChecked(True)
        self.legal_overdue.stateChanged.connect(self.on_settings_changed)
        legal_form.addRow("Overdue Alerts:", self.legal_overdue)
        
        legal_layout.addLayout(legal_form)
        legal_group.setLayout(legal_layout)
        layout.addWidget(legal_group)
        
        # Court date notifications
        court_group = QGroupBox("Court Date Notifications")
        court_layout = QVBoxLayout()
        
        self.court_enabled = QCheckBox("Enable Court Date Notifications")
        self.court_enabled.setChecked(True)
        self.court_enabled.stateChanged.connect(self.on_settings_changed)
        court_layout.addWidget(self.court_enabled)
        
        court_form = QFormLayout()
        
        self.court_warning_days = QLabel("30, 14, 7, 3, 1")
        court_btn = QPushButton("Configure...")
        court_btn.clicked.connect(lambda: self.configure_warning_days('court_warning'))
        court_layout_h = QHBoxLayout()
        court_layout_h.addWidget(self.court_warning_days)
        court_layout_h.addWidget(court_btn)
        court_layout_h.addStretch()
        court_form.addRow("Advance Warning Days:", court_layout_h)
        
        self.same_day_reminder = QCheckBox()
        self.same_day_reminder.setChecked(True)
        self.same_day_reminder.stateChanged.connect(self.on_settings_changed)
        court_form.addRow("Same Day Reminder:", self.same_day_reminder)
        
        self.reminder_time = QTimeEdit()
        self.reminder_time.setDisplayFormat("HH:mm")
        self.reminder_time.setTime(QTime(8, 0))
        self.reminder_time.timeChanged.connect(self.on_settings_changed)
        court_form.addRow("Reminder Time:", self.reminder_time)
        
        self.court_date_changed = QCheckBox()
        self.court_date_changed.setChecked(True)
        self.court_date_changed.stateChanged.connect(self.on_settings_changed)
        court_form.addRow("Date Changed Alerts:", self.court_date_changed)
        
        court_layout.addLayout(court_form)
        court_group.setLayout(court_layout)
        layout.addWidget(court_group)
        
        # Evidence notifications
        evidence_group = QGroupBox("Evidence Status Notifications")
        evidence_layout = QVBoxLayout()
        
        self.evidence_enabled = QCheckBox("Enable Evidence Notifications")
        self.evidence_enabled.setChecked(True)
        self.evidence_enabled.stateChanged.connect(self.on_settings_changed)
        evidence_layout.addWidget(self.evidence_enabled)
        
        evidence_form = QFormLayout()
        
        self.evidence_completion = QCheckBox()
        self.evidence_completion.setChecked(True)
        self.evidence_completion.stateChanged.connect(self.on_settings_changed)
        evidence_form.addRow("Completion Alerts:", self.evidence_completion)
        
        self.evidence_status_change = QCheckBox()
        self.evidence_status_change.setChecked(True)
        self.evidence_status_change.stateChanged.connect(self.on_settings_changed)
        evidence_form.addRow("Status Change Alerts:", self.evidence_status_change)
        
        self.evidence_new_item = QCheckBox()
        self.evidence_new_item.setChecked(False)
        self.evidence_new_item.stateChanged.connect(self.on_settings_changed)
        evidence_form.addRow("New Item Alerts:", self.evidence_new_item)
        
        evidence_layout.addLayout(evidence_form)
        evidence_group.setLayout(evidence_layout)
        layout.addWidget(evidence_group)
        
        layout.addStretch()
    
    def on_settings_changed(self):
        """Emit signal when settings change"""
        self.settings_changed.emit()
    
    def configure_warning_days(self, warning_type: str):
        """Open dialog to configure warning days"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Configure Warning Days")
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel("Enter comma-separated days (e.g., 7, 3, 1):"))
        
        edit = QLineEdit()
        if warning_type == 'legal_due_date':
            edit.setText(self.legal_due_date_days.text())
        elif warning_type == 'legal_expiration':
            edit.setText(self.legal_expiration_days.text())
        elif warning_type == 'court_warning':
            edit.setText(self.court_warning_days.text())
        
        layout.addWidget(edit)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        if dialog.exec_() == QDialog.Accepted:
            # Validate and set
            try:
                days_str = edit.text()
                days = [int(d.strip()) for d in days_str.split(',')]
                days.sort(reverse=True)
                days_str = ', '.join(map(str, days))
                
                if warning_type == 'legal_due_date':
                    self.legal_due_date_days.setText(days_str)
                elif warning_type == 'legal_expiration':
                    self.legal_expiration_days.setText(days_str)
                elif warning_type == 'court_warning':
                    self.court_warning_days.setText(days_str)
                
                self.on_settings_changed()
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Please enter valid comma-separated numbers.")
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current notification settings as dictionary"""
        position_map = {
            "Top Right": "top_right",
            "Top Left": "top_left",
            "Bottom Right": "bottom_right",
            "Bottom Left": "bottom_left"
        }
        
        return {
            "enabled": self.enabled_check.isChecked(),
            "check_interval_seconds": self.check_interval.value(),
            "show_system_tray": self.show_system_tray.isChecked(),
            "sound_enabled": self.sound_enabled.isChecked(),
            "sound_file": None,
            
            "display_settings": {
                "show_badge_count": self.show_badge.isChecked(),
                "popup_duration_seconds": self.popup_duration.value(),
                "max_popup_notifications": self.max_popups.value(),
                "position": position_map.get(self.position_combo.currentText(), "top_right")
            },
            
            "legal_notifications": {
                "enabled": self.legal_enabled.isChecked(),
                "due_date_warning_days": [int(d.strip()) for d in self.legal_due_date_days.text().split(',')],
                "expiration_warning_days": [int(d.strip()) for d in self.legal_expiration_days.text().split(',')],
                "status_changes": self.legal_status_changes.isChecked(),
                "overdue_alert": self.legal_overdue.isChecked()
            },
            
            "court_date_notifications": {
                "enabled": self.court_enabled.isChecked(),
                "advance_warning_days": [int(d.strip()) for d in self.court_warning_days.text().split(',')],
                "same_day_reminder": self.same_day_reminder.isChecked(),
                "same_day_reminder_time": self.reminder_time.time().toString("HH:mm"),
                "date_changed_alert": self.court_date_changed.isChecked()
            },
            
            "evidence_notifications": {
                "enabled": self.evidence_enabled.isChecked(),
                "completion_alert": self.evidence_completion.isChecked(),
                "status_change_alert": self.evidence_status_change.isChecked(),
                "new_evidence_alert": self.evidence_new_item.isChecked()
            }
        }
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings from dictionary"""
        self.enabled_check.setChecked(settings.get('enabled', True))
        self.check_interval.setValue(settings.get('check_interval_seconds', 300))
        self.show_system_tray.setChecked(settings.get('show_system_tray', False))
        self.sound_enabled.setChecked(settings.get('sound_enabled', False))
        
        display = settings.get('display_settings', {})
        self.show_badge.setChecked(display.get('show_badge_count', True))
        self.popup_duration.setValue(display.get('popup_duration_seconds', 10))
        self.max_popups.setValue(display.get('max_popup_notifications', 3))
        
        position_reverse_map = {
            "top_right": "Top Right",
            "top_left": "Top Left",
            "bottom_right": "Bottom Right",
            "bottom_left": "Bottom Left"
        }
        position = position_reverse_map.get(display.get('position', 'top_right'), "Top Right")
        self.position_combo.setCurrentText(position)
        
        legal = settings.get('legal_notifications', {})
        self.legal_enabled.setChecked(legal.get('enabled', True))
        self.legal_due_date_days.setText(', '.join(map(str, legal.get('due_date_warning_days', [7, 3, 1]))))
        self.legal_expiration_days.setText(', '.join(map(str, legal.get('expiration_warning_days', [30, 14, 7, 1]))))
        self.legal_status_changes.setChecked(legal.get('status_changes', True))
        self.legal_overdue.setChecked(legal.get('overdue_alert', True))
        
        court = settings.get('court_date_notifications', {})
        self.court_enabled.setChecked(court.get('enabled', True))
        self.court_warning_days.setText(', '.join(map(str, court.get('advance_warning_days', [30, 14, 7, 3, 1]))))
        self.same_day_reminder.setChecked(court.get('same_day_reminder', True))
        time_str = court.get('same_day_reminder_time', '08:00')
        hour, minute = map(int, time_str.split(':'))
        self.reminder_time.setTime(QTime(hour, minute))
        self.court_date_changed.setChecked(court.get('date_changed_alert', True))
        
        evidence = settings.get('evidence_notifications', {})
        self.evidence_enabled.setChecked(evidence.get('enabled', True))
        self.evidence_completion.setChecked(evidence.get('completion_alert', True))
        self.evidence_status_change.setChecked(evidence.get('status_change_alert', True))
        self.evidence_new_item.setChecked(evidence.get('new_evidence_alert', False))
    
    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """Get default notification settings"""
        return {
            "enabled": True,
            "check_interval_seconds": 300,
            "show_system_tray": False,
            "sound_enabled": False,
            "sound_file": None,
            
            "display_settings": {
                "show_badge_count": True,
                "popup_duration_seconds": 10,
                "max_popup_notifications": 3,
                "position": "top_right"
            },
            
            "legal_notifications": {
                "enabled": True,
                "due_date_warning_days": [7, 3, 1],
                "expiration_warning_days": [30, 14, 7, 1],
                "status_changes": True,
                "overdue_alert": True
            },
            
            "court_date_notifications": {
                "enabled": True,
                "advance_warning_days": [30, 14, 7, 3, 1],
                "same_day_reminder": True,
                "same_day_reminder_time": "08:00",
                "date_changed_alert": True
            },
            
            "evidence_notifications": {
                "enabled": True,
                "completion_alert": True,
                "status_change_alert": True,
                "new_evidence_alert": False
            }
        }
