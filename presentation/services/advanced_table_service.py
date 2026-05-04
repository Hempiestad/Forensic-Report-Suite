"""
AdvancedTableService — pure-Python HTML table / evidence-table generation.

No PyQt dependency; can be used from both widget code and unit tests.
"""
from __future__ import annotations

from typing import List, Optional


# Predefined forensic evidence column sets
EVIDENCE_COLUMNS_STANDARD = [
    "id",
    "description",
    "type",
    "date_collected",
    "collected_by",
    "chain_of_custody",
]

EVIDENCE_COLUMNS_DIGITAL = [
    "id",
    "filename",
    "file_size",
    "md5_hash",
    "sha256_hash",
    "acquisition_date",
    "tool",
]

EVIDENCE_COLUMNS_PHYSICAL = [
    "id",
    "description",
    "location",
    "date_collected",
    "collected_by",
    "storage_location",
    "notes",
]


class AdvancedTableService:
    """Generate HTML tables for insertion into forensic reports."""

    # ------------------------------------------------------------------
    # Generic table builder
    # ------------------------------------------------------------------

    def generate_table_html(
        self,
        rows: int,
        cols: int,
        *,
        border: int = 1,
        padding: int = 5,
        spacing: int = 0,
        header_row: bool = True,
        alternate_rows: bool = True,
        header_labels: Optional[List[str]] = None,
    ) -> str:
        """Return an HTML string for a blank *rows* × *cols* table.

        Parameters
        ----------
        rows:
            Number of data rows (not counting the header row).
        cols:
            Number of columns.
        border:
            Border width in pixels (0 = borderless).
        padding:
            Cell padding in pixels.
        spacing:
            Cell spacing in pixels.
        header_row:
            Emit a styled header row as the first row.
        alternate_rows:
            Apply alternating row background colours.
        header_labels:
            Custom column header labels.  Defaults to ``["Column 1", ...]``
            when *None*.
        """
        if rows < 1:
            raise ValueError(f"rows must be ≥ 1, got {rows}")
        if cols < 1:
            raise ValueError(f"cols must be ≥ 1, got {cols}")

        if header_labels is None:
            header_labels = [f"Column {i + 1}" for i in range(cols)]
        else:
            # Pad / truncate to match cols
            header_labels = list(header_labels)[:cols]
            while len(header_labels) < cols:
                header_labels.append(f"Column {len(header_labels) + 1}")

        table_style = (
            f"border-collapse: separate; border-spacing: {spacing}px;"
        )
        if border > 0:
            table_style += f" border: {border}px solid #000000;"

        cell_style = f"padding: {padding}px;"
        if border > 0:
            cell_style += f" border: {border}px solid #cccccc;"

        parts: list[str] = [f'<table style="{table_style}">']

        if header_row:
            parts.append("<tr style=\"background-color: #f0f0f0; font-weight: bold;\">")
            for label in header_labels:
                parts.append(f'<th style="{cell_style}">{label}</th>')
            parts.append("</tr>")

        for r in range(rows):
            row_style = ""
            if alternate_rows and r % 2 == 1:
                row_style = ' style="background-color: #f9f9f9;"'
            parts.append(f"<tr{row_style}>")
            for _ in range(cols):
                parts.append(f'<td style="{cell_style}">&nbsp;</td>')
            parts.append("</tr>")

        parts.append("</table>")
        return "".join(parts)

    # ------------------------------------------------------------------
    # Evidence-table builder
    # ------------------------------------------------------------------

    def generate_evidence_table(
        self,
        evidence_items: list,
        *,
        columns: Optional[List[str]] = None,
        preset: str = "standard",
        border: int = 1,
        padding: int = 5,
        alternate_rows: bool = True,
        include_row_numbers: bool = True,
    ) -> str:
        """Return an HTML evidence table populated with *evidence_items*.

        Parameters
        ----------
        evidence_items:
            Each element is a ``dict`` with evidence field keys, or a
            plain list / tuple for positional columns.
        columns:
            Explicit list of column keys to render.  When *None* the
            *preset* is used (``"standard"``, ``"digital"``, or
            ``"physical"``).  If the first item is a dict with different
            keys, those keys are used instead.
        preset:
            ``"standard"`` | ``"digital"`` | ``"physical"`` — selects the
            built-in forensic column set when *columns* is *None*.
        border:
            HTML table border width in pixels.
        padding:
            Cell padding in pixels.
        alternate_rows:
            Apply alternating row background colours.
        include_row_numbers:
            Prepend a ``#`` column with 1-based row numbers.
        """
        if not evidence_items:
            return ""

        # Resolve columns
        if columns is None:
            first = evidence_items[0]
            if isinstance(first, dict):
                columns = list(first.keys())
            else:
                preset_map = {
                    "standard": EVIDENCE_COLUMNS_STANDARD,
                    "digital": EVIDENCE_COLUMNS_DIGITAL,
                    "physical": EVIDENCE_COLUMNS_PHYSICAL,
                }
                columns = preset_map.get(preset, EVIDENCE_COLUMNS_STANDARD)
        else:
            columns = list(columns)

        cell_style = (
            f"border: {border}px solid #cccccc; padding: {padding}px;"
        )
        table_style = f"border-collapse: collapse; border: {border}px solid #000000;"

        parts: list[str] = [f'<table style="{table_style}">']

        # Header
        parts.append(
            "<thead><tr style=\"background-color: #dce6f1; font-weight: bold;\">"
        )
        if include_row_numbers:
            parts.append(f'<th style="{cell_style}">#</th>')
        for col in columns:
            label = col.replace("_", " ").title()
            parts.append(f'<th style="{cell_style}">{label}</th>')
        parts.append("</tr></thead><tbody>")

        # Data rows
        for idx, item in enumerate(evidence_items):
            row_style = ""
            if alternate_rows and idx % 2 == 1:
                row_style = ' style="background-color: #f5f9ff;"'
            parts.append(f"<tr{row_style}>")
            if include_row_numbers:
                parts.append(f'<td style="{cell_style}">{idx + 1}</td>')
            for col in columns:
                if isinstance(item, dict):
                    raw = item.get(col, "")
                else:
                    try:
                        raw = item[columns.index(col)]
                    except (IndexError, ValueError):
                        raw = ""
                safe = (
                    str(raw)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                parts.append(f'<td style="{cell_style}">{safe}</td>')
            parts.append("</tr>")

        parts.append("</tbody></table>")
        return "".join(parts)

    # ------------------------------------------------------------------
    # List-style name → label mapping (used by toolbar menus)
    # ------------------------------------------------------------------

    LIST_STYLES: dict[str, str] = {
        "bullet":      "• Bullet (Disc)",
        "numbered":    "1. Numbered",
        "alpha_upper": "A. Uppercase Alpha",
        "alpha_lower": "a. Lowercase Alpha",
        "roman_upper": "I. Uppercase Roman",
        "roman_lower": "i. Lowercase Roman",
    }
