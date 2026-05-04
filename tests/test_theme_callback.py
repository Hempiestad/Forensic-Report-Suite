#!/usr/bin/env python3
"""
Test script for theme callback functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication, QWidget
from accessibility import ThemeManager
from main import generate_pie_chart

def test_theme_callback():
    """Test that theme callback is triggered and charts update"""
    print("Testing theme callback functionality...")

    # Create a minimal QApplication for testing
    app = QApplication(sys.argv)

    # Mock main window using QWidget
    class MockMainWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.refresh_called = False

        def refresh_dashboard(self):
            self.refresh_called = True
            print("✓ Dashboard refresh called")

    mock_window = MockMainWindow()

    # Create ThemeManager
    theme_manager = ThemeManager(app, mock_window)

    # Set callback
    theme_manager.set_theme_changed_callback(mock_window.refresh_dashboard)

    # Test theme changes
    themes = ['light', 'dark', 'high_contrast']
    for theme in themes:
        print(f"Switching to {theme} theme...")
        theme_manager.apply_theme(theme)
        if mock_window.refresh_called:
            print(f"✓ Callback triggered for {theme} theme")
            mock_window.refresh_called = False  # Reset for next test
        else:
            print(f"✗ Callback not triggered for {theme} theme")
            return False

    # Test chart background colors
    print("Testing chart background colors...")
    theme_bg_colors = {
        'light': '#f8f9fa',
        'dark': '#2d3748',
        'high_contrast': '#000000'
    }

    test_data = {'Test': 1}
    for theme, expected_bg in theme_bg_colors.items():
        print(f"Testing {theme} theme chart background...")
        # Note: We can't directly test the bgcolor in generate_pie_chart without modifying it
        # But we can verify the function runs without error
        pixmap = generate_pie_chart(test_data, f"{theme.capitalize()} Chart", bgcolor=expected_bg)
        if pixmap:
            print(f"✓ Chart generated for {theme} theme")
        else:
            print(f"✗ Chart generation failed for {theme} theme")
            return False

    return True

if __name__ == "__main__":
    print("Running theme callback tests...\n")

    if test_theme_callback():
        print("\n✓ All theme callback tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some theme callback tests failed!")
        sys.exit(1)
