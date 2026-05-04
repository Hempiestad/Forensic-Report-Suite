from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func, or_

from .models import Case, EvidenceItem, LegalProcess, UserAccount, SupervisorAssignment, db
from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger


server_view_bp = Blueprint('server_view', __name__, url_prefix='/api/v1/server-view')
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


def _require_roles(*allowed_roles: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    allowed = {role.lower() for role in allowed_roles}

    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def _wrapper(*args: Any, **kwargs: Any):
            ident = _identity()
            if ident['role'] not in allowed:
                return jsonify({'error': 'Permission denied'}), 403
            return func(*args, **kwargs)

        return _wrapper

    return _decorator


def _is_supervisor_assigned_case(supervisor_username: str, case: Case) -> bool:
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


def _toolbar_for_role(role: str) -> dict[str, list[dict[str, str]]]:
    management_actions = [
        {'id': 'reassign_case', 'label': 'Reassign Case', 'scope': 'case'},
        {'id': 'set_priority', 'label': 'Set Priority', 'scope': 'case'},
        {'id': 'escalate_case', 'label': 'Escalate', 'scope': 'case'},
        {'id': 'request_review', 'label': 'Request Review', 'scope': 'case'},
        {'id': 'export_team_report', 'label': 'Export Team Report', 'scope': 'team'},
    ]
    admin_actions = [
        {'id': 'add_user', 'label': 'Add User', 'scope': 'admin'},
        {'id': 'remove_user', 'label': 'Remove User', 'scope': 'admin'},
        {'id': 'disable_user', 'label': 'Disable User', 'scope': 'admin'},
        {'id': 'assign_role', 'label': 'Assign Role', 'scope': 'admin'},
    ]

    tabs = ['cases', 'examiners', 'queue', 'discovery', 'reports']
    if role == 'admin':
        tabs.append('settings')

    return {
        'tabs': [{'id': tab, 'label': tab.title()} for tab in tabs],
        'management_toolbar': management_actions,
        'admin_toolbar': admin_actions if role == 'admin' else [],
    }


@server_view_bp.route('/layout', methods=['GET'])
@jwt_required()
@_require_roles('admin', 'supervisor')
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def get_layout():
    ident = _identity()
    layout = _toolbar_for_role(ident['role'])
    return jsonify(
        {
            'role': ident['role'],
            'username': ident['username'],
            'default_tab': 'cases',
            'default_view_mode': 'case',
            'layout': layout,
            'focus': 'case_management',
        }
    )


@server_view_bp.route('/cases', methods=['GET'])
@jwt_required()
@_require_roles('admin', 'supervisor')
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def get_case_management_view():
    ident = _identity()
    view_mode = (request.args.get('view', 'case') or 'case').lower()
    search = (request.args.get('search', '') or '').strip().lower()
    status_filter = (request.args.get('status', '') or '').strip().lower()
    examiner_filter = (request.args.get('examiner', '') or '').strip().lower()

    cases = Case.query.all()
    case_rows = []
    for case in cases:
        if ident['role'] == 'supervisor' and not _is_supervisor_assigned_case(ident['username'], case):
            continue

        examiner = (case.examiner_id or case.assigned_to or '').strip()
        row = {
            'case_number': case.case_number,
            'title': case.title or '',
            'status': case.status,
            'assigned_to': case.assigned_to or '',
            'examiner': examiner,
            'trial_date': case.trial_date,
            'sentencing_date': case.sentencing_date,
            'evidence_count': EvidenceItem.query.filter_by(case_number=case.case_number).count(),
            'legal_count': LegalProcess.query.filter_by(case_number=case.case_number).count(),
        }

        if status_filter and row['status'].lower() != status_filter:
            continue
        if examiner_filter and examiner_filter not in row['examiner'].lower():
            continue
        if search and not (
            search in row['case_number'].lower()
            or search in row['title'].lower()
            or search in row['assigned_to'].lower()
            or search in row['examiner'].lower()
        ):
            continue

        case_rows.append(row)

    if view_mode == 'examiner':
        grouped: dict[str, dict[str, Any]] = {}
        for row in case_rows:
            examiner = row['examiner'] or 'unassigned'
            bucket = grouped.setdefault(
                examiner,
                {
                    'examiner': examiner,
                    'case_count': 0,
                    'active_count': 0,
                    'cases': [],
                },
            )
            bucket['case_count'] += 1
            if row['status'] not in {'approved', 'closed'}:
                bucket['active_count'] += 1
            bucket['cases'].append(row)

        return jsonify(
            {
                'view': 'examiner',
                'total_examiners': len(grouped),
                'rows': sorted(grouped.values(), key=lambda item: item['examiner'].lower()),
            }
        )

    _log.info(
        'server_view_case_list',
        extra={
            'viewer': ident['username'],
            'role': ident['role'],
            'view_mode': view_mode,
            'rows_returned': len(case_rows),
        },
    )
    return jsonify(
        {
            'view': 'case',
            'total_cases': len(case_rows),
            'rows': sorted(case_rows, key=lambda item: item['case_number'].lower()),
        }
    )


@server_view_bp.route('/search', methods=['GET'])
@jwt_required()
@_require_roles('admin', 'supervisor')
@rate_limit(limit=240, window_seconds=60, strategy='user_or_ip')
def search_case_management():
    ident = _identity()
    query = (request.args.get('q', '') or '').strip().lower()
    scope = (request.args.get('scope', 'all') or 'all').strip().lower()
    if not query:
        return jsonify({'results': [], 'count': 0})

    results: list[dict[str, str]] = []
    if scope in {'all', 'cases'}:
        for case in Case.query.all():
            if ident['role'] == 'supervisor' and not _is_supervisor_assigned_case(ident['username'], case):
                continue
            haystack = ' '.join([case.case_number or '', case.title or '', case.assigned_to or '', case.examiner_id or '']).lower()
            if query in haystack:
                results.append(
                    {
                        'type': 'case',
                        'id': case.case_number,
                        'title': case.title or case.case_number,
                        'status': case.status,
                    }
                )

    if scope in {'all', 'examiners', 'investigators'}:
        seen = set()
        for case in Case.query.all():
            if ident['role'] == 'supervisor' and not _is_supervisor_assigned_case(ident['username'], case):
                continue
            name = (case.examiner_id or case.assigned_to or '').strip()
            if name and query in name.lower() and name.lower() not in seen:
                seen.add(name.lower())
                results.append({'type': 'examiner', 'id': name, 'title': name})

    _log.info(
        'server_view_search',
        extra={
            'viewer': ident['username'],
            'role': ident['role'],
            'query': query,
            'scope': scope,
            'results': len(results),
        },
    )
    return jsonify({'results': results, 'count': len(results), 'query': query, 'scope': scope})


@server_view_bp.route('/admin/users', methods=['GET'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=180, window_seconds=60, strategy='user_or_ip')
def list_users():
    ident = _identity()
    users = UserAccount.query.order_by(UserAccount.username.asc()).all()
    _log.info('admin_users_listed', extra={'actor': ident['username'], 'count': len(users)})
    return jsonify(
        [
            {
                'username': user.username,
                'role': user.role,
                'is_active': user.is_active,
                'created_at': user.created_at.isoformat() if user.created_at else None,
            }
            for user in users
        ]
    )


@server_view_bp.route('/admin/users', methods=['POST'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def add_user():
    ident = _identity()
    data = request.get_json(silent=True) or {}
    username = str(data.get('username', '')).strip().lower()
    role = str(data.get('role', 'writer')).strip().lower()

    if not username:
        return jsonify({'error': 'username is required'}), 400
    if role not in {'admin', 'supervisor', 'writer'}:
        return jsonify({'error': 'role must be one of admin, supervisor, writer'}), 400

    existing = UserAccount.query.get(username)
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.role = role
            db.session.commit()
            _log.info('admin_user_reactivated', extra={'actor': ident['username'], 'target_user': username, 'role': role})
            return jsonify({'message': 'User reactivated', 'username': username, 'role': role}), 200
        return jsonify({'error': 'User already exists'}), 409

    user = UserAccount(username=username, role=role, is_active=True)
    db.session.add(user)
    db.session.commit()
    _log.info('admin_user_created', extra={'actor': ident['username'], 'target_user': username, 'role': role})
    return jsonify({'message': 'User created', 'username': username, 'role': role}), 201


@server_view_bp.route('/admin/users/<string:username>', methods=['DELETE'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def remove_user(username: str):
    ident = _identity()
    user = UserAccount.query.get(username.lower())
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.is_active = False
    db.session.commit()
    _log.info('admin_user_disabled', extra={'actor': ident['username'], 'target_user': user.username})
    return jsonify({'message': 'User disabled', 'username': user.username})


@server_view_bp.route('/admin/supervisor-assignments', methods=['GET'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=180, window_seconds=60, strategy='user_or_ip')
def list_supervisor_assignments():
    supervisor = str(request.args.get('supervisor', '') or '').strip().lower()
    investigator = str(request.args.get('investigator', '') or '').strip().lower()
    examiner = str(request.args.get('examiner', '') or '').strip().lower()

    query = SupervisorAssignment.query.filter_by(is_active=True)
    if supervisor:
        query = query.filter(SupervisorAssignment.supervisor.ilike(f'%{supervisor}%'))
    if investigator:
        query = query.filter(SupervisorAssignment.investigator.ilike(f'%{investigator}%'))
    if examiner:
        query = query.filter(SupervisorAssignment.examiner.ilike(f'%{examiner}%'))

    rows = query.order_by(SupervisorAssignment.created_at.desc()).all()
    ident = _identity()
    _log.info('supervisor_assignments_listed', extra={'actor': ident['username'], 'count': len(rows)})
    return jsonify(
        [
            {
                'id': row.id,
                'supervisor': row.supervisor,
                'investigator': row.investigator,
                'examiner': row.examiner,
                'assigned_by': row.assigned_by,
                'created_at': row.created_at.isoformat() if row.created_at else None,
                'is_active': row.is_active,
            }
            for row in rows
        ]
    )


@server_view_bp.route('/admin/supervisor-assignments', methods=['POST'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def add_supervisor_assignment():
    ident = _identity()
    data = request.get_json(silent=True) or {}

    supervisor = str(data.get('supervisor', '') or '').strip().lower()
    investigator = str(data.get('investigator', '') or '').strip().lower()
    examiner = str(data.get('examiner', '') or '').strip().lower() or None

    if not supervisor or not investigator:
        return jsonify({'error': 'supervisor and investigator are required'}), 400

    row = SupervisorAssignment.query.filter_by(
        supervisor=supervisor,
        investigator=investigator,
        examiner=examiner,
        is_active=True,
    ).first()
    if row:
        return jsonify({'error': 'Assignment already exists'}), 409

    assignment = SupervisorAssignment(
        supervisor=supervisor,
        investigator=investigator,
        examiner=examiner,
        assigned_by=ident['username'],
        is_active=True,
    )
    db.session.add(assignment)
    db.session.commit()
    _log.info(
        'supervisor_assignment_created',
        extra={
            'actor': ident['username'],
            'supervisor': supervisor,
            'investigator': investigator,
            'examiner': examiner or '',
            'assignment_id': assignment.id,
        },
    )
    return jsonify({'message': 'Assignment created', 'id': assignment.id}), 201


@server_view_bp.route('/admin/supervisor-assignments/<int:assignment_id>', methods=['DELETE'])
@jwt_required()
@_require_roles('admin')
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def remove_supervisor_assignment(assignment_id: int):
    ident = _identity()
    row = SupervisorAssignment.query.get(assignment_id)
    if not row:
        return jsonify({'error': 'Assignment not found'}), 404
    row.is_active = False
    db.session.commit()
    _log.info(
        'supervisor_assignment_removed',
        extra={
            'actor': ident['username'],
            'assignment_id': assignment_id,
            'supervisor': row.supervisor,
            'investigator': row.investigator,
            'examiner': row.examiner or '',
        },
    )
    return jsonify({'message': 'Assignment removed', 'id': assignment_id})
