from flask import Blueprint, request, jsonify, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timezone
from werkzeug.exceptions import BadRequest
import hashlib
import json
from sqlalchemy import func, or_

from .models import db, Case, EvidenceItem, LegalProcess, CourtDate, SupervisorAssignment
from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger


cases_bp = Blueprint('cases', __name__, url_prefix='/api/v1/cases')
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


def _has_case_access(case: Case, identity: dict[str, str]) -> bool:
    role = identity['role']
    username = identity['username']
    if role == 'admin':
        return True
    if role == 'supervisor':
        return _supervisor_can_access_case(username, case)
    return username in {case.assigned_to, case.examiner_id}


def get_evidence_details(case_number):
    items = EvidenceItem.query.filter_by(case_number=case_number).all()
    return [{
        'id': item.id,
        'type': item.item_type,
        'imaging_status': item.imaging_status if item.item_type == 'digital' else 'n/a',
        'imaged_date': item.imaged_date.isoformat() if item.imaged_date else None,
        'completed_date': item.completed_date.isoformat() if item.completed_date else None
    } for item in items]


def get_legal_details(case_number):
    processes = LegalProcess.query.filter_by(case_number=case_number).all()
    today = datetime.now(timezone.utc)
    details = []
    for p in processes:
        suggested_color = 'green' if p.status in ['completed', 'no_longer_needed'] else 'yellow'
        if p.process_type == 'preservation' and p.expiration_date:
            try:
                exp_date = p.expiration_date.date() if hasattr(p.expiration_date, 'date') else p.expiration_date
                days_left = (exp_date - datetime.now(timezone.utc).date()).days
                if days_left <= 0:
                    suggested_color = 'red'
                elif days_left <= 10:
                    suggested_color = 'yellow'
            except Exception:
                pass
        elif p.process_type in ['subpoena', 'warrant'] and p.due_date and (p.due_date.date() if hasattr(p.due_date, 'date') else p.due_date) < today.date() and p.status != 'completed':
            suggested_color = 'red'

        details.append({
            'id': p.id,
            'type': p.process_type,
            'provider': p.provider or '',
            'submission_date': p.submission_date.isoformat() if p.submission_date else None,
            'due_date': p.due_date.isoformat() if p.due_date else None,
            'expiration_date': p.expiration_date.isoformat() if p.expiration_date else None,
            'status': p.status,
            'received_date': p.received_date.isoformat() if p.received_date else None,
            'analysis_start_date': p.analysis_start_date.isoformat() if p.analysis_start_date else None,
            'completed_date': p.completed_date.isoformat() if p.completed_date else None,
            'suggested_color': suggested_color
        })
    return details


