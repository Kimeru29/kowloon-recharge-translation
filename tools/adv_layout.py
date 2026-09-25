from __future__ import annotations

import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class AdvCoordinateConsumer:
    file_offset: int
    va: int
    line_field: int
    position_field: int
    line_load_word: int
    position_load_word: int
    role: str


# Pristine coordinate consumers discovered in SLPM_665.11.  These are probes,
# not patch targets: ownership must be proven separately before either path is
# mutated for English layout.
_CONSUMER_PREIMAGES: tuple[tuple[int, int, int, int], ...] = (
    # file offset, VA, line-field load offset, position-field load offset
    (0x14EDA0, 0x24ED20, 0x14EDA0, 0x14EDD8),
    (0x14FA60, 0x24F9E0, 0x14FA60, 0x14FAA4),
)

_CONSUMER_LOAD_WORDS: dict[int, tuple[int, int]] = {
    0x14EDA0: (0x80450463, 0x80630465),
    0x14FA60: (0x80430463, 0x80440465),
}

# Role classification requires the full pristine call/data chain, not merely a
# matching +0x463/+0x465 field pattern.  The second consumer is tied to the
# ordinary ADV script-text constructor; the first is its registered progress
# callback and does not compute X/Y coordinates.
_CONSUMER_ROLE_PREIMAGES: dict[int, tuple[str, tuple[tuple[int, int], ...]]] = {
    0x14EDA0: (
        "glyph_progress_gate",
        (
            # Read current message line, normalize record byte-position / 2,
            # then release/activate the child glyph object when progress passes.
            (0x14EDA4, 0x8F84E290),
            (0x14EDDC, 0x00031043),
            (0x14EE00, 0x0C0632B8),  # jal 0x18CAE0
        ),
    ),
    0x14FA60: (
        "dg_dialogue",
        (
            # Script-byte dispatcher -> message driver -> constructor wrapper.
            (0x1158E0, 0x27BDFFE0),  # function at VA 0x215860
            (0x1158F0, 0x90A30000),  # lbu v1, 0(a1): current script byte
            (0x115A00, 0x0C0939A4),  # jal 0x24E690
            (0x115AF0, 0x0C0939A4),  # second dispatcher path -> 0x24E690
            (0x14E7A0, 0x0C093A28),  # 0x24E690 -> jal 0x24E8A0
            # Constructor prologue and wrapper call.
            (0x14F6E0, 0x27BDFF20),
            (0x14E978, 0x0C093D98),  # 0x24E8A0 -> jal 0x24F660
            # Constructor registers 0x24E920 as its progress callback.
            (0x14F808, 0x3C070025),
            (0x14F80C, 0x24E7E920),
            (0x14F81C, 0x0C068464),  # jal 0x1A1190
            # Coordinate builder followed by glyph/sprite construction.
            (0x14FB10, 0x0C094700),  # jal 0x251C00
            (0x14FB90, 0x0C062FC4),  # jal 0x18BF10
        ),
    ),
}


def _require_word(raw: bytes, offset: int, expected: int) -> int:
    if offset + 4 > len(raw):
        raise ValueError("ADV consumer preimage is outside executable")
    actual = struct.unpack_from("<I", raw, offset)[0]
    if actual != expected:
        raise ValueError(
            f"ADV consumer preimage mismatch at {offset:#x}: "
            f"expected {expected:#010x}, got {actual:#010x}"
        )
    return actual


def inspect_adv_coordinate_consumers(raw: bytes) -> tuple[AdvCoordinateConsumer, ...]:
    """Validate and describe the two known ADV coordinate consumers.

    Matching the +0x463/+0x465 field pattern alone is deliberately not treated
    as DG ownership proof.  Exact call/data-chain preimages are required before
    the ordinary ADV text constructor is classified as the live DG layout path.
    """

    consumers: list[AdvCoordinateConsumer] = []
    for file_offset, va, line_load_offset, position_load_offset in _CONSUMER_PREIMAGES:
        expected_line, expected_position = _CONSUMER_LOAD_WORDS[file_offset]
        line_word = _require_word(raw, line_load_offset, expected_line)
        position_word = _require_word(raw, position_load_offset, expected_position)

        role, role_preimages = _CONSUMER_ROLE_PREIMAGES[file_offset]
        for offset, expected in role_preimages:
            _require_word(raw, offset, expected)

        consumers.append(
            AdvCoordinateConsumer(
                file_offset=file_offset,
                va=va,
                line_field=0x463,
                position_field=0x465,
                line_load_word=line_word,
                position_load_word=position_word,
                role=role,
            )
        )

    return tuple(consumers)


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
