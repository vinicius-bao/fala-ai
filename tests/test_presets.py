import unittest

from assistente_voz.config import (
    DEFAULT_REFINE_PROMPT,
    REFINE_PRESETS,
    match_preset,
)


class TestRefinePresets(unittest.TestCase):
    def test_presets_exist(self):
        for key in ("natural", "prompt_ia", "formal", "pontuacao"):
            self.assertIn(key, REFINE_PRESETS)
            label, prompt = REFINE_PRESETS[key]
            self.assertTrue(label and prompt.strip())

    def test_all_presets_ask_for_paragraphs(self):
        # era o defeito do prompt antigo: nunca pedia parágrafos
        for key, (_, prompt) in REFINE_PRESETS.items():
            self.assertIn("parágrafo", prompt.lower(), key)

    def test_default_is_natural(self):
        self.assertEqual(DEFAULT_REFINE_PROMPT, REFINE_PRESETS["natural"][1])
        self.assertEqual(match_preset(DEFAULT_REFINE_PROMPT), "natural")

    def test_match_preset_custom(self):
        self.assertEqual(match_preset("qualquer coisa minha"), "custom")
        self.assertEqual(match_preset(""), "custom")

    def test_match_preset_ignores_surrounding_space(self):
        self.assertEqual(
            match_preset("\n  " + REFINE_PRESETS["formal"][1] + "  \n"), "formal"
        )


if __name__ == "__main__":
    unittest.main()
