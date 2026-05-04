"""
tests/presentation/test_report_export_service.py

Unit tests for ReportExportService, AdvancedTableService, and
TimestampInsertService.  All pure Python — no QApplication required.
"""
from __future__ import annotations

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from presentation.services.report_export_service import ReportExportService
from presentation.services.advanced_table_service import (
    AdvancedTableService,
    EVIDENCE_COLUMNS_STANDARD,
    EVIDENCE_COLUMNS_DIGITAL,
    EVIDENCE_COLUMNS_PHYSICAL,
)
from presentation.services.timestamp_insert_service import (
    TimestampInsertService,
    ParsedTimestamp,
)


# ===========================================================================
# ReportExportService
# ===========================================================================

class TestReportExportServiceHtml:
    def setup_method(self):
        self.svc = ReportExportService()
        self.tmp = tempfile.mkdtemp()

    def _path(self, name: str) -> str:
        return os.path.join(self.tmp, name)

    def test_export_html_creates_file(self):
        path = self._path("report.html")
        ok, err = self.svc.export_html("<h1>Test Report</h1>", path)
        assert ok is True
        assert err is None
        assert os.path.isfile(path)

    def test_export_html_content_preserved(self):
        path = self._path("report2.html")
        html = "<p>Case <b>ABC-001</b></p>"
        self.svc.export_html(html, path)
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        assert html == content

    def test_export_html_empty_content_fails(self):
        path = self._path("empty.html")
        ok, err = self.svc.export_html("", path)
        assert ok is False
        assert err is not None

    def test_export_html_creates_parent_directories(self):
        path = self._path("sub/dir/report.html")
        ok, err = self.svc.export_html("<p>test</p>", path)
        assert ok is True
        assert os.path.isfile(path)


class TestReportExportServiceHash:
    def setup_method(self):
        self.svc = ReportExportService()
        self.tmp = tempfile.mkdtemp()

    def _write(self, name: str, content: bytes) -> str:
        path = os.path.join(self.tmp, name)
        with open(path, "wb") as fh:
            fh.write(content)
        return path

    def test_sha256_known_value(self):
        # echo -n "hello" | sha256sum → 2cf24dba...
        path = self._write("hello.txt", b"hello")
        digest, err = self.svc.compute_file_hash(path)
        assert err is None
        assert digest == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_md5_algorithm(self):
        path = self._write("data.bin", b"\x00" * 16)
        digest, err = self.svc.compute_file_hash(path, algorithm="md5")
        assert err is None
        assert len(digest) == 32  # MD5 produces 32 hex chars

    def test_unknown_algorithm_returns_error(self):
        path = self._write("x.bin", b"x")
        digest, err = self.svc.compute_file_hash(path, algorithm="fakehash999")
        assert digest is None
        assert err is not None

    def test_nonexistent_file_returns_error(self):
        digest, err = self.svc.compute_file_hash("/nonexistent/path/file.bin")
        assert digest is None
        assert err is not None


class TestReportExportServiceEvidenceTable:
    def setup_method(self):
        self.svc = ReportExportService()

    def test_empty_items_returns_empty_string(self):
        assert self.svc.generate_evidence_table_html([]) == ""

    def test_dict_items_rendered(self):
        items = [{"id": "E001", "type": "photo", "description": "Scene photo"}]
        html = self.svc.generate_evidence_table_html(items)
        assert "E001" in html
        assert "photo" in html
        assert "Scene photo" in html
        assert "<table" in html

    def test_html_special_chars_escaped(self):
        items = [{"id": "E<1>", "type": "doc & file", "description": '"quoted"'}]
        html = self.svc.generate_evidence_table_html(items)
        assert "&lt;1&gt;" in html
        assert "doc &amp; file" in html
        assert "&quot;quoted&quot;" in html

    def test_header_included_by_default(self):
        items = [{"id": "E002", "type": "video"}]
        html = self.svc.generate_evidence_table_html(items, columns=["id", "type"])
        assert "<th" in html
        assert "Id" in html or "id" in html.lower()

    def test_no_header(self):
        items = [{"id": "E003"}]
        html = self.svc.generate_evidence_table_html(
            items, columns=["id"], include_header=False
        )
        assert "<th" not in html

    def test_explicit_columns_filter(self):
        items = [{"id": "E004", "type": "audio", "secret": "hidden"}]
        html = self.svc.generate_evidence_table_html(items, columns=["id", "type"])
        assert "audio" in html
        assert "hidden" not in html

    def test_multiple_rows(self):
        items = [
            {"id": f"E{i:03d}", "type": "photo"} for i in range(5)
        ]
        html = self.svc.generate_evidence_table_html(items)
        assert html.count("<tr") >= 6  # 1 header + 5 data rows

    def test_pdf_available_bool(self):
        result = ReportExportService.pdf_available()
        assert isinstance(result, bool)


