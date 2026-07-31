# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller (build em UMA pasta -> dist/FalaAI/).

Empacota os assets (logo/ícone), coleta DLLs/dados que às vezes não são achados
sozinhos (PortAudio do sounddevice, certificados do certifi) e usa
assets/icon.ico como ícone do .exe quando existir.
"""

import os

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []
for pkg in ("groq", "openai", "sounddevice", "pynput", "pyperclip", "platformdirs", "dotenv", "certifi"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules("assistente_voz")
hiddenimports += ["PySide6.QtSvg", "PySide6.QtNetwork"]

# Inclui a pasta assets/ no app empacotado.
if os.path.isdir("assets"):
    for _f in os.listdir("assets"):
        _p = os.path.join("assets", _f)
        if os.path.isfile(_p):
            datas.append((_p, "assets"))

_ico = os.path.join("assets", "icon.ico")
_icon = _ico if os.path.isfile(_ico) else None

a = Analysis(
    ["launcher.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FalaAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FalaAI",
)
