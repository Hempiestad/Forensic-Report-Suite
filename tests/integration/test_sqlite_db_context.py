from __future__ import annotations

import sqlite3
from pathlib import Path

from infrastructure.persistence.db_context import SQLiteDbContext


def test_db_context_initializes_cases_table(tmp_path: Path) -> None:
    db_path = tmp_path / "ctx_init.db"
    db = SQLiteDbContext(str(db_path))

    row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='cases'"
    ).fetchone()

    assert row is not None
    assert row["name"] == "cases"

    version_row = db.connection.execute(
        "SELECT MAX(version) AS v FROM schema_versions"
    ).fetchone()
    assert version_row is not None
    assert int(version_row["v"]) >= 2

    reports_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
    ).fetchone()
    audit_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_entries'"
    ).fetchone()
    assert reports_row is not None
    assert audit_row is not None


def test_db_context_commit_and_rollback(tmp_path: Path) -> None:
    db_path = tmp_path / "ctx_tx.db"
    db = SQLiteDbContext(str(db_path))

    db.connection.execute(
        "INSERT INTO cases (case_number, title, assigned_to, created_by, status, created_at, modified_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        ("CASE-TX-1", "Tx Case", "det.tx", "admin", "draft"),
    )
    db.rollback()

    missing = db.connection.execute(
        "SELECT case_number FROM cases WHERE case_number = 'CASE-TX-1'"
    ).fetchone()
    assert missing is None

    db.connection.execute(
        "INSERT INTO cases (case_number, title, assigned_to, created_by, status, created_at, modified_at) VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))",
        ("CASE-TX-2", "Tx Case 2", "det.tx", "admin", "draft"),
    )
    db.commit()

    present = db.connection.execute(
        "SELECT case_number FROM cases WHERE case_number = 'CASE-TX-2'"
    ).fetchone()
    assert present is not None


def test_db_context_migrates_legacy_db_without_data_loss(tmp_path: Path) -> None:
    db_path = tmp_path / "ctx_upgrade_from_v1.db"

    # Simulate a legacy pre-versioning database that only had the cases table.
    legacy = sqlite3.connect(str(db_path))
    legacy.execute(
        """
        CREATE TABLE cases (
            case_number TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            assigned_to TEXT NOT NULL,
            created_by TEXT NOT NULL,
            status TEXT NOT NULL,
            examiner_id TEXT,
            review_comments TEXT,
            trial_date TEXT,
            sentencing_date TEXT,
            created_at TEXT NOT NULL,
            modified_at TEXT NOT NULL,
            modified_by TEXT,
            peer_reviewers TEXT
        )
        """
    )
    legacy.execute(
        """
        INSERT INTO cases (case_number, title, assigned_to, created_by, status, created_at, modified_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
        """,
        ("CASE-LEGACY-1", "Legacy Case", "det.legacy", "admin", "draft"),
    )
    legacy.commit()
    legacy.close()

    # Opening through context should apply migrations and preserve existing case rows.
    db = SQLiteDbContext(str(db_path))

    migrated_case = db.connection.execute(
        "SELECT case_number, title FROM cases WHERE case_number = 'CASE-LEGACY-1'"
    ).fetchone()
    assert migrated_case is not None
    assert migrated_case["title"] == "Legacy Case"

    version_row = db.connection.execute("SELECT MAX(version) AS v FROM schema_versions").fetchone()
    assert version_row is not None
    assert int(version_row["v"]) == SQLiteDbContext.SCHEMA_VERSION

    # Confirm v2 tables now exist after migration.
    reports_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reports'"
    ).fetchone()
    audit_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='audit_entries'"
    ).fetchone()
    templates_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='templates'"
    ).fetchone()
    notifications_row = db.connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='notifications'"
    ).fetchone()

    assert reports_row is not None
    assert audit_row is not None
    assert templates_row is not None
    assert notifications_row is not None
