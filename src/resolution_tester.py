"""
Resolution Testing Utility for Forensic Report Suite
Tests UI responsiveness across different screen resolutions and identifies issues.
"""

import sys
import json
import time
from datetime import datetime
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt5.QtCore import Qt, QSize, QRect, QPoint
from PyQt5.QtGui import QFont

# Common resolutions to test
RESOLUTION_PRESETS = {
    # Minimal/Mobile resolutions
    "600x480": (600, 480),
    "768x576": (768, 576),
    
    # Older monitors/netbooks
    "1024x768": (1024, 768),
    "1280x720": (1280, 720),  # HD
    
    # Standard desktop
    "1280x960": (1280, 960),
    "1366x768": (1366, 768),
    "1400x900": (1400, 900),  # Current minimum
    "1600x900": (1600, 900),
    "1920x1080": (1920, 1080),  # Full HD
    
    # High DPI / Large monitors
    "2560x1440": (2560, 1440),  # 2K
    "3840x2160": (3840, 2160),  # 4K
    
    # Ultra-wide
    "3440x1440": (3440, 1440),
    "5120x1440": (5120, 1440),
}


@dataclass
class UIElement:
    """Represents a UI element with position and size"""
    widget_type: str
    text: str
    x: int
    y: int
    width: int
    height: int
    parent_type: str
    visible: bool

    @property
    def rect(self) -> QRect:
        return QRect(self.x, self.y, self.width, self.height)

    def overlaps_with(self, other: 'UIElement') -> bool:
        """Check if this element overlaps with another"""
        return self.rect.intersects(other.rect)


@dataclass
class ResolutionTestResult:
    """Results from testing a single resolution"""
    resolution: str
    width: int
    height: int
    timestamp: str
    ui_elements: List[dict]
    overlaps: List[Dict[str, Any]]
    issues: List[str]
    warnings: List[str]
    success: bool
    
    def to_dict(self) -> dict:
        return asdict(self)


