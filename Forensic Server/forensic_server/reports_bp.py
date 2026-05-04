from __future__ import annotations

from datetime import datetime

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func, or_

from .infrastructure.api.decorators import rate_limit
from .models import Case, Report, ReportComment, ReportWorkflow, SupervisorAssignment, db
from .infrastructure.observability import get_logger


reports_bp = Blueprint('reports', __name__, url_prefix='/api/v1/reports')
_log = get_logger(__name__)


def _identity() -> dict[str, str]:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return {
            'username': str(identity.get('username', 'unknown')),
            'role': str(identity.get('role', 'writer')).lower(),
        }
    claims = get_jwt() or {}
    username = str(claims.get('username') or identity or 'unknown')
    role = str(claims.get('role') or 'writer').lower()
    return {'username': username, 'role': role}


def _workflow_for_case(case_number: str) -> ReportWorkflow:
    workflow = ReportWorkflow.query.filter_by(case_number=case_number).first()
    if workflow is None:
        workflow = ReportWorkflow(case_number=case_number)
        db.session.add(workflow)
        db.session.flush()
    return workflow


def _supervisor_can_access_case(supervisor_username: str, case: Case) -> bool:
    supervisor = (supervisor_username or '').strip().lower()
    investigator = (case.assigned_to or '').strip().lower()
    examiner = (case.examiner_id or '').strip().lower()
    if not supervisor:
        return False
    q = SupervisorAssignment.query.filter(
        func.lower(SupervisorAssignment.supervisor) == supervisor,
        SupervisorAssignment.is_active.is_(True),
        or_(
            func.lower(SupervisorAssignment.investigator) == investigator,
            func.lower(SupervisorAssignment.examiner) == examiner,
        ),
    )
    return q.first() is not None


def _can_access_case(case: Case, ident: dict[str, str]) -> bool:
    if ident['role'] == 'admin':
        return True
    if ident['role'] == 'supervisor':
        return _supervisor_can_access_case(ident['username'], case)
    return ident['username'] in {case.assigned_to, case.examiner_id}


