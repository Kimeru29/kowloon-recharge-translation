from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
import tools.title_layout as title_layout

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class TitleLayoutTests(unittest.TestCase):
    def test_title_layout_inventory_is_tied_to_m_title_region(self) -> None:
        evidence = title_layout.inspect_title_layout(RAW)

        self.assertEqual(0x5CBDE8, evidence.string_arena_start)
        self.assertEqual(0x5CBE50, evidence.string_pointer_table)
        self.assertEqual(17, len(evidence.sprite_records))
        self.assertTrue(all(record.group in (88, 91) for record in evidence.sprite_records))

    def test_title_layout_classifies_gp088_12_as_packed_title_art_not_label_backing(self) -> None:
        evidence = title_layout.inspect_title_layout(RAW)

        self.assertEqual(
            (
                (0x5CBF3C, 88, 12, 64.0, 296.0),
                (0x5CBF50, 88, 12, 376.0, 296.0),
            ),
            tuple(
                (item.record_offset, item.group, item.index, item.x, item.y)
                for item in evidence.packed_title_instances
            ),
        )
        self.assertEqual(((68.0, 299.0), (380.0, 299.0)), evidence.label_anchors)
        self.assertTrue(all(item.texture_name == "GRP088/GP088_12.TMX" for item in evidence.packed_title_instances))
        self.assertTrue(all(item.initial_scale_x == 0.0 for item in evidence.packed_title_instances))
        self.assertTrue(all(item.presented_scale_x == 1.0 for item in evidence.packed_title_instances))
        self.assertTrue(any("packed title art" in item for item in evidence.evidence))

    def test_group2_index8e_is_reveal_marker_not_static_backing(self) -> None:
        evidence = title_layout.inspect_title_layout(RAW)

        self.assertEqual(0x19A118, evidence.reveal_marker.file_offset)
        self.assertEqual((2, 0x8E), (evidence.reveal_marker.group, evidence.reveal_marker.index))
        self.assertTrue(evidence.reveal_marker.x_is_mutated_during_reveal)
        self.assertNotIn(
            evidence.reveal_marker.file_offset,
            {item.record_offset for item in evidence.packed_title_instances},
        )

    def test_title_layout_probe_fails_closed_on_owner_or_marker_drift(self) -> None:
        for offset in (0x5CBE60, 0x5CBF3C, 0x1AC5B8, 0x19A1BC):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1

                with self.assertRaisesRegex(ValueError, "title layout preimage"):
                    title_layout.inspect_title_layout(bytes(tampered))

    def test_title_patch_recenters_wide_english_labels_without_rescaling_packed_title_art(self) -> None:
        result = title_layout.patch_title_layout(RAW)

        # The live label renderer advances exactly 16 px per two-byte glyph.
        # The pristine four-glyph labels therefore center at X=100 and X=412:
        #   68 + 4*16/2 = 100; 380 + 4*16/2 = 412.
        # Preserve those visual centers for exact New Game (8 glyphs) and
        # Load Game (9 glyphs), giving new left origins 36 and 340.
        self.assertEqual(0x3C024210, struct.unpack_from("<I", result, 0x1ABF64)[0])  # 36.0f
        self.assertEqual(0x3C0243AA, struct.unpack_from("<I", result, 0x1ABF84)[0])  # 340.0f

        # r5 widened GP088_12 after misclassifying it as menu backing. Existing
        # asset evidence and r5 runtime prove it is packed title artwork, so r6
        # must preserve both its shared (1,1) target and the third-object call.
        self.assertEqual(RAW[0x6989C0:0x6989C8], result[0x6989C0:0x6989C8])
        self.assertEqual(RAW[0x1AC600:0x1AC604], result[0x1AC600:0x1AC604])

        changed = {index for index, (before, after) in enumerate(zip(RAW, result, strict=True)) if before != after}
        allowed = set(range(0x1ABF64, 0x1ABF68)) | set(range(0x1ABF84, 0x1ABF88))
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)
        self.assertTrue(changed & set(range(0x1ABF64, 0x1ABF68)))
        self.assertTrue(changed & set(range(0x1ABF84, 0x1ABF88)))

    def test_title_layout_patch_fails_closed_on_label_anchor_drift(self) -> None:
        for offset in (0x1ABF64, 0x1ABF84):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "title layout preimage"):
                    title_layout.patch_title_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
