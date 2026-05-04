import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QColorDialog,
    QCheckBox, QFormLayout, QDialogButtonBox, QGroupBox, QScrollArea, QWidget
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class StatusColorDialog(QDialog):
    def __init__(self, current_colors, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customize Status Colors")
        self.setModal(True)
        self.resize(600, 500)

        self.current_colors = current_colors.copy()
        self.status_keys = [
            "evidence_not_imaged", "evidence_imaged", "evidence_analyzed",
            "legal_pending", "legal_completed",
            "leads_pending", "leads_completed",
            "default_status"
        ]
        self.status_labels = {
            "evidence_not_imaged": "Evidence: Not Imaged",
            "evidence_imaged": "Evidence: Imaged",
            "evidence_analyzed": "Evidence: Analyzed",
            "legal_pending": "Legal: Pending",
            "legal_completed": "Legal: Completed",
            "leads_pending": "Leads: Pending",
            "leads_completed": "Leads: Completed",
            "default_status": "Default Status"
        }

        layout = QVBoxLayout(self)

        # Scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)

        self.color_buttons = {}
        self.bold_checkboxes = {}

        for key in self.status_keys:
            group = QGroupBox(self.status_labels[key])
            group_layout = QVBoxLayout(group)

            # Background color
            bg_layout = QHBoxLayout()
            bg_layout.addWidget(QLabel("Background:"))
            bg_button = QPushButton()
            bg_button.setFixedSize(50, 30)
            bg_color = QColor(self.current_colors.get(key, {}).get('bg', '#6c757d'))
            bg_button.setStyleSheet(f"background-color: {bg_color.name()}; border: 1px solid #000;")
            bg_button.clicked.connect(lambda checked, k=key, t='bg': self.choose_color(k, t))
            self.color_buttons[f"{key}_bg"] = bg_button
            bg_layout.addWidget(bg_button)
            bg_layout.addStretch()
            group_layout.addLayout(bg_layout)

            # Text color
            text_layout = QHBoxLayout()
            text_layout.addWidget(QLabel("Text:"))
            text_button = QPushButton()
            text_button.setFixedSize(50, 30)
            text_color = QColor(self.current_colors.get(key, {}).get('text', '#000000'))
            text_button.setStyleSheet(f"background-color: {text_color.name()}; border: 1px solid #000;")
            text_button.clicked.connect(lambda checked, k=key, t='text': self.choose_color(k, t))
            self.color_buttons[f"{key}_text"] = text_button
            text_layout.addWidget(text_button)

            # Bold checkbox
            bold_cb = QCheckBox("Bold")
            bold_cb.setChecked(self.current_colors.get(key, {}).get('bold', False))
            self.bold_checkboxes[key] = bold_cb
            text_layout.addWidget(bold_cb)
            text_layout.addStretch()
            group_layout.addLayout(text_layout)

            form_layout.addRow(group)

        scroll.setWidget(form_widget)
        layout.addWidget(scroll)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.RestoreDefaults)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        layout.addWidget(buttons)

    def choose_color(self, key, color_type):
        current_color = QColor(self.current_colors.get(key, {}).get(color_type, '#000000'))
        color = QColorDialog.getColor(current_color, self, f"Choose {color_type} color for {self.status_labels[key]}")
        if color.isValid():
            self.current_colors[key][color_type] = color.name()
            button = self.color_buttons[f"{key}_{color_type}"]
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #000;")

    def restore_defaults(self):
        self.current_colors = {
            "evidence_not_imaged": {"bg": "#ffc107", "text": "#000000", "bold": False},
            "evidence_imaged": {"bg": "#28a745", "text": "#000000", "bold": False},
            "evidence_analyzed": {"bg": "#17a2b8", "text": "#000000", "bold": False},
            "legal_pending": {"bg": "#ffc107", "text": "#000000", "bold": False},
            "legal_completed": {"bg": "#28a745", "text": "#000000", "bold": False},
            "leads_pending": {"bg": "#ffc107", "text": "#000000", "bold": False},
            "leads_completed": {"bg": "#28a745", "text": "#000000", "bold": False},
            "default_status": {"bg": "#6c757d", "text": "#ffffff", "bold": False}
        }
        self.update_buttons()

    def update_buttons(self):
        for key in self.status_keys:
            for color_type in ['bg', 'text']:
                color = QColor(self.current_colors.get(key, {}).get(color_type, '#000000'))
                button = self.color_buttons[f"{key}_{color_type}"]
                button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #000;")
            self.bold_checkboxes[key].setChecked(self.current_colors.get(key, {}).get('bold', False))

    def get_colors(self):
        for key in self.status_keys:
            self.current_colors[key]['bold'] = self.bold_checkboxes[key].isChecked()
        return self.current_colors
