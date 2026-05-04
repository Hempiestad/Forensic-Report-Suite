from datetime import datetime
import json

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func, or_

from .infrastructure.api.decorators import rate_limit
from .infrastructure.observability import get_logger
from .models import (
    LegalTemplateLibrary,
    LegalTemplateShare,
    SupervisorAssignment,
    UserAccount,
    db,
)


legal_template_library_bp = Blueprint('legal_template_library', __name__, url_prefix='/api/v1/legal-template-library')
_log = get_logger(__name__)

_ALLOWED_TEMPLATE_TYPES = {
    'preservation_letter',
    'subpoena',
    'search_warrant',
    'other',
}


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
        or_(
            func.lower(SupervisorAssignment.examiner) == user,
            func.lower(SupervisorAssignment.investigator) == user,
        ),
    ).all()
    return {str(r.supervisor).strip().lower() for r in rows if r.supervisor}


def _is_supervisor_for_user(supervisor_username: str, username: str) -> bool:
    sup = (supervisor_username or '').strip().lower()
    user = (username or '').strip().lower()
    if not sup or not user:
        return False
    row = SupervisorAssignment.query.filter(
        SupervisorAssignment.is_active.is_(True),
        func.lower(SupervisorAssignment.supervisor) == sup,
        or_(
            func.lower(SupervisorAssignment.investigator) == user,
            func.lower(SupervisorAssignment.examiner) == user,
        ),
    ).first()
    return row is not None


def _can_share_between(owner_username: str, recipient_username: str) -> bool:
    owner = (owner_username or '').strip().lower()
    recipient = (recipient_username or '').strip().lower()
    if not owner or not recipient:
        return False
    if owner == recipient:
        return True
    owner_sup = _supervisors_for_user(owner)
    recipient_sup = _supervisors_for_user(recipient)
    if owner_sup and recipient_sup and owner_sup.intersection(recipient_sup):
        return True
    return False


def _serialize_tags(tags_json: str) -> list[str]:
    if not tags_json:
        return []
    try:
        raw = json.loads(tags_json)
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
    except Exception:
        return []
    return []


def _as_template_dict(template: LegalTemplateLibrary, actor_username: str, is_shared: bool) -> dict:
    return {
        'id': template.id,
        'owner_username': template.owner_username,
        'vendor_name': template.vendor_name,
        'template_type': template.template_type,
        'title': template.title,
        'template_content': template.template_content,
        'tags': _serialize_tags(template.tags),
        'is_shared': bool(is_shared),
        'is_owned': str(template.owner_username).strip().lower() == actor_username.lower(),
        'created_at': template.created_at.isoformat() if template.created_at else None,
        'updated_at': template.updated_at.isoformat() if template.updated_at else None,
    }


@legal_template_library_bp.route('/templates', methods=['GET'])
@jwt_required()
@rate_limit(limit=200, window_seconds=60, strategy='user_or_ip')
def list_templates():
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    if role == 'admin':
        rows = LegalTemplateLibrary.query.filter_by(is_active=True).order_by(LegalTemplateLibrary.updated_at.desc()).all()
        payload = [_as_template_dict(row, actor, is_shared=False) for row in rows]
    else:
        owned_rows = LegalTemplateLibrary.query.filter(
            LegalTemplateLibrary.is_active.is_(True),
            func.lower(LegalTemplateLibrary.owner_username) == actor.lower(),
        ).all()

        shared_rows = (
            db.session.query(LegalTemplateLibrary)
            .join(LegalTemplateShare, LegalTemplateShare.template_id == LegalTemplateLibrary.id)
            .filter(
                LegalTemplateLibrary.is_active.is_(True),
                func.lower(LegalTemplateShare.shared_with) == actor.lower(),
            )
            .all()
        )

        row_map: dict[int, tuple[LegalTemplateLibrary, bool]] = {}
        for row in owned_rows:
            row_map[row.id] = (row, False)
        for row in shared_rows:
            if row.id not in row_map:
                row_map[row.id] = (row, True)

        payload = [
            _as_template_dict(item[0], actor, item[1])
            for item in sorted(
                row_map.values(),
                key=lambda pair: pair[0].updated_at or datetime.min,
                reverse=True,
            )
        ]

    _log.info('legal_template_listed', extra={'actor': actor, 'role': role, 'count': len(payload)})
    return jsonify(payload)


