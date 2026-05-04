from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from sqlalchemy import func, or_

from .models import Case, SupervisorAssignment
from .cases_bp import get_evidence_details, get_legal_details
from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger


dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/v1/dashboard')
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


@dashboard_bp.route('', methods=['GET'])
@jwt_required()
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def dashboard():
    ident = _identity()
    role = ident['role']
    username = ident['username']

    if role not in {'admin', 'supervisor'}:
        _log.warning('dashboard_access_denied', extra={'actor': username, 'role': role})
        return jsonify({"error": "Access denied"}), 403

    if role == 'admin':
        cases = Case.query.all()
    else:
        # Supervisors only see cases belonging to their assigned investigators/examiners
        assignments = SupervisorAssignment.query.filter(
            func.lower(SupervisorAssignment.supervisor) == username.lower(),
            SupervisorAssignment.is_active.is_(True),
        ).all()
        investigators = {str(a.investigator).strip() for a in assignments if a.investigator}
        examiners = {str(a.examiner).strip() for a in assignments if a.examiner}
        filters = []
        if investigators:
            filters.append(Case.assigned_to.in_(investigators))
        if examiners:
            filters.append(Case.examiner_id.in_(examiners))
        cases = Case.query.filter(or_(*filters)).all() if filters else []

    cases_data = []
    for case in cases:
        cases_data.append({
            'case_number': case.case_number,
            'assigned_to': case.assigned_to or '',
            'status': case.status,
            'evidence_details': get_evidence_details(case.case_number),
            'legal_details': get_legal_details(case.case_number),
            'court_date': getattr(case, 'trial_date', None),
            'sentencing_date': getattr(case, 'sentencing_date', None)
        })

    _log.info(
        'dashboard_viewed',
        extra={'actor': username, 'role': role, 'cases_returned': len(cases_data)},
    )
    return jsonify(cases_data)
