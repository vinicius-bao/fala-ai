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
    pal = palette_for(mode, dark_os)
    down = up = check = ""
    try:
        from .resources import chevron_png, icon_png

        down = chevron_png(pal.text_muted, up=False)
        up = chevron_png(pal.text_muted, up=True)
        check = icon_png("check", pal.accent_text, 14)
    except Exception:  # sem cache gravável: usa os padrões do Qt
        pass
    app.setStyleSheet(build_qss(pal, down, up, check))


def build_qss(
    p: Palette, chevron_down: str = "", chevron_up: str = "", check: str = ""
) -> str:
    """Folha de estilo (QSS) gerada a partir da paleta.

    ``chevron_*`` são caminhos de PNG para as setas de QComboBox/QSpinBox; se
    vazios, o Qt usa as setas padrão.
    """
    grad = (
        f"qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {p.grad_start}, stop:0.5 {p.grad_mid}, stop:1 {p.grad_end})"
    )
    arrows = ""
    if chevron_down:
        arrows += (
            f"QComboBox::down-arrow {{ image: url({chevron_down}); "
            "width: 12px; height: 8px; }\n"
            f"QSpinBox::down-arrow {{ image: url({chevron_down}); "
            "width: 12px; height: 8px; }\n"
        )
    if chevron_up:
        arrows += (
            f"QSpinBox::up-arrow {{ image: url({chevron_up}); "
            "width: 12px; height: 8px; }\n"
        )
    check_rule = f"image: url({check});" if check else ""
    return f"""
    * {{ outline: none; }}
    QWidget {{ background-color: {p.bg}; color: {p.text}; font-size: 13px; }}
    QMainWindow, QDialog {{ background-color: {p.bg}; }}

    #Header {{ background-color: {p.surface}; border-bottom: 1px solid {p.border}; }}
    #HeaderTitle {{ font-size: 16px; font-weight: 500; color: {p.text}; }}
    #Hero {{ background-color: {p.surface}; border-bottom: 1px solid {p.border}; }}
    QLabel#Muted {{ color: {p.text_muted}; }}
    #SectionTitle {{ font-size: 13px; font-weight: 500; color: {p.text}; }}
    #StepNum {{ background-color: {p.accent}; color: {p.accent_text};
        border-radius: 11px; font-size: 12px; font-weight: 500; }}
    #Alert {{ background-color: {p.surface_alt}; color: {p.text};
        border: 1px solid {p.warning}; border-radius: 8px; padding: 9px 12px; }}
    #Sep {{ background-color: {p.border}; max-height: 1px; border: none; }}

    #Card {{ background-color: {p.surface}; border: 1px solid {p.border};
        border-radius: 12px; }}
    #Card QLabel, #Card QCheckBox {{ background: transparent; }}

    QPushButton#Chip {{ background-color: {p.surface_alt}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 10px; padding: 8px 14px;
        font-size: 12px; text-align: left; }}
    QPushButton#Chip:hover {{ border-color: {p.accent}; }}
    QPushButton#Chip:disabled {{ color: {p.text_muted}; background-color: transparent; }}

    QPushButton#IconBtn {{ background: transparent; border: 1px solid transparent;
        border-radius: 8px; padding: 0; }}
    QPushButton#IconBtn:hover {{ background-color: {p.surface_alt};
        border-color: {p.border}; }}

    #HistoryList {{ background: transparent; border: none; }}
    #HistoryList::item {{ background: transparent; border: none; padding: 0; }}
    #HistoryCard {{ background-color: {p.surface}; border: 1px solid {p.border};
        border-radius: 10px; }}
    #HistoryCard:hover {{ border-color: {p.accent}; }}
    #TimePill {{ color: {p.text_muted}; background-color: {p.surface_alt};
        border-radius: 6px; padding: 3px 7px; font-size: 11px; }}
    #CardText {{ color: {p.text}; font-size: 12px; }}
    #RefinedPill {{ color: {p.accent_text}; background-color: {p.accent};
        border-radius: 8px; padding: 2px 8px; font-size: 10px; }}

    QTabWidget::pane {{ border: none; background: {p.bg}; }}
    QTabWidget::tab-bar {{ alignment: center; }}
    QTabBar {{ background: transparent; }}
    QTabBar::tab {{ background: transparent; color: {p.text_muted};
        padding: 8px 22px; border: none; border-radius: 9px; margin: 8px 3px 4px 3px; }}
    QTabBar::tab:selected {{ color: {p.text}; background-color: {p.surface}; }}
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
    #VersionPill {{ color: {p.text_muted}; background: {p.surface_alt};
        border: 1px solid {p.border}; border-radius: 11px; padding: 3px 10px;
        font-size: 11px; }}

    QLineEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 8px; padding: 6px 8px;
        selection-background-color: {p.accent}; selection-color: {p.accent_text}; }}
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{
        border-color: {p.accent}; }}
    QComboBox::drop-down {{ border: none; background: transparent; width: 24px;
        subcontrol-origin: padding; subcontrol-position: center right; }}
    {arrows}
    QComboBox QAbstractItemView {{ background-color: {p.surface};
        border: 1px solid {p.border}; border-radius: 8px; padding: 4px;
        selection-background-color: {p.accent}; selection-color: {p.accent_text}; }}
    QSpinBox::up-button, QSpinBox::down-button {{ background: transparent;
        border: none; width: 16px; margin-right: 4px; }}

    QListWidget {{ background-color: {p.surface}; color: {p.text};
        border: 1px solid {p.border}; border-radius: 10px; padding: 4px; }}
    QListWidget::item {{ padding: 8px; border-radius: 6px; }}
    QListWidget::item:selected {{ background-color: {p.accent}; color: {p.accent_text}; }}
    QListWidget::item:hover {{ background-color: {p.surface_alt}; }}

    QCheckBox {{ color: {p.text}; spacing: 9px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 5px;
        border: 1px solid {p.border}; background-color: {p.surface_alt}; }}
    QCheckBox::indicator:hover {{ border-color: {p.accent}; }}
    QCheckBox::indicator:checked {{ background-color: {p.accent};
        border-color: {p.accent}; {check_rule} }}
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
