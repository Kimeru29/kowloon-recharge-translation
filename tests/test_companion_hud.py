from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.companion_afk_data import COMPANION_AFK_OFFICIAL_FIELDS, COMPANION_AFK_TRANSLATIONS
from tools.companion_hud import (
    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_BUBBLE_METADATA_VA,
    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
    COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY,
    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
    COMPANION_ACTION_SLOT_RESOURCES,
    COMPANION_ACTION_SLOT_TEXT_X,
    COMPANION_ACTION_ID_GETTER_VA,
    COMPANION_ACTION_ID_KEY,
    COMPANION_ACTION_ID_REFERENCE_PREIMAGES,
    COMPANION_ACTION_LABELS,
    COMPANION_ACTION_LAYOUTS,
    COMPANION_ACTION_LAYOUT_PATCHES,
    COMPANION_ACTION_RUNTIME_HOOK_SIZE,
    COMPANION_ACTION_RUNTIME_PREIMAGES,
    COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE,
    COMPANION_ACTION_VISIBILITY_HOOK_SIZE,
    COMPANION_ACTION_VISIBILITY_PREIMAGES,
    COMPANION_AFK_PANEL_FRAME_COUNT,
    COMPANION_AFK_PANEL_FRAME_STRIDE,
    COMPANION_AFK_PANEL_METADATA_OFFSET,
    COMPANION_AFK_PANEL_METADATA_VA,
    COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
    COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES,
    COMPANION_AFK_PANEL_PRISTINE_PLACEMENTS,
    COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET,
    COMPANION_AFK_PANEL_TARGET_GEOMETRIES,
    COMPANION_AFK_PANEL_TARGET_PLACEMENTS,
    COMPANION_AFK_EMPTY_VA,
    COMPANION_AFK_EXPECTED_LIVE_FIELDS,
    COMPANION_AFK_MAX_CHARS,
    COMPANION_AFK_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_SCALE_HOOK_SIZE,
    COMPANION_AFK_TEXT_SAFE_CELLS,
    COMPANION_AFK_TEXT_SCALES,
    COMPANION_AFK_RECORD_COUNT,
    COMPANION_AFK_RECORD_STRIDE,
    COMPANION_AFK_TABLE_OFFSET,
    COMPANION_SLOT_INDEX_PREIMAGES,
    COMPANION_SLOT_POSITIONS,
    COMPANION_SLOT_POSITION_TABLE_OFFSET,
    COMPANION_COMMENT_LINES,
    encode_companion_action,
    patch_companion_action_layout,
    patch_companion_afk_layout,
    relocated_companion_entries,
    validate_companion_afk_source,
    validate_companion_hud_source,
    wrap_companion_action_text,
)
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.early_ui import build_early_ui_elf
from tools.localization import encode_ps2_english


ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


def _read_at_va(raw: bytes, va: int, size: int) -> bytes:
    _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
        "<IIIIIIII", raw, 0x54
    )
    relative = va - p_vaddr
    if 0 <= relative and relative + size <= p_filesz:
        return raw[p_offset + relative:p_offset + relative + size]
    main_offset = va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET
    if 0 <= main_offset <= len(raw) - size:
        return raw[main_offset:main_offset + size]
    return b""


