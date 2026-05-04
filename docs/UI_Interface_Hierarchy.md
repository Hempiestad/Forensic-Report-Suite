# FuDog Labs Forensic Report Suite - UI Interface Hierarchy

## Overview
This document details the hierarchical structure of the user interface components and how they are organized within the application. The UI is built using PyQt5 and follows a tabbed interface design with role-based visibility.

## Main Application Window (MainWindow)

### Window Properties
- Title: "FuDog Labs Forensic Report Suite"
- Minimum Size: 1400x900
- Central Widget: QTabWidget (tabs)

### Menu Bar Structure
```
File Menu
├── New Case
├── Export CSV
├── Export PDF
├── Export Excel

Tools Menu
├── Export PDF
├── Audit Log
├── Peer Review Mode
├── SWGDE Glossary Search
└── Glossary Assist

View Menu
├── Theme Submenu (Light/Dark/High Contrast)
├── Separator
└── User View Submenu
    ├── Investigator (checkable)
    └── Examiner (checkable)

Customize Menu
└── Status Colors...
```

### Tab Widget Structure
```
Dashboard Tab (always visible)
├── Title Label: "My Cases Dashboard"
├── Filter Bar (QHBoxLayout)
│   ├── Search QLineEdit (placeholder: "Case #, Assigned, Status...")
│   ├── Status QComboBox (All/Draft/Submitted/In Peer Review/Revisions Needed/Approved/Closed)
│   ├── Assigned To QComboBox (All + dynamic user list)
│   └── Stretch spacer
├── Charts Layout (QHBoxLayout)
│   ├── Case Status Pie Chart (QLabel with QPixmap)
│   ├── Evidence Status Pie Chart (QLabel with QPixmap)
│   └── Stretch spacer
├── Cases Table (QTableView with custom delegate)
│   └── Columns: Case #, Assigned To, Evidence, [Legal], Report Status
└── Table interactions: Click for details, double-click to open case
```

## Case Tab Structure (CaseTab)

### Case Dashboard (QWidget)
```
Case Dashboard Layout (QHBoxLayout)
├── Case Status Label: "Case Status: [Status]"
├── Evidence Metrics Label: "Evidence: X items (Y imaged, Z analyzed)"
├── Legal Metrics Label: "Legal: X processes (Y completed)" (Investigator view only)
├── Open Notes QPushButton
├── Open Reports QPushButton
└── Stretch spacer
```

### Sub-Tabs (QTabWidget)
```
Evidence Tab (always visible)
└── Evidence Table (QTableWidget)
    ├── Columns: ID, Item Number, Type, Details, Make, Model, Digital Type, SN#, Storage Size, Password, Status
    └── Add Evidence Item QPushButton

Legal Processes Tab (Investigator view only)
└── Legal Table (QTableWidget)
    ├── Columns: ID, Type, Provider, Submitted, Due/Expires, Received, Analyzing, Completed, Status
    └── Add Legal Process QPushButton

Lead Tracker Tab (Investigator view only)
└── Leads Table (QTableWidget)
    ├── Columns: ID, Name, Description, Source, Completed (QCheckBox)
    └── Add Lead QPushButton
```

### Workflow Buttons (QHBoxLayout, role-based)
```
Writer Role Buttons
└── Submit for Approval QPushButton

Supervisor/Admin Role Buttons
├── Approve Report QPushButton
├── Reject with Comments QPushButton
└── Close Case QPushButton

All Roles
└── Stretch spacer
```

### Status Display
```
Final PDF Hash Label: "Final PDF Hash: [SHA-256 hash or 'Not generated']"
```

## Notes Window (NotesWindow)

### Window Structure
```
Notes Window (QDialog)
├── Toolbar (QToolBar)
│   ├── Font QComboBox
│   ├── Size QComboBox
│   ├── Style Dropdown (QToolButton + QMenu)
│   │   ├── Bold QAction
│   │   ├── Italic QAction
│   │   └── Underline QAction
│   ├── Color Dropdown (QToolButton + QMenu)
│   │   ├── Text Color QAction
│   │   └── Background Color QAction
│   ├── Alignment Dropdown (QToolButton + QMenu)
│   │   ├── Left QAction
│   │   ├── Center QAction
│   │   ├── Right QAction
│   │   └── Justify QAction
│   ├── Lists Dropdown (QToolButton + QMenu)
│   │   ├── Bullet List QAction
│   │   └── Numbered List QAction
│   └── Indent Dropdown (QToolButton + QMenu)
│       ├── Increase Indent QAction
│       └── Decrease Indent QAction
├── Notes Editor (QTextEdit)
│   └── Placeholder: "Enter your notes here..."
└── Button Box (QDialogButtonBox)
    ├── Save QPushButton
    └── Cancel QPushButton
```

