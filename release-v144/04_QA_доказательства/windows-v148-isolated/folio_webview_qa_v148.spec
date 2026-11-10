# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from pathlib import Path

root = Path(r"C:\Users\Windows-10\Desktop\Портфолио_веб-разработчика")
datas = [(str(root / 'web'), 'web')]
binaries = []
hiddenimports = []
for package in ('webview', 'pythonnet', 'clr_loader'):
    collected = collect_all(package)
    datas += collected[0]
    binaries += collected[1]
    hiddenimports += collected[2]

analysis = Analysis(
    [str(root / 'служебные_файлы' / 'qa_05-11-2026' / 'windows-v148-isolated' / 'folio_webview_qa_v148.py')],
    pathex=[str(root)],
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
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name='folio-webview-v148-qa',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=True, name='folio-webview-v148-qa')
