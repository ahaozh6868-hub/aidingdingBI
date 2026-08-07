# -*- mode: python -*-
"""PyInstaller spec for PMS Sync Panel (Single EXE)"""
import os; from PyInstaller.utils.hooks import collect_data_files, collect_submodules

a = Analysis(
    ['panel.py'],
    pathex=[os.path.dirname(os.path.abspath(__file__))],
    binaries=[],
    datas=[('pms_sync.py', '.')] + collect_data_files('certifi'),
    hiddenimports=['certifi','certifi.core','ssl','json','argparse','urllib','urllib.request','urllib.error','urllib.parse','subprocess','datetime','sys','os','logging','logging.handlers','traceback','time','io','http.server','webbrowser'] + collect_submodules('certifi'),
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    win_no_prefer_redirects=False, win_private_assemblies=False, cipher=None, noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=None)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='pms_panel', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None, icon=None,
)