@legal_template_library_bp.route('/templates', methods=['POST'])
@jwt_required()
@rate_limit(limit=100, window_seconds=60, strategy='user_or_ip')
def create_template():
    ident = _identity()
    actor = ident['username']

    data = request.get_json(silent=True) or {}
    vendor_name = str(data.get('vendor_name') or 'General Vendor').strip()
    template_type = str(data.get('template_type') or 'other').strip().lower()
    title = str(data.get('title') or '').strip()
    content = str(data.get('template_content') or '').strip()
    tags = data.get('tags') or []

    if template_type not in _ALLOWED_TEMPLATE_TYPES:
        return jsonify({'error': 'Invalid template_type'}), 400
    if not vendor_name or not title or not content:
        return jsonify({'error': 'vendor_name, title and template_content are required'}), 400

    if not isinstance(tags, list):
        tags = [str(tags)]
    tags = [str(tag).strip() for tag in tags if str(tag).strip()]

    row = LegalTemplateLibrary(
        owner_username=actor,
        vendor_name=vendor_name,
        template_type=template_type,
        title=title,
        template_content=content,
        tags=json.dumps(tags),
        is_active=True,
    )
    db.session.add(row)
    db.session.commit()

    _log.info('legal_template_created', extra={'actor': actor, 'template_id': row.id, 'template_type': template_type})
    return jsonify(_as_template_dict(row, actor, is_shared=False)), 201


@legal_template_library_bp.route('/templates/<int:template_id>', methods=['PUT'])
@jwt_required()
@rate_limit(limit=120, window_seconds=60, strategy='user_or_ip')
def update_template(template_id: int):
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    row = LegalTemplateLibrary.query.filter_by(id=template_id, is_active=True).first()
    if not row:
        return jsonify({'error': 'Template not found'}), 404

    if role != 'admin' and str(row.owner_username).strip().lower() != actor.lower():
        _log.warning('legal_template_update_denied', extra={'actor': actor, 'template_id': template_id})
        return jsonify({'error': 'Only the owner can update this template'}), 403

    data = request.get_json(silent=True) or {}
    vendor_name = str(data.get('vendor_name') or row.vendor_name or 'General Vendor').strip()
    template_type = str(data.get('template_type') or row.template_type).strip().lower()
    if template_type not in _ALLOWED_TEMPLATE_TYPES:
        return jsonify({'error': 'Invalid template_type'}), 400

    title = str(data.get('title') or row.title).strip()
    content = str(data.get('template_content') or row.template_content).strip()
    tags = data.get('tags')

    if not vendor_name or not title or not content:
        return jsonify({'error': 'vendor_name, title and template_content are required'}), 400

    row.vendor_name = vendor_name
    row.template_type = template_type
    row.title = title
    row.template_content = content
    row.updated_at = datetime.utcnow()

    if tags is not None:
        if not isinstance(tags, list):
            tags = [str(tags)]
        row.tags = json.dumps([str(tag).strip() for tag in tags if str(tag).strip()])

    db.session.add(row)
    db.session.commit()

    _log.info('legal_template_updated', extra={'actor': actor, 'template_id': template_id})
    return jsonify(_as_template_dict(row, actor, is_shared=False)), 200


@legal_template_library_bp.route('/export', methods=['GET'])
@jwt_required()
@rate_limit(limit=30, window_seconds=60, strategy='user_or_ip')
def export_library():
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    owner = actor.lower()
    if role == 'admin':
        requested_owner = str(request.args.get('owner_username') or '').strip().lower()
        if requested_owner:
            owner = requested_owner

    rows = LegalTemplateLibrary.query.filter(
        LegalTemplateLibrary.is_active.is_(True),
        func.lower(LegalTemplateLibrary.owner_username) == owner,
    ).order_by(LegalTemplateLibrary.vendor_name.asc(), LegalTemplateLibrary.template_type.asc(), LegalTemplateLibrary.title.asc()).all()

    payload = {
        'schema_version': 1,
        'exported_at': datetime.utcnow().isoformat(),
        'owner_username': owner,
        'templates': [
            {
                'vendor_name': row.vendor_name,
                'template_type': row.template_type,
                'title': row.title,
                'template_content': row.template_content,
                'tags': _serialize_tags(row.tags),
            }
            for row in rows
        ],
    }

    _log.info('legal_template_library_exported', extra={'actor': actor, 'owner': owner, 'count': len(payload['templates'])})
    return jsonify(payload), 200


