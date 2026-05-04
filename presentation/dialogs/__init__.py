"""
presentation/dialogs/ — reusable dialog widgets.

Phase 4: re-export dialog classes from this package.
"""
from templates import TemplateManager
from glossary import GlossaryDialog
from status_color_dialog import StatusColorDialog
from bug_report import BugReportDialog
from feature_request import FeatureRequestDialog
from archive_case_dialog import ArchiveCaseDialog
from archived_cases_dialog import ArchivedCasesDialog
from legal_workflow_dialogs import (
    InvestigatorApprovalDialog,
    StateAttorneyApprovalDialog,
    JudicialApprovalDialog,
    SendToProviderDialog,
    ProviderAcknowledgedDialog,
    MarkSLABreachDialog,
)

__all__ = [
    "TemplateManager",
    "GlossaryDialog",
    "StatusColorDialog",
    "BugReportDialog",
    "FeatureRequestDialog",
    "ArchiveCaseDialog",
    "ArchivedCasesDialog",
    "InvestigatorApprovalDialog",
    "StateAttorneyApprovalDialog",
    "JudicialApprovalDialog",
    "SendToProviderDialog",
    "ProviderAcknowledgedDialog",
    "MarkSLABreachDialog",
]
