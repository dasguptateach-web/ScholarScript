# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\81\\ScholarScript\\ScholarScriptApp\\assets\\icon.ico', 'assets'), ('C:\\Users\\81\\ScholarScript\\ScholarScriptApp\\scholarscript', 'scholarscript')]
binaries = []
hiddenimports = ['docx', 'pdfplumber', 'jinja2', 'PIL', 'docx.oxml.ns', 'lxml', 'pdfplumber.page']
tmp_ret = collect_all('scholarscript')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Users\\81\\ScholarScript\\ScholarScriptApp\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ScholarScriptPortable',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\81\\ScholarScript\\ScholarScriptApp\\assets\\icon.ico'],
)
