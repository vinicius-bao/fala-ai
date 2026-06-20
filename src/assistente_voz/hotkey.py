"""Atalho global com suporte a segurar/tocar, sobre o pynput.

``parse_hotkey`` é puro (stdlib) e testável. ``HotkeyListener`` registra o hook
global; o ``pynput`` é importado de forma preguiçosa para não exigir a lib em
ambientes onde só se quer testar o parsing.
"""

from __future__ import annotations

import time
from typing import Callable

_MOD_TOKENS = {"ctrl", "alt", "shift", "cmd"}


def parse_hotkey(spec: str) -> tuple[frozenset[str], str]:
    """'ctrl+alt+space' -> (frozenset({'ctrl','alt'}), 'space')."""
    parts = [p.strip().lower() for p in spec.split("+") if p.strip()]
    if not parts:
        raise ValueError("atalho vazio")
    mods = frozenset(p for p in parts if p in _MOD_TOKENS)
    main = [p for p in parts if p not in _MOD_TOKENS]
    if len(main) != 1:
        raise ValueError(
            f"o atalho precisa de exatamente uma tecla principal: {spec!r}"
        )
    return mods, main[0]


class HotkeyListener:
    """Emite ``on_start()`` quando a combinação fica totalmente pressionada e
    ``on_release(duration_ms)`` quando é solta. A decisão toque-vs-segurar é do
    consumidor (ver ``Activation``)."""

    def __init__(
        self,
        hotkey: str,
        on_start: Callable[[], None],
        on_release: Callable[[float], None],
    ):
        self._on_start = on_start
        self._on_release = on_release
        self._mods, self._main = parse_hotkey(hotkey)
        self._pressed: set[str] = set()
        self._active = False
        self._t0 = 0.0
        self._listener = None

    # ----- ciclo de vida -----
    def start(self) -> None:
        from pynput import keyboard

        self._listener = keyboard.Listener(
            on_press=self._handle_press, on_release=self._handle_release
        )
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        self._pressed.clear()
        self._active = False

    def set_hotkey(self, hotkey: str) -> None:
        self._mods, self._main = parse_hotkey(hotkey)
        self._pressed.clear()
        self._active = False

    # ----- callbacks do pynput (rodam na thread do listener) -----
    def _tokens_for(self, key) -> set[str]:
        from pynput import keyboard

        Key = keyboard.Key
        KeyCode = keyboard.KeyCode
        mods = {
            Key.ctrl: "ctrl", Key.ctrl_l: "ctrl", Key.ctrl_r: "ctrl",
            Key.alt: "alt", Key.alt_l: "alt", Key.alt_r: "alt",
            Key.shift: "shift", Key.shift_l: "shift", Key.shift_r: "shift",
            Key.cmd: "cmd",
        }
        for name in ("alt_gr", "cmd_l", "cmd_r"):
            k = getattr(Key, name, None)
            if k is not None:
                mods[k] = "alt" if name == "alt_gr" else "cmd"
        if key in mods:
            return {mods[key]}
        if isinstance(key, Key):
            return {key.name}                 # 'space', 'f8', 'pause', ...
        if isinstance(key, KeyCode) and key.char:
            return {key.char.lower()}
        return set()

    def _satisfied(self) -> bool:
        return self._main in self._pressed and self._mods.issubset(self._pressed)

    def _handle_press(self, key) -> None:
        self._pressed |= self._tokens_for(key)
        if not self._active and self._satisfied():
            self._active = True
            self._t0 = time.monotonic()
            self._safe(self._on_start)

    def _handle_release(self, key) -> None:
        tokens = self._tokens_for(key)
        relevant = self._active and (self._main in tokens or bool(tokens & self._mods))
        self._pressed -= tokens
        if relevant:
            self._active = False
            duration_ms = (time.monotonic() - self._t0) * 1000.0
            self._safe(lambda: self._on_release(duration_ms))

    @staticmethod
    def _safe(fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception:
            pass