## Reports Window (ReportsWindow)

### Window Structure
```
Reports Window (QDialog)
├── Toolbar (QToolBar)
│   ├── Bold QAction
│   ├── Italic QAction
│   ├── Underline QAction
│   ├── Separator
│   ├── Bullet List QAction
│   ├── Numbered List QAction
│   ├── Separator
│   ├── Load Template QAction
│   └── Peer Review Toggle (if enabled)
├── Report Editor (QTextEdit)
├── Button Box (QHBoxLayout)
│   ├── Export PDF QPushButton
│   ├── Finalize QPushButton
│   └── Close QPushButton
└── Hash Label: "PDF Hash: [hash]"
```

## Dialog Windows

### New Case Dialog
```
New Case Dialog (QDialog)
├── Form Layout
│   ├── Case Number QLineEdit (required)
│   ├── Suspect QLineEdit
│   ├── Investigator QLineEdit
│   ├── Agency QLineEdit
└── Button Box (Ok/Cancel)
```

### Add Evidence Dialog
```
Add Evidence Dialog (QDialog)
├── Form Layout
│   ├── Evidence Item Number QLineEdit (required)
│   ├── Type QComboBox (physical/digital)
│   ├── Physical Description QTextEdit (physical only)
│   ├── Password QLineEdit
│   ├── Make QLineEdit (digital only)
│   ├── Model QLineEdit (digital only)
│   ├── Digital Type QComboBox (digital only)
│   ├── SN# QLineEdit (digital only)
│   ├── Storage Size QLineEdit (digital only)
└── Button Box (Ok/Cancel)
```

### Add Legal Process Dialog
```
Add Legal Process Dialog (QDialog)
├── Form Layout
│   ├── Type QComboBox (preservation/subpoena/warrant)
│   ├── Provider QLineEdit (required)
│   ├── Submission Date QDateTimeEdit
│   ├── Due Date QDateTimeEdit (subpoena/warrant)
│   ├── Expiration Date QDateTimeEdit (preservation)
│   ├── Received Date QDateTimeEdit (warrant)
│   ├── Analysis Start Date QDateTimeEdit (subpoena/warrant)
│   ├── Completed Date QDateTimeEdit (subpoena)
│   ├── Notes QTextEdit
│   └── NDR QCheckBox (warrant only)
└── Button Box (Ok/Cancel)
```

### Add Lead Dialog
```
Add Lead Dialog (QDialog)
├── Form Layout
│   ├── Lead Name QLineEdit (required)
│   ├── Description QTextEdit
│   └── Source QLineEdit
└── Button Box (Ok/Cancel)
```

## Supporting Dialogs

### Status Color Dialog (StatusColorDialog)
```
Status Color Dialog (QDialog)
├── Status List (QListWidget)
├── Color Preview (QWidget)
├── Color Picker Buttons
│   ├── Background Color
│   └── Text Color
├── Bold QCheckBox
└── Button Box (Ok/Cancel)
```

### Glossary Dialog (GlossaryDialog)
```
Glossary Dialog (QDialog)
├── Search QLineEdit
├── Results QListWidget
├── Definition QTextEdit (read-only)
└── Button Box (Ok)
```

### Template Manager Dialog (TemplateManager)
```
Template Manager Dialog (QDialog)
├── Template List (QListWidget)
├── Preview QTextEdit (read-only)
├── Load QPushButton
├── Save QPushButton
├── Delete QPushButton
└── Button Box (Close)
```

## UI Interaction Flow

### Application Startup
1. Authentication dialog (if configured)
2. MainWindow displays with Dashboard tab
3. Cases load into dashboard table
4. Charts generate based on case data

### Case Management
1. Click case in dashboard → opens CaseTab
2. CaseTab shows dashboard metrics and sub-tabs
3. Evidence/Legal/Lead management through respective tables
4. Workflow progression through role-based buttons

### Document Editing
1. Open Notes/Reports from CaseTab
2. Rich text editing with toolbar controls
3. Auto-save or manual save operations
4. PDF export with hash generation

### View Switching
1. Select Investigator/Examiner from View menu
2. Dashboard columns adjust (Legal column visibility)
3. Case tabs update (hide/show Legal and Lead tabs)
4. Metrics labels adjust visibility

## Theme Integration
- All UI elements support theming through ThemeManager
- Charts adapt background colors based on theme
- Status colors configurable per theme
- Consistent styling across all dialogs and windows

## Accessibility Features
- Keyboard shortcuts for common actions
- High contrast theme support
- Tooltips on interactive elements
- Screen reader compatible labels

This hierarchical structure ensures intuitive navigation and role-appropriate functionality while maintaining forensic accountability through comprehensive audit logging.
