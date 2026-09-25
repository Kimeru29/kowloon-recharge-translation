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
            # Preserve the pristine signed byte-position /2 normalization.
            (0x14FAA8, 0x00041843),  # sra v1,a0,1
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


# The pristine constructor computes both coordinate formulas correctly for its
# two record fields; only their destination argument registers are vertical-JP
# ordered.  Swap the finished signed integer coordinate outputs immediately
# before the 0x251C00 call.  This preserves the proven FPU formula/pipeline and
# the existing signed byte-position /2 normalization path.
ADV_DG_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    # First formula: 114 - 39 * line.  a1 (X) -> a2 (Y).
    (0x14FA9C, 0x00032C3C, 0x0003343C),  # dsll32 a1,v1,16 -> dsll32 a2,v1,16
    (0x14FAA0, 0x00052C3F, 0x0006343F),  # dsra32 a1,a1,16 -> dsra32 a2,a2,16
    # Second formula: 20 + 26 * (byte_position / 2).  a2 (Y) -> a1 (X).
    (0x14FAF4, 0x0003343C, 0x00032C3C),  # dsll32 a2,v1,16 -> dsll32 a1,v1,16
    (0x14FAF8, 0x0006343F, 0x00052C3F),  # dsra32 a2,a2,16 -> dsra32 a1,a1,16
)


def patch_adv_horizontal_layout(raw: bytes) -> bytes:
    """Transpose only the proven ADV/DG glyph-layout constructor to English.

    The pristine constructor computes X-like ``114 - 39 * line`` and Y-like
    ``20 + 26 * (byte_position / 2)`` integer coordinates before passing them as
    ``a1``/``a2`` to the coordinate helper.  English needs the second formula as
    X and the first as Y.  Swapping the completed argument registers preserves
    the existing two-byte glyph normalization exactly once, does not halve the
    line index, and avoids modifying the FPU pipeline or the separate reveal
    progress callback.
    """

    try:
        consumers = inspect_adv_coordinate_consumers(raw)
    except ValueError as exc:
        raise ValueError(f"ADV layout preimage mismatch: {exc}") from exc

    live = [consumer for consumer in consumers if consumer.role == "dg_dialogue"]
    if len(live) != 1 or live[0].file_offset != 0x14FA60:
        raise ValueError("ADV layout preimage does not identify exactly one proven DG consumer")

    result = bytearray(raw)
    for offset, expected, replacement in ADV_DG_LAYOUT_PATCHES:
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
