"""
Interactive Resolution Tester
Allows manual testing of specific resolutions with visual overlay of UI issues
"""

import sys
import os
from typing import Optional, List
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QSpinBox, QComboBox, QTextEdit, 
    QGroupBox, QGridLayout, QMessageBox, QStatusBar
)
from PyQt5.QtCore import Qt, QRect, QSize, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QFont, QTextCursor
from PyQt5.QtWidgets import QDialog, QDialogButtonBox


class OverlayWidget(QWidget):
    """Overlay widget that draws rectangles around UI elements to visualize them"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.elements_to_draw = []
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
    def set_elements(self, elements):
        """Set the elements to draw"""
        self.elements_to_draw = elements
        self.update()
    
    def paintEvent(self, event):
        """Draw rectangles around UI elements"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        for i, elem in enumerate(self.elements_to_draw):
            # Alternate colors for visibility
            if i % 3 == 0:
                color = QColor(255, 0, 0, 80)  # Red
            elif i % 3 == 1:
                color = QColor(0, 255, 0, 80)  # Green
            else:
                color = QColor(0, 0, 255, 80)  # Blue
            
            painter.fillRect(elem['rect'], color)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawRect(elem['rect'])
            
            # Draw label
            label_text = elem['type'][:15]
            painter.setPen(QPen(QColor(255, 255, 255)))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(elem['rect'], Qt.AlignTop | Qt.AlignLeft, label_text)


