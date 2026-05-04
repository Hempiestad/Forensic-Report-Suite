# database.py
# FuDog Labs Forensic Report Suite - Database Manager (Standalone + Server Proxy)
# Supports local encrypted SQLite and centralized server mode

import requests
import json
import sqlite3
import os
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from secure_key_manager import encrypt_data, decrypt_data
from auth import load_config
from password_utils import hash_password, verify_password
from status_validator import StatusValidator, StatusTransitionError

logger = logging.getLogger(__name__)


# ============================================================================
# CONNECTION RESILIENCE UTILITIES
# ============================================================================

class DatabaseConnectionError(Exception):
    """Raised when database connection fails after retries."""
    pass


def get_db_connection(db_path, max_retries=3, timeout=5):
    """
    Connect to SQLite database with automatic retry and exponential backoff.
    
    Args:
        db_path: Path to SQLite database file
        max_retries: Maximum number of connection attempts
        timeout: Timeout in seconds for each attempt
        
    Returns:
        sqlite3.Connection object on success
        
    Raises:
        DatabaseConnectionError: If connection fails after all retries
    """
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=timeout)
            conn.row_factory = sqlite3.Row
            
            # Test connection with simple query
            conn.execute("SELECT 1")
            conn.commit()
            
            if attempt > 0:
                logger.info(f"Database connection established after {attempt + 1} attempts")
            
            return conn
        
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                logger.info(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"Database connection failed after {max_retries} attempts: {e}")
                raise DatabaseConnectionError(f"Cannot connect to database at {db_path}: {e}")
    
    raise DatabaseConnectionError(f"Cannot connect to database at {db_path}")


def test_database_accessibility(db_path):
    """
    Test if database file is accessible and writable.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        (is_accessible, is_writable, message) tuple
    """
    if not os.path.exists(db_path):
        return False, False, f"Database file not found: {db_path}"
    
    try:
        if not os.access(db_path, os.R_OK):
            return False, False, f"Database file is not readable: {db_path}"
        
        if not os.access(db_path, os.W_OK):
            return True, False, f"Database file is readable but not writable: {db_path}"
        
        return True, True, f"Database file is accessible and writable: {db_path}"
    except Exception as e:
        return False, False, f"Error checking database accessibility: {e}"

# Load configuration
config = load_config()
SERVER_URL = config.get('server_url', '').rstrip('/')

