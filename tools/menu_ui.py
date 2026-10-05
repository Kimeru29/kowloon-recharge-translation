from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from tools.elf_strings import ElfFixedStringPatch
from tools.executable_text import RelocatedText
from tools.localization import encode_ps2_english


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000


@dataclass(frozen=True)
class MenuLabelSpec:
    key: str
    source_offset: int
    capacity: int
    source_text: str
    action_owner: str | None
    official_english: str | None
    selected_english: str | None
    evidence: str
    storage: str
    status: str
    pointer_offsets: tuple[int, ...] = ()


# The command-thumbnail renderer consumes the game's two-byte glyph stream. r29
# runtime evidence (Items -> ISdlR, Noise -> NnhRd while H.A.N.T survives) proves
# that earlier ASCII fixed-slot writes were interpreted through the wrong glyph
# path. Every proven command label is therefore pointer-relocated as wide PS2
# text; the compact Japanese source slots remain immutable provenance.
_COMMAND_MENU_OWNER = (
    "command-menu label table VA 0x004BC830; selected pointer is loaded at "
    "renderer VAs 0x150C68/0x150FEC and passed to text object VA 0x1529E0"
)
_ACCEPTED_MAPPING = "accepted official-remaster mapping; " + _COMMAND_MENU_OWNER

