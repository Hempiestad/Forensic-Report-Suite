import sys
import os
sys.path.append('.')
from database import DatabaseManager
from datetime import datetime

# Test database operations
db = DatabaseManager()

# Test 1: Create a test case with trial date
case_data = {
    'case_number': 'TEST-001',
    'suspect': 'Test Suspect',
    'investigator': 'Test Investigator',
    'agency': 'Test Agency',
    'date_created': datetime.now().isoformat()
}

print('Test 1: Creating case with trial date')
success = db.save_report(case_data, '<h1>Test Report</h1>', [], trial_date='2024-12-25', sentencing_date='2025-01-15')
print(f'Case creation success: {success}')

# Test 2: Add court dates
print('\nTest 2: Adding court dates')
court_date_success = db.add_court_date('TEST-001', 'hearing', '2024-12-20', 'Test hearing', '10:00', 'Courtroom 1')
print(f'Court date addition success: {court_date_success}')

deposition_success = db.add_court_date('TEST-001', 'deposition', '2024-12-22', 'Test deposition', '14:00', 'Law Office')
print(f'Deposition date addition success: {deposition_success}')

# Test 3: Load court dates
print('\nTest 3: Loading court dates')
court_dates = db.load_court_dates('TEST-001')
print(f'Loaded court dates: {len(court_dates)} dates')
for date in court_dates:
    print(f'  - {date["date_type"]}: {date["court_date"]} at {date.get("event_time", "N/A")}')

# Test 4: Check case with dates
print('\nTest 4: Loading case with dates')
html, appendices, pdf_hash, trial_date, sentencing_date, date_created = db.load_report_with_dates('TEST-001')
print(f'Case trial date: {trial_date}')
print(f'Case sentencing date: {sentencing_date}')

# Test 5: Get cases with details (simulates calendar loading)
print('\nTest 5: Getting cases with details')
cases = db.get_cases_with_details()
test_case = next((c for c in cases if c['id'] == 'TEST-001'), None)
if test_case:
    print(f'Found test case: {test_case["id"]}')
    print(f'Trial date: {test_case.get("trial_date")}')
    print(f'Sentencing date: {test_case.get("sentencing_date")}')
else:
    print('Test case not found')

# Cleanup
if db.conn:
    db.conn.execute('DELETE FROM reports WHERE case_number = ?', ('TEST-001',))
    db.conn.execute('DELETE FROM court_dates WHERE case_number = ?', ('TEST-001',))
    db.conn.commit()

print('\nCleanup completed')