@legal_template_library_bp.route('/import', methods=['POST'])
@jwt_required()
@rate_limit(limit=20, window_seconds=60, strategy='user_or_ip')
def import_library():
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    data = request.get_json(silent=True) or {}
    templates = data.get('templates')
    if not isinstance(templates, list):
        return jsonify({'error': 'templates must be a list'}), 400

    owner = actor.lower()
    if role == 'admin':
        requested_owner = str(data.get('owner_username') or '').strip().lower()
        if requested_owner:
            owner = requested_owner

    mode = str(data.get('mode') or 'append').strip().lower()
    if mode not in {'append', 'replace'}:
        return jsonify({'error': 'mode must be append or replace'}), 400

    if mode == 'replace':
        rows = LegalTemplateLibrary.query.filter(
            LegalTemplateLibrary.is_active.is_(True),
            func.lower(LegalTemplateLibrary.owner_username) == owner,
        ).all()
        for row in rows:
            row.is_active = False
            row.updated_at = datetime.utcnow()
            db.session.add(row)

    imported = 0
    skipped = 0
    for entry in templates:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        vendor_name = str(entry.get('vendor_name') or 'General Vendor').strip()
        template_type = str(entry.get('template_type') or 'other').strip().lower()
        title = str(entry.get('title') or '').strip()
        template_content = str(entry.get('template_content') or '').strip()
        tags = entry.get('tags') or []

        if template_type not in _ALLOWED_TEMPLATE_TYPES or not vendor_name or not title or not template_content:
            skipped += 1
            continue

        if not isinstance(tags, list):
            tags = [str(tags)]
        clean_tags = [str(tag).strip() for tag in tags if str(tag).strip()]

        existing = LegalTemplateLibrary.query.filter(
            LegalTemplateLibrary.is_active.is_(True),
            func.lower(LegalTemplateLibrary.owner_username) == owner,
            func.lower(LegalTemplateLibrary.vendor_name) == vendor_name.lower(),
            func.lower(LegalTemplateLibrary.template_type) == template_type,
            func.lower(LegalTemplateLibrary.title) == title.lower(),
        ).first()
        if existing:
            if mode == 'append':
                skipped += 1
                continue
            existing.template_content = template_content
            existing.tags = json.dumps(clean_tags)
            existing.updated_at = datetime.utcnow()
            db.session.add(existing)
            imported += 1
            continue

        row = LegalTemplateLibrary(
            owner_username=owner,
            vendor_name=vendor_name,
            template_type=template_type,
            title=title,
            template_content=template_content,
            tags=json.dumps(clean_tags),
            is_active=True,
        )
        db.session.add(row)
        imported += 1

    db.session.commit()

    _log.info('legal_template_library_imported', extra={'actor': actor, 'owner': owner, 'imported': imported, 'skipped': skipped, 'mode': mode})
    return jsonify({'message': 'Import complete', 'imported': imported, 'skipped': skipped, 'mode': mode}), 200


@legal_template_library_bp.route('/templates/<int:template_id>', methods=['DELETE'])
@jwt_required()
@rate_limit(limit=60, window_seconds=60, strategy='user_or_ip')
def delete_template(template_id: int):
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    row = LegalTemplateLibrary.query.filter_by(id=template_id, is_active=True).first()
    if not row:
        return jsonify({'error': 'Template not found'}), 404

    if role != 'admin' and str(row.owner_username).strip().lower() != actor.lower():
        _log.warning('legal_template_delete_denied', extra={'actor': actor, 'template_id': template_id})
        return jsonify({'error': 'Only the owner can delete this template'}), 403

    row.is_active = False
    row.updated_at = datetime.utcnow()
    db.session.add(row)
    db.session.commit()

    _log.info('legal_template_deleted', extra={'actor': actor, 'template_id': template_id})
    return jsonify({'message': 'Template deleted'}), 200


