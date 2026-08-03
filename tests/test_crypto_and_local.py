import json
import sys
import tempfile
import unittest
from pathlib import Path

from assistente_voz.config import (
    Config,
    load_config,
    provider_model,
    provider_needs_key,
    resolve_provider_key,
    save_config,
)
from assistente_voz.crypto import PREFIX, is_protected, protect, unprotect


class TestCrypto(unittest.TestCase):
    def test_marker(self):
        self.assertTrue(is_protected(PREFIX + "abc"))
        self.assertFalse(is_protected("gsk_chave_pura"))
        self.assertFalse(is_protected(""))

    def test_plaintext_passes_through(self):
        # config antigo (sem criptografia) continua legível
        self.assertEqual(unprotect("gsk_antiga"), "gsk_antiga")

    def test_empty_stays_empty(self):
        self.assertEqual(protect(""), "")
        self.assertEqual(unprotect(""), "")

    def test_never_double_protects(self):
        already = PREFIX + "Zm9v"
        self.assertEqual(protect(already), already)

    def test_corrupted_blob_does_not_crash(self):
        self.assertEqual(unprotect(PREFIX + "!!!nao-e-base64!!!"), "")

    @unittest.skipUnless(sys.platform == "win32", "DPAPI é do Windows")
    def test_roundtrip_on_windows(self):
        secret = "gsk_segredo_123"
        blob = protect(secret)
        self.assertTrue(is_protected(blob))
        self.assertNotIn(secret, blob)          # não vaza em texto puro
        self.assertEqual(unprotect(blob), secret)


class TestConfigKeyStorage(unittest.TestCase):
    def test_key_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            save_config(Config(groq_api_key="gsk_minha_chave"), p)
            self.assertEqual(load_config(p).groq_api_key, "gsk_minha_chave")

    @unittest.skipUnless(sys.platform == "win32", "DPAPI é do Windows")
    def test_key_is_not_plaintext_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            save_config(Config(groq_api_key="gsk_segredo"), p)
            self.assertNotIn("gsk_segredo", p.read_text(encoding="utf-8"))

    def test_old_plaintext_config_still_loads(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            p.write_text(json.dumps({"groq_api_key": "gsk_antiga"}), encoding="utf-8")
            self.assertEqual(load_config(p).groq_api_key, "gsk_antiga")


class TestLocalProvider(unittest.TestCase):
    def test_local_does_not_need_key(self):
        self.assertFalse(provider_needs_key("local"))
        for p in ("groq", "openai", "gemini"):
            self.assertTrue(provider_needs_key(p))

    def test_local_key_resolves_without_config(self):
        self.assertTrue(resolve_provider_key(Config(), "local"))

    def test_local_model_default(self):
        self.assertEqual(provider_model(Config(), "local"), "small")
        self.assertEqual(provider_model(Config(local_model="large-v3"), "local"),
                         "large-v3")

    def test_missing_dependency_explains_itself(self):
        from assistente_voz.transcription import LocalWhisperEngine, make_engine

        try:
            import faster_whisper  # noqa: F401
        except ImportError:
            with self.assertRaises(RuntimeError) as ctx:
                make_engine("local", "", "small")
            self.assertIn("faster-whisper", str(ctx.exception))
        else:  # instalado: a fábrica devolve o motor local
            self.assertIsInstance(make_engine("local", "", "tiny"),
                                  LocalWhisperEngine)


if __name__ == "__main__":
    unittest.main()
