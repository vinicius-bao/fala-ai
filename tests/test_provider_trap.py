"""Regressão da v0.13.0: escolher um provedor que não funciona quebrava tudo.

O Whisper local aparecia na lista mesmo no app instalado (onde a biblioteca não
existe). Ao selecioná-lo, o autosave gravava na hora, o motor falhava e o aviso
ia só para a barra de status — invisível com a janela fechada. Resultado: gravar
não colava nada e parecia que o app tinha morrido.
"""

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from assistente_voz.config import (  # noqa: E402
    PROVIDERS,
    available_providers,
    local_whisper_available,
)

try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except ImportError:
    HAS_QT = False


class TestAvailableProviders(unittest.TestCase):
    def test_nuvem_sempre_disponivel(self):
        for p in ("groq", "openai", "gemini"):
            self.assertIn(p, available_providers())

    def test_local_so_aparece_se_der_para_usar(self):
        self.assertEqual(
            "local" in available_providers(), local_whisper_available()
        )

    def test_lista_e_subconjunto_dos_provedores(self):
        self.assertTrue(set(available_providers()).issubset(set(PROVIDERS)))


@unittest.skipUnless(HAS_QT, "PySide6 não instalado")
class TestFailureIsVisible(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _pump(self, condicao, limite=4.0):
        """Roda o loop do Qt até a thread de trabalho responder."""
        fim = time.time() + limite
        while time.time() < fim and not condicao():
            self.app.processEvents()
            time.sleep(0.02)
        self.app.processEvents()

    def test_motor_indisponivel_avisa_em_vez_de_silenciar(self):
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        c = Controller(Config(provider="local"), History(path=None))
        c._recorder.start = lambda: None
        c._recorder.stop = lambda: b"x" * 100
        c._recorder.last_duration_s = 2.0
        c._recorder.peak_level = 0.5     # houve fala de verdade
        avisos = []
        c.setupNeeded.connect(avisos.append)

        c._on_start()
        c._on_release(50)
        c._on_start()          # para e tenta transcrever -> motor indisponível
        self._pump(lambda: bool(avisos))

        self.assertTrue(avisos, "a falha continuou invisível")
        self.assertIn("faster-whisper", avisos[0])

    def test_nao_fica_preso_apos_o_aviso(self):
        from assistente_voz.activation import State
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        c = Controller(Config(provider="local"), History(path=None))
        c._recorder.start = lambda: None
        c._recorder.stop = lambda: b"x" * 100
        c._recorder.last_duration_s = 2.0
        c._recorder.peak_level = 0.5     # houve fala de verdade
        c._on_start()
        c._on_release(50)
        c._on_start()
        self._pump(lambda: c._activation.state is State.IDLE)
        self.assertIs(c._activation.state, State.IDLE)


if __name__ == "__main__":
    unittest.main()
