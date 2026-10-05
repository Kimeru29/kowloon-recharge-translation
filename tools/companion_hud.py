from __future__ import annotations

from dataclasses import dataclass
import struct

from tools.companion_hud_data import COMPANION_ACTION_DATA, COMPANION_COMMENT_DATA
from tools.executable_text import RelocatedText
from tools.localization import encode_ps2_english


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_MAX_STRING_BYTES = 512

# r31/r32 presentation owners for the persistent companion action caption. r30
# translated the payload but left the Japanese-era style/geometry in place.
# Group-2 index 0x18 is a fixed 160x32 backing sprite; r31 selected the proven
# 12px English style and moved the callout one backing-height above the action
# palette. r32 keeps that accepted text geometry and shifts only the backing 8px
# left so its visible body/spike aligns with the caption like the PS4 HUD.
COMPANION_ACTION_BACKING_WIDTH_OFFSET = 0x34EAD4
COMPANION_ACTION_BACKING_HEIGHT_OFFSET = 0x34EAD8
COMPANION_ACTION_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x666F0, 0x3C024140, 0x3C024080),  # backing X: +12.0 -> +4.0
    (0x66708, 0x3C02C1E8, 0x3C02C274),  # backing Y: -29.0 -> -61.0
    (0x66804, 0x3C024244, 0x3C0241A0),  # text X: +49.0 -> +20.0
    (0x6681C, 0x3C02C1B0, 0x3C02C258),  # text Y: -22.0 -> -54.0
    (0x6686C, 0x0000282D, 0x24050001),  # style 0 (16px) -> style 1 (12px)
)


@dataclass(frozen=True)
class CompanionCommentLine:
    source_offset: int
    source_text: str
    official_english: str
    remaster_offset: int
    pointer_offsets: tuple[int, ...]

    @property
    def display_english(self) -> str:
        # English.bytes uses @D to delete a PS4 line after its content was merged
        # into the previous localized line. An empty C-string preserves that
        # exact presentation semantic in the PS2 two-line HUD table.
        return "" if self.official_english == "@D" else self.official_english


@dataclass(frozen=True)
class CompanionActionLabel:
    action_id: int
    pointer_offset: int
    source_offset: int
    source_text: str
    english: str | None
    remaster_offset: int | None
    provenance: str


COMPANION_COMMENT_LINES: tuple[CompanionCommentLine, ...] = tuple(
    CompanionCommentLine(*record) for record in COMPANION_COMMENT_DATA
)
COMPANION_ACTION_LABELS: tuple[CompanionActionLabel, ...] = tuple(
    CompanionActionLabel(*record) for record in COMPANION_ACTION_DATA
)


def _source_va(source_offset: int) -> int:
    return _ELF_MAIN_VADDR + source_offset - _ELF_MAIN_FILE_OFFSET


def _validate_source_text(raw: bytes, *, owner: str, source_offset: int, source_text: str) -> None:
    expected = source_text.encode("cp932") + b"\x00"
    if source_offset < 0 or source_offset + len(expected) > len(raw):
        raise ValueError(f"{owner} source is outside executable: {source_offset:#x}")
    if raw[source_offset:source_offset + len(expected)] != expected:
        raise ValueError(f"{owner} source preimage mismatch: {source_offset:#x}")


