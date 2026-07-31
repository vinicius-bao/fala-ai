import unittest

from assistente_voz.refiner import GeminiRefiner, make_refiner


class TestMakeRefiner(unittest.TestCase):
    def test_gemini_dispatch(self):
        # Gemini usa REST (sem SDK), então é seguro instanciar no teste
        self.assertIsInstance(
            make_refiner("gemini", "chave", "gemini-2.0-flash"), GeminiRefiner
        )

    def test_gemini_requires_key(self):
        with self.assertRaises(ValueError):
            make_refiner("gemini", "", "gemini-2.0-flash")


if __name__ == "__main__":
    unittest.main()
