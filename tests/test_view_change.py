#!/usr/bin/env python3
"""
Test script to verify chart cache clearing on view change
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import matplotlib
matplotlib.use('Agg')

def test_chart_cache_clear_on_view_change():
    """Test that chart cache is cleared when view changes"""
    print("Testing chart cache clearing on view change...")

    app = None
    try:
        from main import MainWindow
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()

        # Initially set to Investigator view
        initial_view = window.current_view
        print(f"Initial view: {initial_view}")

        # Simulate some chart caching by calling update_dashboard_charts
        cases = window.db.get_cases_with_details()
        window.update_dashboard_charts(cases)
        cache_size_before = len(window.chart_cache.cache)
        print(f"Cache size before view change: {cache_size_before}")

        # Change view to Examiner
        window.on_view_changed("Examiner")
        cache_size_after = len(window.chart_cache.cache)
        print(f"Cache size after view change: {cache_size_after}")

        # Verify cache was cleared
        if cache_size_after == 0:
            print("✓ Chart cache cleared successfully on view change")
            window.close()
            return True
        else:
            print("✗ Chart cache was not cleared on view change")
            window.close()
            return False

    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False
    finally:
        if app:
            app.quit()

if __name__ == "__main__":
    print("Running view change cache test...\n")

    if test_chart_cache_clear_on_view_change():
        print("\n✓ Test passed!")
        sys.exit(0)
    else:
        print("\n✗ Test failed!")
        sys.exit(1)
