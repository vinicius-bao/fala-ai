"""Controlador: orquestra atalho, gravação, transcrição e entrega.

Eventos do atalho chegam pela thread do pynput e são marshalados para a thread
do Qt via signals (QueuedConnection). A transcrição (rede) roda numa thread
separada para não travar a interface.
"""

from __future__ import annotations

import os
import threading
import time

from PySide6.QtCore import QObject, Qt, Signal

from .activation import Action, Activation, State
from .audio import Recorder
from .config import (
    DEFAULT_CHAT_MODELS,
    Config,
    append_note,
    config_dir,
    provider_model,
    resolve_provider_key,
)
from .history import History, Transcription
from .hotkey import HotkeyListener
from .output import TextOutput
from .refiner import make_refiner
from .transcription import make_engine


class Controller(QObject):
    stateChanged = Signal(str)          # "idle" | "recording" | "transcribing"
    transcribed = Signal(str)
    failed = Signal(str)
    historyChanged = Signal()
    fileResult = Signal(str, str)       # transcrição de arquivo: (texto, nome)
    fileBusy = Signal(bool)             # transcrevendo um arquivo
    updateAvailable = Signal(object)    # Release (há versão nova)
    updateUpToDate = Signal()           # já está atualizado (só em checagem manual)
    updateStatus = Signal(str)          # mensagens de progresso da atualização
    updateError = Signal(str)
    quitRequested = Signal()            # pedir encerramento (ex.: após abrir instalador)
    configApplied = Signal()           # configurações aplicadas (ex.: reaplicar tema)
    refineBusy = Signal(bool)          # refinando a transcrição
    setupNeeded = Signal(str)          # falta configuração (motivo legível)
    pendingChanged = Signal(int)       # quantos áudios ficaram para reenviar
    itemRefineBusy = Signal(str, bool)  # (uid, refinando) — item do histórico
    overlayState = Signal(str, str)    # pop-up: (recording|processing|done|hidden, texto)

    # internos: trazem eventos de outras threads para a thread do Qt
    _hkStart = Signal()
    _hkRelease = Signal(float)
    _hkStartRefine = Signal()
    _hkReleaseRefine = Signal(float)
    _refineReady = Signal(str, float)
    _refineFailed = Signal(str, str, float)   # (erro, texto cru, duração)
    _itemRefineReady = Signal(str, str)       # (uid, texto refinado)
    _itemRefineFailed = Signal(str, str)      # (uid, erro)
    _transcriptionReady = Signal(str, float)
    _transcriptionFailed = Signal(str, object)  # (mensagem, wav bytes)
    _fileReady = Signal(str, str)
    _fileFailed = Signal(str)
    _updateDone = Signal(object)        # (Release | None)
    _updateFail = Signal(str)
    _installerReady = Signal(str)       # caminho do instalador baixado

    def __init__(self, config: Config, history: History):
        super().__init__()
        self.config = config
        self.history = history
        self._activation = Activation(config.tap_threshold_ms)
        self._recorder = Recorder(device=config.input_device)
        self._output = TextOutput()
        self._engine = None
        self._refiner = None
        self._pending_refine = False
        self._hotkey: HotkeyListener | None = None
        self._hotkey_refine: HotkeyListener | None = None

        self._hkStart.connect(self._on_start, Qt.QueuedConnection)
        self._hkRelease.connect(self._on_release, Qt.QueuedConnection)
        self._transcriptionReady.connect(self._on_ready, Qt.QueuedConnection)
        self._transcriptionFailed.connect(self._on_failed, Qt.QueuedConnection)
        self._fileReady.connect(self._on_file_ready, Qt.QueuedConnection)
        self._fileFailed.connect(self._on_file_failed, Qt.QueuedConnection)
        self._updateDone.connect(self._on_update_done, Qt.QueuedConnection)
        self._updateFail.connect(self._on_update_fail, Qt.QueuedConnection)
        self._installerReady.connect(self._on_installer_ready, Qt.QueuedConnection)
        self._hkStartRefine.connect(self._on_start_refine, Qt.QueuedConnection)
        self._hkReleaseRefine.connect(self._on_release, Qt.QueuedConnection)
        self._refineReady.connect(self._on_refine_ready, Qt.QueuedConnection)
        self._refineFailed.connect(self._on_refine_failed, Qt.QueuedConnection)
        self._itemRefineReady.connect(self._on_item_refine_ready, Qt.QueuedConnection)
        self._itemRefineFailed.connect(self._on_item_refine_failed, Qt.QueuedConnection)
        self._update_manual = False

    # ---- ciclo de vida ----
    def start(self) -> None:
        self._rebuild_engine()
        self._rebuild_refiner()
        self._hotkey = HotkeyListener(
            self.config.hotkey,
            on_start=self._hkStart.emit,
            on_release=self._hkRelease.emit,
        )
        try:
            self._hotkey.start()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Não consegui registrar o atalho: {e}")
        self._start_refine_hotkey()

    def _start_refine_hotkey(self) -> None:
        if self._hotkey_refine is not None:
            self._hotkey_refine.stop()
            self._hotkey_refine = None
        spec = self.config.refine_hotkey.strip()
        if not spec:
            return
        try:
            self._hotkey_refine = HotkeyListener(
                spec,
                on_start=self._hkStartRefine.emit,
                on_release=self._hkReleaseRefine.emit,
            )
            self._hotkey_refine.start()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Atalho de refino inválido: {e}")

    def shutdown(self) -> None:
        if self._hotkey:
            self._hotkey.stop()
        if self._hotkey_refine:
            self._hotkey_refine.stop()
        if self._recorder.is_recording:
            self._recorder.stop()

    def apply_config(self, new: Config) -> None:
        old = self.config
        self.config = new
        self._activation.tap_threshold_ms = new.tap_threshold_ms
        self.history.max_size = new.history_size
        self._recorder.device = new.input_device
        self._rebuild_engine()  # provedor/chave/modelo podem ter mudado
        self._rebuild_refiner()
        if new.hotkey != old.hotkey and self._hotkey:
            try:
                self._hotkey.set_hotkey(new.hotkey)
            except Exception as e:  # noqa: BLE001
                self.failed.emit(f"Atalho inválido: {e}")
        if new.refine_hotkey != old.refine_hotkey:
            self._start_refine_hotkey()
        self.configApplied.emit()

    def toggle_recording(self) -> None:
        """Inicia/para a gravação pelo botão da interface (comporta como toggle)."""
        if self._activation.state is State.IDLE:
            self._pending_refine = False
        self._run_action(self._activation.toggle_button())

    def stop_recording(self) -> None:
        """Para e transcreve (botão do pop-up)."""
        if self._activation.state is State.RECORDING:
            self._run_action(self._activation.toggle_button())

    def cancel_recording(self) -> None:
        """Descarta a gravação em andamento, sem transcrever."""
        if self._recorder.is_recording:
            self._recorder.stop()
        self._activation.reset()
        self._pending_refine = False
        self.overlayState.emit("hidden", "")
        self._emit_state()

    def current_level(self) -> float:
        """Nível atual do microfone (0..1), para a onda do pop-up."""
        return getattr(self._recorder, "level", 0.0)

    def has_api_key(self) -> bool:
        return bool(resolve_provider_key(self.config, self.config.provider))

    def _rebuild_engine(self) -> None:
        provider = self.config.provider
        key = resolve_provider_key(self.config, provider)
        if not key:
            self._engine = None  # silencioso: quem avisa é quem tenta usar
            return
        try:
            self._engine = make_engine(
                provider, key, provider_model(self.config, provider)
            )
        except Exception as e:  # noqa: BLE001
            self._engine = None
            self.failed.emit(f"Falha ao iniciar a transcrição: {e}")

    def _engine_label(self) -> str:
        return f"{self.config.provider}:{provider_model(self.config, self.config.provider)}"

    def _rebuild_refiner(self) -> None:
        provider = self.config.refiner_provider
        key = resolve_provider_key(self.config, provider)
        if not key:
            self._refiner = None
            return
        try:
            model = self.config.refiner_model.strip() or DEFAULT_CHAT_MODELS.get(
                provider, ""
            )
            self._refiner = make_refiner(provider, key, model)
        except Exception:  # noqa: BLE001
            self._refiner = None

    # ---- ativação (thread do Qt) ----
    def _on_start(self) -> None:
        if self._activation.state is State.IDLE:
            self._pending_refine = False
        self._run_action(self._activation.on_press())

    def _on_start_refine(self) -> None:
        if self._activation.state is State.IDLE:
            self._pending_refine = True
        self._run_action(self._activation.on_press())

    def _on_release(self, duration_ms: float) -> None:
        self._run_action(self._activation.on_release(duration_ms))

    def _run_action(self, action: Action) -> None:
        if action is Action.START_RECORDING:
            self._start_recording()
        elif action is Action.STOP_AND_TRANSCRIBE:
            self._stop_and_transcribe()
        # LATCH_TOGGLE / NONE: nada a fazer (segue gravando ou ignora)
        self._emit_state()

    def _start_recording(self) -> None:
        if not self.has_api_key():
            self._activation.reset()
            self.overlayState.emit("hidden", "")
            self.setupNeeded.emit(
                "Falta a chave de API para transcrever o que você falar."
            )
            return
        try:
            self._recorder.start()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Não consegui acessar o microfone: {e}")
            self._activation.reset()
            self.overlayState.emit("hidden", "")
            return
        self.overlayState.emit("recording", "")

    def _stop_and_transcribe(self) -> None:
        wav = self._recorder.stop()
        duration = self._recorder.last_duration_s
        if duration < 0.3 or not wav:  # silêncio / clique acidental
            self._activation.on_transcription_done()
            self.overlayState.emit("hidden", "")
            self._emit_state()
            return
        if self._engine is None:
            self._rebuild_engine()
        if self._engine is None:
            self._activation.on_transcription_done()
            self.overlayState.emit("hidden", "")
            self._emit_state()
            return
        self.overlayState.emit("processing", "Transcrevendo…")
        threading.Thread(
            target=self._worker, args=(wav, duration), daemon=True
        ).start()

    def _worker(self, wav: bytes, duration: float) -> None:
        try:
            text = self._engine.transcribe(
                wav,
                language=self.config.language,
                hint=self.config.transcribe_hint,
            )
            self._transcriptionReady.emit(text, duration)
        except Exception as e:  # noqa: BLE001
            self._transcriptionFailed.emit(str(e), wav)

    def _on_ready(self, text: str, duration: float) -> None:
        self._activation.on_transcription_done()
        self._emit_state()
        text = text.strip()
        if not text:
            return
        if self._pending_refine and self._refiner is not None:
            self.refineBusy.emit(True)
            self.overlayState.emit("processing", "Refinando…")
            threading.Thread(
                target=self._refine_worker, args=(text, duration), daemon=True
            ).start()
            return
        if self._pending_refine and self._refiner is None:
            self.failed.emit(
                "Refinador não configurado — colei o texto cru. (aba Configurações)"
            )
        self._finish_output(text, duration)

    def _finish_output(self, text: str, duration: float) -> None:
        if self.config.ai_note_enabled:
            text = append_note(text, self.config.ai_note_text)
        self.history.add(Transcription.create(text, duration, self._engine_label()))
        self.historyChanged.emit()
        self._output.deliver(
            text,
            mode=self.config.output_mode,
            restore_clipboard=self.config.restore_clipboard,
        )
        self.transcribed.emit(text)
        done = "Colado ✓" if self.config.output_mode == "paste" else "Copiado ✓"
        self.overlayState.emit("done", done)

    def _refine_worker(self, text: str, duration: float) -> None:
        try:
            context = ""
            if self.config.context_enabled:
                from .context import load_context

                context = load_context(self.config.context_dir)
            refined = self._refiner.refine(
                text, self.config.refine_prompt, context
            ).strip()
            self._refineReady.emit(refined or text, duration)
        except Exception as e:  # noqa: BLE001
            self._refineFailed.emit(str(e), text, duration)

    def _on_refine_ready(self, text: str, duration: float) -> None:
        self.refineBusy.emit(False)
        self._finish_output(text, duration)

    # ---- refinar um item já existente no histórico ----
    def refine_history_item(self, uid: str) -> None:
        entry = self.history.by_uid(uid)
        if entry is None:
            return
        if self._refiner is None:
            self._rebuild_refiner()
        if self._refiner is None:
            self.setupNeeded.emit(
                "Falta a chave do provedor escolhido para refinar o texto."
            )
            return
        self.itemRefineBusy.emit(uid, True)
        threading.Thread(
            target=self._item_refine_worker, args=(uid, entry.text), daemon=True
        ).start()

    def _item_refine_worker(self, uid: str, text: str) -> None:
        try:
            context = ""
            if self.config.context_enabled:
                from .context import load_context

                context = load_context(self.config.context_dir)
            refined = self._refiner.refine(
                text, self.config.refine_prompt, context
            ).strip()
            self._itemRefineReady.emit(uid, refined or text)
        except Exception as e:  # noqa: BLE001
            self._itemRefineFailed.emit(uid, str(e))

    def _on_item_refine_ready(self, uid: str, text: str) -> None:
        self.itemRefineBusy.emit(uid, False)
        entry = self.history.by_uid(uid)
        if entry is None:
            return
        # Guarda o texto original só na primeira vez, para nada se perder.
        original = entry.original or entry.text
        self.history.update_text(uid, text, entry.refined + 1, original)
        self.historyChanged.emit()

    def _on_item_refine_failed(self, uid: str, message: str) -> None:
        self.itemRefineBusy.emit(uid, False)
        self.failed.emit(f"Não consegui refinar: {message}")

    def _on_refine_failed(self, message: str, raw_text: str, duration: float) -> None:
        self.refineBusy.emit(False)
        self.failed.emit(f"Refino falhou: {message} — colei o texto cru.")
        self._finish_output(raw_text, duration)

    def _on_failed(self, message: str, wav: bytes) -> None:
        self._activation.on_transcription_done()
        self._save_failed_audio(wav)
        self.failed.emit(
            f"Falha na transcrição: {message} — guardei o áudio para reenviar."
        )
        self.pendingChanged.emit(len(self.pending_audios()))
        self.overlayState.emit("hidden", "")
        self._emit_state()

    # ---- áudios que falharam e ficaram guardados ----
    def pending_dir(self):
        return config_dir() / "audios_pendentes"

    def pending_audios(self) -> list:
        try:
            return sorted(self.pending_dir().glob("*.wav"))
        except Exception:  # noqa: BLE001
            return []

    def retry_pending(self) -> None:
        """Reenvia o áudio pendente mais antigo (apaga se der certo)."""
        files = self.pending_audios()
        if not files:
            return
        self.transcribe_file(str(files[0]), delete_after=True)

    def discard_pending(self) -> None:
        for f in self.pending_audios():
            try:
                f.unlink()
            except OSError:
                pass

    # ---- transcrição de arquivo de áudio (drag-and-drop / botão) ----
    def transcribe_file(self, path: str, delete_after: bool = False) -> None:
        from .audiofile import AudioFileError, read_audio

        try:
            data, name = read_audio(path)
        except AudioFileError as e:
            self.failed.emit(str(e))
            return
        self._file_source = path if delete_after else ""
        if self._engine is None:
            self._rebuild_engine()
        if self._engine is None:
            self.setupNeeded.emit(
                "Falta a chave de API para transcrever este áudio."
            )
            return
        self.fileBusy.emit(True)
        threading.Thread(
            target=self._file_worker, args=(data, name), daemon=True
        ).start()

    def _file_worker(self, data: bytes, name: str) -> None:
        try:
            text = self._engine.transcribe(
                data,
                language=self.config.language,
                filename=name,
                hint=self.config.transcribe_hint,
            )
            self._fileReady.emit(text, name)
        except Exception as e:  # noqa: BLE001
            self._fileFailed.emit(str(e))

    def _on_file_ready(self, text: str, name: str) -> None:
        self.fileBusy.emit(False)
        # Deu certo: o áudio guardado por falha anterior já cumpriu seu papel.
        source = getattr(self, "_file_source", "")
        if source:
            self._file_source = ""
            try:
                os.remove(source)
            except OSError:
                pass
            self.pendingChanged.emit(len(self.pending_audios()))
        text = text.strip()
        if not text:
            self.failed.emit("Transcrição vazia (o áudio tem fala?).")
            return
        if self.config.ai_note_enabled:
            text = append_note(text, self.config.ai_note_text)
        entry = Transcription.create(text, 0.0, self._engine_label())
        self.history.add(entry)
        self.historyChanged.emit()
        self.fileResult.emit(text, name)

    def _on_file_failed(self, message: str) -> None:
        self.fileBusy.emit(False)
        self.failed.emit(f"Falha ao transcrever o arquivo: {message}")

    # ---- verificação de atualização (GitHub Releases) ----
    def check_updates(self, manual: bool = False) -> None:
        from .config import resolve_update_repo

        repo = resolve_update_repo(self.config)
        if not repo:
            if manual:
                self.updateError.emit(
                    "Atualização automática ainda não configurada nesta versão."
                )
            return
        self._update_manual = manual
        threading.Thread(
            target=self._update_check_worker, args=(repo,), daemon=True
        ).start()

    def _update_check_worker(self, repo: str) -> None:
        from .updater import fetch_latest_release

        try:
            self._updateDone.emit(fetch_latest_release(repo))
        except Exception as e:  # noqa: BLE001
            self._updateFail.emit(str(e))

    def _on_update_done(self, rel) -> None:
        from . import __version__
        from .updater import is_newer

        if rel and is_newer(rel.version, __version__):
            self.updateAvailable.emit(rel)
        elif self._update_manual:
            self.updateUpToDate.emit()

    def _on_update_fail(self, message: str) -> None:
        if self._update_manual:
            self.updateError.emit(f"Não consegui verificar atualizações: {message}")

    def download_and_install(self, rel) -> None:
        url = getattr(rel, "installer_url", None)
        if not url:
            self.updateError.emit("Este release não tem instalador (.exe).")
            return
        self._update_manual = True
        self.updateStatus.emit("Baixando atualização…")
        threading.Thread(
            target=self._download_worker, args=(url,), daemon=True
        ).start()

    def _download_worker(self, url: str) -> None:
        import os
        import tempfile

        from .updater import download_file

        try:
            dest = os.path.join(tempfile.gettempdir(), "FalaAI-Setup.exe")
            download_file(url, dest)
            self._installerReady.emit(dest)
        except Exception as e:  # noqa: BLE001
            self._updateFail.emit(str(e))

    def _on_installer_ready(self, path: str) -> None:
        import os
        import sys

        self.updateStatus.emit("Abrindo o instalador…")
        try:
            if sys.platform == "win32":
                os.startfile(path)  # type: ignore[attr-defined]
            else:
                import webbrowser

                webbrowser.open(f"file://{path}")
        except Exception as e:  # noqa: BLE001
            self.updateError.emit(f"Não consegui abrir o instalador: {e}")
            return
        self.shutdown()
        self.quitRequested.emit()

    def _save_failed_audio(self, wav: bytes) -> str:
        try:
            d = self.pending_dir()
            d.mkdir(parents=True, exist_ok=True)
            p = d / f"audio_{int(time.time())}.wav"
            p.write_bytes(wav)
            return str(p)
        except Exception:  # noqa: BLE001
            return "(não foi possível salvar)"

    def _emit_state(self) -> None:
        mapping = {
            State.IDLE: "idle",
            State.RECORDING: "recording",
            State.TRANSCRIBING: "transcribing",
        }
        self.stateChanged.emit(mapping[self._activation.state])
