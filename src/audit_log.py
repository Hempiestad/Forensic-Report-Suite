# audit_log.py
import os
import json
import hashlib
import logging
import stat
from datetime import datetime
from PyQt5.QtWidgets import QAction, QMessageBox

logger = logging.getLogger(__name__)

class AuditLogger:
    def __init__(self, case_dir, case_number):
        """
        case_dir: Full path to case folder (e.g., cases/CASE123)
        case_number: For log identification
        """
        self.case_dir = case_dir
        self.case_number = case_number
        self.log_file = os.path.join(case_dir, "audit_trail.log")
        self.enabled = True
        self.toggle_action = None
        
        # Ensure audit log file has secure permissions (600 - owner read/write only)
        self._ensure_secure_permissions()

    def _ensure_secure_permissions(self):
        """Set audit log file to secure permissions (600)."""
        if os.path.exists(self.log_file):
            try:
                os.chmod(self.log_file, stat.S_IRUSR | stat.S_IWUSR)  # 600 permissions
            except Exception as e:
                logger.warning(f"Could not set file permissions on audit log: {e}")

    def add_toggle_to_toolbar(self, toolbar):
        """Add the audit log toggle action to the provided toolbar."""
        if self.toggle_action is None:
            self.toggle_action = QAction("Audit Log: ON", toolbar)
            self.toggle_action.setCheckable(True)
            self.toggle_action.setChecked(True)
            self.toggle_action.triggered.connect(self.toggle_logging)
            toolbar.addSeparator()
            toolbar.addAction(self.toggle_action)

    def toggle_logging(self, checked):
        self.enabled = checked
        status = "ENABLED" if checked else "DISABLED"
        self.toggle_action.setText(f"Audit Log: {status}")
        self.log("AUDIT_LOG_TOGGLE", {"enabled": checked})
        QMessageBox.information(None, "Audit Trail", f"Audit logging {status.lower()}.")

    def _get_last_hash(self):
        """Get the last entry's hash for tamper-evident logging"""
        if not os.path.exists(self.log_file):
            return "0" * 64
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return "0" * 64
                last_line = lines[-1].strip()
                last_entry = json.loads(last_line)
                # Return the hash of the last entry, not its prev_hash
                return last_entry.get("entry_hash", "0" * 64)
        except Exception as e:
            logger.warning(f"Could not read last audit hash: {e}")
            return "0" * 64

    def log(self, event_type, details=None):
        if not self.enabled:
            return

        prev_hash = self._get_last_hash()
        timestamp = datetime.now().isoformat()

        entry = {
            "timestamp": timestamp,
            "case_number": self.case_number,
            "event": event_type,
            "details": details or {},
            "prev_hash": prev_hash,
        }

        # Compute hash of this entry (tamper-proofing)
        entry_str = json.dumps(entry, sort_keys=True)
        entry_hash = hashlib.sha256(entry_str.encode('utf-8')).hexdigest()
        entry["entry_hash"] = entry_hash

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            
            # Ensure secure permissions after write
            self._ensure_secure_permissions()
        except Exception as e:
            logger.error(f"Audit log write failed: {e}")

    # Convenience methods
    def log_case_created(self, case_data):
        self.log("CASE_CREATED", {"case_data": case_data})

    def log_text_changed(self, char_count_before=None, char_count_after=None):
        summary = {}
        if char_count_before is not None and char_count_after is not None:
            diff = char_count_after - char_count_before
            summary["change"] = f"{diff:+} characters"
        self.log("REPORT_EDITED", summary)

    def log_appendix_added(self, filename):
        self.log("APPENDIX_ADDED", {"filename": filename})

    def log_appendix_removed(self, filename):
        self.log("APPENDIX_REMOVED", {"filename": filename})

    def log_pdf_finalized(self, pdf_path, pdf_hash):
        self.log("PDF_FINALIZED", {
            "pdf_file": os.path.basename(pdf_path),
            "sha256_hash": pdf_hash
        })

    def log_footnote_inserted(self, term, footnote_number):
        self.log("GLOSSARY_FOOTNOTE_ADDED", {
            "term": term,
            "footnote_number": footnote_number
        })

    def log_evidence_added(self, evidence_item_number, item_type):
        self.log("EVIDENCE_ADDED", {
            "evidence_item_number": evidence_item_number,
            "item_type": item_type
        })

    def log_legal_process_added(self, process_type, provider):
        self.log("LEGAL_PROCESS_ADDED", {
            "process_type": process_type,
            "provider": provider
        })

    def log_lead_added(self, name, source):
        self.log("LEAD_ADDED", {
            "name": name,
            "source": source
        })

    def log_lead_completion_updated(self, lead_id, completed):
        self.log("LEAD_COMPLETION_UPDATED", {
            "lead_id": lead_id,
            "completed": completed
        })

    def log_court_date_added(self, date_type, court_date):
        self.log("COURT_DATE_ADDED", {
            "date_type": date_type,
            "court_date": court_date
        })

    def log_evidence_updated(self, evidence_id, field, new_value):
        self.log("EVIDENCE_UPDATED", {
            "evidence_id": evidence_id,
            "field": field,
            "new_value": new_value
        })

    def log_evidence_deleted(self, evidence_id, evidence_item_number):
        self.log("EVIDENCE_DELETED", {
            "evidence_id": evidence_id,
            "evidence_item_number": evidence_item_number
        })
