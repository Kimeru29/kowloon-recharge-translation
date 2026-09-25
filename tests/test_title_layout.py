from __future__ import annotations

import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.title_layout import inspect_title_layout

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class TitleLayoutTests(unittest.TestCase):
    def test_title_layout_inventory_is_tied_to_m_title_region(self) -> None:
        evidence = inspect_title_layout(RAW)

        self.assertEqual(0x5CBDE8, evidence.string_arena_start)
        self.assertEqual(0x5CBE50, evidence.string_pointer_table)
        self.assertEqual(17, len(evidence.sprite_records))
        self.assertTrue(all(record.group in (88, 91) for record in evidence.sprite_records))

    def test_title_layout_identifies_paired_gp088_12_label_backings(self) -> None:
        evidence = inspect_title_layout(RAW)

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
        self.assertTrue(all(item.texture_name == "GRP088/GP088_12.TMX" for item in evidence.backing_instances))
        self.assertTrue(all(item.initial_scale_x == 0.0 for item in evidence.backing_instances))
        self.assertTrue(all(item.presented_scale_x == 1.0 for item in evidence.backing_instances))

    def test_group2_index8e_is_reveal_marker_not_static_backing(self) -> None:
        evidence = inspect_title_layout(RAW)

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
                    inspect_title_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
