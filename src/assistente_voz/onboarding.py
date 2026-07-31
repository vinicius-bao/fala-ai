"""Primeiros passos: explica o app e coleta a chave de API na 1ª execução.

Também é reaberto quando o usuário tenta usar o app sem chave configurada.
"""

from __future__ import annotations

import webbrowser

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .config import (
    PROVIDER_LABELS,
    PROVIDERS,
    Config,
    resolve_provider_key,
    save_config,
)
from .hotkey import pretty_hotkey
from .resources import app_icon, logo_pixmap

KEY_URLS = {
    "groq": "https://console.groq.com/keys",
    "openai": "https://platform.openai.com/api-keys",
    "gemini": "https://aistudio.google.com/app/apikey",
}


def _step(number: str, text: str) -> QWidget:
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)
    num = QLabel(number)
    num.setObjectName("StepNum")
    num.setAlignment(Qt.AlignCenter)
    num.setFixedSize(22, 22)
    body = QLabel(text)
    body.setWordWrap(True)
    body.setTextFormat(Qt.RichText)
    lay.addWidget(num, 0, Qt.AlignTop)
    lay.addWidget(body, 1)
    return row


class WelcomeDialog(QDialog):
    """Boas-vindas + configuração mínima (provedor e chave)."""

    def __init__(self, controller, parent=None, reason: str = ""):
        super().__init__(parent)
        self.controller = controller
        cfg = controller.config
        self.setWindowTitle("Fala AI — primeiros passos")
        self.setWindowIcon(app_icon())
        self.setMinimumWidth(520)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 20)
        root.setSpacing(14)

        head = QHBoxLayout()
        head.setSpacing(12)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(40))
        title = QLabel("Bem-vindo ao Fala AI")
        title.setObjectName("HeaderTitle")
        head.addWidget(logo)
        head.addWidget(title)
        head.addStretch()
        root.addLayout(head)

        if reason:
            alert = QLabel(reason)
            alert.setObjectName("Alert")
            alert.setWordWrap(True)
            root.addWidget(alert)

        intro = QLabel(
            "Fale e o texto aparece onde o cursor estiver — em qualquer "
            "programa do Windows."
        )
        intro.setObjectName("Muted")
        intro.setWordWrap(True)
        root.addWidget(intro)

        hk = pretty_hotkey(cfg.hotkey)
        rhk = pretty_hotkey(cfg.refine_hotkey) if cfg.refine_hotkey else "—"
        root.addWidget(
            _step("1", f"Segure <b>{hk}</b>, fale e solte. O texto é colado na hora "
                       "(e fica no histórico e na área de transferência).")
        )
        root.addWidget(
            _step("2", f"Use <b>{rhk}</b> para o mesmo, mas com o texto <b>revisado "
                       "por IA</b> antes de colar.")
        )
        root.addWidget(
            _step("3", "Arraste um áudio na janela (ex.: mensagem de voz do "
                       "WhatsApp) para transcrever.")
        )
        root.addWidget(
            _step("4", "O app fica na <b>bandeja</b>, perto do relógio. O "
                       "Windows esconde ícones novos: clique na setinha "
                       "<b>⌃</b> e arraste o Fala AI para fora.")
        )

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("Sep")
        root.addWidget(line)

        need = QLabel(
            "<b>Para funcionar, informe uma chave de API.</b> É grátis para "
            "começar e leva um minuto."
        )
        need.setWordWrap(True)
        root.addWidget(need)

        prov_row = QHBoxLayout()
        prov_row.setSpacing(8)
        self.provider_combo = QComboBox()
        for p in PROVIDERS:
            self.provider_combo.addItem(PROVIDER_LABELS[p], p)
        idx = self.provider_combo.findData(
            cfg.provider if cfg.provider in PROVIDERS else "groq"
        )
        self.provider_combo.setCurrentIndex(max(0, idx))
        self.provider_combo.currentIndexChanged.connect(self._sync_key_field)
        get_btn = QPushButton("Obter chave")
        get_btn.setCursor(Qt.PointingHandCursor)
        get_btn.clicked.connect(self._open_key_page)
        prov_row.addWidget(QLabel("Provedor:"))
        prov_row.addWidget(self.provider_combo, 1)
        prov_row.addWidget(get_btn)
        root.addLayout(prov_row)

        self._keys = {
            "groq": cfg.groq_api_key,
            "openai": cfg.openai_api_key,
            "gemini": cfg.gemini_api_key,
        }
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("cole aqui a chave copiada do site")
        self._current = self.provider_combo.currentData()
        self.key_edit.setText(self._keys.get(self._current, ""))
        root.addWidget(self.key_edit)

        self.status = QLabel("")
        self.status.setObjectName("Muted")
        self.status.setWordWrap(True)
        root.addWidget(self.status)

        btns = QHBoxLayout()
        btns.addStretch()
        later = QPushButton("Fazer depois")
        later.clicked.connect(self._later)
        start = QPushButton("Começar a usar")
        start.setObjectName("Primary")
        start.setCursor(Qt.PointingHandCursor)
        start.clicked.connect(self._finish)
        btns.addWidget(later)
        btns.addWidget(start)
        root.addLayout(btns)

    # ----- ações -----
    def _sync_key_field(self) -> None:
        self._keys[self._current] = self.key_edit.text().strip()
        self._current = self.provider_combo.currentData()
        self.key_edit.setText(self._keys.get(self._current, ""))

    def _open_key_page(self) -> None:
        webbrowser.open(KEY_URLS.get(self.provider_combo.currentData(), ""))
        self.status.setText(
            "Abri a página no navegador. Crie a chave, copie e cole no campo acima."
        )

    def _save(self, done: bool) -> Config:
        self._keys[self._current] = self.key_edit.text().strip()
        cfg = self.controller.config
        new = Config(**{**cfg.to_dict(), **{
            "provider": self.provider_combo.currentData(),
            "groq_api_key": self._keys["groq"],
            "openai_api_key": self._keys["openai"],
            "gemini_api_key": self._keys["gemini"],
            "onboarding_done": done,
        }})
        save_config(new)
        self.controller.apply_config(new)
        return new

    def _later(self) -> None:
        self._save(done=True)
        self.reject()

    def _finish(self) -> None:
        new = self._save(done=True)
        if not resolve_provider_key(new, new.provider):
            self.status.setText(
                "Sem a chave o app não consegue transcrever. Você pode colá-la "
                "depois em Configurações → Transcrição."
            )
            return
        self.accept()
