# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for BunnyScriber.

Build with: pyinstaller bunnyscriber.spec
"""

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('pics', 'pics'),
    ],
    hiddenimports=[
        'bunnyscriber',
        'bunnyscriber.app',
        'bunnyscriber.config',
        'bunnyscriber.constants',
        'bunnyscriber.progress',
        'bunnyscriber.audio_utils',
        'bunnyscriber.pipeline',
        'bunnyscriber.separator',
        'bunnyscriber.transcriber',
        'bunnyscriber.reassembler',
        'bunnyscriber.cleanup',
        'bunnyscriber.backends',
        'bunnyscriber.backends.base',
        'bunnyscriber.backends.whisper_local',
        'bunnyscriber.backends.openai_api',
        'bunnyscriber.backends.groq_api',
        'bunnyscriber.backends.mistral_api',
        'bunnyscriber.backends.custom',
        'PyQt6',
        'PyQt6.QtWidgets',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'pydub',
        'numpy',
        'requests',
        'openai',
        'docx',
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
    [],
    exclude_binaries=True,
    name='BunnyScriber',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BunnyScriber',
)
