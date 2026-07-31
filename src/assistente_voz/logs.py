"""Log em arquivo, para diagnosticar problemas relatados por quem usa o app.

Grava em <config>/logs/falaai.log com rotação (nada de arquivo gigante) e
registra também exceções não tratadas.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"
_MAX_BYTES = 512 * 1024
_BACKUPS = 3


def log_dir() -> Path:
    from .config import config_dir

    d = config_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_file() -> Path:
    return log_dir() / "falaai.log"


def setup_logging(level: int = logging.INFO) -> Path:
    """Configura o log em arquivo. Devolve o caminho do arquivo."""
    path = log_file()
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, RotatingFileHandler) for h in root.handlers):
        handler = RotatingFileHandler(
            path, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(handler)

    def _hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logging.getLogger("falaai").critical(
            "Erro não tratado", exc_info=(exc_type, exc, tb)
        )

    sys.excepthook = _hook
    return path


def open_log_folder() -> None:
    """Abre a pasta de logs no explorador de arquivos."""
    import os
    import subprocess
    import webbrowser

    d = str(log_dir())
    try:
        if sys.platform == "win32":
            os.startfile(d)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", d])
        else:
            webbrowser.open(f"file://{d}")
    except Exception:  # noqa: BLE001
        logging.getLogger("falaai").warning("Não consegui abrir a pasta de logs")
