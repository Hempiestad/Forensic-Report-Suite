"""
presentation/editors/ — word-processing editor components.

Phase 4: re-export root-level editor classes from this package.
"""
from word_processor import WordProcessor, FindReplaceDialog, AdvancedTableDialog
from base_editor import BaseEditor, StatusBar, StyleManager

__all__ = [
    "WordProcessor",
    "FindReplaceDialog",
    "AdvancedTableDialog",
    "BaseEditor",
    "StatusBar",
    "StyleManager",
]
