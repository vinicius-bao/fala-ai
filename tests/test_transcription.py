import unittest

from assistente_voz.transcription import GeminiEngine, make_engine


class TestMakeEngine(unittest.TestCase):
    def test_gemini_dispatch(self):
        # caminho Gemini não importa SDK (usa REST), então é seguro instanciar aqui
        eng = make_engine("gemini", "chave", "gemini-2.0-flash")
        self.assertIsInstance(eng, GeminiEngine)

    def test_gemini_requires_key(self):
        with self.assertRaises(ValueError):
            make_engine("gemini", "", "gemini-2.0-flash")


if __name__ == "__main__":
    unittest.main()
