import sys
import types
from flask import Flask

def make_stub_models():
    mod = types.ModuleType("models")

    class DummySession:
        def commit(self):
            return None

    class DummyDB:
        session = DummySession()

    class Case:
        instances = {}

        def __init__(self, case_number, assigned_to=None):
            self.case_number = case_number
            self.assigned_to = assigned_to
            self.status = 'draft'
            self.trial_date = None
            self.sentencing_date = None
            Case.instances[case_number] = self

        class query:
            @staticmethod
            def get(case_number):
                return Case.instances.get(case_number)

    mod.db = DummyDB()
    mod.Case = Case
    mod.EvidenceItem = object
    mod.LegalProcess = object
    return mod

def make_jwt_for_role(role, username='user1'):
    mod = types.ModuleType('flask_jwt_extended')
    def jwt_required():
        def decorator(f):
            return f
        return decorator
    def get_jwt_identity():
        return {'username': username, 'role': role}
    mod.jwt_required = jwt_required
    mod.get_jwt_identity = get_jwt_identity
    return mod

def test_put_dates_assigned_user_allowed():
    sys.modules['models'] = make_stub_models()
    sys.modules['flask_jwt_extended'] = make_jwt_for_role('writer', username='assigned')
    schemas_mod = types.ModuleType('schemas')
    class DummySchema: pass
    schemas_mod.CaseCreateSchema = DummySchema
    schemas_mod.EvidenceCreateSchema = DummySchema
    schemas_mod.LegalProcessCreateSchema = DummySchema
    sys.modules['schemas'] = schemas_mod

    from models import Case
    Case('CASE1', assigned_to='assigned')
    if 'cases_bp' in sys.modules:
        del sys.modules['cases_bp']
    from cases_bp import cases_bp

    app = Flask(__name__)
    app.register_blueprint(cases_bp)
    client = app.test_client()
    print('URL_MAP:', list(app.url_map.iter_rules()))
    resp = client.put('/api/v1/cases/CASE1/dates', json={'trial_date':'2026-06-01'})
    print('RESP:', resp.status_code, resp.data)
    assert resp.status_code == 200

def test_put_dates_other_user_denied():
    sys.modules['models'] = make_stub_models()
    sys.modules['flask_jwt_extended'] = make_jwt_for_role('writer', username='other')
    schemas_mod = types.ModuleType('schemas')
    class DummySchema: pass
    schemas_mod.CaseCreateSchema = DummySchema
    schemas_mod.EvidenceCreateSchema = DummySchema
    schemas_mod.LegalProcessCreateSchema = DummySchema
    sys.modules['schemas'] = schemas_mod

    from models import Case
    Case('CASE2', assigned_to='someone')
    if 'cases_bp' in sys.modules:
        del sys.modules['cases_bp']
    from cases_bp import cases_bp

    app = Flask(__name__)
    app.register_blueprint(cases_bp)
    client = app.test_client()
    print('URL_MAP:', list(app.url_map.iter_rules()))
    resp = client.put('/api/v1/cases/CASE2/dates', json={'trial_date':'2026-06-01'})
    print('RESP:', resp.status_code, resp.data)
    assert resp.status_code == 403

def test_put_dates_admin_allowed():
    sys.modules['models'] = make_stub_models()
    sys.modules['flask_jwt_extended'] = make_jwt_for_role('admin', username='admin')
    schemas_mod = types.ModuleType('schemas')
    class DummySchema: pass
    schemas_mod.CaseCreateSchema = DummySchema
    schemas_mod.EvidenceCreateSchema = DummySchema
    schemas_mod.LegalProcessCreateSchema = DummySchema
    sys.modules['schemas'] = schemas_mod

    from models import Case
    Case('CASE3', assigned_to='someone')
    if 'cases_bp' in sys.modules:
        del sys.modules['cases_bp']
    from cases_bp import cases_bp

    app = Flask(__name__)
    app.register_blueprint(cases_bp)
    client = app.test_client()
    print('URL_MAP:', list(app.url_map.iter_rules()))
    resp = client.put('/api/v1/cases/CASE3/dates', json={'trial_date':'2026-07-01'})
    print('RESP:', resp.status_code, resp.data)
    assert resp.status_code == 200
