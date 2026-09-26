from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import struct


TITLE_STRING_ARENA_START = 0x5CBDE8
TITLE_STRING_POINTER_TABLE = 0x5CBE50
_TITLE_POINTER_TABLE_PREIMAGE = (0x006CBD68, 0x006CBD78, 0x006CBD90)
_TITLE_RECORD_START = 0x5CBE60
_TITLE_RECORD_COUNT = 17
_TITLE_RECORD_SIZE = 20
_TITLE_RECORD_END = _TITLE_RECORD_START + _TITLE_RECORD_COUNT * _TITLE_RECORD_SIZE
_TITLE_RECORD_SHA256 = "fbb685e638f950a844c169bec567f7102943e4a9b7ef1916f02b2b0dcb530422"

# m_title copies exactly 17 20-byte records from VA 0x006CBDE0, then instantiates
# each record through the generic sprite constructor.  These preimages pin the
# bounded table to the live title-state constructor rather than merely parsing
# float-looking data adjacent to the strings.
_TITLE_RECORD_CONSUMER_WORDS: tuple[tuple[int, int], ...] = (
    (0x1ABDE4, 0x3C05006D),  # lui a1,0x6d
    (0x1ABDE8, 0x24A5BDE0),  # addiu a1,a1,-0x4220 -> 0x006CBDE0
    (0x1ABDF0, 0x24030055),  # copy 0x55 words = 340 bytes = 17 * 20
    (0x1ABE3C, 0x8C640000),  # group
    (0x1ABE40, 0x8C650004),  # index
    (0x1ABE44, 0xC46C0008),  # depth
    (0x1ABE54, 0x0C041F58),  # jal 0x107D60
    (0x1ABE84, 0x2A220011),  # loop bound 17
)

# Records 11/12 are the two (88,12) instances. Existing decoded-asset evidence
# identifies GP088_12 as the packed two-variant TITLE atlas, and r5 runtime
# disproved the earlier inference that these objects were menu-panel backings.
# m_title still animates them adjacent to label creation; that temporal/alignment
# correlation is recorded here without assigning false ownership. Record 13
# follows the same transition but is a distinct (88,11) asset.
_TITLE_PACKED_ART_OWNER_WORDS: tuple[tuple[int, int], ...] = (
    (0x1ABEA4, 0x8E020054),  # record 11 object
    (0x1ABEA8, 0xAC400060),  # initial scale X = 0
    (0x1ABEAC, 0x8E020058),  # record 12 object
    (0x1ABEB0, 0xAC400060),  # initial scale X = 0
    (0x1AC5B8, 0x8E050054),  # activate record 11 immediately before labels
    (0x1AC5C8, 0x0C0424A8),  # jal 0x1092A0 scale animation
    (0x1AC5D8, 0x8E050058),  # activate record 12
    (0x1AC5E8, 0x0C0424A8),  # same animation helper
    (0x1AC7D4, 0x8E020054),  # record 11
    (0x1AC7D8, 0xAC430060),  # presented scale X = 1.0
    (0x1AC7DC, 0x8E020058),  # record 12
    (0x1AC7E0, 0xAC430060),  # presented scale X = 1.0
)

# The two generic title-label anchors are created at (68,299) and (380,299),
# then their strings are passed to VA 0x29A520. That renderer advances one
# two-byte title glyph every 16 px: m_title supplies f16=0 and the label state
# adds the literal 16.0f. The pristine four-glyph Japanese labels therefore
# center at X=100 and X=412. Exact English is 8/9 glyphs, so preserving those
# centers requires X=36 and X=340 respectively. The renderer-owned group 2
# 0x8E/0x8C reveal/chrome follows the same anchor automatically.
_TITLE_LABEL_OWNER_WORDS: tuple[tuple[int, int], ...] = (
    (0x1ABF64, 0x3C024288),  # 68.0f
    (0x1ABF6C, 0x2402012B),  # 299
    (0x1ABF84, 0x3C0243BE),  # 380.0f
    (0x1ABF8C, 0x2402012B),  # 299
    (0x1AC004, 0x0C0622B4),  # jal 0x188AD0 anchor constructor
    (0x1AC628, 0x3C02006D),
    (0x1AC62C, 0x2442BDD0),  # 0x006CBDD0 pointer table
    (0x1AC63C, 0x8C460000),  # load label string pointer
    (0x1AC648, 0x0C0A6948),  # jal 0x29A520 label constructor
    (0x1AC658, 0x2A220002),  # exactly two label objects
)

