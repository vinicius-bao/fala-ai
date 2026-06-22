"""Ponto de entrada: `python -m assistente_voz` ou o script `assistente-voz`."""

from __future__ import annotations

import sys


def main() -> int:
    # Identidade do app no Windows (taskbar/ícone agrupam corretamente).
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FalaAI")
        except Exception:
            pass

    from dotenv import load_dotenv

    load_dotenv()  # carrega GROQ_API_KEY do .env, se existir

    from PySide6.QtCore import QSharedMemory, Qt, QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from .app import Controller
    from .config import config_dir, load_config
    from .history import History
    from .resources import app_icon
    from .theme import DARK, LIGHT, build_qss
    from .ui import MainWindow, TrayApp

    app = QApplication(sys.argv)
    app.setApplicationName("Fala AI")
    app.setQuitOnLastWindowClosed(False)  # vive na bandeja
    app.setWindowIcon(app_icon())

    # Instância única: evita 2+ Fala AI rodando e colando o texto várias vezes.
    lock = QSharedMemory("FalaAI-SingleInstance-v1")
    if not lock.create(1):
        QMessageBox.information(
            None,
            "Fala AI",
            "O Fala AI já está em execução. Veja o ícone na bandeja, perto do relógio.",
        )
        return 0

    # Tema automático: segue o claro/escuro do Windows e reage a mudanças.
    hints = app.styleHints()

    def _apply_theme() -> None:
        try:
            dark = hints.colorScheme() == Qt.ColorScheme.Dark
        except Exception:  # versões antigas do Qt: assume claro
            dark = False
        app.setStyleSheet(build_qss(DARK if dark else LIGHT))

    _apply_theme()
    try:
        hints.colorSchemeChanged.connect(lambda *_: _apply_theme())
    except Exception:
        pass

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Erro", "Bandeja do sistema indisponível.")
        return 1

    cfg = load_config()
    history = History(config_dir() / "history.json", max_size=cfg.history_size)
    controller = Controller(cfg, history)
    window = MainWindow(controller)
    TrayApp(controller, window)
    controller.quitRequested.connect(app.quit)
    controller.start()

    # Verifica atualizações alguns segundos após iniciar (se configurado).
    from .config import resolve_update_repo

    if cfg.check_updates_on_start and resolve_update_repo(cfg):
        QTimer.singleShot(3000, lambda: controller.check_updates(manual=False))

    window.show()  # primeira execução mostra a janela; feche-a para a bandeja
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
