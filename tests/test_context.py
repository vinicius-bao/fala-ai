import tempfile
import unittest
from pathlib import Path

from assistente_voz.context import load_context


class TestLoadContext(unittest.TestCase):
    def test_empty_and_missing(self):
        self.assertEqual(load_context(""), "")
        self.assertEqual(load_context("/caminho/que/nao/existe"), "")

    def test_reads_md_and_txt_only(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "a.md").write_text("conteudo A", encoding="utf-8")
            (Path(d) / "b.txt").write_text("conteudo B", encoding="utf-8")
            (Path(d) / "c.png").write_bytes(b"binario")
            out = load_context(d)
            self.assertIn("conteudo A", out)
            self.assertIn("conteudo B", out)
            self.assertNotIn("binario", out)

    def test_respects_max_chars(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "big.txt").write_text("x" * 5000, encoding="utf-8")
            out = load_context(d, max_chars=100)
            self.assertLessEqual(len(out), 100)


if __name__ == "__main__":
    unittest.main()