# The earlier Task-4 hypothesis incorrectly classified group 2/index 0x8E as
# the static menu backing.  Full state-machine tracing proves it is a reveal
# marker: it is created separately by the label renderer and its X position at
# sprite+0x3c is incremented during state 3.  Keep this fail-closed so future
# work cannot accidentally regress to the discarded ownership hypothesis.
_TITLE_REVEAL_MARKER_WORDS: tuple[tuple[int, int], ...] = (
    (0x19A114, 0x24040002),  # group 2
    (0x19A118, 0x2405008E),  # index 0x8E
    (0x19A128, 0x0C041F58),  # sprite constructor
    (0x19A130, 0xAE420000),  # stored at label object root
    (0x19A198, 0x3C024180),  # 16.0f reveal/glyph advance component
    (0x19A1B8, 0x8E420000),  # load marker object
    (0x19A1BC, 0xC440003C),  # load marker X
    (0x19A1C0, 0x46010000),  # add reveal advance
    (0x19A1C4, 0xE440003C),  # store marker X
    (0x19A220, 0x3C024180),  # same 16.0f component for per-glyph placement
    (0x19A2D8, 0x24040002),  # per-glyph group 2
    (0x19A2DC, 0x2405008C),  # per-glyph index 0x8C
)

TITLE_NEW_GAME_X = 36.0
TITLE_LOAD_GAME_X = 340.0
_TITLE_NEW_GAME_X_OFFSET = 0x1ABF64
_TITLE_LOAD_GAME_X_OFFSET = 0x1ABF84
_TITLE_NEW_GAME_X_PREIMAGE = 0x3C024288  # lui v0,0x4288 -> 68.0f
_TITLE_LOAD_GAME_X_PREIMAGE = 0x3C0243BE  # lui v0,0x43be -> 380.0f
_TITLE_NEW_GAME_X_REPLACEMENT = 0x3C024210  # 36.0f
_TITLE_LOAD_GAME_X_REPLACEMENT = 0x3C0243AA  # 340.0f

# r5 changed these after misclassifying GP088_12 as a static menu backing. r6
# deliberately leaves them pristine because GP088_12 is packed title artwork.
_TITLE_PACKED_ART_TARGET_VECTOR_OFFSET = 0x6989C0
_TITLE_PACKED_ART_TARGET_VECTOR_PREIMAGE = struct.pack("<ff", 1.0, 1.0)
_TITLE_THIRD_OBJECT_VECTOR_CALL_OFFSET = 0x1AC600
_TITLE_SHARED_VECTOR_CALL_WORD = 0x2787D750


@dataclass(frozen=True)
class TitleLayoutRecord:
    file_offset: int
    group: int
    index: int
    values: tuple[float, ...]  # depth, X, Y


@dataclass(frozen=True)
class TitlePackedArtGeometry:
    record_offset: int
    group: int
    index: int
    texture_name: str
    x: float
    y: float
    initial_scale_x: float
    presented_scale_x: float


@dataclass(frozen=True)
class TitleRevealMarkerEvidence:
    file_offset: int
    group: int
    index: int
    x_is_mutated_during_reveal: bool


