"""Gera assets/icon.ico a partir de assets/logo.png.

Requer Pillow:  pip install pillow
Uso:            python tools/make_icon.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    try:
        from PIL import Image
    except ImportError:
        print("Pillow não instalado. Rode: pip install pillow")
        return 1

    src = ROOT / "assets" / "logo.png"
    if not src.is_file():
        print(f"Não encontrei {src}. Coloque a sua logo em assets/logo.png.")
        return 1

    img = Image.open(src).convert("RGBA")
    out = ROOT / "assets" / "icon.ico"
    img.save(out, format="ICO", sizes=SIZES)
    print(f"Gerado: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
