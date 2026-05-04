# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_submodules, collect_dynamic_libs

block_cipher = None

base_path = os.path.abspath(os.getcwd())
src_path = os.path.join(base_path, 'src')

hiddenimports = [
    # Core PyQt5 modules
    "PyQt5.sip",
    "PyQt5.QtWidgets",
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    
    # Application modules (explicitly include all custom modules)
    "database",
    "case_tab",
    "notes_tab",
    "reports_tab",
    "glossary",
    "glossary_assist",
    "accessibility",
    "auth",
    "status_color_dialog",
    "bug_report",
    "feature_request",
    "logging_config",
    "notification_manager",
    "notification_settings",
    "notifications_panel",
    "dashboard_chart_settings",
    "status_validator",
    "validators",
    "password_utils",
    "peer_review",
    "peer_review_portable",
    "templates",
    "security",
    "secure_key_manager",
    "audit_log",
    "base_editor",
    "word_processor",
    "archived_cases_dialog",
    "archive_case_dialog",
    
    # Third-party dependencies
    "weasyprint",
    "pyqtgraph",
    "pandas",
    "openpyxl",
    "html2text",
    "enchant",
    "ldap3",
    "cryptography",
    "argon2",
    "bcrypt",
    "_cffi_backend",  # Critical for bcrypt
    "keyring",
    "requests",
    
    # Optional dependencies (include if available)
    "geopy",
    "networkx",
    "matplotlib",
    "matplotlib.pyplot",
]

hiddenimports += collect_submodules("PyQt5")
hiddenimports += collect_submodules("weasyprint")
hiddenimports += collect_submodules("cryptography")
hiddenimports += collect_submodules("bcrypt")

# Collect bcrypt and other binary files
binaries = []
binaries += collect_dynamic_libs('bcrypt')
binaries += collect_dynamic_libs('cryptography')
binaries += collect_dynamic_libs('_cffi_backend')

# Data files to include
_datas = [
    (os.path.join(base_path, "config.json"), "."),
    (os.path.join(base_path, "docs", "*.md"), "docs"),  # Documentation
    (os.path.join(base_path, "assets", "FuDog Labs.png"), "assets"),  # Splash screen logo
    (os.path.join(base_path, "assets"), "assets"),  # All assets
    (os.path.join(base_path, "themes"), "themes"),  # QSS themes
]

# Exclude server and tests from client build
_excludes = [
    "tests",
    "server.py",
    "__pycache__",
]

analysis = Analysis(
    [os.path.join(base_path, "main.py")],
    pathex=[base_path, src_path],
    binaries=binaries,
    datas=_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=_excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name="ForensicReportWriter",
    icon=os.path.join(base_path, "assets", "forensic_client.ico"),
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ForensicReportWriter",
)
