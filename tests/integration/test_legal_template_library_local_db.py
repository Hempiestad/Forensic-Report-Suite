from pathlib import Path

import database


def test_local_template_library_hierarchy_and_import_export(tmp_path):
    db_file = tmp_path / 'template_local.db'

    old_server_url = database.SERVER_URL
    old_db_name = database.DatabaseManager.DB_NAME
    try:
        database.SERVER_URL = ''
        database.DatabaseManager.DB_NAME = str(db_file)

        manager = database.DatabaseManager()

        created_one = manager.create_legal_template(
            owner_username='alice',
            vendor_name='Google',
            template_type='subpoena',
            title='Google Subpoena - Accounts',
            template_content='<p>Template 1</p>',
            tags=['google'],
        )
        assert created_one is not None

        created_two = manager.create_legal_template(
            owner_username='alice',
            vendor_name='Google',
            template_type='subpoena',
            title='Google Subpoena - IP Logs',
            template_content='<p>Template 2</p>',
            tags=['ip-logs'],
        )
        assert created_two is not None

        created_three = manager.create_legal_template(
            owner_username='alice',
            vendor_name='Apple',
            template_type='search_warrant',
            title='Apple Search Warrant - iCloud',
            template_content='<p>Template 3</p>',
            tags=['apple'],
        )
        assert created_three is not None

        listed = manager.list_legal_template_library('alice', 'writer')
        assert len(listed) == 3
        assert sum(1 for item in listed if item['vendor_name'] == 'Google' and item['template_type'] == 'subpoena') == 2

        shared_scoped = manager.share_legal_template_library_scoped(
            owner_username='alice',
            shared_with='bob',
            vendor_name='Google',
            template_type='subpoena',
        )
        assert shared_scoped == 2

        bob_visible = manager.list_legal_template_library('bob', 'writer')
        bob_titles = {item['title'] for item in bob_visible}
        assert 'Google Subpoena - Accounts' in bob_titles
        assert 'Google Subpoena - IP Logs' in bob_titles
        assert 'Apple Search Warrant - iCloud' not in bob_titles

        exported = manager.export_legal_template_library('alice', role='writer')
        assert exported.get('schema_version') == 1
        assert len(exported.get('templates', [])) == 3

        imported = manager.import_legal_template_library('bob', exported, mode='append', role='writer')
        assert imported['imported'] == 3

        bob_listed = manager.list_legal_template_library('bob', 'writer')
        assert len([item for item in bob_listed if item.get('is_owned')]) == 3

        replace_payload = {
            'templates': [
                {
                    'vendor_name': 'Meta',
                    'template_type': 'preservation_letter',
                    'title': 'Meta Preservation Letter - Emergency',
                    'template_content': '<p>Template Replacement</p>',
                    'tags': ['meta', 'emergency'],
                }
            ]
        }
        replaced = manager.import_legal_template_library('bob', replace_payload, mode='replace', role='writer')
        assert replaced['imported'] == 1

        bob_after_replace = manager.list_legal_template_library('bob', 'writer')
        owned_after_replace = [item for item in bob_after_replace if item.get('is_owned')]
        assert len(owned_after_replace) == 1
        assert owned_after_replace[0]['vendor_name'] == 'Meta'

        manager.close()
    finally:
        database.SERVER_URL = old_server_url
        database.DatabaseManager.DB_NAME = old_db_name
