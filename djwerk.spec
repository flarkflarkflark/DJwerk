# -*- mode: python ; coding: utf-8 -*-
import os
import platform
import customtkinter

# Find customtkinter path to include its theme files
ctk_path = os.path.dirname(customtkinter.__file__)

block_cipher = None

# Assets to include
datas = [
    (ctk_path, 'customtkinter'),
    ('models', 'models'),
    ('library_db.json', '.'),
]

# Optional icons (if they exist)
if os.path.exists('assets/icon.ico'):
    icon_file = 'assets/icon.ico'
elif os.path.exists('assets/icon.png'):
    icon_file = 'assets/icon.png'
else:
    icon_file = None

a = Analysis(
    ['main.py'],
    pathex=[os.path.abspath(os.curdir)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'PIL._tkinter_finder', 
        'customtkinter', 
        'yt_dlp',
        'djwerk_gui',
        'djwerk_core',
        'djwerk_controller',
        'djwerk_matcher',
        'universal_db',
        'engine_db_handler',
        'rekordbox_xml',
        'bandcamp_api_handler',
        'spotify_api_handler',
        'tidal_api_handler',
        'engine_integrity',
        'crate_health',
        'send_report',
        'models',
        'models.config',
        'models.track'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DJwerk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get('DJWERK_ARCH') if platform.system() == 'Darwin' else None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
)

# For macOS .app bundle
if platform.system() == 'Darwin':
    app = BUNDLE(
        exe,
        name='DJwerk.app',
        icon=icon_file if icon_file and icon_file.endswith('.icns') else None,
        bundle_identifier='com.djwerk.app',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'LSMinimumSystemVersion': '10.15.0',
        },
    )
