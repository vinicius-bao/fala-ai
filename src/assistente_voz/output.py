"""Entrega do texto: clipboard + colar (Ctrl+V) no app em foco.

Nada aqui pode dormir na thread da interface — quem espera é o QTimer de quem
chama (ver ``Controller._finish_output``), senão o app congela ao colar.
"""

from __future__ import annotations


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

    def read_clipboard(self) -> str:
        import pyperclip

        try:
            return pyperclip.paste()
        except Exception:  # noqa: BLE001
            return ""

    def stage(self, text: str, keep_previous: bool = False) -> str | None:
        """Coloca o texto no clipboard. Devolve o conteúdo anterior, se pedido."""
        previous = self.read_clipboard() if keep_previous else None
        self.to_clipboard(text)
        return previous

    def send_paste(self) -> bool:
        """Envia Ctrl+V para a janela em foco."""
        from pynput.keyboard import Key

        try:
            kb = self._keyboard()
            with kb.pressed(Key.ctrl):
                kb.press("v")
                kb.release("v")
            return True
        except Exception:  # noqa: BLE001
            return False

    def restore(self, previous: str) -> None:
        try:
            self.to_clipboard(previous)
        except Exception:  # noqa: BLE001
            pass
