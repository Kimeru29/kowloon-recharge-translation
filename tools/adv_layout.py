from __future__ import annotations

import struct


# File offsets in SLPM_665.11 corresponding to the ADV glyph-position code at
# VA 0x24F9E0..0x24FA28 (main PT_LOAD file 0x80 -> VA 0x00100000).
_PATCHES: tuple[tuple[int, int, int], ...] = (
    # lb v1, 0x463(v0) -> lb v1, 0x465(v0)
    (0x14FA60, 0x80430463, 0x80430465),
    # nop -> sra v1, v1, 1  (wide text byte-position -> glyph index)
    (0x14FA68, 0x00000000, 0x00031843),
    # lb a0, 0x465(v0) -> lb a0, 0x463(v0)
    (0x14FAA4, 0x80440465, 0x80440463),
    # sra v1, a0, 1 -> move v1, a0  (line index is already normalized)
    (0x14FAA8, 0x00041843, 0x0080182D),
)


def patch_adv_horizontal_layout(raw: bytes) -> bytes:
    """Transpose Kowloon's ADV message layout from vertical JP to horizontal EN.

    The message compiler stores two independent coordinates per glyph record:
    +0x463 is the message line/column index, while +0x465 is the byte position
    within that line.  The pristine renderer maps +0x463 to X and (+0x465 / 2)
    to Y, yielding vertical Japanese columns.  The English MTX importer keeps
    two-byte glyphs to avoid colliding with ASCII script opcodes, so horizontal
    presentation is obtained by swapping those axes while preserving the /2 on
    the byte-position coordinate.
    """

    result = bytearray(raw)
    for offset, expected, replacement in _PATCHES:
        if offset + 4 > len(result):
            raise ValueError("ADV layout patch is outside executable")
        actual = struct.unpack_from("<I", result, offset)[0]
        if actual != expected:
            raise ValueError(
                f"ADV layout preimage mismatch at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )
        struct.pack_into("<I", result, offset, replacement)
    return bytes(result)