class CompanionHudTests(unittest.TestCase):
    def test_r43_afk_inventory_is_bounded_contextual_and_fail_closed(self) -> None:
        self.assertEqual(COMPANION_AFK_RECORD_COUNT, len(COMPANION_AFK_TRANSLATIONS))
        self.assertEqual(
            {(1, 15, 1), (13, 2, 1), (23, 0, 1), (23, 19, 2)},
            set(COMPANION_AFK_OFFICIAL_FIELDS),
        )
        self.assertEqual("Be careful.", COMPANION_AFK_TRANSLATIONS[15][0])
        self.assertEqual("Hello.", COMPANION_AFK_TRANSLATIONS[(13 - 1) * 20 + 2][0])
        self.assertEqual("Be careful.", COMPANION_AFK_TRANSLATIONS[(23 - 1) * 20][0])
        self.assertEqual(
            "I'm going to do my best!",
            COMPANION_AFK_TRANSLATIONS[(23 - 1) * 20 + 19][1],
        )
        self.assertEqual(
            ("Hm? Lost your way?", ""),
            COMPANION_AFK_TRANSLATIONS[(25 - 1) * 20 + 1],
        )

        live_fields = 0
        english_by_source_va: dict[int, str] = {}
        for record_index, (english_line1, english_line2) in enumerate(COMPANION_AFK_TRANSLATIONS):
            record_offset = COMPANION_AFK_TABLE_OFFSET + record_index * COMPANION_AFK_RECORD_STRIDE
            _enabled, _companion_id, line1_va, line2_va = struct.unpack_from(
                "<IIII", RAW, record_offset
            )
            for source_va, english in ((line1_va, english_line1), (line2_va, english_line2)):
                if source_va == COMPANION_AFK_EMPTY_VA:
                    self.assertEqual("", english)
                    continue
                live_fields += 1
                self.assertTrue(english)
                self.assertLessEqual(len(english), COMPANION_AFK_MAX_CHARS)
                previous_english = english_by_source_va.setdefault(source_va, english)
                self.assertEqual(previous_english, english)
                encode_ps2_english(english, collapse_spaces=False)
        self.assertEqual(COMPANION_AFK_EXPECTED_LIVE_FIELDS, live_fields)
        validate_companion_afk_source(RAW)

        table_tampered = bytearray(RAW)
        table_tampered[COMPANION_AFK_TABLE_OFFSET + 0x20] ^= 1
        with self.assertRaisesRegex(ValueError, "companion AFK table preimage drifted"):
            validate_companion_afk_source(bytes(table_tampered))

        source_tampered = bytearray(RAW)
        source_tampered[0x3D20D0] ^= 1  # Salah 25:01: む？迷ったかの？
        with self.assertRaisesRegex(ValueError, "companion AFK source"):
            validate_companion_afk_source(bytes(source_tampered))

    def test_r43_build_relocates_only_structural_afk_pointer_fields(self) -> None:
        entries = tuple(
            entry
            for entry in relocated_companion_entries(RAW)
            if entry.key.startswith("companion_afk_") and entry.pointer_offsets
        )
        self.assertEqual(COMPANION_AFK_EXPECTED_LIVE_FIELDS, len(entries))

        expected_pointer_offsets: set[int] = set()
        for record_index in range(COMPANION_AFK_RECORD_COUNT):
            record_offset = COMPANION_AFK_TABLE_OFFSET + record_index * COMPANION_AFK_RECORD_STRIDE
            _enabled, _companion_id, line1_va, line2_va = struct.unpack_from(
                "<IIII", RAW, record_offset
            )
            if line1_va != COMPANION_AFK_EMPTY_VA:
                expected_pointer_offsets.add(record_offset + 8)
            if line2_va != COMPANION_AFK_EMPTY_VA:
                expected_pointer_offsets.add(record_offset + 12)

        actual_pointer_offsets = {
            pointer_offset
            for entry in entries
            for pointer_offset in entry.pointer_offsets
        }
        self.assertEqual(expected_pointer_offsets, actual_pointer_offsets)
        self.assertEqual(COMPANION_AFK_EXPECTED_LIVE_FIELDS, len(actual_pointer_offsets))

        salah = next(entry for entry in entries if entry.key == "companion_afk_25_01_1")
        self.assertEqual((0x3F5028,), salah.pointer_offsets)
        self.assertEqual(
            encode_ps2_english("Hm? Lost your way?", collapse_spaces=False) + b"\x00",
            salah.encoded,
        )

        result = build_early_ui_elf(RAW)
        target_va = struct.unpack_from("<I", result, 0x3F5028)[0]
        self.assertEqual(salah.encoded, _read_at_va(result, target_va, len(salah.encoded)))
        source = "む？迷ったかの？".encode("cp932") + b"\x00"
        self.assertEqual(source, result[0x3D20D0:0x3D20D0 + len(source)])

    def test_r30_comment_inventory_is_complete_ps4_exact_and_fail_closed(self) -> None:
        self.assertEqual(1650, len(COMPANION_COMMENT_LINES))
        self.assertEqual(1784, sum(len(spec.pointer_offsets) for spec in COMPANION_COMMENT_LINES))
        self.assertEqual(7, sum(spec.official_english == "@D" for spec in COMPANION_COMMENT_LINES))
        self.assertEqual(1650, len({spec.source_offset for spec in COMPANION_COMMENT_LINES}))
        first = COMPANION_COMMENT_LINES[0]
        self.assertEqual(0x3C19A0, first.source_offset)
        self.assertEqual("千年以上の昔、地震で水没した", first.source_text)
        self.assertEqual("Heracleion flooded after an", first.official_english)
        self.assertEqual((0x3D3328,), first.pointer_offsets)
        validate_companion_hud_source(RAW)

        tampered = bytearray(RAW)
        tampered[first.pointer_offsets[0]] ^= 1
        with self.assertRaisesRegex(ValueError, "companion comment pointer preimage mismatch"):
            validate_companion_hud_source(bytes(tampered))

    def test_r30_companion_action_inventory_covers_hud_skill_labels(self) -> None:
        self.assertEqual(31, len(COMPANION_ACTION_LABELS))
        throw_rock = COMPANION_ACTION_LABELS[25]
        self.assertEqual(0x3F8D84, throw_rock.pointer_offset)
        self.assertEqual("石を投げる", throw_rock.source_text)
        self.assertEqual("Throw a Rock", throw_rock.english)
        self.assertEqual("official_exact", throw_rock.provenance)
        self.assertEqual(26, sum(spec.provenance == "official_exact" for spec in COMPANION_ACTION_LABELS))

    def test_r30_build_relocates_companion_comments_and_current_hud_action(self) -> None:
        result = build_early_ui_elf(RAW)
        cases = (
            (0x3D3328, "Heracleion flooded after an"),
            (0x3D332C, "earthquake 1,000 years ago."),
            (0x3F8D84, "Throw a Rock"),
        )
        for pointer_offset, english in cases:
            with self.subTest(pointer_offset=hex(pointer_offset)):
                target_va = struct.unpack_from("<I", result, pointer_offset)[0]
                expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
                self.assertEqual(expected, _read_at_va(result, target_va, len(expected)))

        for spec in (COMPANION_COMMENT_LINES[0], COMPANION_ACTION_LABELS[25]):
            source = spec.source_text.encode("cp932") + b"\x00"
            self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])

    def test_r36_companion_actions_wrap_generically_and_preserve_r35_short_layout(self) -> None:
        self.assertEqual(("Throw a Rock",), wrap_companion_action_text("Throw a Rock"))
        self.assertEqual(
            ("Smoking an Aroma", "Stick"),
            wrap_companion_action_text("Smoking an Aroma Stick"),
        )
        self.assertEqual(
            ("Secret Technique:", "Reverse Waterfall", "Blade"),
            wrap_companion_action_text("Secret Technique: Reverse Waterfall Blade"),
        )

        self.assertEqual((48.0, 45.0, -99.0), (
            COMPANION_ACTION_LAYOUTS[25].height,
            COMPANION_ACTION_LAYOUTS[25].pivot_y,
            COMPANION_ACTION_LAYOUTS[25].text_y,
        ))
        self.assertEqual((64.0, 61.0, -115.0), (
            COMPANION_ACTION_LAYOUTS[2].height,
            COMPANION_ACTION_LAYOUTS[2].pivot_y,
            COMPANION_ACTION_LAYOUTS[2].text_y,
        ))
        self.assertEqual((80.0, 77.0, -131.0), (
            COMPANION_ACTION_LAYOUTS[24].height,
            COMPANION_ACTION_LAYOUTS[24].pivot_y,
            COMPANION_ACTION_LAYOUTS[24].text_y,
        ))
        self.assertTrue(all(len(line) <= 17 for layout in COMPANION_ACTION_LAYOUTS for line in layout.lines))

        result = build_early_ui_elf(RAW)
        # r47 no longer bakes compact L1 geometry into the shared resource.
        # Static 0x68/0x69 stay native for AFK; the action hook applies the
        # accepted compact body immediately before each normal L1 callout.
        bubble_offsets = (
            COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
            COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
            COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
        )
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            tuple(struct.unpack_from("<f", result, offset)[0] for offset in bubble_offsets),
        )

        # Every owned action is encoded by the same wrapper. Long official PS4
        # labels receive literal 0x0A line breaks; short labels remain unchanged.
        for action_id in (2, 24, 25):
            spec = COMPANION_ACTION_LABELS[action_id]
            target_va = struct.unpack_from("<I", result, spec.pointer_offset)[0]
            expected = encode_companion_action(spec.english)
            self.assertEqual(expected, _read_at_va(result, target_va, len(expected)))
        self.assertIn(b"\x0a", encode_companion_action(COMPANION_ACTION_LABELS[2].english))
        self.assertEqual(2, encode_companion_action(COMPANION_ACTION_LABELS[24].english).count(b"\x0a"))
        self.assertNotIn(b"\x0a", encode_companion_action(COMPANION_ACTION_LABELS[25].english))

    def test_r46_afk_panel_preserves_native_geometry_and_placements(self) -> None:
        result = patch_companion_afk_layout(RAW)

        # r46 is deliberately validation-only after r45 made the blue panel
        # disappear at runtime. Every native 0x6A byte must remain pristine.
        self.assertEqual(RAW, result)
        self.assertEqual(
            (COMPANION_AFK_PANEL_METADATA_VA, COMPANION_AFK_PANEL_FRAME_COUNT),
            struct.unpack_from("<II", result, COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET),
        )
        for frame_index, expected in enumerate(COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES):
            frame_offset = (
                COMPANION_AFK_PANEL_METADATA_OFFSET
                + frame_index * COMPANION_AFK_PANEL_FRAME_STRIDE
            )
            self.assertEqual(expected, struct.unpack_from("<ffff", result, frame_offset + 4))

        for offset, expected in zip(
            COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
            COMPANION_AFK_PANEL_PRISTINE_PLACEMENTS,
            strict=True,
        ):
            self.assertEqual(expected, struct.unpack_from("<IIfff", result, offset))

        owner_bytes = struct.pack("<II", 2, 0x6A)
        owners = tuple(
            offset
            for offset in range(0, len(RAW) - len(owner_bytes) + 1, 4)
            if RAW[offset:offset + len(owner_bytes)] == owner_bytes
        )
        self.assertEqual(COMPANION_AFK_PANEL_PLACEMENT_OFFSETS, owners)

    def test_r46_afk_panel_validation_fails_closed_on_owner_drift(self) -> None:
        tampered = bytearray(RAW)
        tampered[COMPANION_AFK_PANEL_RESOURCE_TABLE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "AFK panel resource-table drifted"):
            patch_companion_afk_layout(bytes(tampered))

        for frame_index in range(COMPANION_AFK_PANEL_FRAME_COUNT):
            frame_offset = (
                COMPANION_AFK_PANEL_METADATA_OFFSET
                + frame_index * COMPANION_AFK_PANEL_FRAME_STRIDE
            )
            with self.subTest(frame=frame_index):
                tampered = bytearray(RAW)
                tampered[frame_offset + 4] ^= 1
                with self.assertRaisesRegex(ValueError, "AFK panel metadata drifted"):
                    patch_companion_afk_layout(bytes(tampered))

        for offset in COMPANION_AFK_PANEL_PLACEMENT_OFFSETS:
            with self.subTest(placement=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset + 8] ^= 1
                with self.assertRaisesRegex(ValueError, "AFK panel placement drifted"):
                    patch_companion_afk_layout(bytes(tampered))

    def test_r46_keeps_r45_visibility_hook_for_native_afk_states_11_through_13(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )

        visibility_jal = struct.unpack_from("<I", result, 0x666BC)[0]
        self.assertEqual(0x03, visibility_jal >> 26)
        visibility_va = (visibility_jal & 0x03FFFFFF) << 2
        self.assertGreaterEqual(visibility_va, p_vaddr)
        self.assertLess(visibility_va + COMPANION_ACTION_VISIBILITY_HOOK_SIZE, p_vaddr + p_filesz + 1)
        self.assertEqual(0x00000000, struct.unpack_from("<I", result, 0x666C0)[0])
        self.assertEqual(0x10400073, struct.unpack_from("<I", result, 0x666C4)[0])

        visibility_file = p_offset + visibility_va - p_vaddr
        words = struct.unpack_from(
            f"<{COMPANION_ACTION_VISIBILITY_HOOK_SIZE // 4}I",
            result,
            visibility_file,
        )
        self.assertEqual(
            (
                0x8E0202C8,  # original s0+0x2c8 L1 visibility guard
                0x1040000C, 0x00000000,
                0x86080004,  # current talk-record index
                0x2D090259,  # AFK/free-talk starts at record 601
                0x15200008, 0x00000000,
                0x86080002,  # native H_TalkBuddyTask state
                0x2508FFF5,  # normalize state 11 -> 0
                0x2D090003,  # states 11..13 only
                0x11200003, 0x00000000,
                0x00001021,  # v0=0 only during the AFK-visible lifecycle
                0x00000000,
                0x03E00008, 0x00000000,
                0x00000000, 0x00000000, 0x00000000,
            ),
            words,
        )

    def test_r47_afk_runtime_restores_native_outer_geometry_and_scales_every_record(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )

        # Shared 0x68/0x69 are pristine at rest; runtime consumers now own
        # their temporary geometry instead of fighting over global metadata.
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            tuple(
                struct.unpack_from("<f", result, offset)[0]
                for offset in (
                    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
                )
            ),
        )
        self.assertEqual(
            COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
            tuple(
                struct.unpack_from("<f", result, offset)[0]
                for offset in (
                    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
                )
            ),
        )

        geometry_jal = struct.unpack_from("<I", result, 0x66050)[0]
        self.assertEqual(0x03, geometry_jal >> 26)
        self.assertEqual(0x000219C0, struct.unpack_from("<I", result, 0x66054)[0])
        geometry_va = (geometry_jal & 0x03FFFFFF) << 2
        geometry_file = p_offset + geometry_va - p_vaddr
        geometry_words = struct.unpack_from(
            f"<{COMPANION_AFK_GEOMETRY_HOOK_SIZE // 4}I",
            result,
            geometry_file,
        )
        self.assertEqual(
            (
                0x86020004, 0x2C490259, 0x15200016, 0x00000000,
                0x860802F8, 0x2D090002, 0x11200012, 0x00000000,
                0x00084900, 0x00085140, 0x012A4821,
                0x3C0A0045, 0x254A0AC4, 0x01495021,
                0x3C094390, 0xAD490000,       # width 288
                0x3C0942A0, 0xAD490004,       # height 80
                0x3C09429A, 0xAD49000C,       # pivot-Y 77
                0x3C094286, 0x11000002, 0x00000000,
                0x3C0942FA, 0xAD490008,       # pivot-X 67 / 125
                0x000219C0, 0x03E00008, 0x00000000,
            ),
            geometry_words,
        )

        scale_jal_1 = struct.unpack_from("<I", result, 0x6625C)[0]
        scale_jal_2 = struct.unpack_from("<I", result, 0x6632C)[0]
        self.assertEqual(scale_jal_1, scale_jal_2)
        self.assertEqual(0x03, scale_jal_1 >> 26)
        self.assertEqual(0, struct.unpack_from("<I", result, 0x66260)[0])
        self.assertEqual(0, struct.unpack_from("<I", result, 0x66330)[0])
        # Original/non-Re:charge h_buddy text keeps f16=1.0.
        self.assertEqual(0x3C023F80, struct.unpack_from("<I", result, 0x6621C)[0])
        self.assertEqual(0x44828000, struct.unpack_from("<I", result, 0x66220)[0])
        self.assertEqual(0x3C023F80, struct.unpack_from("<I", result, 0x662EC)[0])
        self.assertEqual(0x44828000, struct.unpack_from("<I", result, 0x662F0)[0])

        scale_va = (scale_jal_1 & 0x03FFFFFF) << 2
        scale_file = p_offset + scale_va - p_vaddr
        scale_words = struct.unpack_from(
            f"<{COMPANION_AFK_SCALE_HOOK_SIZE // 4}I",
            result,
            scale_file,
        )
        self.assertEqual(
            (
                0x86080004, 0x2508FDA7, 0x2D090258, 0x11200008,
                0x00000000, 0x00084880,
            ),
            scale_words[:6],
        )
        self.assertEqual(
            (
                0x01495021, 0xC5500000, 0x03E00008, 0x00000000,
                0x3C083F80, 0x44888000, 0x03E00008, 0x00000000,
            ),
            scale_words[8:],
        )

        hi = scale_words[6] & 0xFFFF
        lo = scale_words[7] & 0xFFFF
        if lo & 0x8000:
            lo -= 0x10000
        scale_table_va = ((hi << 16) + lo) & 0xFFFFFFFF
        scale_table_file = p_offset + scale_table_va - p_vaddr
        self.assertGreaterEqual(scale_table_va, p_vaddr)
        self.assertLessEqual(
            scale_table_va + len(COMPANION_AFK_TEXT_SCALES) * 4,
            p_vaddr + p_filesz,
        )
        self.assertEqual(
            struct.pack(
                f"<{len(COMPANION_AFK_TEXT_SCALES)}f",
                *COMPANION_AFK_TEXT_SCALES,
            ),
            result[
                scale_table_file:
                scale_table_file + len(COMPANION_AFK_TEXT_SCALES) * 4
            ],
        )

        self.assertEqual(COMPANION_AFK_RECORD_COUNT, len(COMPANION_AFK_TEXT_SCALES))
        for record_index, (lines, scale) in enumerate(
            zip(COMPANION_AFK_TRANSLATIONS, COMPANION_AFK_TEXT_SCALES, strict=True)
        ):
            longest = max((len(line) for line in lines if line), default=0)
            expected = 1.0 if longest == 0 else min(
                1.0,
                COMPANION_AFK_TEXT_SAFE_CELLS / longest,
            )
            with self.subTest(record=record_index):
                self.assertAlmostEqual(expected, scale)
                for line in lines:
                    if line:
                        self.assertLessEqual(
                            len(line) * scale,
                            COMPANION_AFK_TEXT_SAFE_CELLS + 1e-6,
                        )

    def test_r38_runtime_selector_keeps_body_stable_and_points_tail_at_active_slot(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, p_flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )
        self.assertEqual(7, p_flags)

        # Keep the game's proven slot anchors.  r38 changes the bubble resource/
        # pivot, not the companion positions themselves.
        expected_slot_positions = tuple(
            component for position in COMPANION_SLOT_POSITIONS for component in position
        )
        self.assertEqual(
            expected_slot_positions,
            struct.unpack_from("<ffff", RAW, COMPANION_SLOT_POSITION_TABLE_OFFSET),
        )
        self.assertEqual(
            RAW[COMPANION_SLOT_POSITION_TABLE_OFFSET:COMPANION_SLOT_POSITION_TABLE_OFFSET + 16],
            result[COMPANION_SLOT_POSITION_TABLE_OFFSET:COMPANION_SLOT_POSITION_TABLE_OFFSET + 16],
        )
        for offset, expected in COMPANION_SLOT_INDEX_PREIMAGES:
            self.assertEqual(expected, struct.unpack_from("<I", result, offset)[0])

        jal = struct.unpack_from("<I", result, 0x66724)[0]
        self.assertEqual(0x03, jal >> 26)
        hook_va = (jal & 0x03FFFFFF) << 2
        self.assertGreaterEqual(hook_va, p_vaddr)
        self.assertLess(hook_va, p_vaddr + p_filesz)
        self.assertEqual(0x24040002, struct.unpack_from("<I", result, 0x66728)[0])

        hook_file = p_offset + hook_va - p_vaddr
        hook_words = struct.unpack_from(
            f"<{COMPANION_ACTION_RUNTIME_HOOK_SIZE // 4}I", result, hook_file
        )
        self.assertEqual(0x27BDFFF0, hook_words[0])
        self.assertEqual(0xAFBF000C, hook_words[1])
        self.assertEqual(0x34040000 | COMPANION_ACTION_ID_KEY, hook_words[2])
        self.assertEqual(
            0x0C000000 | ((COMPANION_ACTION_ID_GETTER_VA >> 2) & 0x03FFFFFF),
            hook_words[3],
        )
        self.assertEqual(0x3042FFFF, hook_words[5])
        self.assertEqual(0x38420000 | COMPANION_ACTION_ID_KEY, hook_words[6])
        self.assertEqual(0x2C43001F, hook_words[7])
        self.assertIn(0x860D02D0, hook_words)         # lh t5,0x2d0(s0): slot 0/1
        self.assertEqual(0x25A50068, hook_words[-6])  # a1 = slot + 0x68
        self.assertEqual(0x02, hook_words[-5] >> 26)  # tail-jump geometry extension
        self.assertEqual((0, 0, 0, 0), hook_words[-4:])

        extension_va = (hook_words[-5] & 0x03FFFFFF) << 2
        extension_file = p_offset + extension_va - p_vaddr
        extension_words = struct.unpack_from(
            f"<{COMPANION_ACTION_GEOMETRY_EXTENSION_SIZE // 4}I",
            result,
            extension_file,
        )
        self.assertEqual(
            (
                0x000D7100, 0x000D7940, 0x01CF7021,
                0x3C0F0045, 0x25EF0AC4, 0x01EE7821,
                0x3C0E4360, 0xADEE0000,       # width 224
                0x3C0E4250, 0x11A00002, 0x00000000,
                0x3C0E42C2, 0xADEE0008,       # pivot-X 52 / 97
                0x8FBF000C, 0x27BD0010, 0x24040002,
                0x03E00008, 0x00000000,
            ),
            extension_words,
        )

        # The two sibling resources share a body but move the tail 58px.  After
        # r38 scaling, body-left/text-left move only 13px right for slot 2.
        self.assertEqual((0x68, 0x69), COMPANION_ACTION_SLOT_RESOURCES)
        body_left = (
            COMPANION_SLOT_POSITIONS[0][0] - COMPANION_ACTION_BUBBLE_TARGET_GEOMETRY[2],
            COMPANION_SLOT_POSITIONS[1][0] - COMPANION_ACTION_SLOT2_BUBBLE_TARGET_GEOMETRY[2],
        )
        text_left = (
            COMPANION_SLOT_POSITIONS[0][0] + COMPANION_ACTION_SLOT_TEXT_X[0],
            COMPANION_SLOT_POSITIONS[1][0] + COMPANION_ACTION_SLOT_TEXT_X[1],
        )
        self.assertEqual(13.0, body_left[1] - body_left[0])
        self.assertEqual(13.0, text_left[1] - text_left[0])
        self.assertEqual(58.0, COMPANION_SLOT_POSITIONS[1][0] - COMPANION_SLOT_POSITIONS[0][0])

        # The original later action lookup remains byte-identical.
        for offset, expected in COMPANION_ACTION_ID_REFERENCE_PREIMAGES:
            self.assertEqual(expected, struct.unpack_from("<I", result, offset)[0])
        for offset, _expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            self.assertEqual(replacement, struct.unpack_from("<I", result, offset)[0])
        self.assertEqual(0x46000800, struct.unpack_from("<I", result, 0x66810)[0])
        self.assertEqual(0x46000800, struct.unpack_from("<I", result, 0x66828)[0])

    def test_r38_layout_patch_fails_closed_on_all_pristine_owners(self) -> None:
        for offset, _expected, _replacement in COMPANION_ACTION_LAYOUT_PATCHES:
            with self.subTest(static_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action layout preimage mismatch"):
                    patch_companion_action_layout(bytes(tampered))

        for offset, _expected in COMPANION_ACTION_RUNTIME_PREIMAGES:
            with self.subTest(runtime_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action runtime preimage mismatch"):
                    patch_companion_action_layout(bytes(tampered))

        for offset, _expected in COMPANION_ACTION_VISIBILITY_PREIMAGES:
            with self.subTest(visibility_offset=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion action visibility preimage mismatch"):
                    patch_companion_action_layout(bytes(tampered))

        tampered = bytearray(RAW)
        tampered[COMPANION_SLOT_POSITION_TABLE_OFFSET] ^= 1
        with self.assertRaisesRegex(ValueError, "companion slot position table drifted"):
            patch_companion_action_layout(bytes(tampered))

        for offset, _expected in (*COMPANION_SLOT_INDEX_PREIMAGES, *COMPANION_ACTION_ID_REFERENCE_PREIMAGES):
            with self.subTest(slot_or_action_owner=hex(offset)):
                tampered = bytearray(RAW)
                tampered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, "companion slot/action-id owner drifted"):
                    patch_companion_action_layout(bytes(tampered))

        bubble_specs = (
            (
                COMPANION_ACTION_BUBBLE_TABLE_RECORD_OFFSET,
                COMPANION_ACTION_BUBBLE_METADATA_VA,
                (
                    COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
                ),
                COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            ),
            (
                COMPANION_ACTION_SLOT2_BUBBLE_TABLE_RECORD_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_METADATA_VA,
                (
                    COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
                    COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
                ),
                COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
            ),
        )
        for record_offset, metadata_va, geometry_offsets, pristine_geometry in bubble_specs:
            self.assertEqual((metadata_va, 1), struct.unpack_from("<II", RAW, record_offset))
            self.assertEqual(
                pristine_geometry,
                tuple(struct.unpack_from("<f", RAW, offset)[0] for offset in geometry_offsets),
            )
            tampered = bytearray(RAW)
            tampered[record_offset] ^= 1
            with self.assertRaisesRegex(ValueError, "companion action bubble resource-table drifted"):
                patch_companion_action_layout(bytes(tampered))
            for offset in geometry_offsets:
                with self.subTest(metadata_offset=hex(offset)):
                    tampered = bytearray(RAW)
                    tampered[offset] ^= 1
                    with self.assertRaisesRegex(ValueError, "companion action bubble geometry drifted"):
                        patch_companion_action_layout(bytes(tampered))

    def test_r30_keeps_accepted_r29_dungeon_owners_frozen(self) -> None:
        result = build_early_ui_elf(RAW)
        for spec in DUNGEON_ACTION_LABELS:
            ref = spec.code_reference
            self.assertNotEqual(ref.expected_lui, struct.unpack_from("<I", result, ref.lui_offset)[0])
        for spec in DUNGEON_ITEM_NAMES:
            with self.subTest(item_id=spec.item_id):
                self.assertNotEqual(
                    _ELF_MAIN_VADDR + spec.source_offset - _ELF_MAIN_FILE_OFFSET,
                    struct.unpack_from("<I", result, spec.pointer_offset)[0],
                )


if __name__ == "__main__":
    unittest.main()