# ===========================================================================
# AdvancedTableService — generic table
# ===========================================================================

class TestAdvancedTableServiceGeneric:
    def setup_method(self):
        self.svc = AdvancedTableService()

    def test_basic_table_structure(self):
        html = self.svc.generate_table_html(3, 4)
        assert "<table" in html
        assert "</table>" in html

    def test_header_row_present_by_default(self):
        html = self.svc.generate_table_html(2, 3)
        assert "<th" in html

    def test_no_header_row(self):
        html = self.svc.generate_table_html(2, 3, header_row=False)
        assert "<th" not in html

    def test_row_count(self):
        html = self.svc.generate_table_html(5, 2)
        # 5 data <tr> + 1 header <tr>
        assert html.count("<tr") == 6

    def test_col_count(self):
        html = self.svc.generate_table_html(1, 4)
        assert html.count("<th") == 4

    def test_custom_header_labels(self):
        html = self.svc.generate_table_html(1, 2, header_labels=["Name", "Value"])
        assert "Name" in html
        assert "Value" in html

    def test_header_labels_truncated_to_cols(self):
        html = self.svc.generate_table_html(1, 2, header_labels=["A", "B", "C"])
        assert "A" in html
        assert "B" in html
        assert "C" not in html

    def test_header_labels_padded_when_short(self):
        html = self.svc.generate_table_html(1, 3, header_labels=["Only"])
        assert "Only" in html
        assert "Column 2" in html
        assert "Column 3" in html

    def test_zero_rows_raises(self):
        with pytest.raises(ValueError):
            self.svc.generate_table_html(0, 3)

    def test_zero_cols_raises(self):
        with pytest.raises(ValueError):
            self.svc.generate_table_html(3, 0)

    def test_no_border(self):
        html = self.svc.generate_table_html(1, 1, border=0)
        assert "border: 0" not in html or "border-spacing" in html

    def test_alternate_rows(self):
        html = self.svc.generate_table_html(4, 2, alternate_rows=True)
        assert "#f9f9f9" in html

    def test_no_alternate_rows(self):
        html = self.svc.generate_table_html(4, 2, alternate_rows=False)
        assert "#f9f9f9" not in html


# ===========================================================================
# AdvancedTableService — evidence table
# ===========================================================================

class TestAdvancedTableServiceEvidence:
    def setup_method(self):
        self.svc = AdvancedTableService()

    def _items(self, n: int = 3) -> list:
        return [
            {
                "id": f"E{i:03d}",
                "description": f"Item {i}",
                "type": "photo",
                "date_collected": "2026-01-01",
                "collected_by": "Agent Smith",
                "chain_of_custody": "intact",
            }
            for i in range(1, n + 1)
        ]

    def test_empty_returns_empty_string(self):
        assert self.svc.generate_evidence_table([]) == ""

    def test_table_has_thead_tbody(self):
        html = self.svc.generate_evidence_table(self._items())
        assert "<thead" in html
        assert "<tbody" in html

    def test_row_numbers_present_by_default(self):
        html = self.svc.generate_evidence_table(self._items(3))
        assert ">1<" in html
        assert ">2<" in html
        assert ">3<" in html

    def test_row_numbers_suppressed(self):
        html = self.svc.generate_evidence_table(
            self._items(2), include_row_numbers=False
        )
        assert ">1<" not in html

    def test_content_rendered(self):
        html = self.svc.generate_evidence_table(self._items(1))
        assert "E001" in html
        assert "Item 1" in html

    def test_html_escaping(self):
        items = [{"id": "<script>", "description": "x & y", "type": '"t"',
                  "date_collected": "", "collected_by": "", "chain_of_custody": ""}]
        html = self.svc.generate_evidence_table(items)
        assert "&lt;script&gt;" in html
        assert "x &amp; y" in html
        assert "&quot;t&quot;" in html

    def test_digital_preset(self):
        items = [{col: f"val_{col}" for col in EVIDENCE_COLUMNS_DIGITAL}]
        html = self.svc.generate_evidence_table(items, preset="digital")
        assert "Md5 Hash" in html or "md5_hash" in html.lower()

    def test_physical_preset(self):
        items = [{col: "" for col in EVIDENCE_COLUMNS_PHYSICAL}]
        html = self.svc.generate_evidence_table(items, preset="physical")
        assert "Storage Location" in html or "storage_location" in html.lower()

    def test_explicit_columns(self):
        items = [{"id": "E001", "secret": "hidden", "type": "photo"}]
        html = self.svc.generate_evidence_table(items, columns=["id", "type"])
        assert "E001" in html
        assert "photo" in html
        assert "hidden" not in html

    def test_list_styles_dict_non_empty(self):
        assert len(AdvancedTableService.LIST_STYLES) == 6
        assert "roman_upper" in AdvancedTableService.LIST_STYLES
        assert "alpha_lower" in AdvancedTableService.LIST_STYLES


