"""
FormatPainterService — copy/paste text formatting as a pure-Python service.

Stores character and block formatting as plain dicts so the service can be
unit-tested without a running QApplication.  The Qt widget layer is
responsible for translating between QTextCharFormat / QTextBlockFormat and
these plain dicts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FormatState:
    """Snapshot of text character and block formatting."""

    # --- Character formatting ---
    bold: bool = False
    italic: bool = False
    underline: bool = False
    strikethrough: bool = False
    font_family: str = "Arial"
    font_size: float = 12.0
    color: str = "#000000"          # foreground colour, CSS hex
    background_color: str = ""      # background colour, CSS hex; "" = none

    # --- Block / paragraph formatting ---
    alignment: str = "left"         # "left" | "center" | "right" | "justify"
    line_spacing: float = 1.0       # multiplier (1.0 = single, 2.0 = double)
    space_before: float = 0.0       # pt
    space_after: float = 0.0        # pt

    # --- List formatting ---
    list_style: str = ""            # "" | "disc" | "decimal" | "upper_alpha" |
                                    #   "lower_alpha" | "upper_roman" | "lower_roman"

    def to_dict(self) -> dict:
        """Serialise to a plain dict (useful for logging / persistence)."""
        return {
            "bold": self.bold,
            "italic": self.italic,
            "underline": self.underline,
            "strikethrough": self.strikethrough,
            "font_family": self.font_family,
            "font_size": self.font_size,
            "color": self.color,
            "background_color": self.background_color,
            "alignment": self.alignment,
            "line_spacing": self.line_spacing,
            "space_before": self.space_before,
            "space_after": self.space_after,
            "list_style": self.list_style,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FormatState":
        """Deserialise from a plain dict."""
        return cls(
            bold=bool(data.get("bold", False)),
            italic=bool(data.get("italic", False)),
            underline=bool(data.get("underline", False)),
            strikethrough=bool(data.get("strikethrough", False)),
            font_family=str(data.get("font_family", "Arial")),
            font_size=float(data.get("font_size", 12.0)),
            color=str(data.get("color", "#000000")),
            background_color=str(data.get("background_color", "")),
            alignment=str(data.get("alignment", "left")),
            line_spacing=float(data.get("line_spacing", 1.0)),
            space_before=float(data.get("space_before", 0.0)),
            space_after=float(data.get("space_after", 0.0)),
            list_style=str(data.get("list_style", "")),
        )


class FormatPainterService:
    """Copy-paste formatting clipboard independent of any editor widget.

    Usage
    -----
    1. Call ``capture(format_state)`` after the user selects text whose
       formatting they want to copy.
    2. Check ``is_active`` — if True, the painter is "loaded".
    3. Call ``get_format()`` to retrieve the stored :class:`FormatState` and
       apply it to the target editor cursor.
    4. The painter auto-deactivates after one ``get_format()`` call (single-
       click behaviour).  Pass ``keep_active=True`` to stay active (double-
       click / persistent mode).
    """

    def __init__(self, *, persistent: bool = False) -> None:
        """
        Parameters
        ----------
        persistent:
            When *True* the painter stays active after each ``get_format()``
            call (double-click / "lock" mode).  When *False* (default) it
            deactivates after the first paste.
        """
        self._stored: Optional[FormatState] = None
        self._active: bool = False
        self.persistent = persistent

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture(self, format_state: FormatState) -> None:
        """Store *format_state* and activate the painter."""
        if not isinstance(format_state, FormatState):
            raise TypeError(f"Expected FormatState, got {type(format_state).__name__}")
        self._stored = FormatState.from_dict(format_state.to_dict())  # defensive copy
        self._active = True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def has_format(self) -> bool:
        """``True`` if a format has been captured (even if inactive)."""
        return self._stored is not None

    @property
    def is_active(self) -> bool:
        """``True`` when the painter is ready to paste."""
        return self._active

    # ------------------------------------------------------------------
    # Paste / apply
    # ------------------------------------------------------------------

    def get_format(self, *, keep_active: Optional[bool] = None) -> Optional[FormatState]:
        """Return the stored :class:`FormatState`, or *None* if empty.

        After returning the format the painter deactivates unless
        ``persistent=True`` (set at construction) or ``keep_active=True``
        is passed explicitly.
        """
        if not self._active or self._stored is None:
            return None

        fmt = FormatState.from_dict(self._stored.to_dict())  # return a copy

        stay = keep_active if keep_active is not None else self.persistent
        if not stay:
            self._active = False

        return fmt

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        """Re-activate without re-capturing (useful after a cancel)."""
        if self._stored is not None:
            self._active = True

    def deactivate(self) -> None:
        """Cancel the pending paste without clearing the stored format."""
        self._active = False

    def clear(self) -> None:
        """Discard stored format and deactivate."""
        self._stored = None
        self._active = False
