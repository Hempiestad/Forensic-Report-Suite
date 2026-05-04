#!/usr/bin/env python3
"""
Test script for chart generation functionality
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from main import generate_pie_chart

def test_generate_pie_chart():
    """Test the generate_pie_chart function"""
    print("Testing generate_pie_chart function...")

    # Test data
    test_data = {'Draft': 5, 'Submitted': 3, 'Approved': 2}

    # Generate chart
    pixmap = generate_pie_chart(test_data, "Test Chart")

    if pixmap:
        print("✓ Chart generated successfully")
        print(f"  Chart size: {pixmap.width()}x{pixmap.height()}")
        return True
    else:
        print("✗ Chart generation failed")
        return False

def test_empty_data():
    """Test with empty data"""
    print("Testing with empty data...")

    pixmap = generate_pie_chart({}, "Empty Chart")

    if pixmap is None:
        print("✓ Empty data handled correctly (returned None)")
        return True
    else:
        print("✗ Empty data should return None")
        return False

def test_zero_values():
    """Test with all zero values"""
    print("Testing with all zero values...")

    test_data = {'A': 0, 'B': 0, 'C': 0}
    pixmap = generate_pie_chart(test_data, "Zero Chart")

    if pixmap is None:
        print("✓ Zero values handled correctly (returned None)")
        return True
    else:
        print("✗ Zero values should return None")
        return False

if __name__ == "__main__":
    print("Running chart generation tests...\n")

    tests = [
        test_generate_pie_chart,
        test_empty_data,
        test_zero_values
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
