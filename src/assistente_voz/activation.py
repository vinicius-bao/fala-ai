"""Máquina de estados pura da ativação dupla (segurar vs. tocar).

Sem I/O, sem threads, sem Qt — totalmente testável. O controlador alimenta os
eventos do atalho (press/release) e executa a ``Action`` retornada.

Regras:
- Press com estado OCIOSO  -> começa a gravar (START_RECORDING).
- Release rápido (< limiar) -> era um *toque*: trava em modo toggle e CONTINUA
  gravando (LATCH_TOGGLE).
- Release demorado (>= limiar) -> *push-to-talk*: para e transcreve.
- Press seguinte em modo toggle -> para e transcreve.
"""

from __future__ import annotations

from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()


class Action(Enum):
    NONE = auto()
    START_RECORDING = auto()
    STOP_AND_TRANSCRIBE = auto()
    LATCH_TOGGLE = auto()


class Activation:
    def __init__(self, tap_threshold_ms: int = 400):
        self.tap_threshold_ms = tap_threshold_ms
        self.state = State.IDLE
        self._toggle = False

    def on_press(self) -> Action:
        if self.state is State.IDLE:
            self.state = State.RECORDING
            self._toggle = False
            return Action.START_RECORDING
        if self.state is State.RECORDING and self._toggle:
            self.state = State.TRANSCRIBING
            return Action.STOP_AND_TRANSCRIBE
        return Action.NONE

    def on_release(self, duration_ms: float) -> Action:
        if self.state is State.RECORDING and not self._toggle:
            if duration_ms < self.tap_threshold_ms:
                self._toggle = True
                return Action.LATCH_TOGGLE
            self.state = State.TRANSCRIBING
            return Action.STOP_AND_TRANSCRIBE
        return Action.NONE

    def on_transcription_done(self) -> None:
        self.state = State.IDLE
        self._toggle = False

    def reset(self) -> None:
        self.state = State.IDLE
        self._toggle = False
