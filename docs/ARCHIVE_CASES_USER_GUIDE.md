# Archive Cases User Guide

## Quick Start

### Archive a Closed Case (3 steps)
1. **Dashboard** → Right-click closed case
2. **Select** "📦 Archive Case..." 
3. **Confirm** with optional reason

### View Archived Cases (1 click)
- **Menu**: View > Archived Cases OR Press **Ctrl+Shift+A**

### Restore a Case (3 steps)
1. **Open** Archived Cases view (Ctrl+Shift+A)
2. **Select** case to restore
3. **Click** "↩️ Restore Case"

---

## Overview

The Archive System provides a way to manage closed cases by moving them out of the active dashboard while keeping them fully searchable and restorable. This helps keep your active workspace clean and organized.

### What Archives Do
- ✅ Remove cases from active dashboard
- ✅ Keep all case data completely intact
- ✅ Allow full search and filtering
- ✅ Enable restoration at any time
- ✅ Maintain audit logs

### What Archives Don't Do
- ❌ Delete case data
- ❌ Change case information
- ❌ Affect evidence or legal items
- ❌ Remove access permissions
- ❌ Prevent restoration

---

## Archiving Cases

### Prerequisites for Archiving

Your case must meet these requirements:
- ✅ Case status is "Closed"
- ✅ You have access to the case
- ✅ All case work is complete

**Note**: Open or In Progress cases cannot be archived

### Step-by-Step: Archive a Case

**Step 1: Open Dashboard**
- Go to main application dashboard
- You should see all active cases listed

**Step 2: Find Closed Case**
- Locate case with status "Closed"
- Look in the Status column of dashboard

**Step 3: Right-Click Case**
- Right-click on the case row
- Context menu appears

**Step 4: Select Archive Option**
- Click "📦 Archive Case..."
- Archive Case dialog opens

**Step 5: Review Case Details**
- Dialog shows case number
- Dialog shows suspect name
- Verify you selected correct case

**Step 6: Select Archive Date**
- **Option A - Default (Recommended)**:
  - Keep "Use default (30 days from today)" selected
  - Shows calculated date (e.g., "March 6, 2026")
  
- **Option B - Custom Date**:
  - Click "Set custom archive date:" radio button
  - Click date field to open calendar picker
  - Select any future date
  - Date updates in display

**Step 7: Enter Archive Reason (Optional)**
- Click in reason text box
- Type explanation for archiving (optional but recommended)
- Examples:
  - "Case completed and filed"
  - "Prosecution declined"
  - "Transferred to other district"
  - "Statute of limitations expired"

**Step 8: Review and Confirm**
- Dialog shows:
  - Case number
  - Archive date
  - Your entered reason
- Click "📦 Archive Case"

**Step 9: Final Confirmation**
- Confirmation dialog appears
- Shows all details one more time
- Click "Yes" to confirm or "No" to cancel

**Step 10: Case Archived**
- Dialog closes
- Case immediately disappears from dashboard
- Confirmation message appears

### After Archiving

**What Happens**:
- Case removed from active dashboard
- Case stays in system (not deleted)
- Case searchable via Archived Cases view
- Any open case tabs close automatically

**To Find Your Archived Case**:
- Open View > Archived Cases (Ctrl+Shift+A)
- Search or filter to find case
- See full archive details

---

## Viewing Archived Cases

### Opening Archived Cases View

**Method 1: Using Menu**
1. Click **View** in menu bar
2. Select **Archived Cases**

**Method 2: Using Keyboard Shortcut**
- Press **Ctrl+Shift+A**

**Result**: Archived Cases dialog opens

### Understanding the Archived Cases Window

#### Top Section: Search and Filter Controls
```
Search: [_______________]     (Search box - type to search)
Year:   [Dropdown ▼ All  ]    (Year filter - select specific year)
🔄 Refresh  (Refresh button - reload list)
```

#### Main Section: Cases Table
Shows archived cases with columns:
- **Case Number** - Unique ID
- **Suspect** - Suspect/defendant name
- **Assigned To** - Investigator name
- **Agency** - Law enforcement agency
- **Archived Date** - When case was archived
- **Archived By** - Who archived it
- **Reason** - Why archived (truncated)

#### Right Section: Case Details
When you select a case:
- **Case Number**: Shows full case ID
- **Suspect**: Suspect name
- **Archived Date**: Full formatted date
- **Archived By**: Username who archived
- **Reason**: Full text of archive reason

#### Bottom Section: Action Buttons
- **📄 View Details** - Open full case view
- **↩️ Restore Case** - Reactivate to dashboard
- **💾 Export List** - Save to CSV file
- **Close** - Close dialog

