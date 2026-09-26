from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.adv_layout import ADV_DG_LAYOUT_PATCHES, ADV_SPEAKER_LAYOUT_PATCHES, inspect_adv_coordinate_consumers, patch_adv_horizontal_layout

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

    def test_horizontal_patch_swaps_proven_dg_origins_and_clears_constructor_vertical_flag(self) -> None:
        consumers = inspect_adv_coordinate_consumers(RAW)
        live = next(consumer for consumer in consumers if consumer.role == "dg_dialogue")
        secondary = next(consumer for consumer in consumers if consumer is not live)

        result = patch_adv_horizontal_layout(RAW)

        self.assertNotEqual(
            RAW[live.file_offset:live.file_offset + 0x140],
            result[live.file_offset:live.file_offset + 0x140],
        )
        self.assertEqual(
            RAW[secondary.file_offset:secondary.file_offset + 0x140],
            result[secondary.file_offset:secondary.file_offset + 0x140],
        )
        self.assertEqual(
            (
                (0x14FA9C, 0x00032C3C, 0x0003343C),
                (0x14FAA0, 0x00052C3F, 0x0006343F),
                (0x14FAF4, 0x0003343C, 0x00032C3C),
                (0x14FAF8, 0x0006343F, 0x00052C3F),
                # Unique ADV constructor callsite: orientation 1 is propagated
                # to all four child font canvases; zero makes the full DG object
                # horizontal instead of patching only one downstream fragment.
                (0x14E96C, 0x24060001, 0x24060000),
            ),
            ADV_DG_LAYOUT_PATCHES,
        )

        # Preserve both pristine coordinate formulas.  +0x465 remains normalized
        # exactly once by the existing signed /2 path at VA 0x24FA28; +0x463 is
        # never halved.  The final X/Y origin registers are swapped, while the
        # unique caller clears orientation before it is propagated to all four
        # child font canvases. The old r3 downstream-only patch must stay pristine.
        for offset in (0x14FA60, 0x14FAA4, 0x14FAA8, 0x14FAAC, 0x14FAB8):
            self.assertEqual(
                struct.unpack_from("<I", RAW, offset)[0],
                struct.unpack_from("<I", result, offset)[0],
            )
        self.assertEqual(
            struct.unpack_from("<I", RAW, 0x14FB7C)[0],
            struct.unpack_from("<I", result, 0x14FB7C)[0],
        )

        changed = {i for i, (before, after) in enumerate(zip(RAW, result)) if before != after}
        allowed = {
            byte_offset
            for offset, _expected, _replacement in (*ADV_DG_LAYOUT_PATCHES, *ADV_SPEAKER_LAYOUT_PATCHES)
            for byte_offset in range(offset, offset + 4)
        }
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)
        self.assertEqual(len(RAW), len(result))

    def test_horizontal_patch_also_clears_separate_speaker_name_canvas_orientation(self) -> None:
        result = patch_adv_horizontal_layout(RAW)

        # Runtime r4 proved the dialogue body and speaker label are distinct
        # renderers: body text became horizontal while ``Old man\'s voice``
        # remained vertical. The speaker-name state machine at VA 0x251470
        # constructs its own font canvas at VA 0x251594 with a2=1.
        self.assertEqual(0x24060001, struct.unpack_from("<I", RAW, 0x151608)[0])
        self.assertEqual(0x24060000, struct.unpack_from("<I", result, 0x151608)[0])

    def test_fail_closes_if_renderer_preimages_drift(self) -> None:
        for offset in (
            0x14FA60,
            0x14FAA8,
            0x1514F0,
            *(patch[0] for patch in ADV_DG_LAYOUT_PATCHES),
            *(patch[0] for patch in ADV_SPEAKER_LAYOUT_PATCHES),
        ):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "ADV (?:speaker )?layout preimage"):
                    patch_adv_horizontal_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
