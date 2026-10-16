"""Translate the native item-menu SELECT Details paragraph, fail-closed.

The description catalogue is separate from the card-name catalogue. The
constructor hook translates unique official English.bytes matches and retains
the native Japanese pointer for unknown records. Partial results are never
reported as full catalogue coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from pathlib import Path
from typing import Iterable

from tools.inspect_english_bytes import parse as parse_english_bytes
from tools.localization import encode_ps2_english
from tools.r67_chamber_story_text_only import Assembly, _i, _r, _jal, _float_word


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = ROOT / "local/r67-15f-item-panel-layout.elf"
CORPUS_PATH = Path(
    "/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"
)
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"

BREAK = "＠改行"
PRIMARY_DESC_VA = 0x49BEF4
ALTERNATE_DESC_VA = 0x49CB00
PRIMARY_NAME_VA = 0x491234
ALTERNATE_NAME_VA = 0x4913A0
PRIMARY_IDS = range(0, 500)
ALTERNATE_IDS = range(500, 756)
LOW_DESC_TABLE_SHA256 = "4550051ea3a1948f06ec9b594c6616a3abe2e9368d3e414d38e60e4c34af8f01"
HIGH_DESC_TABLE_SHA256 = "dfb51bf0054523ef71feb404d6d950c39c020758a742603fb4b82e4027609e38"
LOW_NAME_TABLE_SHA256 = "5280ead4ca65b89c495970984e650fbec52f51cf0ceac1d8a376995361423057"
HIGH_NAME_TABLE_SHA256 = "fba0631cf1b0b74c2e0027e3250120863f766adba9f13a19374e5e93ebde86fa"

GETTER_VA = 0x134B80
GETTER_CALL_VA = 0x115148
CONSTRUCTOR_VA = 0x189E40
CONSTRUCTOR_CALL_VA = 0x11518C
HOOK_FILE_OFFSET = 0x1520C
ORIGINAL_CONSTRUCTOR_JAL = 0x0C062790
TEXT_SETTER_VA = 0x18B120
BIAS_PRIMARY = 0xFFF80
TRANSLATION_FO = 0x803150
TRANSLATION_VA = 0x902F00
TRANSLATION_RESERVE = 0x100000

PANEL_FRAME_VA = 0x4544B0  # group 4 / sprite type 0x0B
PANEL_WIDTH = 256 - 26 - 10
PANEL_HEIGHT = 112 - 16
FONT_GLYPH_WIDTH = 16
FONT_GLYPH_HEIGHT = 18
TEXT_SCALE = 0.5
CELL_WIDTH = int(FONT_GLYPH_WIDTH * TEXT_SCALE)
ROW_HEIGHT = int(FONT_GLYPH_HEIGHT * TEXT_SCALE)
MAX_LINE_CELLS = PANEL_WIDTH // CELL_WIDTH
MAX_ROWS = PANEL_HEIGHT // ROW_HEIGHT

PERMITTED_EXISTING_RANGES = {
    "item_details_paragraph_constructor": ((HOOK_FILE_OFFSET, HOOK_FILE_OFFSET + 4),),
}
_APPEND_ONLY_RANGES = ((0x64, 0x68),)


@dataclass(frozen=True)
class DescriptionRecord:
    item_id: int
    table: str
    name_pointer: int
    description_pointer: int
    name: str
    source_text: str
    source_lines: tuple[str, ...]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _segments(source: bytes) -> list[tuple[int, int, int, int]]:
    if len(source) < 52 or source[:4] != b"\x7fELF":
        raise ValueError("item Details ELF preimage is malformed")
    phoff = struct.unpack_from("<I", source, 28)[0]
    entsize, count = struct.unpack_from("<HH", source, 42)
    if entsize != 32 or phoff + entsize * count > len(source):
        raise ValueError("item Details ELF program-header preimage is malformed")
    return [
        (offset, va, filesz, memsz)
        for index in range(count)
        for kind, offset, va, _pa, filesz, memsz, _flags, _align in [
            struct.unpack_from("<8I", source, phoff + index * entsize)
        ]
        if kind == 1
    ]


def _va_to_offset(source: bytes, address: int) -> int | None:
    for offset, base, filesz, _memsz in _segments(source):
        if base <= address < base + filesz:
            return offset + address - base
    return None


def _read_string(source: bytes, pointer: int, *, maximum: int = 4096) -> str | None:
    offset = _va_to_offset(source, pointer)
    if offset is None:
        return None
    end = source.find(b"\0", offset, min(len(source), offset + maximum))
    if end < 0:
        return None
    try:
        return source[offset:end].decode("cp932")
    except UnicodeDecodeError:
        return None


def _table_offset(source: bytes, address: int) -> int:
    offset = _va_to_offset(source, address)
    if offset is None:
        raise ValueError(f"unmapped item Details table {address:#x}")
    return offset


def _verify_catalogue_owners(source: bytes) -> None:
    owners = (
        (PRIMARY_DESC_VA, 500 * 4, LOW_DESC_TABLE_SHA256, "primary description"),
        (ALTERNATE_DESC_VA + 500 * 4, 37 * 4, HIGH_DESC_TABLE_SHA256, "alternate description"),
        (PRIMARY_NAME_VA, 500 * 4, LOW_NAME_TABLE_SHA256, "primary item-name"),
        (ALTERNATE_NAME_VA + 500 * 4, 37 * 4, HIGH_NAME_TABLE_SHA256, "alternate item-name"),
    )
    for address, length, expected, label in owners:
        offset = _table_offset(source, address)
        actual = _sha(source[offset:offset + length])
        if actual != expected:
            raise ValueError(f"{label} catalogue preimage mismatch at {address:#x}")


def _verify_native_owner(source: bytes) -> None:
    if struct.unpack_from("<I", source, HOOK_FILE_OFFSET)[0] != ORIGINAL_CONSTRUCTOR_JAL:
        raise ValueError("Details paragraph constructor hook preimage mismatch")
    if struct.unpack_from("<I", source, HOOK_FILE_OFFSET + 4)[0] != 0:
        raise ValueError("Details paragraph constructor delay slot changed")
    if struct.unpack_from("<I", source, GETTER_CALL_VA - BIAS_PRIMARY)[0] != 0x0C04D2E0:
        raise ValueError("native Details description-getter callsite changed")
    getter_words = struct.unpack_from("<8I", source, GETTER_VA - BIAS_PRIMARY)
    if getter_words != (
        0x3083FFFF, 0x3402FFFF, 0x14620005, 0, 0x3C02004A, 0x8C42BEF0,
        0x10000010, 0,
    ):
        raise ValueError("native Details description getter preimage changed")
    calls = []
    for offset in range(0, len(source) - 3, 4):
        word = struct.unpack_from("<I", source, offset)[0]
        if word >> 26 == 3 and ((word & 0x03FFFFFF) << 2) == GETTER_VA:
            calls.append(offset)
    if calls != [GETTER_CALL_VA - BIAS_PRIMARY]:
        raise ValueError(f"native Details getter caller set changed: {calls!r}")

    # Group 4's type-0x0B frame is a 256x112 native panel. The constructor
    # places text at (+26,+16), and its right bound is panelX+width-10.
    group4 = _table_offset(source, 0x485250)
    if struct.unpack_from("<I", source, group4)[0] != 0x4811A0:
        raise ValueError("native Details panel group-4 catalogue changed")
    frame_entry = _table_offset(source, 0x4811A0 + 0x0B * 8)
    frame_va, frames = struct.unpack_from("<II", source, frame_entry)
    if frame_va != PANEL_FRAME_VA or frames != 1:
        raise ValueError("native Details panel type-0x0B frame changed")
    frame = _table_offset(source, frame_va)
    if struct.unpack_from("<HH", source, frame)[1] != 8:
        raise ValueError("native Details panel background resource changed")
    width, height = struct.unpack_from("<2f", source, frame + 4)
    if (width, height) != (256.0, 112.0):
        raise ValueError("native Details panel geometry changed")


def collect_catalogue(source: bytes) -> list[DescriptionRecord]:
    """Read all valid name/description pairs reached by the native getter."""
    _verify_catalogue_owners(source)
    _verify_native_owner(source)
    records: list[DescriptionRecord] = []
    name_sets = (
        ("primary", PRIMARY_IDS, PRIMARY_NAME_VA, PRIMARY_DESC_VA),
        ("alternate", ALTERNATE_IDS, ALTERNATE_NAME_VA, ALTERNATE_DESC_VA),
    )
    for table_name, ids, name_base, description_base in name_sets:
        name_table = _table_offset(source, name_base)
        description_table = _table_offset(source, description_base)
        for item_id in ids:
            name_pointer = struct.unpack_from("<I", source, name_table + item_id * 4)[0]
            description_pointer = struct.unpack_from("<I", source, description_table + item_id * 4)[0]
            name = _read_string(source, name_pointer) if name_pointer else None
            description = _read_string(source, description_pointer) if description_pointer else None
            if name is None:
                continue
            if description_pointer == 0 or description is None:
                # The pinned name table continues beyond the description
                # catalogue. Its remaining description-table words are null or
                # adjacent data, not mapped native text pointers.
                continue
            if not description or BREAK not in description:
                raise ValueError(f"malformed item Details paragraph for id {item_id}")
            parts = description.split(BREAK)
            lines = tuple(
                line + (BREAK if index < len(parts) - 1 else "")
                for index, line in enumerate(parts)
                if line
            )
            records.append(DescriptionRecord(
                item_id, table_name, name_pointer, description_pointer,
                name, description, lines,
            ))
    return records


def load_official_rows(path: Path = CORPUS_PATH) -> list[tuple[str, str, int]]:
    data = path.read_bytes()
    if _sha(data) != CORPUS_SHA256:
        raise ValueError("official English.bytes SHA-256 mismatch")
    return parse_english_bytes(path)


def map_official_descriptions(
    records: Iterable[DescriptionRecord],
    corpus_rows: Iterable[tuple[str, str, int]],
) -> tuple[dict[int, str], list[DescriptionRecord]]:
    records = list(records)
    line_map = map_official_lines(records, corpus_rows)
    translations: dict[int, str] = {}
    unresolved: list[DescriptionRecord] = []
    for record in records:
        values = line_map[record.item_id]
        if any(value is None for value in values):
            unresolved.append(record)
            continue
        translations[record.item_id] = _join_official_lines(
            [value for value in values if value is not None]
        )
    return translations, unresolved


def map_official_lines(
    records: Iterable[DescriptionRecord],
    corpus_rows: Iterable[tuple[str, str, int]],
) -> dict[int, tuple[str | None, ...]]:
    """Map each source row independently; None means retain the source row."""
    by_key: dict[str, list[str]] = {}
    for key, value, _offset in corpus_rows:
        by_key.setdefault(key, []).append(value)
    output: dict[int, tuple[str | None, ...]] = {}
    for record in records:
        if not record.source_lines:
            # Four catalogue IDs intentionally point to the same all-break
            # empty paragraph. They contain no Japanese wording to translate.
            output[record.item_id] = ()
            continue
        output_lines: list[str | None] = []
        for source_key in record.source_lines:
            matches = by_key.get(source_key, [])
            if len(matches) != 1:
                output_lines.append(None)
                continue
            value = matches[0]
            if source_key.endswith(BREAK) and not value.endswith(BREAK):
                output_lines.append(None)
                continue
            output_lines.append(value[:-len(BREAK)] if value.endswith(BREAK) else value)
        output[record.item_id] = tuple(output_lines)
    return output


def _join_official_lines(lines: list[str]) -> str:
    """Flatten corpus row markers without dropping official words/punctuation."""
    translated = ""
    for line in lines:
        if not line:
            continue
        if translated and line[:1] not in ",.;:!?)]}”’\"":
            translated += " "
        translated += line
    return translated


def render_native_description(
    record: DescriptionRecord,
    mapped_lines: tuple[str | None, ...],
) -> tuple[tuple[str, bool], ...]:
    """Return wrapped `(row, is_official_English)` native text rows.

    Unmapped Japanese source rows remain byte-for-byte text-identical. Adjacent
    exact official rows are joined before wrapping, while source rows with no
    official key remain separate native rows.
    """
    output: list[tuple[str, bool]] = []
    english_run: list[str] = []

    def flush_english() -> None:
        if english_run:
            output.extend((line, True) for line in wrap_description(_join_official_lines(english_run)))
            english_run.clear()

    for source_key, translated in zip(record.source_lines, mapped_lines):
        if translated is not None:
            english_run.append(translated)
            continue
        flush_english()
        original = source_key.removesuffix(BREAK)
        if original:
            if len(original) > MAX_LINE_CELLS:
                raise ValueError(f"untranslated Japanese row exceeds native panel width: {record.item_id}")
            output.append((original, False))
    flush_english()
    if len(output) > MAX_ROWS:
        raise ValueError(
            f"item Details {record.item_id} needs {len(output)} rows; native panel holds {MAX_ROWS}"
        )
    return tuple(output)


def wrap_description(text: str) -> list[str]:
    """Wrap by complete English words using the native 8px cell / 9px row."""
    if not text.strip():
        return []
    words = text.split()
    if not words:
        raise ValueError("item Details translation has no words")
    lines: list[str] = []
    current = ""
    for word in words:
        if len(word) > MAX_LINE_CELLS:
            raise ValueError(f"item Details word exceeds native line width: {word!r}")
        candidate = f"{current} {word}" if current else word
        if current and len(candidate) > MAX_LINE_CELLS:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > MAX_ROWS:
        raise ValueError(
            f"item Details paragraph needs {len(lines)} rows; native panel holds {MAX_ROWS}"
        )
    return lines


def _build_helper(pointer_table_va: int) -> bytes:
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x20))            # addiu sp,sp,-32
    m.emit(_i(43, 29, 31, 0))               # sw ra,0(sp)
    m.emit(_i(43, 29, 16, 4))               # sw s0,4(sp)
    m.emit(_r(0, 8, 11, 0, 37))              # t3 = original Japanese getter result
    m.emit(_i(37, 18, 8, 0x1DC))            # lhu t0,item-id(s2)
    m.emit(_i(11, 8, 12, 756))              # sltiu t4,t0,756
    m.branch(4, 12, 0, "preserve")
    m.emit(0)
    m.emit(_r(0, 8, 9, 2, 0))               # sll t1,t0,2
    m.const(10, pointer_table_va)            # t2 = translated string-pointer table
    m.emit(_r(10, 9, 10, 0, 33))            # addu t2,t2,t1
    m.emit(_i(35, 10, 8, 0))                # lw t0,0(t2)
    m.branch(5, 8, 0, "translated")
    m.emit(0)
    m.label("preserve")
    m.emit(_r(11, 0, 8, 0, 37))              # zero slot: retain original Japanese
    m.label("translated")
    m.emit(_jal(CONSTRUCTOR_VA))
    m.emit(0)
    m.emit(_r(2, 0, 16, 0, 37))             # s0 = original constructor result
    m.branch(4, 16, 0, "return")
    m.emit(0)
    m.emit(_r(16, 0, 4, 0, 37))             # a0 = text handle
    m.const(8, _float_word(TEXT_SCALE))
    m.emit((17 << 26) | (4 << 21) | (8 << 16) | (12 << 11))  # mtc1 t0,f12
    m.emit((17 << 26) | (4 << 21) | (8 << 16) | (13 << 11))  # mtc1 t0,f13
    m.emit(_jal(TEXT_SETTER_VA))
    m.emit(0)
    m.label("return")
    m.emit(_r(16, 0, 2, 0, 37))             # preserve native handle in v0
    m.emit(_i(35, 29, 16, 4))               # lw s0,4(sp)
    m.emit(_i(35, 29, 31, 0))               # lw ra,0(sp)
    m.emit(_i(9, 29, 29, 0x20))
    m.emit(_r(31, 0, 0, 0, 8))
    m.emit(0)
    return m.done()


def _build_payload(
    source: bytes,
    rendered: dict[int, tuple[tuple[str, bool], ...]],
) -> tuple[bytes, dict]:
    data = bytearray(source)
    while len(data) & 3:
        data.append(0)
    strings_va: dict[int, int] = {}
    for item_id in sorted(rendered):
        lines = rendered[item_id]
        if not any(is_english for _line, is_english in lines):
            continue
        encoded_lines = [
            encode_ps2_english(line) if is_english else line.encode("cp932")
            for line, is_english in lines
        ]
        encoded = BREAK.encode("cp932").join(encoded_lines) + b"\0"
        strings_va[item_id] = TRANSLATION_VA + len(data) - TRANSLATION_FO
        data.extend(encoded)
        while len(data) & 3:
            data.append(0)
    table_offset = len(data)
    # Reserve the entire bounded index first, then fill sparse valid IDs.
    data.extend(b"\0" * (756 * 4))
    for item_id, pointer in strings_va.items():
        struct.pack_into("<I", data, table_offset + item_id * 4, pointer)
    table_va = TRANSLATION_VA + table_offset - TRANSLATION_FO
    while len(data) & 3:
        data.append(0)
    helper_va = TRANSLATION_VA + len(data) - TRANSLATION_FO
    helper = _build_helper(table_va)
    data.extend(helper)
    while len(data) & 3:
        data.append(0)
    if len(data) - TRANSLATION_FO > TRANSLATION_RESERVE:
        raise ValueError("item Details translation PT_LOAD reservation exceeded")
    return bytes(data), {
        "translation_table_va": hex(table_va),
        "helper_va": hex(helper_va),
        "helper_bytes": len(helper),
        "translated_strings": len(strings_va),
        "maximum_wrapped_rows": max((len(lines) for lines in rendered.values()), default=0),
    }


def apply(source: bytes, *, corpus_path: Path = CORPUS_PATH) -> tuple[bytes, dict]:
    """Apply official exact matches and preserve all unmapped native text.

    No whole-input hash is used: other approved components may have appended
    payload or changed their own hooks before this transform. This component
    pins its own catalogue and native-consumer preimages independently.
    """
    _verify_catalogue_owners(source)
    _verify_native_owner(source)
    rows = load_official_rows(corpus_path)
    records = collect_catalogue(source)
    name_only_ids: list[int] = []
    for table_name, ids, name_base, description_base in (
        ("primary", PRIMARY_IDS, PRIMARY_NAME_VA, PRIMARY_DESC_VA),
        ("alternate", ALTERNATE_IDS, ALTERNATE_NAME_VA, ALTERNATE_DESC_VA),
    ):
        name_table = _table_offset(source, name_base)
        description_table = _table_offset(source, description_base)
        for item_id in ids:
            name_pointer = struct.unpack_from("<I", source, name_table + item_id * 4)[0]
            description_pointer = struct.unpack_from("<I", source, description_table + item_id * 4)[0]
            if (name_pointer and _read_string(source, name_pointer) is not None
                    and _read_string(source, description_pointer) is None):
                name_only_ids.append(item_id)
    line_map = map_official_lines(records, rows)
    translations, unresolved = map_official_descriptions(records, rows)
    unresolved_ids = sorted(record.item_id for record in unresolved)
    partial_ids = sorted(
        record.item_id for record in unresolved
        if any(value is not None for value in line_map[record.item_id])
    )
    fully_japanese_ids = sorted(set(unresolved_ids) - set(partial_ids))
    preserved_japanese_lines = {
        str(record.item_id): [
            source_key for source_key, translated in zip(
                record.source_lines, line_map[record.item_id]
            ) if translated is None
        ]
        for record in unresolved
    }
    rendered = {
        record.item_id: render_native_description(record, line_map[record.item_id])
        for record in records
    }
    line_total = sum(len(record.source_lines) for record in records)
    exact_line_total = sum(
        translated is not None
        for values in line_map.values()
        for translated in values
    )
    empty_native_records = sum(not record.source_lines for record in records)
    report: dict = {
        "source_bytes": len(source),
        "source_sha256": _sha(source),
        "official_corpus_path": str(corpus_path),
        "official_corpus_sha256": CORPUS_SHA256,
        "valid_catalogue_records": len(records),
        "name_only_without_description": len(name_only_ids),
        "name_only_item_ids": name_only_ids,
        "primary_records": sum(record.table == "primary" for record in records),
        "alternate_records": sum(record.table == "alternate" for record in records),
        "fully_resolved_records": len(translations),
        "official_exact_records": len(translations) - empty_native_records,
        "empty_native_records": empty_native_records,
        "unresolved_records": len(unresolved),
        "unresolved_item_ids": unresolved_ids,
        "official_exact_source_rows": exact_line_total,
        "source_rows": line_total,
        "partially_translated_records": partial_ids,
        "fully_japanese_preserved_item_ids": fully_japanese_ids,
        "preserved_native_japanese_item_ids": unresolved_ids,
        "preserved_native_japanese_source_rows": preserved_japanese_lines,
        "preserved_native_japanese_source_row_count": sum(map(len, preserved_japanese_lines.values())),
        "native_getter_va": hex(GETTER_VA),
        "native_getter_call_va": hex(GETTER_CALL_VA),
        "native_constructor_va": hex(CONSTRUCTOR_VA),
        "native_constructor_call_va": hex(CONSTRUCTOR_CALL_VA),
        "native_panel_sprite": {"group": 4, "type": "0x0b", "width": 256, "height": 112},
        "text_bounds_pixels": {"width": PANEL_WIDTH, "height": PANEL_HEIGHT},
        "native_font_cell_pixels": {"width": FONT_GLYPH_WIDTH, "height": FONT_GLYPH_HEIGHT},
        "instance_scale": TEXT_SCALE,
        "wrapped_rows_fit": all(len(lines) <= MAX_ROWS for lines in rendered.values()),
        "all_catalogue_descriptions_translated": not unresolved,
        "permitted_existing_ranges": {
            key: [[hex(start), hex(end)] for start, end in ranges]
            for key, ranges in PERMITTED_EXISTING_RANGES.items()
        },
        "unresolved_runtime_assumptions": [],
        "gameplay_approved": False,
    }
    payload_bytes, payload = _build_payload(source, rendered)
    data = bytearray(payload_bytes)
    jump = _jal(payload["helper_va"] and int(payload["helper_va"], 16))
    struct.pack_into("<I", data, HOOK_FILE_OFFSET, jump)
    struct.pack_into("<I", data, 0x64, len(data) - TRANSLATION_FO)
    changed = [
        offset for offset, (before, after) in enumerate(zip(source, data[:len(source)]))
        if before != after
    ]
    allowed = {offset for ranges in PERMITTED_EXISTING_RANGES.values()
               for start, end in ranges for offset in range(start, end)}
    allowed.update(range(*_APPEND_ONLY_RANGES[0]))
    if set(changed) - allowed:
        raise ValueError(f"unexpected existing ELF edits: {set(changed) - allowed}")
    report.update(payload)
    report.update({
        "status": "PARTIAL_OFFICIAL_SUBSET" if unresolved else "PATCHED_ALL_OFFICIAL_DESCRIPTIONS",
        "release_eligibility": "PARTIAL_NOT_FULL_SCOPE" if unresolved else "FULL_CATALOGUE_COVERED",
        "preserved_native_japanese_item_ids": unresolved_ids,
        "actionable_blocker": (
            "Find exact official English keys for the unresolved item IDs in the PS4 source; "
            "until then their original Japanese description pointers are retained."
            if unresolved else None
        ),
        "hook_jump_word": hex(jump),
        "result_sha256": _sha(data),
        "result_bytes": len(data),
        "existing_elf_changed_offsets": [hex(offset) for offset in changed],
    })
    return data, report
