"""Quem fecha a gravação decide se refina (inversão de intenção)."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    HAS_QT = True
except ImportError:  # ambiente sem GUI: o resto da suíte continua valendo
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 não instalado")
class TestRefineIntent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _controller(self):
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        c = Controller(Config(groq_api_key="x"), History(path=None))
        c._recorder.start = lambda: None          # não abre microfone no teste
        c._recorder.stop = lambda: b""
        return c

    def test_dita_e_fecha_com_refino(self):
        c = self._controller()
        c._on_start()          # Alt+Q: começa a ditar
        c._on_release(50)      # toque rápido -> modo travado
        self.assertFalse(c._pending_refine)
        c._on_start_refine()   # Alt+W fecha: mudou de ideia, quer refinar
        self.assertTrue(c._pending_refine)

    def test_refino_e_fecha_com_ditado(self):
        c = self._controller()
        c._on_start_refine()   # Alt+W: começa querendo refinar
        c._on_release(50)
        self.assertTrue(c._pending_refine)
        c._on_start()          # Alt+Q fecha: desistiu do refino
        self.assertFalse(c._pending_refine)

    def test_mesmo_atalho_mantem_intencao(self):
        for starter, expected in ((("_on_start",), False), (("_on_start_refine",), True)):
            c = self._controller()
            getattr(c, starter[0])()
            c._on_release(50)
            getattr(c, starter[0])()
            self.assertEqual(c._pending_refine, expected)

    def test_segurando_a_outra_tecla_troca_a_intencao(self):
        # push-to-talk: segura Alt+W e, no meio, aperta Alt+Q para desistir
        c = self._controller()
        c._on_start_refine()
        self.assertTrue(c._pending_refine)
        c._on_start()                    # ainda gravando (segurando)
        self.assertFalse(c._pending_refine)


if __name__ == "__main__":
    unittest.main()
