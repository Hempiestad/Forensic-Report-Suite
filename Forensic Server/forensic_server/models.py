from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class Case(db.Model):
    __tablename__ = 'cases'
    case_number = db.Column(db.String(50), primary_key=True)
    assigned_to = db.Column(db.String(100))
    status = db.Column(db.String(50), default='draft')
    trial_date = db.Column(db.String(20))
    sentencing_date = db.Column(db.String(20))
    review_comments = db.Column(db.Text)
    examiner_id = db.Column(db.String(100))
    title = db.Column(db.String(200))
    peer_reviewers = db.Column(db.Text)

    __table_args__ = (
        db.Index('idx_case_assigned_to', 'assigned_to'),
        db.Index('idx_case_status', 'status'),
    )


class EvidenceItem(db.Model):
    __tablename__ = 'evidence_items'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False)
    item_type = db.Column(db.String(50))
    details = db.Column(db.Text)
    imaging_status = db.Column(db.String(50), default='not_imaged')
    imaged_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_evidence_case_number', 'case_number'),
    )


class LegalProcess(db.Model):
    __tablename__ = 'legal_processes'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False)
    process_type = db.Column(db.String(50))
    provider = db.Column(db.String(100))
    status = db.Column(db.String(50), default='pending')
    submission_date = db.Column(db.DateTime)
    due_date = db.Column(db.DateTime)
    expiration_date = db.Column(db.DateTime)
    received_date = db.Column(db.DateTime)
    analysis_start_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)

    __table_args__ = (
        db.Index('idx_legal_case_number', 'case_number'),
    )


class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False)
    report_html = db.Column(db.Text)
    appendices = db.Column(db.Text)
    final_pdf_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_report_case_number', 'case_number'),
    )


class UserAccount(db.Model):
    __tablename__ = 'user_accounts'
    username = db.Column(db.String(100), primary_key=True)
    role = db.Column(db.String(30), nullable=False, default='writer')
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_user_accounts_role', 'role'),
        db.Index('idx_user_accounts_active', 'is_active'),
    )


class CourtDate(db.Model):
    __tablename__ = 'court_dates'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False)
    date_type = db.Column(db.String(50), nullable=False, default='court')
    event_date = db.Column(db.String(30), nullable=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_court_dates_case_number', 'case_number'),
        db.Index('idx_court_dates_event_date', 'event_date'),
    )


class ReportWorkflow(db.Model):
    __tablename__ = 'report_workflow'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False, unique=True)
    status = db.Column(db.String(40), nullable=False, default='draft')
    denied_reason = db.Column(db.Text)
    approved_by = db.Column(db.String(100))
    approved_at = db.Column(db.DateTime)
    peer_review_status = db.Column(db.String(40), nullable=False, default='not_started')
    peer_review_required = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_report_workflow_case_number', 'case_number'),
        db.Index('idx_report_workflow_status', 'status'),
        db.Index('idx_report_workflow_peer_review_status', 'peer_review_status'),
    )


class ReportComment(db.Model):
    __tablename__ = 'report_comments'
    id = db.Column(db.Integer, primary_key=True)
    case_number = db.Column(db.String(50), db.ForeignKey('cases.case_number'), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    author_role = db.Column(db.String(40), nullable=False, default='writer')
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_report_comments_case_number', 'case_number'),
        db.Index('idx_report_comments_created_at', 'created_at'),
    )


class SupervisorAssignment(db.Model):
    __tablename__ = 'supervisor_assignments'
    id = db.Column(db.Integer, primary_key=True)
    supervisor = db.Column(db.String(100), nullable=False)
    investigator = db.Column(db.String(100), nullable=False)
    examiner = db.Column(db.String(100), nullable=True)
    assigned_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.Index('idx_supervisor_assignments_supervisor', 'supervisor'),
        db.Index('idx_supervisor_assignments_investigator', 'investigator'),
        db.Index('idx_supervisor_assignments_examiner', 'examiner'),
    )


class PeerReviewConnection(db.Model):
    __tablename__ = 'peer_review_connections'
    id = db.Column(db.Integer, primary_key=True)
    requester = db.Column(db.String(100), nullable=False)
    reviewer = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')
    requested_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(100))

    __table_args__ = (
        db.Index('idx_peer_review_connections_requester', 'requester'),
        db.Index('idx_peer_review_connections_reviewer', 'reviewer'),
        db.Index('idx_peer_review_connections_status', 'status'),
    )


class LegalTemplateLibrary(db.Model):
    __tablename__ = 'legal_template_library'
    id = db.Column(db.Integer, primary_key=True)
    owner_username = db.Column(db.String(100), nullable=False)
    vendor_name = db.Column(db.String(150), nullable=False, default='General Vendor')
    template_type = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    template_content = db.Column(db.Text, nullable=False)
    tags = db.Column(db.Text, nullable=False, default='[]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.Index('idx_legal_template_owner', 'owner_username'),
        db.Index('idx_legal_template_vendor', 'vendor_name'),
        db.Index('idx_legal_template_type', 'template_type'),
        db.Index('idx_legal_template_updated_at', 'updated_at'),
    )


class LegalTemplateShare(db.Model):
    __tablename__ = 'legal_template_shares'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('legal_template_library.id'), nullable=False)
    shared_with = db.Column(db.String(100), nullable=False)
    shared_by = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_legal_template_share_template_id', 'template_id'),
        db.Index('idx_legal_template_share_shared_with', 'shared_with'),
        db.UniqueConstraint('template_id', 'shared_with', name='uq_legal_template_share_unique'),
    )
