import os
from pathlib import Path

import pytest
from flask_jwt_extended import create_access_token

from forensic_server_loader import ensure_forensic_server_path

ensure_forensic_server_path()


@pytest.fixture
def app_instance(tmp_path, monkeypatch):
    db_file = tmp_path / 'template_api_server.db'
    monkeypatch.setenv('JWT_SECRET', 'x' * 48)
    monkeypatch.setenv('DATABASE_URL', f"sqlite:///{db_file.as_posix()}")
    monkeypatch.setenv('RATE_LIMIT_ENABLED', 'false')

    from forensic_server.app import create_app
    from forensic_server.models import SupervisorAssignment, UserAccount, db

    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    with app.app_context():
        db.drop_all()
        db.create_all()

        db.session.add(UserAccount(username='admin1', role='admin', is_active=True))
        db.session.add(UserAccount(username='sup1', role='supervisor', is_active=True))
        db.session.add(UserAccount(username='alice', role='writer', is_active=True))
        db.session.add(UserAccount(username='bob', role='writer', is_active=True))

        db.session.add(
            SupervisorAssignment(
                supervisor='sup1',
                investigator='alice',
                examiner='bob',
                assigned_by='admin1',
                is_active=True,
            )
        )
        db.session.commit()

    return app


def _auth_header(app, username: str, role: str) -> dict:
    with app.app_context():
        token = create_access_token(
            identity=username,
            additional_claims={'username': username, 'role': role},
        )
    return {'Authorization': f'Bearer {token}'}


def test_template_hierarchy_share_and_import_export(app_instance):
    client = app_instance.test_client()

    alice_headers = _auth_header(app_instance, 'alice', 'writer')
    bob_headers = _auth_header(app_instance, 'bob', 'writer')

    create_one = client.post(
        '/api/v1/legal-template-library/templates',
        json={
            'vendor_name': 'Google',
            'template_type': 'subpoena',
            'title': 'Google Subpoena - Financial Records',
            'template_content': '<p>Template A</p>',
            'tags': ['google', 'financial'],
        },
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert create_one.status_code == 201
    first_template_id = create_one.get_json()['id']

    create_two = client.post(
        '/api/v1/legal-template-library/templates',
        json={
            'vendor_name': 'Google',
            'template_type': 'subpoena',
            'title': 'Google Subpoena - Subscriber Info',
            'template_content': '<p>Template B</p>',
            'tags': ['google', 'subscriber'],
        },
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert create_two.status_code == 201

    create_three = client.post(
        '/api/v1/legal-template-library/templates',
        json={
            'vendor_name': 'Apple',
            'template_type': 'search_warrant',
            'title': 'Apple Search Warrant - iCloud',
            'template_content': '<p>Template C</p>',
            'tags': ['apple', 'icloud'],
        },
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert create_three.status_code == 201

    list_alice = client.get(
        '/api/v1/legal-template-library/templates',
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert list_alice.status_code == 200
    alice_templates = list_alice.get_json()
    assert len(alice_templates) == 3
    assert {item['vendor_name'] for item in alice_templates} == {'Google', 'Apple'}
    assert sum(1 for item in alice_templates if item['vendor_name'] == 'Google' and item['template_type'] == 'subpoena') == 2

    share_resp = client.post(
        f'/api/v1/legal-template-library/templates/{first_template_id}/share',
        json={'shared_with': 'bob'},
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert share_resp.status_code in (200, 201)

    list_bob = client.get(
        '/api/v1/legal-template-library/templates',
        headers=bob_headers,
        base_url='https://localhost',
    )
    assert list_bob.status_code == 200
    bob_visible = list_bob.get_json()
    assert any(item['title'] == 'Google Subpoena - Financial Records' for item in bob_visible)

    scoped_share_resp = client.post(
        '/api/v1/legal-template-library/libraries/share-scoped',
        json={
            'shared_with': 'bob',
            'vendor_name': 'Google',
            'template_type': 'subpoena',
        },
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert scoped_share_resp.status_code == 200
    assert int((scoped_share_resp.get_json() or {}).get('templates_shared', 0)) >= 1

    list_bob_after_scoped = client.get(
        '/api/v1/legal-template-library/templates',
        headers=bob_headers,
        base_url='https://localhost',
    )
    assert list_bob_after_scoped.status_code == 200
    bob_titles = {item['title'] for item in list_bob_after_scoped.get_json()}
    assert 'Google Subpoena - Financial Records' in bob_titles
    assert 'Google Subpoena - Subscriber Info' in bob_titles

    export_resp = client.get(
        '/api/v1/legal-template-library/export',
        headers=alice_headers,
        base_url='https://localhost',
    )
    assert export_resp.status_code == 200
    export_payload = export_resp.get_json()
    assert len(export_payload.get('templates', [])) == 3

    import_resp = client.post(
        '/api/v1/legal-template-library/import',
        json={'templates': export_payload['templates'], 'mode': 'append'},
        headers=bob_headers,
        base_url='https://localhost',
    )
    assert import_resp.status_code == 200
    import_result = import_resp.get_json()
    assert int(import_result.get('imported', 0)) >= 1
