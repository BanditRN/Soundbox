# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\Git Soundbox\\Soundbox-1\\app.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Git Soundbox\\Soundbox-1\\close.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\down.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\minimize.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\pause.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\play.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\reload.png', '.'), ('D:\\Git Soundbox\\Soundbox-1\\splashscreen.gif', '.'), ('D:\\Git Soundbox\\Soundbox-1\\stop.webp', '.'), ('D:\\Git Soundbox\\Soundbox-1\\window_icon.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=2,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [('O', None, 'OPTION'), ('O', None, 'OPTION')],
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
    icon=['D:\\Git Soundbox\\Soundbox-1\\window_icon.ico'],
    hide_console='hide-early',
)
