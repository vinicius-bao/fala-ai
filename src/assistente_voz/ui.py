"""Interface: bandeja (tray) + janela única com abas Histórico e Configurações."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QLinearGradient, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from . import icons
from .app import Controller
from .audio import list_input_devices
from .audiofile import SUPPORTED_EXTS, is_supported
from .config import (
    AI_NOTE,
    DEFAULT_CHAT_MODELS,
    DEFAULT_MODELS,
    DEFAULT_REFINE_PROMPT,
    PROVIDER_LABELS,
    PROVIDERS,
    REFINE_PRESETS,
    Config,
    match_preset,
    save_config,
)
from .hotkey import parse_hotkey, pretty_hotkey
from .onboarding import WelcomeDialog
from .resources import app_icon, logo_pixmap, tray_icon

APP_NAME = "Fala AI"
BRAND = ("#BD619D", "#B48BB9", "#FBB03B")
DANGER = "#E5484D"


def _qt_key_to_token(key: int) -> str:
    if Qt.Key_A <= key <= Qt.Key_Z:
        return chr(key).lower()
    if Qt.Key_0 <= key <= Qt.Key_9:
        return chr(key)
    if Qt.Key_F1 <= key <= Qt.Key_F35:
        return f"f{key - Qt.Key_F1 + 1}"
    special = {
        Qt.Key_Space: "space",
        Qt.Key_Pause: "pause",
        Qt.Key_Insert: "insert",
        Qt.Key_Home: "home",
        Qt.Key_End: "end",
        Qt.Key_PageUp: "page_up",
        Qt.Key_PageDown: "page_down",
    }
    return special.get(key, "")


class NoScrollComboBox(QComboBox):
    """Combo que ignora a roda do mouse e não impõe largura pelo texto.

    Sem isso, uma opção longa ("Automático (segue o Windows)") vira largura
    mínima da janela inteira — e em telas com escala 125% o conteúdo era
    cortado.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def wheelEvent(self, event):  # noqa: N802
        event.ignore()


class NoScrollSpinBox(QSpinBox):
    """SpinBox que ignora a roda do mouse (só teclado e setas)."""

    def wheelEvent(self, event):  # noqa: N802
        event.ignore()


class RecordButton(QPushButton):
    """Botão circular pintado à mão (gradiente da marca / vermelho ao gravar)."""

    def __init__(self, diameter: int = 88, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        # O min-height do QSS global sobrepõe setFixedSize; por isso o tamanho
        # também vai no stylesheet do próprio widget (e o fixed size vem depois).
        self.setStyleSheet(
            "border:none;background:transparent;padding:0;"
            f"min-width:{diameter}px;min-height:{diameter}px;"
            f"max-width:{diameter}px;max-height:{diameter}px;"
        )
        self.setFixedSize(diameter, diameter)
        self._recording = False

    def set_recording(self, value: bool) -> None:
        self._recording = value
        self.setToolTip("Parar gravação" if value else "Iniciar gravação")
        self.update()

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s = float(min(self.width(), self.height()))
        pad = s * 0.06                      # espaço para o halo
        circle = QRectF(pad, pad, s - 2 * pad, s - 2 * pad)

        halo = QColor(DANGER if self._recording else BRAND[0])
        halo.setAlpha(60 if self.underMouse() else 38)
        p.setPen(Qt.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QRectF(0, 0, s, s))

        if self._recording:
            p.setBrush(QColor(DANGER))
        else:
            grad = QLinearGradient(circle.left(), circle.bottom(),
                                   circle.right(), circle.top())
            grad.setColorAt(0.0, QColor(BRAND[0]))
            grad.setColorAt(0.5, QColor(BRAND[1]))
            grad.setColorAt(1.0, QColor(BRAND[2]))
            p.setBrush(grad)
        p.drawEllipse(circle)

        glyph = s * 0.46
        p.translate((s - glyph) / 2, (s - glyph) / 2)
        icons.draw("stop" if self._recording else "mic", p, glyph, QColor("#FFFFFF"))
        p.end()

    def enterEvent(self, event):  # noqa: N802
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):  # noqa: N802
        self.update()
        super().leaveEvent(event)


def _chip(text: str, icon_name: str, on_click) -> QPushButton:
    btn = QPushButton("  " + text)
    btn.setObjectName("Chip")
    btn.setCursor(Qt.PointingHandCursor)
    btn.setIcon(icons.icon(icon_name, 18, "#9A93A6"))
    if on_click is not None:
        btn.clicked.connect(on_click)
    return btn


def _section(title: str) -> tuple[QFrame, QFormLayout]:
    """Cartão de seção com título; devolve (frame, form) para preencher."""
    card = QFrame()
    card.setObjectName("Card")
    box = QVBoxLayout(card)
    box.setContentsMargins(16, 14, 16, 16)
    box.setSpacing(10)
    label = QLabel(title)
    label.setObjectName("SectionTitle")
    box.addWidget(label)
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    form.setFormAlignment(Qt.AlignTop)
    form.setHorizontalSpacing(14)
    form.setVerticalSpacing(10)
    # Em janelas estreitas (ou com fonte grande por causa da escala da tela),
    # o rótulo passa para cima do campo em vez de espremer/cortar a linha.
    form.setRowWrapPolicy(QFormLayout.WrapLongRows)
    form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
    box.addLayout(form)
    return card, form


