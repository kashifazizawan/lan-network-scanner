# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for LAN Network Scanner (Windows one-file build)."""

import sys
from PyInstaller.utils.hooks import collect_submodules

import os

block_cipher = None

# Use a custom icon only if one exists; otherwise PyInstaller uses its default.
icon_path = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "openpyxl",
    "reportlab.lib",
    "reportlab.platypus",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=[("sample_data", "sample_data")],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "PySide6.QtWebEngineCore"],
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
    name="LanScanner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app: no console window on Windows
    icon=icon_path,         # assets/icon.ico if present, else PyInstaller default
)
