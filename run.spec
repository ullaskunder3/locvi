# run.spec
# generated for PyInstaller with VSVersionInfo metadata
import os
import sys
from PyInstaller.utils.win32.versioninfo import (VSVersionInfo, FixedFileInfo,
    StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct)

version = "0.2.0"   # update this every release

# Windows VERSIONINFO details
vs = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=(0, 2, 0, 0),
        prodvers=(0, 2, 0, 0),
        mask=0x3f,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0)
    ),
    kids=[
        StringFileInfo([StringTable('040904B0', [
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

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[('app/templates','app/templates'), ('app/static','app/static')],
    hiddenimports=[],
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LocVi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icons/icon-ico.ico',
    version=vs  # embed version info
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='LocVi'
)
