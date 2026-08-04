# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PMS Sync Tool (Windows .exe)
在 Windows 上运行: pyinstaller pms_sync.spec --clean --noconfirm
"""
import os, sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# 收集 certifi 证书文件（SSL 必需）
certifi_datas = collect_data_files('certifi')

# 收集 certifi 子模块
certifi_hidden = collect_submodules('certifi')

a = Analysis(
    ['pms_sync.py'],
    pathex=[],
    binaries=[],
    datas=certifi_datas + [
        # 确保 certifi cacert.pem 被正确打包
    ],
    hiddenimports=[
        'certifi', 'certifi.core',
        'ssl', 'json', 'argparse',
        'urllib', 'urllib.request', 'urllib.error', 'urllib.parse',
        'subprocess', 'datetime', 'sys', 'os',
        'logging', 'logging.handlers',
        'traceback', 'time', 'io',
    ] + certifi_hidden,
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
    name='pms_sync',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 显示控制台窗口，方便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