def validate_companion_hud_source(raw: bytes) -> None:
    if len(COMPANION_COMMENT_LINES) != 1650:
        raise ValueError(f"companion comment corpus size drifted: {len(COMPANION_COMMENT_LINES)}")
    if sum(len(spec.pointer_offsets) for spec in COMPANION_COMMENT_LINES) != 1784:
        raise ValueError("companion comment pointer-alias count drifted")
    if len(COMPANION_ACTION_LABELS) != 31:
        raise ValueError(f"companion action corpus size drifted: {len(COMPANION_ACTION_LABELS)}")

    owned_pointers: set[int] = set()
    for spec in COMPANION_COMMENT_LINES:
        _validate_source_text(
            raw,
            owner="companion comment",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        expected_va = _source_va(spec.source_offset)
        for pointer_offset in spec.pointer_offsets:
            if pointer_offset in owned_pointers:
                raise ValueError(f"duplicate companion comment pointer owner: {pointer_offset:#x}")
            owned_pointers.add(pointer_offset)
            if pointer_offset < 0 or pointer_offset + 4 > len(raw):
                raise ValueError(f"companion comment pointer is outside executable: {pointer_offset:#x}")
            actual_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            if actual_va != expected_va:
                raise ValueError(
                    "companion comment pointer preimage mismatch: "
                    f"{pointer_offset:#x}: expected {expected_va:#x}, got {actual_va:#x}"
                )

    for expected_id, spec in enumerate(COMPANION_ACTION_LABELS):
        if spec.action_id != expected_id:
            raise ValueError(
                f"companion action table order drifted: expected {expected_id}, got {spec.action_id}"
            )
        _validate_source_text(
            raw,
            owner="companion action",
            source_offset=spec.source_offset,
            source_text=spec.source_text,
        )
        if spec.pointer_offset < 0 or spec.pointer_offset + 4 > len(raw):
            raise ValueError(f"companion action pointer is outside executable: {spec.action_id}")
        actual_va = struct.unpack_from("<I", raw, spec.pointer_offset)[0]
        expected_va = _source_va(spec.source_offset)
        if actual_va != expected_va:
            raise ValueError(
                "companion action pointer preimage mismatch: "
                f"id={spec.action_id}, expected {expected_va:#x}, got {actual_va:#x}"
            )


def patch_companion_action_layout(raw: bytes) -> bytes:
    """Apply the bounded r31/r32 companion-action callout presentation patch."""

    width = struct.unpack_from("<f", raw, COMPANION_ACTION_BACKING_WIDTH_OFFSET)[0]
    height = struct.unpack_from("<f", raw, COMPANION_ACTION_BACKING_HEIGHT_OFFSET)[0]
    if (width, height) != (160.0, 32.0):
        raise ValueError(
            "companion action backing geometry drifted: "
            f"expected 160x32, got {width:g}x{height:g}"
        )

    out = bytearray(raw)
    for offset, expected, replacement in COMPANION_ACTION_LAYOUT_PATCHES:
        if offset < 0 or offset + 4 > len(out):
            raise ValueError(f"companion action layout owner is outside executable: {offset:#x}")
        actual = struct.unpack_from("<I", out, offset)[0]
        if actual != expected:
            raise ValueError(
                "companion action layout preimage mismatch: "
                f"{offset:#x}: expected {expected:#010x}, got {actual:#010x}"
            )
        struct.pack_into("<I", out, offset, replacement)
    return bytes(out)


def relocated_companion_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    """Return the proven companion HUD text owners for the shared PT_LOAD.

    The two-line transient comment table is fully covered by unique exact
    CUSA27034 English.bytes keys: 1,650 source strings / 1,784 live aliases.
    Action labels reuse the same official corpus where possible, with four
    explicit Re:charge-only semantic labels and the id-0 placeholder left
    pristine. Japanese source bytes remain immutable provenance throughout.
    """

    validate_companion_hud_source(raw)
    entries = [
        RelocatedText(
            key=f"companion_comment_{spec.source_offset:06x}",
            encoded=encode_ps2_english(spec.display_english, collapse_spaces=False) + b"\x00",
            pointer_offsets=spec.pointer_offsets,
        )
        for spec in COMPANION_COMMENT_LINES
    ]
    entries.extend(
        RelocatedText(
            key=f"companion_action_{spec.action_id:02d}",
            encoded=encode_ps2_english(spec.english, collapse_spaces=False) + b"\x00",
            pointer_offsets=(spec.pointer_offset,),
        )
        for spec in COMPANION_ACTION_LABELS
        if spec.english is not None
    )
    return tuple(entries)
