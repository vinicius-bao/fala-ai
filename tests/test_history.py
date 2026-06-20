import tempfile
import unittest
from pathlib import Path

from assistente_voz.history import History, Transcription


class TestHistory(unittest.TestCase):
    def test_add_recent_order(self):
        h = History(path=None, max_size=10)
        h.add(Transcription.create("primeiro", 1.0, "groq"))
        h.add(Transcription.create("segundo", 1.0, "groq"))
        recent = h.recent()
        self.assertEqual(recent[0].text, "segundo")  # mais novo primeiro
        self.assertEqual(recent[1].text, "primeiro")

    def test_max_size_trim(self):
        h = History(path=None, max_size=2)
        for i in range(5):
            h.add(Transcription.create(f"t{i}", 1.0, "groq"))
        self.assertEqual(len(h.all()), 2)
        self.assertEqual([t.text for t in h.all()], ["t3", "t4"])

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            h = History(path=p, max_size=10)
            h.add(Transcription.create("olá mundo", 2.5, "groq:whisper-large-v3"))
            h2 = History(path=p, max_size=10)
            self.assertEqual(len(h2.all()), 1)
            self.assertEqual(h2.all()[0].text, "olá mundo")
            self.assertEqual(h2.all()[0].duration_s, 2.5)


if __name__ == "__main__":
    unittest.main()
