import unittest
from pathlib import Path
from tools.tmx import find_tmx_entry, _decode_indices, _decode_palette

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'local/r67-14y-analysis/current-B_GP018.BIN'


@unittest.skipUnless(SOURCE.exists(), 'requires pinned local save atlas')
class SaveAtlasTests(unittest.TestCase):
    def test_only_native_caption_rectangles_change(self):
        from tools.r67_14y_save_atlas import apply, RECTS
        source = SOURCE.read_bytes()
        out, report = apply(source)
        entry = find_tmx_entry(source, 'GRP018/GP018_03.TMX')
        self.assertEqual(find_tmx_entry(out, entry.name), entry)
        self.assertEqual(_decode_palette(source, entry), _decode_palette(out, entry))
        a, b = _decode_indices(source, entry), _decode_indices(out, entry)
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                self.assertTrue(any(l <= i % 512 < r and t <= i // 512 < d
                                    for l, t, r, d in RECTS))
        self.assertEqual(report['captions'], ['LOAD', 'SAVE', 'BACK'])
        self.assertNotEqual(a, b)

    def test_source_mutation_fails_closed(self):
        from tools.r67_14y_save_atlas import apply
        b = bytearray(SOURCE.read_bytes())
        b[660736] ^= 1
        with self.assertRaisesRegex(ValueError, 'preimage'):
            apply(bytes(b))

    def test_overlong_caption_and_bad_rect_rejected(self):
        from tools.r67_14y_save_atlas import draw
        b = bytearray(512 * 64)
        with self.assertRaisesRegex(ValueError, 'fit'):
            draw(b, 512, 64, (0, 40, 32, 64), 'SAVE SAVE', 168, 188)
        with self.assertRaisesRegex(ValueError, 'rectangle'):
            draw(b, 512, 64, (500, 40, 520, 64), 'SAVE', 168, 188)


if __name__ == '__main__':
    unittest.main()
