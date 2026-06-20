"""Entrega do texto: clipboard + colar (Ctrl+V) no app em foco."""

from __future__ import annotations

import threading
import time


class TextOutput:
    def __init__(self):
        self._kb = None

    def _keyboard(self):
        if self._kb is None:
            from pynput.keyboard import Controller

            self._kb = Controller()
        return self._kb

    def to_clipboard(self, text: str) -> None:
        import pyperclip

        pyperclip.copy(text)

    def _read_clipboard(self) -> str:
        import pyperclip

        try:
            return pyperclip.paste()
        except Exception:
            return ""

    def paste_into_active(self, text: str, restore_clipboard: bool = False) -> bool:
        """Coloca o texto no clipboard e envia Ctrl+V. Retorna True se conseguiu
        enviar o atalho de colar (não há como saber se o app o aceitou)."""
        import pyperclip
        from pynput.keyboard import Key

        previous = self._read_clipboard() if restore_clipboard else None
        pyperclip.copy(text)
        time.sleep(0.05)
        try:
            kb = self._keyboard()
            with kb.pressed(Key.ctrl):
                kb.press("v")
                kb.release("v")
        except Exception:
            return False

        if restore_clipboard and previous is not None:
            def _restore():
                time.sleep(0.4)
                try:
                    pyperclip.copy(previous)
                except Exception:
                    pass

            threading.Thread(target=_restore, daemon=True).start()
        return True

    def deliver(
        self, text: str, mode: str = "paste", restore_clipboard: bool = False
    ) -> bool:
        """`mode`: 'paste' cola no app ativo; 'clipboard_only' só copia."""
        if mode == "clipboard_only":
            self.to_clipboard(text)
            return False
        return self.paste_into_active(text, restore_clipboard=restore_clipboard)
