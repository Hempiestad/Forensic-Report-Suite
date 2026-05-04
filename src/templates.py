# templates.py
import json
import os
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QListWidget, QMessageBox, QInputDialog

TEMPLATES_FILE = "templates.json"

DEFAULT_TEMPLATES = {
    "SWGDE/NIST Standard": """
<h1>Digital Forensic Examination Report</h1>

<h2>1. Executive Summary</h2>
<p>[Brief overview of key findings and conclusions]</p>

<h2>2. Case Information</h2>
<p>Case Number: {case_number}<br>
Suspect: {suspect}<br>
Investigator: {investigator}<br>
Agency: {agency}<br>
Date of Report: {date}</p>

<h2>3. Scope of Examination</h2>
<p>[Define objectives, limitations, and authorized actions]</p>

<h2>4. Evidence Items Received</h2>
<table border="1" cellpadding="5">
<tr><th>Item ID</th><th>Description</th><th>Make/Model</th><th>Serial/IMEI</th><th>Hash (Acquisition)</th></tr>
<tr><td></td><td></td><td></td><td></td><td></td></tr>
</table>

<h2>5. Methodology and Tools Used</h2>
<p>[Describe acquisition, examination methods, tools and versions]</p>

<h2>6. Findings and Analysis</h2>
<p>[Detailed technical findings]</p>

<h2>7. Conclusions</h2>
<p>[Interpretation and significance of findings]</p>

<h2>8. Appendices</h2>
<p>[List of attached files and glossary footnotes]</p>

<h2>9. References</h2>
<p>[Sources and glossary terms]</p>
    """.strip(),

    "Basic Template": """
<h1>Forensic Report</h1>
<h2>Summary</h2><p></p>
<h2>Findings</h2><p></p>
<h2>Conclusion</h2><p></p>
    """.strip()
}

def load_templates():
    if os.path.exists(TEMPLATES_FILE):
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_TEMPLATES

def save_templates(templates):
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=4)

class TemplateManager(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Report Templates")
        self.setMinimumSize(800, 600)
        layout = QVBoxLayout(self)

        self.list = QListWidget()
        self.templates = load_templates()
        for name in self.templates:
            self.list.addItem(name)
        layout.addWidget(self.list)

        btn_layout = QVBoxLayout()
        QPushButton("Load Selected into Editor", clicked=self.load_to_editor).setParent(self)
        QPushButton("Edit Selected", clicked=self.edit_template).setParent(self)
        QPushButton("Add New Template", clicked=self.add_template).setParent(self)
        QPushButton("Delete Selected", clicked=self.delete_template).setParent(self)
        for btn in self.findChildren(QPushButton):
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

        self.parent_editor = parent.editor if parent else None

    def load_to_editor(self):
        if not self.parent_editor:
            QMessageBox.warning(self, "Error", "No editor available.")
            return
        item = self.list.currentItem()
        if item:
            name = item.text()
            html = self.templates[name]
            # Replace placeholders
            case = self.parent().case_data if hasattr(self.parent(), 'case_data') else {}
            html = html.format(
                case_number=case.get('case_number', ''),
                suspect=case.get('suspect', 'N/A'),
                investigator=case.get('investigator', ''),
                agency=case.get('agency', ''),
                date=datetime.now().strftime('%B %d, %Y')
            )
            self.parent_editor.setHtml(html)
            self.accept()

    def edit_template(self):
        item = self.list.currentItem()
        if item:
            name = item.text()
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Edit Template: {name}")
            layout = QVBoxLayout(dlg)
            editor = QTextEdit()
            editor.setHtml(self.templates[name])
            layout.addWidget(editor)
            save_btn = QPushButton("Save Changes")
            save_btn.clicked.connect(lambda: self.save_edit(name, editor.toHtml(), dlg))
            layout.addWidget(save_btn)
            dlg.exec_()

    def save_edit(self, name, html, dlg):
        self.templates[name] = html
        save_templates(self.templates)
        QMessageBox.information(self, "Saved", f"Template '{name}' updated.")
        dlg.accept()

    def add_template(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template Name:")
        if ok and name:
            self.templates[name] = "<h1>New Template</h1><p>Edit me...</p>"
            save_templates(self.templates)
            self.list.addItem(name)

    def delete_template(self):
        item = self.list.currentItem()
        if item:
            name = item.text()
            if QMessageBox.question(self, "Delete", f"Delete template '{name}'?") == QMessageBox.Yes:
                del self.templates[name]
                save_templates(self.templates)
                self.list.takeItem(self.list.row(item))

    def list_templates(self):
        """Return list of available template names"""
        return list(self.templates.keys())

    def render(self, template_name, context=None):
        """Render a template with optional context data
        
        Args:
            template_name: Name of the template to render
            context: Optional dict with placeholder values
        
        Returns:
            Rendered HTML string
        """
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        html = self.templates[template_name]
        
        # Apply context if provided
        if context:
            try:
                html = html.format(**context)
            except KeyError as e:
                # If some placeholders are missing, that's okay - leave them as is
                pass
        
        return html