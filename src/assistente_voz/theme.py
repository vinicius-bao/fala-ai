"""Tema do Fala AI — paleta centralizada e geração do estilo (QSS).

Mude o visual inteiro editando as paletas abaixo. Cores da marca:
gradiente #BD619D -> #B48BB9 -> #FBB03B; claro #E6E7E8/branco texto #5A5C63;
escuro base #5A5C63 texto branco. ``build_qss`` é puro (sem Qt) e testável.
"""

from __future__ import annotations

from dataclasses import dataclass

# Cores da marca (gradiente da logo)
BRAND_START = "#BD619D"
BRAND_MID = "#B48BB9"
BRAND_END = "#FBB03B"


@dataclass(frozen=True)
class Palette:
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    text_muted: str
    accent: str
    accent_text: str
    accent_hover: str
    danger: str
    success: str
    warning: str
    grad_start: str = BRAND_START
    grad_mid: str = BRAND_MID
    grad_end: str = BRAND_END


LIGHT = Palette(
    bg="#E6E7E8",
    surface="#FFFFFF",
    surface_alt="#F1F1F3",
    border="#D4D5D9",
    text="#5A5C63",
    text_muted="#8C8E96",
    accent="#BD619D",
    accent_text="#FFFFFF",
    accent_hover="#A9527F",
    danger="#E5484D",
    success="#30A46C",
    warning="#FBB03B",
)

DARK = Palette(
    bg="#4F5158",
    surface="#5A5C63",
    surface_alt="#666870",
    border="#73757F",
    text="#FFFFFF",
    text_muted="#C7C8CD",
    accent="#CE84B4",
    accent_text="#FFFFFF",
    accent_hover="#D89AC2",
    danger="#FF6166",
    success="#4CC38A",
    warning="#FBB03B",
)


def palette_for(mode: str, dark_os: bool) -> Palette:
    """Escolhe a paleta pelo modo ('auto'/'light'/'dark') e pelo tema do SO."""
    if mode == "dark":
        return DARK
    if mode == "light":
        return LIGHT
    return DARK if dark_os else LIGHT


def apply_theme(app, mode: str) -> None:
    """Aplica o tema no QApplication conforme o modo escolhido."""
    from PySide6.QtCore import Qt

    dark_os = False
    try:
        dark_os = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        pass
    app.setStyleSheet(build_qss(palette_for(mode, dark_os)))


def build_qss(p: Palette) -> str:
    """Folha de estilo (QSS) gerada a partir da paleta."""
    grad = (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {p.grad_start}, stop:0.5 {p.grad_mid}, stop:1 {p.grad_end})"
    )
    return f"""
    * {{ outline: none; }}
    QWidget {{ background-color: {p.bg}; color: {p.text}; font-size: 13px; }}
    QMainWindow, QDialog {{ background-color: {p.bg}; }}

    #Header {{ background-color: {p.surface}; border-bottom: 1px solid {p.border}; }}
    #HeaderTitle {{ font-size: 17px; font-weight: 600; color: {p.text}; }}
    QLabel#Muted {{ color: {p.text_muted}; }}

    QTabWidget::pane {{ border: none; background: {p.bg}; }}
    QTabBar::tab {{ background: transparent; color: {p.text_muted};
        padding: 8px 18px; border: none; border-bottom: 2px solid transparent; }}
    QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; }}
    QTabBar::tab:hover {{ color: {p.text}; }}

    QPushButton {{ background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 9px; padding: 9px 16px;
        min-height: 18px; }}
    QPushButton:hover {{ border-color: {p.accent}; background-color: {p.surface_alt}; }}
    QPushButton:pressed {{ background-color: {p.surface_alt}; }}
    QPushButton#Primary {{ border: none; color: #FFFFFF; border-radius: 9px;
        padding: 10px 18px; min-height: 18px; font-weight: 500;
        background-color: {grad}; }}
    QPushButton#Primary:hover {{ background-color: {p.accent_hover}; }}
    QPushButton#Record {{ border: none; color: #FFFFFF; border-radius: 9px;
        padding: 10px 18px; min-height: 18px; font-weight: 500;
        background-color: {grad}; }}
    QPushButton#Record:hover {{ background-color: {p.accent_hover}; }}
    QPushButton#Record[recording="true"] {{ background-color: {p.danger}; }}
    QPushButton#Record[recording="true"]:hover {{ background-color: {p.danger}; }}

    #Hero {{ background: transparent; }}
    #VersionPill {{ color: {p.text_muted}; background: {p.surface_alt};
        border: 1px solid {p.border}; border-radius: 11px; padding: 3px 10px;
        font-size: 11px; }}
    QPushButton#RecordBig {{ border: none; border-radius: 38px; color: #FFFFFF;
        font-size: 30px; background-color: {grad}; }}
    QPushButton#RecordBig:hover {{ background-color: {p.accent_hover}; }}
    QPushButton#RecordBig[recording="true"] {{ background-color: {p.danger}; }}

    QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 8px; padding: 6px 8px;
        selection-background-color: {p.accent}; selection-color: {p.accent_text}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border-color: {p.accent}; }}

    QListWidget {{ background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 10px; padding: 4px; }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background-color: {p.accent}; color: {p.accent_text}; }}
    QListWidget::item:hover {{ background-color: {p.surface_alt}; }}

    QCheckBox {{ color: {p.text}; spacing: 8px; }}
    QLabel {{ background: transparent; color: {p.text}; }}
    QStatusBar {{ background-color: {p.surface}; color: {p.text_muted};
        border-top: 1px solid {p.border}; }}

    QMenu {{ background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 8px; padding: 4px; }}
    QMenu::item {{ padding: 6px 22px; border-radius: 6px; }}
    QMenu::item:selected {{ background-color: {p.accent}; color: {p.accent_text}; }}

    QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 6px;
        min-height: 28px; margin: 2px; }}
    QScrollBar::handle:vertical:hover {{ background: {p.text_muted}; }}
    QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 6px;
        min-width: 28px; margin: 2px; }}
    QScrollBar::handle:horizontal:hover {{ background: {p.text_muted}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """
