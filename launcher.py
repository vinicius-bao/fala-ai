"""Ponto de entrada usado pelo PyInstaller (vira o AssistenteDeVoz.exe)."""

from assistente_voz.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
