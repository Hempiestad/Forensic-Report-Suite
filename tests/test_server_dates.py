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


def make_stub_jwt():
    mod = types.ModuleType('flask_jwt_extended')

    def jwt_required():
        def decorator(f):
            return f
        return decorator

    def get_jwt_identity():
        return {'username': 'tester', 'role': 'admin'}

    mod.jwt_required = jwt_required
    mod.get_jwt_identity = get_jwt_identity
    return mod


def test_update_dates_blueprint():
    # Inject stubs before importing the blueprint
    sys.modules['models'] = make_stub_models()
    sys.modules['flask_jwt_extended'] = make_stub_jwt()
    # Minimal schemas stub
    schemas_mod = types.ModuleType('schemas')
    class DummySchema:
        pass
    schemas_mod.CaseCreateSchema = DummySchema
    schemas_mod.EvidenceCreateSchema = DummySchema
    schemas_mod.LegalProcessCreateSchema = DummySchema
    sys.modules['schemas'] = schemas_mod

    # Now import the blueprint (ensure fresh import so it picks up our stub models)
    if 'cases_bp' in sys.modules:
        del sys.modules['cases_bp']
    from cases_bp import cases_bp

    # Create a test case in the stub models
    from models import Case
    Case('SVC123', assigned_to='tester')

    app = Flask(__name__)
    app.register_blueprint(cases_bp)

    client = app.test_client()

    resp = client.put('/api/v1/cases/SVC123/dates', json={'trial_date': '2026-03-01', 'sentencing_date': '2026-09-01'})
    assert resp.status_code == 200
    # Verify model updated
    c = Case.instances.get('SVC123')
    assert c.trial_date == '2026-03-01'
    assert c.sentencing_date == '2026-09-01'
