from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime

from .models import db, UserAccount, SupervisorAssignment
from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger

users_bp = Blueprint('users', __name__, url_prefix='/api/v1/users')
supervisor_bp = Blueprint('supervisors', __name__, url_prefix='/api/v1/supervisor-assignments')
_log = get_logger(__name__)

VALID_ROLES = {'admin', 'supervisor', 'examiner', 'writer'}


def _identity() -> dict:
    identity = get_jwt_identity()
    if isinstance(identity, dict):
        return {
            'username': str(identity.get('username', 'unknown')),
            'role': str(identity.get('role', 'writer')).lower(),
        }
    claims = get_jwt() or {}
    return {
        'username': str(claims.get('username') or identity or 'unknown'),
        'role': str(claims.get('role') or 'writer').lower(),
    }


def _require_admin(identity: dict):
    if identity['role'] != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    return None


def _user_to_dict(u: UserAccount) -> dict:
    return {
        'username': u.username,
        'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat() if u.created_at else None,
    }


# ---------------------------------------------------------------------------
# User management endpoints (admin only)
# ---------------------------------------------------------------------------

@users_bp.route('', methods=['GET'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def list_users():
    identity = _identity()
    # Supervisors may list users to assign them; admins get full list
    if identity['role'] not in ('admin', 'supervisor'):
        return jsonify({'error': 'Access denied'}), 403

    role_filter = request.args.get('role', '').strip().lower()
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    q = UserAccount.query
    if active_only:
        q = q.filter(UserAccount.is_active.is_(True))
    if role_filter and role_filter in VALID_ROLES:
        q = q.filter(UserAccount.role == role_filter)

    users = q.order_by(UserAccount.username).all()
    return jsonify({'users': [_user_to_dict(u) for u in users]}), 200


@users_bp.route('', methods=['POST'])
@jwt_required()
@rate_limit(limit=20, window_seconds=60, strategy='user_or_ip')
def create_user():
    identity = _identity()
    err = _require_admin(identity)
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    username = str(payload.get('username') or '').strip().lower()
    role = str(payload.get('role') or 'writer').strip().lower()

    if not username:
        return jsonify({'error': 'username is required'}), 400
    if role not in VALID_ROLES:
        return jsonify({'error': f'role must be one of: {", ".join(sorted(VALID_ROLES))}'}), 400
    if len(username) > 100:
        return jsonify({'error': 'username too long (max 100 chars)'}), 400

    if UserAccount.query.get(username):
        return jsonify({'error': 'User already exists'}), 409

    user = UserAccount(username=username, role=role, is_active=True, created_at=datetime.utcnow())
    db.session.add(user)
    db.session.commit()
    _log.info('User created', extra={'admin': identity['username'], 'new_user': username, 'role': role})
    return jsonify({'user': _user_to_dict(user)}), 201


@users_bp.route('/<username>', methods=['PUT'])
@jwt_required()
@rate_limit(limit=30, window_seconds=60, strategy='user_or_ip')
def update_user(username: str):
    identity = _identity()
    err = _require_admin(identity)
    if err:
        return err

    user = UserAccount.query.get(username.lower())
    if not user:
        return jsonify({'error': 'User not found'}), 404

    payload = request.get_json(silent=True) or {}

    if 'role' in payload:
        role = str(payload['role']).strip().lower()
        if role not in VALID_ROLES:
            return jsonify({'error': f'role must be one of: {", ".join(sorted(VALID_ROLES))}'}), 400
        user.role = role

    if 'is_active' in payload:
        user.is_active = bool(payload['is_active'])

    db.session.commit()
    _log.info('User updated', extra={'admin': identity['username'], 'target': username})
    return jsonify({'user': _user_to_dict(user)}), 200


@users_bp.route('/<username>', methods=['DELETE'])
@jwt_required()
@rate_limit(limit=20, window_seconds=60, strategy='user_or_ip')
def deactivate_user(username: str):
    """Soft-delete: sets is_active=False rather than removing the record."""
    identity = _identity()
    err = _require_admin(identity)
    if err:
        return err

    if username.lower() == identity['username'].lower():
        return jsonify({'error': 'Cannot deactivate your own account'}), 400

    user = UserAccount.query.get(username.lower())
    if not user:
        return jsonify({'error': 'User not found'}), 404

    user.is_active = False
    db.session.commit()
    _log.info('User deactivated', extra={'admin': identity['username'], 'target': username})
    return jsonify({'message': f"User '{username}' deactivated"}), 200


@users_bp.route('/roles', methods=['GET'])
@jwt_required()
def list_roles():
    return jsonify({'roles': sorted(VALID_ROLES)}), 200


# ---------------------------------------------------------------------------
# Supervisor assignment endpoints
# ---------------------------------------------------------------------------

def _assignment_to_dict(a: SupervisorAssignment) -> dict:
    return {
        'id': a.id,
        'supervisor': a.supervisor,
        'investigator': a.investigator,
        'examiner': a.examiner,
        'assigned_by': a.assigned_by,
        'created_at': a.created_at.isoformat() if a.created_at else None,
        'is_active': a.is_active,
    }


@supervisor_bp.route('', methods=['GET'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def list_assignments():
    identity = _identity()
    if identity['role'] not in ('admin', 'supervisor'):
        return jsonify({'error': 'Access denied'}), 403

    q = SupervisorAssignment.query.filter(SupervisorAssignment.is_active.is_(True))

    # Supervisors only see their own assignments
    if identity['role'] == 'supervisor':
        q = q.filter(SupervisorAssignment.supervisor == identity['username'])

    assignments = q.order_by(SupervisorAssignment.supervisor, SupervisorAssignment.investigator).all()
    return jsonify({'assignments': [_assignment_to_dict(a) for a in assignments]}), 200


@supervisor_bp.route('', methods=['POST'])
@jwt_required()
@rate_limit(limit=30, window_seconds=60, strategy='user_or_ip')
def create_assignment():
    identity = _identity()
    err = _require_admin(identity)
    if err:
        return err

    payload = request.get_json(silent=True) or {}
    supervisor = str(payload.get('supervisor') or '').strip().lower()
    investigator = str(payload.get('investigator') or '').strip().lower()
    examiner = str(payload.get('examiner') or '').strip().lower() or None

    if not supervisor or not investigator:
        return jsonify({'error': 'supervisor and investigator are required'}), 400

    # Verify supervisor exists and has supervisor/admin role
    sup_user = UserAccount.query.get(supervisor)
    if not sup_user or sup_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'supervisor must be an existing user with supervisor or admin role'}), 400

    existing = SupervisorAssignment.query.filter_by(
        supervisor=supervisor, investigator=investigator, examiner=examiner, is_active=True
    ).first()
    if existing:
        return jsonify({'error': 'Assignment already exists'}), 409

    assignment = SupervisorAssignment(
        supervisor=supervisor,
        investigator=investigator,
        examiner=examiner,
        assigned_by=identity['username'],
        created_at=datetime.utcnow(),
        is_active=True,
    )
    db.session.add(assignment)
    db.session.commit()
    _log.info('Supervisor assignment created', extra={'admin': identity['username'], 'supervisor': supervisor, 'investigator': investigator})
    return jsonify({'assignment': _assignment_to_dict(assignment)}), 201


@supervisor_bp.route('/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
@rate_limit(limit=30, window_seconds=60, strategy='user_or_ip')
def delete_assignment(assignment_id: int):
    identity = _identity()
    err = _require_admin(identity)
    if err:
        return err

    assignment = SupervisorAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Assignment not found'}), 404

    assignment.is_active = False
    db.session.commit()
    _log.info('Supervisor assignment removed', extra={'admin': identity['username'], 'assignment_id': assignment_id})
    return jsonify({'message': 'Assignment removed'}), 200
