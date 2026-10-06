from __future__ import annotations

from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class TranslationSegmentInfo:
    file_offset: int
    segment_vaddr: int
    heap_vaddr: int
    payload_size: int
    reserve_size: int


_ELF32_HEADER_MIN = 0x34
_PT_LOAD = 1
_SECOND_PH_OFFSET = 0x54
TRANSLATION_SEGMENT_VADDR = 0x00902F00
_TRANSLATION_VADDR = TRANSLATION_SEGMENT_VADDR
_HEAP_LUI_FILE_OFFSET = 0x250
_HEAP_ADDIU_FILE_OFFSET = 0x258
_BSS_END_LUI_FILE_OFFSET = 0x1A0
_BSS_END_ADDIU_FILE_OFFSET = 0x1A8
_HEAP_SECTION_ADDR_OFFSET = 0x8030BC
_LIBKERNEL_HEAP_BREAK_FILE_OFFSET = 0x650014
_EXPECTED_SECOND_PH = (
    _PT_LOAD,
    0x00802F80,
    _TRANSLATION_VADDR,
    _TRANSLATION_VADDR,
    0,
    0,
    6,
    0x10,
)
_EXPECTED_HEAP_LUI = 0x3C040090  # lui a0, 0x90
_EXPECTED_HEAP_ADDIU = 0x24842F00  # addiu a0, a0, 0x2f00
_EXPECTED_BSS_LUI = 0x3C030090  # lui v1, 0x90
_EXPECTED_BSS_ADDIU = 0x24632F00  # addiu v1, v1, 0x2f00
_EXPECTED_HEAP_SECTION_ADDR = _TRANSLATION_VADDR
_EXPECTED_LIBKERNEL_HEAP_BREAK = _TRANSLATION_VADDR


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def install_translation_segment(
    raw: bytes,
    payload: bytes,
    *,
    reserve_size: int = 0x100000,
    executable: bool = False,
) -> tuple[bytes, TranslationSegmentInfo]:
    """Use Kowloon's dormant second PT_LOAD as an ELF translation-text segment.

    The pristine executable's first segment/BSS is zeroed through 0x902F00 and
    its second PT_LOAD starts there with filesz=memsz=0.  We keep the BSS bound
    untouched, load translated data at 0x902F00, reserve ``reserve_size`` bytes
    of virtual RAM, and move only the runtime heap-start syscall to the first
    byte after that reservation.

    This is intentionally fail-closed against the proven SLPM-66511 layout.
    """

    if len(raw) < _ELF32_HEADER_MIN or raw[:4] != b"\x7fELF":
        raise ValueError("Expected a 32-bit ELF executable")
    if reserve_size <= 0 or reserve_size & 0xFFFF:
        raise ValueError("Translation segment reserve must be a positive 64 KiB multiple")
    if len(payload) > reserve_size:
        raise ValueError("Translation payload exceeds reserved RAM window")

    if _SECOND_PH_OFFSET + 32 > len(raw):
        raise ValueError("ELF second PT_LOAD is outside file")
    actual_second_ph = struct.unpack_from("<IIIIIIII", raw, _SECOND_PH_OFFSET)
    if actual_second_ph != _EXPECTED_SECOND_PH:
        raise ValueError(
            "Unexpected second PT_LOAD preimage: "
            f"expected {_EXPECTED_SECOND_PH!r}, got {actual_second_ph!r}"
        )

    if struct.unpack_from("<I", raw, _BSS_END_LUI_FILE_OFFSET)[0] != _EXPECTED_BSS_LUI:
        raise ValueError("Unexpected BSS-end instruction preimage")
    if struct.unpack_from("<I", raw, _BSS_END_ADDIU_FILE_OFFSET)[0] != _EXPECTED_BSS_ADDIU:
        raise ValueError("Unexpected BSS-end instruction preimage")
    if struct.unpack_from("<I", raw, _HEAP_LUI_FILE_OFFSET)[0] != _EXPECTED_HEAP_LUI:
        raise ValueError("Unexpected heap-start instruction preimage")
    if struct.unpack_from("<I", raw, _HEAP_ADDIU_FILE_OFFSET)[0] != _EXPECTED_HEAP_ADDIU:
        raise ValueError("Unexpected heap-start instruction preimage")
    if _HEAP_SECTION_ADDR_OFFSET + 4 > len(raw):
        raise ValueError("Heap section header is outside ELF")
    if struct.unpack_from("<I", raw, _HEAP_SECTION_ADDR_OFFSET)[0] != _EXPECTED_HEAP_SECTION_ADDR:
        raise ValueError("Unexpected heap section address preimage")
    if struct.unpack_from("<I", raw, _LIBKERNEL_HEAP_BREAK_FILE_OFFSET)[0] != _EXPECTED_LIBKERNEL_HEAP_BREAK:
        raise ValueError("Unexpected libkernel heap break preimage")

    heap_vaddr = _TRANSLATION_VADDR + reserve_size
    if (heap_vaddr & 0xFFFF) != (_TRANSLATION_VADDR & 0xFFFF):
        raise ValueError("Translation reserve must preserve the proven heap low halfword")
    heap_hi = heap_vaddr >> 16
    if heap_hi > 0xFFFF:
        raise ValueError("Translated heap address is not representable by proven startup sequence")

    file_offset = _align(len(raw), 0x10)
    result = bytearray(raw)
    if len(result) < file_offset:
        result.extend(b"\x00" * (file_offset - len(result)))
    result.extend(payload)

    # p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align
    struct.pack_into(
        "<IIIIIIII",
        result,
        _SECOND_PH_OFFSET,
        _PT_LOAD,
        file_offset,
        _TRANSLATION_VADDR,
        _TRANSLATION_VADDR,
        len(payload),
        reserve_size,
        7 if executable else 6,
        0x10,
    )

    # Preserve BSS zero-fill through 0x902F00.  Move only the heap syscall from
    # 0x902F00 to the end of the reserved translation window.
    heap_lui = (_EXPECTED_HEAP_LUI & 0xFFFF0000) | heap_hi
    struct.pack_into("<I", result, _HEAP_LUI_FILE_OFFSET, heap_lui)
    struct.pack_into("<I", result, _HEAP_SECTION_ADDR_OFFSET, heap_vaddr)
    struct.pack_into("<I", result, _LIBKERNEL_HEAP_BREAK_FILE_OFFSET, heap_vaddr)

    return bytes(result), TranslationSegmentInfo(
        file_offset=file_offset,
        segment_vaddr=_TRANSLATION_VADDR,
        heap_vaddr=heap_vaddr,
        payload_size=len(payload),
        reserve_size=reserve_size,
    )
