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
                # r7 runtime proves orientation and spacing are now correct, but
                # the block is still too high. After transposition this 114px
                # Japanese column base is the live body Y origin. Move it near
                # the lower dialogue-safe area without touching line spacing.
                (0x14FA78, 0x3C0342E4, 0x3C03439C),  # 114 -> 312 px body base
                # The live child font constructor uses style 1, whose profile is
                # 12x12. After transposition the old Japanese 26 px column stride
                # becomes English X spacing, so match the actual 12 px glyph
                # advance instead of leaving every fragment 14 px too far apart.
                (0x14FAC8, 0x3C0341D0, 0x3C034140),
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

        # VA 0x24FAF0 creates each body fragment with font style 1. Its profile
        # record at VA 0x5D7800 stores width/height 12/12 in the low bytes.
        self.assertEqual(0x24050001, struct.unpack_from("<I", RAW, 0x14FB70)[0])
        self.assertEqual((12, 12), tuple(RAW[0x4D7884:0x4D7886]))
        self.assertEqual(0x3C034140, struct.unpack_from("<I", result, 0x14FAC8)[0])

        changed = {i for i, (before, after) in enumerate(zip(RAW, result)) if before != after}
        allowed = {
            byte_offset
            for offset, _expected, _replacement in (*ADV_DG_LAYOUT_PATCHES, *ADV_SPEAKER_LAYOUT_PATCHES)
            for byte_offset in range(offset, offset + 4)
        }
        self.assertTrue(changed)
        self.assertTrue(changed <= allowed)
        self.assertEqual(len(RAW), len(result))

    def test_horizontal_patch_preserves_r5_record_label_orientation_change(self) -> None:
        result = patch_adv_horizontal_layout(RAW)

        # r5 changed the separate 0x251470 ADV record-label canvas. Runtime r5
        # disproved it as the inline bracket-derived DG speaker owner, but there
        # is not yet evidence that the record-label patch itself is harmful or
        # dead. Preserve that shipped change until runtime gives a reason to
        # remove it; the actual DG speaker owner is tested independently below.
        self.assertEqual(0x24060001, struct.unpack_from("<I", RAW, 0x151608)[0])
        self.assertEqual(0x24060000, struct.unpack_from("<I", result, 0x151608)[0])

    def test_inline_bracket_speaker_uses_horizontal_advance_and_header_geometry(self) -> None:
        result = patch_adv_horizontal_layout(RAW)

        # r6 runtime disproved the mode-only hypothesis: changing speaker mode
        # 2 -> 1 still left the resolved name vertical. The generic constructor
        # at VA 0x190A50 hardcodes a2=1 before calling 0x188AD0; 0x188AD0 stores
        # that byte at +0x24, and the live glyph renderer advances Y whenever
        # +0x24 is nonzero. Make that orientation depend on the saved text mode
        # (s0): only mode 0 becomes horizontal, while every existing nonzero mode
        # retains pristine vertical advance. The inline speaker is the only direct
        # 0x190A50 caller moved to mode 0. r7 proved that horizontal path; r8
        # keeps X=20 and moves only Y to 276, above body base X=20/Y=312.
        expected = (
            (0x150048, 0x3C024301, 0x3C0241A0),  # 129 -> 20 px X
            (0x150050, 0x3C0241A0, 0x3C02438A),  # 20 -> 276 px Y
            (0x15006C, 0x24050002, 0x24050000),  # speaker mode 2 -> 0
            (0x090B30, 0x24060001, 0x0010302B),  # a2 = (mode != 0)
            (0x151608, 0x24060001, 0x24060000),  # preserved r5 record label
        )
        self.assertEqual(expected, ADV_SPEAKER_LAYOUT_PATCHES)
        for offset, pristine, replacement in expected:
            self.assertEqual(pristine, struct.unpack_from("<I", RAW, offset)[0])
            self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])

    def test_fail_closes_if_renderer_preimages_drift(self) -> None:
        for offset in (
            0x14FA60,
            0x14FAA8,
            0x1514F0,
            0x14FB70,
            0x4D7884,
            *(patch[0] for patch in ADV_DG_LAYOUT_PATCHES),
            *(patch[0] for patch in ADV_SPEAKER_LAYOUT_PATCHES),
        ):
            with self.subTest(offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "ADV (?:speaker |body style )?layout preimage"):
                    patch_adv_horizontal_layout(bytes(tampered))


if __name__ == "__main__":
    unittest.main()
