from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
import json
import os
from datetime import datetime
from sqlalchemy import func

from .models import Case, Report, ReportWorkflow, PeerReviewConnection, SupervisorAssignment
from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger


peer_review_bp = Blueprint('peer_review', __name__)
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


def _supervisors_for_user(username: str) -> set[str]:
    user = (username or '').strip().lower()
    if not user:
        return set()
    rows = SupervisorAssignment.query.filter(
        SupervisorAssignment.is_active.is_(True),
        (func.lower(SupervisorAssignment.examiner) == user) | (func.lower(SupervisorAssignment.investigator) == user),
    ).all()
    return {str(r.supervisor).strip().lower() for r in rows if r.supervisor}


def _is_supervisor_for_examiner(supervisor_username: str, examiner_username: str) -> bool:
    return (supervisor_username or '').strip().lower() in _supervisors_for_user(examiner_username)


@peer_review_bp.route('/api/peer-review/share/<case_number>', methods=['GET'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def share_report(case_number):
    ident = _identity()
    current_user = ident['username']
    current_user_l = current_user.lower()

    case = Case.query.filter_by(case_number=case_number).first()
    if not case:
        return jsonify({"error": "Case not found"}), 404

    peer_reviewers = []
    try:
        if case.peer_reviewers:
            peer_reviewers = json.loads(case.peer_reviewers)
    except Exception:
        peer_reviewers = []

    examiner = str(case.examiner_id or '').strip().lower()
    reviewers = {str(r).strip().lower() for r in peer_reviewers}
    if current_user_l != examiner and current_user_l not in reviewers and not _is_supervisor_for_examiner(current_user_l, examiner):
        _log.warning('peer_review_share_denied', extra={'actor': current_user, 'case_number': case_number})
        return jsonify({"error": "Unauthorized access"}), 403

    report = Report.query.filter_by(case_number=case_number).first()
    if not report:
        return jsonify({"error": "Report not found"}), 404

    appendices = []
    if report.appendices:
        try:
            appendices = json.loads(report.appendices)
            if not isinstance(appendices, list):
                appendices = []
        except Exception:
            appendices = [p for p in report.appendices.split(',') if p]

    report_data = {
        "case_number": case_number,
        "case_title": case.title,
        "examiner": case.examiner_id,
        "report_html": report.report_html or '',
        "appendices": appendices,
        "pdf_hash": report.final_pdf_hash or '',
        "shared_at": datetime.now().isoformat(),
        "shared_by": current_user
    }

    return jsonify(report_data), 200


@peer_review_bp.route('/api/peer-review/submit/<case_number>', methods=['POST'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def submit_peer_review(case_number):
    ident = _identity()
    current_user = ident['username']
    current_user_l = current_user.lower()
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ['reviewer_info', 'review_data', 'summary']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    case = Case.query.filter_by(case_number=case_number).first()
    if not case:
        return jsonify({"error": "Case not found"}), 404

    peer_reviewers = []
    try:
        if case.peer_reviewers:
            peer_reviewers = json.loads(case.peer_reviewers)
    except Exception:
        peer_reviewers = []
    examiner = str(case.examiner_id or '').strip().lower()
    reviewers = {str(r).strip().lower() for r in peer_reviewers}
    if current_user_l not in {examiner} and current_user_l not in reviewers and not _is_supervisor_for_examiner(current_user_l, examiner):
        _log.warning('peer_review_submit_denied', extra={'actor': current_user, 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    review_record = {
        "case_number": case_number,
        "reviewer": current_user,
        "reviewer_info": data['reviewer_info'],
        "review_data": data['review_data'],
        "summary": data['summary'],
        "submitted_at": datetime.now().isoformat(),
        "signature_hash": data.get('signature_hash', '')
    }

    case_dir = os.path.join("cases", case_number)
    os.makedirs(case_dir, exist_ok=True)

    review_file = os.path.join(case_dir, f"peer_review_{current_user}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(review_file, 'w', encoding='utf-8') as f:
        json.dump(review_record, f, indent=2)

    workflow = ReportWorkflow.query.filter_by(case_number=case_number).first()
    if workflow is None:
        workflow = ReportWorkflow(case_number=case_number, peer_review_required=True)
    workflow.peer_review_status = 'completed'

    from .models import db
    db.session.add(workflow)
    db.session.commit()
    _log.info('peer_review_submitted', extra={'actor': current_user, 'case_number': case_number})

    return jsonify({"message": "Peer review submitted successfully", "review_file": review_file}), 201


@peer_review_bp.route('/api/peer-review/connections', methods=['GET'])
@jwt_required()
@rate_limit(limit=180, window_seconds=60, strategy='user_or_ip')
def list_connections():
    ident = _identity()
    role = ident['role']
    username = ident['username']
    username_l = username.lower()

    rows = PeerReviewConnection.query.order_by(PeerReviewConnection.requested_at.desc()).all()
    scoped_rows = []
    for row in rows:
        requester = str(row.requester or '').strip().lower()
        reviewer = str(row.reviewer or '').strip().lower()
        if username_l in {requester, reviewer}:
            scoped_rows.append(row)
            continue
        if role == 'supervisor' and _is_supervisor_for_examiner(username_l, requester):
            scoped_rows.append(row)

    _log.info('peer_review_connections_listed', extra={'actor': username, 'role': role, 'visible_count': len(scoped_rows)})
    return jsonify(
        [
            {
                'id': row.id,
                'requester': row.requester,
                'reviewer': row.reviewer,
                'status': row.status,
                'requested_at': row.requested_at.isoformat() if row.requested_at else None,
                'approved_at': row.approved_at.isoformat() if row.approved_at else None,
                'approved_by': row.approved_by,
            }
            for row in scoped_rows
        ]
    )


@peer_review_bp.route('/api/peer-review/connections/request', methods=['POST'])
@jwt_required()
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def request_connection():
    ident = _identity()
    data = request.get_json(silent=True) or {}
    reviewer = str(data.get('reviewer', '') or '').strip().lower()
    if not reviewer:
        return jsonify({'error': 'reviewer is required'}), 400
    if reviewer == ident['username'].lower():
        return jsonify({'error': 'Cannot request peer review connection to yourself'}), 400

    requester = ident['username'].lower()
    requester_supervisors = _supervisors_for_user(requester)
    if not requester_supervisors:
        _log.warning('peer_review_connection_request_denied_no_supervisor', extra={'actor': ident['username'], 'reviewer': reviewer})
        return jsonify({'error': 'Requester must be assigned to a supervisor before initiating peer review'}), 403

    existing = PeerReviewConnection.query.filter_by(
        requester=requester,
        reviewer=reviewer,
        status='pending',
    ).first()
    if existing:
        return jsonify({'error': 'Connection request already pending'}), 409

    row = PeerReviewConnection(
        requester=requester,
        reviewer=reviewer,
        status='pending',
    )
    from .models import db
    db.session.add(row)
    db.session.commit()
    _log.info('peer_review_connection_requested', extra={'actor': ident['username'], 'requester': requester, 'reviewer': reviewer, 'connection_id': row.id})
    return jsonify({'message': 'Connection request sent', 'id': row.id}), 201


@peer_review_bp.route('/api/peer-review/connections/<int:connection_id>/approve', methods=['POST'])
@jwt_required()
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def approve_connection(connection_id: int):
    ident = _identity()
    row = PeerReviewConnection.query.get(connection_id)
    if not row:
        return jsonify({'error': 'Connection not found'}), 404

    actor = ident['username'].lower()
    reviewer = str(row.reviewer or '').strip().lower()
    requester = str(row.requester or '').strip().lower()
    can_approve = actor == reviewer or _is_supervisor_for_examiner(actor, requester)
    if not can_approve:
        _log.warning('peer_review_connection_approve_denied', extra={'actor': ident['username'], 'connection_id': connection_id})
        return jsonify({'error': 'Permission denied'}), 403

    row.status = 'approved'
    row.approved_at = datetime.utcnow()
    row.approved_by = ident['username']
    from .models import db
    db.session.commit()
    _log.info('peer_review_connection_approved', extra={'actor': ident['username'], 'connection_id': row.id, 'requester': row.requester, 'reviewer': row.reviewer})
    return jsonify({'message': 'Connection approved', 'id': row.id})
