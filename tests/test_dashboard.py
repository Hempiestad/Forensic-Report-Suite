#!/usr/bin/env python3
"""
Test script for dashboard functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Mock QApplication for testing
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend

def test_mainwindow_instantiation():
    """Test if MainWindow can be instantiated without errors"""
    print("Testing MainWindow instantiation...")

    app = None
    try:
        from main import MainWindow
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Set non-interactive mode
        app.setAttribute(Qt.AA_DontShowIconsInMenus, True)

        window = MainWindow()
        print("✓ MainWindow instantiated successfully")
        window.close()
        return True

    except Exception as e:
        print(f"✗ MainWindow instantiation failed: {e}")
        return False
    finally:
        if app:
            app.quit()

def test_dashboard_setup():
    """Test dashboard setup methods"""
    print("Testing dashboard setup...")

    app = None
    try:
        from main import MainWindow
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()

        # Test setup_dashboard
        window.setup_dashboard()
        print("✓ setup_dashboard completed")

        # Test refresh_dashboard
        window.refresh_dashboard()
        print("✓ refresh_dashboard completed")

        window.close()
        return True

    except Exception as e:
        print(f"✗ Dashboard setup failed: {e}")
        return False
    finally:
        if app:
            app.quit()

if __name__ == "__main__":
    print("Running dashboard tests...\n")

    tests = [
        test_mainwindow_instantiation,
        test_dashboard_setup
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("✗ Some tests failed!")
        sys.exit(1)
