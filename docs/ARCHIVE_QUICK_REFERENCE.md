# Archive System - Quick Reference Guide

> Consolidation note (May 2026): This guide is retained as a fast reference.
> Canonical end-user archive workflow documentation: [ARCHIVE_CASES_USER_GUIDE.md](ARCHIVE_CASES_USER_GUIDE.md).
> For system/implementation details, use [ARCHIVE_SYSTEM_DOCUMENTATION.md](ARCHIVE_SYSTEM_DOCUMENTATION.md).

## 🚀 Quick Start

### Archive a Case (2 clicks)
1. Right-click closed case in dashboard
2. Select "📦 Archive Case..." 
3. Confirm with reason (optional)

### View Archived Cases (1 click)
- **Menu**: View > Archived Cases
- **Shortcut**: Ctrl+Shift+A

### Restore a Case (1 click)
1. Open View > Archived Cases
2. Select case
3. Click "↩️ Restore Case"

---

## 📋 Archive Dialog Reference

### Opening Archive Dialog
```
Dashboard > Right-click closed case > "📦 Archive Case..."
```

**Default Behavior**:
- Shows case number and suspect name
- Pre-fills 30 days from today as archive date
- Allows custom date selection
- Optional reason text field
- Confirmation required before archiving

**Key Points**:
- ⚠️ Only "Closed" status cases can be archived
- ✅ Archive date can be set to any future date
- ✅ Reason is optional but recommended
- ✅ Case removed from dashboard immediately after archiving

---

## 📋 Archived Cases Dialog Reference

### Opening Archived Cases View
```
View > Archived Cases  (or Ctrl+Shift+A)
```

### Table Columns
| Column | Purpose | Editable |
|--------|---------|----------|
| Case Number | Case ID | No |
| Suspect | Suspect name | No |
| Assigned To | Investigator name | No |
| Agency | Associated agency | No |
| Archived Date | When archived | No |
| Archived By | Who archived | No |
| Reason | Archive reason (truncated) | No |

### Search Features
```
Search: [_______________]  (Case # or Suspect name)
Year:   [Dropdown ▼]      (Filter by year)
         🔄 Refresh
```

**Search Tips**:
- Partial matches work ("Smith" finds "Smithson")
- Case-insensitive
- Works across case numbers and suspect names
- Reason text not searchable in main search

**Year Filter**:
- Dropdown shows current year and 10 years back
- "All" option to show all archived cases
- Combines with search filter
- Real-time updates

### Case Details Panel
When you select a case:
```
Case Number:   [Value]
Suspect:       [Value]
Archived Date: [Formatted]
Archived By:   [Username]
Reason:        [Full text box]
```

### Action Buttons
| Button | Shortcut | Result |
|--------|----------|--------|
| 📄 View Details | Double-click | Opens case in viewer |
| ↩️ Restore Case | - | Reactivates to dashboard |
| 💾 Export List | - | CSV download |
| Close | Esc | Closes dialog |

---

## 🎯 Common Tasks

### Task: Find a case I archived last month
```
1. Open View > Archived Cases (Ctrl+Shift+A)
2. In Year dropdown: Select last month's year
3. In Search box: Type case number or suspect name
4. Click 🔄 Refresh
5. Look for case in results
```

### Task: Restore an archived case to dashboard
```
1. Open View > Archived Cases (Ctrl+Shift+A)
2. Search/filter to find case
3. Click on case to select
4. Click ↩️ Restore Case
5. Confirm in dialog
6. Case now appears in dashboard
```

### Task: Report on archived cases
```
1. Open View > Archived Cases (Ctrl+Shift+A)
2. Apply filters as needed
3. Click 💾 Export List
4. Choose location and filename
5. CSV file ready for Excel/reporting
```

### Task: Archive multiple cases
```
1. Right-click first closed case
2. Select "📦 Archive Case..."
3. Set date/reason and confirm
4. Repeat for each case
5. (Bulk archive planned for future)
```

---

## ⚙️ Settings & Preferences

### Archive Date Options
- **Default**: 30 days from today (recommended)
- **Custom**: Any future date you choose
- **Format**: YYYY-MM-DD displayed

### Archive Reason Options
- **Optional**: Can leave blank
- **Recommended**: Add context for future reference
- **Examples**:
  - "Case completed and filed"
  - "Prosecution declined"
  - "Transferred to other district"
  - "Statute of limitations expired"