@legal_template_library_bp.route('/templates/<int:template_id>/share', methods=['POST'])
@jwt_required()
@rate_limit(limit=90, window_seconds=60, strategy='user_or_ip')
def share_template(template_id: int):
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    row = LegalTemplateLibrary.query.filter_by(id=template_id, is_active=True).first()
    if not row:
        return jsonify({'error': 'Template not found'}), 404

    owner = str(row.owner_username or '').strip().lower()
    if role != 'admin' and owner != actor.lower():
        _log.warning('legal_template_share_denied_not_owner', extra={'actor': actor, 'template_id': template_id})
        return jsonify({'error': 'Only the owner can share this template'}), 403

    data = request.get_json(silent=True) or {}
    shared_with = str(data.get('shared_with') or '').strip().lower()
    if not shared_with:
        return jsonify({'error': 'shared_with is required'}), 400

    recipient = UserAccount.query.filter(
        func.lower(UserAccount.username) == shared_with,
        UserAccount.is_active.is_(True),
    ).first()
    if not recipient:
        return jsonify({'error': 'Target user not found'}), 404

    if shared_with == owner:
        return jsonify({'message': 'Template already available to owner'}), 200

    if role != 'admin':
        if not _can_share_between(owner, shared_with):
            _log.warning(
                'legal_template_share_denied_scope',
                extra={'actor': actor, 'template_id': template_id, 'shared_with': shared_with},
            )
            return jsonify({'error': 'Sharing is only allowed within related supervision groups'}), 403
        if role == 'supervisor' and not _is_supervisor_for_user(actor, shared_with):
            _log.warning(
                'legal_template_share_denied_supervisor_scope',
                extra={'actor': actor, 'template_id': template_id, 'shared_with': shared_with},
            )
            return jsonify({'error': 'Supervisors may only share with assigned users'}), 403

    existing = LegalTemplateShare.query.filter(
        LegalTemplateShare.template_id == template_id,
        func.lower(LegalTemplateShare.shared_with) == shared_with,
    ).first()
    if existing:
        return jsonify({'message': 'Template already shared'}), 200

    share_row = LegalTemplateShare(
        template_id=template_id,
        shared_with=shared_with,
        shared_by=actor,
    )
    db.session.add(share_row)
    db.session.commit()

    _log.info(
        'legal_template_shared',
        extra={'actor': actor, 'template_id': template_id, 'owner': owner, 'shared_with': shared_with},
    )
    return jsonify({'message': 'Template shared'}), 201


@legal_template_library_bp.route('/libraries/share', methods=['POST'])
@jwt_required()
@rate_limit(limit=30, window_seconds=60, strategy='user_or_ip')
def share_library():
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    data = request.get_json(silent=True) or {}
    shared_with = str(data.get('shared_with') or '').strip().lower()
    if not shared_with:
        return jsonify({'error': 'shared_with is required'}), 400

    recipient = UserAccount.query.filter(
        func.lower(UserAccount.username) == shared_with,
        UserAccount.is_active.is_(True),
    ).first()
    if not recipient:
        return jsonify({'error': 'Target user not found'}), 404

    owner = actor.lower()
    if role == 'admin':
        requested_owner = str(data.get('owner_username') or '').strip().lower()
        if requested_owner:
            owner = requested_owner

    if role != 'admin':
        if not _can_share_between(owner, shared_with):
            _log.warning('legal_template_library_share_denied_scope', extra={'actor': actor, 'owner': owner, 'shared_with': shared_with})
            return jsonify({'error': 'Sharing is only allowed within related supervision groups'}), 403
        if role == 'supervisor' and not _is_supervisor_for_user(actor, shared_with):
            _log.warning('legal_template_library_share_denied_supervisor_scope', extra={'actor': actor, 'owner': owner, 'shared_with': shared_with})
            return jsonify({'error': 'Supervisors may only share with assigned users'}), 403

    rows = LegalTemplateLibrary.query.filter(
        LegalTemplateLibrary.is_active.is_(True),
        func.lower(LegalTemplateLibrary.owner_username) == owner,
    ).all()

    created = 0
    for row in rows:
        if shared_with == owner:
            continue
        exists = LegalTemplateShare.query.filter(
            LegalTemplateShare.template_id == row.id,
            func.lower(LegalTemplateShare.shared_with) == shared_with,
        ).first()
        if exists:
            continue
        db.session.add(LegalTemplateShare(template_id=row.id, shared_with=shared_with, shared_by=actor))
        created += 1

    db.session.commit()

    _log.info(
        'legal_template_library_shared',
        extra={'actor': actor, 'owner': owner, 'shared_with': shared_with, 'templates_shared': created},
    )
    return jsonify({'message': 'Library shared', 'templates_shared': created}), 200


