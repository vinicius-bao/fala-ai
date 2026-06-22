import tempfile
import unittest
from pathlib import Path

from assistente_voz.audiofile import (
    MAX_BYTES,
    AudioFileError,
    is_supported,
    read_audio,
)


class TestAudioFile(unittest.TestCase):
    def test_is_supported(self):
        self.assertTrue(is_supported("msg.opus"))
        self.assertTrue(is_supported("AUDIO.MP3"))  # case-insensitive
        self.assertTrue(is_supported("/x/y/nota.m4a"))
        self.assertFalse(is_supported("doc.txt"))
        self.assertFalse(is_supported("semext"))

    def test_read_audio_ok(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "nota.opus"
            p.write_bytes(b"conteudo-de-audio-falso")
            data, name = read_audio(p)
            self.assertEqual(data, b"conteudo-de-audio-falso")
            self.assertEqual(name, "nota.opus")

    def test_unsupported_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "arquivo.txt"
            p.write_bytes(b"x")
            with self.assertRaises(AudioFileError):
                read_audio(p)

    def test_missing_file_raises(self):
        with self.assertRaises(AudioFileError):
            read_audio("/caminho/que/nao/existe.mp3")

    def test_empty_file_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "vazio.wav"
            p.write_bytes(b"")
            with self.assertRaises(AudioFileError):
                read_audio(p)

    def test_too_big_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "grande.mp3"
            with p.open("wb") as f:
                f.seek(MAX_BYTES + 1)
                f.write(b"\0")
            with self.assertRaises(AudioFileError):
                read_audio(p)


if __name__ == "__main__":
    unittest.main()
