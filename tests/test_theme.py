import unittest

from assistente_voz.theme import DARK, LIGHT, build_qss


class TestTheme(unittest.TestCase):
    def test_brand_colors_present(self):
        for pal in (LIGHT, DARK):
            qss = build_qss(pal)
            self.assertIsInstance(qss, str)
            self.assertIn(pal.bg, qss)
            self.assertIn(pal.accent, qss)
            # gradiente da marca
            self.assertIn("#FBB03B", qss)

    def test_light_palette_values(self):
        self.assertEqual(LIGHT.bg, "#E6E7E8")
        self.assertEqual(LIGHT.text, "#5A5C63")

    def test_dark_palette_text_white(self):
        self.assertEqual(DARK.text, "#FFFFFF")

    def test_qss_contains_widgets(self):
        qss = build_qss(LIGHT)
        self.assertIn("QPushButton", qss)
        self.assertIn("QTabBar::tab", qss)


if __name__ == "__main__":
    unittest.main()
