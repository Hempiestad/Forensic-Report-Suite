"""
TemplateCategory — 25 organised template categories (mirrors C# TemplateCategory.cs).

Groups:
  - Standard Reports (6)
  - Specialised Reports (4)
  - Legal / Court Documents (5)
  - Note Templates (7)
  - Informal / General (3)
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List


class TemplateCategory(str, Enum):
    # ── Standard Reports ────────────────────────────────────────────────
    SWGDE_NIST = "swgde_nist"
    MOBILE_DEVICE = "mobile_device"
    NETWORK_FORENSICS = "network_forensics"
    CLOUD_FORENSICS = "cloud_forensics"
    EMAIL_FORENSICS = "email_forensics"
    DATABASE_FORENSICS = "database_forensics"

    # ── Specialised Reports ──────────────────────────────────────────────
    INTRUSION_INVESTIGATION = "intrusion_investigation"
    MALWARE_ANALYSIS = "malware_analysis"
    DATA_BREACH = "data_breach"
    INCIDENT_RESPONSE = "incident_response"

    # ── Legal / Court Documents ─────────────────────────────────────────
    EVIDENCE_INTAKE = "evidence_intake"
    CHAIN_OF_CUSTODY = "chain_of_custody"
    LEGAL_DOCUMENT = "legal_document"
    SUBPOENA_RESPONSE = "subpoena_response"
    COURT_PRESENTATION = "court_presentation"

    # ── Note Templates ───────────────────────────────────────────────────
    INVESTIGATION_TIMELINE = "investigation_timeline"
    PERSON_PROFILE = "person_profile"
    EVIDENCE_LOG = "evidence_log"
    INTERVIEW_NOTES = "interview_notes"
    OBSERVATION_LOG = "observation_log"
    TECHNICAL_FINDINGS = "technical_findings"
    CONCLUSIONS = "conclusions"

    # ── Informal / General ───────────────────────────────────────────────
    BASIC = "basic"
    MEMO = "memo"
    CHECKLIST = "checklist"

    # ------------------------------------------------------------------ #
    # Metadata                                                              #
    # ------------------------------------------------------------------ #

    @property
    def display_name(self) -> str:
        return self.value.replace("_", " ").title()

    @property
    def description(self) -> str:
        _desc: Dict[str, str] = {
            "swgde_nist": "SWGDE/NIST standard digital forensic examination report",
            "mobile_device": "Mobile device forensic examination",
            "network_forensics": "Network traffic and log analysis",
            "cloud_forensics": "Cloud service and storage investigation",
            "email_forensics": "Email header and content analysis",
            "database_forensics": "Database forensic examination",
            "intrusion_investigation": "Network intrusion and unauthorised access",
            "malware_analysis": "Malware and suspicious code analysis",
            "data_breach": "Data breach investigation and impact assessment",
            "incident_response": "Security incident response documentation",
            "evidence_intake": "Evidence receipt and intake form",
            "chain_of_custody": "Chain of custody documentation",
            "legal_document": "General legal proceeding document",
            "subpoena_response": "Response to legal subpoena",
            "court_presentation": "Court presentation and exhibit document",
            "investigation_timeline": "Chronological investigation timeline",
            "person_profile": "Subject / person of interest profile",
            "evidence_log": "Evidence tracking log notes",
            "interview_notes": "Witness / suspect interview notes",
            "observation_log": "Field observation and scene notes",
            "technical_findings": "Detailed technical finding notes",
            "conclusions": "Investigation conclusion notes",
            "basic": "Blank general-purpose template",
            "memo": "Internal memorandum",
            "checklist": "Investigation checklist",
        }
        return _desc.get(self.value, self.display_name)

    # ------------------------------------------------------------------ #
    # Group helpers                                                         #
    # ------------------------------------------------------------------ #

    @classmethod
    def standard_reports(cls) -> List["TemplateCategory"]:
        return [
            cls.SWGDE_NIST,
            cls.MOBILE_DEVICE,
            cls.NETWORK_FORENSICS,
            cls.CLOUD_FORENSICS,
            cls.EMAIL_FORENSICS,
            cls.DATABASE_FORENSICS,
        ]

    @classmethod
    def specialised_reports(cls) -> List["TemplateCategory"]:
        return [
            cls.INTRUSION_INVESTIGATION,
            cls.MALWARE_ANALYSIS,
            cls.DATA_BREACH,
            cls.INCIDENT_RESPONSE,
        ]

    @classmethod
    def legal_documents(cls) -> List["TemplateCategory"]:
        return [
            cls.EVIDENCE_INTAKE,
            cls.CHAIN_OF_CUSTODY,
            cls.LEGAL_DOCUMENT,
            cls.SUBPOENA_RESPONSE,
            cls.COURT_PRESENTATION,
        ]

    @classmethod
    def note_templates(cls) -> List["TemplateCategory"]:
        return [
            cls.INVESTIGATION_TIMELINE,
            cls.PERSON_PROFILE,
            cls.EVIDENCE_LOG,
            cls.INTERVIEW_NOTES,
            cls.OBSERVATION_LOG,
            cls.TECHNICAL_FINDINGS,
            cls.CONCLUSIONS,
        ]

    @classmethod
    def informal_templates(cls) -> List["TemplateCategory"]:
        return [cls.BASIC, cls.MEMO, cls.CHECKLIST]

    @classmethod
    def all_categories(cls) -> List["TemplateCategory"]:
        return list(cls)

    @property
    def is_report_template(self) -> bool:
        return self in (
            self.standard_reports() + self.specialised_reports()
        )

    @property
    def is_note_template(self) -> bool:
        return self in self.note_templates()

    def __str__(self) -> str:  # noqa: D105
        return self.value
