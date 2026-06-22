"""Carregamento de assets (logo/ícone), com fallback e suporte a PyInstaller.

Preferência: assets/logo.png (do usuário) -> assets/logo.svg (marca) ->
desenho gerado em tempo de execução com o gradiente da marca.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BRAND = ("#BD619D", "#B48BB9", "#FBB03B")


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):  # empacotado pelo PyInstaller
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent.parent  # raiz do projeto


def asset_path(name: str) -> Path:
    return _base_dir() / "assets" / name


def logo_pixmap(size: int = 64):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter, QPixmap

    png = asset_path("logo.png")
    if png.is_file():
        pm = QPixmap(str(png))
        if not pm.isNull():
            return pm.scaled(
                size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )

    svg = asset_path("logo.svg")
    if svg.is_file():
        try:
            from PySide6.QtSvg import QSvgRenderer

            pm = QPixmap(size, size)
            pm.fill(Qt.transparent)
            painter = QPainter(pm)
            QSvgRenderer(str(svg)).render(painter)
            painter.end()
            return pm
        except Exception:
            pass

    return _generated_pixmap(size)


def _generated_pixmap(size: int):
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPixmap

    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    grad = QLinearGradient(0, size, size, 0)
    grad.setColorAt(0.0, QColor(_BRAND[0]))
    grad.setColorAt(0.5, QColor(_BRAND[1]))
    grad.setColorAt(1.0, QColor(_BRAND[2]))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.NoPen)
    bars = [(0.14, 0.22), (0.32, 0.54), (0.50, 0.78), (0.68, 0.54), (0.86, 0.22)]
    w = size * 0.10
    for cx, hf in bars:
        h = size * hf
        x = size * cx - w / 2
        y = (size - h) / 2
        painter.drawRoundedRect(QRectF(x, y, w, h), w / 2, w / 2)
    painter.end()
    return pm


def app_icon():
    from PySide6.QtGui import QIcon

    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(logo_pixmap(s))
    return icon


def tray_icon(state: str):
    from PySide6.QtCore import Qt, QRectF
    from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.drawPixmap(0, 0, logo_pixmap(size))

    badge = {"recording": "#E5484D", "transcribing": "#FBB03B"}.get(state)
    if badge:
        d = size * 0.36
        painter.setPen(QPen(QColor("#FFFFFF"), size * 0.05))
        painter.setBrush(QColor(badge))
        painter.drawEllipse(QRectF(size - d - 1, size - d - 1, d, d))
    painter.end()
    return QIcon(pm)
