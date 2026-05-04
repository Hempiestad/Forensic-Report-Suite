"""
presentation/tabs/ — thin tab widgets delegating to application services.

Phase 4: re-export root-level tab classes from this package so that future
callers can import from presentation.tabs without changing call sites.
"""
from case_tab import CaseTab
from notes_tab import NotesTab, NotesWindow
from reports_tab import ReportsTab, ReportsWindow

__all__ = ["CaseTab", "NotesTab", "NotesWindow", "ReportsTab", "ReportsWindow"]
