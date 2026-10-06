from __future__ import annotations

from dataclasses import dataclass
import struct
from collections.abc import Sequence

from tools.elf_translation_segment import TranslationSegmentInfo, install_translation_segment


@dataclass(frozen=True)
class RelocatedText:
    key: str
    encoded: bytes
    pointer_offsets: tuple[int, ...]
    alignment: int = 2


@dataclass(frozen=True)
class RelocatedCodeReference:
    key: str
    lui_offset: int
    addiu_offset: int
    expected_lui: int
    expected_addiu: int


@dataclass(frozen=True)
class ExecutableTextResult:
    raw: bytes
    info: TranslationSegmentInfo
    target_vas: dict[str, int]


def install_executable_text(
    raw: bytes,
    entries: Sequence[RelocatedText],
    reserve_size: int = 0x100000,
    *,
    executable_segment: bool = False,
) -> ExecutableTextResult:
    """Pack executable text once and repoint every declared external alias.

    The caller owns semantic/source-preimage validation. This layer owns only the
    deterministic allocation contract: input sequence order, declared power-
    of-two entry alignment (2-byte by default), unique keys/pointer ownership,
    one translation PT_LOAD install, and deterministic target-VA reporting.
    """

    ordered = tuple(entries)
    keys: set[str] = set()
    pointer_owners: dict[int, str] = {}
    for entry in ordered:
        if not entry.key:
            raise ValueError("Relocated text key must not be empty")
        if entry.key in keys:
            raise ValueError(f"Relocated text duplicate key: {entry.key}")
        keys.add(entry.key)
        if not isinstance(entry.encoded, bytes):
            raise TypeError(f"Relocated text payload must be bytes: {entry.key}")
        if entry.alignment < 2 or entry.alignment & (entry.alignment - 1):
            raise ValueError(f"Relocated text alignment must be a power of two >= 2: {entry.key}")

        for pointer_offset in entry.pointer_offsets:
            if pointer_offset < 0 or pointer_offset + 4 > len(raw):
                raise ValueError(f"Relocated text pointer offset is outside executable: {pointer_offset:#x}")
            previous = pointer_owners.get(pointer_offset)
            if previous is not None:
                raise ValueError(
                    "Relocated text pointer ownership conflict at "
                    f"{pointer_offset:#x}: {previous} vs {entry.key}"
                )
            pointer_owners[pointer_offset] = entry.key

    payload = bytearray()
    payload_offsets: dict[str, int] = {}
    for entry in ordered:
        while len(payload) & (entry.alignment - 1):
            payload.append(0)
        payload_offsets[entry.key] = len(payload)
        payload.extend(entry.encoded)

    if len(payload) > reserve_size:
        raise ValueError("Executable text payload exceeds translation reserve")

    expanded, info = install_translation_segment(
        raw,
        bytes(payload),
        reserve_size=reserve_size,
        executable=executable_segment,
    )
    result = bytearray(expanded)
    target_vas = {
        key: info.segment_vaddr + payload_offset
        for key, payload_offset in payload_offsets.items()
    }

    for entry in ordered:
        target_va = target_vas[entry.key]
        for pointer_offset in entry.pointer_offsets:
            struct.pack_into("<I", result, pointer_offset, target_va)

    return ExecutableTextResult(bytes(result), info, target_vas)
