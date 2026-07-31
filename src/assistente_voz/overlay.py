"""Sobreposição flutuante (pop-up) no centro inferior da tela.

Mostra: gravando (onda de voz reagindo ao microfone) → processando (barra) →
concluído ("Colado ✓"), sumindo em seguida. Não rouba o foco de quem digita.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTime, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

_GRAD = ((0xBD, 0x61, 0x9D), (0xB4, 0x8B, 0xB9), (0xFB, 0xB0, 0x3B))


def _badge(icon_name: str, color: str, size: int = 26) -> QPixmap:
    """Círculo colorido com um ícone branco no meio."""
    from . import icons

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QRectF(0, 0, size, size))
    glyph = size * 0.62
    p.translate((size - glyph) / 2, (size - glyph) / 2)
    icons.draw(icon_name, p, glyph, QColor("#FFFFFF"))
    p.end()
    return pm


def _grad_color(t: float) -> QColor:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        a, b, f = _GRAD[0], _GRAD[1], t / 0.5
    else:
        a, b, f = _GRAD[1], _GRAD[2], (t - 0.5) / 0.5
    return QColor(
        int(a[0] + (b[0] - a[0]) * f),
        int(a[1] + (b[1] - a[1]) * f),
        int(a[2] + (b[2] - a[2]) * f),
    )


class _WaveBars(QWidget):
    def __init__(self, n: int = 17, parent=None):
        super().__init__(parent)
        self._n = n
        self._levels = self._idle()
        self.setFixedSize(n * 8, 30)

    def _idle(self) -> list[float]:
        import math

        return [0.12 + 0.06 * math.sin(i * 0.9) for i in range(self._n)]

    def push(self, level: float) -> None:
        self._levels = self._levels[1:] + [max(0.10, min(1.0, level))]
        self.update()

    def reset(self) -> None:
        self._levels = self._idle()
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        w = self.width() / self._n
        barw = w * 0.42
        height = self.height()
        for i, lv in enumerate(self._levels):
            h = max(3.0, lv * height)
            x = i * w + (w - barw) / 2
            y = (height - h) / 2
            p.setBrush(_grad_color(i / (self._n - 1)))
            p.drawRoundedRect(
                int(x), int(y), int(barw), int(h), int(barw / 2), int(barw / 2)
            )
        p.end()


class RecordingOverlay(QWidget):
    def __init__(self, level_provider):
        super().__init__(None)
        self._level_provider = level_provider
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        pill = QFrame(self)
        pill.setObjectName("OverlayPill")
        pill.setStyleSheet(
            "#OverlayPill{background:#211E27;border:1px solid #3C3646;"
            "border-radius:22px;}"
            "#OverlayLabel{color:#E7E0EE;font-size:13px;}"
            "#OverlayBar{background:#2E2A34;border:none;border-radius:3px;}"
            "#OverlayBar::chunk{background:#B48BB9;border-radius:3px;}"
        )
        lay = QHBoxLayout(pill)
        lay.setContentsMargins(16, 10, 18, 10)
        lay.setSpacing(12)
        self._dot = QLabel()
        self._dot.setFixedSize(22, 22)
        self._wave = _WaveBars()
        self._bar = QProgressBar()
        self._bar.setObjectName("OverlayBar")
        self._bar.setFixedSize(150, 6)
        self._bar.setTextVisible(False)
        self._bar.setRange(0, 0)
        self._label = QLabel("Ouvindo…")
        self._label.setObjectName("OverlayLabel")
        lay.addWidget(self._dot)
        lay.addWidget(self._wave)
        lay.addWidget(self._bar)
        lay.addWidget(self._label)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.addWidget(pill)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 160))
        pill.setGraphicsEffect(shadow)

        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(60)
        self._wave_timer.timeout.connect(self._tick_wave)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(500)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._t0: QTime | None = None

    # ---- estados ----
    def show_recording(self) -> None:
        self._hide_timer.stop()
        self._wave.show()
        self._wave.reset()
        self._bar.hide()
        self._set_dot("mic", "#E5484D")
        self._t0 = QTime.currentTime()
        self._label.setText("Ouvindo…  0:00")
        self._wave_timer.start()
        self._elapsed_timer.start()
        self._show_at_bottom()

    def show_processing(self, text: str = "Transcrevendo…") -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._wave.hide()
        self._bar.show()
        self._bar.setRange(0, 0)
        self._set_dot("sparkle", "#FBB03B")
        self._label.setText(text)
        self._show_at_bottom()

    def show_done(self, text: str = "Colado ✓") -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._wave.hide()
        self._bar.hide()
        self._set_dot("check", "#30A46C")
        self._label.setText(text)
        self._show_at_bottom()
        self._hide_timer.start(1500)

    def hide_overlay(self) -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._hide_timer.stop()
        self.hide()

    # ---- internos ----
    def _set_dot(self, icon_name: str, color: str) -> None:
        self._dot.setPixmap(_badge(icon_name, color, 24))

    def _show_at_bottom(self) -> None:
        self.adjustSize()
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.center().x() - self.width() // 2
        y = screen.bottom() - self.height() - 50
        self.move(x, y)
        self.show()
        self.raise_()

    def _tick_wave(self) -> None:
        try:
            level = float(self._level_provider())
        except Exception:
            level = 0.0
        self._wave.push(level)

    def _tick_elapsed(self) -> None:
        if self._t0 is None:
            return
        secs = self._t0.secsTo(QTime.currentTime())
        self._label.setText(f"Ouvindo…  {secs // 60}:{secs % 60:02d}")