@dataclass(frozen=True)
class TitleLayoutEvidence:
    string_arena_start: int
    string_pointer_table: int
    sprite_records: tuple[TitleLayoutRecord, ...]
    packed_title_instances: tuple[TitlePackedArtGeometry, ...]
    label_anchors: tuple[tuple[float, float], ...]
    reveal_marker: TitleRevealMarkerEvidence
    unrelated_record_bytes: tuple[tuple[int, bytes], ...]
    evidence: tuple[str, ...]


def _require_words(raw: bytes, words: tuple[tuple[int, int], ...], label: str) -> None:
    for offset, expected in words:
        if offset + 4 > len(raw):
            raise ValueError(f"title layout preimage for {label} is outside executable")
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"title layout preimage mismatch for {label} at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )


def inspect_title_layout(raw: bytes) -> TitleLayoutEvidence:
    """Return fail-closed static evidence for the title menu layout owner.

    Evidence is deliberately split into three classes: the bounded m_title
    sprite table, the paired GP088_12 packed-title objects that happen to animate
    adjacent to label creation, and the label renderer's dynamic group-2/index-
    0x8E/0x8C chrome path. Runtime evidence is authoritative over the discarded
    GP088_12-as-menu-backing inference. No arbitrary floats outside the proven
    title-state region are interpreted.
    """

    if _TITLE_RECORD_END > len(raw):
        raise ValueError("title layout preimage is outside executable")

    pointers = struct.unpack_from("<III", raw, TITLE_STRING_POINTER_TABLE)
    if pointers != _TITLE_POINTER_TABLE_PREIMAGE:
        raise ValueError(
            "title layout preimage mismatch for title string pointer table: "
            f"expected {_TITLE_POINTER_TABLE_PREIMAGE!r}, got {pointers!r}"
        )

    region = raw[_TITLE_RECORD_START:_TITLE_RECORD_END]
    actual_hash = sha256(region).hexdigest()
    if actual_hash != _TITLE_RECORD_SHA256:
        raise ValueError(
            "title layout preimage mismatch for bounded m_title.c sprite records: "
            f"expected {_TITLE_RECORD_SHA256}, got {actual_hash}"
        )

    _require_words(raw, _TITLE_RECORD_CONSUMER_WORDS, "m_title record consumer")
    _require_words(raw, _TITLE_PACKED_ART_OWNER_WORDS, "packed title-art owner")
    _require_words(raw, _TITLE_LABEL_OWNER_WORDS, "title label owner")
    _require_words(raw, _TITLE_REVEAL_MARKER_WORDS, "title reveal marker")

    records: list[TitleLayoutRecord] = []
    for ordinal in range(_TITLE_RECORD_COUNT):
        offset = _TITLE_RECORD_START + ordinal * _TITLE_RECORD_SIZE
        group, index, depth, x, y = struct.unpack_from("<IIfff", raw, offset)
        if group not in (88, 91):
            raise ValueError(f"title layout preimage has unexpected group {group} at {offset:#x}")
        records.append(
            TitleLayoutRecord(
                file_offset=offset,
                group=group,
                index=index,
                values=(depth, x, y),
            )
        )

    paired = tuple(record for record in records if (record.group, record.index) == (88, 12))
    if tuple(record.file_offset for record in paired) != (0x5CBF3C, 0x5CBF50):
        raise ValueError("title layout preimage mismatch for paired GP088_12 packed-title records")

    packed_title = tuple(
        TitlePackedArtGeometry(
            record_offset=record.file_offset,
            group=record.group,
            index=record.index,
            texture_name="GRP088/GP088_12.TMX",
            x=record.values[1],
            y=record.values[2],
            initial_scale_x=0.0,
            presented_scale_x=1.0,
        )
        for record in paired
    )
    label_anchors = ((68.0, 299.0), (380.0, 299.0))

    # Keep the observed +4/+3 relationship as evidence only. r5 runtime proved
    # that proximity does not imply that GP088_12 owns the visible menu panels.
    for art, anchor in zip(packed_title, label_anchors, strict=True):
        if (anchor[0] - art.x, anchor[1] - art.y) != (4.0, 3.0):
            raise ValueError("title layout preimage mismatch for label/packed-art alignment")

    return TitleLayoutEvidence(
        string_arena_start=TITLE_STRING_ARENA_START,
        string_pointer_table=TITLE_STRING_POINTER_TABLE,
        sprite_records=tuple(records),
        packed_title_instances=packed_title,
        label_anchors=label_anchors,
        reveal_marker=TitleRevealMarkerEvidence(
            file_offset=0x19A118,
            group=2,
            index=0x8E,
            x_is_mutated_during_reveal=True,
        ),
        unrelated_record_bytes=tuple(
            (record.file_offset, raw[record.file_offset:record.file_offset + _TITLE_RECORD_SIZE])
            for record in records
            if record.file_offset not in {0x5CBF3C, 0x5CBF50}
        ),
        evidence=(
            "proven: title-state constructor copies exactly 17 20-byte GP088/GP091 records from VA 0x006CBDE0 and instantiates each through VA 0x107D60",
            "proven: records 11/12 are the only two (group 88,index 12) instances, at (64,296) and (376,296), and resolve to GRP088/GP088_12.TMX packed title art",
            "proven: existing decoded GP088_12 asset is the packed two-variant vertical title atlas; r5 runtime disproves treating its +4/+3 proximity to label anchors as menu-panel ownership",
            "proven: title labels use anchors (68,299)/(380,299), f16=0, and the label state adds a literal 16.0f per two-byte glyph",
            "proven: m_title initializes both GP088_12 packed-title instances with X scale 0, activates them immediately before constructing labels, and later presents both at X scale 1",
            "proven: group 2/index 0x8E is the moving reveal marker and per-glyph group 2/index 0x8C follows the same title-label anchor path",
        ),
    )