MENU_LABELS: tuple[MenuLabelSpec, ...] = (
    MenuLabelSpec("items", 0x3BC7C8, 16, "アイテム", "command-label id 3", "Items", "Items", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8BC", "relocated", "proven", (0x3BC8BC,)),
    MenuLabelSpec("quests", 0x3BC7D8, 16, "クエスト", "command-label id 4", "Quests", "Quests", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8C0", "relocated", "proven", (0x3BC8C0,)),
    MenuLabelSpec("hant", 0x3BC7E8, 16, "Ｈ．Ａ．Ｎ．Ｔ", "command-label id 5", "H.A.N.T", "H.A.N.T", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8C4", "relocated", "proven", (0x3BC8C4,)),
    MenuLabelSpec("save_load", 0x3BC7F8, 16, "セーブ＆ロード", "command-label id 6", "Save & load", "Save & load", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8C8", "relocated", "proven", (0x3BC8C8,)),
    MenuLabelSpec("leave_room", 0x3BC808, 16, "部屋を出る", "command-label ids 7/20", "Leave room", "Leave room", _ACCEPTED_MAPPING + "; source pointer aliases file 0x3BC8CC/0x3BC900", "relocated", "proven", (0x3BC8CC, 0x3BC900)),
    MenuLabelSpec("shop", 0x3BC818, 16, "ショップ", "command-label id 8", "Shop", "Shop", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8D0", "relocated", "proven", (0x3BC8D0,)),
    MenuLabelSpec("guild_site", 0x3BC828, 16, "ギルドサイト", "command-label id 9", "Guild site", "Guild site", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8D4", "relocated", "proven", (0x3BC8D4,)),
    MenuLabelSpec("broadband", 0x3BC838, 16, "ブロードバンド", "command-label id 10", "Broadband", "Broadband", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8D8", "relocated", "proven", (0x3BC8D8,)),
    MenuLabelSpec("collection", 0x3BC848, 16, "コレクション", "command-label ids 11/18", "Collection", "Collection", _ACCEPTED_MAPPING + "; source pointer aliases file 0x3BC8DC/0x3BC8F8", "relocated", "proven", (0x3BC8DC, 0x3BC8F8)),
    MenuLabelSpec("media", 0x3BC858, 16, "メディア", "command-label id 12", None, None, _COMMAND_MENU_OWNER + "; source pointer file 0x3BC8E0; no exact official counterpart/action semantic proven", "pristine", "unresolved", (0x3BC8E0,)),
    MenuLabelSpec("next_chapter", 0x3BC868, 16, "次の話へ", "command-label id 14", "Next chapter", "Next chapter", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8E8", "relocated", "proven", (0x3BC8E8,)),
    MenuLabelSpec("end_turn", 0x3BC878, 16, "ターン終了", "command-label id 15", "End turn", "End turn", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8EC", "relocated", "proven", (0x3BC8EC,)),
    MenuLabelSpec(
        "return_above_ground",
        0x3BC888,
        16,
        "地上へ脱出",
        "command-label id 17",
        "Return above ground",
        "Return above ground",
        _COMMAND_MENU_OWNER
        + "; whole-ELF pointer scan finds sole source alias at file 0x3BC8F4 and no direct absolute source materialization",
        "relocated",
        "proven",
        (0x3BC8F4,),
    ),
    MenuLabelSpec("interior", 0x3BC898, 16, "インテリア", "command-label id 19", "Interior", "Interior", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8FC", "relocated", "proven", (0x3BC8FC,)),
    MenuLabelSpec("none", 0x694180, 8, "なし", "command-label id 0", "None", "None", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8B0", "relocated", "proven", (0x3BC8B0,)),
    MenuLabelSpec("map", 0x694188, 8, "マップ", "command-label id 1", "Map", "Map", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8B4", "relocated", "proven", (0x3BC8B4,)),
    MenuLabelSpec(
        "report_card",
        0x694190,
        8,
        "成績表",
        "command-label id 2",
        "Report card",
        "Report card",
        _COMMAND_MENU_OWNER
        + "; whole-ELF pointer scan finds sole source alias at file 0x3BC8B8; GP=0x79B1F0 scan finds no direct source access",
        "relocated",
        "proven",
        (0x3BC8B8,),
    ),
    MenuLabelSpec("noise", 0x694198, 8, "ノイズ", "command-label id 13", "Noise", "Noise", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8E4", "relocated", "proven", (0x3BC8E4,)),
    MenuLabelSpec("battle", 0x6941A0, 8, "戦闘", "command-label id 16", "Battle", "Battle", _ACCEPTED_MAPPING + "; source pointer file 0x3BC8F0", "relocated", "proven", (0x3BC8F0,)),
)


def _source_va(source_offset: int) -> int:
    return _ELF_MAIN_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET


def _validate_manifest() -> None:
    if len({spec.key for spec in MENU_LABELS}) != len(MENU_LABELS):
        raise ValueError("Menu manifest contains duplicate keys")
    if len({spec.source_offset for spec in MENU_LABELS}) != len(MENU_LABELS):
        raise ValueError("Menu manifest contains duplicate source offsets")

    ordered = sorted(MENU_LABELS, key=lambda spec: spec.source_offset)
    previous_end = 0
    for spec in ordered:
        if spec.capacity <= 0 or spec.source_offset < 0:
            raise ValueError(f"Invalid menu source slot for {spec.key}")
        if spec.source_offset < previous_end:
            raise ValueError("Menu source slots overlap")
        previous_end = spec.source_offset + spec.capacity

        if spec.storage not in {"fixed-slot", "relocated", "pristine"}:
            raise ValueError(f"Invalid menu storage class for {spec.key}: {spec.storage}")
        if spec.status not in {"proven", "unresolved", "intentionally-pristine"}:
            raise ValueError(f"Invalid menu status for {spec.key}: {spec.status}")
        if spec.status == "proven" and not spec.evidence:
            raise ValueError(f"Proven menu label lacks evidence: {spec.key}")
        if spec.status == "unresolved" and spec.selected_english is not None:
            raise ValueError(f"Unresolved menu label cannot select English: {spec.key}")
        if spec.storage == "fixed-slot":
            if spec.status != "proven" or spec.selected_english is None:
                raise ValueError(f"Fixed menu label must be proven and selected: {spec.key}")
            try:
                encoded = spec.selected_english.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError(f"Fixed menu English must be ASCII: {spec.key}") from exc
            if len(encoded) >= spec.capacity:
                raise ValueError(f"Fixed menu English does not fit source slot: {spec.key}")
        if spec.storage == "relocated":
            if spec.status != "proven" or spec.selected_english is None:
                raise ValueError(f"Relocated menu label must be proven and selected: {spec.key}")
            if not spec.pointer_offsets:
                raise ValueError(f"Relocated menu label has no proven pointers: {spec.key}")


_validate_manifest()


def _validate_source_slot(raw: bytes, spec: MenuLabelSpec) -> None:
    end = spec.source_offset + spec.capacity
    if end > len(raw):
        raise ValueError(f"Menu source slot is outside executable: {spec.key}")
    expected = spec.source_text.encode("cp932")
    if len(expected) >= spec.capacity:
        raise ValueError(f"Menu source text does not fit declared slot: {spec.key}")
    if raw[spec.source_offset:spec.source_offset + len(expected)] != expected or raw[spec.source_offset + len(expected)] != 0:
        raise ValueError(f"Menu source preimage mismatch: {spec.key}")


def _validate_source_slots(raw: bytes) -> None:
    for spec in MENU_LABELS:
        _validate_source_slot(raw, spec)


def fixed_menu_patches() -> tuple[ElfFixedStringPatch, ...]:
    return tuple(
        ElfFixedStringPatch(spec.source_offset, spec.capacity, spec.source_text, spec.selected_english)
        for spec in MENU_LABELS
        if spec.storage == "fixed-slot" and spec.selected_english is not None
    )



def relocated_menu_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    """Return every proven command label in the renderer's two-byte glyph path."""

    entries: list[RelocatedText] = []
    for spec in MENU_LABELS:
        if spec.storage != "relocated":
            continue
        _validate_source_slot(raw, spec)
        expected_va = _source_va(spec.source_offset)
        for pointer_offset in spec.pointer_offsets:
            if pointer_offset < 0 or pointer_offset + 4 > len(raw):
                raise ValueError(f"Menu pointer is outside executable: {spec.key}")
            actual_va = int.from_bytes(raw[pointer_offset:pointer_offset + 4], "little")
            if actual_va != expected_va:
                raise ValueError(
                    f"Menu pointer preimage mismatch for {spec.key} at {pointer_offset:#x}: "
                    f"expected {expected_va:#x}, got {actual_va:#x}"
                )
        if spec.selected_english is None:
            raise ValueError(f"Relocated menu label has no selected English: {spec.key}")
        entries.append(
            RelocatedText(
                key=f"menu_{spec.key}",
                encoded=encode_ps2_english(spec.selected_english, collapse_spaces=False) + b"\x00",
                pointer_offsets=spec.pointer_offsets,
            )
        )
    return tuple(entries)

def patch_menu_labels(
    raw: bytes,
    relocated_targets: Mapping[str, int] | None = None,
) -> bytes:
    """Validate command-label provenance and optionally redirect proven owners.

    Normal composite builds install ``relocated_menu_entries`` through the shared
    translation PT_LOAD, so this function intentionally leaves source slots
    untouched when no explicit target mapping is supplied.
    """

    _validate_source_slots(raw)
    result = bytearray(raw)

    if relocated_targets is None:
        return bytes(result)

    by_key = {spec.key: spec for spec in MENU_LABELS}
    unknown = set(relocated_targets) - set(by_key)
    if unknown:
        raise ValueError(f"Unknown relocated menu target(s): {', '.join(sorted(unknown))}")

    for key, target_va in relocated_targets.items():
        spec = by_key[key]
        if spec.storage != "relocated":
            raise ValueError(f"Menu label is not relocation-owned: {key}")
        if not isinstance(target_va, int) or not (0 < target_va <= 0xFFFFFFFF):
            raise ValueError(f"Invalid relocated menu target VA: {key}")
        expected_va = _source_va(spec.source_offset)
        for pointer_offset in spec.pointer_offsets:
            if pointer_offset < 0 or pointer_offset + 4 > len(result):
                raise ValueError(f"Menu pointer is outside executable: {key}")
            actual_va = int.from_bytes(result[pointer_offset:pointer_offset + 4], "little")
            if actual_va != expected_va:
                raise ValueError(
                    f"Menu pointer preimage mismatch for {key} at {pointer_offset:#x}: "
                    f"expected {expected_va:#x}, got {actual_va:#x}"
                )
            result[pointer_offset:pointer_offset + 4] = target_va.to_bytes(4, "little")

    return bytes(result)
