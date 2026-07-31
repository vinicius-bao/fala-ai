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

    def test_old_history_still_loads(self):
        # Regressão: registros gravados antes dos campos uid/refined/original
        # não podem zerar o histórico de quem atualiza o app.
        import json

        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "history.json"
            p.write_text(
                json.dumps(
                    [{"text": "antigo", "timestamp": "2026-01-01T10:00:00",
                      "duration_s": 1.0, "engine": "groq"}]
                ),
                encoding="utf-8",
            )
            h = History(path=p, max_size=10)
            self.assertEqual(len(h.all()), 1)
            self.assertEqual(h.all()[0].text, "antigo")
            self.assertTrue(h.all()[0].uid)      # ganha uid automaticamente
            self.assertEqual(h.all()[0].refined, 0)

    def test_unknown_fields_are_ignored(self):
        entry = Transcription.from_dict(
            {"text": "x", "timestamp": "t", "duration_s": 1, "engine": "e",
             "campo_do_futuro": 123}
        )
        self.assertEqual(entry.text, "x")

    def test_update_text_marks_refined(self):
        h = History(path=None, max_size=10)
        e = Transcription.create("texto cru", 1.0, "groq")
        h.add(e)
        self.assertTrue(h.update_text(e.uid, "texto refinado", 1, "texto cru"))
        got = h.by_uid(e.uid)
        self.assertEqual(got.text, "texto refinado")
        self.assertEqual(got.refined, 1)
        self.assertEqual(got.original, "texto cru")
        # segunda rodada continua contando
        h.update_text(e.uid, "ainda melhor", got.refined + 1, got.original)
        self.assertEqual(h.by_uid(e.uid).refined, 2)
        self.assertEqual(h.by_uid(e.uid).original, "texto cru")

    def test_update_text_unknown_uid(self):
        h = History(path=None, max_size=10)
        self.assertFalse(h.update_text("nao-existe", "x", 1, "y"))

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
