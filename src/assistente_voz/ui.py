"""Interface: bandeja (tray) + janela única com abas Histórico e Configurações."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
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
    QSpinBox,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .app import Controller
from .audiofile import SUPPORTED_EXTS, is_supported
from .config import Config, save_config
from .hotkey import parse_hotkey
from .resources import app_icon, logo_pixmap, tray_icon

APP_NAME = "Fala AI"


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


class HotkeyCaptureButton(QPushButton):
    """Captura a próxima combinação pressionada e a grava como atalho."""

    def __init__(self, value: str, parent=None):
        super().__init__(parent)
        self._value = value
        self._capturing = False
        self._refresh()
        self.clicked.connect(self._begin)

    def value(self) -> str:
        return self._value

    def _refresh(self) -> None:
        self.setText("Pressione o atalho…" if self._capturing else self._value)

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


class TranscriptionResultDialog(QDialog):
    """Mostra a transcrição de um arquivo, dentro do app, com botão Copiar."""

    def __init__(self, text: str, name: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setWindowTitle(f"{APP_NAME} — {name}")
        self.setWindowIcon(app_icon())
        self.resize(540, 380)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Áudio: {name}"))
        view = QPlainTextEdit(text)
        view.setReadOnly(True)
        lay.addWidget(view)
        row = QHBoxLayout()
        row.addStretch()
        copy_btn = QPushButton("Copiar")
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
        self.resize(480, 360)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Nova versão disponível: {rel.version}"))
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
    def __init__(self, controller: Controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(app_icon())
        self.resize(580, 500)
        self.setAcceptDrops(True)

        tabs = QTabWidget()
        tabs.addTab(self._history_tab(), "Histórico")
        tabs.addTab(self._settings_tab(), "Configurações")

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._header())
        outer.addWidget(tabs)
        self.setCentralWidget(central)

        controller.historyChanged.connect(self.refresh_history)
        controller.transcribed.connect(
            lambda t: self.statusBar().showMessage(f"Transcrito: {t[:60]}", 4000)
        )
        controller.failed.connect(lambda m: self.statusBar().showMessage(m, 8000))
        controller.stateChanged.connect(self._on_state)
        controller.fileResult.connect(self._show_file_result)
        controller.fileBusy.connect(self._on_file_busy)
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

    def _show_update(self, rel) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
        UpdateDialog(rel, self.controller, self).exec()

    def _header(self) -> QWidget:
        h = QWidget()
        h.setObjectName("Header")
        lay = QHBoxLayout(h)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(logo_pixmap(34))
        title = QLabel(APP_NAME)
        title.setObjectName("HeaderTitle")
        lay.addWidget(logo)
        lay.addWidget(title)
        lay.addStretch()
        return h

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
            self.statusBar().showMessage("⏳ Transcrevendo arquivo…")
        else:
            self.statusBar().showMessage("Pronto", 3000)

    # ----- aba Histórico -----
    def _history_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        top = QHBoxLayout()
        file_btn = QPushButton("🎧 Transcrever arquivo de áudio…")
        file_btn.setObjectName("Primary")
        file_btn.clicked.connect(self._open_audio_file)
        top.addWidget(file_btn)
        top.addStretch()
        lay.addLayout(top)
        hint = QLabel(
            "Ou arraste um áudio aqui (WhatsApp .opus, .mp3, .m4a, .wav…) "
            "para transcrever."
        )
        hint.setObjectName("Muted")
        lay.addWidget(hint)

        lay.addWidget(QLabel("Dê duplo clique (ou use o botão) para copiar:"))
        self.history_list = QListWidget()
        self.history_list.itemDoubleClicked.connect(self._copy_item)
        lay.addWidget(self.history_list)
        row = QHBoxLayout()
        copy_btn = QPushButton("Copiar selecionado")
        copy_btn.clicked.connect(self._copy_selected)
        clear_btn = QPushButton("Limpar histórico")
        clear_btn.clicked.connect(self._clear_history)
        row.addWidget(copy_btn)
        row.addWidget(clear_btn)
        row.addStretch()
        lay.addLayout(row)
        return w

    def refresh_history(self) -> None:
        self.history_list.clear()
        for entry in self.controller.history.recent(self.controller.config.history_size):
            item = QListWidgetItem(f"[{entry.timestamp}]  {entry.text}")
            item.setData(Qt.UserRole, entry.text)
            self.history_list.addItem(item)

    def _copy_item(self, item: QListWidgetItem) -> None:
        QApplication.clipboard().setText(item.data(Qt.UserRole))
        self.statusBar().showMessage("Copiado!", 2000)

    def _copy_selected(self) -> None:
        item = self.history_list.currentItem()
        if item:
            self._copy_item(item)

    def _clear_history(self) -> None:
        self.controller.history.clear()
        self.refresh_history()

    # ----- aba Configurações -----
    def _settings_tab(self) -> QWidget:
        cfg = self.controller.config
        w = QWidget()
        form = QFormLayout(w)

        self.hotkey_btn = HotkeyCaptureButton(cfg.hotkey)
        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(100, 2000)
        self.threshold_spin.setSingleStep(50)
        self.threshold_spin.setValue(cfg.tap_threshold_ms)
        self.threshold_spin.setSuffix(" ms")
        self.language_edit = QLineEdit(cfg.language)
        self.output_combo = QComboBox()
        self.output_combo.addItems(["paste", "clipboard_only"])
        self.output_combo.setCurrentText(cfg.output_mode)
        self.restore_check = QCheckBox("Restaurar o clipboard anterior após colar")
        self.restore_check.setChecked(cfg.restore_clipboard)
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1, 1000)
        self.history_spin.setValue(cfg.history_size)
        self.autostart_check = QCheckBox("Iniciar com o Windows")
        self.autostart_check.setChecked(cfg.autostart)
        self.model_edit = QLineEdit(cfg.groq_model)
        self.apikey_edit = QLineEdit(cfg.groq_api_key)
        self.apikey_edit.setEchoMode(QLineEdit.Password)
        self.apikey_edit.setPlaceholderText("vazio = usa GROQ_API_KEY do ambiente")
        self.update_repo_edit = QLineEdit(cfg.update_repo)
        self.update_repo_edit.setPlaceholderText("usuario/repositorio (GitHub)")
        self.update_check_box = QCheckBox("Verificar atualizações ao iniciar")
        self.update_check_box.setChecked(cfg.check_updates_on_start)
        check_now_btn = QPushButton("Verificar atualizações agora")
        check_now_btn.clicked.connect(
            lambda: self.controller.check_updates(manual=True)
        )
        save_btn = QPushButton("Salvar")
        save_btn.setObjectName("Primary")
        save_btn.clicked.connect(self._save_settings)

        form.addRow("Atalho:", self.hotkey_btn)
        form.addRow("Limiar toque/segurar:", self.threshold_spin)
        form.addRow("Idioma:", self.language_edit)
        form.addRow("Modo de saída:", self.output_combo)
        form.addRow("", self.restore_check)
        form.addRow("Itens no histórico:", self.history_spin)
        form.addRow("", self.autostart_check)
        form.addRow("Modelo Groq:", self.model_edit)
        form.addRow("Chave Groq:", self.apikey_edit)
        form.addRow("Repositório de updates:", self.update_repo_edit)
        form.addRow("", self.update_check_box)
        form.addRow("", check_now_btn)
        form.addRow(save_btn)
        return w

    def _save_settings(self) -> None:
        cfg = Config(
            hotkey=self.hotkey_btn.value(),
            tap_threshold_ms=self.threshold_spin.value(),
            language=self.language_edit.text().strip() or "pt",
            output_mode=self.output_combo.currentText(),
            restore_clipboard=self.restore_check.isChecked(),
            history_size=self.history_spin.value(),
            autostart=self.autostart_check.isChecked(),
            groq_model=self.model_edit.text().strip() or "whisper-large-v3",
            groq_api_key=self.apikey_edit.text().strip(),
            update_repo=self.update_repo_edit.text().strip(),
            check_updates_on_start=self.update_check_box.isChecked(),
        )
        try:
            parse_hotkey(cfg.hotkey)
        except ValueError as e:
            QMessageBox.warning(self, "Atalho inválido", str(e))
            return
        save_config(cfg)
        self.controller.apply_config(cfg)
        try:
            from .autostart import set_autostart

            set_autostart(cfg.autostart)
        except Exception:  # noqa: BLE001
            pass
        self.statusBar().showMessage("Configurações salvas.", 3000)

    def _on_state(self, state: str) -> None:
        labels = {
            "idle": "Pronto",
            "recording": "🎙️ Gravando…",
            "transcribing": "⏳ Transcrevendo…",
        }
        self.statusBar().showMessage(labels.get(state, state))

    def closeEvent(self, event):  # noqa: N802 — fecha para a bandeja
        event.ignore()
        self.hide()


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
        update_action = QAction("Verificar atualizações…", menu)
        update_action.triggered.connect(lambda: controller.check_updates(manual=True))
        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(self._quit)
        menu.addAction(open_action)
        menu.addAction(file_action)
        menu.addAction(update_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        controller.stateChanged.connect(self._on_state)
        controller.fileBusy.connect(self._on_file_busy)
        self.tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.show_window()

    def show_window(self) -> None:
        self.window.show()
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
            self.tray.setToolTip(f"{APP_NAME} — Transcrevendo arquivo…")
        else:
            self.tray.setIcon(self.icons["idle"])
            self.tray.setToolTip(f"{APP_NAME} — Pronto")

    def _quit(self) -> None:
        self.controller.shutdown()
        QApplication.quit()
