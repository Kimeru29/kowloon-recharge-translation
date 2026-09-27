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
            # Constructor prologue and wrapper call.  The wrapper passes
            # orientation a2=1 (vertical); the constructor saves it in s4.
            (0x14F6E0, 0x27BDFF20),
            (0x14E96C, 0x24060001),  # addiu a2,zero,1
            (0x14E978, 0x0C093D98),  # 0x24E8A0 -> jal 0x24F660
            # Constructor registers 0x24E920 as its progress callback.
            (0x14F808, 0x3C070025),
            (0x14F80C, 0x24E7E920),
            (0x14F81C, 0x0C068464),  # jal 0x1A1190
            # Preserve the pristine signed byte-position /2 normalization.
            (0x14FAA8, 0x00041843),  # sra v1,a0,1
            # Coordinate builder followed by fragment-font construction.
            # s4 is forwarded as font orientation; generic font drawing uses
            # zero to advance X and nonzero to advance Y.
            (0x14FB10, 0x0C094700),  # jal 0x251C00
            (0x14FB7C, 0x0280302D),  # move a2,s4
            (0x14FB90, 0x0C062FC4),  # jal 0x18BF10
            (0x08E07C, 0x16C00009),  # bnez s6 -> vertical advance
            (0x08E098, 0x4600AD40),  # horizontal: add.s f21,f21,f0
            (0x08E0B8, 0x4600A500),  # vertical: add.s f20,f20,f0
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


# The pristine ADV object has two independent vertical-JP behaviors. First,
# its completed record coordinates are routed as X=line/Y=position. Second,
# the unique wrapper calls the object constructor with orientation=1; that flag
# is saved in s4 and propagated to all four child font canvases, whose generic
# draw callback advances Y per character. English must transpose the finished
# origins AND clear the single upstream constructor orientation. The FPU formulas
# and signed byte-position /2 normalization remain unchanged.
#
# Inline bracket-derived speaker names are a third, independent path. Runtime r6
# disproved the earlier mode-only hypothesis: changing its 0x190A50 text mode
# from 2 to 1 changed the mesh path but the visible speaker still advanced down
# the screen. Static tracing now proves why: 0x190A50 overwrites a2 with 1 before
# calling 0x188AD0; 0x188AD0 stores that byte at the font object +0x24; and the
# live renderer at 0x18DFFC advances X only when +0x24 is zero, otherwise Y.
# Preserve every existing nonzero-mode caller by replacing the hardcoded 1 with
# ``sltu a2,zero,s0`` where s0 is the saved text mode, then move only this speaker
# to otherwise-unused direct-call mode 0. Mode 0 keeps the normal 16x18 font and
# becomes horizontal while modes 1..7 retain their pristine vertical flag. The
# speaker's own fixed X remains 20. r7 runtime proves the horizontal header path;
# r8 moves only Y to 276 so it sits just above the lower-screen body block whose
# transposed base moves to 312, matching the remaster composition more closely.
#
# Keep the r5 0x251470 record-label orientation patch because it is a distinct
# ADV record-label renderer and removing a shipped change without contrary
# runtime evidence would risk a regression. It is not the inline DG speaker.
_ADV_SPEAKER_ROLE_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x11597C, 0x24020081),  # dispatcher: first CP932 bracket byte 0x81
    (0x115988, 0x92030001),  # dispatcher: load second bracket byte
    (0x11598C, 0x24020079),  # dispatcher: second CP932 bracket byte 0x79
    (0x1159E8, 0x0C0942C4),  # bracket path -> jal 0x250B10
    (0x1506F8, 0x24640198),  # parser destination: global +0x198
    (0x150078, 0x24470198),  # live renderer a3 = global +0x198
    (0x15007C, 0x0C064294),  # live renderer -> jal 0x190A50
    (0x088D50, 0xA2120024),  # VA 0x188CD0 stores a2-derived orientation at +0x24
    (0x08E07C, 0x16C00009),  # VA 0x18DFFC branches on orientation byte
    (0x1514F0, 0x27BDFF30),  # distinct r5 record-label state machine
    (0x151614, 0x0C062FC4),  # separate 0x18BF10 font canvas constructor
)

_ADV_DG_BODY_STYLE_PREIMAGES: tuple[tuple[int, int], ...] = (
    (0x14FB70, 0x24050001),  # VA 0x24FAF0: body fragments use font style 1
    (0x4D7884, 0x01000C0C),  # style-1 profile starts with 12x12 glyph dimensions
)

