import io
import unittest
import wave

from assistente_voz.history import History, Transcription, matches, normalize_search
from assistente_voz.sounds import tone_wav


class TestSearch(unittest.TestCase):
    def test_normalize_removes_accents_and_case(self):
        self.assertEqual(normalize_search("Refinação ÁÉÍÕÇ"), "refinacao aeioc")

    def test_matches_ignores_accents(self):
        self.assertTrue(matches("transcrição do áudio", "transcricao"))
        self.assertTrue(matches("Reunião de Quinta", "reuniao quinta"))
        self.assertFalse(matches("reunião de quinta", "sexta"))

    def test_empty_query_matches_all(self):
        self.assertTrue(matches("qualquer coisa", ""))
        self.assertTrue(matches("qualquer coisa", "   "))

    def test_all_words_must_match(self):
        self.assertTrue(matches("comprar pão e café", "pao cafe"))
        self.assertFalse(matches("comprar pão e café", "pao leite"))

    def test_history_search_and_remove(self):
        h = History(path=None, max_size=10)
        a = Transcription.create("reunião de quinta às 9h", 1.0, "groq")
        b = Transcription.create("comprar pão e café", 1.0, "groq")
        h.add(a)
        h.add(b)
        self.assertEqual([i.uid for i in h.search("reuniao")], [a.uid])
        self.assertEqual(len(h.search("")), 2)          # sem busca, tudo
        self.assertTrue(h.remove(a.uid))
        self.assertEqual(len(h.all()), 1)
        self.assertFalse(h.remove("inexistente"))


class TestSounds(unittest.TestCase):
    def test_tone_is_valid_wav(self):
        data = tone_wav(880, 70)
        with wave.open(io.BytesIO(data), "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertGreater(wf.getnframes(), 0)

    def test_duration_roughly_matches(self):
        with wave.open(io.BytesIO(tone_wav(440, 100)), "rb") as wf:
            secs = wf.getnframes() / wf.getframerate()
        self.assertAlmostEqual(secs, 0.1, places=2)

    def test_starts_and_ends_silent(self):
        # fade in/out evita o 'clique' no começo e no fim
        import struct

        data = tone_wav(880, 70)
        with wave.open(io.BytesIO(data), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
        first = struct.unpack("<h", frames[:2])[0]
        last = struct.unpack("<h", frames[-2:])[0]
        self.assertEqual(first, 0)
        self.assertLess(abs(last), 2000)


if __name__ == "__main__":
    unittest.main()
