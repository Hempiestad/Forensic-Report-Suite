# Main Application User Guide — FuDog Labs Forensic Report Suite

## Overview

The Main Application is the central hub of the FuDog Labs Forensic Report Suite. It provides a comprehensive case management dashboard, user authentication, theme customization, and access to all forensic reporting tools. The application supports role-based access control and integrates with both local and server-based databases.

## Getting Started

### Launching the Application

1. Run the main.py file or executable
2. The application will prompt for authentication if configured
3. Upon successful login, the main window opens with the Dashboard tab

### Authentication

The application supports multiple authentication methods:

- **Local Authentication**: Default anonymous access for standalone use
- **Active Directory**: Enterprise authentication via AD integration
- **Server Authentication**: Remote authentication against a forensic server

**Configuration**: Authentication method is set in `config.json`:
```json
{
  "use_ad": true,
  "server_url": "https://forensic-server.example.com"
}
```

### User Roles and Permissions

- **Admin**: Full access to all features and case management
- **Supervisor**: Can manage cases, add evidence/legal items, access all tools
- **Investigator**: Can view and edit assigned cases, access investigation tools
- **Examiner**: Can view cases, perform examinations, generate reports

## Interface Overview

### Main Window Layout

- **Menu Bar**: File, Tools, View, and Tracker operations
- **Tab Widget**: Dashboard and individual case tabs
- **Status Bar**: Application status and notifications

### Dashboard Tab

The Dashboard provides an overview of all accessible cases with advanced filtering and visualization.

#### Dashboard Features

- **Case Table**: Expandable tree view showing case details
- **Charts Section**: Visual representation of case statuses
- **Filter Bar**: Search and filter cases by various criteria
- **Sorting**: Click column headers to sort data

## Dashboard Navigation

### Viewing Cases

Cases are displayed in a hierarchical table with the following columns:

- **Case #**: Unique case identifier
- **Assigned To**: User responsible for the case
- **Evidence**: Status of evidence items (color-coded)
- **Legal** (Investigator view only): Status of legal processes
- **Report Status**: Current report workflow status
- **Trial Date**: Scheduled trial date with highlighting
- **Sentencing Date**: Scheduled sentencing date

### Expanding Case Details

- Click the arrow next to a case to expand/collapse details
- Evidence and Legal columns show summary badges with detailed tooltips
- Double-click case rows to open individual case tabs

### Status Color Coding

- **Green**: Completed/Imaged items
- **Yellow**: Pending/Not Imaged items
- **Red**: Overdue items
- **Grey**: Cancelled/Not Needed items

## Filtering and Search

### Global Search

- Use the search box to filter cases by case number, assigned user, or status
- Search is case-insensitive and searches across multiple columns

### Column Filters

- **Status Filter**: Filter by report status (Draft, Submitted, etc.)
- **Assigned To Filter**: Filter by assigned investigator/examiner
- **Upcoming Trials**: Highlight trials within specified days
- **Upcoming Only**: Show only cases with upcoming trial dates

### Date Highlighting

- **Red**: Trial date has passed (overdue)
- **Orange**: Trial within 7 days
- **Yellow**: Trial within specified upcoming days
- **Green**: Trial more than upcoming days away

## Charts and Analytics

### Chart Types

The dashboard displays pie charts showing:

- **Case Status**: Distribution of report statuses
- **Evidence Status**: Evidence imaging completion
- **Legal Processes** (Investigator view): Legal process completion
- **Leads** (Investigator view): Lead investigation status

### Chart Caching

Charts are cached for 30 seconds to improve performance. Charts automatically refresh when:
- View changes between Investigator/Examiner
- New data is available
- Cache timeout expires

## Menu Operations

### File Menu

