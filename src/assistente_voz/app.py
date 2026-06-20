"""Controlador: orquestra atalho, gravação, transcrição e entrega.

Eventos do atalho chegam pela thread do pynput e são marshalados para a thread
do Qt via signals (QueuedConnection). A transcrição (rede) roda numa thread
separada para não travar a interface.
"""

from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, Qt, Signal

from .activation import Action, Activation, State
from .audio import Recorder
from .config import Config, config_dir, resolve_api_key
from .history import History, Transcription
from .hotkey import HotkeyListener
from .output import TextOutput
from .transcription import GroqEngine


class Controller(QObject):
    stateChanged = Signal(str)          # "idle" | "recording" | "transcribing"
    transcribed = Signal(str)
    failed = Signal(str)
    historyChanged = Signal()

    # internos: trazem eventos de outras threads para a thread do Qt
    _hkStart = Signal()
    _hkRelease = Signal(float)
    _transcriptionReady = Signal(str, float)
    _transcriptionFailed = Signal(str, object)  # (mensagem, wav bytes)

    def __init__(self, config: Config, history: History):
        super().__init__()
        self.config = config
        self.history = history
        self._activation = Activation(config.tap_threshold_ms)
        self._recorder = Recorder()
        self._output = TextOutput()
        self._engine: GroqEngine | None = None
        self._hotkey: HotkeyListener | None = None

        self._hkStart.connect(self._on_start, Qt.QueuedConnection)
        self._hkRelease.connect(self._on_release, Qt.QueuedConnection)
        self._transcriptionReady.connect(self._on_ready, Qt.QueuedConnection)
        self._transcriptionFailed.connect(self._on_failed, Qt.QueuedConnection)

    # ---- ciclo de vida ----
    def start(self) -> None:
        self._rebuild_engine()
        self._hotkey = HotkeyListener(
            self.config.hotkey,
            on_start=self._hkStart.emit,
            on_release=self._hkRelease.emit,
        )
        try:
            self._hotkey.start()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Não consegui registrar o atalho: {e}")

    def shutdown(self) -> None:
        if self._hotkey:
            self._hotkey.stop()
        if self._recorder.is_recording:
            self._recorder.stop()

    def apply_config(self, new: Config) -> None:
        old = self.config
        self.config = new
        self._activation.tap_threshold_ms = new.tap_threshold_ms
        self.history.max_size = new.history_size
        if (new.groq_api_key, new.groq_model) != (old.groq_api_key, old.groq_model):
            self._rebuild_engine()
        if new.hotkey != old.hotkey and self._hotkey:
            try:
                self._hotkey.set_hotkey(new.hotkey)
            except Exception as e:  # noqa: BLE001
                self.failed.emit(f"Atalho inválido: {e}")

    def _rebuild_engine(self) -> None:
        key = resolve_api_key(self.config)
        if not key:
            self._engine = None
            self.failed.emit(
                "Chave da Groq não configurada (GROQ_API_KEY ou aba Configurações)."
            )
            return
        try:
            self._engine = GroqEngine(key, model=self.config.groq_model)
        except Exception as e:  # noqa: BLE001
            self._engine = None
            self.failed.emit(f"Falha ao iniciar a transcrição: {e}")

    # ---- ativação (thread do Qt) ----
    def _on_start(self) -> None:
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
        try:
            self._recorder.start()
        except Exception as e:  # noqa: BLE001
            self.failed.emit(f"Não consegui acessar o microfone: {e}")
            self._activation.reset()

    def _stop_and_transcribe(self) -> None:
        wav = self._recorder.stop()
        duration = self._recorder.last_duration_s
        if duration < 0.3 or not wav:  # silêncio / clique acidental
            self._activation.on_transcription_done()
            self._emit_state()
            return
        if self._engine is None:
            self._rebuild_engine()
        if self._engine is None:
            self._activation.on_transcription_done()
            self._emit_state()
            return
        threading.Thread(
            target=self._worker, args=(wav, duration), daemon=True
        ).start()

    def _worker(self, wav: bytes, duration: float) -> None:
        try:
            text = self._engine.transcribe(wav, language=self.config.language)
            self._transcriptionReady.emit(text, duration)
        except Exception as e:  # noqa: BLE001
            self._transcriptionFailed.emit(str(e), wav)

    def _on_ready(self, text: str, duration: float) -> None:
        self._activation.on_transcription_done()
        text = text.strip()
        if text:
            entry = Transcription.create(text, duration, "groq:" + self.config.groq_model)
            self.history.add(entry)
            self.historyChanged.emit()
            self._output.deliver(
                text,
                mode=self.config.output_mode,
                restore_clipboard=self.config.restore_clipboard,
            )
            self.transcribed.emit(text)
        self._emit_state()

    def _on_failed(self, message: str, wav: bytes) -> None:
        self._activation.on_transcription_done()
        path = self._save_failed_audio(wav)
        self.failed.emit(f"Falha na transcrição: {message}\nÁudio salvo em: {path}")
        self._emit_state()

    def _save_failed_audio(self, wav: bytes) -> str:
        try:
            d = config_dir() / "audios_pendentes"
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
