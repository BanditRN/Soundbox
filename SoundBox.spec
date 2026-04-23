# -*- mode: python ; coding: utf-8 -*-
import os

project_root = os.path.abspath(SPECPATH)
resources_dir = os.path.join(project_root, 'resources')

resource_files = []
if os.path.isdir(resources_dir):
    for fname in os.listdir(resources_dir):
        full = os.path.join(resources_dir, fname)
        if os.path.isfile(full):
            resource_files.append((full, '.'))

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=resource_files,
    hiddenimports=[
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'unittest',
        'pydoc',
        'doctest',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SoundBox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(resources_dir, 'window_icon.ico'),
    hide_console='hide-early',
)