### Selecting an Archived Case

**To Select a Case**:
1. Click on any row in the cases table
2. Row highlights in blue
3. Details appear on the right panel
4. View Details and Restore buttons become active

**To See Full Details**:
- Double-click the row, OR
- Click "📄 View Details" button
- Case opens in read-only view

---

## Searching Archived Cases

### Using the Search Box

**To Search**:
1. Click in the Search box (top of dialog)
2. Type case number or suspect name
3. Results update in real-time
4. Clear box and press Enter to reset

**What You Can Search**:
- Case numbers (e.g., "2024-001")
- Case numbers partial (e.g., "2024" finds "2024-001")
- Suspect names (e.g., "Smith")
- Suspect names partial (e.g., "Smi" finds "Smith")

**Search Examples**:
- Type: "2024" → Finds all 2024 cases
- Type: "John" → Finds suspects named John
- Type: "Smith" → Finds suspect Smith or Smithson
- Search is case-insensitive

### Combining Search with Year Filter

**To Use Both**:
1. Select year from dropdown
2. Type search term in search box
3. Results show only cases matching BOTH filters
4. Click Refresh to update if needed

**Example**:
- Year: "2024"
- Search: "Smith"
- Result: Only Smith cases from 2024

---

## Filtering by Year

### Using the Year Dropdown

**To Filter by Year**:
1. Click the Year dropdown (shows "All" by default)
2. Select specific year or "All"
3. Dropdown closes
4. Table updates automatically

**Available Years**:
- Current year
- Previous 10 years
- "All" - No year filter

**Year Filter Examples**:
- Select "2026" → See only 2026 archived cases
- Select "2025" → See only 2025 archived cases
- Select "All" → See all archived cases

### Year + Search Combination

**Most Powerful Filter**:
1. Year dropdown: Select "2024"
2. Search box: Type "Smith"
3. Refresh: Click refresh button
4. Result: Only Smith cases from 2024

---

## Restoring Archived Cases

### When to Restore

Restore a case when:
- Investigation needs to resume
- New evidence discovered
- Case reopened by prosecutor
- Wrong case was archived

### Step-by-Step: Restore an Archived Case

**Step 1: Open Archived Cases**
- Menu: View > Archived Cases
- Or press: Ctrl+Shift+A

**Step 2: Find the Case**
- Search by case number
- Filter by year
- Scroll through table

**Step 3: Select the Case**
- Click on case row to select
- Row highlights in blue
- Details appear on right

**Step 4: Click Restore Button**
- Click "↩️ Restore Case" button
- Becomes active only when case selected

**Step 5: Confirm Restoration**
- Confirmation dialog appears
- Shows case number and details
- Click "Yes" to restore or "No" to cancel

**Step 6: Case Restored**
- Dialog closes
- Case immediately reappears in active dashboard
- Archived flag removed
- Case fully functional

### After Restoration

**What Changes**:
- Case added back to active dashboard
- Archived status removed
- Can be edited and worked on again
- Can be archived again if needed

**What Stays Same**:
- All case data intact
- All evidence and legal items unchanged
- All notes and documents preserved
- All court dates unchanged

---

## Exporting Archived Cases

### When to Export

Export archived cases for:
- Reporting to management
- Backup purposes
- Historical records
- Data analysis
- Archive in external system

### Step-by-Step: Export Archived Cases

**Step 1: Open Archived Cases**
- Menu: View > Archived Cases
- Or press: Ctrl+Shift+A

**Step 2: Apply Filters (Optional)**
- Use search to narrow results
- Use year filter if desired
- Leave blank to export all

**Step 3: Click Export Button**
- Click "💾 Export List" button
- File save dialog opens

**Step 4: Choose Location**
- Navigate to desired folder
- Default filename: "archived_cases_YYYYMMDD.csv"
- Change name if desired

**Step 5: Save File**
- Click Save button
- File saved to location
- Confirmation message appears

### CSV File Contents

**Exported Columns**:
1. Case Number
2. Suspect Name
3. Assigned To (Investigator)
4. Agency
5. Archived Date (formatted)
6. Archived By (Username)
7. Archive Reason

**Opening CSV File**:
- Open in Microsoft Excel
- Open in Google Sheets
- Open in Numbers (Mac)
- Edit in text editor

**Using Exported Data**:
- Print for filing
- Forward to prosecutors
- Import to other systems
- Create reports
- Backup records

---

## Tips and Best Practices

### Archive Best Practices

