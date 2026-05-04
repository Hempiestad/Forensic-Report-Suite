"""
ReportExportService — pure-Python report export logic.

Extracted from reports_tab.py so it can be unit-tested without a QApplication.
The service accepts HTML content as a string and writes it to disk.  PDF
output requires the optional ``weasyprint`` package.
"""
from __future__ import annotations

import hashlib
import logging
import os
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from weasyprint import HTML as _WeasyHTML  # type: ignore[import-untyped]
    _WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    _WeasyHTML = None
    _WEASYPRINT_AVAILABLE = False


class ReportExportService:
    """Export report content to HTML or PDF and compute a SHA-256 hash."""

    # ------------------------------------------------------------------
    # Availability query
    # ------------------------------------------------------------------

    @staticmethod
    def pdf_available() -> bool:
        """Return *True* if PDF export (weasyprint) is available."""
        return _WEASYPRINT_AVAILABLE

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_html(self, html_content: str, path: str) -> Tuple[bool, Optional[str]]:
        """Write *html_content* to *path* as UTF-8 HTML.

        Returns
        -------
        (success, error_message)
        """
        if not html_content:
            return False, "No content to export."
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(html_content)
            return True, None
        except OSError as exc:
            logger.error("HTML export failed: %s", exc)
            return False, str(exc)

    def export_pdf(
        self,
        html_content: str,
        path: str,
    ) -> Tuple[bool, Optional[str]]:
        """Render *html_content* to a PDF file at *path* using weasyprint.

        Falls back gracefully when weasyprint is not installed.

        Returns
        -------
        (success, error_message)
        """
        if not _WEASYPRINT_AVAILABLE:
            return False, (
                "PDF export requires the 'weasyprint' package. "
                "Install it with: pip install weasyprint"
            )
        if not html_content:
            return False, "No content to export."
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _WeasyHTML(
                    string=f"<html><head><meta charset='utf-8'></head>"
                    f"<body>{html_content}</body></html>"
                ).write_pdf(path, presentational_hints=True)
            return True, None
        except Exception as exc:
            logger.error("PDF export failed: %s", exc)
            return False, str(exc)

    # ------------------------------------------------------------------
    # Integrity hash
    # ------------------------------------------------------------------

    def compute_file_hash(
        self,
        path: str,
        algorithm: str = "sha256",
        chunk_size: int = 65_536,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Compute the hex digest of *path*.

        Returns
        -------
        (hex_digest, error_message)
        """
        try:
            h = hashlib.new(algorithm)
        except ValueError:
            return None, f"Unknown hash algorithm: {algorithm}"
        try:
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(chunk_size), b""):
                    h.update(chunk)
            return h.hexdigest(), None
        except OSError as exc:
            logger.error("Hash computation failed for %s: %s", path, exc)
            return None, str(exc)

    # ------------------------------------------------------------------
    # Evidence table
    # ------------------------------------------------------------------

    def generate_evidence_table_html(
        self,
        evidence_items: list,
        *,
        columns: Optional[list] = None,
        border: int = 1,
        padding: int = 5,
        include_header: bool = True,
    ) -> str:
        """Generate an HTML evidence table from a list of dicts.

        Parameters
        ----------
        evidence_items:
            Each element is a ``dict`` whose keys become column names (or a
            list / tuple for positional data).
        columns:
            Explicit column names.  Inferred from the first item's keys when
            *None* and items are dicts.
        border:
            HTML table border width in pixels.
        padding:
            Cell padding in pixels.
        include_header:
            Whether to emit a ``<thead>`` row.

        Returns an HTML string; returns an empty string when *evidence_items*
        is empty.
        """
        if not evidence_items:
            return ""

        # Determine columns
        if columns is None:
            first = evidence_items[0]
            if isinstance(first, dict):
                columns = list(first.keys())
            else:
                columns = [f"Column {i + 1}" for i in range(len(first))]

        cell_style = (
            f"border: {border}px solid #cccccc; padding: {padding}px;"
        )
        table_style = (
            f"border-collapse: collapse; border: {border}px solid #000000;"
        )

        html_parts = [f'<table style="{table_style}">']

        if include_header:
            html_parts.append("<thead><tr>")
            for col in columns:
                label = col.replace("_", " ").title()
                html_parts.append(
                    f'<th style="background-color: #f0f0f0; font-weight: bold;'
                    f" {cell_style}\">{label}</th>"
                )
            html_parts.append("</tr></thead>")

        html_parts.append("<tbody>")
        for idx, item in enumerate(evidence_items):
            row_style = (
                "background-color: #f9f9f9;" if idx % 2 == 1 else ""
            )
            html_parts.append(f'<tr style="{row_style}">')
            for col in columns:
                if isinstance(item, dict):
                    value = item.get(col, "")
                else:
                    try:
                        col_idx = columns.index(col)
                        value = item[col_idx]
                    except (IndexError, ValueError):
                        value = ""
                # Escape HTML special characters
                safe_value = (
                    str(value)
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                )
                html_parts.append(
                    f'<td style="{cell_style}">{safe_value}</td>'
                )
            html_parts.append("</tr>")
        html_parts.append("</tbody></table>")
        return "".join(html_parts)