ADV_SPEAKER_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    (0x150048, 0x3C024301, 0x3C0241A0),  # speaker X: 129 -> 20
    (0x150050, 0x3C0241A0, 0x3C02438A),  # speaker Y: 20 -> 276
    (0x15006C, 0x24050002, 0x24050000),  # speaker mode 2 -> mode 0
    (0x090B30, 0x24060001, 0x0010302B),  # a2 = (saved text mode != 0)
    (0x151608, 0x24060001, 0x24060000),  # preserve r5 record-label orientation
)

ADV_DG_LAYOUT_PATCHES: tuple[tuple[int, int, int], ...] = (
    # First formula: 114 - 39 * line.  a1 (X) -> a2 (Y).
    (0x14FA9C, 0x00032C3C, 0x0003343C),  # dsll32 a1,v1,16 -> dsll32 a2,v1,16
    (0x14FAA0, 0x00052C3F, 0x0006343F),  # dsra32 a1,a1,16 -> dsra32 a2,a2,16
    # Second formula becomes English X. Preserve the proven /2 byte-to-glyph
    # normalization, but replace the Japanese 26 px column stride with the 12 px
    # advance of the exact style-1 font profile used by these child fragments.
    (0x14FAF4, 0x0003343C, 0x00032C3C),  # dsll32 a2,v1,16 -> dsll32 a1,v1,16
    (0x14FAF8, 0x0006343F, 0x00052C3F),  # dsra32 a2,a2,16 -> dsra32 a1,a1,16
    # r7 runtime proves horizontal orientation and 12px spacing. Move only the
    # transposed body Y base from the upper Japanese layout to the lower-screen
    # remaster-style dialogue area. The helper adds ~1px to the first fragment.
    (0x14FA78, 0x3C0342E4, 0x3C03439C),  # 114.0f -> 312.0f body Y base
    (0x14FAC8, 0x3C0341D0, 0x3C034140),  # 26.0f -> 12.0f X fragment stride
    # Unique wrapper callsite: orientation=1 is saved in s4 and reaches all four
    # child font canvases. Clear it before construction rather than patching only
    # one downstream fragment as the failed r3 experiment did.
    (0x14E96C, 0x24060001, 0x24060000),  # addiu a2,zero,1 -> addiu a2,zero,0
)


def patch_adv_horizontal_layout(raw: bytes) -> bytes:
    """Transpose only the proven ADV/DG glyph-layout constructor to English.

    The pristine constructor computes X-like ``114 - 39 * line`` and Y-like
    ``20 + 26 * (byte_position / 2)`` integer origins before passing them as
    ``a1``/``a2`` to the coordinate helper. English needs the second formula as
    X and the first as Y; because the live body fragments use the 12x12 style-1
    font, their transposed X stride is tightened from 26 to 12 pixels. Separately,
    the unique wrapper passes orientation=1
    into the ADV object constructor; that value is propagated to every child font
    canvas, and the generic callback proves nonzero advances Y while zero advances
    X. Swap the completed origins and clear that one upstream orientation flag.
    Preserve the existing two-byte glyph normalization exactly once, the FPU
    pipeline, sibling-object construction, and the reveal-progress callback.
    """

    try:
        consumers = inspect_adv_coordinate_consumers(raw)
    except ValueError as exc:
        raise ValueError(f"ADV layout preimage mismatch: {exc}") from exc

    live = [consumer for consumer in consumers if consumer.role == "dg_dialogue"]
    if len(live) != 1 or live[0].file_offset != 0x14FA60:
        raise ValueError("ADV layout preimage does not identify exactly one proven DG consumer")

    for offset, expected in _ADV_SPEAKER_ROLE_PREIMAGES:
        try:
            _require_word(raw, offset, expected)
        except ValueError as exc:
            raise ValueError(f"ADV speaker layout preimage mismatch: {exc}") from exc

    for offset, expected in _ADV_DG_BODY_STYLE_PREIMAGES:
        try:
            _require_word(raw, offset, expected)
        except ValueError as exc:
            raise ValueError(f"ADV body style layout preimage mismatch: {exc}") from exc

    result = bytearray(raw)
    for offset, expected, replacement in (*ADV_DG_LAYOUT_PATCHES, *ADV_SPEAKER_LAYOUT_PATCHES):
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
