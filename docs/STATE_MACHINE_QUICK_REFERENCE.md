# State Machine and Caching - Quick Reference Guide

## For Developers

### Using State Machine Validation

#### Handling Status Transitions

```python
from database import DatabaseManager
from status_validator import StatusTransitionError

db = DatabaseManager()

# Case status transitions
try:
    db.submit_case('12345')  # draft → submitted
    db.approve_case('12345')  # submitted → approved
    db.close_case('12345')   # approved → closed
except StatusTransitionError as e:
    print(f"Invalid transition: {e}")
    # Show error message to user
```

#### Checking Valid Transitions Before Attempting

```python
from status_validator import StatusValidator

current_status = 'submitted'
target_status = 'approved'

# Check if transition is valid
if StatusValidator.validate_case_status_transition(current_status, target_status):
    db.approve_case(case_number)
else:
    print(f"Cannot change from {current_status} to {target_status}")
```

#### Getting Allowed Next Statuses

```python
from status_validator import StatusValidator

current_status = 'submitted'

# Get all valid next statuses
valid_next = StatusValidator.get_allowed_case_statuses(current_status)
print(f"From {current_status}, can transition to: {valid_next}")
# Output: ['approved', 'revisions_needed', 'closed']

# Use in UI dropdown
for status in valid_next:
    dropdown.add_item(status)
```

### Using Legal Status Cache

#### Displaying Cached Summaries in Dashboard

```python
from database import DatabaseManager

db = DatabaseManager()

for case in db.load_cases():
    case_number = case['case_number']
    
    # Get cached legal status (fast)
    cache = db.get_legal_status_from_cache(case_number)
    
    pending_count = cache['pending_count']
    overdue_count = cache['overdue_count']
    last_updated = cache['last_updated']
    
    # Display in UI
    if overdue_count > 0:
        print(f"⚠️ {case_number}: {overdue_count} overdue, {pending_count} pending")
    elif pending_count > 0:
        print(f"📋 {case_number}: {pending_count} pending")
    else:
        print(f"✅ {case_number}: All legal processes complete")
```

#### Manually Refreshing Cache

```python
# After bulk legal process changes
case_number = '12345'

# Make multiple changes
for i in range(10):
    db.add_legal_process(case_number, 'search_warrant', 'Court A')

# Cache was already updated automatically by add_legal_process()
# But you can manually refresh if needed
db.update_legal_status_cache(case_number)

# Get updated cache
cache = db.get_legal_status_from_cache(case_number)
print(f"Cache updated at: {cache['last_updated']}")
```

## For UI Developers

### Displaying Status Transitions in Forms

#### Creating Dynamic Status Dropdown

```python
from PyQt5.QtWidgets import QComboBox
from status_validator import StatusValidator

class CaseStatusWidget:
    def __init__(self, current_status):
        self.status_combo = QComboBox()
        
        # Get valid next statuses
        allowed = StatusValidator.get_allowed_case_statuses(current_status)
        
        # Populate dropdown with only valid options
        for status in allowed:
            display_text = status.replace('_', ' ').title()
            self.status_combo.addItem(display_text, status)
    
    def on_status_change(self):
        try:
            new_status = self.status_combo.currentData()
            db.submit_case(case_number)  # Or appropriate method
        except StatusTransitionError as e:
            QMessageBox.warning(self, "Invalid Status Change", str(e))
```

#### Showing Status Flow Diagram

```python
# Case Status Flow
CASE_STATUS_FLOW = """
Draft → Submitted → Approved → Closed
              ↓        ↓
         Revisions   Closed
         Needed
              ↓
          Closed
"""

# Evidence Status Flow
EVIDENCE_STATUS_FLOW = """
Pending → In Progress → Completed → Verified
   ↓           ↓            ↓
Failed       Failed       Failed
   ↓
Pending (retry)
"""

# Legal Status Flow
LEGAL_STATUS_FLOW = """
Pending → Submitted → In Review → Completed
                ↓          ↓
         No Longer Needed
                ↓
            Cancelled
"""
```

### Dashboard Legal Status Display

#### Color-Coded Status Badges