#### ✅ DO:
- Archive when case truly closed
- Add meaningful archive reason
- Regularly review archived list
- Export for backup periodically
- Restore promptly if needed

#### ❌ DON'T:
- Archive active/open cases
- Forget to add archive reason
- Archive without purpose
- Ignore archived cases
- Delete archives manually

### Productivity Tips

**Keep Dashboard Clean**
- Archive closed cases regularly
- Prevents dashboard clutter
- Makes active cases easier to find

**Use Reasons for Context**
- Future you will appreciate reason
- Helps with audit trail
- Documents case decision

**Export Regularly**
- Backup your archives
- Create historical records
- Export at month/quarter end

**Search Tips**
- Partial searches work
- Case-insensitive
- Type slowly for best results
- Use refresh if stuck

---

## Common Questions and Answers

### Q: Can I archive a case that's still open?

**A**: No. Only "Closed" status cases can be archived. You must close the case first.

### Q: What happens to my case data when I archive?

**A**: NOTHING. All case data is 100% preserved:
- Evidence items untouched
- Legal processes unchanged
- Notes and documents stay
- Court dates maintained
- User assignments preserved

### Q: Can I unarchive (restore) a case?

**A**: Yes, absolutely! Any archived case can be restored to active status at any time with one click.

### Q: Can I archive a case, then archive it again later?

**A**: Yes. Cases can be archived and restored multiple times without problems.

### Q: How long does archive stay in system?

**A**: Indefinitely. Archived cases stay in system until you restore them or manually delete (not recommended).

### Q: Can others see my archived cases?

**A**: Only people with access to the case and the archive feature can see them. Permissions are maintained.

### Q: What if I archive the wrong case by mistake?

**A**: No problem! Use View > Archived Cases (Ctrl+Shift+A) to find and restore it immediately.

### Q: Can I export my archived cases?

**A**: Yes! Click "💾 Export List" to save to CSV file with all details.

### Q: What does the archive date mean?

**A**: The date shown is when the case was archived. You can set custom dates during archiving.

### Q: Can I view archived case details?

**A**: Yes. Select case in Archived Cases view and click "📄 View Details" for full case information.

### Q: How do I search archived cases?

**A**: Use the Search box (case #, suspect name) or Year filter (dropdown). Type to search in real-time.

---

## Troubleshooting

### Problem: "I can't find the Archive option"

**Solution**:
1. Make sure case status is "Closed"
2. Right-click on the case row
3. If menu doesn't appear, refresh dashboard
4. If still missing, case not closed - change status first

### Problem: "Case still appears in dashboard after archiving"

**Solution**:
1. Refresh the dashboard (F5 or click refresh)
2. Close and reopen the application
3. Clear browser cache if using web version
4. Check that archive confirmation was accepted

### Problem: "I can't restore a case"

**Solution**:
1. Make sure you clicked "Yes" in confirmation dialog
2. Check Archived Cases dialog again - case may be restored
3. If not visible, check year filter setting
4. Restart application if problems persist

### Problem: "My search isn't finding the case"

**Solution**:
1. Try searching differently (search terms different)
2. Set Year filter to "All" instead of specific year
3. Clear search box and try partial match
4. Click Refresh button
5. Manually scroll through list

### Problem: "Can't open Archived Cases view"

**Solution**:
1. Try keyboard shortcut: Ctrl+Shift+A
2. Check View menu - option should show
3. Restart application
4. Check permissions - may need admin

### Problem: "Export file is empty"

**Solution**:
1. Make sure cases are showing in dialog
2. Clear filters and try exporting all
3. Try saving to different location
4. Check file permissions on save location

---

## Keyboard Shortcuts

### Archive Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Shift+A | Open Archived Cases view |
| Esc | Close Archived Cases dialog |
| Double-click | View selected case details |
| Enter | Refresh search results |

### General Dashboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+N | New Case |
| Right-click | Context menu (dashboard) |
| Ctrl+F | Find/Search |

---

## Support and Help

### Getting More Help

**In Application**:
- Tools > Report Bug - Report problems
- View > Archived Cases - Access archive help
- Tooltips - Hover over buttons for help

**Documentation**:
- Main User Guide - Complete feature overview
- This guide - Archive system details
- Installation Guide - Setup information

### Reporting Issues

If something doesn't work:
1. Tools > Report Bug
2. Describe what happened
3. Include steps to reproduce
4. Include case number if relevant
5. Note any error messages

---

## Version Information

**Archive System Version**: 1.0
**Release Date**: February 2026
**Status**: Production Release

---

**Need more help? Check MAIN_USER_GUIDE.md for complete application documentation.**

