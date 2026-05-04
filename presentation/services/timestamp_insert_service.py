"""
TimestampInsertService — pure-Python timestamp insert and conversion logic.

Extracted from reports_tab.py so it can be unit-tested without a QApplication.
The widget layer calls ``format_timestamp()`` / ``convert_timestamp()`` and
inserts the returned strings into the editor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

# Optional third-party dependencies — same graceful-degradation pattern as the
# rest of the codebase.
try:
    from zoneinfo import ZoneInfo as _ZoneInfo  # Python 3.9+
except ImportError:  # pragma: no cover
    _ZoneInfo = None  # type: ignore[assignment]

try:
    from dateutil import parser as _dateutil_parser
    from dateutil import tz as _dateutil_tz
except ImportError:  # pragma: no cover
    _dateutil_parser = None  # type: ignore[assignment]
    _dateutil_tz = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# IANA timezone abbreviation lookup table
# ---------------------------------------------------------------------------

_TZ_ABBREV: dict[str, list[str]] = {
    "PST": ["America/Los_Angeles"],
    "PDT": ["America/Los_Angeles"],
    "MST": ["America/Denver"],
    "MDT": ["America/Denver"],
    "CST": ["America/Chicago", "Asia/Shanghai"],
    "CDT": ["America/Chicago"],
    "EST": ["America/New_York"],
    "EDT": ["America/New_York"],
    "AKST": ["America/Anchorage"],
    "AKDT": ["America/Anchorage"],
    "HST": ["Pacific/Honolulu"],
    "UTC": ["UTC"],
    "GMT": ["Etc/GMT"],
    "BST": ["Europe/London"],
    "CET": ["Europe/Paris"],
    "CEST": ["Europe/Paris"],
    "JST": ["Asia/Tokyo"],
    "AEST": ["Australia/Sydney"],
    "AEDT": ["Australia/Sydney"],
}


@dataclass
class ParsedTimestamp:
    """Result of parsing a raw timestamp string."""

    dt: datetime
    tz_name: Optional[str]
    parser_used: str  # "dateutil" | "iso" | "strptime"


class TimestampInsertService:
    """Stateless service for timestamp insertion and conversion."""

    # ------------------------------------------------------------------
    # Timezone helpers
    # ------------------------------------------------------------------

    def detect_tz_from_abbrev(self, text: str) -> Optional[str]:
        """Return the first IANA zone name for a timezone abbreviation found
        in *text*, or *None* if unrecognised."""
        choices = self.detect_tz_choices(text)
        if choices:
            return choices[0]
        return None

    def detect_tz_choices(self, text: str) -> Optional[List[str]]:
        """Return all candidate IANA zone names for the abbreviation in
        *text*, or *None* if none found."""
        if not text:
            return None
        match = re.search(r"\b([A-Z]{2,5}|UTC|GMT)\b", text)
        if not match:
            return None
        abbrev = match.group(1).upper()
        return _TZ_ABBREV.get(abbrev)

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def parse_timestamp(self, text: str) -> Optional[ParsedTimestamp]:
        """Parse *text* as a timestamp, auto-detecting timezone if possible.

        Returns a :class:`ParsedTimestamp` or *None* if the text cannot be
        parsed.
        """
        if not text or not text.strip():
            return None

        # ── dateutil ────────────────────────────────────────────────────
        if _dateutil_parser is not None:
            try:
                dt = _dateutil_parser.parse(text, fuzzy=True)
                tz_name: Optional[str] = None
                if dt.tzinfo is None:
                    tz_name = self.detect_tz_from_abbrev(text)
                    if tz_name:
                        dt = self._attach_tz(dt, tz_name)
                else:
                    try:
                        tz_name = dt.tzname()
                    except Exception:
                        tz_name = None
                return ParsedTimestamp(dt=dt, tz_name=tz_name, parser_used="dateutil")
            except Exception:
                pass

        # ── stdlib ISO format ────────────────────────────────────────────
        try:
            dt = datetime.fromisoformat(text)
            tz_name = None
            if dt.tzinfo is None:
                tz_name = self.detect_tz_from_abbrev(text)
                if tz_name:
                    dt = self._attach_tz(dt, tz_name)
            return ParsedTimestamp(dt=dt, tz_name=tz_name, parser_used="iso")
        except Exception:
            pass

        # ── common forensic patterns ─────────────────────────────────────
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
            "%m/%d/%Y %H:%M:%S",
            "%m/%d/%Y",
        ):
            try:
                dt = datetime.strptime(text.strip(), fmt)
                return ParsedTimestamp(dt=dt, tz_name=None, parser_used="strptime")
            except Exception:
                continue

        return None

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def format_timestamp(self, fmt: str = "local") -> str:
        """Return a formatted timestamp string for the current moment.

        Parameters
        ----------
        fmt:
            ``"local"`` — ``YYYY-MM-DD HH:MM:SS`` (no timezone)
            ``"iso"``   — ISO 8601 with local timezone offset
        """
        now = datetime.now()
        if fmt == "iso":
            return now.astimezone().isoformat()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def convert_timestamp(
        self,
        text: str,
        target_tz: str,
        output_format: str = "iso",
        source_tz: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """Convert a timestamp string to *target_tz*.

        Parameters
        ----------
        text:
            Raw timestamp string (e.g. ``"2026-01-15 14:30:00 EST"``).
        target_tz:
            IANA timezone name (``"UTC"``, ``"America/New_York"``, …) or
            ``"local"`` for the system-local timezone.
        output_format:
            ``"iso"`` for ISO 8601 with offset, or ``"readable"`` for
            ``YYYY-MM-DD HH:MM:SS TZ``.
        source_tz:
            Override the source timezone when *text* has no embedded TZ info.

        Returns
        -------
        (converted_str, error_message)
            *error_message* is *None* on success, a human-readable string on
            failure.
        """
        parsed = self.parse_timestamp(text)
        if parsed is None:
            return "", f"Could not parse '{text}' as a timestamp."

        dt = parsed.dt

        # Attach source TZ if the parsed datetime is naïve
        if dt.tzinfo is None:
            effective_tz = source_tz or parsed.tz_name
            if effective_tz:
                dt = self._attach_tz(dt, effective_tz)

        # Resolve target timezone object
        try:
            tgt_tz = self._resolve_tz(target_tz)
        except Exception as exc:
            return "", f"Unknown target timezone '{target_tz}': {exc}"

        # Convert
        try:
            if tgt_tz is not None:
                converted = dt.astimezone(tgt_tz)
            elif _dateutil_tz is not None:
                converted = dt.astimezone(_dateutil_tz.tzlocal())
            else:
                converted = dt
        except Exception as exc:
            return "", f"Conversion error: {exc}"

        # Format output
        if output_format == "iso":
            return converted.isoformat(), None

        # "readable"
        try:
            tz_label = converted.tzname() or ""
        except Exception:
            tz_label = ""
        out = converted.strftime("%Y-%m-%d %H:%M:%S")
        if tz_label:
            out += f" {tz_label}"
        return out, None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _attach_tz(self, dt: datetime, iana_name: str) -> datetime:
        """Return *dt* with the named IANA timezone attached."""
        if _ZoneInfo is not None:
            return dt.replace(tzinfo=_ZoneInfo(iana_name))
        if _dateutil_tz is not None:
            return dt.replace(tzinfo=_dateutil_tz.gettz(iana_name))
        return dt  # can't attach — return naïve

    def _resolve_tz(self, tz_name: str):
        """Return a tzinfo object for *tz_name*, or *None* for local time."""
        if tz_name in ("local", "System Local"):
            return None
        if _ZoneInfo is not None:
            return _ZoneInfo(tz_name)
        if _dateutil_tz is not None:
            result = _dateutil_tz.gettz(tz_name)
            if result is None:
                raise ValueError(f"dateutil could not resolve '{tz_name}'")
            return result
        raise RuntimeError("No timezone library available (zoneinfo / dateutil).")
