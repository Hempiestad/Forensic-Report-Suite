# Notes Tab User Guide — FuDog Labs Forensic Report Suite

## Overview

The Notes Tab is a comprehensive note-taking and documentation tool within the Forensic Suite application. It provides rich text editing capabilities, timestamp management, multimedia support, and specialized forensic features like geo-lookup and voice-to-text transcription.

## Getting Started

### Opening the Notes Tab

The Notes Tab is accessible within each case file. To open notes for a specific case:

1. Open a case in the main application
2. Navigate to the Notes section
3. The notes interface will display with a tree view of existing notes on the left and the editor on the right

### Interface Layout

- **Notes Tree (Left Panel)**: Displays all notes for the current case
- **Note Editor (Right Panel)**: Rich text editor for creating and editing notes
- **Toolbar**: Quick access to formatting and common functions
- **Status Bar**: Shows statistics and information about the current note

## Basic Note Operations

### Creating a New Note

1. Click **File → Add New Note** or press `Ctrl+N`
2. Enter a name for the note
3. The new note will appear in the notes tree and open in the editor

### Editing Notes

- Click on any note in the notes tree to load it in the editor
- Type directly in the editor - changes are auto-saved
- Notes support rich text formatting (see Text Formatting section)

### Saving Notes

Notes are automatically saved when:
- You switch between notes
- The application detects changes
- You manually save via **File → Save** (`Ctrl+S`)

### Deleting Notes

Currently, notes can only be managed through the file system. To delete a note:
1. Close the notes window
2. Navigate to the case directory (`cases/{case_number}/notes/`)
3. Delete the corresponding entry from `notes_data.json`

## Text Formatting

### Basic Formatting

- **Bold**: `Ctrl+B` or use the Style dropdown
- **Italic**: `Ctrl+I` or use the Style dropdown
- **Underline**: `Ctrl+U` or use the Style dropdown
- **Strikethrough**: Available in Style dropdown
- **Subscript/Superscript**: Available in Style dropdown

### Font and Size

- **Font Family**: Select from the font dropdown in the toolbar
- **Font Size**: Choose from the size dropdown (8pt to 72pt)
- **Advanced Font Settings**: **Format → Font...** for complete font control

### Colors

- **Text Color**: **Format → Text Color...** or Color dropdown
- **Background Color**: **Format → Background Color...** or Color dropdown

### Alignment

- **Left Align**: Default alignment
- **Center**: **Format → Align Center**
- **Right Align**: **Format → Align Right**
- **Justify**: **Format → Justify**

### Lists

- **Bullet Lists**: **Format → Lists → Bullet List**
- **Numbered Lists**: **Format → Lists → Numbered List**

### Indentation

- **Increase Indent**: **Format → Indent → Increase Indent**
- **Decrease Indent**: **Format → Indent → Decrease Indent**

### Line and Paragraph Spacing

- **Line Spacing**: **Format → Line Spacing**
  - Single
  - 1.5 Lines
  - Double
- **Paragraph Spacing**: **Format → Paragraph Spacing**
  - No Spacing
  - Small
  - Medium
  - Large

### Advanced Formatting

- **Copy/Paste Formatting**: **Format → Copy/Paste Formatting** (`Ctrl+Shift+C/V`)
- **Clear Formatting**: **Format → Clear Formatting**

## Timestamp Management

### Inserting Timestamps

- **Local Format**: **Insert Timestamp** button or `Ctrl+Shift+T`
  - Format: `YYYY-MM-DD HH:MM:SS`
- **ISO Format**: `Ctrl+Alt+Shift+T`
  - Format: `YYYY-MM-DDTHH:MM:SS±HH:MM`

### Converting Timestamps

1. Select a timestamp in the text
2. Right-click → **Convert Selected Timestamp** or `Ctrl+Shift+C`
3. Choose target timezone and output format
4. The timestamp will be converted and replaced

Supported timezone abbreviations: PST, PDT, MST, MDT, CST, CDT, EST, EDT, AKST, AKDT, HST, UTC, GMT

## Templates

### Using Templates

1. **Edit → Load Template** or `Ctrl+T`
2. Select a template from the list
3. The template content will be inserted at the cursor position

### Inserting Templates via Context Menu

1. Right-click in the editor
2. Select **Insert Template**
3. Choose from available templates

### Relationship to Legal Template Library

Notes templates and legal-process templates are managed separately:

- Notes templates are for reusable note snippets in the Notes editor.
- Legal templates are managed from the main app under **Tools → Legal Template Library**.
- Legal templates are edited and finalized in the Reports editor.

## Tags and Links

### Adding Tags

1. Select text to tag
2. Right-click → **Tag / Label Selection**
3. Enter a tag name
4. The tag is associated with the current note

### Adding Links

1. **Edit → Add Link** or `Ctrl+L`
2. Enter a link to another note ID or entity
3. The link is stored with the current note

## Attachments

### Adding Attachments

1. **Edit → Add Attachment**
2. Select a file from your computer
3. The file is copied to the case notes directory
4. Attachments are tracked with SHA256 hashes for integrity

Supported file types: All file types are supported, with image preview for common formats

## Voice-to-Text

### Converting Speech to Text

1. **Tools → Voice to Text** or `Ctrl+V`
2. Speak clearly into your microphone
3. The transcribed text will be inserted at the cursor position

**Requirements**: SpeechRecognition library must be installed for offline transcription

## Geo Lookup

### Single Location Lookup

1. **Tools → Geo Lookup** → Select "Single"
2. Enter latitude and longitude coordinates
3. The system will attempt to reverse geocode the location
4. Choose to insert the address into your note

### Bulk Geo Lookup

