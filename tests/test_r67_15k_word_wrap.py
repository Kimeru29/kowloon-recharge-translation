"""Contract tests for the shared native description layout kernel."""
import unittest
from pathlib import Path
import struct

from tools.r67_15k_word_wrap import fixture, invoke, layout_text


class DescriptionWordWrapTests(unittest.TestCase):
    def assert_enclosed(self, result, width, height):
        self.assertGreaterEqual(result.factor, 0.)
        self.assertLessEqual(result.factor, 1.)
        for quad in result.quads:
            self.assertGreaterEqual(quad.left, 0.)
            self.assertGreaterEqual(quad.top, 0.)
            self.assertLessEqual(quad.right, width)
            self.assertLessEqual(quad.bottom, height)

    def test_grenade_wraps_whole_words_without_shrinking(self):
        text = 'Compressed gas grenade that is very lethal upon impact. [Blast] 20% Sprain'
        result = layout_text([text], width=198., height=60., scale=.5)
        self.assertEqual(result.lines, ('Compressed gas grenade', 'that is very lethal upon',
                                       'impact. [Blast] 20%', 'Sprain'))
        self.assertEqual(result.factor, 1.)
        self.assert_enclosed(result, 198., 60.)

    def test_font_growth_changes_word_boundaries(self):
        text = 'Ancient Heracleion epitaph.'
        normal = layout_text([text], width=336., height=90., scale=1., space_ratio=.5)
        larger = layout_text([text], width=336., height=90., scale=1.25, space_ratio=.5)
        self.assertEqual(normal.lines, ('Ancient Heracleion', 'epitaph.'))
        self.assertEqual(larger.lines, ('Ancient', 'Heracleion', 'epitaph.'))
        self.assertEqual(larger.factor, 1.)
        self.assert_enclosed(larger, 336., 90.)

    def test_inspection_fields_flow_as_one_group(self):
        paragraphs = ['Ancient Heracleion epitaph.', 'Strong Kirlian effect identified.',
                      '台座に固定されている。', '']
        result = layout_text(paragraphs, width=336., height=90., scale=1., space_ratio=.5)
        self.assertEqual(len(result.lines), 5)
        self.assertEqual(result.factor, 1.)
        self.assert_enclosed(result, 336., 90.)

    def test_over_capacity_retains_every_visible_character(self):
        text = 'Complete description with every original word preserved. ' * 4
        result = layout_text([text], width=198., height=60., scale=1.)
        self.assertLess(result.factor, 1.)
        self.assertEqual(''.join(result.lines).replace(' ', ''), text.replace(' ', ''))
        self.assert_enclosed(result, 198., 60.)

    def test_long_unbroken_word_uses_emergency_wrap_without_dropping_glyphs(self):
        result = layout_text(['X' * 60], width=198., height=60., scale=.5)
        self.assertEqual(''.join(result.lines), 'X' * 60)
        self.assertEqual(result.factor, 1.)
        self.assert_enclosed(result, 198., 60.)

    def test_empty_description_is_valid(self):
        result = layout_text(['', '  '], width=198., height=60., scale=.5)
        self.assertEqual(result.quads, ())
        self.assertEqual(result.lines, ())

    def test_complete_catalogues_preserve_all_visible_text_at_live_sizes(self):
        from tools.r67_15i_item_details import catalogue_rows
        from tools.r67_15j_inspection_layout import catalogue
        raw = (Path(__file__).resolve().parents[1] /
               'local/r67-15j-generic-text-bounds.elf').read_bytes()
        items, objects = catalogue_rows(raw), catalogue(raw)
        self.assertEqual((len(items), len(objects)), (431, 600))
        for owner, text in [(i, ['\n'.join(lines)]) for i, lines in items.items()]:
            for scale in (.5, .75, 1.):
                with self.subTest(item=owner, scale=scale):
                    result = layout_text(text, width=198., height=60., scale=scale,
                                         soft=True)
                    self.assert_enclosed(result, 198., 60.)
                    self.assertEqual(''.join(result.lines).replace(' ', ''),
                                     ''.join(text).replace('\n', '').replace(' ', '').replace('　', ''))
        for owner, fields in objects.items():
            for scale in (1., 1.25):
                with self.subTest(object=hex(owner), scale=scale):
                    text = fields[1:5]
                    result = layout_text(text, width=336., height=90., scale=scale,
                                         space_ratio=.5)
                    self.assert_enclosed(result, 336., 90.)
                    self.assertEqual(''.join(result.lines).replace(' ', ''),
                                     ''.join(text).replace(' ', '').replace('　', ''))

    def test_repeated_draw_is_idempotent_and_preserves_every_nonvertex_byte(self):
        ram, context, visible = fixture(['Long description ' * 8], width=198.,
                                        height=60., scale=1.)
        before = bytes(ram)
        self.assertEqual(invoke(ram, context), 1)
        first = bytes(ram)
        factor = context.factor
        self.assertEqual(invoke(ram, context), 1)
        self.assertEqual(bytes(ram), first)
        self.assertEqual(context.factor, factor)
        allowed = {node + offset + byte for node, _ in visible
                   for offset in (0x10, 0x50, 0x90, 0xd0) for byte in range(8)}
        self.assertFalse({i for i, (a, b) in enumerate(zip(before, ram)) if a != b} - allowed)

    def test_bad_chain_or_unknown_control_does_not_partially_write(self):
        for kind in ('cycle', 'control', 'scale', 'pointer'):
            ram, context, visible = fixture(['Word ' * 10], width=198., height=60., scale=.5)
            node = visible[-1][0]
            if kind == 'cycle':
                struct.pack_into('<I', ram, node + 0x120, visible[0][0])
            elif kind == 'control':
                struct.pack_into('<I', ram, node, 0xffffff49)
            elif kind == 'scale':
                struct.pack_into('<f', ram, context.fonts[0] + 0x48, float('nan'))
            else:
                struct.pack_into('<I', ram, node + 0x120, 0x2000000)
            before = bytes(ram)
            self.assertEqual(invoke(ram, context), 0, kind)
            self.assertEqual(ram, before)

    def test_width_mutation_changes_layout_and_full_cell_extent_is_used(self):
        wide = layout_text(['AAAA BBBB CCCC'], width=104., height=60., scale=.5)
        narrow = layout_text(['AAAA BBBB CCCC'], width=70., height=60., scale=.5)
        self.assertEqual(wide.lines, ('AAAA BBBB', 'CCCC'))
        self.assertEqual(narrow.lines, ('AAAA', 'BBBB', 'CCCC'))
        self.assert_enclosed(narrow, 70., 60.)


if __name__ == '__main__':
    unittest.main()
