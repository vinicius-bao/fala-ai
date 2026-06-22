"""Gera assets/icon.ico (ícone do .exe e do instalador).

Usa assets/logo.png se existir; caso contrário, renderiza assets/logo.svg.
Requer Pillow (e PySide6, no caso do SVG):  pip install pillow PySide6
Uso:  python tools/make_icon.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _png_from_svg(svg: Path, out_png: Path, size: int = 512) -> None:
    import sys

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication

    QApplication.instance() or QApplication(sys.argv)
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    QSvgRenderer(str(svg)).render(painter)
    painter.end()
    pm.save(str(out_png), "PNG")


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow não instalado. Rode: pip install pillow")
        return 1

    assets = ROOT / "assets"
    src = assets / "logo.png"
    tmp = None
    if not src.is_file():
        svg = assets / "logo.svg"
        if not svg.is_file():
            print("Coloque assets/logo.png (ou mantenha assets/logo.svg).")
            return 1
        try:
            tmp = assets / "_logo_from_svg.png"
            _png_from_svg(svg, tmp)
            src = tmp
        except Exception as e:  # noqa: BLE001
            print(f"Não consegui renderizar o SVG ({e}). Coloque assets/logo.png.")
            return 1

    img = Image.open(src).convert("RGBA")
    out = assets / "icon.ico"
    img.save(out, format="ICO", sizes=SIZES)
    if tmp and tmp.exists():
        tmp.unlink()
    print(f"Gerado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