@cases_bp.route('', methods=['GET'])
@jwt_required()
@rate_limit(limit=300, window_seconds=60, strategy='user_or_ip')
def get_cases():
    from flask_caching import current_cache

    current_user = _identity()
    role = current_user['role']
    username = current_user['username']
    cache_key = f"cases_{username}_{role}"

    cached_result = current_cache.get(cache_key)
    if cached_result:
        result, etag, last_modified = cached_result
    else:
        if role == 'admin':
            cases = Case.query.all()
        elif role == 'supervisor':
            assignments = SupervisorAssignment.query.filter(
                func.lower(SupervisorAssignment.supervisor) == username.lower(),
                SupervisorAssignment.is_active.is_(True),
            ).all()
            investigators = {str(a.investigator).strip() for a in assignments if a.investigator}
            examiners = {str(a.examiner).strip() for a in assignments if a.examiner}
            query = Case.query
            filters = []
            if investigators:
                filters.append(Case.assigned_to.in_(investigators))
            if examiners:
                filters.append(Case.examiner_id.in_(examiners))
            if filters:
                cases = query.filter(or_(*filters)).all()
            else:
                cases = []
        else:
            cases = Case.query.filter(
                or_(Case.assigned_to == username, Case.examiner_id == username)
            ).all()

        result = []
        for case in cases:
            result.append({
                'id': case.case_number,
                'assigned_to': case.assigned_to or '',
                'status': case.status,
                'trial_date': getattr(case, 'trial_date', None),
                'sentencing_date': getattr(case, 'sentencing_date', None),
                'review_comments': case.review_comments or '',
                'evidence_details': get_evidence_details(case.case_number),
                'legal_details': get_legal_details(case.case_number)
            })

        data_str = json.dumps(result, sort_keys=True)
        etag = hashlib.md5(data_str.encode()).hexdigest()
        last_modified = datetime.now(timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
        current_cache.set(cache_key, (result, etag, last_modified), timeout=45)

    if request.if_none_match and etag in request.if_none_match:
        return '', 304
    if request.if_modified_since and request.if_modified_since == last_modified:
        return '', 304

    response = make_response(jsonify(result))
    response.headers['ETag'] = etag
    response.headers['Last-Modified'] = last_modified
    response.headers['Cache-Control'] = 'private, max-age=45'
    return response


@cases_bp.route('', methods=['POST'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def create_case():
    current_user = _identity()
    if current_user['role'] not in ['admin', 'supervisor']:
        return jsonify({"error": "Insufficient permissions"}), 403

    data = request.get_json()
    case_number = data['case_number']
    if Case.query.get(case_number):
        return jsonify({"error": "Case already exists"}), 409

    assigned_to = data.get('assigned_to', current_user['username'])
    examiner_id = data.get('examiner_id') or assigned_to

    # Supervisors may only create cases for investigators/examiners assigned to them
    if current_user['role'] == 'supervisor':
        sup = current_user['username'].lower()
        assigned_l = (assigned_to or '').strip().lower()
        examiner_l = (examiner_id or '').strip().lower()
        assigned_rows = SupervisorAssignment.query.filter(
            func.lower(SupervisorAssignment.supervisor) == sup,
            SupervisorAssignment.is_active.is_(True),
        ).all()
        allowed_investigators = {str(r.investigator).strip().lower() for r in assigned_rows if r.investigator}
        allowed_examiners = {str(r.examiner).strip().lower() for r in assigned_rows if r.examiner}
        if assigned_l not in allowed_investigators and examiner_l not in allowed_examiners:
            _log.warning(
                'case_create_denied_unassigned',
                extra={'actor': current_user['username'], 'assigned_to': assigned_to, 'examiner_id': examiner_id},
            )
            return jsonify({'error': 'Supervisor may only create cases for assigned investigators/examiners'}), 403

    new_case = Case(
        case_number=case_number,
        assigned_to=assigned_to,
        examiner_id=examiner_id,
        title=data.get('title', ''),
        status='draft'
    )
    db.session.add(new_case)
    db.session.commit()
    _log.info(
        'case_created',
        extra={
            'actor': current_user['username'],
            'role': current_user['role'],
            'case_number': case_number,
            'assigned_to': assigned_to,
            'examiner_id': examiner_id,
        },
    )
    return jsonify({"message": "Case created"}), 201


@cases_bp.route('/<case_number>/submit', methods=['POST'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def submit_case(case_number):
    current_user = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if not _has_case_access(case, current_user):
        _log.warning('case_submit_denied', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403
    case.status = 'submitted'
    db.session.commit()
    _log.info('case_submitted', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
    return jsonify({"message": "Case submitted for review"})


@cases_bp.route('/<case_number>/approve', methods=['POST'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def approve_case(case_number):
    current_user = _identity()
    if current_user['role'] not in ['admin', 'supervisor']:
        return jsonify({"error": "Permission denied"}), 403
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if current_user['role'] == 'supervisor' and not _supervisor_can_access_case(current_user['username'], case):
        _log.warning('case_approve_denied', extra={'actor': current_user['username'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403
    case.status = 'approved'
    db.session.commit()
    _log.info('case_approved', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
    return jsonify({"message": "Case approved"})


@cases_bp.route('/<case_number>/reject', methods=['POST'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def reject_case(case_number):
    current_user = _identity()
    if current_user['role'] not in ['admin', 'supervisor']:
        return jsonify({"error": "Permission denied"}), 403
    data = request.get_json()
    comments = data.get('comments', '')
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if current_user['role'] == 'supervisor' and not _supervisor_can_access_case(current_user['username'], case):
        _log.warning('case_reject_denied', extra={'actor': current_user['username'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403
    case.status = 'revisions_needed'
    case.review_comments = comments
    db.session.commit()
    _log.info('case_rejected', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
    return jsonify({"message": "Case rejected with comments"})


@cases_bp.route('/<case_number>/evidence', methods=['POST'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def add_evidence(case_number):
    current_user = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if not _has_case_access(case, current_user):
        _log.warning('evidence_add_denied', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    item = EvidenceItem(
        case_number=case_number,
        item_type=data['type'],
        details=data.get('details'),
        imaging_status=data.get('imaging_status', 'not_imaged')
    )
    db.session.add(item)
    db.session.commit()
    _log.info('evidence_added', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number, 'item_type': data['type']})
    return jsonify({"message": "Evidence item added"}), 201


@cases_bp.route('/<case_number>/legal', methods=['POST'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def add_legal_process(case_number):
    current_user = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if not _has_case_access(case, current_user):
        _log.warning('legal_process_add_denied', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json()
    proc = LegalProcess(
        case_number=case_number,
        process_type=data['type'],
        provider=data.get('provider'),
        status=data.get('status', 'pending'),
        submission_date=datetime.fromisoformat(data['submission_date']) if data.get('submission_date') else None,
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        expiration_date=datetime.fromisoformat(data['expiration_date']) if data.get('expiration_date') else None
    )
    db.session.add(proc)
    db.session.commit()
    _log.info('legal_process_added', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number, 'process_type': data['type']})
    return jsonify({"message": "Legal process added"}), 201


@cases_bp.route('/<case_number>/dates', methods=['PUT'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def update_case_dates(case_number):
    current_user = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if not _has_case_access(case, current_user):
        _log.warning('case_dates_update_denied', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json() or {}
    trial_date = data.get('trial_date')
    sentencing_date = data.get('sentencing_date')

    try:
        if trial_date is not None and trial_date != '':
            datetime.fromisoformat(trial_date)
            case.trial_date = trial_date
        elif trial_date == '':
            case.trial_date = None

        if sentencing_date is not None and sentencing_date != '':
            datetime.fromisoformat(sentencing_date)
            case.sentencing_date = sentencing_date
        elif sentencing_date == '':
            case.sentencing_date = None
    except ValueError:
        return jsonify({"error": "Invalid date format. Use ISO YYYY-MM-DD."}), 400

    db.session.commit()
    _log.info('case_dates_updated', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
    return jsonify({"message": "Dates updated"})


@cases_bp.route('/<case_number>/court-dates', methods=['GET'])
@jwt_required()
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def list_court_dates(case_number):
    current_user = _identity()
    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if not _has_case_access(case, current_user):
        _log.warning('court_dates_list_denied', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    rows = CourtDate.query.filter_by(case_number=case_number).order_by(CourtDate.event_date.asc()).all()
    return jsonify(
        [
            {
                'id': row.id,
                'case_number': row.case_number,
                'date_type': row.date_type,
                'event_date': row.event_date,
                'notes': row.notes or '',
                'created_by': row.created_by or '',
                'created_at': row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    )


@cases_bp.route('/<case_number>/court-dates', methods=['POST'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def add_court_date(case_number):
    current_user = _identity()
    if current_user['role'] not in {'admin', 'supervisor'}:
        return jsonify({"error": "Permission denied"}), 403

    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if current_user['role'] == 'supervisor' and not _supervisor_can_access_case(current_user['username'], case):
        _log.warning('court_date_add_denied', extra={'actor': current_user['username'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json(silent=True) or {}
    date_type = str(data.get('date_type', 'court')).strip()
    event_date = str(data.get('event_date', '')).strip()
    notes = str(data.get('notes', '') or '').strip()

    if not event_date:
        return jsonify({"error": "event_date is required"}), 400
    try:
        datetime.fromisoformat(event_date)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS."}), 400

    row = CourtDate(
        case_number=case_number,
        date_type=date_type or 'court',
        event_date=event_date,
        notes=notes,
        created_by=current_user['username'],
    )
    db.session.add(row)
    db.session.commit()
    _log.info('court_date_added', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number, 'court_date_id': row.id})
    return jsonify({'message': 'Court date added', 'id': row.id}), 201


@cases_bp.route('/<case_number>/assignments', methods=['PUT'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def update_case_assignments(case_number):
    current_user = _identity()
    if current_user['role'] not in {'admin', 'supervisor'}:
        return jsonify({"error": "Permission denied"}), 403

    case = Case.query.get(case_number)
    if not case:
        return jsonify({"error": "Case not found"}), 404
    if current_user['role'] == 'supervisor' and not _supervisor_can_access_case(current_user['username'], case):
        _log.warning('case_assignment_update_denied', extra={'actor': current_user['username'], 'case_number': case_number})
        return jsonify({"error": "Permission denied"}), 403

    data = request.get_json(silent=True) or {}
    assigned_to = data.get('investigator')
    examiner_id = data.get('examiner')

    if assigned_to is not None:
        case.assigned_to = str(assigned_to).strip() or None
    if examiner_id is not None:
        case.examiner_id = str(examiner_id).strip() or None

    db.session.commit()
    _log.info('case_assignment_updated', extra={'actor': current_user['username'], 'role': current_user['role'], 'case_number': case_number, 'investigator': case.assigned_to or '', 'examiner': case.examiner_id or ''})
    return jsonify(
        {
            'message': 'Case assignments updated',
            'case_number': case_number,
            'investigator': case.assigned_to,
            'examiner': case.examiner_id,
        }
    )
