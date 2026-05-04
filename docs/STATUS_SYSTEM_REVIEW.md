# Status Update System Review

## Overview
The forensic case management system tracks three interconnected status types across the Cases tab:
1. **Case Status** - Overall case workflow state
2. **Evidence Status** - Imaging and processing state of evidence items
3. **Legal Status** - Status of legal processes

---

## 1. CASE STATUS

### Definition
The overall state of the forensic report and case workflow.

### Status Values
Located in: [models.py](models.py#L11)
```
Default: 'draft'
Field: Case.status (String, 50 chars)
```

**Possible States:**
- **draft** - Case created, being worked on
- **submitted** - Report submitted for peer review/approval
- **approved** - Peer reviewer approved the case
- **rejected** - Peer reviewer rejected (with comments)
- **completed** - Case finalized and closed

### State Transitions
1. `draft` → `submitted` - User clicks "Submit for Approval"
2. `submitted` → `approved` - Examiner approves the case
3. `submitted` → `rejected` - Examiner rejects with comments
4. `rejected` → `draft` - Return to editing
5. `approved` → `completed` - User finalizes the case

### Status Update Mechanism

**In [case_tab.py](case_tab.py#L800-L815):**
```python
def update_dashboard_metrics(self):
    # Case status is retrieved from database
    cursor = self.db.conn.execute('SELECT status FROM reports WHERE case_number = ?')
    status = row['status'].capitalize() if row else 'Draft'
    self.case_status_label.setText(f"Case Status: {status}")
```

**Update Points:**
- [case_tab.py#L877](case_tab.py#L877) - `submit_for_approval()` - Updates status to 'submitted'
- [case_tab.py#L888](case_tab.py#L888) - `approve_case()` - Updates status to 'approved'
- [case_tab.py#L899](case_tab.py#L899) - `reject_case()` - Updates status to 'rejected'
- [case_tab.py#L910](case_tab.py#L910) - `close_case()` - Updates status to 'completed'

**Display Location:** 
- [main.py](main.py#L1019-L1023) - Dashboard shows case status in row
- [case_tab.py](case_tab.py#L68) - Case tab shows "Case Status: {status}" label

---

## 2. EVIDENCE STATUS

### Definition
The imaging/processing state of individual evidence items within a case.

### Database Structure
Located in: [models.py](models.py#L24-L35)
```python
class EvidenceItem(db.Model):
    imaging_status = db.Column(db.String(50), default='not_imaged')
    imaged_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
```

### Status Values

**Primary Status:** `imaging_status` field
- **not_imaged** - Evidence received, not yet imaged/analyzed
- **imaged** - Evidence has been imaged
- **analyzed** - Evidence analysis completed
- **other** - Custom/other status

### Evidence Completion Calculation
Located in: [main.py](main.py#L955-L967)

**Dashboard calculates:**
```python
total_evidence = len(case['evidence_details'])
completed_evidence = sum(1 for ev in case['evidence_details'] 
                         if ev.get('imaging_status') == 'imaged')
pending_count = total_evidence - completed_evidence
completion_pct = int((completed_evidence / total_evidence * 100)) 
                 if total_evidence > 0 else 0
```

**Color-Coded Summary Badge:**
- **Green (✓)** - 100% complete - All evidence imaged
- **Yellow (⚠)** - 1-99% complete - Some pending (<=2 items)
- **Red (✗)** - Less than ideal - 3+ items pending

**Badge Display:** [main.py](main.py#L967-L976)
```python
if completion_pct == 100:
    summary_color = 'green'
    summary_text = f"✓ {completion_pct}% Complete"
elif pending_count <= 2:
    summary_color = 'yellow'
    summary_text = f"⚠ {completion_pct}% ({pending_count} pending)"
else:
    summary_color = 'red'
    summary_text = f"✗ {completion_pct}% ({pending_count} pending)"
```

### Status Update Mechanism

**Edit Methods:**
- Inline editing in table [case_tab.py](case_tab.py#L1202-L1237) - Direct cell changes
- Dialog update [case_tab.py](case_tab.py#L1309-L1372) - Full evidence item dialog

**Status Update Points:**
- [case_tab.py#L1220-L1237](case_tab.py#L1220-L1237) - `on_evidence_cell_changed()` - Inline edit
- [case_tab.py#L1358-L1372](case_tab.py#L1358-L1372) - `update_evidence_item()` - Dialog update
- Refresh triggers [case_tab.py#L1231-L1235](case_tab.py#L1231-L1235):
  - `update_dashboard_metrics()`
  - `parent_window.refresh_dashboard()` 
  - Audit logging

**Display Locations:**
- [main.py](main.py#L950-L985) - Dashboard evidence column with color badge
- [main.py](main.py#L2350-2362) - Evidence status chart (Imaged vs Not Imaged)
- [case_tab.py](case_tab.py#L71) - Evidence metrics label "Evidence: X items (Y imaged, Z analyzed)"
- [case_tab.py](case_tab.py#L542-575) - Evidence table with status column

---

## 3. LEGAL STATUS

### Definition
The workflow state of legal processes (warrants, subpoenas, etc.) associated with a case.

### Database Structure
Located in: [models.py](models.py#L39-L53)
```python
class LegalProcess(db.Model):
    status = db.Column(db.String(50), default='pending')
    submission_date = db.Column(db.DateTime)
    due_date = db.DateTime)
    expiration_date = db.Column(db.DateTime)
    received_date = db.Column(db.DateTime)
    analysis_start_date = db.Column(db.DateTime)
    completed_date = db.Column(db.DateTime)
```

### Status Values

**Primary Status:** `status` field
- **pending** - Legal process initiated, awaiting response
- **in_progress** - Process underway (response received, analyzing)
- **completed** - Process finished, all results received
- **no_longer_needed** - Process canceled or superseded
- **cancelled** - Process terminated

**Process-Specific Fields by Type:**

| Type | Key Fields | Status Workflow |
|------|-----------|-----------------|
| **Warrant** | submission_date, due_date, received_date, analysis_start_date, completed_date | pending → in_progress → completed |
| **Subpoena** | submission_date, due_date, received_date, analysis_start_date, completed_date | pending → in_progress → completed |
| **Other** | submission_date, received_date, analysis_start_date, completed_date | pending → in_progress → completed |

### Legal Summary Calculation
Located in: [main.py](main.py#L1000-1018)

**Dashboard calculates:**
```python
pending_legal = sum(1 for l in case['legal_details'] 
                    if l.get('status') not in ['completed', 'no_longer_needed'])

# Check for overdue items
overdue_legal = 0
for l in case['legal_details']:
    due = l.get('due_date')
    if due:
        due_dt = datetime.fromisoformat(due)
        if due_dt.date() < datetime.now(timezone.utc).date() 
           and l.get('status') not in ['completed', 'no_longer_needed']:
            overdue_legal += 1
```

**Color-Coded Status:**
- **Red** - One or more items overdue
- **Yellow** - Items pending (but not overdue)
- **Green** - All items completed

**Badge Display:** [main.py](main.py#L1007-1019)
```python
if overdue_legal > 0:
    legal_color = 'red'
elif pending_legal > 0:
    legal_color = 'yellow'
else:
    legal_color = 'green'
legal_summary = (f"Pending {pending_legal}", legal_color, 
                f"{pending_legal} legal processes pending; {overdue_legal} overdue")
```

### Status Update Mechanism

**Edit Methods:**
- Dialog update [case_tab.py](case_tab.py#L1489-L1587) - Comprehensive legal process dialog

**Status Update Points:**
- [case_tab.py#L1567-1587](case_tab.py#L1567-1587) - `update_legal_process()` - Update legal item
  - Captures: submission_date, due_date, expiration_date, received_date, analysis_start_date, completed_date, status, notes, ndr (non-disclosure request)
  - Triggers refresh: `update_dashboard_metrics()`, `parent_window.refresh_dashboard()`

**Display Locations:**
- [main.py](main.py#L1000-1019) - Dashboard legal column with color badge (Investigator view only)
- [case_tab.py](case_tab.py#L72) - Legal metrics label "Legal: X processes (Y completed)"
- [case_tab.py](case_tab.py#L712-781) - Legal table with status column
- [case_tab.py](case_tab.py#L279-340) - Legal tab (hidden in Examiner view)

---

## 4. STATUS UPDATE FLOW

### Complete Update Sequence

```
User Action (e.g., update evidence status)
    ↓
[case_tab.py] on_evidence_cell_changed() or update_evidence_item()
    ↓
[database.py] update_evidence_field() or update_evidence_item()
    ↓
Database UPDATE query executes
    ↓
[case_tab.py] update_dashboard_metrics() 
    - Recalculates evidence completion %
    - Updates evidence metrics label
    ↓
[main.py] refresh_dashboard()
    - Refreshes main dashboard table
    - Regenerates charts
    - Updates case status badges
    ↓
[audit_log.py] Log evidence/legal update
```

### Audit Logging Points
- [case_tab.py#L1235](case_tab.py#L1235) - `audit.log_evidence_updated()`
- [case_tab.py#L1233](case_tab.py#L1233) - Logs: evidence_id, field, new_value
- [case_tab.py#L1585](case_tab.py#L1585) - `audit.log_legal_process_updated()`
- [case_tab.py#L1583](case_tab.py#L1583) - Logs: legal_id, process_type, provider

---

## 5. STATUS COLORS CONFIGURATION

### Configuration File
Located in: [config.json](config.json)

```json
{
    "status_colors": {
        "evidence_not_imaged": {
            "bg": "#ffff00",
            "text": "#aa0000",
            "bold": true
        },
        "evidence_imaged": {
            "bg": "#28a745",
            "text": "#000000",
            "bold": false
        },
        "evidence_analyzed": {
            "bg": "#17a2b8",
            "text": "#000000",
            "bold": false
        },
        "legal_pending": {
            "bg": "#ffc107",
            "text": "#000000",
            "bold": false
        },
        "legal_completed": {
            "bg": "#28a745",
            "text": "#000000",
            "bold": false
        }
    }
}
```

### Customization
- Dialog: [main.py#L2438](main.py#L2438) - `show_status_color_dialog()`
- Persisted in config.json via [main.py#L2440-2442](main.py#L2440-2442)
- Applied via [StatusColorDialog](status_color_dialog.py)

---

## 6. ISSUES & RECOMMENDATIONS

### Current Implementation ✅
- **Automatic recalculation** - Completion percentages calculated on demand
- **Audit trail** - All updates logged with timestamps
- **Color coding** - Visual status indicators for quick identification
- **Overdue detection** - Legal items checked against due dates
- **View filtering** - Legal tab hidden in Examiner view

### Recommendations for Enhancement

1. **Status Validation**
   - Add state machine validation (prevent invalid transitions)
   - Example: Can't go from 'completed' directly to 'pending'

2. **Performance**
   - Cache legal status summary in case record (recalculated periodically)
   - Current: Recalculated on every dashboard refresh

3. **UI/UX**
   - Add status change history/timeline view
   - Show reason for status changes (e.g., rejection comments)
   - Add bulk status updates for multiple items

4. **Notifications**
   - Alert when legal items become overdue
   - Notify when all evidence items imaged
   - Remind when case pending approval

5. **Reporting**
   - Add "Status Report" showing case health metrics
   - Timeline showing when evidence reaches each status
   - Legal process progress tracking

---

## 7. VERIFICATION CHECKLIST

### Testing Status Updates

- [ ] **Case Status Changes**
  - [ ] Submit case → status changes to 'submitted'
  - [ ] Approve case → status changes to 'approved'
  - [ ] Reject case → status changes to 'rejected' + comments shown
  - [ ] Close case → status changes to 'completed'

- [ ] **Evidence Status Updates**
  - [ ] Add evidence item → appears in table
  - [ ] Change imaging_status → completion % recalculates
  - [ ] 100% complete evidence → green badge shows
  - [ ] Partial evidence → yellow/red badge shows appropriately
  - [ ] Inline edit → updates without dialog

- [ ] **Legal Status Updates**
  - [ ] Add legal process → appears in table
  - [ ] Update status to 'completed' → completion count updates
  - [ ] Set past due_date → red color appears
  - [ ] All completed → green badge shows
  - [ ] Dialog update → all fields save correctly

- [ ] **Dashboard Refresh**
  - [ ] Case status reflects in main dashboard
  - [ ] Evidence metrics update immediately
  - [ ] Legal metrics update immediately
  - [ ] Charts regenerate with new data

- [ ] **Audit Logging**
  - [ ] All updates logged to audit_log table
  - [ ] Timestamps recorded correctly
  - [ ] User identity captured

---

## File References

**Core Files:**
- [models.py](models.py) - Database models
- [database.py](database.py) - Update methods
- [case_tab.py](case_tab.py) - Case UI and update handlers
- [main.py](main.py) - Dashboard display
- [config.json](config.json) - Status colors

**Related Files:**
- [cases_bp.py](cases_bp.py) - Server API endpoints
- [audit_log.py](audit_log.py) - Audit logging
- [status_color_dialog.py](status_color_dialog.py) - Color customization

