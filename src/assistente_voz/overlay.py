"""Sobreposição flutuante (pop-up) na parte de baixo da tela.

Estados: gravando (onda reagindo à voz, com botões parar/cancelar) →
processando → concluído. Tudo é pintado à mão com antialiasing para ficar
nítido em qualquer escala de tela; não rouba o foco de quem está digitando.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QWidget,
)

from . import icons

_GRAD = ((0xBD, 0x61, 0x9D), (0xB4, 0x8B, 0xB9), (0xFB, 0xB0, 0x3B))
_PILL_BG = QColor(0x21, 0x1E, 0x27, 250)
_PILL_BORDER = QColor(0x3C, 0x36, 0x46)
_TEXT = "#E7E0EE"


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


def _badge(icon_name: str, color: str, size: int = 24) -> QPixmap:
    """Círculo colorido com ícone branco, nítido em telas com escala."""
    dpr = icons._dpr()
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(dpr, dpr)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    p.drawEllipse(QRectF(0, 0, size, size))
    glyph = size * 0.6
    p.translate((size - glyph) / 2, (size - glyph) / 2)
    icons.draw(icon_name, p, glyph, QColor("#FFFFFF"))
    p.end()
    return pm


class _WaveBars(QWidget):
    """Onda de voz: cada barra persegue suavemente o nível do microfone."""

    def __init__(self, n: int = 21, parent=None):
        super().__init__(parent)
        self._n = n
        self._levels = [0.06] * n   # histórico rolante do que foi falado
        self._smooth = 0.06         # nível suavizado no tempo
        self._phase = 0.0
        self.setFixedSize(n * 7, 30)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def reset(self) -> None:
        self._levels = [0.06] * self._n
        self._smooth = 0.06
        self._repaint()

    def push(self, level: float) -> None:
        """Entra um novo nível: rola o histórico e repinta."""
        level = max(0.0, min(1.0, level))
        # sobe rápido (acompanha a voz) e desce mais devagar (fica fluido)
        k = 0.6 if level > self._smooth else 0.25
        self._smooth += (level - self._smooth) * k
        self._phase += 0.5
        self._levels = self._levels[1:] + [self._smooth]
        self._repaint()

    def _repaint(self) -> None:
        # Em janela translúcida, repintar só o filho pode não recompor na tela
        # (o Windows mantém o quadro anterior) — repintamos o balão inteiro.
        win = self.window()
        (win if win is not None else self).update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        slot = self.width() / self._n
        barw = slot * 0.44
        h_max = float(self.height())
        for i, lv in enumerate(self._levels):
            wobble = 0.9 + 0.1 * math.sin(self._phase + i * 0.8)
            h = max(3.0, min(h_max, lv * wobble * h_max))
            x = i * slot + (slot - barw) / 2
            y = (h_max - h) / 2
            p.setBrush(_grad_color(i / (self._n - 1)))
            p.drawRoundedRect(QRectF(x, y, barw, h), barw / 2, barw / 2)
        p.end()


class _RoundIconButton(QPushButton):
    """Botãozinho redondo do pop-up (pintado à mão, sem QSS)."""

    def __init__(self, icon_name: str, color: str, tip: str, size: int = 28):
        super().__init__()
        self._icon = icon_name
        self._color = color
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tip)
        self.setFlat(True)
        self.setStyleSheet(
            f"border:none;background:transparent;padding:0;"
            f"min-width:{size}px;min-height:{size}px;"
            f"max-width:{size}px;max-height:{size}px;"
        )

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = float(min(self.width(), self.height()))
        base = QColor(self._color)
        if not self.underMouse():
            base.setAlpha(190)
        p.setPen(Qt.NoPen)
        p.setBrush(base)
        p.drawEllipse(QRectF(0, 0, s, s))
        glyph = s * 0.5
        p.translate((s - glyph) / 2, (s - glyph) / 2)
        icons.draw(self._icon, p, glyph, QColor("#FFFFFF"))
        p.end()

    def enterEvent(self, event):  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self.update()
        super().leaveEvent(event)


class RecordingOverlay(QWidget):
    stopRequested = Signal()
    cancelRequested = Signal()

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

        lay = QHBoxLayout(self)
        lay.setContentsMargins(30, 24, 32, 26)  # espaço para a sombra pintada
        lay.setSpacing(12)

        self._dot = QLabel()
        self._dot.setFixedSize(24, 24)
        self._dot.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._wave = _WaveBars()
        self._bar = QProgressBar()
        self._bar.setFixedSize(150, 6)
        self._bar.setTextVisible(False)
        self._bar.setRange(0, 0)
        self._bar.setStyleSheet(
            "QProgressBar{background:#2E2A34;border:none;border-radius:3px;}"
            "QProgressBar::chunk{background:#B48BB9;border-radius:3px;}"
        )
        self._label = QLabel("Ouvindo…")
        self._label.setStyleSheet(f"color:{_TEXT};font-size:13px;background:transparent;")
        self._stop_btn = _RoundIconButton("stop", "#E5484D", "Parar e transcrever")
        self._stop_btn.clicked.connect(self.stopRequested)
        self._cancel_btn = _RoundIconButton("close", "#6B6478", "Cancelar (descartar)")
        self._cancel_btn.clicked.connect(self.cancelRequested)

        for w in (self._dot, self._wave, self._bar, self._label,
                  self._stop_btn, self._cancel_btn):
            lay.addWidget(w)

        self._wave_timer = QTimer(self)
        self._wave_timer.setInterval(33)  # ~30 fps
        self._wave_timer.timeout.connect(self._tick_wave)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(250)
        self._elapsed_timer.timeout.connect(self._tick_elapsed)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._t0: QTime | None = None

    # ---- pintura do balão (nítida, sem efeito de sombra do Qt) ----
    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        m = self.layout().contentsMargins()
        inner = QRectF(
            m.left() - 14, m.top() - 12,
            self.width() - m.left() - m.right() + 28,
            self.height() - m.top() - m.bottom() + 24,
        )
        r = inner.height() / 2
        # sombra: camadas suaves em vez de QGraphicsDropShadowEffect
        p.setPen(Qt.NoPen)
        for i in range(10, 0, -1):
            p.setBrush(QColor(0, 0, 0, 7))
            p.drawRoundedRect(inner.adjusted(-i, -i * 0.5 + 2, i, i * 0.9 + 2),
                              r + i, r + i)
        p.setBrush(_PILL_BG)
        p.setPen(_PILL_BORDER)
        p.drawRoundedRect(inner, r, r)
        p.end()

    # ---- estados ----
    def show_recording(self) -> None:
        self._hide_timer.stop()
        self._wave.show()
        self._wave.reset()
        self._bar.hide()
        self._stop_btn.show()
        self._cancel_btn.show()
        self._set_dot("mic", "#E5484D")
        self._t0 = QTime.currentTime()
        self._label.setText("0:00")
        self._wave_timer.start()
        self._elapsed_timer.start()
        self._show_at_bottom()

    def show_processing(self, text: str = "Transcrevendo…") -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._wave.hide()
        self._bar.show()
        self._stop_btn.hide()
        self._cancel_btn.hide()
        self._set_dot("sparkle", "#FBB03B")
        self._label.setText(text)
        self._show_at_bottom()

    def show_done(self, text: str = "Colado ✓") -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._wave.hide()
        self._bar.hide()
        self._stop_btn.hide()
        self._cancel_btn.hide()
        self._set_dot("check", "#30A46C")
        self._label.setText(text)
        self._show_at_bottom()
        self._hide_timer.start(1400)

    def hide_overlay(self) -> None:
        self._wave_timer.stop()
        self._elapsed_timer.stop()
        self._hide_timer.stop()
        self.hide()

    # ---- internos ----
    def _set_dot(self, icon_name: str, color: str) -> None:
        self._dot.setPixmap(_badge(icon_name, color, 24))

    def _show_at_bottom(self) -> None:
        from PySide6.QtGui import QCursor

        self.adjustSize()
        # Segue o monitor onde está o cursor (não o principal).
        scr = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        screen = scr.availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.bottom() - self.height() - 40,
        )
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
        self._label.setText(f"{secs // 60}:{secs % 60:02d}")