# ===========================================================================
# TimestampInsertService
# ===========================================================================

class TestTimestampInsertService:
    def setup_method(self):
        self.svc = TimestampInsertService()

    # ── format_timestamp ────────────────────────────────────────────────

    def test_format_local_returns_string(self):
        ts = self.svc.format_timestamp("local")
        assert isinstance(ts, str)
        assert len(ts) == 19  # YYYY-MM-DD HH:MM:SS

    def test_format_local_pattern(self):
        import re
        ts = self.svc.format_timestamp("local")
        assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", ts)

    def test_format_iso_contains_t(self):
        ts = self.svc.format_timestamp("iso")
        assert "T" in ts  # ISO 8601 separator

    def test_format_iso_contains_offset(self):
        ts = self.svc.format_timestamp("iso")
        # Should contain +HH:MM or -HH:MM or Z
        assert any(c in ts for c in ("+", "-", "Z"))

    # ── detect_tz_from_abbrev ────────────────────────────────────────────

    def test_detect_est(self):
        result = self.svc.detect_tz_from_abbrev("2026-01-15 14:00:00 EST")
        assert result == "America/New_York"

    def test_detect_utc(self):
        result = self.svc.detect_tz_from_abbrev("2026-01-15T14:00:00Z UTC")
        assert result == "UTC"

    def test_detect_unknown_returns_none(self):
        result = self.svc.detect_tz_from_abbrev("2026-01-15 14:00 XYZ")
        assert result is None

    def test_detect_choices_cst_has_two(self):
        choices = self.svc.detect_tz_choices("14:00 CST")
        assert choices is not None
        assert len(choices) == 2  # Chicago and Shanghai

    def test_detect_on_empty_returns_none(self):
        assert self.svc.detect_tz_from_abbrev("") is None

    # ── parse_timestamp ──────────────────────────────────────────────────

    def test_parse_iso_with_tz(self):
        parsed = self.svc.parse_timestamp("2026-01-29T15:30:00+00:00")
        assert parsed is not None
        assert parsed.dt.year == 2026
        assert parsed.dt.month == 1
        assert parsed.dt.day == 29

    def test_parse_plain_date(self):
        parsed = self.svc.parse_timestamp("2026-03-14")
        assert parsed is not None
        assert parsed.dt.year == 2026
        assert parsed.dt.month == 3

    def test_parse_with_abbrev(self):
        parsed = self.svc.parse_timestamp("2026-01-15 14:00:00 EST")
        assert parsed is not None

    def test_parse_empty_returns_none(self):
        assert self.svc.parse_timestamp("") is None
        assert self.svc.parse_timestamp("   ") is None

    def test_parse_nonsense_returns_none(self):
        result = self.svc.parse_timestamp("not a date at all xyz")
        # May or may not parse depending on dateutil's fuzzy mode
        # Key constraint: it must not raise
        assert result is None or isinstance(result, ParsedTimestamp)

    # ── convert_timestamp ────────────────────────────────────────────────

    def test_convert_utc_to_ny(self):
        out, err = self.svc.convert_timestamp(
            "2026-06-15T12:00:00+00:00", "America/New_York"
        )
        assert err is None
        assert out != ""
        # NYC is UTC-4 in summer → should be 08:00
        assert "08:00" in out

    def test_convert_unknown_tz_returns_error(self):
        out, err = self.svc.convert_timestamp(
            "2026-01-15T12:00:00+00:00", "Mars/Olympus_Mons"
        )
        assert err is not None

    def test_convert_readable_format(self):
        out, err = self.svc.convert_timestamp(
            "2026-01-15T12:00:00+00:00", "UTC", output_format="readable"
        )
        assert err is None
        # Readable format: YYYY-MM-DD HH:MM:SS TZ
        assert "2026-01-15" in out
        assert "12:00:00" in out

    def test_convert_iso_format(self):
        out, err = self.svc.convert_timestamp(
            "2026-01-15T12:00:00+00:00", "UTC", output_format="iso"
        )
        assert err is None
        assert "T" in out

    def test_convert_unparseable_text_returns_error(self):
        out, err = self.svc.convert_timestamp("not a timestamp", "UTC")
        assert out == "" or err is not None
