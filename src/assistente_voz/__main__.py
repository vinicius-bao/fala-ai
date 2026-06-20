"""Ponto de entrada: `python -m assistente_voz` ou o script `assistente-voz`."""

from __future__ import annotations

import sys


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv()  # carrega GROQ_API_KEY do .env, se existir

    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from .app import Controller
    from .config import config_dir, load_config
    from .history import History
    from .ui import MainWindow, TrayApp

    app = QApplication(sys.argv)
    app.setApplicationName("Assistente de Voz")
    app.setQuitOnLastWindowClosed(False)  # vive na bandeja

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Erro", "Bandeja do sistema indisponível.")
        return 1

    cfg = load_config()
    history = History(config_dir() / "history.json", max_size=cfg.history_size)
    controller = Controller(cfg, history)
    window = MainWindow(controller)
    TrayApp(controller, window)
    controller.start()

    window.show()  # primeira execução mostra a janela; feche-a para a bandeja
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
