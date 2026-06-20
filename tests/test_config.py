import os
import tempfile
import unittest
from pathlib import Path

from assistente_voz.config import Config, load_config, resolve_api_key, save_config


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
