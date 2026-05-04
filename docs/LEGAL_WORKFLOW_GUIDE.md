# Legal Process Approval Workflow — FuDog Labs Forensic Report Suite

## Overview

Legal processes (warrants, subpoenas, preservation letters) now support a **5-stage approval workflow** with automatic **SLA tracking** and **calendar integration**.

## Workflow Stages

```text
┌─────────────────┐
│ 1. Created      │  Investigator drafts the request
└────────┬────────┘
         │
         v
┌─────────────────┐
│ 2. Investigator │  mark_investigator_approved()
│    Approved     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ 3. State        │  mark_state_attorney_approved()
│    Attorney     │
│    Approved     │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ 4. Judicial     │  mark_judicial_approval()
│    Approval     │  (Judge signs)
└────────┬────────┘
         │
         v
┌─────────────────┐
│ 5. Sent to      │  mark_sent_to_provider()
│    Provider     │  ⏱️ SLA CLOCK STARTS HERE
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Provider        │  mark_provider_acknowledged()
│ Acknowledged    │
└────────┬────────┘
         │
         v
┌─────────────────┐
│ Response        │  update_legal_process_status(id, 'completed', ...)
│ Received        │  ⏱️ SLA CLOCK STOPS, breach check runs
└─────────────────┘
```

## Python Usage Examples

### 1. Create a Legal Process with Expected SLA

```python
from database import DatabaseManager

db = DatabaseManager()

# Create the legal process
db.add_legal_process(
    case_number='C001',
    process_type='search_warrant',
    provider='Google',
    expected_response_days=45,  # Google standard SLA
    notes='Gmail account data'
)

# Get the process ID (just created)
cursor = db.conn.execute(
    "SELECT id FROM legal_processes WHERE case_number = 'C001' ORDER BY id DESC LIMIT 1"
)
process_id = cursor.fetchone()['id']
```

### 2. Mark Investigator Approval

```python
from legal_workflow_helpers import mark_investigator_approved

success = mark_investigator_approved(
    db_manager=db,
    process_id=process_id,
    approved_date='2026-02-10',
    investigator_name='Det. John Smith'
)

# Creates:
# - Notification: "Search Warrant approved by Det. John Smith"
# - Calendar event on 2026-02-10 (green dot)
```

### 3. Mark State Attorney Approval

```python
from legal_workflow_helpers import mark_state_attorney_approved

success = mark_state_attorney_approved(
    db_manager=db,
    process_id=process_id,
    approved_date='2026-02-12',
    attorney_name='ADA Jane Doe'
)

# Creates:
# - Notification: "Search Warrant approved by State's Attorney Jane Doe"
# - Calendar event on 2026-02-12 (cyan dot)
```

### 4. Mark Judicial Approval

```python
from legal_workflow_helpers import mark_judicial_approval

success = mark_judicial_approval(
    db_manager=db,
    process_id=process_id,
    approval_date='2026-02-13',
    court_name='Circuit Court of Cook County',
    judge_name='Hon. Michael Brown'
)

# Creates:
# - Notification: "Search Warrant approved by Judge Michael Brown (Circuit Court)"
# - Calendar event on 2026-02-13 (purple dot - important milestone)
```

### 5. Send to Provider (⏱️ SLA Clock Starts)

```python
from legal_workflow_helpers import mark_sent_to_provider

success = mark_sent_to_provider(
    db_manager=db,
    process_id=process_id,
    sent_date='2026-02-14',
    transmission_method='Email via Law Enforcement Portal',
    expected_response_days=45  # Can override if different from default
)

# Creates:
# - Notification: "Search Warrant sent to Google via Email. Due: 2026-03-31"
# - Calendar event on 2026-02-14 (orange dot - sent)
# - Calendar event on 2026-03-31 (yellow dot - SLA due)
# - Sets sla_due_date = 2026-03-31 (45 days from sent date)
```

### 6. Provider Acknowledges Receipt (Optional)

