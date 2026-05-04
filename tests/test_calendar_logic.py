from database import DatabaseManager
from datetime import datetime

def run_test():
    db = DatabaseManager()
    case_id = 'CALENDAR-TEST-001'

    # Cleanup previous runs
    if db.conn:
        db.conn.execute('DELETE FROM court_dates WHERE case_number = ?', (case_id,))
        db.conn.execute('DELETE FROM reports WHERE case_number = ?', (case_id,))
        db.conn.commit()

    case_data = {'case_number': case_id, 'suspect': 'Test', 'investigator': 'Test', 'agency': 'Test', 'date_created': datetime.now().isoformat()}
    print('Saving report...')
    db.save_report(case_data, '<h1>Test</h1>', [], trial_date='2024-12-25', sentencing_date='2025-01-15')

    print('Adding court dates...')
    db.add_court_date(case_id, 'hearing', '2024-12-20', 'Test hearing', '10:00', 'Courtroom 1')
    db.add_court_date(case_id, 'deposition', '2024-12-22', 'Test deposition', '14:00', 'Law Office')

    print('\nLoaded court dates:')
    for d in db.load_court_dates(case_id):
        print(d)

    print('\nCases with details for test case:')
    cases = db.get_cases_with_details()
    for c in cases:
        if c['id'] == case_id:
            print(c)

    print('\nComputed event map same as calendar build:')
    event_map = {}
    for case in cases:
        if case['id'] != case_id:
            continue
        case_data = db.load_report_with_dates(case['id'])
        if case_data and len(case_data) >= 6:
            creation_date = case_data[5].split('T')[0] if case_data[5] else None
            if creation_date:
                event_map.setdefault(creation_date, set()).add('case_created')
        if case.get('trial_date'):
            event_map.setdefault(case.get('trial_date'), set()).add('trial')
        if case.get('sentencing_date'):
            event_map.setdefault(case.get('sentencing_date'), set()).add('sentencing')
        for cd in db.load_court_dates(case['id']):
            event_map.setdefault(cd.get('court_date'), set()).add(cd.get('date_type'))
        for leg in case.get('legal_details', []):
            if leg.get('due_date'):
                event_map.setdefault(leg.get('due_date'), set()).add('legal_due')

    print(event_map)

    # Cleanup
    if db.conn:
        db.conn.execute('DELETE FROM court_dates WHERE case_number = ?', (case_id,))
        db.conn.execute('DELETE FROM reports WHERE case_number = ?', (case_id,))
        db.conn.commit()
    print('\nDone')

if __name__ == '__main__':
    run_test()