def patch_title_layout(raw: bytes) -> bytes:
    """Recenter the exact English title labels while preserving title artwork.

    r5 widened GP088_12 after a static correlation was mistaken for ownership.
    The decoded texture and r5 runtime contradict that inference: GP088_12 is
    packed title art. r6 therefore leaves its animation target pristine and
    changes only the two title-specific text-anchor X immediates. The label
    renderer's own group-2 reveal/per-glyph chrome is derived from those anchors,
    so text and its dynamic presentation move together without touching art.
    """

    inspect_title_layout(raw)

    if raw[
        _TITLE_PACKED_ART_TARGET_VECTOR_OFFSET:_TITLE_PACKED_ART_TARGET_VECTOR_OFFSET + 8
    ] != _TITLE_PACKED_ART_TARGET_VECTOR_PREIMAGE:
        raise ValueError("title layout preimage mismatch for packed title-art target vector")
    if struct.unpack_from("<I", raw, _TITLE_THIRD_OBJECT_VECTOR_CALL_OFFSET)[0] != _TITLE_SHARED_VECTOR_CALL_WORD:
        raise ValueError("title layout preimage mismatch for third packed-art animation call")

    for offset, expected in (
        (_TITLE_NEW_GAME_X_OFFSET, _TITLE_NEW_GAME_X_PREIMAGE),
        (_TITLE_LOAD_GAME_X_OFFSET, _TITLE_LOAD_GAME_X_PREIMAGE),
    ):
        actual = struct.unpack_from("<I", raw, offset)[0]
        if actual != expected:
            raise ValueError(
                f"title layout preimage mismatch for label anchor at {offset:#x}: "
                f"expected {expected:#010x}, got {actual:#010x}"
            )

    result = bytearray(raw)
    struct.pack_into("<I", result, _TITLE_NEW_GAME_X_OFFSET, _TITLE_NEW_GAME_X_REPLACEMENT)
    struct.pack_into("<I", result, _TITLE_LOAD_GAME_X_OFFSET, _TITLE_LOAD_GAME_X_REPLACEMENT)
    return bytes(result)