class UIOverlapDetector:
    """Detects overlapping UI elements in the application"""

    def __init__(self):
        self.elements: List[UIElement] = []
        self.overlaps: List[Tuple[UIElement, UIElement]] = []

    def scan_widgets(self, parent_widget) -> List[UIElement]:
        """Recursively scan all widgets and their geometry"""
        elements = []
        self._collect_widgets(parent_widget, elements, "root")
        self.elements = elements
        return elements

    def _collect_widgets(self, widget, elements: List[UIElement], parent_type: str):
        """Recursively collect widget information"""
        if not widget.isVisible():
            return

        # Get widget information
        geometry = widget.geometry()
        # Map to global coordinates if needed
        if hasattr(widget, 'mapToGlobal'):
            global_pos = widget.mapToGlobal(geometry.topLeft())
            x, y = global_pos.x(), global_pos.y()
        else:
            x, y = geometry.x(), geometry.y()

        widget_type = widget.__class__.__name__
        text = ""

        # Extract text from various widget types
        if hasattr(widget, 'text'):
            text = widget.text()
        elif hasattr(widget, 'title'):
            text = widget.title()
        elif hasattr(widget, 'toPlainText'):
            text = widget.toPlainText()[:50]  # First 50 chars

        element = UIElement(
            widget_type=widget_type,
            text=text.replace('\n', ' ')[:100],
            x=x,
            y=y,
            width=geometry.width(),
            height=geometry.height(),
            parent_type=parent_type,
            visible=widget.isVisible()
        )
        
        # Only add elements with meaningful dimensions
        if element.width > 0 and element.height > 0:
            elements.append(element)

        # Recursively process children
        if hasattr(widget, 'children'):
            for child in widget.children():
                if hasattr(child, 'geometry'):
                    self._collect_widgets(child, elements, widget_type)

    def detect_overlaps(self, min_area_threshold: int = 50) -> List[Tuple[UIElement, UIElement]]:
        """Find overlapping UI elements"""
        overlaps = []
        
        # Only check interactive elements (buttons, labels, etc.)
        interactive_types = (
            'QPushButton', 'QLabel', 'QLineEdit', 'QComboBox', 
            'QCheckBox', 'QRadioButton', 'QTableWidgetItem'
        )
        
        interactive = [e for e in self.elements if e.widget_type in interactive_types]
        
        for i, elem1 in enumerate(interactive):
            for elem2 in interactive[i+1:]:
                if elem1.overlaps_with(elem2):
                    # Check overlap area to filter out minor overlaps
                    overlap_rect = elem1.rect.intersected(elem2.rect)
                    overlap_area = overlap_rect.width() * overlap_rect.height()
                    
                    if overlap_area > min_area_threshold:
                        overlaps.append((elem1, elem2))
        
        self.overlaps = overlaps
        return overlaps

    def get_overlap_report(self) -> List[Dict[str, Any]]:
        """Generate a detailed overlap report"""
        report = []
        
        for elem1, elem2 in self.overlaps:
            overlap_rect = elem1.rect.intersected(elem2.rect)
            overlap_area = overlap_rect.width() * overlap_rect.height()
            
            report.append({
                'element1': {
                    'type': elem1.widget_type,
                    'text': elem1.text,
                    'position': f"({elem1.x}, {elem1.y})",
                    'size': f"{elem1.width}x{elem1.height}"
                },
                'element2': {
                    'type': elem2.widget_type,
                    'text': elem2.text,
                    'position': f"({elem2.x}, {elem2.y})",
                    'size': f"{elem2.width}x{elem2.height}"
                },
                'overlap_area': overlap_area,
                'severity': self._calculate_severity(overlap_area, elem1, elem2)
            })
        
        return report

    @staticmethod
    def _calculate_severity(overlap_area: int, elem1: UIElement, elem2: UIElement) -> str:
        """Calculate severity level of overlap"""
        max_area = min(elem1.width * elem1.height, elem2.width * elem2.height)
        percentage = (overlap_area / max_area * 100) if max_area > 0 else 0
        
        if percentage > 50:
            return "CRITICAL"
        elif percentage > 25:
            return "HIGH"
        elif percentage > 10:
            return "MEDIUM"
        else:
            return "LOW"


