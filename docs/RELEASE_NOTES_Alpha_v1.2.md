# Release Notes - FuDog Labs Forensic Report Suite v1.2 Alpha

**Release Date**: February 3, 2026  
**Version**: 1.2 Alpha  
**Build Type**: Alpha Testing Release

---

## Overview

This is an **alpha release** of the FuDog Labs Forensic Report Suite for testing purposes. This release includes significant new features and improvements, particularly in notification management and user documentation access.

**Target Audience**: Internal testers, selected partners, and early adopters for feedback collection.

---

## What's New in v1.2 Alpha

### Major Features

#### 1. **Documentation Menu System** ✨
- Added **File > Documentation** submenu with quick access to all user guides
- Integrated documentation opens directly from the application
- Includes:
  - Main User Guide
  - Notes User Guide
  - Reports User Guide
  - Server User Guide
  - Installation Guide

#### 2. **Comprehensive Notifications System** 🔔
- Real-time notification tracking for legal processes, court dates, and evidence
- **Notifications Menu** with:
  - View Notifications panel (Ctrl+Shift+N)
  - Manual notification check
  - Dismiss all notifications
- Configurable notification settings:
  - Legal process due date warnings
  - Court date advance warnings
  - Evidence status change alerts
  - Customizable warning intervals
- Notification severity levels: Critical, Warning, Info
- Filter notifications by type and status

### Improvements

#### User Interface
- Enhanced menu organization with clearer groupings
- Updated Main User Guide with complete menu documentation
- Better notification badge visibility
- Improved status color indicators

#### Performance
- Chart caching for faster dashboard rendering (30-second cache)
- Optimized database queries for notifications
- Efficient notification checking (5-minute intervals by default)

#### Documentation
- Complete user guides for all major features
- In-app documentation access
- Comprehensive build and installation guides
- Updated troubleshooting sections

---

## Feature Summary

### Core Features
- ✓ Case management with evidence and legal process tracking
- ✓ Rich text notes with timestamp management
- ✓ Professional report generation with PDF export
- ✓ SWGDE/NIST template support
- ✓ Peer review workflow
- ✓ Audit logging for all actions
- ✓ Role-based access control (Admin, Supervisor, Investigator, Examiner)
- ✓ Theme support (Light, Dark, High Contrast)

### Dashboard
- ✓ Hierarchical case view with expandable details
- ✓ Status-based filtering and search
- ✓ Visual charts for case/evidence/legal status
- ✓ Export to CSV, PDF, and Excel
- ✓ Upcoming trial date highlighting
- ✓ View switching (Investigator/Examiner modes)

### Notes Tab
- ✓ Rich text formatting with comprehensive toolbar
- ✓ Timestamp insertion and conversion (multiple timezones)
- ✓ Template management
- ✓ Attachment support with hash verification
- ✓ Voice-to-text transcription (optional)
- ✓ Geo-lookup functionality (optional)
- ✓ Timeline generation

### Reports Tab
- ✓ Professional report editor
- ✓ PDF generation with SHA-256 hash verification
- ✓ Appendices management
- ✓ NIST template with auto-populated evidence tables
- ✓ DOCX import capability
- ✓ Peer review export/import
- ✓ Evidence reference embedding

### Notifications (NEW in v1.2)
- ✓ Automated legal process monitoring
- ✓ Court date reminders
- ✓ Evidence status tracking
- ✓ Customizable warning periods
- ✓ Notification history and filtering
- ✓ One-click case access from notifications

---

## Known Issues

### High Priority
1. **Icon Files**: Application icons (forensic_client.ico) may not display correctly on all systems
2. **First Launch**: Initial database creation may take 5-10 seconds
3. **PDF Generation**: WeasyPrint may show warnings on first PDF export (these can be ignored)

### Medium Priority
1. **Theme Switching**: Some UI elements may require application restart to fully apply theme changes
2. **Chart Rendering**: On systems without matplotlib/pyqtgraph, charts will not display (feature degrades gracefully)
3. **Notification Timing**: First notification check occurs 5 minutes after application start

