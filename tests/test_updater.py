import unittest

from assistente_voz.updater import is_newer, parse_version


class TestUpdater(unittest.TestCase):
    def test_parse_version(self):
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3))
        self.assertEqual(parse_version("v0.1.0"), (0, 1, 0))
        self.assertEqual(parse_version("V2.0"), (2, 0))
        self.assertEqual(parse_version("1.4.0-beta"), (1, 4, 0))
        self.assertEqual(parse_version("1.2.3+build7"), (1, 2, 3))

    def test_is_newer(self):
        self.assertTrue(is_newer("0.2.0", "0.1.0"))
        self.assertTrue(is_newer("v1.0.0", "0.9.9"))
        self.assertTrue(is_newer("1.2.10", "1.2.9"))
        self.assertFalse(is_newer("0.1.0", "0.1.0"))
        self.assertFalse(is_newer("0.1.0", "0.2.0"))

    def test_is_newer_different_lengths(self):
        self.assertTrue(is_newer("1.2.1", "1.2"))
        self.assertFalse(is_newer("1.2", "1.2.0"))


if __name__ == "__main__":
    unittest.main()
