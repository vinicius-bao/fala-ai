"""Renderiza a interface em PNG (headless) para conferir o visual sem abrir o app.

Requer PySide6 instalado.  Uso:
    QT_QPA_PLATFORM=offscreen python tools/render_ui.py [pasta_de_saida]

Gera: main_dark.png, main_light.png, settings_dark.png e os 3 estados do pop-up.
"""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from assistente_voz.app import Controller  # noqa: E402
from assistente_voz.config import Config  # noqa: E402
from assistente_voz.history import History, Transcription  # noqa: E402
from assistente_voz.overlay import RecordingOverlay  # noqa: E402
from assistente_voz.theme import apply_theme  # noqa: E402
from assistente_voz.ui import MainWindow  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "ui-preview")
os.makedirs(OUT, exist_ok=True)

app = QApplication([])
history = History(path=None, max_size=50)
for sample in (
    "primeira transcrição de exemplo para conferir o cartão do histórico",
    "segunda transcrição, um pouco mais longa, para validar a elisão do texto",
):
    history.add(Transcription.create(sample, 2.5, "groq:whisper-large-v3"))
controller = Controller(Config(), history)


def shot(name: str, mode: str, tab: int = 0) -> None:
    apply_theme(app, mode)
    win = MainWindow(controller)
    win.resize(620, 660)
    win.centralWidget().layout().itemAt(2).widget().setCurrentIndex(tab)
    win.show()
    app.processEvents()
    app.processEvents()
    win.grab().save(os.path.join(OUT, name))
    print("gerado", name)
    win.close()


shot("main_dark.png", "dark", 0)
shot("main_light.png", "light", 0)
shot("settings_dark.png", "dark", 1)

apply_theme(app, "dark")
overlay = RecordingOverlay(lambda: 0.6)
for name, action in (
    ("overlay_recording.png", lambda: overlay.show_recording()),
    ("overlay_processing.png", lambda: overlay.show_processing()),
    ("overlay_done.png", lambda: overlay.show_done()),
):
    action()
    for _ in range(20):
        overlay._tick_wave()
    app.processEvents()
    overlay.grab().save(os.path.join(OUT, name))
    print("gerado", name)

print("saída em", OUT)