class ResolutionTestingWindow(QMainWindow):
    """Interactive resolution testing tool"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resolution Testing Tool - Forensic Suite")
        self.setGeometry(100, 100, 900, 700)
        
        # Create main widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Control panel
        control_group = QGroupBox("Resolution Control Panel")
        control_layout = QGridLayout()
        
        # Width control
        control_layout.addWidget(QLabel("Width:"), 0, 0)
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setMinimum(600)
        self.width_spinbox.setMaximum(5120)
        self.width_spinbox.setValue(1400)
        control_layout.addWidget(self.width_spinbox, 0, 1)
        
        # Height control
        control_layout.addWidget(QLabel("Height:"), 0, 2)
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setMinimum(480)
        self.height_spinbox.setMaximum(2160)
        self.height_spinbox.setValue(900)
        control_layout.addWidget(self.height_spinbox, 0, 3)
        
        # Preset resolutions
        control_layout.addWidget(QLabel("Presets:"), 1, 0)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "600x480 (Minimal)",
            "1024x768 (XGA)",
            "1280x720 (HD)",
            "1366x768 (Common)",
            "1400x900 (Current Min)",
            "1600x900",
            "1920x1080 (Full HD)",
            "2560x1440 (2K)",
            "3840x2160 (4K)",
            "3440x1440 (Ultrawide)",
        ])
        self.preset_combo.currentIndexChanged.connect(self.on_preset_selected)
        control_layout.addWidget(self.preset_combo, 1, 1, 1, 3)
        
        # Test button
        self.test_button = QPushButton("Test This Resolution")
        self.test_button.clicked.connect(self.test_resolution)
        self.test_button.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; "
            "padding: 8px; font-weight: bold; border-radius: 4px; }"
        )
        control_layout.addWidget(self.test_button, 2, 0, 1, 4)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Results display
        results_group = QGroupBox("Test Results & Recommendations")
        results_layout = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier", 9))
        results_layout.addWidget(self.results_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        # Status bar
        self.statusBar().showMessage("Ready to test. Select a resolution and click 'Test This Resolution'")
        
        # Presets mapping
        self.presets_map = {
            0: (600, 480),
            1: (1024, 768),
            2: (1280, 720),
            3: (1366, 768),
            4: (1400, 900),
            5: (1600, 900),
            6: (1920, 1080),
            7: (2560, 1440),
            8: (3840, 2160),
            9: (3440, 1440),
        }
        
        self.test_window = None
    
    def on_preset_selected(self, index):
        """Update spinboxes when preset is selected"""
        if index in self.presets_map:
            w, h = self.presets_map[index]
            self.width_spinbox.setValue(w)
            self.height_spinbox.setValue(h)
    
    def test_resolution(self):
        """Test the selected resolution"""
        width = self.width_spinbox.value()
        height = self.height_spinbox.value()
        
        try:
            from main import MainWindow
            
            # Close previous test window if open
            if self.test_window:
                self.test_window.close()
            
            self.statusBar().showMessage(f"Opening test window at {width}x{height}...")
            
            # Create test window
            self.test_window = MainWindow()
            self.test_window.resize(width, height)
            self.test_window.move(500, 100)
            self.test_window.setWindowTitle(f"Forensic Suite - Testing {width}x{height}")
            
            # Process events to ensure layout
            QApplication.processEvents()
            
            # Analyze the window
            results = self._analyze_window(self.test_window, width, height)
            
            self.test_window.show()
            self._display_results(results, width, height)
            
            self.statusBar().showMessage(f"Test window open at {width}x{height}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open test window:\n{str(e)}")
            self.statusBar().showMessage("Error during test")
    
    def _analyze_window(self, window, width, height):
        """Analyze the window for issues"""
        results = {
            'resolution': f"{width}x{height}",
            'issues': [],
            'warnings': [],
            'ui_count': 0,
        }
        
        # Check against minimum size
        if width < 1400 or height < 900:
            results['issues'].append(
                f"⚠ Resolution {width}x{height} is below recommended minimum (1400x900)"
            )
        
        # Check for very small resolutions
        if width < 800:
            results['issues'].append(
                f"✗ Resolution {width}x{height} is too small for proper UI display"
            )
        
        # Count widgets
        ui_count = self._count_widgets(window)
        results['ui_count'] = ui_count
        
        if ui_count == 0:
            results['warnings'].append("No UI elements detected (window may not be fully loaded)")
        
        # Collect all child widgets
        visible_widgets = self._collect_visible_widgets(window)
        results['widget_count'] = len(visible_widgets)
        
        # Check for overlaps (simplified)
        overlaps = self._detect_basic_overlaps(visible_widgets)
        if overlaps:
            results['issues'].append(
                f"✗ Detected {len(overlaps)} potential UI element overlap(s)"
            )
            for overlap in overlaps[:3]:
                results['issues'].append(f"  - {overlap}")
        
        # Check for visibility issues
        visibility_issues = self._check_visibility(window, width, height)
        results['warnings'].extend(visibility_issues)
        
        return results
    
    def _count_widgets(self, widget):
        """Count all widgets recursively"""
        count = 1
        if hasattr(widget, 'children'):
            for child in widget.children():
                if hasattr(child, 'geometry'):
                    count += self._count_widgets(child)
        return count
    
    def _collect_visible_widgets(self, widget):
        """Collect all visible widgets with geometry"""
        widgets = []
        if widget.isVisible() and hasattr(widget, 'geometry'):
            geom = widget.geometry()
            if geom.width() > 0 and geom.height() > 0:
                widgets.append({
                    'type': widget.__class__.__name__,
                    'rect': geom,
                    'text': self._get_widget_text(widget),
                })
        
        if hasattr(widget, 'children'):
            for child in widget.children():
                if hasattr(child, 'geometry'):
                    widgets.extend(self._collect_visible_widgets(child))
        
        return widgets
    
    def _get_widget_text(self, widget):
        """Get text from widget if available"""
        if hasattr(widget, 'text'):
            return widget.text()[:30]
        elif hasattr(widget, 'title'):
            return widget.title()[:30]
        return ""
    
    def _detect_basic_overlaps(self, widgets):
        """Simple overlap detection"""
        overlaps = []
        for i, w1 in enumerate(widgets):
            for w2 in widgets[i+1:]:
                if w1['rect'].intersects(w2['rect']):
                    overlap = w1['rect'].intersected(w2['rect'])
                    area = overlap.width() * overlap.height()
                    if area > 100:  # Only report significant overlaps
                        overlaps.append(
                            f"{w1['type']} overlaps {w2['type']} ({area}px²)"
                        )
        return overlaps
    
    def _check_visibility(self, window, width, height):
        """Check for visibility and sizing issues"""
        issues = []
        
        # Check if window fits on assumed screen
        if width < 1280:
            issues.append(
                "⚠ Very narrow resolution - text truncation likely"
            )
        
        if height < 720:
            issues.append(
                "⚠ Very short resolution - vertical scrolling required"
            )
        
        return issues
    
    def _display_results(self, results, width, height):
        """Display analysis results in the text area"""
        lines = [
            "=" * 70,
            f"RESOLUTION TEST RESULTS: {results['resolution']}",
            "=" * 70,
            "",
            f"Window Dimensions: {width}x{height}",
            f"Total UI Elements Found: {results.get('widget_count', 'N/A')}",
            "",
        ]
        
        if results['issues']:
            lines.append("⚠ ISSUES DETECTED:")
            for issue in results['issues']:
                lines.append(f"  {issue}")
            lines.append("")
        else:
            lines.append("✓ No major issues detected")
            lines.append("")
        
        if results['warnings']:
            lines.append("⚠ WARNINGS:")
            for warning in results['warnings']:
                lines.append(f"  {warning}")
            lines.append("")
        
        lines.extend([
            "RECOMMENDATIONS:",
            "",
            "✓ Current Minimum: 1400x900",
            "  - All UI should be fully visible and functional",
            "",
            "For Better Support:",
            "  • Test with different window manager configurations",
            "  • Check tooltips and popup menus near screen edges",
            "  • Verify that all dialog windows fit on screen",
            "  • Test with zoom/DPI scaling on high-res displays",
            "  • Ensure text remains readable at small distances",
            "",
            "Technical Guidance:",
            "  • Use layouts instead of absolute positioning",
            "  • Implement dynamic text wrapping",
            "  • Use setSizePolicy() for responsive widgets",
            "  • Test tab order and keyboard navigation",
            "  • Consider responsive column widths in tables",
        ])
        
        self.results_text.setText("\n".join(lines))


def main():
    """Run the interactive resolution tester"""
    app = QApplication(sys.argv)
    
    # Style the application
    app.setStyle('Fusion')
    
    tester = ResolutionTestingWindow()
    tester.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
