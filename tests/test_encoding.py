from __future__ import annotations

import unittest

from tools.localization import encode_ps2_english


class PortablePs2EnglishEncodingTests(unittest.TestCase):
    def test_encodes_complete_observed_official_repertoire_as_two_byte_cp932(self) -> None:
        text = " !\"'()*,-./0123456789;=?ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz—―’♪【】"

        encoded = encode_ps2_english(text)
        decoded = encoded.decode("cp932")

        self.assertEqual(len(decoded) * 2, len(encoded))
        self.assertNotIn("—", decoded)
        self.assertIn("―", decoded)
        self.assertIn("’", decoded)
        self.assertIn("♪", decoded)
        self.assertIn("【", decoded)
        self.assertIn("】", decoded)
        self.assertTrue(all(ord(char) >= 0x80 for char in decoded))

    def test_maps_arbitrary_printable_ascii_punctuation_to_fullwidth_glyphs(self) -> None:
        encoded = encode_ps2_english('"()*-./;=')

        self.assertEqual("＂（）＊－．／；＝", encoded.decode("cp932"))


if __name__ == "__main__":
    unittest.main()
