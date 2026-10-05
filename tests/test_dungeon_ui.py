from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.dungeon_ui import DUNGEON_ACTION_LABELS, DUNGEON_ITEM_NAMES, validate_dungeon_ui_source
from tools.early_ui import build_early_ui_elf
from tools.localization import encode_ps2_english


ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


def _direct_target(raw: bytes, lui_offset: int, addiu_offset: int) -> int:
    lui = struct.unpack_from("<I", raw, lui_offset)[0]
    addiu = struct.unpack_from("<I", raw, addiu_offset)[0]
    hi = lui & 0xFFFF
    lo = addiu & 0xFFFF
    signed_lo = lo if lo < 0x8000 else lo - 0x10000
    return ((hi << 16) + signed_lo) & 0xFFFFFFFF


def _read_at_va(raw: bytes, va: int, size: int) -> bytes:
    p_type, p_offset, p_vaddr, _paddr, p_filesz, _memsz, _flags, _align = struct.unpack_from(
        "<IIIIIIII", raw, 0x54
    )
    if p_type == 1:
        relative = va - p_vaddr
        if 0 <= relative and relative + size <= p_filesz:
            return raw[p_offset + relative:p_offset + relative + size]

    main_offset = va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET
    if 0 <= main_offset <= len(raw) - size:
        return raw[main_offset:main_offset + size]
    return b""


class DungeonUiTests(unittest.TestCase):
    def test_r29_owner_inventory_is_complete_and_fail_closed(self) -> None:
        self.assertEqual(3, len(DUNGEON_ACTION_LABELS))
        self.assertEqual(446, len(DUNGEON_ITEM_NAMES))
        self.assertEqual(446, len({spec.item_id for spec in DUNGEON_ITEM_NAMES}))
        self.assertEqual(446, len({spec.source_offset for spec in DUNGEON_ITEM_NAMES}))
        self.assertEqual(
            tuple(0x3912B4 + spec.item_id * 4 for spec in DUNGEON_ITEM_NAMES),
            tuple(spec.pointer_offset for spec in DUNGEON_ITEM_NAMES),
        )
        validate_dungeon_ui_source(RAW)

        action_tampered = bytearray(RAW)
        action_tampered[DUNGEON_ACTION_LABELS[0].code_reference.lui_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "action code preimage mismatch"):
            validate_dungeon_ui_source(bytes(action_tampered))

        item_tampered = bytearray(RAW)
        item_tampered[DUNGEON_ITEM_NAMES[0].pointer_offset] ^= 1
        with self.assertRaisesRegex(ValueError, "item pointer preimage mismatch"):
            validate_dungeon_ui_source(bytes(item_tampered))

    def test_r29_exploration_action_palette_uses_wide_official_labels(self) -> None:
        result = build_early_ui_elf(RAW)
        cases = (
            ("調べる　", "Examine", 0x3BC5F8, 0x4B654, 0x4B658),
            ("アイテム", "Items", 0x3BC608, 0x4B680, 0x4B684),
            ("ジャンプ", "Jump", 0x3BC618, 0x4B6AC, 0x4B6B0),
        )

        for source, english, source_offset, lui_offset, addiu_offset in cases:
            with self.subTest(source=source):
                source_bytes = source.encode("cp932") + b"\x00"
                self.assertEqual(
                    source_bytes,
                    result[source_offset:source_offset + len(source_bytes)],
                    "Japanese provenance must remain byte-identical",
                )
                target = _direct_target(result, lui_offset, addiu_offset)
                expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
                self.assertEqual(expected, _read_at_va(result, target, len(expected)))

    def test_r29_battle_palette_and_l1_selected_item_names_use_wide_official_text(self) -> None:
        result = build_early_ui_elf(RAW)
        # VA 0x134AB0 indexes this 500-entry item-name pointer table. The moving
        # battle-palette/L1 selection path passes that pointer straight to the HUD
        # text constructor, so every exact official-remaster match is relocated in
        # the PS2 two-byte glyph path while preserving its Japanese source bytes.
        for spec in DUNGEON_ITEM_NAMES:
            with self.subTest(item_id=spec.item_id):
                target = struct.unpack_from("<I", result, spec.pointer_offset)[0]
                payload = encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00"
                self.assertEqual(payload, _read_at_va(result, target, len(payload)))
                source = spec.source_text.encode("cp932") + b"\x00"
                self.assertEqual(source, result[spec.source_offset:spec.source_offset + len(source)])


if __name__ == "__main__":
    unittest.main()
