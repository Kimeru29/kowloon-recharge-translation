from __future__ import annotations

import hashlib
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
    COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE,
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
    COMPANION_AFK_GREEN_PLACEMENT_OFFSETS,
    COMPANION_AFK_GREEN_PRISTINE_PLACEMENTS,
    COMPANION_AFK_GREEN_TARGET_PLACEMENTS,
    COMPANION_AFK_EMPTY_VA,
    COMPANION_AFK_EXPECTED_LIVE_FIELDS,
    COMPANION_AFK_MAX_CHARS,
    COMPANION_AFK_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_SCALE_HOOK_SIZE,
    COMPANION_AFK_TEXT_SAFE_CELLS,
    COMPANION_AFK_TEXT_SCALES,
    COMPANION_AFK_LAYOUTS,
    COMPANION_AFK_WRAP_CELLS,
    COMPANION_AFK_LINE_STEP,
    COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION,
    COMPANION_AFK_GREEN_BASE_HEIGHT,
    COMPANION_AFK_GREEN_BASE_PIVOT_Y,
    COMPANION_AFK_BLUE_BASE_HEIGHT,
    COMPANION_AFK_R55_MULTILINE_BLUE_BOTTOM_TRIM,
    COMPANION_AFK_R57_FOUR_ROW_EXTRA_BOTTOM_TRIM,
    COMPANION_AFK_R59_FOUR_ROW_BLUE_BOTTOM_TRIM,
    COMPANION_AFK_R59_FOUR_ROW_TEXT_TOP_PADDING,
    COMPANION_AFK_ANCHOR_Y,
    COMPANION_ACTION_R59_BLUE_RESOURCE_ID,
    COMPANION_ACTION_R59_BLUE_METADATA_VA,
    COMPANION_ACTION_R59_BLUE_FRAME_STRIDE,
    COMPANION_ACTION_R59_BLUE_PRISTINE,
    COMPANION_AFK_R56_SECOND_OBJECT_GAP_CORRECTION,
    COMPANION_AFK_BLUE_BASE_PIVOT_Y,
    COMPANION_AFK_TEXT1_BASE_Y,
    COMPANION_AFK_TEXT2_BASE_Y,
    COMPANION_AFK_WRAP_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_WRAP_TEXT_HOOK_SIZE,
    COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE,
    COMPANION_AFK_R52_PRETEXT_HOOK_SIZE,
    COMPANION_ACTION_R60_PRECONSTRUCT_SIZE,
    COMPANION_ACTION_R60_NATIVE_CONSTRUCTOR_RETURN_VA,
    _action_r60_preconstruct_bytes,
    _action_r62_inset_layout_table_bytes,
    COMPANION_ACTION_R62_INSET_X,
    COMPANION_ACTION_R62_INSET_TOP,
    COMPANION_ACTION_R62_INSET_BOTTOM,
    COMPANION_ACTION_R62_INSET_WIDTH,
    COMPANION_ACTION_R61_LIVE_OFFSET_SIZE,
    COMPANION_ACTION_R61_BLUE_SHIFT_X,
    COMPANION_ACTION_R61_BLUE_SHIFT_Y,
    _action_r61_live_blue_xy_bytes,
    COMPANION_ACTION_R58_POSITION_SIZE,
    COMPANION_AFK_R58_RESTORE_SIZE,
    COMPANION_ACTION_R58_PLACEMENT_X_VA,
    _action_r58_blue_placement_bytes,
    _afk_r58_restore_placement_bytes,
    COMPANION_AFK_RECORD_COUNT,
    COMPANION_AFK_RECORD_STRIDE,
    COMPANION_AFK_TABLE_OFFSET,
    COMPANION_SLOT_INDEX_PREIMAGES,
    COMPANION_SLOT_POSITIONS,
    COMPANION_SLOT_POSITION_TABLE_OFFSET,
    COMPANION_COMMENT_LINES,
    encode_companion_action,
    encode_companion_afk_text,
    patch_companion_action_layout,
    patch_companion_afk_layout,
    relocated_companion_entries,
    validate_companion_afk_source,
    validate_companion_hud_source,
    wrap_companion_action_text,
    wrap_companion_afk_text,
)
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES
from tools.early_ui import build_early_ui_elf
from tools.startup_acceptance import verify_startup_elf
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
            encode_companion_afk_text("Hm? Lost your way?"),
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

    def test_r50_afk_panel_keeps_metadata_pristine_but_moves_composition_up(self) -> None:
        result = patch_companion_afk_layout(RAW)

        # r50 still never bakes resized 0x6A metadata into the static ELF.
        # Only the four structured AFK placement records move to the accepted
        # L1 vertical band; slot-1 blue also follows its companion X anchor.
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

        for offsets, expected_targets in (
            (COMPANION_AFK_GREEN_PLACEMENT_OFFSETS, COMPANION_AFK_GREEN_TARGET_PLACEMENTS),
            (COMPANION_AFK_PANEL_PLACEMENT_OFFSETS, COMPANION_AFK_PANEL_TARGET_PLACEMENTS),
        ):
            for offset, expected in zip(offsets, expected_targets, strict=True):
                self.assertEqual(expected, struct.unpack_from("<IIfff", result, offset))

        # Every byte outside the explicitly owned placement dwords stays pristine.
        expected_changed = set()
        for offset, pristine, target in (
            *zip(
                COMPANION_AFK_GREEN_PLACEMENT_OFFSETS,
                COMPANION_AFK_GREEN_PRISTINE_PLACEMENTS,
                COMPANION_AFK_GREEN_TARGET_PLACEMENTS,
                strict=True,
            ),
            *zip(
                COMPANION_AFK_PANEL_PLACEMENT_OFFSETS,
                COMPANION_AFK_PANEL_PRISTINE_PLACEMENTS,
                COMPANION_AFK_PANEL_TARGET_PLACEMENTS,
                strict=True,
            ),
        ):
            before = struct.pack("<IIfff", *pristine)
            after = struct.pack("<IIfff", *target)
            expected_changed.update(
                offset + i for i, (a, b) in enumerate(zip(before, after, strict=True)) if a != b
            )
        actual_changed = {
            i for i, (a, b) in enumerate(zip(RAW, result, strict=True)) if a != b
        }
        self.assertEqual(expected_changed, actual_changed)

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

        for owner, offsets in (
            ("green", COMPANION_AFK_GREEN_PLACEMENT_OFFSETS),
            ("blue", COMPANION_AFK_PANEL_PLACEMENT_OFFSETS),
        ):
            for offset in offsets:
                with self.subTest(owner=owner, placement=hex(offset)):
                    tampered = bytearray(RAW)
                    tampered[offset + 8] ^= 1
                    with self.assertRaisesRegex(ValueError, rf"AFK {owner} placement drifted"):
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

    def test_r50_afk_wrap_is_generic_anchored_and_grows_upward(self) -> None:
        result = build_early_ui_elf(RAW)
        _ptype, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
            "<IIIIIIII", result, 0x54
        )

        # Static metadata remains pristine; all AFK resizing is runtime-only.
        self.assertEqual(
            COMPANION_ACTION_BUBBLE_PRISTINE_GEOMETRY,
            tuple(struct.unpack_from("<f", result, offset)[0] for offset in (
                COMPANION_ACTION_BUBBLE_WIDTH_OFFSET,
                COMPANION_ACTION_BUBBLE_HEIGHT_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_X_OFFSET,
                COMPANION_ACTION_BUBBLE_PIVOT_Y_OFFSET,
            )),
        )
        self.assertEqual(
            COMPANION_ACTION_SLOT2_BUBBLE_PRISTINE_GEOMETRY,
            tuple(struct.unpack_from("<f", result, offset)[0] for offset in (
                COMPANION_ACTION_SLOT2_BUBBLE_WIDTH_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_HEIGHT_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_X_OFFSET,
                COMPANION_ACTION_SLOT2_BUBBLE_PIVOT_Y_OFFSET,
            )),
        )
        for frame_index, expected in enumerate(COMPANION_AFK_PANEL_PRISTINE_GEOMETRIES):
            frame_offset = COMPANION_AFK_PANEL_METADATA_OFFSET + frame_index * COMPANION_AFK_PANEL_FRAME_STRIDE
            self.assertEqual(expected, struct.unpack_from("<ffff", result, frame_offset + 4))

        # Runtime proved f16 is alpha. Every constructor path keeps it at 1.0.
        for lui_offset, mtc1_offset in (
            (0x6621C, 0x66220),
            (0x6625C, 0x66260),
            (0x662EC, 0x662F0),
            (0x6632C, 0x66330),
        ):
            self.assertEqual(0x3C023F80, struct.unpack_from("<I", result, lui_offset)[0])
            self.assertEqual(0x44828000, struct.unpack_from("<I", result, mtc1_offset)[0])

        # r50 geometry is selected per AFK record and companion slot before
        # construction. Green and all three blue frames receive the same height
        # growth; blue pivot-X follows slot 0/1 instead of remaining slot-0-only.
        geometry_jal = struct.unpack_from("<I", result, 0x66050)[0]
        self.assertEqual(0x03, geometry_jal >> 26)
        self.assertEqual(0x000219C0, struct.unpack_from("<I", result, 0x66054)[0])
        geometry_va = (geometry_jal & 0x03FFFFFF) << 2
        geometry_file = p_offset + geometry_va - p_vaddr
        geometry_words = struct.unpack_from(
            f"<{COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE // 4}I", result, geometry_file
        )
        self.assertEqual(COMPANION_AFK_R50_GEOMETRY_HOOK_SIZE // 4, len(geometry_words))
        self.assertEqual((0x86020004, 0x2448FDA7, 0x2D090258, 0x1120002D), geometry_words[:4])
        self.assertEqual((0x860A02F8, 0x2D490002, 0x11200029), geometry_words[5:8])
        self.assertEqual(0x00085940, geometry_words[9])  # record * 32
        self.assertEqual(0x3C0C0000, geometry_words[10] & 0xFFFF0000)
        self.assertEqual(0x258C0000, geometry_words[11] & 0xFFFF0000)
        self.assertEqual(0x3C0F4390, geometry_words[19])  # green width 288
        self.assertEqual(0x3C0F4286, geometry_words[25])  # slot0 pivot X 67
        self.assertEqual(0x3C0F42FA, geometry_words[28])  # slot1 pivot X 125
        self.assertEqual(0x25CE0B24, geometry_words[31])  # blue frame0 width field
        self.assertEqual(0x3C0D438D, geometry_words[32])  # blue 282, 3px green inset
        self.assertEqual((0xADCF0008, 0xADCF0038, 0xADCF0068), geometry_words[40:43])
        self.assertEqual((0x86020004, 0x000219C0, geometry_words[-2], 0), geometry_words[-4:])

        hi = geometry_words[10] & 0xFFFF
        lo = geometry_words[11] & 0xFFFF
        if lo & 0x8000:
            lo -= 0x10000
        layout_table_va = ((hi << 16) + lo) & 0xFFFFFFFF
        layout_table_file = p_offset + layout_table_va - p_vaddr
        expected_layout_table = b"".join(
            struct.pack(
                "<8f",
                layout.green_height,
                layout.green_pivot_y,
                layout.blue_height,
                *layout.blue_pivot_y,
                layout.text1_y,
                layout.text2_y,
            )
            for layout in COMPANION_AFK_LAYOUTS
        )
        self.assertEqual(600 * 32, len(expected_layout_table))
        self.assertEqual(
            expected_layout_table,
            result[layout_table_file:layout_table_file + len(expected_layout_table)],
        )

        # Both text constructors share one post-construction hook. It keeps X
        # scale at 1.0 and changes only object +0x18 (Y position).
        text_jal_1 = struct.unpack_from("<I", result, 0x66284)[0]
        text_jal_2 = struct.unpack_from("<I", result, 0x66354)[0]
        self.assertEqual(text_jal_1, text_jal_2)
        self.assertEqual(0x03, text_jal_1 >> 26)
        self.assertEqual(0xAE020028, struct.unpack_from("<I", result, 0x66288)[0])
        self.assertEqual(0xAE02002C, struct.unpack_from("<I", result, 0x66358)[0])
        text_va = (text_jal_1 & 0x03FFFFFF) << 2
        text_file = p_offset + text_va - p_vaddr
        text_words = struct.unpack_from(
            f"<{COMPANION_AFK_WRAP_TEXT_HOOK_SIZE // 4}I", result, text_file
        )
        self.assertEqual((0x00405821, 0x3C0F3F80, 0xAD6F0048), text_words[:3])
        self.assertEqual(0x00084140, text_words[10])  # record * 32
        self.assertEqual(0x3C090000, text_words[11] & 0xFFFF0000)
        self.assertEqual(0x25290000, text_words[12] & 0xFFFF0000)
        self.assertEqual(0x8D2A0018, text_words[16])  # line1 Y
        self.assertEqual(0x8D2A001C, text_words[19])  # line2 Y
        self.assertEqual(0xAD6A0018, text_words[20])  # object +0x18
        self.assertEqual(layout_table_va, (
            ((text_words[11] & 0xFFFF) << 16)
            + ((text_words[12] & 0xFFFF) - (0x10000 if text_words[12] & 0x8000 else 0))
        ) & 0xFFFFFFFF)

        # Complete-corpus invariant: every visual row is <=16 cells. Bubble width
        # never changes; only height/pivot-Y grow, so both layers extend upward
        # while their bottom/tail relationships remain fixed for either slot.
        self.assertEqual(COMPANION_AFK_RECORD_COUNT, len(COMPANION_AFK_LAYOUTS))
        for record_index, (source_lines, layout) in enumerate(
            zip(COMPANION_AFK_TRANSLATIONS, COMPANION_AFK_LAYOUTS, strict=True)
        ):
            rows = (*layout.line1_rows, *layout.line2_rows)
            total_rows = len(rows)
            delta = COMPANION_AFK_LINE_STEP * max(0, total_rows - 2)
            with self.subTest(record=record_index):
                self.assertTrue(rows)
                self.assertTrue(all(1 <= len(row) <= COMPANION_AFK_WRAP_CELLS for row in rows))
                self.assertEqual(COMPANION_AFK_GREEN_BASE_HEIGHT + delta, layout.green_height)
                self.assertEqual(COMPANION_AFK_GREEN_BASE_PIVOT_Y + delta, layout.green_pivot_y)
                trim = (
                    (COMPANION_AFK_R55_MULTILINE_BLUE_BOTTOM_TRIM if total_rows > 2 else 0.0)
                    + (COMPANION_AFK_R57_FOUR_ROW_EXTRA_BOTTOM_TRIM if total_rows >= 4 else 0.0)
                    + (COMPANION_AFK_R59_FOUR_ROW_BLUE_BOTTOM_TRIM if total_rows >= 4 else 0.0)
                )
                self.assertEqual(COMPANION_AFK_BLUE_BASE_HEIGHT + delta - trim, layout.blue_height)
                self.assertEqual(3.0, layout.green_height - layout.green_pivot_y)
                green_top_y = COMPANION_AFK_ANCHOR_Y - layout.green_pivot_y
                native_inset = COMPANION_AFK_TEXT1_BASE_Y - (
                    COMPANION_AFK_ANCHOR_Y - COMPANION_AFK_GREEN_BASE_PIVOT_Y
                )
                extra_inset = COMPANION_AFK_R59_FOUR_ROW_TEXT_TOP_PADDING if total_rows >= 4 else 0.0
                self.assertEqual(green_top_y + native_inset + extra_inset, layout.text1_y)
                # The text remains attached to the GREEN frame, regardless of
                # the independent blue height or AFK-specific placement.
                self.assertEqual(native_inset + extra_inset, layout.text1_y - green_top_y)
                if layout.line2_rows:
                    last_row_y = layout.text2_y + COMPANION_AFK_LINE_STEP * (len(layout.line2_rows) - 1)
                else:
                    last_row_y = layout.text1_y + COMPANION_AFK_LINE_STEP * (len(layout.line1_rows) - 1)
                self.assertLessEqual(last_row_y, COMPANION_AFK_TEXT2_BASE_Y + extra_inset)
                if total_rows >= 2:
                    # The r53 32px *bubble* budget is deliberately retained,
                    # but the second text object's internal glyph rows should
                    # not receive the same 32px spacing twice.
                    self.assertEqual(
                        COMPANION_AFK_TEXT2_BASE_Y + extra_inset
                        - COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION
                        * max(0, len(layout.line2_rows) - 1)
                        - COMPANION_AFK_R56_SECOND_OBJECT_GAP_CORRECTION
                        * max(0, len(layout.line1_rows) - 1)
                        * int(bool(layout.line2_rows)),
                        last_row_y,
                    )
                self.assertEqual(
                    layout.text1_y
                    + COMPANION_AFK_LINE_STEP * len(layout.line1_rows)
                    - COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION
                    * max(0, len(layout.line2_rows) - 1)
                    - COMPANION_AFK_R56_SECOND_OBJECT_GAP_CORRECTION
                    * max(0, len(layout.line1_rows) - 1)
                    * int(bool(layout.line2_rows)),
                    layout.text2_y,
                )
                for base, pivot in zip(COMPANION_AFK_BLUE_BASE_PIVOT_Y, layout.blue_pivot_y, strict=True):
                    self.assertEqual(base + delta, pivot)
                    self.assertEqual(COMPANION_AFK_BLUE_BASE_HEIGHT - base - trim, layout.blue_height - pivot)

                for source in source_lines:
                    if not source:
                        continue
                    encoded = encode_companion_afk_text(source)
                    expected_rows = wrap_companion_afk_text(source)
                    self.assertEqual(max(0, len(expected_rows) - 1), encoded.split(b"\x00", 1)[0].count(b"\x0a"))
                    # Current corpus preserves r48 allocation size exactly.
                    self.assertEqual(
                        len(encode_ps2_english(source, collapse_spaces=False)) + 1,
                        len(encoded),
                    )

        # r53 screenshot: "Ruins and people / both / grow richer with / age."
        # previously painted "age." below the green bottom border.
        long_afk = COMPANION_AFK_LAYOUTS[487]
        self.assertEqual(("Ruins and people", "both"), long_afk.line1_rows)
        self.assertEqual(("grow richer with", "age."), long_afk.line2_rows)
        self.assertEqual(220.0, long_afk.text1_y)
        self.assertEqual(257.0, long_afk.text2_y)
        self.assertEqual(144.0, long_afk.green_height)
        self.assertEqual(105.0, long_afk.blue_height)
        self.assertEqual(275.0, long_afk.text2_y + COMPANION_AFK_R54_SECOND_OBJECT_ROW_CORRECTION)
        short_afk = COMPANION_AFK_LAYOUTS[480]
        self.assertEqual(("Come now, this", "way."), short_afk.line1_rows)
        self.assertEqual(56.0, short_afk.blue_height)
        self.assertEqual(278.0, short_afk.text1_y)
        self.assertFalse(short_afk.line2_rows)

        # The generic wrapper has no corpus-specific ceiling and hard-splits an
        # overlong token while still enforcing the same horizontal bound.
        self.assertEqual(("X" * 16, "X" * 16, "X" * 8), wrap_companion_afk_text("X" * 40))
        self.assertEqual(2, encode_companion_afk_text("X" * 40).count(b"\x0a"))


    def test_r63_blue_keeps_green_left_top_with_right_bottom_trim(self) -> None:
        # Constructor geometry, not a postconstruct XY write, defines bounds.
        blue_bytes=_action_r62_inset_layout_table_bytes()
        self.assertEqual(len(COMPANION_ACTION_LAYOUTS)*12,len(blue_bytes))
        for action_id,green in enumerate(COMPANION_ACTION_LAYOUTS):
            blue_height,blue_pivot_y,_=struct.unpack_from("<fff",blue_bytes,12*action_id)
            with self.subTest(action=action_id):
                self.assertEqual(green.height-2.0,blue_height)
                self.assertEqual(green.pivot_y,blue_pivot_y)
                for slot,green_pivot_x in ((0,52.0),(1,97.0)):
                    blue_pivot_x=green_pivot_x
                    green_left=-green_pivot_x
                    blue_left=-blue_pivot_x
                    green_top=-green.pivot_y
                    blue_top=-blue_pivot_y
                    # User's r62 image shows too much left padding; do not
                    # move the blue left or top relative to r60 green.
                    self.assertEqual(0.0,blue_left-green_left)
                    self.assertEqual(0.0,blue_top-green_top)
                    self.assertEqual(2.0,(green_left+224.0)-(blue_left+222.0))
                    self.assertEqual(2.0,(green_top+green.height)-(blue_top+blue_height))

    def test_r62_l1_blue_preconstructor_retains_metadata_until_native_draw(self) -> None:
        elf=build_early_ui_elf(RAW)
        _,off,va,_,_,_,_,_=struct.unpack_from("<8I",elf,0x54)
        selector_jal=struct.unpack_from("<I",elf,0x66724)[0]
        action=off+((selector_jal&0x03FFFFFF)<<2)-va
        action_words=struct.unpack_from("<47I",elf,action)
        targets=[w for w in action_words if w>>26==2]
        self.assertEqual(1,len(targets))
        ext=off+((targets[0]&0x03FFFFFF)<<2)-va
        ext_words=struct.unpack_from("<34I",elf,ext)
        self.assertEqual((0,)*12,ext_words[16:28])
        self.assertEqual(2,ext_words[-3]>>26)
        place=off+((ext_words[-3]&0x03FFFFFF)<<2)-va
        self.assertEqual(0x03E00008,struct.unpack_from("<I",elf,place+13*4)[0])
        for index in (16,17,18,19,20,21,22,23,24,25,26,27):
            with self.subTest(no_late_blue_store=index):
                tampered=bytearray(elf)
                tampered[ext+4*index]^=1
                check=next(x for x in verify_startup_elf(bytes(tampered))
                           if x["name"]=="companion_hud_layout")
                self.assertFalse(check["ok"])

    def test_r60_l1_preconstructs_blue_geometry_before_native_0x78(self) -> None:
        elf = build_early_ui_elf(RAW)
        _, segment_offset, segment_va, _, size, _, _, _ = struct.unpack_from("<8I", elf, 0x54)
        def follow(site: int) -> int:
            jal = struct.unpack_from("<I", elf, site)[0]
            self.assertEqual(3, jal >> 26)
            return segment_offset + (((jal & 0x03FFFFFF) << 2) - segment_va)
        scan_file = follow(0x66740)
        scanner = struct.unpack_from("<39I", elf, scan_file)
        self.assertEqual(2, scanner[36] >> 26)  # tail J (not early JR)
        self.assertEqual(0, scanner[37])
        pre_va = (scanner[36] & 0x03FFFFFF) << 2
        pre_file = segment_offset + pre_va - segment_va
        selector = follow(0x66724)
        sel = struct.unpack_from("<47I", elf, selector)
        hi, lo = sel[14] & 0xFFFF, sel[15] & 0xFFFF
        layout_va = (hi << 16) + lo - (0x10000 if lo & 0x8000 else 0)
        words = struct.unpack_from("<55I", elf, pre_file)
        blue_table_va = ((words[18]&0xFFFF)<<16) + (
            (words[19]&0xFFFF) - (0x10000 if words[19]&0x8000 else 0)
        )
        self.assertNotEqual(layout_va,blue_table_va)
        blue_table_off=segment_offset+blue_table_va-segment_va
        expected_blue_table=_action_r62_inset_layout_table_bytes()
        self.assertEqual(
            expected_blue_table,
            elf[blue_table_off:blue_table_off+len(expected_blue_table)],
        )
        self.assertEqual(
            _action_r60_preconstruct_bytes(table_va=blue_table_va),
            elf[pre_file:pre_file + COMPANION_ACTION_R60_PRECONSTRUCT_SIZE],
        )
        self.assertEqual(0x001666C8, COMPANION_ACTION_R60_NATIVE_CONSTRUCTOR_RETURN_VA)
        self.assertEqual((0x3C180016, 0x371866C8), words[:2])  # RA guard
        self.assertEqual(0x17F80032, words[2])  # bne ra,t8 -> fast-return
        self.assertEqual(0x0C04BFB8, words[7]) # getter at 0x12FEE0
        self.assertEqual(0x25EF13F4, words[29]) # native 0x78 metadata
        self.assertEqual(0xADEA0004, words[34]) # height from layout
        self.assertEqual(0xADEB000C, words[44]) # pivot Y from layout
        self.assertEqual(0x3C024371, words[49]) # displaced ctor v0
        self.assertEqual(0x44826000, words[50]) # displaced f12
        self.assertEqual((0x03E00008,0),words[53:55]) # alpha fast return
        # Any r60 preconstructor instruction changed -> fail final-image check.
        for index in (0,2,7,19,29,33,37,44,49,53):
            with self.subTest(preconstructor_word=index):
                changed=bytearray(elf)
                changed[pre_file+4*index]^=1
                result=next(c for c in verify_startup_elf(bytes(changed))
                            if c["name"]=="companion_hud_layout")
                self.assertFalse(result["ok"])

    def test_r60_freezes_user_accepted_r59_afk_layout_and_runtime_bytes(self) -> None:
        """Fail closed on AFK regression now that user visually accepted r59."""
        elf=build_early_ui_elf(RAW)
        _, off, va, _, _, _, _, _=struct.unpack_from("<8I",elf,0x54)
        def resolved(site: int) -> int:
            word=struct.unpack_from("<I",elf,site)[0]
            self.assertEqual(3,word>>26)
            return off+(((word&0x03FFFFFF)<<2)-va)
        geometry=resolved(0x66050)
        geo=struct.unpack_from("<53I",elf,geometry)
        hi,lo=geo[10]&0xFFFF,geo[11]&0xFFFF
        layout_va=(hi<<16)+lo-(0x10000 if lo&0x8000 else 0)
        layout=off+layout_va-va
        self.assertEqual(2,geo[51]>>26)
        restore=off+(((geo[51]&0x03FFFFFF)<<2)-va)
        # Literal, independent GOLDEN SHA256 snapshots from user-accepted
        # r59 ISO, not values dynamically generated by the code under test.
        golden={
            "afk_layout_600":(layout,600*32,"26fbc80e8ca834f731227a993b85b71e1d2bf4735588589974714519ebbf1321"),
            "afk_geometry":(geometry,212,"a2eae62bb06880977f469ff4e57a27107b65f5fbfb24fbf0e7c07ea93bf2bf5d"),
            "afk_pretext":(resolved(0x66250),84,"66b4cfb68eee9c2c9e7db3094fbf2878218fd9b59754fcf53b3604afb62899d2"),
            "afk_text":(resolved(0x66284),112,"82ab3f62fc7cb29b87fa94d51a89bc06d4f0c0f8b8442c89e4a7022bcca5d426"),
            "afk_restore":(restore,112,"8ac70718a8bb3c8ada8f3a9cd6c00ad0c7f17f45ad9f8d8ea52add6abf883b2a"),
            "afk_native_records_pointers":(COMPANION_AFK_TABLE_OFFSET,COMPANION_AFK_RECORD_COUNT*COMPANION_AFK_RECORD_STRIDE,
                "b662c1b000c2be0639534196c18f1a542f1f35edc437129f656357f176dcdbec"),
            "afk_blue_native_frames":(0x350BA0,144,"0ace1c8ee6346e27f539a6a55c801e2c19efdb06fc8ec07a4420548b8a73030d"),
            "afk_green_native_frames":(0x350B40,96,"bb9f329fefa170c7052d7396e00de21f58e1e2c6f76c870d2973f4bba07c34bb"),
            "afk_placements":(0x3F8E1C,80,"cfe30e2770427ff3ac5192a7b8bac77bfe9b392e332622f2635fd4b58c017a6a"),
        }
        for name,(start,length,digest) in golden.items():
            with self.subTest(afk_owner=name):
                self.assertEqual(digest,hashlib.sha256(elf[start:start+length]).hexdigest())
        for index,text_baseline,blue_height in [(480,278.,56.),(485,246.,82.),(487,220.,105.)]:
            with self.subTest(afk_record=index):
                layout_record=COMPANION_AFK_LAYOUTS[index]
                self.assertEqual((text_baseline,blue_height),
                                 (layout_record.text1_y,layout_record.blue_height))

    def test_r59_action_uses_actual_native_0x78_blue_resource(self) -> None:
        # Original H_TalkBuddyTask actually constructs resource 0x78 at
        # VA0x1666D8, task+0x2E0, sharing the 0x178(sp) XY of the green bubble.
        # r53-r58 exclusively targeted 0x6A (AFK) and left this frame metadata
        # unchanged, explaining the unchanged displaced lower L1 panel.
        resource_record = 0x380AF0 + 8 * COMPANION_ACTION_R59_BLUE_RESOURCE_ID
        va, count = struct.unpack_from('<II', RAW, resource_record)
        self.assertEqual((COMPANION_ACTION_R59_BLUE_METADATA_VA, 3), (va,count))
        native_off = va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET
        self.assertEqual(COMPANION_ACTION_R59_BLUE_PRISTINE,
                         struct.unpack_from('<4f', RAW, native_off + 4))
        for frame in range(3):
            self.assertEqual(152.0, struct.unpack_from('<f', RAW, native_off + 4 + frame * COMPANION_ACTION_R59_BLUE_FRAME_STRIDE)[0])
        # Group2/0x78 is created at the same coordinates as the green sprite.
        result = build_early_ui_elf(RAW)
        _type, p_offset, p_va, _paddr, _size, _mem, _flags, _align = struct.unpack_from('<8I', result, 0x54)
        action_hook = struct.unpack_from('<I', result, 0x66724)[0]
        hook_va = (action_hook & 0x03FFFFFF) << 2
        hook_words = struct.unpack_from('<47I', result, p_offset + hook_va - p_va)
        ext_va = (hook_words[-5] & 0x03FFFFFF) << 2
        ext_off = p_offset + ext_va - p_va
        ext_words = struct.unpack_from('<34I', result, ext_off)
        self.assertEqual(0x25EF13F4, ext_words[14])
        self.assertNotIn(0x25EF0B24, ext_words)
        self.assertEqual((0,)*12, ext_words[16:28])  # retire late blue writes
        tampered = bytearray(result)
        tampered[ext_off+14*4] ^= 1
        check = next(c for c in verify_startup_elf(bytes(tampered)) if c['name']=='companion_hud_layout')
        self.assertFalse(check['ok'])

    def test_r58_native_blue_compositor_placement_and_afk_restore(self) -> None:
        # Native global 0x6A X/Y placement records are written from the L1
        # live green object and restored at AFK construction, unlike the
        # r53-r57 ineffective task-local/pool sprite XY-only attempts.
        elf = build_early_ui_elf(RAW)
        _, p_offset, p_va, _, _, _, _, _ = struct.unpack_from("<8I", elf, 0x54)
        def rel_jal(site: int) -> int:
            instruction = struct.unpack_from("<I", elf, site)[0]
            self.assertEqual(3, instruction >> 26)
            return p_offset + (((instruction & 0x03FFFFFF) << 2) - p_va)
        afk_geo_off = rel_jal(0x66050)
        afk_tail = struct.unpack_from("<I", elf, afk_geo_off + 204)[0]
        self.assertEqual(2, afk_tail >> 26)
        afk_restore = p_offset + (((afk_tail & 0x03FFFFFF) << 2) - p_va)
        self.assertEqual(_afk_r58_restore_placement_bytes(),
                         elf[afk_restore:afk_restore + COMPANION_AFK_R58_RESTORE_SIZE])
        action_off = rel_jal(0x66724)
        action_words = struct.unpack_from("<47I", elf, action_off)
        pointers = [(w & 0x03FFFFFF) << 2 for w in action_words if w >> 26 == 2]
        self.assertEqual(1, len(pointers))
        ext = p_offset + pointers[0] - p_va
        ext_words = struct.unpack_from("<34I", elf, ext)
        self.assertEqual(0x24040002, ext_words[-4])
        self.assertEqual(2, ext_words[-3] >> 26)
        placement = p_offset + ((ext_words[-3] & 0x03FFFFFF) << 2) - p_va
        tail = struct.unpack_from("<I", elf, placement + 13*4)[0]
        self.assertEqual(0x03E00008, tail)
        self.assertEqual(
            _action_r58_blue_placement_bytes(tail_va=0),
            elf[placement:placement + COMPANION_ACTION_R58_POSITION_SIZE],
        )
        # Exact data consumer is ELF file 0x3F8E50 (VA 0x4F8DD0),
        # consecutive slot records have 20-byte stride.
        self.assertEqual(0x004F8DD0, COMPANION_ACTION_R58_PLACEMENT_X_VA)
        action = struct.unpack_from("<16I", elf, placement)
        self.assertEqual(0x8E0C02D8, action[0])
        self.assertEqual(0x8D8E003C, action[9])
        self.assertEqual(0xADEE0000, action[10])
        self.assertEqual(0x8D8E0040, action[11])
        self.assertEqual(0xADEE0004, action[12])
        restore = struct.unpack_from("<28I", elf, afk_restore)
        self.assertEqual(0x860D02F8, restore[6]) # selected AFK slot
        self.assertEqual(0x2DAE0002, restore[7]) # sltiu slot,2
        self.assertEqual(0x15C00002, restore[8]) # branch on valid slot
        self.assertEqual(0x8DEF0000, restore[17]) # live green height
        self.assertEqual(0x43AC, restore[20] & 0xFFFF) # 344 for >=4 rows
        self.assertEqual(0x43AD, restore[23] & 0xFFFF) # 346 for <=3 rows
        # Fail closed on any change to either compositor owner.
        for off in (placement + 9*4, placement + 12*4,
                    afk_restore + 20*4, afk_restore + 23*4,
                    ext + 31*4, afk_geo_off + 51*4):
            with self.subTest(offset=hex(off)):
                changed = bytearray(elf)
                changed[off] ^= 1
                check = next(x for x in verify_startup_elf(bytes(changed))
                             if x["name"] == "companion_hud_layout")
                self.assertFalse(check["ok"])

    def test_r53_preserves_afk_native_text_args_and_l1_sprite_fades(self) -> None:
        result = build_early_ui_elf(RAW)
        _, p_offset, p_vaddr, _, p_filesz, _, _, _ = struct.unpack_from("<IIIIIIII", result, 0x54)
        first = struct.unpack_from("<I", result, 0x66250)[0]
        second = struct.unpack_from("<I", result, 0x66320)[0]
        self.assertEqual(first, second)
        self.assertEqual(3, first >> 26)
        helper_va = (first & 0x03FFFFFF) << 2
        helper_file = p_offset + helper_va - p_vaddr
        words = struct.unpack_from("<21I", result, helper_file)
        self.assertEqual(0xE7AD01A4, words[18])
        # r51/r52 destroyed t1, passed by 0x1950A0 as live text input.
        self.assertEqual((12, 12), ((words[1] >> 16) & 31, (words[2] >> 16) & 31))
        self.assertEqual(13, (words[3] >> 16) & 31)
        for word in words:
            opcode, rt, rd = word >> 26, (word >> 16) & 31, (word >> 11) & 31
            if opcode in (0x09, 0x0D, 0x0F, 0x21, 0x23):
                self.assertNotIn(rt, (8, 9, 10, 11))
            if opcode == 0 and (word & 0x3F) in (0x00, 0x21):
                self.assertNotIn(rd, (8, 9, 10, 11))
        # r56 uses the actual native EE sprite pool instead of a task-local
        # +0x5C pointer (which is not the visible L1 lower-panel owner).
        new_jal = struct.unpack_from("<I", result, 0x66740)[0]
        new_va = (new_jal & 0x03FFFFFF) << 2
        create_offset = p_offset + new_va - p_vaddr
        create_words = struct.unpack_from("<39I", result, create_offset)
        self.assertNotIn(0x0C041F58, create_words)   # no jal native constructor
        self.assertEqual(0x8E0C02D8, create_words[0])  # green live instance
        self.assertEqual(0x3C0D007A, create_words[6])  # EE pool hi
        self.assertEqual(0x25AD5060, create_words[7])  # EE pool low
        self.assertEqual(0x240E0200, create_words[8])  # 512 slots
        self.assertEqual(0x91AF0093, create_words[9]) # active flag
        self.assertEqual(0x95AF0082, create_words[12])# group
        self.assertEqual(0x95AF0084, create_words[16])# resource
        self.assertEqual(0x8D8F003C, create_words[20])# green X
        self.assertEqual(0xADAF003C, create_words[21])# native blue X
        self.assertEqual(0x8D8F0040, create_words[22])# green Y
        self.assertEqual(0xADAF0040, create_words[23])# native blue Y
        self.assertEqual(0xADAF0068, create_words[26])# native blue Z
        self.assertEqual(0xAF0D0000, create_words[27])# cache located blue
        self.assertEqual(0x3C024371, create_words[34])# preserve f12
        self.assertEqual(0x44826000, create_words[35])
        self.assertEqual(0, create_words[38]) # relocated RWX cache
        cached_va = new_va + 152
        self.assertEqual(
            cached_va,
            ((create_words[1] & 0xFFFF) << 16)
            + (create_words[2] & 0xFFFF)
            - (0x10000 if create_words[2] & 0x8000 else 0),
        )
        for alpha_site in (0x65A88, 0x65B40, 0x65C5C):
            jal = struct.unpack_from("<I", result, alpha_site)[0]
            va = (jal & 0x03FFFFFF) << 2
            words = struct.unpack_from("<20I", result, p_offset + va - p_vaddr)
            self.assertEqual(0x27BDFFE0, words[1])  # aligned -32 stack
            self.assertEqual(0xAFBF001C, words[2])  # preserve native RA
            self.assertEqual(0xAFA20018, words[3])  # preserve native v0
            self.assertEqual(0xE7AC0014, words[4])  # preserve native f12
            self.assertEqual(3, words[5] >> 26)
            self.assertEqual(new_va, (words[5] & 0x03FFFFFF) << 2)
            self.assertEqual(0xC7AC0014, words[7]) # restore f12
            self.assertEqual(0x8FA20018, words[8]) # restore v0
            self.assertEqual(0x8FBF001C, words[9]) # restore ra
            self.assertEqual(0x27BD0020, words[10]) # restore sp
            self.assertEqual(
                cached_va,
                ((words[11] & 0xFFFF) << 16)
                + (words[12] & 0xFFFF)
                - (0x10000 if words[12] & 0x8000 else 0),
            )
            self.assertEqual(0xA1850023 if alpha_site == 0x65A88 else 0xA1800023, words[17])
        for off in (0x66668, 0x66DD4):
            self.assertEqual(0x0C06850C, struct.unpack_from("<I", result, off)[0])
        for owner, offset in (
            ("AFK Y spill", helper_file + 72),
            ("AFK preserved register", helper_file + 4),
            ("AFK constructor owner", 0x66250),
            ("L1 blue creation", 0x66740),
            ("L1 native pool", create_offset + 6 * 4),
            ("L1 pool resource selector", create_offset + 16 * 4),
            ("L1 green X copy", create_offset + 20 * 4),
            ("L1 green Y copy", create_offset + 22 * 4),
            ("L1 native blue depth", create_offset + 26 * 4),
            ("L1 animated live-rescan JAL", create_offset + 20),
            ("L1 visibility show", 0x65A88),
            ("L1 visibility hide", 0x65B40),
            ("L1 fade hide", 0x65C5C),
        ):
            with self.subTest(owner=owner):
                tampered = bytearray(result)
                tampered[offset] ^= 1
                check = next(
                    check for check in verify_startup_elf(bytes(tampered))
                    if check["name"] == "companion_hud_layout"
                )
                self.assertFalse(check["ok"])

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
            f"<{COMPANION_ACTION_R50_PANEL_EXTENSION_SIZE // 4}I",
            result,
            extension_file,
        )
        self.assertEqual(
            (
                0x000D7100, 0x000D7940, 0x01CF7021,
                0x3C0F0045, 0x25EF0AC4, 0x01EE7821,
                0x3C0E4360, 0xADEE0000,       # green width 224
                0x3C0E4250, 0x11A00002, 0x00000000,
                0x3C0E42C2, 0xADEE0008,       # green pivot-X 52 / 97
                0x3C0F0045, 0x25EF13F4,       # blue frame0 geometry
                0x3C0C4360,
                0, 0, 0, 0, 0, 0,  # r62 preserve preconstructor-only geometry
                0, 0, 0, 0, 0, 0,
                0x8FBF000C, 0x27BD0010, 0x24040002,
                extension_words[31], 0x00000000, 0x00000000,
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