```python
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QColor

def create_legal_status_badge(case_number):
    cache = db.get_legal_status_from_cache(case_number)
    
    pending = cache['pending_count']
    overdue = cache['overdue_count']
    
    label = QLabel()
    
    if overdue > 0:
        # Red for overdue
        label.setText(f"⚠️ {overdue} overdue")
        label.setStyleSheet("background-color: #ff4444; color: white; padding: 5px;")
    elif pending > 0:
        # Yellow for pending
        label.setText(f"📋 {pending} pending")
        label.setStyleSheet("background-color: #ffaa00; color: white; padding: 5px;")
    else:
        # Green for complete
        label.setText("✅ Complete")
        label.setStyleSheet("background-color: #44ff44; color: black; padding: 5px;")
    
    return label
```

#### Showing Cache Freshness

```python
from datetime import datetime, timedelta

def show_cache_age(case_number):
    cache = db.get_legal_status_from_cache(case_number)
    
    if cache['last_updated']:
        updated = datetime.fromisoformat(cache['last_updated'])
        age = datetime.now() - updated
        
        if age < timedelta(minutes=5):
            return "🟢 Live"
        elif age < timedelta(hours=1):
            return f"🟡 {int(age.seconds / 60)} min ago"
        else:
            return f"🔴 {int(age.seconds / 3600)} hr ago"
    
    return "❓ Unknown"
```

## Status Reference Tables

### Case Statuses

| Status | Description | Can Transition To |
|--------|-------------|-------------------|
| draft | Initial creation | submitted, closed |
| submitted | Ready for review | approved, revisions_needed, closed |
| approved | Approved by supervisor | closed |
| revisions_needed | Needs corrections | closed |
| closed | Case finalized | (none) |

### Evidence Statuses

| Status | Description | Can Transition To |
|--------|-------------|-------------------|
| pending | Not started | in_progress, failed |
| in_progress | Currently imaging | completed, failed |
| completed | Imaging done | verified, failed |
| verified | Quality checked | (none) |
| failed | Process failed | pending (retry) |

### Legal Statuses

| Status | Description | Can Transition To |
|--------|-------------|-------------------|
| pending | Awaiting submission | submitted, cancelled |
| submitted | Submitted to court | in_review, no_longer_needed |
| in_review | Under court review | completed, no_longer_needed |
| completed | Process finished | (none) |
| no_longer_needed | Process cancelled | (none) |
| cancelled | Cancelled before submission | (none) |

## Error Messages

### Common StatusTransitionError Messages

```
Invalid case status transition from 'approved' to 'submitted'
→ Cannot undo approval. Case must remain approved or be closed.

Invalid case status transition from 'closed' to 'approved'
→ Closed cases cannot be reopened. Create new case if needed.

Invalid evidence status transition from 'verified' to 'in_progress'
→ Verified evidence is final. Cannot re-image.

Invalid legal status transition from 'completed' to 'in_review'
→ Completed legal processes are final.
```

### User-Friendly Error Handling

```python
def handle_status_error(e: StatusTransitionError):
    """Convert technical error to user-friendly message"""
    
    error_msg = str(e)
    
    if 'approved' in error_msg and 'submitted' in error_msg:
        return "Cannot undo approval. Please close the case instead."
    
    elif 'closed' in error_msg:
        return "This case is closed and cannot be modified. Please create a new case."
    
    elif 'verified' in error_msg:
        return "Verified evidence cannot be changed. Contact supervisor if correction needed."
    
    elif 'completed' in error_msg:
        return "This process is complete and cannot be modified."
    
    else:
        return f"Invalid status change: {error_msg}"
```

## Performance Tips

### For Dashboard Loading

```python
# ✅ GOOD - Use cache
cache = db.get_legal_status_from_cache(case_number)
pending_count = cache['pending_count']

# ❌ BAD - Recalculate every time
legal_items = db.load_legal_processes(case_number)
pending_count = sum(1 for item in legal_items if item['status'] not in ['completed'])
```

### For Batch Operations

```python
# Update multiple legal processes
case_number = '12345'

for process_id in [1, 2, 3, 4, 5]:
    db.update_legal_process_status(process_id, 'completed')
    # Cache is automatically updated after each change

# Final cache will be correct after all updates
```

### Cache Refresh Strategy