### Dashboard Behavior
- Archived cases **automatically hidden**
- No configuration needed
- Use View > Archived Cases to see them
- Restoring immediately shows in dashboard

---

## 🐛 Troubleshooting

### "Can't archive this case"
**Problem**: Archive button disabled or menu grayed out
**Solution**: Case must be in "Closed" status. Change status first, then archive.

### "Case still shows in dashboard"
**Problem**: Archived case still visible
**Solution**: Click refresh or close/reopen dashboard. May need to restart app.

### "Can't find my archived case"
**Problem**: Expected case not in archived list
**Solution**: 
- Check year filter - wrong year selected?
- Try "All" in year dropdown
- Try searching by case number
- Case may not have been archived

### "Export CSV is empty"
**Problem**: CSV file created but no data
**Solution**:
- Make sure cases are showing in dialog first
- Check filters are correct
- Try removing filters and exporting all

### "Restore didn't work"
**Problem**: Case still archived after clicking restore
**Solution**:
- Confirm in dialog - must click Yes
- Check app didn't crash (see error log)
- Restart app and try again
- Check case status in dashboard

---

## 📊 Archive System Stats

### What Gets Archived
- ✅ Case information (case #, suspect, assigned to)
- ✅ Archive metadata (date, reason, who archived)
- ✅ All evidence items
- ✅ All legal processes
- ✅ All leads
- ✅ All notes
- ✅ All court dates

### What Doesn't Change
- ❌ Case data doesn't change
- ❌ Evidence counts same
- ❌ User permissions same
- ❌ Audit logs unchanged

### Restore Guarantees
- ✅ All data preserved
- ✅ No information lost
- ✅ Case fully functional
- ✅ Can archive again if needed

---

## 🔐 Security & Access

### Who Can Archive?
- Users with case access
- (Same permissions as case editing)

### Who Can Restore?
- Users with case access
- (Same permissions as editing)

### Audit Trail
- Archive logged with username and timestamp
- Reason for archiving recorded
- Restore also logged
- All operations in audit log

### Data Privacy
- Encrypted case data maintained
- Archived cases not publicly visible
- Archive status controlled by permissions
- Restore restricted to authorized users

---

## 📈 Performance Notes

### Archive Operations Speed
- Archive a case: < 1 second
- Open archived cases view: 1-2 seconds
- Search archived cases: Real-time
- Restore a case: < 1 second
- Export 100 cases to CSV: < 5 seconds

### Dashboard Performance
- Filtering out archived cases: Automatic
- No noticeable slowdown
- Works with 100+ archived cases
- Caching optimizes repeated queries

---

## 🆘 Getting Help

### In the Application
- Tooltips on hover
- Status bar shows case counts
- Confirmation dialogs before actions
- Error messages explain problems

### Documentation
- ARCHIVE_SYSTEM_DOCUMENTATION.md - Complete guide
- This file - Quick reference
- Code comments - Technical details

### Reporting Issues
- Menu > Tools > Report Bug
- Include steps to reproduce
- Mention your OS and case count
- Check logs for error details

---

## 💡 Tips & Tricks

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+A | Open archived cases |
| Esc | Close archived cases dialog |
| Ctrl+F | Search (in archived cases view) |

### Batch Operations
Currently: Archive one at a time (right-click > archive)
Future: Bulk archive/restore coming in v1.1

### Export Uses
- Reporting archived cases to management
- Data backup before purge
- Historical analysis
- Record keeping

### Best Practices
✅ **Do**:
- Archive when case is truly closed
- Add reason for archiving
- Regularly review archived cases
- Export historical data periodically

❌ **Don't**:
- Archive while case still open
- Restore unless truly needed
- Delete archives (no permanent delete yet)
- Archive recent cases (wait 30 days)

---

## 📞 Version & Support

**Archive System Version**: 1.0 (Alpha)
**Release Date**: [Current Date]
**Status**: Ready for Alpha Testing

**Support**: 
- See Troubleshooting above
- Check ARCHIVE_SYSTEM_DOCUMENTATION.md for detailed info
- Contact: [Support Channel]

---

**Last Updated**: [Current Date]
**Documentation Version**: 1.0

