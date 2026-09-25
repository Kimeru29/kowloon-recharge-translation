from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.adv_layout import inspect_adv_coordinate_consumers, patch_adv_horizontal_layout

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class AdvHorizontalLayoutTests(unittest.TestCase):
    def test_finds_both_known_adv_coordinate_consumers(self) -> None:
        consumers = inspect_adv_coordinate_consumers(RAW)

        self.assertEqual(
            [(0x14EDA0, 0x24ED20), (0x14FA60, 0x24F9E0)],
            [(consumer.file_offset, consumer.va) for consumer in consumers],
        )
        self.assertTrue(all(consumer.line_field == 0x463 for consumer in consumers))
        self.assertTrue(all(consumer.position_field == 0x465 for consumer in consumers))

    def test_consumer_probe_fails_closed_on_known_load_drift(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x14EDA0] ^= 1

        with self.assertRaisesRegex(ValueError, "ADV consumer preimage"):
            inspect_adv_coordinate_consumers(bytes(tampered))

    def test_static_trace_classifies_exactly_one_live_dg_dialogue_consumer(self) -> None:
        consumers = inspect_adv_coordinate_consumers(RAW)

        self.assertEqual(
            ["glyph_progress_gate", "dg_dialogue"],
            [consumer.role for consumer in consumers],
        )
        dg = [consumer for consumer in consumers if consumer.role == "dg_dialogue"]
        self.assertEqual(1, len(dg))
        self.assertEqual(0x14FA60, dg[0].file_offset)

    def test_transposes_line_and_glyph_axes_without_touching_font_renderer(self) -> None:
        result = patch_adv_horizontal_layout(RAW)

        # VA 0x24F9E0: X now reads byte-position field +0x465 rather than line +0x463.
        self.assertEqual(0x80430465, struct.unpack_from("<I", result, 0x14FA60)[0])
        # VA 0x24F9E8: normalize the byte position to a two-byte glyph index.
        self.assertEqual(0x00031843, struct.unpack_from("<I", result, 0x14FA68)[0])
        # VA 0x24FA24: Y now reads the line field +0x463.
        self.assertEqual(0x80440463, struct.unpack_from("<I", result, 0x14FAA4)[0])
        # VA 0x24FA28: line number is already a glyph-row index; do not halve it.
        self.assertEqual(0x0080182D, struct.unpack_from("<I", result, 0x14FAA8)[0])

        changed = [i for i, (a, b) in enumerate(zip(RAW, result)) if a != b]
        allowed = set()
        for offset in (0x14FA60, 0x14FA68, 0x14FAA4, 0x14FAA8):
            allowed.update(range(offset, offset + 4))
        self.assertTrue(changed)
        self.assertTrue(set(changed) <= allowed)
        self.assertEqual(len(RAW), len(result))

    def test_fail_closes_if_renderer_instructions_do_not_match_proven_build(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x14FA60] ^= 1
        with self.assertRaisesRegex(ValueError, "ADV layout preimage"):
            patch_adv_horizontal_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
