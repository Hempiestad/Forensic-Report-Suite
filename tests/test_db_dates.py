import os
import sqlite3
from database import DatabaseManager


def test_update_case_dates_local():
    # Use an isolated DB file for the test to avoid conflicts with running app
    test_db = "test_forensic_reports.db"
    try:
        if os.path.exists(test_db):
            os.remove(test_db)
    except Exception:
        pass

    DatabaseManager.DB_NAME = test_db
    dbm = DatabaseManager()

    # Insert a minimal case row directly (avoid encryption prompts)
    with dbm.conn:
        dbm.conn.execute(
            "INSERT INTO reports (case_number, encrypted_metadata, report_html_encrypted, appendices, final_pdf_hash, assigned_to, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("TEST123", b"", b"", "", "", "tester", "draft")
        )

    # Update dates via the method we added
    assert dbm.update_case_dates("TEST123", trial_date="2026-02-15", sentencing_date="2026-05-01") is True

    # Verify the DB row was updated
    cur = dbm.conn.execute("SELECT trial_date, sentencing_date FROM reports WHERE case_number = ?", ("TEST123",))
    row = cur.fetchone()
    assert row is not None
    assert row[0] == "2026-02-15"
    assert row[1] == "2026-05-01"
