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

    def test_title_layout_resolves_group88_index12_to_gp088_08_backing(self) -> None:
        evidence = title_layout.inspect_title_layout(RAW)

        self.assertEqual(
            (
                (0x5CBF3C, 88, 12, 64.0, 296.0),
                (0x5CBF50, 88, 12, 376.0, 296.0),
            ),
            tuple(
                (item.record_offset, item.group, item.index, item.x, item.y)
                for item in evidence.backing_instances
            ),
        )
        self.assertEqual(((68.0, 299.0), (380.0, 299.0)), evidence.label_anchors)
        self.assertTrue(all(item.texture_name == "GRP088/GP088_08.TMX" for item in evidence.backing_instances))
        self.assertTrue(all(item.initial_scale_x == 0.0 for item in evidence.backing_instances))
        self.assertTrue(all(item.presented_scale_x == 1.0 for item in evidence.backing_instances))
        self.assertTrue(any("texture ordinal 8" in item for item in evidence.evidence))
        self.assertTrue(any("width 72" in item for item in evidence.evidence))

    def test_group2_index8e_is_reveal_marker_not_static_backing(self) -> None:
        evidence = title_layout.inspect_title_layout(RAW)

        self.assertEqual(0x19A118, evidence.reveal_marker.file_offset)
        self.assertEqual((2, 0x8E), (evidence.reveal_marker.group, evidence.reveal_marker.index))
        self.assertTrue(evidence.reveal_marker.x_is_mutated_during_reveal)
        self.assertNotIn(
            evidence.reveal_marker.file_offset,
            {item.record_offset for item in evidence.backing_instances},
        )

    def test_title_layout_probe_fails_closed_on_owner_or_marker_drift(self) -> None:
        for offset in (0x5CBE60, 0x5CBF3C, 0x1AC5B8, 0x19A1BC):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1

                with self.assertRaisesRegex(ValueError, "title layout preimage"):
                    title_layout.inspect_title_layout(bytes(tampered))

    def test_title_patch_recenters_labels_and_expands_actual_gp088_08_backing(self) -> None:
        result = title_layout.patch_title_layout(RAW)

        # The live label renderer advances exactly 16 px per two-byte glyph.
        # The pristine four-glyph labels therefore center at X=100 and X=412:
        #   68 + 4*16/2 = 100; 380 + 4*16/2 = 412.
        # Preserve those visual centers for exact New Game (8 glyphs) and
        # Load Game (9 glyphs), giving new left origins 36 and 340.
        self.assertEqual(0x3C024210, struct.unpack_from("<I", result, 0x1ABF64)[0])  # 36.0f
        self.assertEqual(0x3C0243AA, struct.unpack_from("<I", result, 0x1ABF84)[0])  # 340.0f

        # Runtime disproves the generic-font X-offset hypothesis. The visible
        # backing is group 88/index 12, whose sprite metadata selects texture 8
        # (GP088_08): pristine width=72 and U extent=72/512. Both title-state
        # instances use that same sprite. Longest English label is 9*16=144px;
        # preserve the original 4px-per-side padding => 152px, centered on the
        # accepted label centers X=100/412.
        self.assertEqual(128, len("New Game") * 16)
        self.assertEqual(144, len("Load Game") * 16)
        self.assertEqual(0x43180000, struct.unpack_from("<I", result, 0x3787A4)[0])  # width 152
        self.assertEqual(0x3E980000, struct.unpack_from("<I", result, 0x3787BC)[0])  # U=152/512
        self.assertEqual(0x41C00000, struct.unpack_from("<I", result, 0x5CBF48)[0])  # left X=24
        self.assertEqual(0x43A80000, struct.unpack_from("<I", result, 0x5CBF5C)[0])  # left X=336

        # The prior candidate changed these generic text-canvas X offsets 64->80,
        # but runtime showed no backing-width effect. r11 restores them pristine.
        self.assertEqual(RAW[0x19AB38:0x19AB3C], result[0x19AB38:0x19AB3C])
        self.assertEqual(RAW[0x19ABD8:0x19ABDC], result[0x19ABD8:0x19ABDC])

        # Preserve the existing reveal-animation target and unrelated third-object
        # call while changing only the proven backing metadata/positions.
        self.assertEqual(RAW[0x6989C0:0x6989C8], result[0x6989C0:0x6989C8])
        self.assertEqual(RAW[0x1AC600:0x1AC604], result[0x1AC600:0x1AC604])

        changed = {index for index, (before, after) in enumerate(zip(RAW, result, strict=True)) if before != after}
        allowed = (
            set(range(0x1ABF64, 0x1ABF68))
            | set(range(0x1ABF84, 0x1ABF88))
            | set(range(0x3787A4, 0x3787A8))
            | set(range(0x3787BC, 0x3787C0))
            | set(range(0x5CBF48, 0x5CBF4C))
            | set(range(0x5CBF5C, 0x5CBF60))
        )
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)
        self.assertTrue(changed & set(range(0x1ABF64, 0x1ABF68)))
        self.assertTrue(changed & set(range(0x1ABF84, 0x1ABF88)))

    def test_title_layout_patch_fails_closed_on_label_anchor_drift(self) -> None:
        for offset in (0x1ABF64, 0x1ABF84, 0x3787A4, 0x3787BC, 0x5CBF48, 0x5CBF5C):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "title layout preimage"):
                    title_layout.patch_title_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