- **New Case**: Create a new case with basic information
- **Export CSV**: Export dashboard data to CSV format
- **Export PDF**: Export dashboard data to PDF format
- **Export Excel**: Export dashboard data to Excel format
- **Request Feature**: Submit feature requests
- **Documentation**: Access user guides and installation guide
  - **Main User Guide**: Overview of application features
  - **Notes User Guide**: Notes tab documentation
  - **Reports User Guide**: Reports tab documentation
  - **Server User Guide**: Server setup and configuration
  - **Server Component Guide**: Server architecture and module map
  - **Server Deployment Guide**: Production deployment and operations checklist
  - **Installation Guide**: Installation instructions
- **Settings**: Configure application preferences
- **Close**: Close the application

### Tools Menu

- **Export PDF**: Export current case report as PDF
- **Audit Log**: View audit trail for current case
- **Peer Review Mode**: Toggle peer review functionality
- **SWGDE Glossary Search**: Search forensic terminology
- **Glossary Assist**: Advanced glossary assistance
- **Legal Template Library**: Manage shared legal-process templates (hierarchical vendor/type structure) — **Tools → Legal Template Library**
- **Report Bug**: Submit bug reports
- **Case Calendar**: View case events in calendar format

### View Menu

- **Archived Cases** (Ctrl+Shift+A): View and manage archived cases
  - **Search**: Find cases by case number or suspect name
  - **Filter**: Filter archived cases by year or assigned user
  - **Restore**: Reactivate archived cases to the active dashboard
  - **Export**: Export archived case list to CSV format
  - See [Archived Cases Management](#archived-cases-management) section below
- **User View**: Switch between Investigator and Examiner perspectives
  - **Investigator**: Full case management and legal tracking
  - **Examiner**: Report generation and evidence examination

### Tracker Menu

- **Add Evidence Item**: Add evidence to current case (Supervisor+ only)
- **Add Legal Process**: Add legal process to current case (Supervisor+ only)
- **Add Lead**: Add investigation lead to current case
- **Add Case Date**: Add important case date/milestone

### Notifications Menu

The Notifications menu provides access to the application's notification system for tracking legal deadlines, court dates, and evidence status changes.

- **View Notifications** (Ctrl+Shift+N): Open the notifications panel to view all notifications
  - Filter by type: All, Unread, Critical, Warning, Info, Legal, Court Dates, Evidence
  - View notification details with severity indicators
  - Mark notifications as read or dismiss them
  - Open related cases directly from notifications
- **Check Now**: Manually trigger a notification check
- **Dismiss All**: Dismiss all current notifications

#### Notification Types

- **Legal Process Notifications**: Due date warnings, expiration alerts, overdue notices
- **Court Date Notifications**: Advance warnings for trials, hearings, depositions
- **Evidence Notifications**: Completion alerts and status change notifications

#### Notification Settings

Configure notification preferences in **File → Settings → Notifications**:
- Enable/disable notification types
- Set warning days for legal processes and court dates
- Configure display settings (popup duration, badge count)
- Enable/disable system tray notifications

## Legal Template Library

The Legal Template Library supports reusable templates for:

- Preservation letters
- Subpoenas
- Search warrants

### Structure

Templates are organized in a hierarchy:

- Vendor root folder (for example, Google, Apple, Meta)
- Template type subfolder (`preservation_letter`, `subpoena`, `search_warrant`, `other`)
- Individual templates in each folder

### Common Actions

- **Save Current as Template**: Saves current report text to the selected folder.
- **Open in Report Writer**: Opens template content in the report writer for editing.
- **Share Selected**: Shares one template with another investigator.
- **Share Folder**: Shares vendor-only or vendor+type scope.
- **Share Library**: Shares all templates you own.
- **Import/Export**: Move templates between environments.

### Limited Sharing Behavior

Folder sharing is scoped to what you selected:

- Vendor node selected -> share all templates under that vendor.
- Type folder selected -> share only that vendor/type folder.
- Template selected -> share that template's folder scope.

Users only see templates they own or templates explicitly shared with them.

### Permissions

- Admin can view all templates.
- Owners can edit their own templates.
- Shared recipients can view/use shared templates.
- Supervisor/examiner assignment constraints are enforced in server mode.

## Settings Configuration

### Accessing Settings

**File → Settings** or configure via `config.json`

### Timezone Settings

- **System Local**: Use system timezone
- **UTC**: Use Coordinated Universal Time
- **Custom Offset**: Specify hours offset from UTC

### Theme Selection

- **Light**: Traditional light theme
- **Dark**: Dark theme for low-light environments
- **High Contrast**: High contrast for accessibility

### Status Colors

Customize the color scheme for status indicators:
- Open, Pending, Overdue, Closed
- Colors are applied across dashboard and case tabs

### Context Menu Configuration

Toggle availability of context menu items in Notes and Reports tabs:
- Insert Timestamp, Convert Timestamp, Insert Template
- Create Task, Tag Selection, Redact Selection
- Create Calendar Event, Export Selection

## Case Management

### Creating New Cases

1. **File → New Case**
2. Enter case number (required)
3. Optional: Suspect, Investigator, Agency, Trial/Sentencing dates
4. Case is created and opened in new tab

### Opening Cases

- Double-click case in dashboard
- Cases open in separate tabs
- Closed cases cannot be opened (greyed out)

### Case Tabs

Each case opens in its own tab containing:
- **Case Tab**: Evidence, legal processes, leads management
- **Notes Tab**: Rich text note-taking with timestamps
- **Reports Tab**: PDF report generation with appendices

## Calendar Integration

### Case Calendar

**Tools → Case Calendar** displays a monthly calendar with:

- **Event Highlighting**: Colored dots for different event types
- **Event Types**:
  - Case creation dates
  - Trial dates
  - Sentencing dates
  - Court dates (hearings, depositions)
  - Legal due dates

### Calendar Navigation

- Click dates to view events
- Events show case information and allow direct case opening
- Color-coded badges indicate event types

## Export Functionality

### Dashboard Export

- **CSV**: Tabular data export
- **PDF**: Formatted report with tables
- **Excel**: Spreadsheet format with formatting

### Case Export

- **PDF Export**: Generate final forensic reports
- **Audit Log**: Export case activity history
- **Peer Review**: Export for external review

## User Interface Customization

### Theme Application

Themes are applied immediately and persist across sessions. Available themes:
- Light: Standard desktop appearance
- Dark: Reduced eye strain in low light
- High Contrast: Improved accessibility

### View Switching

Switch between Investigator and Examiner views:
- Investigator: Full case lifecycle management
- Examiner: Focused on evidence examination and reporting

## Data Management

### Database Integration

- **Local Database**: SQLite for standalone operation
- **Server Database**: PostgreSQL/MySQL for multi-user environments
- **Automatic Sync**: Changes saved immediately

### Audit Trail

All actions are logged including:
- Case creation/modification
- User access and authentication
- Report generation and exports
- Evidence and legal process changes

## Performance Features

### Chart Caching

- Charts cached for 30 seconds
- Reduces database load during dashboard refreshes
- Automatic cache invalidation on data changes

### Incremental Updates

- Dashboard updates only changed cases
- Efficient sorting and filtering
- Lazy loading of case details

## Archived Cases Management

### Overview

The Archive System allows investigators to clean up the active dashboard by archiving closed cases while maintaining full searchability and the ability to restore cases if needed. Archived cases are removed from the active dashboard but remain fully accessible through the dedicated Archived Cases viewer.

### When to Archive Cases

Archive a case when:
- The case is in "Closed" status
- All investigation and reporting is complete
- Case no longer needs active dashboard space
- You want to keep historical records organized

### Archiving a Case

#### Method 1: Dashboard Context Menu (Recommended)
1. In the Dashboard, right-click on a **Closed** case
2. Select **"📦 Archive Case..."** from the context menu
3. The Archive Case dialog opens showing:
   - Case number and suspect name
   - Default archive date (30 days from today)
   - Option to set custom archive date
   - Optional reason text field
4. Review the archive date and enter a reason (recommended)
5. Click **"Archive Case"** to confirm
6. Case immediately disappears from the active dashboard

**Note**: Only cases with "Closed" status can be archived

#### Archive Dialog Options

- **Default Date (Recommended)**: 30 days from today
- **Custom Date**: Click radio button and pick any future date
- **Archive Reason**: Optional field for recording why case was archived
- **Confirmation**: Dialog shows all details before final commitment

### Viewing Archived Cases

#### Opening the Archived Cases View

- **Menu**: View > Archived Cases
- **Keyboard Shortcut**: Ctrl+Shift+A
- Opens a dedicated dialog showing all archived cases

#### Archived Cases Table

Displays the following columns for each archived case:
- **Case Number**: Unique case identifier
- **Suspect**: Suspect/defendant name
- **Assigned To**: Investigator assigned to case
- **Agency**: Associated law enforcement agency
- **Archived Date**: Date when case was archived
- **Archived By**: Username who performed the archive
- **Reason**: Archive reason (truncated in table, full in details panel)

#### Selecting a Case

- Click any row to select and view full details
- Right panel displays complete information including full reason text
- Double-click to view full case details in read-only mode

### Searching and Filtering Archived Cases

#### Search Box

- Search by **Case Number** or **Suspect Name**
- Partial matches work (e.g., "Smith" finds "Smithson")
- Case-insensitive search
- Real-time as you type

#### Year Filter

- Dropdown showing current year and 10 previous years
- Select "All" to view archived cases from any year
- Combines with search filter for precise results

#### Applying Filters

1. Use search box to find specific cases
2. Use year dropdown to limit by date range
3. Click **🔄 Refresh** to update results
4. Results update automatically

### Restoring Archived Cases

#### To Restore an Archived Case

1. Open View > Archived Cases (Ctrl+Shift+A)
2. Search or filter to find the case
3. Select the case by clicking its row
4. Click **"↩️ Restore Case"** button
5. Confirm restoration in the dialog
6. Case immediately reappears in active dashboard

**Result**: Archived flag removed, case fully reactivated with all data intact

#### Restoring Multiple Cases

Archive/Restore is currently a one-at-a-time operation. To restore multiple cases:
1. Repeat the restore process for each case
2. Each restoration is independent

### Exporting Archived Cases

#### To Export Archived Cases List

1. Open View > Archived Cases (Ctrl+Shift+A)
2. Apply search/filter filters as needed (exports filtered results)
3. Click **"💾 Export List"** button
4. Choose save location and filename
5. CSV file is created with archive data

#### CSV Export Contents

Exported file includes:
- Case Number
- Suspect Name
- Assigned To (Investigator)
- Agency
- Archived Date
- Archived By
- Archive Reason

**Use for**: Reporting, backups, historical analysis

### Archive Case Details

#### Case Information Preserved

When a case is archived, the following information is **fully preserved**:
- Case number and suspect information
- All evidence items and imaging status
- All legal processes and status
- All leads and investigation notes
- All notes and documents
- All court dates and deadlines
- All user assignments and permissions

**No data is lost or modified** when archiving or restoring

#### Archive Metadata

The following information is **recorded** when archiving:
- Archive date (when archived)
- Archived by (which user performed archive)
- Archive reason (optional explanation)

#### Viewing Case Details

- Select archived case in dialog
- Right panel shows: Case #, Suspect, Archive Date, Archived By, full Reason
- Click **"📄 View Details"** to see full case information

### Keyboard Shortcuts for Archive

- **Ctrl+Shift+A**: Open Archived Cases view
- **Esc**: Close Archived Cases dialog
- **Double-click**: View case details

### Tips and Best Practices

#### DO:
✅ Archive when case is truly "Closed"
✅ Add a descriptive reason for archiving
✅ Regularly review archived cases
✅ Export archived cases for backup
✅ Restore promptly if case needs reopening

#### DON'T:
❌ Archive open/active cases
❌ Forget to add reason for later reference
❌ Restore unless truly needed
❌ Archive recent cases (wait until truly closed)

### Common Archive Tasks

#### Task: Find and restore a case archived 6 months ago
1. View > Archived Cases (Ctrl+Shift+A)
2. Year filter: Select the year archived
3. Search: Type case number or suspect name
4. Select case from results
5. Click "↩️ Restore Case"

#### Task: Export archive for record keeping
1. View > Archived Cases
2. Apply filters for desired date range
3. Click "💾 Export List"
4. Save CSV file to backup location

#### Task: Archive multiple closed cases
1. For each closed case:
   - Right-click on dashboard
   - Select "📦 Archive Case..."
   - Enter reason and confirm
   - Case disappears from dashboard

### Archive Troubleshooting

**Q: Can't archive a case**
A: Only "Closed" status cases can be archived. Check case status in dashboard.

**Q: Archived case still shows in dashboard**
A: Refresh dashboard or close/reopen application. Try again.

**Q: Can't find archived case**
A: Check year filter (wrong year selected). Try "All" in year dropdown.

**Q: Can I restore a case multiple times?**
A: Yes, cases can be archived and restored repeatedly without data loss.

**Q: What happens to evidence/legal when I archive?**
A: All data is preserved. Archive only affects dashboard visibility.

## Troubleshooting

### Common Issues

**Authentication Fails**
- Check network connectivity for server authentication
- Verify AD configuration
- Ensure user credentials are correct

**Charts Not Loading**
- Install matplotlib: `pip install matplotlib`
- Check pyqtgraph availability
- Verify data availability

**Theme Not Applying**
- Restart application after theme change
- Check config.json permissions
- Verify theme file integrity

**Calendar Not Showing Events**
- Ensure case dates are properly formatted (YYYY-MM-DD)
- Check database connectivity
- Verify user permissions for case access

### Performance Optimization

- Close unused case tabs to free memory
- Use filters to limit displayed cases
- Dashboard refreshes automatically every 30 seconds
- Export large datasets during off-peak hours

## Security Features

### Access Control

- Role-based permissions for all operations
- Encrypted database storage
- Secure authentication protocols

### Data Integrity

- SHA-256 hashing for exported PDFs
- Audit logging for all changes
- Path validation to prevent directory traversal

### Session Management

- Automatic logout on inactivity (configurable)
- Secure credential handling
- Session-based access control

## Configuration Files

### config.json

Main configuration file containing:
```json
{
  "use_ad": false,
  "server_url": null,
  "theme": "dark",
  "timezone": "local",
  "status_colors": {...},
  "context_menu": {...},
  "dashboard_sort": {...}
}
```

### Database Files

- **forensic_reports.db**: Local SQLite database
- **Server connection**: Remote database via configured URL

## Keyboard Shortcuts

### General
- `Ctrl+N`: New Case
- `Ctrl+W`: Close Current Tab

### Dashboard
- Click column headers for sorting
- Double-click rows to open cases

### Navigation
- Tab switching with `Ctrl+Tab`
- Menu access with `Alt+` + underlined letter

## Integration with Case Tools

### Notes Tab Integration

- Access via case tabs
- Timestamp conversion and insertion
- Template management
- Voice-to-text transcription

### Reports Tab Integration

- PDF generation with integrity verification
- Appendix management
- Peer review workflow
- Evidence embedding
- Legal template editing through the report writer

### Case Tab Integration

- Evidence tracking and imaging status
- Legal process management
- Lead investigation tracking
- Court date scheduling

---

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Installation Guide](INSTALLATION_GUIDE.md) — Installation and configuration
- [Notes Tab User Guide](NOTES_USER_GUIDE.md) — Rich text note-taking
- [Reports Tab User Guide](REPORTS_USER_GUIDE.md) — PDF report authoring
- [Server User Guide](SERVER_USER_GUIDE.md) — Server setup and API reference
- [Legal Workflow Guide](LEGAL_WORKFLOW_GUIDE.md) — Legal process approval stages
- [Legal Workflow UI Guide](LEGAL_WORKFLOW_UI_GUIDE.md) — Workflow UI dialog reference

