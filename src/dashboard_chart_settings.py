# dashboard_chart_settings.py
# Dashboard Chart Customization Settings Widget

import logging
from typing import Dict, Any, Optional
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox, 
    QComboBox, QLabel, QPushButton, QMessageBox, QSpinBox
)
from PyQt5.QtCore import pyqtSignal

logger = logging.getLogger(__name__)


class DashboardChartSettings(QWidget):
    """Widget for customizing dashboard charts"""
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent: Optional[QWidget] = None, current_settings: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(parent)
        self.current_settings = current_settings or self.get_default_settings()
        self.setup_ui()
        
    def setup_ui(self) -> None:
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Chart Visibility Group
        visibility_group = QGroupBox("Chart Visibility")
        visibility_layout = QVBoxLayout()
        
        self.chart_checkboxes: Dict[str, QCheckBox] = {}
        for chart_id, chart_name in [
            ('case_status', 'Case Status Chart'),
            ('evidence_status', 'Evidence Status Chart'),
            ('legal_processes', 'Legal Processes Chart'),
            ('leads_status', 'Leads Status Chart')
        ]:
            cb = QCheckBox(chart_name)
            visible_charts = self.current_settings.get('visible_charts', {})
            cb.setChecked(visible_charts.get(chart_id, True))
            cb.stateChanged.connect(self.on_settings_changed)
            visibility_layout.addWidget(cb)
            self.chart_checkboxes[chart_id] = cb
        
        visibility_group.setLayout(visibility_layout)
        layout.addWidget(visibility_group)
        
        # Chart Appearance Group
        appearance_group = QGroupBox("Chart Appearance")
        appearance_layout = QVBoxLayout()
        
        # Chart Type
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Chart Type:"))
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(['Pie', 'Bar', 'Donut', 'Horizontal Bar'])
        chart_type = self.current_settings.get('chart_type', 'pie')
        self.chart_type_combo.setCurrentText(chart_type.replace('_', ' ').title())
        self.chart_type_combo.currentTextChanged.connect(self.on_settings_changed)
        type_layout.addWidget(self.chart_type_combo)
        type_layout.addStretch()
        appearance_layout.addLayout(type_layout)
        
        # Size
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Chart Size:"))
        self.size_combo = QComboBox()
        self.size_combo.addItems(['Small', 'Medium', 'Large'])
        size = self.current_settings.get('size', 'medium')
        self.size_combo.setCurrentText(size.title())
        self.size_combo.currentTextChanged.connect(self.on_settings_changed)
        size_layout.addWidget(self.size_combo)
        size_layout.addStretch()
        appearance_layout.addLayout(size_layout)
        
        # Color Scheme
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color Scheme:"))
        self.color_scheme_combo = QComboBox()
        self.color_scheme_combo.addItems(['Professional', 'Colorblind-Friendly', 'Monochrome', 'Custom'])
        color_scheme = self.current_settings.get('color_scheme', 'professional')
        self.color_scheme_combo.setCurrentText(color_scheme.replace('_', ' ').title())
        self.color_scheme_combo.currentTextChanged.connect(self.on_settings_changed)
        self.color_scheme_combo.currentTextChanged.connect(self.on_color_scheme_changed)
        color_layout.addWidget(self.color_scheme_combo)
        
        # Custom Colors Button
        self.custom_colors_btn = QPushButton("Edit Colors...")
        self.custom_colors_btn.setEnabled(self.color_scheme_combo.currentText() == 'Custom')
        self.custom_colors_btn.clicked.connect(self.edit_custom_colors)
        color_layout.addWidget(self.custom_colors_btn)
        color_layout.addStretch()
        appearance_layout.addLayout(color_layout)
        
        # Display Options
        self.show_percentages_cb = QCheckBox("Show Percentages")
        self.show_percentages_cb.setChecked(self.current_settings.get('show_percentages', True))
        self.show_percentages_cb.stateChanged.connect(self.on_settings_changed)
        appearance_layout.addWidget(self.show_percentages_cb)
        
        self.show_labels_cb = QCheckBox("Show Labels")
        self.show_labels_cb.setChecked(self.current_settings.get('show_labels', True))
        self.show_labels_cb.stateChanged.connect(self.on_settings_changed)
        appearance_layout.addWidget(self.show_labels_cb)
        
        # Legend
        legend_layout = QHBoxLayout()
        self.show_legend_cb = QCheckBox("Show Legend")
        self.show_legend_cb.setChecked(self.current_settings.get('show_legend', True))
        self.show_legend_cb.stateChanged.connect(self.on_settings_changed)
        legend_layout.addWidget(self.show_legend_cb)
        
        legend_layout.addWidget(QLabel("Position:"))
        self.legend_position_combo = QComboBox()
        self.legend_position_combo.addItems(['Right', 'Bottom', 'Top', 'Left'])
        legend_pos = self.current_settings.get('legend_position', 'right')
        self.legend_position_combo.setCurrentText(legend_pos.title())
        self.legend_position_combo.currentTextChanged.connect(self.on_settings_changed)
        legend_layout.addWidget(self.legend_position_combo)
        legend_layout.addStretch()
        appearance_layout.addLayout(legend_layout)
        
        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)
        
        # Performance Group
        performance_group = QGroupBox("Performance")
        performance_layout = QVBoxLayout()
        
        refresh_layout = QHBoxLayout()
        refresh_layout.addWidget(QLabel("Auto-refresh interval:"))
        self.refresh_interval_combo = QComboBox()
        self.refresh_interval_combo.addItems(['Manual Only', '30 seconds', '1 minute', '5 minutes', '10 minutes'])
        current_interval = self.current_settings.get('auto_refresh_interval', 30)
        interval_map = {0: 'Manual Only', 30: '30 seconds', 60: '1 minute', 300: '5 minutes', 600: '10 minutes'}
        self.refresh_interval_combo.setCurrentText(interval_map.get(current_interval, '30 seconds'))
        self.refresh_interval_combo.currentTextChanged.connect(self.on_settings_changed)
        refresh_layout.addWidget(self.refresh_interval_combo)
        refresh_layout.addStretch()
        performance_layout.addLayout(refresh_layout)
        
        self.enable_caching_cb = QCheckBox("Enable chart caching (improves performance)")
        self.enable_caching_cb.setChecked(self.current_settings.get('enable_caching', True))
        self.enable_caching_cb.stateChanged.connect(self.on_settings_changed)
        performance_layout.addWidget(self.enable_caching_cb)
        
        performance_group.setLayout(performance_layout)
        layout.addWidget(performance_group)

        # Adaptive Layout Group
        adaptive_group = QGroupBox("Adaptive Layout")
        adaptive_layout = QVBoxLayout()

        self.adaptive_enabled_cb = QCheckBox("Enable adaptive chart sizing based on window width")
        self.adaptive_enabled_cb.setChecked(self.current_settings.get('adaptive_layout_enabled', True))
        self.adaptive_enabled_cb.stateChanged.connect(self.on_settings_changed)
        adaptive_layout.addWidget(self.adaptive_enabled_cb)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Layout Mode:"))
        self.adaptive_mode_combo = QComboBox()
        self.adaptive_mode_combo.addItems(['Balanced', 'Readable', 'Compact'])
        adaptive_mode = self.current_settings.get('adaptive_density', 'balanced')
        self.adaptive_mode_combo.setCurrentText(adaptive_mode.title())
        self.adaptive_mode_combo.currentTextChanged.connect(self.on_settings_changed)
        mode_layout.addWidget(self.adaptive_mode_combo)
        mode_layout.addStretch()
        adaptive_layout.addLayout(mode_layout)

        breakpoints = self.current_settings.get('adaptive_breakpoints', {})

        narrow_layout = QHBoxLayout()
        narrow_layout.addWidget(QLabel("Narrow width <"))
        self.narrow_breakpoint_spin = QSpinBox()
        self.narrow_breakpoint_spin.setRange(900, 2200)
        self.narrow_breakpoint_spin.setSingleStep(50)
        self.narrow_breakpoint_spin.setValue(int(breakpoints.get('narrow', 1280)))
        self.narrow_breakpoint_spin.valueChanged.connect(self.on_settings_changed)
        narrow_layout.addWidget(self.narrow_breakpoint_spin)
        narrow_layout.addWidget(QLabel("px"))
        narrow_layout.addStretch()
        adaptive_layout.addLayout(narrow_layout)

        medium_layout = QHBoxLayout()
        medium_layout.addWidget(QLabel("Medium width <"))
        self.medium_breakpoint_spin = QSpinBox()
        self.medium_breakpoint_spin.setRange(1100, 2800)
        self.medium_breakpoint_spin.setSingleStep(50)
        self.medium_breakpoint_spin.setValue(int(breakpoints.get('medium', 1700)))
        self.medium_breakpoint_spin.valueChanged.connect(self.on_settings_changed)
        medium_layout.addWidget(self.medium_breakpoint_spin)
        medium_layout.addWidget(QLabel("px"))
        medium_layout.addStretch()
        adaptive_layout.addLayout(medium_layout)

        adaptive_group.setLayout(adaptive_layout)
        layout.addWidget(adaptive_group)
        
        layout.addStretch()
        
    def on_settings_changed(self) -> None:
        """Emit signal when any setting changes"""
        self.settings_changed.emit(self.get_current_settings())
    
    def on_color_scheme_changed(self) -> None:
        """Handle color scheme combo box changes"""
        self.custom_colors_btn.setEnabled(
            self.color_scheme_combo.currentText() == 'Custom'
        )
    
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current settings from UI"""
        interval_map = {
            'Manual Only': 0,
            '30 seconds': 30,
            '1 minute': 60,
            '5 minutes': 300,
            '10 minutes': 600
        }
        
        chart_type = self.chart_type_combo.currentText().lower().replace(' ', '_')
        narrow_breakpoint = self.narrow_breakpoint_spin.value()
        medium_breakpoint = max(narrow_breakpoint + 120, self.medium_breakpoint_spin.value())
        
        return {
            'chart_type': chart_type,
            'size': self.size_combo.currentText().lower(),
            'color_scheme': self.color_scheme_combo.currentText().lower().replace(' ', '_').replace('-', '_'),
            'show_percentages': self.show_percentages_cb.isChecked(),
            'show_labels': self.show_labels_cb.isChecked(),
            'show_legend': self.show_legend_cb.isChecked(),
            'legend_position': self.legend_position_combo.currentText().lower(),
            'auto_refresh_interval': interval_map.get(self.refresh_interval_combo.currentText(), 30),
            'enable_caching': self.enable_caching_cb.isChecked(),
            'visible_charts': {
                chart_id: cb.isChecked()
                for chart_id, cb in self.chart_checkboxes.items()
            },
            'adaptive_layout_enabled': self.adaptive_enabled_cb.isChecked(),
            'adaptive_density': self.adaptive_mode_combo.currentText().lower(),
            'adaptive_breakpoints': {
                'narrow': narrow_breakpoint,
                'medium': medium_breakpoint,
            }
        }
    
    def edit_custom_colors(self) -> None:
        """Open dialog to edit custom color scheme"""
        QMessageBox.information(
            self, 
            "Custom Colors", 
            "Custom color editor will be available in a future update.\n\n"
            "For now, you can manually edit the 'custom_colors' array in config.json"
        )
    
    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """Return default chart settings"""
        return {
            'chart_type': 'pie',
            'size': 'medium',
            'color_scheme': 'professional',
            'show_percentages': True,
            'show_labels': True,
            'show_legend': True,
            'legend_position': 'right',
            'auto_refresh_interval': 30,
            'enable_caching': True,
            'visible_charts': {
                'case_status': True,
                'evidence_status': True,
                'legal_processes': True,
                'leads_status': True
            },
            'custom_colors': [],
            'adaptive_layout_enabled': True,
            'adaptive_density': 'balanced',
            'adaptive_breakpoints': {
                'narrow': 1280,
                'medium': 1700,
            }
        }
