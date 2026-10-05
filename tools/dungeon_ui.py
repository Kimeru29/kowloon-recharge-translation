from __future__ import annotations

from dataclasses import dataclass
import struct

from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA
from tools.executable_text import RelocatedCodeReference, RelocatedText
from tools.localization import encode_ps2_english


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
DUNGEON_ITEM_NAME_TABLE_OFFSET = 0x3912B4
DUNGEON_ITEM_NAME_TABLE_COUNT = 500


@dataclass(frozen=True)
class DungeonActionLabel:
    key: str
    source_offset: int
    source_text: str
    english: str
    remaster_offset: int
    code_reference: RelocatedCodeReference


@dataclass(frozen=True)
class DungeonItemName:
    item_id: int
    source_offset: int
    source_text: str
    english: str
    remaster_offset: int

    @property
    def pointer_offset(self) -> int:
        return DUNGEON_ITEM_NAME_TABLE_OFFSET + self.item_id * 4


# H_CmdIconDraw builds the three exploration-palette labels through direct
# LUI/ADDIU string owners. English.bytes provides exact JP-key matches for each.
# Keep the compact Japanese source bytes immutable and retarget only these code
# references into the shared executable translation segment.
DUNGEON_ACTION_LABELS: tuple[DungeonActionLabel, ...] = (
    DungeonActionLabel(
        "examine",
        0x3BC5F8,
        "調べる　",
        "Examine",
        0xD1CEF,
        RelocatedCodeReference("dungeon_action_examine", 0x4B654, 0x4B658, 0x3C06004C, 0x24C6C578),
    ),
    DungeonActionLabel(
        "items",
        0x3BC608,
        "アイテム",
        "Items",
        0x314C,
        RelocatedCodeReference("dungeon_action_items", 0x4B680, 0x4B684, 0x3C06004C, 0x24C6C588),
    ),
    DungeonActionLabel(
        "jump",
        0x3BC618,
        "ジャンプ",
        "Jump",
        0x3165,
        RelocatedCodeReference("dungeon_action_jump", 0x4B6AC, 0x4B6B0, 0x3C06004C, 0x24C6C598),
    ),
)

DUNGEON_ITEM_NAMES: tuple[DungeonItemName, ...] = tuple(
    DungeonItemName(*record) for record in DUNGEON_ITEM_NAME_DATA
)


def _source_va(source_offset: int) -> int:
    return _ELF_MAIN_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET


def _validate_source_text(raw: bytes, *, key: str, source_offset: int, source_text: str) -> None:
    encoded = source_text.encode("cp932") + b"\x00"
    if source_offset < 0 or source_offset + len(encoded) > len(raw):
        raise ValueError(f"Dungeon source is outside executable: {key}")
    if raw[source_offset:source_offset + len(encoded)] != encoded:
        raise ValueError(f"Dungeon source preimage mismatch: {key}")


def validate_dungeon_ui_source(raw: bytes) -> None:
    for spec in DUNGEON_ACTION_LABELS:
        _validate_source_text(
            raw,
            key=f"action/{spec.key}",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        ref = spec.code_reference
        if ref.lui_offset + 4 > len(raw) or ref.addiu_offset + 4 > len(raw):
            raise ValueError(f"Dungeon action code owner is outside executable: {spec.key}")
        actual_lui = struct.unpack_from("<I", raw, ref.lui_offset)[0]
        actual_addiu = struct.unpack_from("<I", raw, ref.addiu_offset)[0]
        if actual_lui != ref.expected_lui or actual_addiu != ref.expected_addiu:
            raise ValueError(
                f"Dungeon action code preimage mismatch: {spec.key}: "
                f"{actual_lui:#010x}/{actual_addiu:#010x}"
            )

    if len(DUNGEON_ITEM_NAMES) != 446:
        raise ValueError(f"Dungeon item-name corpus must contain 446 exact owners, got {len(DUNGEON_ITEM_NAMES)}")
    ids = {spec.item_id for spec in DUNGEON_ITEM_NAMES}
    if len(ids) != len(DUNGEON_ITEM_NAMES):
        raise ValueError("Dungeon item-name corpus contains duplicate item IDs")

    for spec in DUNGEON_ITEM_NAMES:
        if not (0 <= spec.item_id < DUNGEON_ITEM_NAME_TABLE_COUNT):
            raise ValueError(f"Dungeon item ID is outside pointer table: {spec.item_id}")
        _validate_source_text(
            raw,
            key=f"item/{spec.item_id}",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        pointer_offset = spec.pointer_offset
        if pointer_offset + 4 > len(raw):
            raise ValueError(f"Dungeon item pointer is outside executable: {spec.item_id}")
        actual = struct.unpack_from("<I", raw, pointer_offset)[0]
        expected = _source_va(spec.source_offset)
        if actual != expected:
            raise ValueError(
                f"Dungeon item pointer preimage mismatch for {spec.item_id}: "
                f"expected {expected:#x}, got {actual:#x}"
            )


def relocated_dungeon_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    validate_dungeon_ui_source(raw)
    entries = [
        RelocatedText(
            spec.code_reference.key,
            encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00",
            (),
        )
        for spec in DUNGEON_ACTION_LABELS
    ]
    entries.extend(
        RelocatedText(
            f"dungeon_item_{spec.item_id}",
            encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00",
            (spec.pointer_offset,),
        )
        for spec in DUNGEON_ITEM_NAMES
    )
    return tuple(entries)


def dungeon_code_references(raw: bytes) -> tuple[RelocatedCodeReference, ...]:
    validate_dungeon_ui_source(raw)
    return tuple(spec.code_reference for spec in DUNGEON_ACTION_LABELS)