1. **Tools → Geo Lookup** → Select "Bulk"
2. Select a CSV file with latitude/longitude columns
3. The system processes all coordinates
4. View results in a table and insert selected addresses

**Requirements**: Geopy library and internet connection for geocoding services

## Timeline Generation

### Creating Case Timelines

1. **Tools → Generate Timeline**
2. A visual timeline of all notes will be generated
3. The timeline is saved as an image in the case directory

**Requirements**: Matplotlib library for chart generation

## Search Functionality

### Searching Notes

1. Use the search box in the toolbar
2. Enter search terms
3. Matching notes will be highlighted in the notes tree

## Context Menu Features

Right-click in the note editor to access:

- **Insert Timestamp**: Quick timestamp insertion
- **Convert Selected Timestamp**: Convert highlighted timestamps
- **Insert Template**: Insert predefined templates
- **Create Task from Selection**: Create actionable tasks
- **Tag / Label Selection**: Add tags to selected text
- **Redact Selection**: Replace text with [REDACTED]
- **Create Calendar Event**: Schedule events from selected text
- **Export Selection**: Export selected text as HTML

## Tasks Management

### Creating Tasks

1. Select text in a note
2. Right-click → **Create Task from Selection**
3. Enter task description and due date
4. Tasks are stored and can be tracked

## Calendar Integration

### Creating Calendar Events

1. Select date-related text
2. Right-click → **Create Calendar Event from Selection**
3. Choose event type (hearing, trial, deposition, etc.)
4. Events are logged for manual calendar integration

## Export and Integration

### Exporting to Reports

1. **File → Export to Report**
2. Notes, entities, tasks, and attachments are exported as HTML
3. Content is inserted into the main report editor

### Working with Shared Legal Templates

When your team shares legal templates with you:

1. Open the legal template library from the main window.
2. Open a shared template in the report writer.
3. Copy required sections into your active report.
4. Keep case-specific facts in Notes, then export key sections into Reports.

### Exporting Selections

1. Select text in the editor
2. Right-click → **Export Selection...**
3. Save as HTML file

## Find and Replace

### Using Find/Replace

1. **Tools → Find and Replace** or `Ctrl+F`
2. Enter search term and replacement
3. Navigate through matches and replace as needed

## Inserting Media

### Images

1. **Insert → Image**
2. Select an image file
3. The image will be embedded in the note

### Tables

1. **Insert → Table**
2. Configure table properties
3. Insert advanced tables with the word processor

### Page Breaks

1. **Insert → Page Break**
2. Insert page break for printing/formatting

## Configuration

### Context Menu Settings

The availability of context menu items can be controlled via `config.json`:

```json
{
  "context_menu": {
    "notes": {
      "insert_timestamp": true,
      "convert_timestamp": true,
      "insert_template": true,
      "create_task": true,
      "tag": true,
      "redact": true,
      "create_calendar_event": true,
      "export_selection": true
    }
  }
}
```

### Timezone Configuration

Set your preferred timezone in `config.json`:

```json
{
  "timezone": "America/New_York"
}
```

## Keyboard Shortcuts

### File Operations
- `Ctrl+N`: New Note
- `Ctrl+S`: Save
- `Ctrl+W`: Close

### Editing
- `Ctrl+Z`: Undo
- `Ctrl+Y`: Redo
- `Ctrl+X`: Cut
- `Ctrl+C`: Copy
- `Ctrl+V`: Paste

### Formatting
- `Ctrl+B`: Bold
- `Ctrl+I`: Italic
- `Ctrl+U`: Underline
- `Ctrl+Shift+C`: Copy Formatting
- `Ctrl+Shift+V`: Paste Formatting

### Timestamps
- `Ctrl+Shift+T`: Insert Local Timestamp
- `Ctrl+Alt+Shift+T`: Insert ISO Timestamp
- `Ctrl+Shift+C`: Convert Selected Timestamp

### Tools
- `Ctrl+F`: Find and Replace
- `Ctrl+T`: Load Template
- `Ctrl+G`: Add Tag
- `Ctrl+L`: Add Link
- `Ctrl+V`: Voice to Text
- `Ctrl+Shift+G`: Geo Lookup

## Data Storage

### File Structure

Notes are stored in the case directory:
```
cases/{case_number}/notes/
├── notes_data.json    # Note content and metadata
├── timeline.png       # Generated timeline images
└── attachments/       # Attached files
```

### Data Integrity

- All notes include SHA256 hashes for content verification
- Changes are logged in the audit trail
- Attachments are hashed for integrity checking

## Troubleshooting

### Common Issues

**Voice-to-Text Not Working**
- Ensure SpeechRecognition library is installed
- Check microphone permissions
- Try using offline recognition (CMU Sphinx)

**Geo Lookup Failing**
- Verify internet connection
- Check Geopy library installation
- Ensure coordinates are in decimal format

**Templates Not Loading**
- Check templates.py file exists
- Verify template files are accessible

**Timeline Not Generating**
- Install Matplotlib library
- Ensure notes have valid timestamps

### Performance Tips

- Large attachments may slow down loading
- Bulk geo lookups require internet connection
- Voice recognition works best in quiet environments
- Regular saving prevents data loss

## Security Features

- All changes are logged in the audit trail
- Content hashing ensures data integrity
- Redaction tools for sensitive information
- Secure file handling for attachments

---

## Related Documentation

- [README](README.md) — Project overview and quick start
- [Main Application User Guide](MAIN_USER_GUIDE.md) — Dashboard, menus, and case management
- [Reports Tab User Guide](REPORTS_USER_GUIDE.md) — PDF report authoring and appendices
- [Legal Workflow Guide](LEGAL_WORKFLOW_GUIDE.md) — Legal process approval stages
- [Installation Guide](INSTALLATION_GUIDE.md) — Installation and configuration

