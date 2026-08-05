"""Trocar de provedor não pode construir o cliente na thread da interface.

Importar o SDK da Groq/OpenAI pela primeira vez dentro do .exe leva segundos.
Fazer isso ao salvar as configurações travava o app inteiro.
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
class TestLazyEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _controller(self):
        from assistente_voz.app import Controller
        from assistente_voz.config import Config
        from assistente_voz.history import History

        return Controller(Config(groq_api_key="k"), History(path=None))

    def test_apply_config_nao_constroi_o_motor(self):
        from assistente_voz import app as app_mod
        from assistente_voz.config import Config

        c = self._controller()
        criados = []
        original = app_mod.make_engine
        app_mod.make_engine = lambda *a, **k: criados.append(a) or object()
        try:
            c.apply_config(Config(openai_api_key="k", provider="openai"))
            self.assertEqual(criados, [], "construiu o cliente ao salvar")
            # ...mas constrói quando realmente vai transcrever
            self.assertTrue(c._ensure_engine())
            self.assertEqual(len(criados), 1)
        finally:
            app_mod.make_engine = original

    def test_start_nao_constroi_o_motor(self):
        from assistente_voz import app as app_mod

        c = self._controller()
        criados = []
        original = app_mod.make_engine
        app_mod.make_engine = lambda *a, **k: criados.append(a) or object()
        try:
            c._rebuild_engine()
            self.assertIsNone(c._engine)
            self.assertEqual(criados, [])
        finally:
            app_mod.make_engine = original

    def test_motor_e_reaproveitado(self):
        from assistente_voz import app as app_mod

        c = self._controller()
        criados = []
        original = app_mod.make_engine
        app_mod.make_engine = lambda *a, **k: criados.append(a) or object()
        try:
            c._ensure_engine()
            c._ensure_engine()
            self.assertEqual(len(criados), 1, "recriou o cliente à toa")
        finally:
            app_mod.make_engine = original

    def test_troca_de_provedor_invalida_o_motor(self):
        from assistente_voz import app as app_mod
        from assistente_voz.config import Config

        c = self._controller()
        original = app_mod.make_engine
        app_mod.make_engine = lambda *a, **k: object()
        try:
            c._ensure_engine()
            self.assertIsNotNone(c._engine)
            c.apply_config(Config(gemini_api_key="k", provider="gemini"))
            self.assertIsNone(c._engine, "seguiu usando o motor antigo")
        finally:
            app_mod.make_engine = original


if __name__ == "__main__":
    unittest.main()
