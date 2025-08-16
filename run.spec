# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo, FixedFileInfo, StringFileInfo,
    StringStruct, VarFileInfo, VarStruct, StringTable
)

# Version info
version = "0.2.0"
vs = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(0,2,0,0),
        prodvers=(0,2,0,0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0,0)
    ),
    kids=[StringFileInfo([StringTable('040904B0', [
        StringStruct('CompanyName', 'Ullas'),
        StringStruct('FileDescription', 'LocVi – Local File Viewer'),
        StringStruct('FileVersion', version),
        StringStruct('InternalName', 'LocVi'),
        StringStruct('OriginalFilename', 'LocVi.exe'),
        StringStruct('ProductName', 'LocVi'),
        StringStruct('ProductVersion', version),
        StringStruct('LegalCopyright', '© 2025 Ullas. MIT License'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
    ]
)

# --------------------------
# Paths
# --------------------------
spec_dir = os.path.abspath(".")
icon_path = os.path.join(spec_dir, 'assets', 'icons', 'icon-ico.ico')
# IMPORTANT: Use the correct path to your global Python DLL
python_dll_path = 'C:\\Users\\ullas\\AppData\\Local\\Programs\\Python\\Python313\\python313.dll'

# --------------------------
# Analysis
# --------------------------
a = Analysis(
    ['run.py'],
    pathex=[spec_dir],
    binaries=[
        # Explicitly add the Python DLL from its correct location
        (python_dll_path, '.'),
    ],
    datas=[
        # Add your data files
        (os.path.join(spec_dir, 'app', 'templates'), 'app/templates'),
        (os.path.join(spec_dir, 'app', 'static'), 'app/static')
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# --------------------------
# PYZ
# --------------------------
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# --------------------------
# EXE - Configured for One-File Mode
# --------------------------
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,  # Include the binaries from the analysis step
    a.datas,     # Include the data files
    name='LocVi.exe',
    debug=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
    version=vs,
    # This ensures a single executable file is created
    # The 'onedir' flag is false by default if 'collect' is not used
    # This also means we don't need a separate 'COLLECT' object.
)
