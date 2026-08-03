"""Ícones desenhados vetorialmente (QPainter).

Emoji renderiza mal e inconsistente no Windows dentro do Qt; aqui os ícones são
desenhados na mão, ficam nítidos em qualquer DPI e assumem a cor do tema.
"""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def _mic(p: QPainter, s: float, c: QColor) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    w, h = s * 0.30, s * 0.44
    p.drawRoundedRect(QRectF((s - w) / 2, s * 0.12, w, h), w / 2, w / 2)
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.08, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(QRectF(s * 0.25, s * 0.32, s * 0.50, s * 0.44), 180 * 16, 180 * 16)
    p.drawLine(QPointF(s / 2, s * 0.76), QPointF(s / 2, s * 0.88))


def _stop(p: QPainter, s: float, c: QColor) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    side = s * 0.42
    p.drawRoundedRect(
        QRectF((s - side) / 2, (s - side) / 2, side, side), s * 0.07, s * 0.07
    )


def _headphones(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.09, Qt.SolidLine, Qt.RoundCap))
    p.drawArc(QRectF(s * 0.16, s * 0.20, s * 0.68, s * 0.62), 0, 180 * 16)
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    w, h = s * 0.16, s * 0.30
    p.drawRoundedRect(QRectF(s * 0.14, s * 0.48, w, h), w / 2, w / 2)
    p.drawRoundedRect(QRectF(s * 0.70, s * 0.48, w, h), w / 2, w / 2)


def _sparkle(p: QPainter, s: float, c: QColor) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(c)

    def star(cx: float, cy: float, r: float) -> None:
        path = [
            QPointF(cx, cy - r),
            QPointF(cx + r * 0.26, cy - r * 0.26),
            QPointF(cx + r, cy),
            QPointF(cx + r * 0.26, cy + r * 0.26),
            QPointF(cx, cy + r),
            QPointF(cx - r * 0.26, cy + r * 0.26),
            QPointF(cx - r, cy),
            QPointF(cx - r * 0.26, cy - r * 0.26),
        ]
        p.drawPolygon(path)

    star(s * 0.42, s * 0.42, s * 0.30)
    star(s * 0.76, s * 0.74, s * 0.16)


def _copy(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.085, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawRoundedRect(
        QRectF(s * 0.32, s * 0.16, s * 0.50, s * 0.50), s * 0.10, s * 0.10
    )
    p.drawRoundedRect(
        QRectF(s * 0.18, s * 0.34, s * 0.50, s * 0.50), s * 0.10, s * 0.10
    )


def _trash(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.085, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(s * 0.18, s * 0.28), QPointF(s * 0.82, s * 0.28))
    p.drawLine(QPointF(s * 0.40, s * 0.28), QPointF(s * 0.42, s * 0.18))
    p.drawLine(QPointF(s * 0.42, s * 0.18), QPointF(s * 0.58, s * 0.18))
    p.drawLine(QPointF(s * 0.58, s * 0.18), QPointF(s * 0.60, s * 0.28))
    p.drawRoundedRect(
        QRectF(s * 0.26, s * 0.32, s * 0.48, s * 0.52), s * 0.08, s * 0.08
    )


def _folder(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.085, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(s * 0.16, s * 0.30), QPointF(s * 0.44, s * 0.30))
    p.drawRoundedRect(
        QRectF(s * 0.14, s * 0.30, s * 0.72, s * 0.46), s * 0.08, s * 0.08
    )


def _check(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.13, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawLine(QPointF(s * 0.24, s * 0.52), QPointF(s * 0.43, s * 0.71))
    p.drawLine(QPointF(s * 0.43, s * 0.71), QPointF(s * 0.77, s * 0.31))


def _close(p: QPainter, s: float, c: QColor) -> None:
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(c, s * 0.12, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(QPointF(s * 0.3, s * 0.3), QPointF(s * 0.7, s * 0.7))
    p.drawLine(QPointF(s * 0.7, s * 0.3), QPointF(s * 0.3, s * 0.7))


_DRAWERS = {
    "close": _close,
    "check": _check,
    "mic": _mic,
    "stop": _stop,
    "headphones": _headphones,
    "sparkle": _sparkle,
    "copy": _copy,
    "trash": _trash,
    "folder": _folder,
}


def draw(name: str, painter: QPainter, size: float, color: QColor) -> None:
    fn = _DRAWERS.get(name)
    if fn:
        fn(painter, size, color)


def _dpr() -> float:
    """Escala da tela (125%, 150%…). Sem isso o ícone sai borrado."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    try:
        return float(app.devicePixelRatio()) if app else 1.0
    except Exception:
        return 1.0


def pixmap(name: str, size: int = 20, color: str = "#FFFFFF") -> QPixmap:
    dpr = _dpr()
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.transparent)
    pm.setDevicePixelRatio(dpr)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.scale(dpr, dpr)  # o Qt não escala sozinho ao pintar em QPixmap
    draw(name, p, float(size), QColor(color))
    p.end()
    return pm


_ICON_CACHE: dict = {}


def icon(name: str, size: int = 20, color: str = "#FFFFFF") -> QIcon:
    """Ícone memorizado — a lista do histórico pedia centenas por atualização."""
    key = (name, size, color, _dpr())
    cached = _ICON_CACHE.get(key)
    if cached is None:
        cached = QIcon(pixmap(name, size, color))
        _ICON_CACHE[key] = cached
    return cached
