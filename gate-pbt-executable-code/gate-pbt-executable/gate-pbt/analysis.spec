# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all
import os

hiddenimports = collect_submodules('itk')
# collect_data_files includes .py, .pyi, .pyd, etc. with relative folder paths
itk_datas = collect_data_files('itk', include_py_files=True)

# Sweep the whole of scipy. PyInstaller's built-in scipy hook misses several
# dynamically-loaded extension modules (_arpack, _propack, unuran_wrapper,
# _highs, givens_elimination, _traversal), which fail at import time with a
# misleading "circular import" error. Returns (datas, binaries, hiddenimports).
scipy_datas, scipy_binaries, scipy_hidden = collect_all('scipy')

a = Analysis(
    ['analysis\\analysis.py'],
    binaries=scipy_binaries,
    datas=itk_datas + scipy_datas,
    hiddenimports=hiddenimports + scipy_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    pathex=[os.path.abspath('.')],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='analysis',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='analysis',
)