```python
from datetime import timedelta

def get_legal_summary(case_number):
    """Get legal summary with smart cache refresh"""
    
    cache = db.get_legal_status_from_cache(case_number)
    
    # Check cache age
    if cache['last_updated']:
        updated = datetime.fromisoformat(cache['last_updated'])
        age = datetime.now() - updated
        
        # Refresh if older than 1 hour
        if age > timedelta(hours=1):
            logger.info(f"Refreshing stale cache for {case_number}")
            db.update_legal_status_cache(case_number)
            cache = db.get_legal_status_from_cache(case_number)
    
    return cache
```

## Testing Examples

### Unit Test for Validation

```python
import pytest
from status_validator import StatusValidator, StatusTransitionError

def test_case_status_transitions():
    # Valid transitions
    assert StatusValidator.validate_case_status_transition('draft', 'submitted')
    assert StatusValidator.validate_case_status_transition('submitted', 'approved')
    assert StatusValidator.validate_case_status_transition('approved', 'closed')
    
    # Invalid transitions
    assert not StatusValidator.validate_case_status_transition('approved', 'draft')
    assert not StatusValidator.validate_case_status_transition('closed', 'submitted')

def test_database_enforces_validation():
    db = DatabaseManager()
    case_number = 'TEST-001'
    
    # Create and submit case
    db.save_case({'case_number': case_number, 'status': 'draft'})
    db.submit_case(case_number)  # draft → submitted (OK)
    
    # Try to submit again (should fail)
    with pytest.raises(StatusTransitionError):
        db.submit_case(case_number)  # submitted → submitted (FAIL)
```

### Integration Test for Cache

```python
def test_legal_cache_updates():
    db = DatabaseManager()
    case_number = 'TEST-002'
    
    # Initial state
    cache = db.get_legal_status_from_cache(case_number)
    assert cache['pending_count'] == 0
    
    # Add pending legal process
    db.add_legal_process(
        case_number=case_number,
        process_type='search_warrant',
        provider='Court A',
        due_date='2024-01-01'  # Past date = overdue
    )
    
    # Cache should be updated
    cache = db.get_legal_status_from_cache(case_number)
    assert cache['pending_count'] == 1
    assert cache['overdue_count'] == 1
    
    # Complete the process
    db.update_legal_process_status(1, 'completed')
    
    # Cache should reflect completion
    cache = db.get_legal_status_from_cache(case_number)
    assert cache['pending_count'] == 0
    assert cache['overdue_count'] == 0
```

## API Quick Reference

### StatusValidator Methods

```python
# Check if transition is valid
StatusValidator.validate_case_status_transition(from_status, to_status) -> bool
StatusValidator.validate_evidence_status_transition(from_status, to_status) -> bool
StatusValidator.validate_legal_status_transition(from_status, to_status) -> bool

# Get allowed next statuses
StatusValidator.get_allowed_case_statuses(current_status) -> List[str]
StatusValidator.get_allowed_evidence_statuses(current_status) -> List[str]
StatusValidator.get_allowed_legal_statuses(current_status) -> List[str]
```

### DatabaseManager Cache Methods

```python
# Update cache (called automatically by add/update methods)
db.update_legal_status_cache(case_number: str) -> bool

# Get cached summary (fast)
db.get_legal_status_from_cache(case_number: str) -> Dict[str, Any]
# Returns: {'pending_count': int, 'overdue_count': int, 'last_updated': str}
```

### DatabaseManager Status Methods (with validation)

```python
# Case status (validates transitions)
db.submit_case(case_number: str) -> bool  # draft → submitted
db.approve_case(case_number: str) -> bool  # submitted → approved
db.reject_case(case_number: str, comments: str) -> bool  # submitted → revisions_needed
db.close_case(case_number: str) -> bool  # any → closed

# Evidence status (validates transitions)
db.update_evidence_field(evidence_id: int, field: str, value: Any) -> bool
db.update_evidence_item(evidence_id: int, **kwargs) -> bool

# Legal status (validates transitions + updates cache)
db.update_legal_process_status(
    process_id: int,
    status: str,
    date_field: Optional[str] = None,
    date_value: Optional[str] = None
) -> bool
```

## Summary

✅ **Always use** StatusValidator to check transitions before attempting
✅ **Always catch** StatusTransitionError for user-friendly error messages
✅ **Always use** cache methods for dashboard performance
✅ **Never** bypass validation by writing to database directly
✅ **Never** recalculate legal summaries when cache is available

For more details, see [STATUS_SYSTEM_REVIEW.md](STATUS_SYSTEM_REVIEW.md)