class HistoryCard(QFrame):
    """Item do histórico: hora, texto e botão de copiar."""

    def __init__(self, entry, on_copy, on_refine, on_delete, parent=None):
        super().__init__(parent)
        self.setObjectName("HistoryCard")
        self.setMinimumHeight(50)
        self.uid = entry.uid
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 10, 10)
        lay.setSpacing(10)

        stamp = QLabel(entry.timestamp[11:16] if len(entry.timestamp) >= 16 else "")
        stamp.setObjectName("TimePill")
        self._full = " ".join(entry.text.split())
        body = QLabel()
        body.setObjectName("CardText")
        # Sem largura fixa: o texto é cortado conforme o espaço real do cartão
        # (calculado no resize), então nunca estoura a lista.
        body.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        body.setToolTip(entry.text)
        self._body = body

        lay.addWidget(stamp)
        lay.addWidget(body, 1)

        if entry.refined:
            mark = "refinado" if entry.refined == 1 else f"refinado {entry.refined}×"
            self._badge = QLabel(mark)
            self._badge.setObjectName("RefinedPill")
            if entry.original:
                self._badge.setToolTip("Texto original:\n\n" + entry.original)
            lay.addWidget(self._badge)

        self._refine_btn = QPushButton()
        self._refine_btn.setObjectName("IconBtn")
        self._refine_btn.setCursor(Qt.PointingHandCursor)
        self._refine_btn.setIcon(icons.icon("sparkle", 18, "#9A93A6"))
        self._refine_btn.setFixedSize(30, 30)
        self._refine_btn.setToolTip(
            "Refinar de novo com IA" if entry.refined else "Refinar com IA"
        )
        self._refine_btn.clicked.connect(lambda: on_refine(entry.uid))
        lay.addWidget(self._refine_btn)

        copy_btn = QPushButton()
        copy_btn.setObjectName("IconBtn")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setIcon(icons.icon("copy", 18, "#9A93A6"))
        copy_btn.setFixedSize(30, 30)
        copy_btn.setToolTip("Copiar")
        copy_btn.clicked.connect(lambda: on_copy(entry.text))
        lay.addWidget(copy_btn)

        del_btn = QPushButton()
        del_btn.setObjectName("IconBtn")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setIcon(icons.icon("trash", 18, "#9A93A6"))
        del_btn.setFixedSize(30, 30)
        del_btn.setToolTip("Apagar este item")
        del_btn.clicked.connect(lambda: on_delete(entry.uid))
        lay.addWidget(del_btn)

    def set_busy(self, busy: bool) -> None:
        self._refine_btn.setEnabled(not busy)
        self._refine_btn.setToolTip("Refinando…" if busy else "Refinar com IA")

    def _elide(self) -> None:
        w = self._body.width()
        if w > 1:
            self._body.setText(
                self._body.fontMetrics().elidedText(self._full, Qt.ElideRight, w)
            )

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._elide()

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        self._elide()


class HotkeyCaptureButton(QPushButton):
    """Captura a próxima combinação pressionada e a grava como atalho."""

    changed = Signal(str)

    def __init__(self, value: str, parent=None):
        super().__init__(parent)
        self._value = value
        self._capturing = False
        self.setCursor(Qt.PointingHandCursor)
        self._refresh()
        self.clicked.connect(self._begin)

    def value(self) -> str:
        return self._value

    def _refresh(self) -> None:
        self.setText(
            "Pressione a combinação…" if self._capturing else pretty_hotkey(self._value)
        )

    def _begin(self) -> None:
        self._capturing = True
        self._refresh()
        self.grabKeyboard()
        self.setFocus()

    def keyPressEvent(self, event):  # noqa: N802 (override do Qt)
        if not self._capturing:
            return super().keyPressEvent(event)
        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Alt, Qt.Key_Shift, Qt.Key_Meta):
            return  # espera a tecla principal
        token = _qt_key_to_token(key)
        if not token:
            return
        mods = []
        m = event.modifiers()
        if m & Qt.ControlModifier:
            mods.append("ctrl")
        if m & Qt.AltModifier:
            mods.append("alt")
        if m & Qt.ShiftModifier:
            mods.append("shift")
        if m & Qt.MetaModifier:
            mods.append("cmd")
        self._value = "+".join(mods + [token])
        self._capturing = False
        self.releaseKeyboard()
        self._refresh()
        self.changed.emit(self._value)


