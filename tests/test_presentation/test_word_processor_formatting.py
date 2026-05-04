"""
tests/presentation/test_word_processor_formatting.py

Unit tests for FormatPainterService and FormatState.
No QApplication required — all logic is pure Python.
"""
from __future__ import annotations

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from presentation.services.format_painter_service import FormatPainterService, FormatState


# ---------------------------------------------------------------------------
# FormatState
# ---------------------------------------------------------------------------

class TestFormatState:
    def test_default_values(self):
        fs = FormatState()
        assert fs.bold is False
        assert fs.italic is False
        assert fs.underline is False
        assert fs.strikethrough is False
        assert fs.font_family == "Arial"
        assert fs.font_size == 12.0
        assert fs.color == "#000000"
        assert fs.background_color == ""
        assert fs.alignment == "left"
        assert fs.list_style == ""

    def test_round_trip_to_from_dict(self):
        fs = FormatState(
            bold=True,
            italic=True,
            font_family="Courier New",
            font_size=14.0,
            color="#ff0000",
            background_color="#ffffff",
            alignment="center",
            line_spacing=2.0,
            list_style="numbered",
        )
        d = fs.to_dict()
        restored = FormatState.from_dict(d)
        assert restored.bold is True
        assert restored.italic is True
        assert restored.font_family == "Courier New"
        assert restored.font_size == 14.0
        assert restored.color == "#ff0000"
        assert restored.alignment == "center"
        assert restored.line_spacing == 2.0
        assert restored.list_style == "numbered"

    def test_from_dict_partial_keys(self):
        """from_dict should fill missing keys with defaults."""
        fs = FormatState.from_dict({"bold": True})
        assert fs.bold is True
        assert fs.italic is False
        assert fs.font_family == "Arial"

    def test_from_dict_type_coercion(self):
        """Numeric types are coerced correctly."""
        fs = FormatState.from_dict({"font_size": "16", "bold": 1})
        assert fs.font_size == 16.0
        assert isinstance(fs.font_size, float)
        assert fs.bold is True

    def test_to_dict_contains_all_keys(self):
        d = FormatState().to_dict()
        expected_keys = {
            "bold", "italic", "underline", "strikethrough",
            "font_family", "font_size", "color", "background_color",
            "alignment", "line_spacing", "space_before", "space_after",
            "list_style",
        }
        assert expected_keys == set(d.keys())


# ---------------------------------------------------------------------------
# FormatPainterService — basic capture / paste
# ---------------------------------------------------------------------------

class TestFormatPainterServiceBasic:
    def _fmt(self, **kw) -> FormatState:
        return FormatState(**kw)

    def test_initially_inactive_no_format(self):
        svc = FormatPainterService()
        assert svc.is_active is False
        assert svc.has_format is False

    def test_capture_activates_painter(self):
        svc = FormatPainterService()
        svc.capture(self._fmt(bold=True))
        assert svc.is_active is True
        assert svc.has_format is True

    def test_get_format_returns_copy(self):
        svc = FormatPainterService()
        original = self._fmt(bold=True, italic=True, font_size=14.0)
        svc.capture(original)
        result = svc.get_format()
        assert result is not None
        assert result.bold is True
        assert result.italic is True
        assert result.font_size == 14.0

    def test_get_format_returns_independent_copy(self):
        """Mutating the returned FormatState must not affect the stored one."""
        svc = FormatPainterService()
        svc.capture(self._fmt(color="#000000"))
        result = svc.get_format(keep_active=True)
        result.color = "#ff0000"
        # Re-capture should still return original colour
        result2 = svc.get_format(keep_active=True)
        assert result2.color == "#000000"

    def test_get_format_deactivates_by_default(self):
        svc = FormatPainterService()
        svc.capture(self._fmt(bold=True))
        svc.get_format()
        assert svc.is_active is False
        assert svc.has_format is True  # stored format persists

    def test_get_format_returns_none_when_inactive(self):
        svc = FormatPainterService()
        svc.capture(self._fmt(bold=True))
        svc.get_format()          # deactivates
        assert svc.get_format() is None

    def test_get_format_keep_active_true(self):
        svc = FormatPainterService()
        svc.capture(self._fmt(underline=True))
        svc.get_format(keep_active=True)
        assert svc.is_active is True
        result = svc.get_format()
        assert result is not None
        assert result.underline is True

    def test_capture_bad_type_raises(self):
        svc = FormatPainterService()
        with pytest.raises(TypeError):
            svc.capture({"bold": True})  # type: ignore[arg-type]

    def test_capture_overwrites_previous_format(self):
        svc = FormatPainterService()
        svc.capture(self._fmt(bold=True))
        svc.capture(self._fmt(italic=True))
        result = svc.get_format()
        assert result.bold is False
        assert result.italic is True


# ---------------------------------------------------------------------------
# FormatPainterService — persistent mode
# ---------------------------------------------------------------------------

class TestFormatPainterPersistent:
    def test_persistent_stays_active(self):
        svc = FormatPainterService(persistent=True)
        svc.capture(FormatState(bold=True))
        svc.get_format()
        assert svc.is_active is True

    def test_persistent_can_paste_multiple_times(self):
        svc = FormatPainterService(persistent=True)
        svc.capture(FormatState(font_size=18.0))
        for _ in range(5):
            result = svc.get_format()
            assert result is not None
            assert result.font_size == 18.0
        assert svc.is_active is True


# ---------------------------------------------------------------------------
# FormatPainterService — lifecycle (activate / deactivate / clear)
# ---------------------------------------------------------------------------

class TestFormatPainterLifecycle:
    def test_deactivate_keeps_stored_format(self):
        svc = FormatPainterService()
        svc.capture(FormatState(bold=True))
        svc.deactivate()
        assert svc.is_active is False
        assert svc.has_format is True

    def test_activate_restores_inactive_painter(self):
        svc = FormatPainterService()
        svc.capture(FormatState(bold=True))
        svc.deactivate()
        svc.activate()
        assert svc.is_active is True

    def test_activate_without_format_has_no_effect(self):
        svc = FormatPainterService()
        svc.activate()
        assert svc.is_active is False  # nothing stored — stays inactive

    def test_clear_removes_stored_format(self):
        svc = FormatPainterService()
        svc.capture(FormatState(bold=True))
        svc.clear()
        assert svc.is_active is False
        assert svc.has_format is False
        assert svc.get_format() is None

    def test_recapture_after_clear(self):
        svc = FormatPainterService()
        svc.capture(FormatState(bold=True))
        svc.clear()
        svc.capture(FormatState(italic=True))
        result = svc.get_format()
        assert result.italic is True
        assert result.bold is False
