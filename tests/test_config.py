import os
import tempfile
import unittest
from pathlib import Path

from assistente_voz.config import (
    Config,
    append_note,
    load_config,
    provider_model,
    resolve_api_key,
    resolve_provider_key,
    save_config,
)


class TestConfig(unittest.TestCase):
    def test_defaults(self):
        c = Config()
        self.assertEqual(c.hotkey, "ctrl+alt+space")
        self.assertEqual(c.tap_threshold_ms, 400)
        self.assertEqual(c.output_mode, "paste")

    def test_from_dict_ignores_unknown(self):
        c = Config.from_dict({"hotkey": "f8", "lixo": 123})
        self.assertEqual(c.hotkey, "f8")

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.json"
            save_config(Config(hotkey="ctrl+shift+d", history_size=7), p)
            c = load_config(p)
            self.assertEqual(c.hotkey, "ctrl+shift+d")
            self.assertEqual(c.history_size, 7)

    def test_append_note(self):
        self.assertEqual(append_note("olá", "nota"), "olá\nnota")
        self.assertEqual(append_note("  olá  ", "nota"), "olá\nnota")
        self.assertEqual(append_note("", "nota"), "")     # sem texto, sem nota
        self.assertEqual(append_note("olá", ""), "olá")   # nota vazia: texto puro

    def test_provider_model_default_and_override(self):
        self.assertEqual(provider_model(Config(openai_model=""), "openai"),
                         "gpt-4o-transcribe")
        self.assertEqual(provider_model(Config(groq_model="whisper-x"), "groq"),
                         "whisper-x")
        self.assertEqual(provider_model(Config(), "gemini"), "gemini-2.0-flash")

    def test_resolve_provider_key_env_priority(self):
        os.environ.pop("OPENAI_API_KEY", None)
        c = Config(openai_api_key="cfgkey")
        self.assertEqual(resolve_provider_key(c, "openai"), "cfgkey")
        os.environ["OPENAI_API_KEY"] = "envkey"
        try:
            self.assertEqual(resolve_provider_key(c, "openai"), "envkey")
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_resolve_api_key_env_priority(self):
        old = os.environ.get("GROQ_API_KEY")
        try:
            os.environ["GROQ_API_KEY"] = "gsk_do_ambiente"
            self.assertEqual(resolve_api_key(Config(groq_api_key="gsk_config")),
                             "gsk_do_ambiente")
            del os.environ["GROQ_API_KEY"]
            self.assertEqual(resolve_api_key(Config(groq_api_key="gsk_config")),
                             "gsk_config")
        finally:
            if old is not None:
                os.environ["GROQ_API_KEY"] = old
            elif "GROQ_API_KEY" in os.environ:
                del os.environ["GROQ_API_KEY"]


if __name__ == "__main__":
    unittest.main()
