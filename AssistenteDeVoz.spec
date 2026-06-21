# -*- mode: python ; coding: utf-8 -*-
"""Configuração do PyInstaller (build em UMA pasta -> dist/AssistenteDeVoz/).

Coleta explicitamente os pacotes com dados/binários que o PyInstaller às vezes
não acha sozinho (DLL do PortAudio do sounddevice, certificados do certifi para
as chamadas HTTPS da Groq, etc.). O PySide6 é tratado pelo hook embutido do
PyInstaller.
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = [], [], []
for pkg in ("groq", "sounddevice", "pynput", "pyperclip", "platformdirs", "dotenv", "certifi"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += collect_submodules("assistente_voz")

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
    name="AssistenteDeVoz",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # app de janela/bandeja: sem console
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
    name="AssistenteDeVoz",
)
