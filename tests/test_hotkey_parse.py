import unittest

from assistente_voz.hotkey import parse_hotkey


class TestParseHotkey(unittest.TestCase):
    def test_combo(self):
        mods, main = parse_hotkey("ctrl+alt+space")
        self.assertEqual(mods, frozenset({"ctrl", "alt"}))
        self.assertEqual(main, "space")

    def test_single_key(self):
        mods, main = parse_hotkey("f8")
        self.assertEqual(mods, frozenset())
        self.assertEqual(main, "f8")

    def test_case_and_spaces(self):
        mods, main = parse_hotkey(" Ctrl + Shift + A ")
        self.assertEqual(mods, frozenset({"ctrl", "shift"}))
        self.assertEqual(main, "a")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            parse_hotkey("")

    def test_only_modifiers_raises(self):
        with self.assertRaises(ValueError):
            parse_hotkey("ctrl+alt")

    def test_two_main_keys_raises(self):
        with self.assertRaises(ValueError):
            parse_hotkey("a+b")


if __name__ == "__main__":
    unittest.main()
