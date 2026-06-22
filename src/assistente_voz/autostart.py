"""Iniciar com o Windows (chave Run do registro). No-op fora do Windows."""

from __future__ import annotations

import sys

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE = "FalaAI"


def set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        if enabled:
            winreg.SetValueEx(key, _VALUE, 0, winreg.REG_SZ, _launch_command())
        else:
            try:
                winreg.DeleteValue(key, _VALUE)
            except FileNotFoundError:
                pass


def _launch_command() -> str:
    if getattr(sys, "frozen", False):  # empacotado com PyInstaller
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m assistente_voz'
