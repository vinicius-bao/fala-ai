"""Regressão da v0.13.0: uma falha não pode deixar o atalho morto.

O estado vira TRANSCREVENDO antes de o áudio ser fechado/enviado. Se algo
estourar (ou a rede pendurar) e ninguém destravar, todo aperto de atalho
seguinte é ignorado — o app parece "morto".
"""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 não instalado")
class TestNeverStuck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _controller(self):
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        c = Controller(Config(groq_api_key="k"), History(path=None))
        c._recorder.start = lambda: None
        c._recorder.stop = lambda: b"x" * 100
        type(c._recorder).is_recording = property(lambda self: False)
        c._recorder.last_duration_s = 2.0
        return c

    def _state(self, c):
        from assistente_voz.activation import State

        return c._activation.state

    def test_falha_ao_fechar_o_audio_nao_trava(self):
        from assistente_voz.activation import State

        c = self._controller()

        def explode():
            raise OSError("driver de áudio travou")

        c._recorder.stop = explode
        c._on_start()
        c._on_release(50)          # gravando (modo travado)
        c._on_start()              # tenta parar -> estoura
        self.assertIs(self._state(c), State.IDLE, "ficou preso após a falha")

    def test_apos_a_falha_o_atalho_volta_a_funcionar(self):
        from assistente_voz.activation import Action, State

        c = self._controller()
        c._recorder.stop = lambda: (_ for _ in ()).throw(OSError("boom"))
        c._on_start()
        c._on_release(50)
        c._on_start()                        # falha
        c._recorder.stop = lambda: b"x" * 100  # microfone volta ao normal
        c._on_start()                        # deve gravar de novo
        self.assertIs(self._state(c), State.RECORDING)

    def test_watchdog_destrava_transcricao_pendurada(self):
        from assistente_voz.activation import State

        c = self._controller()
        c._engine = object()  # não vai ser usado: simulamos o pendurado
        c._on_start()
        c._on_release(50)
        # entra em transcrição e "pendura" (worker que nunca responde)
        c._activation.state = State.TRANSCRIBING
        c._on_watchdog()
        self.assertIs(self._state(c), State.IDLE)

    def test_falha_na_interface_nao_impede_a_colagem(self):
        c = self._controller()
        entregue = []
        c._output.stage = lambda text, keep=False: entregue.append(text) or None
        c._output.send_paste = lambda: True

        def historico_quebrado(*a, **k):
            raise RuntimeError("interface quebrou")

        c.history.add = historico_quebrado
        c._on_ready("meu texto falado", 2.0)
        self.assertEqual(entregue, ["meu texto falado"])


if __name__ == "__main__":
    unittest.main()