@legal_template_library_bp.route('/libraries/share-scoped', methods=['POST'])
@jwt_required()
@rate_limit(limit=40, window_seconds=60, strategy='user_or_ip')
def share_library_scoped():
    """Share a subset of templates by vendor and optional template type."""
    ident = _identity()
    actor = ident['username']
    role = ident['role']

    data = request.get_json(silent=True) or {}
    shared_with = str(data.get('shared_with') or '').strip().lower()
    vendor_name = str(data.get('vendor_name') or '').strip()
    template_type = str(data.get('template_type') or '').strip().lower()

    if not shared_with:
        return jsonify({'error': 'shared_with is required'}), 400
    if not vendor_name:
        return jsonify({'error': 'vendor_name is required for scoped share'}), 400
    if template_type and template_type not in _ALLOWED_TEMPLATE_TYPES:
        return jsonify({'error': 'Invalid template_type'}), 400

    recipient = UserAccount.query.filter(
        func.lower(UserAccount.username) == shared_with,
        UserAccount.is_active.is_(True),
    ).first()
    if not recipient:
        return jsonify({'error': 'Target user not found'}), 404

    owner = actor.lower()
    if role == 'admin':
        requested_owner = str(data.get('owner_username') or '').strip().lower()
        if requested_owner:
            owner = requested_owner

    if role != 'admin':
        if not _can_share_between(owner, shared_with):
            _log.warning('legal_template_library_share_scoped_denied_scope', extra={'actor': actor, 'owner': owner, 'shared_with': shared_with})
            return jsonify({'error': 'Sharing is only allowed within related supervision groups'}), 403
        if role == 'supervisor' and not _is_supervisor_for_user(actor, shared_with):
            _log.warning('legal_template_library_share_scoped_denied_supervisor_scope', extra={'actor': actor, 'owner': owner, 'shared_with': shared_with})
            return jsonify({'error': 'Supervisors may only share with assigned users'}), 403

    query = LegalTemplateLibrary.query.filter(
        LegalTemplateLibrary.is_active.is_(True),
        func.lower(LegalTemplateLibrary.owner_username) == owner,
        func.lower(LegalTemplateLibrary.vendor_name) == vendor_name.lower(),
    )
    if template_type:
        query = query.filter(func.lower(LegalTemplateLibrary.template_type) == template_type)

    rows = query.all()
    created = 0
    for row in rows:
        if shared_with == owner:
            continue
        exists = LegalTemplateShare.query.filter(
            LegalTemplateShare.template_id == row.id,
            func.lower(LegalTemplateShare.shared_with) == shared_with,
        ).first()
        if exists:
            continue
        db.session.add(LegalTemplateShare(template_id=row.id, shared_with=shared_with, shared_by=actor))
        created += 1

    db.session.commit()

    _log.info(
        'legal_template_library_shared_scoped',
        extra={
            'actor': actor,
            'owner': owner,
            'shared_with': shared_with,
            'vendor_name': vendor_name,
            'template_type': template_type or '',
            'templates_shared': created,
        },
    )
    return jsonify({'message': 'Scoped library share complete', 'templates_shared': created}), 200