class TranscriptionResultDialog(QDialog):
    """Mostra a transcrição de um arquivo, dentro do app, com botão Copiar."""

    def __init__(self, text: str, name: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setWindowTitle(f"{APP_NAME} — {name}")
        self.setWindowIcon(app_icon())
        self.resize(560, 400)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        head = QLabel(name)
        head.setObjectName("SectionTitle")
        lay.addWidget(head)
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        lay.addWidget(view)
        row = QHBoxLayout()
        row.addStretch()
        copy_btn = QPushButton("Copiar")
        copy_btn.setObjectName("Primary")
        copy_btn.clicked.connect(self._copy)
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        row.addWidget(copy_btn)
        row.addWidget(close_btn)
        lay.addLayout(row)

    def _copy(self) -> None:
        QApplication.clipboard().setText(self._text)


class UpdateDialog(QDialog):
    """Avisa que há uma versão nova, com notas e ações de download."""

    def __init__(self, rel, controller, parent=None):
        super().__init__(parent)
        self._rel = rel
        self._controller = controller
        self.setWindowTitle("Atualização disponível")
        self.setWindowIcon(app_icon())
        self.resize(500, 380)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(12)
        head = QLabel(f"Nova versão disponível: {rel.version}")
        head.setObjectName("SectionTitle")
        lay.addWidget(head)
        notes = QPlainTextEdit(rel.notes or "(sem notas de versão)")
        notes.setReadOnly(True)
        lay.addWidget(notes)
        row = QHBoxLayout()
        row.addStretch()
        if rel.installer_url:
            install_btn = QPushButton("Baixar e instalar")
            install_btn.setObjectName("Primary")
            install_btn.clicked.connect(self._install)
            row.addWidget(install_btn)
        page_btn = QPushButton("Abrir página")
        page_btn.clicked.connect(self._open_page)
        later_btn = QPushButton("Agora não")
        later_btn.clicked.connect(self.reject)
        row.addWidget(page_btn)
        row.addWidget(later_btn)
        lay.addLayout(row)

    def _install(self) -> None:
        self._controller.download_and_install(self._rel)
        self.accept()

    def _open_page(self) -> None:
        import webbrowser

        if self._rel.page_url:
            webbrowser.open(self._rel.page_url)
        self.accept()


class MainWindow(QMainWindow):
    minimizedToTray = Signal()

    def __init__(self, controller: Controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(620, 640)
        self.setAcceptDrops(True)
        self._min_applied = False
        self._loading = True
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_settings)

        tabs = QTabWidget()
        tabs.addTab(self._history_tab(), "Histórico")
        tabs.addTab(self._settings_tab(), "Configurações")

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header())
        outer.addWidget(self._hero())
        outer.addWidget(tabs, 1)
        self.setCentralWidget(central)

        controller.historyChanged.connect(self.refresh_history)
        controller.transcribed.connect(
            lambda t: self.statusBar().showMessage(f"Transcrito: {t[:60]}", 4000)
        )
        controller.failed.connect(lambda m: self.statusBar().showMessage(m, 8000))
        controller.stateChanged.connect(self._on_state)
        controller.fileResult.connect(self._show_file_result)
        controller.fileBusy.connect(self._on_file_busy)
        controller.refineBusy.connect(
            lambda b: self.statusBar().showMessage(
                "Refinando…" if b else "Pronto", 0 if b else 3000
            )
        )
        controller.setupNeeded.connect(self._show_setup)
        controller.pendingChanged.connect(self._update_pending)
        controller.itemRefineBusy.connect(self._on_item_refine_busy)
        controller.updateAvailable.connect(self._show_update)
        controller.updateUpToDate.connect(
            lambda: self.statusBar().showMessage(
                "Você já está na versão mais recente.", 5000
            )
        )
        controller.updateStatus.connect(
            lambda m: self.statusBar().showMessage(m, 6000)
        )
        controller.updateError.connect(
            lambda m: self.statusBar().showMessage(m, 8000)
        )
        self.refresh_history()
        self._update_pending()

    def show_welcome(self, reason: str = "") -> None:
        """Abre os primeiros passos (1ª execução ou falta de configuração)."""
        if getattr(self, "_welcome_open", False):
            return
        self._welcome_open = True
        try:
            self.show()
            self.raise_()
            self.activateWindow()
            WelcomeDialog(self.controller, self, reason).exec()
            self._reload_settings_fields()
        finally:
            self._welcome_open = False

    def _show_setup(self, reason: str) -> None:
        self.show_welcome(reason)

    def _reload_settings_fields(self) -> None:
        """Reflete na aba Configurações o que foi salvo em outro lugar."""
        cfg = self.controller.config
        self._loading = True
        try:
            self._prov_keys = {
                "groq": cfg.groq_api_key,
                "openai": cfg.openai_api_key,
                "gemini": cfg.gemini_api_key,
            }
            self._cur_provider = cfg.provider if cfg.provider in PROVIDERS else "groq"
            i = self.provider_combo.findData(self._cur_provider)
            if i >= 0:
                self.provider_combo.setCurrentIndex(i)
            self.apikey_edit.setText(self._prov_keys[self._cur_provider])
        finally:
            self._loading = False

    def _show_update(self, rel) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        UpdateDialog(rel, self.controller, self).exec()

    # ----- cabeçalho e herói -----
    def _header(self) -> QWidget:
        h = QWidget()
        h.setObjectName("Header")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(30))
        title = QLabel(APP_NAME)
        title.setObjectName("HeaderTitle")
        from . import __version__

        version = QPushButton(f"v{__version__}")
        version.setObjectName("VersionPill")
        version.setCursor(Qt.PointingHandCursor)
        version.setToolTip("Clique para verificar se há atualização")
        version.clicked.connect(lambda: self.controller.check_updates(manual=True))
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addStretch()
        lay.addWidget(version)
        return h

    def _hero(self) -> QWidget:
        w = QWidget()
        w.setObjectName("Hero")
        v = QVBoxLayout(w)
        v.setContentsMargins(18, 22, 18, 18)
        v.setSpacing(14)

        self.record_btn = RecordButton(88)
        self.record_btn.clicked.connect(self.controller.toggle_recording)
        v.addWidget(self.record_btn, alignment=Qt.AlignHCenter)

        self.hero_hint = QLabel()
        self.hero_hint.setObjectName("Muted")
        self.hero_hint.setAlignment(Qt.AlignHCenter)
        self.hero_hint.setTextFormat(Qt.RichText)
        self._refresh_hint()
        v.addWidget(self.hero_hint)

        row = QHBoxLayout()
        row.setSpacing(10)
        row.addStretch()
        row.addWidget(
            _chip("Transcrever arquivo", "headphones", self._open_audio_file)
        )
        self.refine_chip = _chip("Refino", "sparkle", None)
        self.refine_chip.setEnabled(False)
        self.refine_chip.setCursor(Qt.ArrowCursor)
        row.addWidget(self.refine_chip)
        row.addStretch()
        v.addLayout(row)
        self._refresh_hint()  # agora o chip já existe: mostra o atalho de refino
        return w

    def _refresh_hint(self) -> None:
        cfg = self.controller.config
        key = pretty_hotkey(cfg.hotkey)
        self.hero_hint.setText(
            f"Segure <b>{key}</b> &nbsp;ou clique para gravar"
        )
        if hasattr(self, "refine_chip"):
            rk = pretty_hotkey(cfg.refine_hotkey) if cfg.refine_hotkey else "—"
            self.refine_chip.setText(f"  Refino: {rk}")

    # ----- arrastar e soltar arquivos de áudio -----
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls() and any(
            u.isLocalFile() and is_supported(u.toLocalFile())
            for u in event.mimeData().urls()
        ):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # noqa: N802
        for url in event.mimeData().urls():
            if not url.isLocalFile():
                continue
            path = url.toLocalFile()
            if is_supported(path):
                self.controller.transcribe_file(path)
            else:
                self.statusBar().showMessage(f"Formato não suportado: {path}", 5000)

    def _open_audio_file(self) -> None:
        patterns = " ".join(f"*{e}" for e in sorted(SUPPORTED_EXTS))
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher áudio para transcrever",
            "",
            f"Áudio ({patterns});;Todos os arquivos (*.*)",
        )
        if path:
            self.controller.transcribe_file(path)

    def _show_file_result(self, text: str, name: str) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        TranscriptionResultDialog(text, name, self).exec()

    def _on_file_busy(self, busy: bool) -> None:
        if busy:
            self.statusBar().showMessage("Transcrevendo arquivo…")
        else:
            self.statusBar().showMessage("Pronto", 3000)

    # ----- aba Histórico -----
    def _history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(10)

        top = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Buscar no histórico…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda _: self.refresh_history())
        hint = self.search_edit
        clear_btn = QPushButton()
        clear_btn.setObjectName("IconBtn")
        clear_btn.setIcon(icons.icon("trash", 18, "#9A93A6"))
        clear_btn.setFixedSize(30, 30)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setToolTip("Limpar histórico")
        clear_btn.clicked.connect(self._clear_history)
        top.addWidget(hint, 1)
        top.addWidget(clear_btn)
        lay.addLayout(top)

        self.drop_hint = QLabel("Arraste um áudio aqui para transcrever")
        self.drop_hint.setObjectName("Muted")
        lay.addWidget(self.drop_hint)

        # Faixa que aparece só quando algum áudio ficou para reenviar.
        self.pending_bar = QFrame()
        self.pending_bar.setObjectName("Card")
        pb = QHBoxLayout(self.pending_bar)
        pb.setContentsMargins(12, 8, 10, 8)
        pb.setSpacing(8)
        self.pending_label = QLabel()
        pb.addWidget(self.pending_label, 1)
        retry_btn = QPushButton("Tentar de novo")
        retry_btn.setObjectName("Primary")
        retry_btn.setCursor(Qt.PointingHandCursor)
        retry_btn.clicked.connect(self.controller.retry_pending)
        discard_btn = QPushButton("Descartar")
        discard_btn.setCursor(Qt.PointingHandCursor)
        discard_btn.clicked.connect(self._discard_pending)
        pb.addWidget(retry_btn)
        pb.addWidget(discard_btn)
        self.pending_bar.hide()
        lay.addWidget(self.pending_bar)

        self.history_list = QListWidget()
        self.history_list.setObjectName("HistoryList")
        self.history_list.setSpacing(6)
        self.history_list.setSelectionMode(QAbstractItemView.NoSelection)
        # Sem barras visíveis: a roda do mouse continua rolando, e a largura da
        # área visível para de mudar (era o que cortava os cartões).
        self.history_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history_list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        lay.addWidget(self.history_list, 1)

        self.empty_label = QLabel("Nada por aqui ainda — grave algo para começar.")
        self.empty_label.setObjectName("Muted")
        self.empty_label.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.empty_label)
        return w

    def refresh_history(self) -> None:
        self.history_list.clear()
        size = self.controller.config.history_size
        query = self.search_edit.text() if hasattr(self, "search_edit") else ""
        entries = (
            self.controller.history.search(query, size)
            if query.strip()
            else self.controller.history.recent(size)
        )
        self.empty_label.setVisible(not entries)
        self.empty_label.setText(
            "Nada encontrado para essa busca."
            if query.strip()
            else "Nada por aqui ainda — grave algo para começar."
        )
        self.history_list.setVisible(bool(entries))
        self._cards = {}
        for entry in entries:
            card = HistoryCard(
                entry, self._copy_text, self._refine_entry, self._delete_entry
            )
            self._cards[entry.uid] = card
            item = QListWidgetItem()
            # Largura 1: a lista estica o item até a área visível sozinha.
            item.setSizeHint(QSize(1, max(50, card.sizeHint().height())))
            self.history_list.addItem(item)
            self.history_list.setItemWidget(item, card)

    def _update_pending(self, count: int | None = None) -> None:
        if count is None:
            count = len(self.controller.pending_audios())
        self.pending_bar.setVisible(count > 0)
        if count:
            plural = "s" if count > 1 else ""
            self.pending_label.setText(
                f"{count} áudio{plural} não enviado{plural} (falha de conexão)"
            )

    def _discard_pending(self) -> None:
        if (
            QMessageBox.question(
                self, "Descartar áudios", "Apagar os áudios que não foram enviados?"
            )
            == QMessageBox.Yes
        ):
            self.controller.discard_pending()
            self._update_pending()

    def _delete_entry(self, uid: str) -> None:
        if self.controller.history.remove(uid):
            self.refresh_history()
            self.statusBar().showMessage("Item apagado.", 2000)

    def _refine_entry(self, uid: str) -> None:
        self.statusBar().showMessage("Refinando o texto…", 0)
        self.controller.refine_history_item(uid)

    def _on_item_refine_busy(self, uid: str, busy: bool) -> None:
        card = getattr(self, "_cards", {}).get(uid)
        if card is not None:
            card.set_busy(busy)
        if not busy:
            self.statusBar().showMessage("Texto refinado ✓", 3000)

    def _copy_text(self, text: str) -> None:
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Copiado!", 2000)

    def _clear_history(self) -> None:
        if (
            QMessageBox.question(self, "Limpar histórico", "Apagar todo o histórico?")
            == QMessageBox.Yes
        ):
            self.controller.history.clear()
            self.refresh_history()

    # ----- aba Configurações -----
    def _settings_tab(self) -> QWidget:
        cfg = self.controller.config
        self._loading = True  # evita salvar enquanto os campos são preenchidos
        page = QWidget()
        col = QVBoxLayout(page)
        col.setContentsMargins(16, 14, 16, 14)
        col.setSpacing(12)

        # --- Gravação ---
        card, form = _section("Gravação")
        self.hotkey_btn = HotkeyCaptureButton(cfg.hotkey)
        self.threshold_spin = NoScrollSpinBox()
        self.threshold_spin.setRange(100, 2000)
        self.threshold_spin.setSingleStep(50)
        self.threshold_spin.setValue(cfg.tap_threshold_ms)
        self.threshold_spin.setSuffix(" ms")
        self.language_edit = QLineEdit(cfg.language)
        self.device_combo = NoScrollComboBox()
        self.device_combo.addItem("Padrão do sistema", "")
        for name in list_input_devices():
            self.device_combo.addItem(name, name)
        _di = self.device_combo.findData(cfg.input_device)
        if _di < 0 and cfg.input_device:  # microfone salvo não está conectado
            self.device_combo.addItem(f"{cfg.input_device} (desconectado)",
                                      cfg.input_device)
            _di = self.device_combo.count() - 1
        self.device_combo.setCurrentIndex(max(0, _di))
        self.sound_check = QCheckBox("Tocar um bipe ao iniciar e parar a gravação")
        self.sound_check.setChecked(cfg.sound_enabled)
        form.addRow("Atalho", self.hotkey_btn)
        form.addRow("Microfone", self.device_combo)
        form.addRow("Limiar toque/segurar", self.threshold_spin)
        form.addRow("Idioma", self.language_edit)
        form.addRow("", self.sound_check)
        col.addWidget(card)

        # --- Aparência ---
        card, form = _section("Aparência")
        self.theme_combo = NoScrollComboBox()
        self.theme_combo.addItem("Automático (segue o Windows)", "auto")
        self.theme_combo.addItem("Claro", "light")
        self.theme_combo.addItem("Escuro", "dark")
        _ti = self.theme_combo.findData(cfg.theme_mode)
        self.theme_combo.setCurrentIndex(_ti if _ti >= 0 else 0)
        form.addRow("Tema", self.theme_combo)
        col.addWidget(card)

        # --- Saída do texto ---
        card, form = _section("Saída do texto")
        self.output_combo = NoScrollComboBox()
        self.output_combo.addItem("Colar onde o cursor estiver", "paste")
        self.output_combo.addItem("Somente copiar", "clipboard_only")
        _oi = self.output_combo.findData(cfg.output_mode)
        self.output_combo.setCurrentIndex(_oi if _oi >= 0 else 0)
        self.restore_check = QCheckBox("Restaurar o clipboard anterior após colar")
        self.restore_check.setChecked(cfg.restore_clipboard)
        self.ai_note_box = QCheckBox("Acrescentar aviso de IA ao final")
        self.ai_note_box.setChecked(cfg.ai_note_enabled)
        self.ai_note_edit = QLineEdit(cfg.ai_note_text)
        self.ai_note_edit.setPlaceholderText(AI_NOTE)
        self.history_spin = NoScrollSpinBox()
        self.history_spin.setRange(1, 1000)
        self.history_spin.setValue(cfg.history_size)
        self.autostart_check = QCheckBox("Iniciar com o Windows")
        self.autostart_check.setChecked(cfg.autostart)
        form.addRow("Modo", self.output_combo)
        form.addRow("", self.restore_check)
        form.addRow("", self.ai_note_box)
        form.addRow("Texto do aviso", self.ai_note_edit)
        form.addRow("Itens no histórico", self.history_spin)
        form.addRow("", self.autostart_check)
        col.addWidget(card)

        # --- Transcrição ---
        card, form = _section("Transcrição")
        self._prov_keys = {
            "groq": cfg.groq_api_key,
            "openai": cfg.openai_api_key,
            "gemini": cfg.gemini_api_key,
        }
        self._prov_models = {
            "groq": cfg.groq_model,
            "openai": cfg.openai_model,
            "gemini": cfg.gemini_model,
        }
        self._cur_provider = cfg.provider if cfg.provider in PROVIDERS else "groq"
        self.provider_combo = NoScrollComboBox()
        for _p in PROVIDERS:
            self.provider_combo.addItem(PROVIDER_LABELS[_p], _p)
        _pi = self.provider_combo.findData(self._cur_provider)
        self.provider_combo.setCurrentIndex(_pi if _pi >= 0 else 0)
        self.model_edit = QLineEdit(
            self._prov_models[self._cur_provider] or DEFAULT_MODELS[self._cur_provider]
        )
        self.apikey_edit = QLineEdit(self._prov_keys[self._cur_provider])
        self.apikey_edit.setEchoMode(QLineEdit.Password)
        self.apikey_edit.setPlaceholderText("cole a chave do provedor selecionado")
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.hint_edit = QLineEdit(cfg.transcribe_hint)
        self.hint_edit.setPlaceholderText(
            "ex.: Águia Brindes, Evolution Go, Prisma, funil, romaneio"
        )
        self.hint_edit.setToolTip(
            "Termos e nomes que você usa muito. Ajuda o modelo a não errar a "
            "grafia (ex.: 'correção' virando 'coleção')."
        )
        form.addRow("Provedor", self.provider_combo)
        form.addRow("Modelo", self.model_edit)
        form.addRow("Chave (API)", self.apikey_edit)
        form.addRow("Termos frequentes", self.hint_edit)
        col.addWidget(card)

        # --- Refinamento ---
        card, form = _section("Refinamento (2º atalho)")
        self.refine_hotkey_btn = HotkeyCaptureButton(cfg.refine_hotkey)
        self.refiner_combo = NoScrollComboBox()
        for _rp in PROVIDERS:
            self.refiner_combo.addItem(PROVIDER_LABELS[_rp], _rp)
        _ri = self.refiner_combo.findData(cfg.refiner_provider)
        self.refiner_combo.setCurrentIndex(_ri if _ri >= 0 else 0)
        self.refiner_model_edit = QLineEdit(
            cfg.refiner_model or DEFAULT_CHAT_MODELS.get(cfg.refiner_provider, "")
        )
        self.refiner_combo.currentIndexChanged.connect(self._on_refiner_changed)
        self.refine_preset_combo = NoScrollComboBox()
        for _k, (_lbl, _txt) in REFINE_PRESETS.items():
            self.refine_preset_combo.addItem(_lbl, _k)
        self.refine_preset_combo.addItem("Personalizado", "custom")
        _cur_preset = match_preset(cfg.refine_prompt)
        _si = self.refine_preset_combo.findData(_cur_preset)
        self.refine_preset_combo.setCurrentIndex(_si if _si >= 0 else 0)
        self.refine_preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        self.refine_prompt_edit = QPlainTextEdit(
            cfg.refine_prompt or DEFAULT_REFINE_PROMPT
        )
        self.refine_prompt_edit.setFixedHeight(110)
        self.context_box = QCheckBox("Usar pasta de contexto no refinamento")
        self.context_box.setChecked(cfg.context_enabled)
        self.context_dir_edit = QLineEdit(cfg.context_dir)
        self.context_dir_edit.setPlaceholderText("pasta com .md/.txt de referência")
        context_browse = QPushButton()
        context_browse.setObjectName("IconBtn")
        context_browse.setIcon(icons.icon("folder", 18, "#9A93A6"))
        context_browse.setFixedSize(32, 32)
        context_browse.setCursor(Qt.PointingHandCursor)
        context_browse.setToolTip("Escolher pasta")
        context_browse.clicked.connect(self._browse_context)
        context_row = QWidget()
        _crl = QHBoxLayout(context_row)
        _crl.setContentsMargins(0, 0, 0, 0)
        _crl.setSpacing(8)
        _crl.addWidget(self.context_dir_edit)
        _crl.addWidget(context_browse)
        form.addRow("Atalho", self.refine_hotkey_btn)
        form.addRow("Provedor", self.refiner_combo)
        form.addRow("Modelo", self.refiner_model_edit)
        form.addRow("Estilo", self.refine_preset_combo)
        form.addRow("Prompt", self.refine_prompt_edit)
        form.addRow("", self.context_box)
        form.addRow("Pasta de contexto", context_row)
        col.addWidget(card)

        # --- Atualizações ---
        card, form = _section("Atualizações")
        self.update_check_box = QCheckBox("Verificar atualizações ao iniciar")
        self.update_check_box.setChecked(cfg.check_updates_on_start)
        check_now_btn = QPushButton("Verificar agora")
        check_now_btn.setCursor(Qt.PointingHandCursor)
        check_now_btn.clicked.connect(
            lambda: self.controller.check_updates(manual=True)
        )
        form.addRow("", self.update_check_box)
        form.addRow("", check_now_btn)
        col.addWidget(card)

        card, form = _section("Ajuda")
        help_btn = QPushButton("Ver primeiros passos")
        help_btn.setCursor(Qt.PointingHandCursor)
        help_btn.clicked.connect(lambda: self.show_welcome())
        logs_btn = QPushButton("Abrir pasta de logs")
        logs_btn.setCursor(Qt.PointingHandCursor)
        logs_btn.setToolTip(
            "Registros de erro do app — úteis para diagnosticar problemas."
        )
        logs_btn.clicked.connect(self._open_logs)
        form.addRow("", help_btn)
        form.addRow("", logs_btn)
        col.addWidget(card)

        note = QLabel("As alterações são salvas automaticamente.")
        note.setObjectName("Muted")
        note.setAlignment(Qt.AlignHCenter)
        col.addWidget(note)
        col.addStretch()

        self._connect_autosave()
        self._loading = False

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        # Vertical escondida (rola com a roda). A horizontal fica "se precisar":
        # é rede de segurança — melhor uma barra rara do que cortar conteúdo.
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    def _on_provider_changed(self) -> None:
        # guarda o que está nos campos para o provedor anterior
        self._prov_keys[self._cur_provider] = self.apikey_edit.text().strip()
        self._prov_models[self._cur_provider] = self.model_edit.text().strip()
        p = self.provider_combo.currentData()
        self._cur_provider = p
        self.model_edit.setText(self._prov_models.get(p) or DEFAULT_MODELS[p])
        self.apikey_edit.setText(self._prov_keys.get(p, ""))

    # ----- salvamento ao vivo -----
    def _connect_autosave(self) -> None:
        """Liga todos os campos ao salvamento automático (com debounce)."""
        for w in (self.hotkey_btn, self.refine_hotkey_btn):
            w.changed.connect(self._queue_save)
        for w in (self.threshold_spin, self.history_spin):
            w.valueChanged.connect(self._queue_save)
        for w in (
            self.device_combo,
            self.theme_combo,
            self.output_combo,
            self.provider_combo,
            self.refiner_combo,
            self.refine_preset_combo,
        ):
            w.currentIndexChanged.connect(self._queue_save)
        for w in (
            self.restore_check,
            self.sound_check,
            self.ai_note_box,
            self.autostart_check,
            self.context_box,
            self.update_check_box,
        ):
            w.toggled.connect(self._queue_save)
        # Campos de texto: salva ao sair do campo (evita gravar meia palavra).
        for w in (
            self.language_edit,
            self.ai_note_edit,
            self.model_edit,
            self.apikey_edit,
            self.hint_edit,
            self.refiner_model_edit,
            self.context_dir_edit,
        ):
            w.editingFinished.connect(self._queue_save)
        self.refine_prompt_edit.textChanged.connect(self._queue_save)

    def _queue_save(self, *_args) -> None:
        if getattr(self, "_loading", False):
            return
        self._save_timer.start(600)

    def _flush_save(self) -> None:
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_settings()

    def _on_preset_changed(self) -> None:
        key = self.refine_preset_combo.currentData()
        if key in REFINE_PRESETS:
            self.refine_prompt_edit.setPlainText(REFINE_PRESETS[key][1])

    def _on_refiner_changed(self) -> None:
        p = self.refiner_combo.currentData()
        self.refiner_model_edit.setText(DEFAULT_CHAT_MODELS.get(p, ""))

    def _open_logs(self) -> None:
        from .logs import open_log_folder

        open_log_folder()
        self.statusBar().showMessage("Abri a pasta de logs.", 3000)

    def _browse_context(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Escolher pasta de contexto")
        if folder:
            self.context_dir_edit.setText(folder)

    def _save_settings(self) -> None:
        self._prov_keys[self._cur_provider] = self.apikey_edit.text().strip()
        self._prov_models[self._cur_provider] = self.model_edit.text().strip()
        cfg = Config(
            hotkey=self.hotkey_btn.value(),
            tap_threshold_ms=self.threshold_spin.value(),
            language=self.language_edit.text().strip() or "pt",
            input_device=self.device_combo.currentData() or "",
            theme_mode=self.theme_combo.currentData(),
            sound_enabled=self.sound_check.isChecked(),
            output_mode=self.output_combo.currentData(),
            restore_clipboard=self.restore_check.isChecked(),
            history_size=self.history_spin.value(),
            autostart=self.autostart_check.isChecked(),
            provider=self.provider_combo.currentData(),
            groq_model=self._prov_models["groq"] or DEFAULT_MODELS["groq"],
            groq_api_key=self._prov_keys["groq"],
            openai_model=self._prov_models["openai"] or DEFAULT_MODELS["openai"],
            openai_api_key=self._prov_keys["openai"],
            gemini_model=self._prov_models["gemini"] or DEFAULT_MODELS["gemini"],
            gemini_api_key=self._prov_keys["gemini"],
            refine_hotkey=self.refine_hotkey_btn.value(),
            refiner_provider=self.refiner_combo.currentData(),
            refiner_model=self.refiner_model_edit.text().strip()
            or DEFAULT_CHAT_MODELS.get(self.refiner_combo.currentData(), ""),
            refine_prompt=self.refine_prompt_edit.toPlainText().strip()
            or DEFAULT_REFINE_PROMPT,
            refine_preset=match_preset(self.refine_prompt_edit.toPlainText()),
            transcribe_hint=self.hint_edit.text().strip(),
            context_enabled=self.context_box.isChecked(),
            context_dir=self.context_dir_edit.text().strip(),
            check_updates_on_start=self.update_check_box.isChecked(),
            ai_note_enabled=self.ai_note_box.isChecked(),
            ai_note_text=self.ai_note_edit.text().strip() or AI_NOTE,
            onboarding_done=self.controller.config.onboarding_done,
        )
        # Atalho inválido: avisa na barra de status e não grava (sem modal, já
        # que o salvamento agora é automático).
        try:
            parse_hotkey(cfg.hotkey)
            if cfg.refine_hotkey:
                parse_hotkey(cfg.refine_hotkey)
        except ValueError as e:
            self.statusBar().showMessage(f"Atalho inválido: {e}", 6000)
            return
        save_config(cfg)
        self.controller.apply_config(cfg)
        try:
            from .autostart import set_autostart

            set_autostart(cfg.autostart)
        except Exception:  # noqa: BLE001
            pass
        self._refresh_hint()
        self.refresh_history()
        self.statusBar().showMessage("Salvo ✓", 2000)

    def _on_state(self, state: str) -> None:
        labels = {
            "idle": "Pronto",
            "recording": "Gravando…",
            "transcribing": "Transcrevendo…",
        }
        self.statusBar().showMessage(labels.get(state, state))
        if hasattr(self, "record_btn"):
            self.record_btn.set_recording(state == "recording")

    def showEvent(self, event):  # noqa: N802
        super().showEvent(event)
        # A janela não pode ficar menor do que o conteúdo precisa. Como o
        # QScrollArea esconde essa necessidade (ele corta em vez de reclamar),
        # calculamos o mínimo depois do primeiro layout — assim vale também
        # para telas com escala 125%/150%, onde a fonte é maior.
        if not self._min_applied:
            self._min_applied = True
            need = self.centralWidget().minimumSizeHint().width() + 24
            self.setMinimumSize(max(480, need), 420)

    def closeEvent(self, event):  # noqa: N802 — fecha para a bandeja
        self._flush_save()  # não perde edição pendente ao fechar
        event.ignore()
        self.hide()
        self.minimizedToTray.emit()


class TrayApp:
    def __init__(self, controller: Controller, window: MainWindow):
        self.controller = controller
        self.window = window
        self.icons = {
            "idle": tray_icon("idle"),
            "recording": tray_icon("recording"),
            "transcribing": tray_icon("transcribing"),
        }
        self.tray = QSystemTrayIcon(self.icons["idle"])
        self.tray.setToolTip(f"{APP_NAME} — Pronto")

        menu = QMenu()
        open_action = QAction("Abrir", menu)
        open_action.triggered.connect(self.show_window)
        file_action = QAction("Transcrever arquivo de áudio…", menu)
        file_action.triggered.connect(window._open_audio_file)
        help_action = QAction("Primeiros passos…", menu)
        help_action.triggered.connect(lambda: window.show_welcome())
        update_action = QAction("Verificar atualizações…", menu)
        update_action.triggered.connect(lambda: controller.check_updates(manual=True))
        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(open_action)
        menu.addAction(file_action)
        menu.addAction(help_action)
        menu.addAction(update_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        controller.stateChanged.connect(self._on_state)
        controller.fileBusy.connect(self._on_file_busy)
        controller.refineBusy.connect(self._on_file_busy)
        self._notified = False
        window.minimizedToTray.connect(self._notify_minimized)
        self.tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def show_window(self) -> None:
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def _on_state(self, state: str) -> None:
        self.tray.setIcon(self.icons.get(state, self.icons["idle"]))
        tips = {
            "idle": "Pronto",
            "recording": "Gravando…",
            "transcribing": "Transcrevendo…",
        }
        self.tray.setToolTip(f"{APP_NAME} — {tips.get(state, '')}")

    def _on_file_busy(self, busy: bool) -> None:
        if busy:
            self.tray.setIcon(self.icons["transcribing"])
            self.tray.setToolTip(f"{APP_NAME} — Transcrevendo…")
        else:
            self.tray.setIcon(self.icons["idle"])
            self.tray.setToolTip(f"{APP_NAME} — Pronto")

    def _notify_minimized(self) -> None:
        if self._notified:
            return
        self._notified = True
        self.tray.showMessage(
            "Fala AI",
            "Continuo rodando aqui. Clique no ícone (ou no app) para reabrir.",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )

    def _quit(self) -> None:
        self.controller.shutdown()
        QApplication.quit()
