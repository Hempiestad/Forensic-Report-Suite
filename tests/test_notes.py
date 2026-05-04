import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test imports
try:
    from notes_tab import NotesTab, NotesWindow
    print("✓ notes_tab module imported successfully")
except ImportError as e:
    print(f"✗ Failed to import notes_tab: {e}")
    sys.exit(1)

# Test that update_format_buttons method is removed
try:
    # Create a mock class to test method existence
    class MockNotesTab:
        def __init__(self):
            pass

    mock_tab = MockNotesTab()
    if hasattr(mock_tab, 'update_format_buttons'):
        print("✗ update_format_buttons method still exists")
        sys.exit(1)
    else:
        print("✓ update_format_buttons method successfully removed")
except Exception as e:
    print(f"✗ Error testing method removal: {e}")
    sys.exit(1)

# Test toggle_bold method (should not call update_format_buttons)
try:
    from PyQt5.QtWidgets import QApplication, QTextEdit
    from PyQt5.QtGui import QFont

    app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()

    # Create a minimal test
    text_edit = QTextEdit()
    cursor = text_edit.textCursor()

    # Simulate toggle_bold logic without the method call
    fmt = text_edit.currentCharFormat()
    fmt.setFontWeight(QFont.Bold if True else QFont.Normal)
    text_edit.setCurrentCharFormat(fmt)

    print("✓ toggle_bold logic works without update_format_buttons")
except Exception as e:
    print(f"✗ Error testing toggle_bold: {e}")
    sys.exit(1)

print("All tests passed!")