class DatabaseManager:
    DB_NAME = "forensic_reports_encrypted.db"
    CURRENT_SCHEMA_VERSION = 11

    def __init__(self, token: Optional[str] = None, safe_mode: bool = False) -> None:
        """Initialize DatabaseManager for standalone or server mode.
        
        Args:
            token: Optional authentication token for server mode
            safe_mode: If True, use cached data when database connection fails
        """
        self.token = token
        self.safe_mode = safe_mode
        self._dashboard_cache: Dict[str, Any] = {}  # Cache for dashboard data
        self._cache_expiry: Dict[str, float] = {}  # Cache expiry times
        self._decryption_cache: Dict[str, Dict[str, Any]] = {}  # Cache for decrypted report data
        self._db_accessible = True  # Track database accessibility
        self._readonly_mode = False  # Track if operating in read-only mode
        
        if not SERVER_URL:
            # Standalone mode: Use local encrypted SQLite
            try:
                # Check database file accessibility (skip check for new DB files that don't exist yet)
                if os.path.exists(self.DB_NAME):
                    accessible, writable, msg = test_database_accessibility(self.DB_NAME)
                    logger.info(msg)

                    if not accessible:
                        logger.error(f"Database not accessible: {msg}")
                        self._db_accessible = False
                        if safe_mode:
                            logger.warning("SAFE MODE: Continuing with cached data only")
                            self._readonly_mode = True
                            self.conn = None
                            return
                        else:
                            raise DatabaseConnectionError(msg)
                else:
                    logger.info(f"Database file not found, will create new: {self.DB_NAME}")
                
                # Try to establish connection with retries
                self.conn = get_db_connection(self.DB_NAME, max_retries=3, timeout=5)
                self._create_local_tables()
                
            except DatabaseConnectionError as e:
                logger.error(f"Failed to connect to database: {e}")
                self._db_accessible = False
                
                if safe_mode or self.safe_mode:
                    logger.warning("SAFE MODE: Operating with read-only cache. Data modifications will not persist.")
                    self._readonly_mode = True
                    self.conn = None
                else:
                    raise
        else:
            # Server mode: All operations go through API
            self.conn = None

    def _create_local_tables(self) -> None:
        """Create local tables for standalone mode with schema versioning"""
        with self.conn:
            # Schema versions table
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_versions (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Check current schema version
            cursor = self.conn.execute('SELECT MAX(version) as current_version FROM schema_versions')
            row = cursor.fetchone()
            current_version = row['current_version'] if row and row['current_version'] else 0

            # Apply migrations if needed
            if current_version < self.CURRENT_SCHEMA_VERSION:
                self._run_migrations(current_version)

    def _run_migrations(self, from_version: int) -> None:
        """Run database migrations from a specific version
        
        Args:
            from_version: Starting schema version to migrate from
        """
        migrations = {
            1: self._migration_v1,
            2: self._migration_v2,
            3: self._migration_v3,
            4: self._migration_v4,
            5: self._migration_v5,
            6: self._migration_v6,
            7: self._migration_v7,
            8: self._migration_v8,
            9: self._migration_v9,
            10: self._migration_v10,
            11: self._migration_v11,
        }

        for version in range(from_version + 1, self.CURRENT_SCHEMA_VERSION + 1):
            if version in migrations:
                logger.info(f"Applying database migration v{version}")
                migrations[version]()
                self.conn.execute('INSERT INTO schema_versions (version) VALUES (?)', (version,))
                self.conn.commit()

    def _migration_v1(self) -> None:
        """Migration to version 1: Complete schema setup"""
        # Main cases table
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                case_number TEXT PRIMARY KEY,
                encrypted_metadata BLOB,
                report_html_encrypted BLOB,
                appendices TEXT,
                final_pdf_hash TEXT,
                assigned_to TEXT,
                status TEXT DEFAULT 'draft',
                review_comments TEXT,
                trial_date TEXT,
                sentencing_date TEXT,
                legal_pending_count INTEGER DEFAULT 0,
                legal_overdue_count INTEGER DEFAULT 0,
                legal_summary_updated TEXT
            )
        ''')

        # Evidence items
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS evidence_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT,
                evidence_item_number TEXT,
                item_type TEXT,
                physical_description TEXT,
                digital_make TEXT,
                digital_model TEXT,
                digital_type TEXT,
                digital_sn TEXT,
                digital_storage_size TEXT,
                password TEXT,
                imaged_date TEXT,
                analyzed_date TEXT,
                completed_date TEXT,
                evidence_found TEXT,
                imaging_status TEXT DEFAULT 'not_imaged',
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

        # Legal processes
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS legal_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT,
                process_type TEXT,
                provider TEXT,
                status TEXT DEFAULT 'pending',
                submission_date TEXT,
                due_date TEXT,
                expiration_date TEXT,
                received_date TEXT,
                analysis_start_date TEXT,
                completed_date TEXT,
                notes TEXT,
                ndr INTEGER DEFAULT 0,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

        # Investigative leads
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS investigative_leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT,
                name TEXT,
                description TEXT,
                source TEXT,
                completed INTEGER DEFAULT 0,
                created_date TEXT,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

        # Court dates
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS court_dates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT,
                date_type TEXT,
                court_date TEXT,
                notes TEXT,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

        # Dashboard summaries table for caching decrypted data
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS dashboard_summaries (
                case_number TEXT PRIMARY KEY,
                summary_text TEXT,
                last_updated TEXT,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

    def _migration_v2(self):
        """Migration to version 2: Add database indexes for performance"""
        # Add indexes after table creation
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_case_number ON reports(case_number);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_evidence_case_number ON evidence_items(case_number);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_case_number ON legal_processes(case_number);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_assigned_to ON reports(assigned_to);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_status ON reports(status);')

    def _migration_v3(self):
        """Migration to version 3: Add time and location to court_dates table"""
        self.conn.execute('ALTER TABLE court_dates ADD COLUMN event_time TEXT;')
        self.conn.execute('ALTER TABLE court_dates ADD COLUMN location TEXT;')

    def _migration_v4(self):
        """Migration to version 4: Add date_created column to reports table"""
        self.conn.execute('ALTER TABLE reports ADD COLUMN date_created TEXT;')
    
    def _migration_v5(self):
        """Migration to version 5: Add notifications table"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                notification_type TEXT NOT NULL,
                notification_subtype TEXT,
                related_id INTEGER,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT DEFAULT 'info',
                created_date TEXT NOT NULL,
                trigger_date TEXT,
                read INTEGER DEFAULT 0,
                dismissed INTEGER DEFAULT 0,
                acknowledged_date TEXT,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')
        
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_case_number ON notifications(case_number);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(read);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_trigger_date ON notifications(trigger_date);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);')

    def _migration_v6(self):
        """Migration to version 6: Add archive fields to cases/reports table"""
        self.conn.execute('ALTER TABLE reports ADD COLUMN archived INTEGER DEFAULT 0;')
        self.conn.execute('ALTER TABLE reports ADD COLUMN archived_date TEXT;')
        self.conn.execute('ALTER TABLE reports ADD COLUMN archived_by TEXT;')
        self.conn.execute('ALTER TABLE reports ADD COLUMN archive_reason TEXT;')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_reports_archived ON reports(archived);')
        logger.info("Added archive fields to reports table")

    def _migration_v7(self):
        """Migration to version 7: Add case events table for calendar integration"""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS case_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                event_type TEXT NOT NULL,
                event_date TEXT NOT NULL,
                title TEXT NOT NULL,
                details TEXT,
                related_id INTEGER,
                severity TEXT DEFAULT 'info',
                created_date TEXT NOT NULL,
                FOREIGN KEY (case_number) REFERENCES reports (case_number) ON DELETE CASCADE
            )
        ''')

        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_case_events_case_number ON case_events(case_number);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_case_events_event_date ON case_events(event_date);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_case_events_event_type ON case_events(event_type);')
        logger.info("Added case events table for calendar integration")

    def _migration_v8(self):
        """Migration to version 8: Add legal process approval workflow tracking"""
        # Add approval workflow fields
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN investigator_approved_date TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN investigator_name TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN state_attorney_approved_date TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN state_attorney_name TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN judicial_approval_date TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN court_name TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN judge_name TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN sent_to_provider_date TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN transmission_method TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN provider_acknowledged_date TEXT;')
        
        # Add SLA tracking fields
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN expected_response_days INTEGER;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN sla_due_date TEXT;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN sla_breach INTEGER DEFAULT 0;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN days_late INTEGER DEFAULT 0;')
        self.conn.execute('ALTER TABLE legal_processes ADD COLUMN breach_reason TEXT;')
        
        # Add index for SLA queries
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_sla_due_date ON legal_processes(sla_due_date);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_sent_to_provider ON legal_processes(sent_to_provider_date);')
        logger.info("Added legal process approval workflow and SLA tracking fields")

    def _migration_v9(self) -> None:
        """Migration to version 9: Add template system tables."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                html_content TEXT NOT NULL,
                description TEXT,
                is_published INTEGER DEFAULT 0,
                is_default INTEGER DEFAULT 0,
                is_favorite INTEGER DEFAULT 0,
                version_number INTEGER DEFAULT 1,
                tags TEXT DEFAULT '[]',
                usage_count INTEGER DEFAULT 0,
                last_used_at TEXT,
                parent_template_id INTEGER,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                modified_by TEXT
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS template_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                version_number INTEGER NOT NULL,
                html_content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                notes TEXT,
                FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS template_placeholders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                placeholder_type TEXT DEFAULT 'string',
                is_required INTEGER DEFAULT 1,
                default_value TEXT,
                sample_value TEXT,
                validation_pattern TEXT,
                help_text TEXT,
                FOREIGN KEY (template_id) REFERENCES templates (id) ON DELETE CASCADE,
                UNIQUE (template_id, name)
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_name ON templates(name);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_category ON templates(category);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_templates_published ON templates(is_published);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_template_versions_template_id ON template_versions(template_id);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_template_placeholders_template_id ON template_placeholders(template_id);')
        logger.info("Added template system tables (v9)")

    def _migration_v10(self) -> None:
        """Migration to version 10: Add legal template library and share tables."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS legal_template_library (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_username TEXT NOT NULL,
                vendor_name TEXT NOT NULL DEFAULT 'General Vendor',
                template_type TEXT NOT NULL,
                title TEXT NOT NULL,
                template_content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS legal_template_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                shared_with TEXT NOT NULL,
                shared_by TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES legal_template_library (id) ON DELETE CASCADE,
                UNIQUE (template_id, shared_with)
            )
        ''')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_owner ON legal_template_library(owner_username);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_vendor ON legal_template_library(vendor_name);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_type ON legal_template_library(template_type);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_share_template ON legal_template_shares(template_id);')
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_share_target ON legal_template_shares(shared_with);')
        logger.info("Added legal template library tables (v10)")

    def _migration_v11(self) -> None:
        """Migration to version 11: Add vendor root category to existing legal templates."""
        try:
            self.conn.execute("ALTER TABLE legal_template_library ADD COLUMN vendor_name TEXT NOT NULL DEFAULT 'General Vendor';")
        except sqlite3.OperationalError:
            # Column already exists.
            pass
        self.conn.execute('UPDATE legal_template_library SET vendor_name = ? WHERE vendor_name IS NULL OR trim(vendor_name) = ?', ('General Vendor', ''))
        self.conn.execute('CREATE INDEX IF NOT EXISTS idx_legal_template_vendor ON legal_template_library(vendor_name);')
        logger.info("Added legal template vendor category field (v11)")

    def _auth_headers(self) -> Dict[str, str]:
        """Build bearer auth header when token is available."""
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

    # ------------------------------------------------------------------
    # Legal Template Library
    # ------------------------------------------------------------------

    def list_legal_template_library(self, username: str, role: str = 'writer') -> List[Dict[str, Any]]:
        """Return templates owned by user plus templates shared with the user."""
        if SERVER_URL:
            resp = requests.get(f'{SERVER_URL}/legal-template-library/templates', headers=self._auth_headers())
            return resp.json() if resp.ok else []

        if not self.conn:
            return []

        def _parse_tags(raw: str) -> List[str]:
            if not raw:
                return []
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return [str(tag).strip() for tag in data if str(tag).strip()]
            except Exception:
                return []
            return []

        if role == 'admin':
            rows = self.conn.execute(
                '''
                SELECT id, owner_username, vendor_name, template_type, title, template_content, tags, created_at, updated_at
                FROM legal_template_library
                WHERE is_active = 1
                ORDER BY updated_at DESC
                '''
            ).fetchall()
            return [
                {
                    'id': row['id'],
                    'owner_username': row['owner_username'],
                    'vendor_name': row['vendor_name'] or 'General Vendor',
                    'template_type': row['template_type'],
                    'title': row['title'],
                    'template_content': row['template_content'],
                    'tags': _parse_tags(row['tags']),
                    'is_shared': False,
                    'is_owned': str(row['owner_username']).lower() == str(username).lower(),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at'],
                }
                for row in rows
            ]

        owned_rows = self.conn.execute(
            '''
            SELECT id, owner_username, vendor_name, template_type, title, template_content, tags, created_at, updated_at
            FROM legal_template_library
            WHERE is_active = 1 AND lower(owner_username) = lower(?)
            ORDER BY updated_at DESC
            ''',
            (username,),
        ).fetchall()

        shared_rows = self.conn.execute(
            '''
            SELECT t.id, t.owner_username, t.vendor_name, t.template_type, t.title, t.template_content, t.tags, t.created_at, t.updated_at
            FROM legal_template_library t
            JOIN legal_template_shares s ON s.template_id = t.id
            WHERE t.is_active = 1 AND lower(s.shared_with) = lower(?)
            ORDER BY t.updated_at DESC
            ''',
            (username,),
        ).fetchall()

        row_map: Dict[int, Dict[str, Any]] = {}
        for row in owned_rows:
            row_map[row['id']] = {
                'id': row['id'],
                'owner_username': row['owner_username'],
                'vendor_name': row['vendor_name'] or 'General Vendor',
                'template_type': row['template_type'],
                'title': row['title'],
                'template_content': row['template_content'],
                'tags': _parse_tags(row['tags']),
                'is_shared': False,
                'is_owned': True,
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }
        for row in shared_rows:
            if row['id'] in row_map:
                continue
            row_map[row['id']] = {
                'id': row['id'],
                'owner_username': row['owner_username'],
                'vendor_name': row['vendor_name'] or 'General Vendor',
                'template_type': row['template_type'],
                'title': row['title'],
                'template_content': row['template_content'],
                'tags': _parse_tags(row['tags']),
                'is_shared': True,
                'is_owned': False,
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            }

        templates = list(row_map.values())
        templates.sort(key=lambda item: str(item.get('updated_at') or ''), reverse=True)
        return templates

    def create_legal_template(
        self,
        owner_username: str,
        vendor_name: str,
        template_type: str,
        title: str,
        template_content: str,
        tags: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Create a new legal template and return the created record."""
        tags = tags or []
        if SERVER_URL:
            payload = {
                'vendor_name': vendor_name,
                'template_type': template_type,
                'title': title,
                'template_content': template_content,
                'tags': tags,
            }
            resp = requests.post(f'{SERVER_URL}/legal-template-library/templates', json=payload, headers=self._auth_headers())
            return resp.json() if resp.ok else None

        if not self.conn:
            return None

        now = datetime.now().isoformat()
        clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        with self.conn:
            cursor = self.conn.execute(
                '''
                INSERT INTO legal_template_library
                (owner_username, vendor_name, template_type, title, template_content, tags, created_at, updated_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                ''',
                (owner_username, vendor_name, template_type, title, template_content, json.dumps(clean_tags), now, now),
            )
            template_id = cursor.lastrowid

        return {
            'id': template_id,
            'owner_username': owner_username,
            'vendor_name': vendor_name,
            'template_type': template_type,
            'title': title,
            'template_content': template_content,
            'tags': clean_tags,
            'is_shared': False,
            'is_owned': True,
            'created_at': now,
            'updated_at': now,
        }

    def update_legal_template(
        self,
        template_id: int,
        actor_username: str,
        actor_role: str,
        vendor_name: str,
        template_type: str,
        title: str,
        template_content: str,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Update an existing legal template if actor has ownership/admin rights."""
        tags = tags or []
        if SERVER_URL:
            payload = {
                'vendor_name': vendor_name,
                'template_type': template_type,
                'title': title,
                'template_content': template_content,
                'tags': tags,
            }
            resp = requests.put(
                f'{SERVER_URL}/legal-template-library/templates/{template_id}',
                json=payload,
                headers=self._auth_headers(),
            )
            return resp.ok

        if not self.conn:
            return False

        row = self.conn.execute(
            'SELECT owner_username FROM legal_template_library WHERE id = ? AND is_active = 1',
            (template_id,),
        ).fetchone()
        if not row:
            return False

        owner = str(row['owner_username'] or '').lower()
        if actor_role != 'admin' and owner != str(actor_username or '').lower():
            return False

        now = datetime.now().isoformat()
        clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        with self.conn:
            self.conn.execute(
                '''
                UPDATE legal_template_library
                SET vendor_name = ?, template_type = ?, title = ?, template_content = ?, tags = ?, updated_at = ?
                WHERE id = ?
                ''',
                (vendor_name, template_type, title, template_content, json.dumps(clean_tags), now, template_id),
            )
        return True

    def delete_legal_template(self, template_id: int, actor_username: str, actor_role: str) -> bool:
        """Soft-delete a legal template if actor has ownership/admin rights."""
        if SERVER_URL:
            resp = requests.delete(
                f'{SERVER_URL}/legal-template-library/templates/{template_id}',
                headers=self._auth_headers(),
            )
            return resp.ok

        if not self.conn:
            return False

        row = self.conn.execute(
            'SELECT owner_username FROM legal_template_library WHERE id = ? AND is_active = 1',
            (template_id,),
        ).fetchone()
        if not row:
            return False

        owner = str(row['owner_username'] or '').lower()
        if actor_role != 'admin' and owner != str(actor_username or '').lower():
            return False

        with self.conn:
            self.conn.execute(
                'UPDATE legal_template_library SET is_active = 0, updated_at = ? WHERE id = ?',
                (datetime.now().isoformat(), template_id),
            )
        return True

    def share_legal_template(self, template_id: int, shared_with: str, actor_username: str) -> bool:
        """Share a single legal template with another user."""
        shared_with = str(shared_with or '').strip().lower()
        if not shared_with:
            return False

        if SERVER_URL:
            payload = {'shared_with': shared_with}
            resp = requests.post(
                f'{SERVER_URL}/legal-template-library/templates/{template_id}/share',
                json=payload,
                headers=self._auth_headers(),
            )
            return resp.ok

        if not self.conn:
            return False

        row = self.conn.execute(
            'SELECT owner_username FROM legal_template_library WHERE id = ? AND is_active = 1',
            (template_id,),
        ).fetchone()
        if not row:
            return False

        owner = str(row['owner_username'] or '').lower()
        if owner != str(actor_username or '').lower():
            return False

        with self.conn:
            self.conn.execute(
                '''
                INSERT OR IGNORE INTO legal_template_shares
                (template_id, shared_with, shared_by, created_at)
                VALUES (?, ?, ?, ?)
                ''',
                (template_id, shared_with, actor_username, datetime.now().isoformat()),
            )
        return True

    def share_legal_template_library(self, owner_username: str, shared_with: str) -> int:
        """Share all templates from owner with a recipient and return number of new shares."""
        shared_with = str(shared_with or '').strip().lower()
        if not shared_with:
            return 0

        if SERVER_URL:
            payload = {'shared_with': shared_with, 'owner_username': owner_username}
            resp = requests.post(
                f'{SERVER_URL}/legal-template-library/libraries/share',
                json=payload,
                headers=self._auth_headers(),
            )
            if not resp.ok:
                return 0
            try:
                return int((resp.json() or {}).get('templates_shared', 0) or 0)
            except Exception:
                return 0

        if not self.conn:
            return 0

        owner = str(owner_username or '').strip().lower()
        rows = self.conn.execute(
            'SELECT id FROM legal_template_library WHERE is_active = 1 AND lower(owner_username) = lower(?)',
            (owner,),
        ).fetchall()

        created = 0
        with self.conn:
            for row in rows:
                cursor = self.conn.execute(
                    '''
                    INSERT OR IGNORE INTO legal_template_shares
                    (template_id, shared_with, shared_by, created_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (row['id'], shared_with, owner_username, datetime.now().isoformat()),
                )
                if cursor.rowcount and cursor.rowcount > 0:
                    created += 1
        return created

    def share_legal_template_library_scoped(
        self,
        owner_username: str,
        shared_with: str,
        vendor_name: str,
        template_type: Optional[str] = None,
    ) -> int:
        """Share templates under a vendor root and optional process-type subfolder."""
        shared_with = str(shared_with or '').strip().lower()
        vendor_name = str(vendor_name or '').strip()
        template_type = str(template_type or '').strip().lower() or None
        if not shared_with or not vendor_name:
            return 0

        if SERVER_URL:
            payload = {
                'shared_with': shared_with,
                'owner_username': owner_username,
                'vendor_name': vendor_name,
            }
            if template_type:
                payload['template_type'] = template_type
            resp = requests.post(
                f'{SERVER_URL}/legal-template-library/libraries/share-scoped',
                json=payload,
                headers=self._auth_headers(),
            )
            if not resp.ok:
                return 0
            try:
                return int((resp.json() or {}).get('templates_shared', 0) or 0)
            except Exception:
                return 0

        if not self.conn:
            return 0

        owner = str(owner_username or '').strip().lower()
        query = (
            'SELECT id FROM legal_template_library '
            'WHERE is_active = 1 AND lower(owner_username) = lower(?) AND lower(vendor_name) = lower(?)'
        )
        params: List[Any] = [owner, vendor_name]
        if template_type:
            query += ' AND lower(template_type) = lower(?)'
            params.append(template_type)
        rows = self.conn.execute(query, tuple(params)).fetchall()

        created = 0
        with self.conn:
            for row in rows:
                cursor = self.conn.execute(
                    '''
                    INSERT OR IGNORE INTO legal_template_shares
                    (template_id, shared_with, shared_by, created_at)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (row['id'], shared_with, owner_username, datetime.now().isoformat()),
                )
                if cursor.rowcount and cursor.rowcount > 0:
                    created += 1
        return created

    def export_legal_template_library(self, owner_username: str, role: str = 'writer') -> Dict[str, Any]:
        """Export templates in JSON-serializable format for backup/transfer."""
        owner = str(owner_username or '').strip().lower()
        if SERVER_URL:
            params = {'owner_username': owner} if role == 'admin' else None
            resp = requests.get(
                f'{SERVER_URL}/legal-template-library/export',
                params=params,
                headers=self._auth_headers(),
            )
            if resp.ok:
                return resp.json()
            return {'schema_version': 1, 'owner_username': owner, 'templates': []}

        if not self.conn:
            return {'schema_version': 1, 'owner_username': owner, 'templates': []}

        rows = self.conn.execute(
            '''
            SELECT vendor_name, template_type, title, template_content, tags
            FROM legal_template_library
            WHERE is_active = 1 AND lower(owner_username) = lower(?)
            ORDER BY vendor_name ASC, template_type ASC, title ASC
            ''',
            (owner,),
        ).fetchall()

        templates = []
        for row in rows:
            try:
                tags = json.loads(row['tags']) if row['tags'] else []
                if not isinstance(tags, list):
                    tags = []
            except Exception:
                tags = []
            templates.append(
                {
                    'vendor_name': row['vendor_name'] or 'General Vendor',
                    'template_type': row['template_type'],
                    'title': row['title'],
                    'template_content': row['template_content'],
                    'tags': [str(tag).strip() for tag in tags if str(tag).strip()],
                }
            )

        return {
            'schema_version': 1,
            'owner_username': owner,
            'templates': templates,
        }

    def import_legal_template_library(
        self,
        owner_username: str,
        import_payload: Dict[str, Any],
        mode: str = 'append',
        role: str = 'writer',
    ) -> Dict[str, int]:
        """Import templates from export payload.

        mode: append keeps existing entries; replace clears owner's active templates first.
        """
        owner = str(owner_username or '').strip().lower()
        templates = import_payload.get('templates') if isinstance(import_payload, dict) else None
        if not isinstance(templates, list):
            return {'imported': 0, 'skipped': 0}

        mode = str(mode or 'append').strip().lower()
        if mode not in {'append', 'replace'}:
            mode = 'append'

        if SERVER_URL:
            payload = {
                'owner_username': owner if role == 'admin' else None,
                'templates': templates,
                'mode': mode,
            }
            if payload.get('owner_username') is None:
                payload.pop('owner_username')
            resp = requests.post(
                f'{SERVER_URL}/legal-template-library/import',
                json=payload,
                headers=self._auth_headers(),
            )
            if not resp.ok:
                return {'imported': 0, 'skipped': len(templates)}
            data = resp.json() or {}
            return {'imported': int(data.get('imported', 0) or 0), 'skipped': int(data.get('skipped', 0) or 0)}

        if not self.conn:
            return {'imported': 0, 'skipped': len(templates)}

        imported = 0
        skipped = 0

        with self.conn:
            if mode == 'replace':
                self.conn.execute(
                    'UPDATE legal_template_library SET is_active = 0, updated_at = ? WHERE lower(owner_username) = lower(?) AND is_active = 1',
                    (datetime.now().isoformat(), owner),
                )

            for entry in templates:
                if not isinstance(entry, dict):
                    skipped += 1
                    continue
                vendor_name = str(entry.get('vendor_name') or 'General Vendor').strip()
                template_type = str(entry.get('template_type') or 'other').strip().lower()
                title = str(entry.get('title') or '').strip()
                content = str(entry.get('template_content') or '').strip()
                tags = entry.get('tags') or []

                if template_type not in {'preservation_letter', 'subpoena', 'search_warrant', 'other'}:
                    skipped += 1
                    continue
                if not vendor_name or not title or not content:
                    skipped += 1
                    continue
                if not isinstance(tags, list):
                    tags = [str(tags)]
                clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]

                existing = self.conn.execute(
                    '''
                    SELECT id FROM legal_template_library
                    WHERE is_active = 1
                      AND lower(owner_username) = lower(?)
                      AND lower(vendor_name) = lower(?)
                      AND lower(template_type) = lower(?)
                      AND lower(title) = lower(?)
                    ''',
                    (owner, vendor_name, template_type, title),
                ).fetchone()

                if existing:
                    if mode == 'append':
                        skipped += 1
                        continue
                    self.conn.execute(
                        '''
                        UPDATE legal_template_library
                        SET template_content = ?, tags = ?, updated_at = ?, is_active = 1
                        WHERE id = ?
                        ''',
                        (content, json.dumps(clean_tags), datetime.now().isoformat(), existing['id']),
                    )
                    imported += 1
                    continue

                now = datetime.now().isoformat()
                self.conn.execute(
                    '''
                    INSERT INTO legal_template_library
                    (owner_username, vendor_name, template_type, title, template_content, tags, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ''',
                    (owner, vendor_name, template_type, title, content, json.dumps(clean_tags), now, now),
                )
                imported += 1

        return {'imported': imported, 'skipped': skipped}

    # ------------------------------------------------------------------
    # Case Operations
    # ------------------------------------------------------------------

    def load_report(self, case_number: str) -> Tuple[str, List[str], str]:
        """Return (report_html, appendices, final_pdf_hash) for compatibility.

        Use `load_report_with_dates` if you need trial/sentencing dates.
        
        Args:
            case_number: Case number to load
            
        Returns:
            Tuple of (html_content, appendices_list, pdf_hash)
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/cases/{case_number}', headers=headers)
            if resp.ok:
                data = resp.json()
                return data.get('report_html', ''), data.get('appendices', []), data.get('final_pdf_hash', '')
            return '', [], ''
        else:
            # Check decryption cache first
            cache_key = f"report_{case_number}"
            if cache_key in self._decryption_cache:
                cached_data = self._decryption_cache[cache_key]
                return cached_data['html'], cached_data['appendices'], cached_data['pdf_hash']

            cursor = self.conn.execute('''
                SELECT report_html_encrypted, appendices, final_pdf_hash FROM reports WHERE case_number = ?
            ''', (case_number,))
            row = cursor.fetchone()
            if row:
                decrypted_html = decrypt_data(row['report_html_encrypted'])
                appendices = row['appendices'].split(',') if row['appendices'] else []

                # Cache the decrypted data
                self._decryption_cache[cache_key] = {
                    'html': decrypted_html,
                    'appendices': appendices,
                    'pdf_hash': row['final_pdf_hash'] or ''
                }

                return decrypted_html, appendices, row['final_pdf_hash'] or ''
            return '', [], ''

    def load_report_with_dates(self, case_number: str) -> Tuple[str, List[str], str, Optional[str], Optional[str], Optional[str]]:
        """Return (report_html, appendices, final_pdf_hash, trial_date, sentencing_date, date_created).
        
        Args:
            case_number: Case number to load
            
        Returns:
            Tuple of (html_content, appendices_list, pdf_hash, trial_date, sentencing_date, date_created)
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/cases/{case_number}', headers=headers)
            if resp.ok:
                data = resp.json()
                return (
                    data.get('report_html', ''),
                    data.get('appendices', []),
                    data.get('final_pdf_hash', ''),
                    data.get('trial_date'),
                    data.get('sentencing_date'),
                    data.get('date_created')
                )
            return '', [], '', None, None
        else:
            cursor = self.conn.execute('''
                SELECT report_html_encrypted, appendices, final_pdf_hash, trial_date, sentencing_date, date_created FROM reports WHERE case_number = ?
            ''', (case_number,))
            row = cursor.fetchone()
            if row:
                decrypted_html = decrypt_data(row['report_html_encrypted'])
                appendices = row['appendices'].split(',') if row['appendices'] else []
                return decrypted_html, appendices, row['final_pdf_hash'] or '', row['trial_date'], row['sentencing_date'], row['date_created']
            return '', [], '', None, None

    def save_report(self, case_data: Dict[str, Any], report_html: str, appendices_list: List[str], 
                   pdf_hash: str = "", assigned_to: Optional[str] = None, status: str = 'draft', 
                   trial_date: Optional[str] = None, sentencing_date: Optional[str] = None) -> bool:
        """Save or update a forensic report.
        
        Args:
            case_data: Case metadata dictionary
            report_html: HTML report content
            appendices_list: List of appendix file paths
            pdf_hash: PDF hash for integrity verification
            assigned_to: Optional user assignment
            status: Report status (draft/submitted/approved)
            trial_date: Optional trial date
            sentencing_date: Optional sentencing date
            
        Returns:
            True if save successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            data = {
                'case_number': case_data['case_number'],
                'metadata': case_data,
                'report_html': report_html,
                'appendices': [os.path.basename(p) for p in appendices_list],
                'final_pdf_hash': pdf_hash,
                'assigned_to': assigned_to or current_user['username'],
                'status': status,
                'trial_date': trial_date,
                'sentencing_date': sentencing_date
            }
            resp = requests.post(f'{SERVER_URL}/cases/save', json=data, headers=headers)
            return resp.ok
        else:
            encrypted_metadata = encrypt_data(json.dumps(case_data))
            encrypted_html = encrypt_data(report_html)
            appendices_str = ",".join([os.path.basename(p) for p in appendices_list])
            assigned = assigned_to or "anonymous"

            with self.conn:
                # Check if case already exists
                cursor = self.conn.execute('SELECT date_created FROM reports WHERE case_number = ?', (case_data['case_number'],))
                existing_row = cursor.fetchone()
                date_created = existing_row['date_created'] if existing_row else datetime.now().isoformat()

                self.conn.execute('''
                    INSERT OR REPLACE INTO reports
                    (case_number, encrypted_metadata, report_html_encrypted, appendices, final_pdf_hash, assigned_to, status, trial_date, sentencing_date, date_created)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    case_data['case_number'], encrypted_metadata, encrypted_html,
                    appendices_str, pdf_hash, assigned, status, trial_date, sentencing_date, date_created
                ))

                # Clear decryption cache for this case
                case_number = case_data['case_number']
                cache_keys_to_remove = [k for k in self._decryption_cache.keys() if case_number in k]
                for key in cache_keys_to_remove:
                    del self._decryption_cache[key]

                # Clear dashboard cache to ensure new cases appear immediately
                self._clear_dashboard_cache()

                # Update dashboard summary
                self._update_dashboard_summary(case_number, report_html)

            return True

    def load_all_cases(self, username: str, role: str) -> List[Dict[str, Any]]:
        """Load cases based on role
        
        Args:
            username: Current user username
            role: User role for filtering
            
        Returns:
            List of case dictionaries
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/cases', headers=headers)
            if resp.ok:
                return resp.json()
            return []
        else:
            # Standalone: All cases visible
            cursor = self.conn.execute('SELECT case_number, assigned_to, status, trial_date, sentencing_date FROM reports')
            return [{'case_number': row['case_number'], 'assigned_to': row['assigned_to'], 'status': row['status'], 'trial_date': row['trial_date'], 'sentencing_date': row['sentencing_date']} for row in cursor]

    def get_cases_with_details(self, limit: Optional[int] = None, offset: int = 0, include_archived: bool = False) -> List[Dict[str, Any]]:
        """Get cases with evidence and legal details for dashboard with batch queries and caching
        
        Args:
            limit: Maximum number of cases to return
            offset: Number of cases to skip
            include_archived: Whether to include archived cases (default: False)
            
        Returns:
            List of case dictionaries with details
        """
        cache_key = f"dashboard_cases_{limit}_{offset}_{include_archived}"
        now = datetime.now()

        # Check cache
        if cache_key in self._dashboard_cache and cache_key in self._cache_expiry:
            if now < self._cache_expiry[cache_key]:
                return self._dashboard_cache[cache_key]

        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            params = {}
            if limit:
                params['limit'] = limit
            if offset:
                params['offset'] = offset
            if not include_archived:
                params['include_archived'] = 'false'
            resp = requests.get(f'{SERVER_URL}/cases/details', headers=headers, params=params)
            result = resp.json() if resp.ok else []
        else:
            # Batch query approach: Load all cases first, then batch load evidence and legal details
            query = 'SELECT case_number, assigned_to, status, trial_date, sentencing_date FROM reports'
            query_params = []
            
            # Filter out archived cases unless explicitly requested
            if not include_archived:
                query += ' WHERE (archived IS NULL OR archived = 0)'
            
            if limit is not None and isinstance(limit, int) and limit > 0:
                query += ' LIMIT ?'
                query_params.append(limit)
                if offset is not None and isinstance(offset, int) and offset >= 0:
                    query += ' OFFSET ?'
                    query_params.append(offset)
            
            cursor = self.conn.execute(query, query_params)
            cases = []
            case_numbers = []

            for row in cursor:
                case_numbers.append(row['case_number'])
                case = {
                    'id': row['case_number'],
                    'assigned_to': row['assigned_to'],
                    'status': row['status'],
                    'trial_date': row['trial_date'],
                    'sentencing_date': row['sentencing_date'],
                    'evidence_details': [],
                    'legal_details': []
                }
                cases.append(case)

            if case_numbers:
                # Batch load evidence details for all cases
                placeholders = ','.join('?' * len(case_numbers))
                evidence_cursor = self.conn.execute(f'''
                    SELECT id, case_number, evidence_item_number, item_type, imaging_status, imaged_date, analyzed_date, completed_date
                    FROM evidence_items WHERE case_number IN ({placeholders})
                ''', case_numbers)
                evidence_by_case = {}
                for row in evidence_cursor:
                    case_num = row['case_number']
                    if case_num not in evidence_by_case:
                        evidence_by_case[case_num] = []
                    evidence_by_case[case_num].append({
                        'id': row['id'],
                        'evidence_item_number': row['evidence_item_number'],
                        'type': row['item_type'],
                        'imaging_status': row['imaging_status'],
                        'imaged_date': row['imaged_date'],
                        'analyzed_date': row['analyzed_date'],
                        'completed_date': row['completed_date']
                    })

                # Batch load legal details for all cases
                legal_cursor = self.conn.execute(f'''
                    SELECT id, case_number, process_type, provider, status, submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, ndr
                    FROM legal_processes WHERE case_number IN ({placeholders})
                ''', case_numbers)
                legal_by_case = {}
                today = datetime.now()
                for row in legal_cursor:
                    case_num = row['case_number']
                    if case_num not in legal_by_case:
                        legal_by_case[case_num] = []
                    detail = {
                        'id': row['id'],
                        'type': row['process_type'],
                        'provider': row['provider'] or '',
                        'status': row['status'],
                        'submission_date': row['submission_date'],
                        'due_date': row['due_date'],
                        'expiration_date': row['expiration_date'],
                        'received_date': row['received_date'],
                        'analysis_start_date': row['analysis_start_date'],
                        'completed_date': row['completed_date']
                    }
                    # Calculate color based on status and dates
                    color = 'green' if detail['status'] in ['completed', 'no_longer_needed'] else 'yellow'
                    if detail['type'] == 'preservation' and detail['expiration_date']:
                        try:
                            exp = datetime.fromisoformat(detail['expiration_date'])
                            days_left = (exp - today).days
                            if days_left <= 0:
                                color = 'red'
                            elif days_left <= 10:
                                color = 'yellow'
                        except ValueError:
                            pass
                    elif detail['type'] in ['subpoena', 'warrant'] and detail['due_date']:
                        try:
                            due = datetime.fromisoformat(detail['due_date'])
                            if due < today and detail['status'] != 'completed':
                                color = 'red'
                        except ValueError:
                            pass
                    detail['suggested_color'] = color
                    legal_by_case[case_num].append(detail)

                # Batch load leads details for all cases
                leads_cursor = self.conn.execute(f'''
                    SELECT id, case_number, name, description, source, completed, created_date
                    FROM investigative_leads WHERE case_number IN ({placeholders})
                ''', case_numbers)
                leads_by_case = {}
                for row in leads_cursor:
                    case_num = row['case_number']
                    if case_num not in leads_by_case:
                        leads_by_case[case_num] = []
                    leads_by_case[case_num].append({
                        'id': row['id'],
                        'name': row['name'],
                        'description': row['description'],
                        'source': row['source'],
                        'completed': bool(row['completed']),
                        'created_date': row['created_date']
                    })

                # Assign batched data to cases
                for case in cases:
                    case_num = case['id']
                    case['evidence_details'] = evidence_by_case.get(case_num, [])
                    case['legal_details'] = legal_by_case.get(case_num, [])
                    case['leads_details'] = leads_by_case.get(case_num, [])

            result = cases

        # Cache the result for 5-10 minutes
        self._dashboard_cache[cache_key] = result
        self._cache_expiry[cache_key] = now + timedelta(minutes=7)  # 7 minutes cache

        return result

    def _local_get_evidence_details(self, case_number):
        cursor = self.conn.execute('''
            SELECT id, evidence_item_number, item_type, imaging_status, imaged_date, analyzed_date, completed_date
            FROM evidence_items WHERE case_number = ?
        ''', (case_number,))
        details = []
        for row in cursor:
            details.append({
                'id': row['id'],
                'evidence_item_number': row['evidence_item_number'],
                'type': row['item_type'],
                'imaging_status': row['imaging_status'],
                'imaged_date': row['imaged_date'],
                'analyzed_date': row['analyzed_date'],
                'completed_date': row['completed_date']
            })
        return details

    def _local_get_legal_details(self, case_number):
        cursor = self.conn.execute('''
            SELECT id, process_type, provider, status, submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, ndr
            FROM legal_processes WHERE case_number = ?
        ''', (case_number,))
        details = []
        today = datetime.now()
        for row in cursor:
            detail = {
                'id': row['id'],
                'type': row['process_type'],
                'provider': row['provider'] or '',
                'status': row['status'],
                'submission_date': row['submission_date'],
                'due_date': row['due_date'],
                'expiration_date': row['expiration_date'],
                'received_date': row['received_date'],
                'analysis_start_date': row['analysis_start_date'],
                'completed_date': row['completed_date']
            }
            color = 'green' if detail['status'] in ['completed', 'no_longer_needed'] else 'yellow'
            if detail['type'] == 'preservation' and detail['expiration_date']:
                exp = datetime.fromisoformat(detail['expiration_date'])
                days_left = (exp - today).days
                if days_left <= 0:
                    color = 'red'
                elif days_left <= 10:
                    color = 'yellow'
            elif detail['type'] in ['subpoena', 'warrant'] and detail['due_date']:
                due = datetime.fromisoformat(detail['due_date'])
                if due < today and detail['status'] != 'completed':
                    color = 'red'
            detail['suggested_color'] = color
            details.append(detail)
        return details

    # ------------------------------------------------------------------
    # Workflow Operations
    # ------------------------------------------------------------------

    def submit_case(self, case_number):
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/submit', headers=headers)
            return resp.ok
        else:
            # Get current status and validate transition
            cursor = self.conn.execute("SELECT status FROM reports WHERE case_number = ?", (case_number,))
            row = cursor.fetchone()
            current_status = row['status'] if row else None
            
            try:
                StatusValidator.validate_case_status_transition(current_status, 'submitted')
            except StatusTransitionError as e:
                logger.error(f"Invalid case status transition: {e}")
                return False
            
            with self.conn:
                self.conn.execute("UPDATE reports SET status = 'submitted' WHERE case_number = ?", (case_number,))
            return True

    def approve_case(self, case_number):
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/approve', headers=headers)
            return resp.ok
        else:
            # Get current status and validate transition
            cursor = self.conn.execute("SELECT status FROM reports WHERE case_number = ?", (case_number,))
            row = cursor.fetchone()
            current_status = row['status'] if row else None
            
            try:
                StatusValidator.validate_case_status_transition(current_status, 'approved')
            except StatusTransitionError as e:
                logger.error(f"Invalid case status transition: {e}")
                return False
            
            with self.conn:
                self.conn.execute("UPDATE reports SET status = 'approved' WHERE case_number = ?", (case_number,))
            return True

    def reject_case(self, case_number, comments):
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/reject', json={'comments': comments}, headers=headers)
            return resp.ok
        else:
            # Get current status and validate transition
            cursor = self.conn.execute("SELECT status FROM reports WHERE case_number = ?", (case_number,))
            row = cursor.fetchone()
            current_status = row['status'] if row else None
            
            try:
                StatusValidator.validate_case_status_transition(current_status, 'revisions_needed')
            except StatusTransitionError as e:
                logger.error(f"Invalid case status transition: {e}")
                return False
            
            with self.conn:
                self.conn.execute("UPDATE reports SET status = 'revisions_needed', review_comments = ? WHERE case_number = ?", (comments, case_number))
            return True

    def close_case(self, case_number):
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/close', headers=headers)
            return resp.ok
        else:
            # Get current status and validate transition
            cursor = self.conn.execute("SELECT status FROM reports WHERE case_number = ?", (case_number,))
            row = cursor.fetchone()
            current_status = row['status'] if row else None
            
            try:
                StatusValidator.validate_case_status_transition(current_status, 'closed')
            except StatusTransitionError as e:
                logger.error(f"Invalid case status transition: {e}")
                return False
            
            with self.conn:
                self.conn.execute("UPDATE reports SET status = 'closed' WHERE case_number = ?", (case_number,))
            return True

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def add_legal_process(self, case_number, process_type, provider, submission_date=None, due_date=None, expiration_date=None, received_date=None, analysis_start_date=None, completed_date=None, notes=None, ndr=False, expected_response_days=None):
        """Add a new legal process with optional SLA tracking"""
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'case_number': case_number,
                'process_type': process_type,
                'provider': provider,
                'submission_date': submission_date,
                'due_date': due_date,
                'expiration_date': expiration_date,
                'received_date': received_date,
                'analysis_start_date': analysis_start_date,
                'completed_date': completed_date,
                'notes': notes,
                'ndr': ndr,
                'expected_response_days': expected_response_days
            }
            resp = requests.post(f'{SERVER_URL}/legal_processes', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO legal_processes
                    (case_number, process_type, provider, submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, notes, ndr, expected_response_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (case_number, process_type, provider, submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, notes, int(ndr), expected_response_days))
            
            # Update the legal status cache for this case
            self.update_legal_status_cache(case_number)
            
            # Clear dashboard cache to reflect new legal process
            self._clear_dashboard_cache()
            
            return True

    def update_legal_process_status(self, process_id: int, status: str, date_field: Optional[str] = None, date_value: Optional[str] = None) -> bool:
        """Update legal process status and optional date field. Prevents SQL injection via whitelist.
        
        Args:
            process_id: Process ID to update
            status: New status value
            date_field: Optional field name to update
            date_value: Optional value for the date field
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ValueError: If date_field is not in whitelist
            StatusTransitionError: If status transition is invalid
        """
        # Whitelist of allowed date field names — validate early, before any DB lookup
        ALLOWED_DATE_FIELDS = {
            'submission_date', 'due_date', 'expiration_date', 'received_date',
            'analysis_start_date', 'completed_date'
        }

        if date_field and date_field not in ALLOWED_DATE_FIELDS:
            raise ValueError(f"Invalid date field: {date_field}. Allowed: {ALLOWED_DATE_FIELDS}")

        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {'status': status}
            if date_field and date_value:
                data[date_field] = date_value
            resp = requests.put(f'{SERVER_URL}/legal_processes/{process_id}', json=data, headers=headers)
            return resp.ok
        else:
            # Get current status and case_number for validation and cache update
            cursor = self.conn.execute(
                'SELECT status, case_number FROM legal_processes WHERE id = ?',
                (process_id,)
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Legal process {process_id} not found")
                return False
            
            current_status = row['status']
            case_number = row['case_number']
            
            # Validate status transition using state machine
            if not StatusValidator.validate_legal_status_transition(current_status, status):
                raise StatusTransitionError(
                    f"Invalid legal status transition from '{current_status}' to '{status}'"
                )
            
            with self.conn:
                if date_field and date_value:
                    # date_field already validated against whitelist above
                    query = f'UPDATE legal_processes SET status = ?, {date_field} = ? WHERE id = ?'
                    self.conn.execute(query, (status, date_value, process_id))
                else:
                    self.conn.execute('UPDATE legal_processes SET status = ? WHERE id = ?', (status, process_id))
            
            # Update the legal status cache for this case
            self.update_legal_status_cache(case_number)
            
            # Trigger notification if status changed
            if current_status != status and hasattr(self, 'notification_manager'):
                from notification_manager import create_status_change_notification
                # Get process type for better description
                cursor = self.conn.execute('SELECT process_type FROM legal_processes WHERE id = ?', (process_id,))
                row = cursor.fetchone()
                if row:
                    process_type = row['process_type']
                    create_status_change_notification(
                        self.notification_manager,
                        case_number,
                        'legal',
                        process_id,
                        current_status,
                        status,
                        process_type.replace('_', ' ').title()
                    )
            
            # Clear dashboard cache to reflect updated legal process status
            self._clear_dashboard_cache()
            
            return True

    def add_evidence(self, case_number, evidence_item_number, item_type, physical_description=None, digital_make=None, digital_model=None, digital_type=None, digital_sn=None, digital_storage_size=None, password=None):
        """Add a new evidence item. Passwords stored in plain text for device access."""
        # Store password as-is (not hashed) - these are device passwords that need to be readable
        
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'case_number': case_number,
                'evidence_item_number': evidence_item_number,
                'item_type': item_type,
                'physical_description': physical_description,
                'digital_make': digital_make,
                'digital_model': digital_model,
                'digital_type': digital_type,
                'digital_sn': digital_sn,
                'digital_storage_size': digital_storage_size,
                'password': password  # Store plain text password
            }
            resp = requests.post(f'{SERVER_URL}/evidence', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO evidence_items
                    (case_number, evidence_item_number, item_type, physical_description, digital_make, digital_model, digital_type, digital_sn, digital_storage_size, password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (case_number, evidence_item_number, item_type, physical_description, digital_make, digital_model, digital_type, digital_sn, digital_storage_size, password))
                
                # Clear dashboard cache to reflect new evidence
                self._clear_dashboard_cache()
                
            return True

    def add_investigative_lead(self, case_number: str, name: str, description: str, source: str) -> bool:
        """Add a new investigative lead
        
        Args:
            case_number: Associated case number
            name: Lead name
            description: Lead description
            source: Lead source
            
        Returns:
            True if insert successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'case_number': case_number,
                'name': name,
                'description': description,
                'source': source,
                'created_date': datetime.now().isoformat()
            }
            resp = requests.post(f'{SERVER_URL}/investigative_leads', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('''
                    INSERT INTO investigative_leads
                    (case_number, name, description, source, created_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (case_number, name, description, source, datetime.now().isoformat()))
            return True

    def update_lead_completion(self, lead_id, completed):
        """Update the completion status of an investigative lead"""
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {'completed': completed}
            resp = requests.put(f'{SERVER_URL}/investigative_leads/{lead_id}', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('UPDATE investigative_leads SET completed = ? WHERE id = ?', (int(completed), lead_id))
            return True

    def load_investigative_leads(self, case_number: str) -> List[Dict[str, Any]]:
        """Load investigative leads for a case
        
        Args:
            case_number: Case number to load leads for
            
        Returns:
            List of investigative lead dictionaries
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/investigative_leads/{case_number}', headers=headers)
            return resp.json() if resp.ok else []
        else:
            cursor = self.conn.execute('''
                SELECT id, name, description, source, completed, created_date
                FROM investigative_leads WHERE case_number = ?
                ORDER BY created_date DESC
            ''', (case_number,))
            leads = []
            for row in cursor:
                leads.append({
                    'id': row['id'],
                    'name': row['name'],
                    'description': row['description'],
                    'source': row['source'],
                    'completed': bool(row['completed']),
                    'created_date': row['created_date']
                })
            return leads

    def close(self) -> None:
        """Close database connection if open"""
        if self.conn:
            self.conn.close()

    def update_case_dates(self, case_number: str, trial_date: Optional[str] = None, sentencing_date: Optional[str] = None) -> bool:
        """Update trial and sentencing dates for a case (local or server mode).
        
        Args:
            case_number: Case number to update
            trial_date: Optional new trial date
            sentencing_date: Optional new sentencing date
            
        Returns:
            True if update successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            data = {'trial_date': trial_date, 'sentencing_date': sentencing_date}
            resp = requests.put(f'{SERVER_URL}/cases/{case_number}/dates', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('UPDATE reports SET trial_date = ?, sentencing_date = ? WHERE case_number = ?', (trial_date, sentencing_date, case_number))
            return True

    # ------------------------------------------------------------------
    # Case Events (Calendar Integration)
    # ------------------------------------------------------------------

    def add_case_event(
        self,
        case_number: str,
        event_type: str,
        event_date: str,
        title: str,
        details: Optional[str] = None,
        related_id: Optional[int] = None,
        severity: str = 'info',
        allow_duplicate: bool = False
    ) -> Optional[int]:
        """Add a case event for calendar and timeline views."""
        if SERVER_URL:
            logger.info("Case events are not persisted in server mode")
            return None

        if not event_date:
            return None

        with self.conn:
            if not allow_duplicate:
                if related_id is None:
                    self.conn.execute('''
                        DELETE FROM case_events
                        WHERE case_number = ? AND event_type = ? AND event_date = ? AND related_id IS NULL
                    ''', (case_number, event_type, event_date))
                else:
                    self.conn.execute('''
                        DELETE FROM case_events
                        WHERE case_number = ? AND event_type = ? AND event_date = ? AND related_id = ?
                    ''', (case_number, event_type, event_date, related_id))

            created_date = datetime.now().isoformat()
            cursor = self.conn.execute('''
                INSERT INTO case_events
                (case_number, event_type, event_date, title, details, related_id, severity, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (case_number, event_type, event_date, title, details, related_id, severity, created_date))
            return cursor.lastrowid

    def get_case_events_on_date(self, event_date: str) -> List[Dict[str, Any]]:
        """Get case events for a specific date (YYYY-MM-DD)."""
        if SERVER_URL:
            return []

        cursor = self.conn.execute('''
            SELECT * FROM case_events
            WHERE event_date = ?
            ORDER BY created_date ASC
        ''', (event_date,))
        return [dict(row) for row in cursor.fetchall()]

    def get_case_event_map(self) -> Dict[str, set]:
        """Get a mapping of event_date -> set of event types."""
        if SERVER_URL:
            return {}

        cursor = self.conn.execute('''
            SELECT event_date, event_type FROM case_events
        ''')

        event_map: Dict[str, set] = {}
        for row in cursor.fetchall():
            event_map.setdefault(row['event_date'], set()).add(row['event_type'])
        return event_map

    def add_court_date(self, case_number: str, date_type: str, court_date: str, notes: Optional[str] = None, event_time: Optional[str] = None, location: Optional[str] = None) -> bool:
        """Add a new court date
        
        Args:
            case_number: Associated case number
            date_type: Type of court date
            court_date: The court date value
            notes: Optional notes about the date
            event_time: Optional event time
            location: Optional court location
            
        Returns:
            True if insert successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {
                'case_number': case_number,
                'date_type': date_type,
                'court_date': court_date,
                'notes': notes,
                'event_time': event_time,
                'location': location
            }
            resp = requests.post(f'{SERVER_URL}/court_dates', json=data, headers=headers)
            return resp.ok
        else:
            with self.conn:
                if date_type == 'trial':
                    # For trial, update the reports table trial_date column
                    self.conn.execute('UPDATE reports SET trial_date = ? WHERE case_number = ?', (court_date, case_number))
                else:
                    # For other types, add to court_dates table
                    self.conn.execute('''
                        INSERT INTO court_dates
                        (case_number, date_type, court_date, notes, event_time, location)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (case_number, date_type, court_date, notes, event_time, location))
            return True

    def load_court_dates(self, case_number: str) -> List[Dict[str, Any]]:
        """Load court dates for a case
        
        Args:
            case_number: Case number to load dates for
            
        Returns:
            List of court date dictionaries
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/court_dates/{case_number}', headers=headers)
            return resp.json() if resp.ok else []
        else:
            cursor = self.conn.execute('''
                SELECT id, date_type, court_date, notes, event_time, location
                FROM court_dates WHERE case_number = ?
                ORDER BY court_date ASC
            ''', (case_number,))
            dates = []
            for row in cursor:
                dates.append({
                    'id': row['id'],
                    'date_type': row['date_type'],
                    'court_date': row['court_date'],
                    'notes': row['notes'],
                    'event_time': row['event_time'],
                    'location': row['location']
                })
            return dates

    def get_earliest_court_date(self, case_number: str) -> Optional[str]:
        """Get the earliest hearing or court date for dashboard
        
        Args:
            case_number: Case number to get dates for
            
        Returns:
            Earliest court date string or None if no dates found
        """
        dates = self.load_court_dates(case_number)
        hearing_court_dates = [d['court_date'] for d in dates if d['date_type'] in ['hearing', 'court']]
        if hearing_court_dates:
            return min(hearing_court_dates)
        return None

    def get_sentencing_date(self, case_number: str) -> Optional[str]:
        """Get the sentencing date for dashboard
        
        Args:
            case_number: Case number to get date for
            
        Returns:
            Sentencing date string or None if not found
        """
        dates = self.load_court_dates(case_number)
        sentencing_dates = [d['court_date'] for d in dates if d['date_type'] == 'sentencing']
        if sentencing_dates:
            return min(sentencing_dates)  # Assuming earliest if multiple
        return None

    def update_evidence_field(self, evidence_id: int, field: str, value: Any) -> bool:
        """Update a single field of an evidence item. Prevents SQL injection via whitelist.
        
        Args:
            evidence_id: ID of evidence item to update
            field: Field name to update (must be whitelisted)
            value: New value for the field
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ValueError: If field is not in whitelist
            StatusTransitionError: If status transition is invalid
        """
        # Whitelist of allowed evidence field names
        ALLOWED_FIELDS = {
            'evidence_item_number', 'item_type', 'physical_description', 'digital_make',
            'digital_model', 'digital_type', 'digital_sn', 'digital_storage_size', 'password',
            'imaged_date', 'analyzed_date', 'completed_date', 'evidence_found', 'imaging_status'
        }
        
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            data = {field: value}
            resp = requests.put(f'{SERVER_URL}/evidence/{evidence_id}', json=data, headers=headers)
            return resp.ok
        else:
            # Validate field against whitelist to prevent SQL injection
            if field not in ALLOWED_FIELDS:
                raise ValueError(f"Invalid evidence field: {field}. Allowed: {ALLOWED_FIELDS}")
            
            # Get old value and case info for notifications
            old_status = None
            case_number = None
            evidence_number = None
            if field == 'imaging_status':
                cursor = self.conn.execute(
                    'SELECT imaging_status, case_number, evidence_item_number FROM evidence_items WHERE id = ?',
                    (evidence_id,)
                )
                row = cursor.fetchone()
                if row:
                    old_status = row['imaging_status']
                    case_number = row['case_number']
                    evidence_number = row['evidence_item_number']
                    
                    # Validate transition using state machine
                    if not StatusValidator.validate_evidence_status_transition(old_status, value):
                        raise StatusTransitionError(
                            f"Invalid evidence status transition from '{old_status}' to '{value}'"
                        )
            
            with self.conn:
                # Safe to use in f-string now that it's whitelisted
                query = f'UPDATE evidence_items SET {field} = ? WHERE id = ?'
                self.conn.execute(query, (value, evidence_id))
            
            # Trigger notification if imaging status changed
            if field == 'imaging_status' and old_status and old_status != value and hasattr(self, 'notification_manager'):
                from notification_manager import create_status_change_notification
                create_status_change_notification(
                    self.notification_manager,
                    case_number,
                    'evidence',
                    evidence_id,
                    old_status,
                    value,
                    f"Evidence {evidence_number}"
                )

                # Record calendar event for evidence status change
                status_event_map = {
                    'not_imaged': 'evidence_not_imaged',
                    'imaged': 'evidence_imaged',
                    'analyzed': 'evidence_analyzed',
                    'other': 'evidence_other'
                }
                event_type = status_event_map.get(str(value).lower(), 'evidence_status')
                event_title = f"Evidence {evidence_number} status: {str(value).replace('_', ' ').title()}"
                self.add_case_event(
                    case_number=case_number,
                    event_type=event_type,
                    event_date=datetime.now().strftime('%Y-%m-%d'),
                    title=event_title,
                    details=f"Evidence {evidence_number} status changed from {old_status} to {value}",
                    related_id=evidence_id,
                    severity='info'
                )
            
            # Clear dashboard cache to reflect updated evidence field
            self._clear_dashboard_cache()
            
            return True

    def update_evidence_item(self, evidence_id: int, **kwargs: Any) -> bool:
        """Update multiple fields of an evidence item. Prevents SQL injection via whitelist.
        
        Args:
            evidence_id: ID of evidence item to update
            **kwargs: Field=value pairs to update (all fields must be whitelisted)
            
        Returns:
            True if update successful, False otherwise
            
        Raises:
            ValueError: If any field is not in whitelist
            StatusTransitionError: If status transition is invalid
        """
        # Whitelist of allowed evidence field names
        ALLOWED_FIELDS = {
            'evidence_item_number', 'item_type', 'physical_description', 'digital_make',
            'digital_model', 'digital_type', 'digital_sn', 'digital_storage_size', 'password',
            'imaged_date', 'analyzed_date', 'completed_date', 'evidence_found', 'imaging_status'
        }
        
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.put(f'{SERVER_URL}/evidence/{evidence_id}', json=kwargs, headers=headers)
            return resp.ok
        else:
            # Validate all fields against whitelist
            invalid_fields = set(kwargs.keys()) - ALLOWED_FIELDS
            if invalid_fields:
                raise ValueError(f"Invalid evidence fields: {invalid_fields}. Allowed: {ALLOWED_FIELDS}")
            
            # Validate evidence status transitions if status is being updated
            if 'imaging_status' in kwargs:
                # Get current status
                cursor = self.conn.execute(
                    'SELECT imaging_status FROM evidence_items WHERE id = ?',
                    (evidence_id,)
                )
                row = cursor.fetchone()
                if row:
                    current_status = row['imaging_status']
                    new_status = kwargs['imaging_status']
                    # Validate transition using state machine
                    if not StatusValidator.validate_evidence_status_transition(current_status, new_status):
                        raise StatusTransitionError(
                            f"Invalid evidence status transition from '{current_status}' to '{new_status}'"
                        )
            
            # Safe to build query now that fields are whitelisted
            set_clause = ', '.join([f'{k} = ?' for k in kwargs.keys()])
            values = list(kwargs.values()) + [evidence_id]
            with self.conn:
                query = f'UPDATE evidence_items SET {set_clause} WHERE id = ?'
                self.conn.execute(query, values)
            
            # Clear dashboard cache to reflect updated evidence
            self._clear_dashboard_cache()
            
            return True

    def delete_evidence_item(self, evidence_id):
        """Delete an evidence item"""
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'}
            resp = requests.delete(f'{SERVER_URL}/evidence/{evidence_id}', headers=headers)
            return resp.ok
        else:
            with self.conn:
                self.conn.execute('DELETE FROM evidence_items WHERE id = ?', (evidence_id,))
            
            # Clear dashboard cache to reflect deleted evidence
            self._clear_dashboard_cache()
            
            return True

    def _ensure_db_available(self):
        """
        Check if database is available and accessible.
        Returns True if safe to perform database operations.
        """
        if self._readonly_mode or not self._db_accessible:
            logger.warning("Database is in read-only mode or not accessible")
            return False
        return True
    
    def get_database_status(self):
        """Get current database connection status and mode."""
        return {
            'accessible': self._db_accessible,
            'connected': self.conn is not None,
            'readonly_mode': self._readonly_mode,
            'safe_mode': self.safe_mode,
            'warning': 'Database operating in read-only mode' if self._readonly_mode else None,
        }

    def _clear_dashboard_cache(self):
        """Clear all dashboard cache entries to ensure fresh data on next refresh"""
        dashboard_cache_keys = [k for k in self._dashboard_cache.keys() if k.startswith('dashboard_cases_')]
        for key in dashboard_cache_keys:
            del self._dashboard_cache[key]
            if key in self._cache_expiry:
                del self._cache_expiry[key]

    def _update_dashboard_summary(self, case_number, report_html):
        """Update the dashboard summary for a case"""
        # Extract a simple text summary from the HTML (first 200 characters)
        import re
        # Remove HTML tags and get plain text
        clean_text = re.sub(r'<[^>]+>', '', report_html)
        summary = clean_text[:200] + '...' if len(clean_text) > 200 else clean_text

        with self.conn:
            self.conn.execute('''
                INSERT OR REPLACE INTO dashboard_summaries
                (case_number, summary_text, last_updated)
                VALUES (?, ?, ?)
            ''', (case_number, summary, datetime.now().isoformat()))
    
    def update_legal_status_cache(self, case_number: str) -> bool:
        """
        Update the cached legal status summary for a case.
        
        This should be called whenever legal processes are added, updated, or deleted.
        Calculates pending and overdue counts and stores them in the reports table.
        
        Args:
            case_number: Case number to update cache for
            
        Returns:
            True if update successful
        """
        if SERVER_URL:
            # In server mode, the server handles caching
            return True
        
        try:
            # Get all legal processes for this case
            cursor = self.conn.execute('''
                SELECT status, due_date 
                FROM legal_processes 
                WHERE case_number = ?
            ''', (case_number,))
            
            legal_items = cursor.fetchall()
            
            # Calculate pending and overdue counts
            pending_count = 0
            overdue_count = 0
            today = datetime.now().date()
            
            for item in legal_items:
                status = item['status']
                due_date_str = item['due_date']
                
                # Count as pending if not completed or cancelled
                if status not in ['completed', 'no_longer_needed', 'cancelled']:
                    pending_count += 1
                    
                    # Check if overdue
                    if due_date_str:
                        try:
                            due_date = datetime.fromisoformat(due_date_str).date()
                            if due_date < today:
                                overdue_count += 1
                        except (ValueError, AttributeError):
                            pass  # Invalid date format, skip
            
            # Update the cache in reports table
            with self.conn:
                self.conn.execute('''
                    UPDATE reports 
                    SET legal_pending_count = ?,
                        legal_overdue_count = ?,
                        legal_summary_updated = ?
                    WHERE case_number = ?
                ''', (pending_count, overdue_count, datetime.now().isoformat(), case_number))
            
            logger.info(f"Updated legal status cache for case {case_number}: {pending_count} pending, {overdue_count} overdue")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update legal status cache for {case_number}: {e}")
            return False
    
    def get_legal_status_from_cache(self, case_number: str) -> Dict[str, Any]:
        """
        Get cached legal status summary for a case.
        
        Args:
            case_number: Case number to retrieve cache for
            
        Returns:
            Dict with 'pending_count', 'overdue_count', and 'last_updated'
        """
        if SERVER_URL:
            # In server mode, fetch from API
            return {'pending_count': 0, 'overdue_count': 0, 'last_updated': None}
        
        try:
            cursor = self.conn.execute('''
                SELECT legal_pending_count, legal_overdue_count, legal_summary_updated
                FROM reports
                WHERE case_number = ?
            ''', (case_number,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'pending_count': row['legal_pending_count'] or 0,
                    'overdue_count': row['legal_overdue_count'] or 0,
                    'last_updated': row['legal_summary_updated']
                }
            
            return {'pending_count': 0, 'overdue_count': 0, 'last_updated': None}
            
        except Exception as e:
            logger.error(f"Failed to get legal status cache for {case_number}: {e}")
            return {'pending_count': 0, 'overdue_count': 0, 'last_updated': None}

    # ------------------------------------------------------------------
    # Archive Operations
    # ------------------------------------------------------------------

    def archive_case(self, case_number: str, user: str, reason: str = None, archive_date: str = None) -> bool:
        """
        Archive a closed case.
        
        Args:
            case_number: Case number to archive
            user: Username performing the archive
            reason: Optional reason for archiving
            archive_date: Optional custom archive date (ISO format), defaults to now
            
        Returns:
            True if successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            data = {
                'archived_by': user,
                'archive_reason': reason,
                'archived_date': archive_date or datetime.now().isoformat()
            }
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/archive', json=data, headers=headers)
            return resp.ok
        
        try:
            # Check if case is closed
            cursor = self.conn.execute('SELECT status FROM reports WHERE case_number = ?', (case_number,))
            row = cursor.fetchone()
            
            if not row:
                logger.error(f"Case {case_number} not found")
                return False
            
            if row['status'].lower() != 'closed':
                logger.error(f"Case {case_number} must be closed before archiving (current status: {row['status']})")
                return False
            
            # Archive the case
            archive_timestamp = archive_date or datetime.now().isoformat()
            
            with self.conn:
                self.conn.execute('''
                    UPDATE reports
                    SET archived = 1,
                        archived_date = ?,
                        archived_by = ?,
                        archive_reason = ?
                    WHERE case_number = ?
                ''', (archive_timestamp, user, reason, case_number))
            
            logger.info(f"Archived case {case_number} by {user}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to archive case {case_number}: {e}")
            return False

    def restore_case(self, case_number: str, user: str) -> bool:
        """
        Restore an archived case to active status.
        
        Args:
            case_number: Case number to restore
            user: Username performing the restore
            
        Returns:
            True if successful, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            data = {'restored_by': user}
            resp = requests.post(f'{SERVER_URL}/cases/{case_number}/restore', json=data, headers=headers)
            return resp.ok
        
        try:
            with self.conn:
                self.conn.execute('''
                    UPDATE reports
                    SET archived = 0,
                        archived_date = NULL,
                        archived_by = NULL,
                        archive_reason = NULL
                    WHERE case_number = ?
                ''', (case_number,))
            
            logger.info(f"Restored case {case_number} by {user}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore case {case_number}: {e}")
            return False

    def get_archived_cases(self, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get list of archived cases with optional filters.
        
        Args:
            filters: Optional dictionary of filters (year, assigned_to, search_term)
            
        Returns:
            List of archived case dictionaries
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            params = filters or {}
            resp = requests.get(f'{SERVER_URL}/cases/archived', params=params, headers=headers)
            if resp.ok:
                return resp.json()
            return []
        
        try:
            query = '''
                SELECT case_number, assigned_to, status, archived_date, archived_by, archive_reason,
                       encrypted_metadata, trial_date, sentencing_date
                FROM reports
                WHERE archived = 1
            '''
            params = []
            
            if filters:
                if filters.get('year'):
                    query += " AND archived_date LIKE ?"
                    params.append(f"{filters['year']}%")
                
                if filters.get('assigned_to'):
                    query += " AND assigned_to = ?"
                    params.append(filters['assigned_to'])
                
                if filters.get('search_term'):
                    query += " AND (case_number LIKE ? OR encrypted_metadata LIKE ?)"
                    search = f"%{filters['search_term']}%"
                    params.extend([search, search])
            
            query += " ORDER BY archived_date DESC"
            
            cursor = self.conn.execute(query, params)
            rows = cursor.fetchall()
            
            cases = []
            for row in rows:
                case_data = {
                    'case_number': row['case_number'],
                    'assigned_to': row['assigned_to'],
                    'status': row['status'],
                    'archived_date': row['archived_date'],
                    'archived_by': row['archived_by'],
                    'archive_reason': row['archive_reason'],
                    'trial_date': row['trial_date'],
                    'sentencing_date': row['sentencing_date']
                }
                
                # Decrypt metadata for suspect info
                if row['encrypted_metadata']:
                    try:
                        metadata = json.loads(decrypt_data(row['encrypted_metadata']))
                        case_data['suspect'] = metadata.get('suspect', 'N/A')
                        case_data['agency'] = metadata.get('agency', 'N/A')
                    except Exception as e:
                        logger.warning(f"Failed to decrypt metadata for case {case_data.get('case_number', '?')}: {e}")
                        case_data['suspect'] = 'N/A'
                        case_data['agency'] = 'N/A'
                
                cases.append(case_data)
            
            return cases
            
        except Exception as e:
            logger.error(f"Failed to get archived cases: {e}")
            return []

    def is_case_archived(self, case_number: str) -> bool:
        """
        Check if a case is archived.
        
        Args:
            case_number: Case number to check
            
        Returns:
            True if archived, False otherwise
        """
        if SERVER_URL:
            headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
            resp = requests.get(f'{SERVER_URL}/cases/{case_number}/archived', headers=headers)
            if resp.ok:
                return resp.json().get('archived', False)
            return False
        
        try:
            cursor = self.conn.execute('SELECT archived FROM reports WHERE case_number = ?', (case_number,))
            row = cursor.fetchone()
            return bool(row and row['archived'])
        except Exception as e:
            logger.error(f"Failed to check archive status for {case_number}: {e}")
            return False

    # ------------------------------------------------------------------
    # User management (server mode only — requires admin/supervisor JWT)
    # ------------------------------------------------------------------

    def list_users(self, role_filter: str = '', active_only: bool = True) -> List[Dict[str, Any]]:
        """List user accounts. Server mode only."""
        if not SERVER_URL:
            return []
        params: Dict[str, Any] = {'active_only': str(active_only).lower()}
        if role_filter:
            params['role'] = role_filter
        try:
            resp = requests.get(
                f'{SERVER_URL}/api/v1/users',
                params=params,
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json().get('users', [])
            logger.warning(f'list_users failed: {resp.status_code}')
        except Exception as exc:
            logger.error(f'list_users error: {exc}')
        return []

    def create_user(self, username: str, role: str = 'writer') -> Optional[Dict[str, Any]]:
        """Create a new user account. Server mode only. Requires admin token."""
        if not SERVER_URL:
            return None
        try:
            resp = requests.post(
                f'{SERVER_URL}/api/v1/users',
                json={'username': username, 'role': role},
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json().get('user')
            logger.warning(f'create_user failed: {resp.status_code} {resp.text}')
        except Exception as exc:
            logger.error(f'create_user error: {exc}')
        return None

    def update_user(self, username: str, role: Optional[str] = None, is_active: Optional[bool] = None) -> Optional[Dict[str, Any]]:
        """Update a user's role or active status. Server mode only. Requires admin token."""
        if not SERVER_URL:
            return None
        payload: Dict[str, Any] = {}
        if role is not None:
            payload['role'] = role
        if is_active is not None:
            payload['is_active'] = is_active
        try:
            resp = requests.put(
                f'{SERVER_URL}/api/v1/users/{username}',
                json=payload,
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json().get('user')
            logger.warning(f'update_user failed: {resp.status_code} {resp.text}')
        except Exception as exc:
            logger.error(f'update_user error: {exc}')
        return None

    def deactivate_user(self, username: str) -> bool:
        """Deactivate (soft-delete) a user account. Server mode only. Requires admin token."""
        if not SERVER_URL:
            return False
        try:
            resp = requests.delete(
                f'{SERVER_URL}/api/v1/users/{username}',
                headers=self._auth_headers(),
                timeout=10,
            )
            return resp.ok
        except Exception as exc:
            logger.error(f'deactivate_user error: {exc}')
        return False

    # ------------------------------------------------------------------
    # Supervisor assignment management (server mode only)
    # ------------------------------------------------------------------

    def list_supervisor_assignments(self) -> List[Dict[str, Any]]:
        """List supervisor assignments. Server mode only. Requires admin/supervisor token."""
        if not SERVER_URL:
            return []
        try:
            resp = requests.get(
                f'{SERVER_URL}/api/v1/supervisor-assignments',
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json().get('assignments', [])
            logger.warning(f'list_supervisor_assignments failed: {resp.status_code}')
        except Exception as exc:
            logger.error(f'list_supervisor_assignments error: {exc}')
        return []

    def create_supervisor_assignment(self, supervisor: str, investigator: str, examiner: str = '') -> Optional[Dict[str, Any]]:
        """Create a supervisor assignment. Server mode only. Requires admin token."""
        if not SERVER_URL:
            return None
        payload: Dict[str, Any] = {'supervisor': supervisor, 'investigator': investigator}
        if examiner:
            payload['examiner'] = examiner
        try:
            resp = requests.post(
                f'{SERVER_URL}/api/v1/supervisor-assignments',
                json=payload,
                headers=self._auth_headers(),
                timeout=10,
            )
            if resp.ok:
                return resp.json().get('assignment')
            logger.warning(f'create_supervisor_assignment failed: {resp.status_code} {resp.text}')
        except Exception as exc:
            logger.error(f'create_supervisor_assignment error: {exc}')
        return None

    def delete_supervisor_assignment(self, assignment_id: int) -> bool:
        """Remove a supervisor assignment. Server mode only. Requires admin token."""
        if not SERVER_URL:
            return False
        try:
            resp = requests.delete(
                f'{SERVER_URL}/api/v1/supervisor-assignments/{assignment_id}',
                headers=self._auth_headers(),
                timeout=10,
            )
            return resp.ok
        except Exception as exc:
            logger.error(f'delete_supervisor_assignment error: {exc}')
        return False

