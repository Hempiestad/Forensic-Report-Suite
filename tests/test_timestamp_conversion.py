import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5.QtWidgets import QApplication

from notes_tab import NotesTab

class DummyDB:
    pass
class DummyAudit:
    def log(self, *a, **k): pass

app = QApplication.instance() or QApplication([])
nt = NotesTab({'case_number':'TEST'}, DummyDB(), DummyAudit())

samples = [
    '2026-01-29T15:30:00Z',
    '2026-03-14 02:30:00 PST',
    'Jan 15, 2025 14:00 EST',
    '2024-11-03 01:30:00',
    '2024-12-25'
]

failed = []
for s in samples:
    dt, tz, used = nt._parse_timestamp(s)
    print(s, '->', dt, 'tz:', tz, 'used:', used)
    if dt is None:
        failed.append(s)

if failed:
    print('Failed to parse:', failed)
    raise SystemExit(1)
else:
    print('All parsed OK')