@reports_bp.route('/<string:case_number>', methods=['GET'])
@jwt_required()
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def get_report(case_number: str):
    ident = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404

    if not _can_access_case(case, ident):
        _log.warning('report_view_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    report = Report.query.filter_by(case_number=case_number).first()
    workflow = _workflow_for_case(case_number)
    db.session.commit()

    comments = ReportComment.query.filter_by(case_number=case_number).order_by(ReportComment.created_at.asc()).all()

    return jsonify(
        {
            'case_number': case_number,
            'title': case.title or '',
            'examiner': case.examiner_id or case.assigned_to or '',
            'report_html': report.report_html if report else '',
            'appendices': report.appendices if report else '',
            'workflow': {
                'status': workflow.status,
                'denied_reason': workflow.denied_reason or '',
                'approved_by': workflow.approved_by or '',
                'approved_at': workflow.approved_at.isoformat() if workflow.approved_at else None,
                'peer_review_status': workflow.peer_review_status,
                'peer_review_required': workflow.peer_review_required,
            },
            'comments': [
                {
                    'id': c.id,
                    'author': c.author,
                    'author_role': c.author_role,
                    'comment': c.comment,
                    'created_at': c.created_at.isoformat() if c.created_at else None,
                }
                for c in comments
            ],
        }
    )


@reports_bp.route('/<string:case_number>', methods=['PUT'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def upsert_report(case_number: str):
    ident = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404

    if not _can_access_case(case, ident):
        _log.warning('report_upsert_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    report_html = str(payload.get('report_html', '') or '')
    appendices = payload.get('appendices', '')
    peer_review_required = bool(payload.get('peer_review_required', False))

    report = Report.query.filter_by(case_number=case_number).first()
    if report is None:
        report = Report(case_number=case_number, report_html=report_html, appendices=str(appendices))
        db.session.add(report)
    else:
        report.report_html = report_html
        report.appendices = str(appendices)

    workflow = _workflow_for_case(case_number)
    if workflow.status in {'approved', 'denied'}:
        workflow.status = 'revisions_needed'
    elif workflow.status == 'draft':
        workflow.status = 'in_review'
    workflow.peer_review_required = peer_review_required

    db.session.commit()
    _log.info('report_saved', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
    return jsonify({'message': 'Report saved', 'case_number': case_number})


@reports_bp.route('/<string:case_number>/comments', methods=['GET'])
@jwt_required()
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def list_comments(case_number: str):
    ident = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    if not _can_access_case(case, ident):
        _log.warning('report_comments_list_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    comments = ReportComment.query.filter_by(case_number=case_number).order_by(ReportComment.created_at.asc()).all()
    return jsonify(
        [
            {
                'id': c.id,
                'author': c.author,
                'author_role': c.author_role,
                'comment': c.comment,
                'created_at': c.created_at.isoformat() if c.created_at else None,
            }
            for c in comments
        ]
    )


@reports_bp.route('/<string:case_number>/comments', methods=['POST'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def add_comment(case_number: str):
    ident = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    if not _can_access_case(case, ident):
        _log.warning('report_comment_add_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    comment_text = str(payload.get('comment', '') or '').strip()
    if not comment_text:
        return jsonify({'error': 'comment is required'}), 400

    comment = ReportComment(
        case_number=case_number,
        author=ident['username'],
        author_role=ident['role'],
        comment=comment_text,
    )
    db.session.add(comment)
    db.session.commit()
    _log.info('report_comment_added', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number, 'comment_id': comment.id})
    return jsonify({'message': 'Comment added', 'id': comment.id}), 201


@reports_bp.route('/<string:case_number>/approve', methods=['POST'])
@jwt_required()
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def approve_report(case_number: str):
    ident = _identity()
    if ident['role'] not in {'admin', 'supervisor'}:
        return jsonify({'error': 'Permission denied'}), 403

    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    if ident['role'] == 'supervisor' and not _supervisor_can_access_case(ident['username'], case):
        _log.warning('report_approve_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    workflow = _workflow_for_case(case_number)
    workflow.status = 'approved'
    workflow.denied_reason = None
    workflow.approved_by = ident['username']
    workflow.approved_at = datetime.utcnow()

    case.status = 'approved'
    db.session.commit()
    _log.info('report_approved', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
    return jsonify({'message': 'Report approved', 'case_number': case_number})


@reports_bp.route('/<string:case_number>/deny', methods=['POST'])
@jwt_required()
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def deny_report(case_number: str):
    ident = _identity()
    if ident['role'] not in {'admin', 'supervisor'}:
        return jsonify({'error': 'Permission denied'}), 403

    case = Case.query.get(case_number)
    if not case:
        return jsonify({'error': 'Case not found'}), 404
    if ident['role'] == 'supervisor' and not _supervisor_can_access_case(ident['username'], case):
        _log.warning('report_deny_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})
        return jsonify({'error': 'Permission denied'}), 403

    payload = request.get_json(silent=True) or {}
    reason = str(payload.get('reason', '') or '').strip()
    if not reason:
        return jsonify({'error': 'A brief deny reason is required'}), 400

    workflow = _workflow_for_case(case_number)
    workflow.status = 'denied'
    workflow.denied_reason = reason
    workflow.approved_by = ident['username']
    workflow.approved_at = datetime.utcnow()

    case.status = 'revisions_needed'
    case.review_comments = reason

    comment = ReportComment(
        case_number=case_number,
        author=ident['username'],
        author_role=ident['role'],
        comment=f'DENIED: {reason}',
    )
    db.session.add(comment)
    db.session.commit()
    _log.info('report_denied', extra={'actor': ident['username'], 'role': ident['role'], 'case_number': case_number})

    return jsonify({'message': 'Report denied', 'case_number': case_number, 'reason': reason})