```python
from legal_workflow_helpers import mark_provider_acknowledged

success = mark_provider_acknowledged(
    db_manager=db,
    process_id=process_id,
    acknowledged_date='2026-02-15'
)

# Creates:
# - Notification: "Google acknowledged receipt of Search Warrant"
# - Calendar event on 2026-02-15 (blue dot)
```

### 7. Response Received (⏱️ SLA Clock Stops)

```python
from legal_workflow_helpers import calculate_legal_sla_breach

# First, update legal process status
db.update_legal_process_status(
    process_id=process_id,
    status='completed',
    date_field='received_date',
    date_value='2026-04-05'  # 5 days late!
)

# Then calculate SLA breach
calculate_legal_sla_breach(
    db_manager=db,
    process_id=process_id,
    received_date='2026-04-05'
)

# If late, creates:
# - Notification: "⚠️ SLA BREACH: Google missed SLA by 5 days"
# - Calendar event on 2026-04-05 (red dot - breach)
# - Sets sla_breach = 1, days_late = 5
```

## Calendar Integration

All workflow milestones automatically appear on the calendar with color-coded dots:

- 🟢 **Green** - Investigator approval
- 🔵 **Cyan** - State Attorney approval
- 🟣 **Purple** - Judicial approval
- 🟠 **Orange** - Sent to provider
- 🔵 **Blue** - Provider acknowledged
- 🟡 **Yellow** - SLA due date
- 🔴 **Red** - SLA breach

## Query Examples

### Check SLA Status for All Active Processes

```python
cursor = db.conn.execute('''
    SELECT id, case_number, process_type, provider,
           sent_to_provider_date, sla_due_date, sla_breach, days_late
    FROM legal_processes
    WHERE status IN ('pending', 'in_progress')
      AND sent_to_provider_date IS NOT NULL
      AND received_date IS NULL
    ORDER BY sla_due_date ASC
''')

for row in cursor.fetchall():
    if row['sla_breach']:
        print(f"⚠️ {row['provider']} is {row['days_late']} days late")
    else:
        print(f"✓ {row['provider']} - Due: {row['sla_due_date']}")
```

### Find Pending Approvals

```python
cursor = db.conn.execute('''
    SELECT id, case_number, process_type,
           investigator_approved_date,
           state_attorney_approved_date,
           judicial_approval_date,
           sent_to_provider_date
    FROM legal_processes
    WHERE status = 'pending'
      AND sent_to_provider_date IS NULL
''')

for row in cursor.fetchall():
    if not row['investigator_approved_date']:
        print(f"Waiting: Investigator approval for {row['case_number']}")
    elif not row['state_attorney_approved_date']:
        print(f"Waiting: State Attorney approval for {row['case_number']}")
    elif not row['judicial_approval_date']:
        print(f"Waiting: Judicial approval for {row['case_number']}")
    else:
        print(f"Approved, not yet sent: {row['case_number']}")
```

## Benefits

✅ **Accurate SLA tracking** - Clock starts when sent to provider, not when drafted  
✅ **Visibility** - See where requests are stuck (attorney? judge?)  
✅ **Compliance** - Document full chain of custody and approval  
✅ **Automated alerts** - Notifications at each stage + SLA breach detection  
✅ **Calendar integration** - All milestones visible at a glance  

## Notes

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Dashboard, menus, and case management
- [Legal Workflow UI Guide](LEGAL_WORKFLOW_UI_GUIDE.md) — UI dialog reference for each workflow stage
- [Server User Guide](SERVER_USER_GUIDE.md) — Server API and legal endpoint documentation

- **Automatic notifications** are created at each stage if `notification_manager` is attached
- **Calendar events** are created automatically for all milestones
- **SLA breach detection** runs automatically when `calculate_legal_sla_breach()` is called after receiving response

## See Also

- [legal_workflow_helpers.py](legal_workflow_helpers.py) - Full implementation
- [Improvement roadmap.txt](Improvement roadmap.txt) - C# implementation plan
- [notification_manager.py](notification_manager.py) - Notification system