class ResolutionTester:
    """Main resolution testing engine"""

    def __init__(self, main_window_class, output_dir: str = "resolution_tests"):
        self.main_window_class = main_window_class
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.results: List[ResolutionTestResult] = []
        self.detector = UIOverlapDetector()

    def test_resolution(self, width: int, height: int, name: str) -> ResolutionTestResult:
        """Test the application at a specific resolution"""
        print(f"\nTesting resolution: {name} ({width}x{height})")
        
        try:
            # Create main window
            window = self.main_window_class()
            
            # Resize window to test resolution
            window.resize(width, height)
            window.move(0, 0)  # Move to top-left
            
            # Process events to ensure layout updates
            QApplication.processEvents()
            time.sleep(0.5)  # Brief pause for rendering
            
            # Scan for UI elements
            ui_elements = self.detector.scan_widgets(window)
            
            # Detect overlaps
            overlaps = self.detector.detect_overlaps()
            overlap_report = self.detector.get_overlap_report()
            
            # Generate issues and warnings
            issues = []
            warnings = []
            
            if overlaps:
                critical_overlaps = [o for o in overlap_report if o['severity'] == 'CRITICAL']
                high_overlaps = [o for o in overlap_report if o['severity'] == 'HIGH']
                
                if critical_overlaps:
                    issues.append(f"Critical overlaps detected: {len(critical_overlaps)} UI elements")
                if high_overlaps:
                    warnings.append(f"High severity overlaps: {len(high_overlaps)} UI elements")
            
            # Check for truncated text
            for elem in ui_elements:
                if elem.text and len(elem.text) > 30:
                    # Could be truncated (estimate)
                    estimated_text_width = len(elem.text) * 7  # Rough estimate
                    if estimated_text_width > elem.width:
                        warnings.append(
                            f"Possible text truncation: {elem.widget_type} "
                            f"'{elem.text[:30]}...'"
                        )
            
            # Check minimum size violations
            if width < 1400 or height < 900:
                issues.append(f"Width {width} or Height {height} below recommended minimum (1400x900)")
            
            # Clean up
            window.close()
            QApplication.processEvents()
            
            result = ResolutionTestResult(
                resolution=name,
                width=width,
                height=height,
                timestamp=datetime.now().isoformat(),
                ui_elements=[asdict(e) for e in ui_elements],
                overlaps=overlap_report,
                issues=issues,
                warnings=warnings,
                success=len(issues) == 0
            )
            
            self.results.append(result)
            return result
            
        except Exception as e:
            print(f"Error testing {name}: {str(e)}")
            return ResolutionTestResult(
                resolution=name,
                width=width,
                height=height,
                timestamp=datetime.now().isoformat(),
                ui_elements=[],
                overlaps=[],
                issues=[f"Exception during test: {str(e)}"],
                warnings=[],
                success=False
            )

    def run_all_tests(self, custom_resolutions: Optional[Dict[str, Tuple[int, int]]] = None) -> List[ResolutionTestResult]:
        """Run tests on all standard resolutions plus custom ones"""
        resolutions = RESOLUTION_PRESETS.copy()
        
        if custom_resolutions:
            resolutions.update(custom_resolutions)
        
        print(f"\n{'='*70}")
        print(f"Resolution Compatibility Testing")
        print(f"{'='*70}")
        print(f"Testing {len(resolutions)} resolution(s)...")
        
        for name, (width, height) in resolutions.items():
            self.test_resolution(width, height, name)
        
        return self.results

    def generate_report(self) -> str:
        """Generate a comprehensive test report"""
        report_lines = [
            "=" * 80,
            "RESOLUTION COMPATIBILITY TEST REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY",
            "-" * 80,
        ]
        
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        
        report_lines.extend([
            f"Total Resolutions Tested: {total}",
            f"Passed: {passed}",
            f"Failed/Issues: {total - passed}",
            f"Success Rate: {(passed/total*100):.1f}%",
            "",
        ])
        
        # Find min/max supported resolutions
        passing_results = [r for r in self.results if r.success]
        if passing_results:
            by_area = sorted(passing_results, key=lambda r: r.width * r.height)
            report_lines.extend([
                "MINIMUM SUPPORTED RESOLUTION:",
                f"  {by_area[0].resolution}: {by_area[0].width}x{by_area[0].height}",
                "",
                "MAXIMUM TESTED RESOLUTION:",
                f"  {by_area[-1].resolution}: {by_area[-1].width}x{by_area[-1].height}",
                "",
            ])
        
        # Detailed results
        report_lines.append("DETAILED RESULTS")
        report_lines.append("-" * 80)
        
        for result in sorted(self.results, key=lambda r: r.width * r.height):
            status = "✓ PASS" if result.success else "✗ FAIL"
            report_lines.append(
                f"\n{result.resolution} ({result.width}x{result.height}) - {status}"
            )
            
            if result.issues:
                report_lines.append("  ISSUES:")
                for issue in result.issues:
                    report_lines.append(f"    - {issue}")
            
            if result.warnings:
                report_lines.append("  WARNINGS:")
                for warning in result.warnings:
                    report_lines.append(f"    - {warning}")
            
            if result.overlaps:
                report_lines.append(f"  OVERLAPS: {len(result.overlaps)}")
                for overlap in result.overlaps[:3]:  # Show first 3
                    severity = overlap.get('severity', 'UNKNOWN')
                    elem1_text = overlap['element1']['text'][:20]
                    elem2_text = overlap['element2']['text'][:20]
                    report_lines.append(
                        f"    [{severity}] '{elem1_text}' overlaps "
                        f"'{elem2_text}'"
                    )
                if len(result.overlaps) > 3:
                    report_lines.append(
                        f"    ... and {len(result.overlaps) - 3} more overlaps"
                    )
        
        # Recommendations
        report_lines.extend([
            "",
            "",
            "RECOMMENDATIONS",
            "-" * 80,
        ])
        
        failed_small = [r for r in self.results if not r.success and r.width * r.height < 1400 * 900]
        failed_large = [r for r in self.results if not r.success and r.width * r.height >= 1400 * 900]
        
        if failed_small:
            report_lines.append(
                f"• Consider supporting smaller resolutions. {len(failed_small)} "
                "resolution(s) below minimum failed."
            )
        
        if failed_large:
            report_lines.append(
                f"• Investigate failures at larger resolutions ({len(failed_large)} "
                "resolution(s)). UI layout may not scale properly."
            )
        
        critical_overlaps_total = sum(
            sum(1 for o in r.overlaps if o.get('severity') == 'CRITICAL')
            for r in self.results
        )
        if critical_overlaps_total > 0:
            report_lines.append(
                f"• Critical overlaps found ({critical_overlaps_total} total). "
                "Review adaptive layouts and use responsive design patterns."
            )
        
        report_lines.extend([
            "",
            "TECHNICAL RECOMMENDATIONS:",
            "  1. Use layouts (QVBoxLayout, QHBoxLayout) instead of fixed positioning",
            "  2. Set minimum/maximum sizes for dialog windows",
            "  3. Use setSizePolicy() for better resizing behavior",
            "  4. Consider using splitters for resizable panes",
            "  5. Test with zoom/DPI scaling on high-resolution displays",
            "",
        ])
        
        return "\n".join(report_lines)

    def save_report(self, filename: str = "resolution_report.txt") -> Path:
        """Save the test report to a file"""
        report = self.generate_report()
        report_path = self.output_dir / filename
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"\nReport saved to: {report_path}")
        return report_path

    def save_json_results(self, filename: str = "resolution_results.json") -> Path:
        """Save detailed results as JSON"""
        json_path = self.output_dir / filename
        
        with open(json_path, 'w') as f:
            json.dump(
                [r.to_dict() for r in self.results],
                f,
                indent=2
            )
        
        print(f"JSON results saved to: {json_path}")
        return json_path

    def print_summary(self):
        """Print a quick summary to console"""
        print("\n" + "=" * 80)
        print("RESOLUTION TEST SUMMARY")
        print("=" * 80)
        
        passed = sum(1 for r in self.results if r.success)
        total = len(self.results)
        
        print(f"\nResults: {passed}/{total} passed")
        
        if passed < total:
            print("\nFailed resolutions:")
            for result in self.results:
                if not result.success:
                    print(f"  {result.resolution}: {', '.join(result.issues)}")
        
        passing = sorted([r for r in self.results if r.success], key=lambda r: r.width * r.height)
        if passing:
            print(f"\nSupported range: {passing[0].resolution} to {passing[-1].resolution}")


def main():
    """Main entry point for resolution testing"""
    from main import MainWindow
    
    # Create QApplication instance
    app = QApplication(sys.argv)
    
    # Create and run tester
    tester = ResolutionTester(MainWindow, output_dir="resolution_tests")
    
    # Optionally add custom resolutions
    custom_resolutions = {
        "1200x800": (1200, 800),  # Slightly below minimum
        "1300x850": (1300, 850),  # Just below minimum
        "1400x900": (1400, 900),  # Current minimum
    }
    
    results = tester.run_all_tests(custom_resolutions)
    
    # Generate and save reports
    report = tester.generate_report()
    print("\n" + report)
    
    tester.save_report()
    tester.save_json_results()
    tester.print_summary()


if __name__ == "__main__":
    main()