### Low Priority
1. **Documentation Links**: Documentation files open in system default application (may be plain text editor instead of Markdown viewer)
2. **Status Colors**: Custom status colors require application restart to apply to existing cases
3. **Export Performance**: Large case exports (100+ cases) may take 15-30 seconds

### Not Implemented Yet
- Real-time collaborative editing
- Advanced analytics and reporting
- Integration with external case management systems
- Mobile companion app
- Cloud synchronization

---

## System Requirements

### Minimum Requirements
- **OS**: Windows 10 (64-bit), macOS 10.15+, Ubuntu 18.04+
- **RAM**: 4GB
- **Storage**: 500MB free space
- **Display**: 1280x720 resolution

### Recommended Requirements
- **OS**: Windows 11 (64-bit), macOS 12+, Ubuntu 20.04+
- **RAM**: 8GB or more
- **Storage**: 2GB free space (for case data)
- **Display**: 1920x1080 or higher

### No Python Required
This executable build includes all necessary dependencies - **no Python installation needed**!

---

## Installation Instructions

### First-Time Installation

1. **Extract the Archive**
   - Unzip `ForensicReportSuite_v1.2_Alpha_Win64.zip` to your desired location
   - Recommended: `C:\Program Files\ForensicReportSuite\`

2. **Run the Application**
   - Navigate to the extracted folder
   - Double-click `ForensicReportWriter.exe`
   - Windows SmartScreen may appear - click "More info" then "Run anyway"

3. **First Launch**
   - Application will create necessary directories
   - Default configuration will be loaded
   - Dashboard will appear with no cases (empty state is normal)

4. **Access Documentation**
   - Go to **File > Documentation** to access user guides
   - Start with the Main User Guide for an overview

### Upgrading from Previous Version

1. **Backup Your Data**
   - Backup the `cases/` directory from your previous installation
   - Export your current config.json (if customized)

2. **Install New Version**
   - Extract to a new location (or overwrite previous version)
   - Copy your `cases/` directory to the new installation
   - Copy your customized `config.json` if applicable

3. **Verify**
   - Launch the application
   - Verify your cases appear in the dashboard
   - Check that settings are preserved

---

## Testing Focus Areas

We need your feedback on the following areas:

### Priority 1: Critical Features
- [ ] Case creation and management workflow
- [ ] Evidence tracking and status updates
- [ ] Legal process management
- [ ] Notification system reliability
- [ ] PDF report generation

### Priority 2: Usability
- [ ] Menu organization and discoverability
- [ ] Documentation accessibility (File > Documentation)
- [ ] Notification settings and preferences
- [ ] Theme consistency across all tabs
- [ ] Search and filtering functionality

### Priority 3: Performance
- [ ] Dashboard loading time with multiple cases
- [ ] Chart rendering performance
- [ ] PDF export speed for large reports
- [ ] Notification check impact on responsiveness
- [ ] Memory usage during extended sessions

### Priority 4: Documentation
- [ ] User guide completeness and accuracy
- [ ] Missing features or undocumented functionality
- [ ] Unclear instructions or examples
- [ ] Need for additional tutorials or walkthroughs

---

## How to Report Issues

### Using the Application
1. **Bug Reports**: Go to **Tools > Report Bug**
   - Describe the issue in detail
   - Include steps to reproduce
   - Note any error messages
   - Bug report is saved to database

2. **Feature Requests**: Go to **File > Request Feature**
   - Describe the desired functionality
   - Explain the use case
   - Priority level (optional)

### Alternative Methods
- Email: [your-email@example.com]
- Issue Tracker: [GitHub/Internal tracker URL]
- Direct Contact: [Phone/Teams/Slack]

### Information to Include
- Version number (v1.2 Alpha)
- Operating system and version
- Steps to reproduce the issue
- Expected vs actual behavior
- Screenshots (if applicable)
- Error messages or log excerpts

---

## Testing Scenarios

### Scenario 1: New Case Workflow
1. Create a new case
2. Add evidence items
3. Add a legal process (subpoena, warrant, etc.)
4. Create a note about the case
5. Generate a report
6. Export report as PDF
7. Check that notifications appear for legal deadlines

### Scenario 2: Notification Testing
1. Create a case with a court date in 7 days
2. Add a legal process with a due date in 3 days
3. Check **Notifications > View Notifications**
4. Verify notifications appear with correct urgency
5. Mark notifications as read
6. Verify badge count updates

### Scenario 3: Documentation Access
1. Go to **File > Documentation**
2. Open Main User Guide
3. Verify it opens in readable format
4. Navigate to other guides
5. Confirm all guides open correctly

### Scenario 4: Dashboard Features
1. Create 5-10 test cases
2. Use filters to narrow results
3. Switch between Investigator and Examiner views
4. Export dashboard to CSV and Excel
5. Verify charts display correctly

---

## Feedback Request

Please provide feedback on:

1. **Overall Experience**
   - Was the application intuitive to use?
   - Did you encounter any confusing workflows?
   - What features did you use most?

2. **Documentation**
   - Was the documentation helpful?
   - What information was missing?
   - Were examples clear and relevant?

3. **Performance**
   - Did the application feel responsive?
   - Were there any noticeable delays?
   - How was memory usage?

4. **Features**
   - What features are most valuable?
   - What's missing that you expected?
   - Any suggestions for improvements?

5. **Stability**
   - Did you experience any crashes?
   - Were there any error messages?
   - What was happening when issues occurred?

---

## Upcoming Features (Future Releases)

### Planned for Beta
- Enhanced chart customization
- Advanced search with full-text indexing
- Batch operations for multiple cases
- Custom report templates
- Improved peer review workflow

### Under Consideration
- Real-time collaboration features
- Cloud backup and sync
- Mobile app integration
- Advanced analytics dashboard
- Integration APIs for external tools

---

## Technical Details

### Build Information
- **PyInstaller Version**: 6.0+
- **Python Version**: 3.8+
- **PyQt5 Version**: 5.15.10
- **Build Date**: February 3, 2026
- **Architecture**: 64-bit

### Dependencies Included
- PyQt5 5.15.10 (GUI framework)
- WeasyPrint 62.0 (PDF generation)
- Pandas 2.2.2 (Data processing)
- Cryptography 43.0.1 (Security)
- All other dependencies bundled

### Database
- SQLite 3 (embedded, no external DB required)
- Database file: `forensic_suite.db`
- Automatic schema creation on first run

---

## Support and Contact

### Getting Help
- **Documentation**: File > Documentation within the application
- **Bug Reports**: Tools > Report Bug
- **Feature Requests**: File > Request Feature
- **Email**: [support email]

### Alpha Test Timeline
- **Alpha Period**: February 3 - February 28, 2026
- **Feedback Deadline**: February 25, 2026
- **Beta Release Target**: March 2026

---

## License and Legal

- This is pre-release software provided for testing purposes only
- Not for production use without explicit approval
- FuDog Labs retains all rights
- By testing this software, you agree to provide feedback
- Report any security concerns immediately

---

## Acknowledgments

Thank you to all alpha testers for helping improve the Forensic Report Suite!

Your feedback is crucial for delivering a stable, feature-rich forensic case management solution.

---

## Changelog

### v1.2 Alpha (February 3, 2026)
- Added Documentation menu system
- Implemented comprehensive notification system
- Updated all user guides
- Enhanced menu organization
- Improved notification settings UI
- Added notification panel with filtering
- Updated Main User Guide with notifications documentation
- Various bug fixes and performance improvements

### v1.1 (January 2, 2026)
- Enhanced peer review system
- Added chart caching
- Improved dashboard performance
- Status machine implementation
- Security enhancements

### v1.0 (December 2025)
- Initial release
- Core case management features
- Notes and reports tabs
- Basic dashboard functionality

---

**End of Release Notes**

For the latest information and updates, check the documentation within the application or contact the development team.

Happy Testing! 🚀
