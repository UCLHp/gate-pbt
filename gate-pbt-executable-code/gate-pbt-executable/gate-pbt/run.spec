# -*- mode: python ; coding: utf-8 -*-


from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

hiddenimports = collect_submodules('itk')
itk_datas = collect_data_files('itk', include_py_files=True)
scipy_datas, scipy_binaries, scipy_hidden = collect_all('scipy')

a = Analysis(
    ['simulation\\run.py'],
    binaries=scipy_binaries,
    datas=itk_datas + scipy_datas + [('templates', 'templates')],
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
    name='run',
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
    name='run',
)
