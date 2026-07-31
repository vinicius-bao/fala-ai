"""Ponto de entrada: `python -m assistente_voz` ou o script `assistente-voz`."""

from __future__ import annotations

import sys

_WIN_MUTEX = None  # mantém o mutex vivo enquanto o app roda


def main() -> int:
    # Identidade do app no Windows (taskbar/ícone agrupam corretamente) e um
    # mutex nomeado, que o instalador usa para detectar o app aberto e fechá-lo
    # antes de atualizar (AppMutex do Inno Setup).
    global _WIN_MUTEX
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FalaAI")
            _WIN_MUTEX = ctypes.windll.kernel32.CreateMutexW(
                None, False, "FalaAI-SingleInstance-Mutex"
            )
        except Exception:
            pass

    import logging

    from .logs import setup_logging

    setup_logging()
    from . import __version__

    logging.getLogger("falaai").info("Fala AI %s iniciando", __version__)

    from dotenv import load_dotenv

    load_dotenv()  # carrega GROQ_API_KEY do .env, se existir

    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from .app import Controller
    from .config import config_dir, load_config
    from .history import History
    from .overlay import RecordingOverlay
    from .resources import app_icon
    from .theme import apply_theme
    from .ui import MainWindow, TrayApp

    app = QApplication(sys.argv)
    app.setApplicationName("Fala AI")
    app.setQuitOnLastWindowClosed(False)  # vive na bandeja
    app.setWindowIcon(app_icon())

    # Instância única: se já houver um Fala AI rodando, manda ele aparecer e sai.
    ipc_name = "FalaAI-SingleInstance"
    probe = QLocalSocket()
    probe.connectToServer(ipc_name)
    if probe.waitForConnected(300):
        probe.write(b"show")
        probe.flush()
        probe.waitForBytesWritten(500)
        probe.disconnectFromServer()
        return 0
    QLocalServer.removeServer(ipc_name)  # limpa socket órfão de um crash
    instance_server = QLocalServer()
    instance_server.listen(ipc_name)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Erro", "Bandeja do sistema indisponível.")
        return 1

    cfg = load_config()
    history = History(config_dir() / "history.json", max_size=cfg.history_size)
    controller = Controller(cfg, history)

    # Tema: aplica conforme o modo (auto/claro/escuro) e reage a mudanças.
    def _apply_theme() -> None:
        apply_theme(app, controller.config.theme_mode)

    _apply_theme()
    try:
        app.styleHints().colorSchemeChanged.connect(lambda *_: _apply_theme())
    except Exception:
        pass
    controller.configApplied.connect(_apply_theme)

    window = MainWindow(controller)
    TrayApp(controller, window)
    controller.quitRequested.connect(app.quit)

    overlay = RecordingOverlay(controller.current_level)
    overlay.stopRequested.connect(controller.stop_recording)
    overlay.cancelRequested.connect(controller.cancel_recording)

    def _on_overlay(state: str, text: str) -> None:
        if state == "recording":
            overlay.show_recording()
        elif state == "processing":
            overlay.show_processing(text or "Transcrevendo…")
        elif state == "done":
            overlay.show_done(text or "Colado ✓")
        else:
            overlay.hide_overlay()

    controller.overlayState.connect(_on_overlay)

    def _activate_window() -> None:
        conn = instance_server.nextPendingConnection()
        if conn is not None:
            conn.close()
        window.showNormal()
        window.raise_()
        window.activateWindow()

    instance_server.newConnection.connect(_activate_window)
    controller.start()

    # Verifica atualizações alguns segundos após iniciar (se configurado).
    from .config import resolve_update_repo

    if cfg.check_updates_on_start and resolve_update_repo(cfg):
        QTimer.singleShot(3000, lambda: controller.check_updates(manual=False))

    window.show()  # primeira execução mostra a janela; feche-a para a bandeja
    if not cfg.onboarding_done:
        QTimer.singleShot(300, window.show_welcome)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
