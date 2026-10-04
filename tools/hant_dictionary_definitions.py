from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
import struct
import unicodedata

from tools.hant_content_data import HANT_DICTIONARY_TERM_DATA
from tools.hant_layout import measured_hant_cells


_MAIN_FILE_START = 0x80
_MAIN_FILE_END = 0x699200
_MAIN_VADDR = 0x00100000
_DICTIONARY_MODE = 1
_DICTIONARY_TEXT_ROOT_VA = 0x006CBAC0
_DICTIONARY_CATEGORIES = ("a", "k", "s", "t", "n", "h", "m", "y", "r", "w")
_BLANK_VA = 0x00795FB8
_EOF_VA = 0x00795FBC
_MAX_ROWS = 128
_MAX_STRING_BYTES = 1024
DICTIONARY_DEFINITION_MAX_CELLS = 21


@dataclass(frozen=True)
class DictionaryDefinitionSource:
    key: str
    category_index: int
    term_index: int
    descriptor_offset: int
    source_table_offset: int
    source_row_count: int
    source_sha256: str


@dataclass(frozen=True)
class OfficialDictionaryDefinition:
    key: str
    descriptor_offset: int
    source_table_offset: int
    source_row_count: int
    source_sha256: str
    english_rows: tuple[str, ...]
    provenance: str = "official_exact_reflow"


def _va_to_file(va: int) -> int | None:
    offset = _MAIN_FILE_START + (va - _MAIN_VADDR)
    if _MAIN_FILE_START <= offset < _MAIN_FILE_END:
        return offset
    return None


def _read_u32(raw: bytes, offset: int, *, owner: str) -> int:
    if offset < _MAIN_FILE_START or offset + 4 > min(len(raw), _MAIN_FILE_END):
        raise ValueError(f"{owner} pointer is outside the main executable: {offset:#x}")
    return struct.unpack_from("<I", raw, offset)[0]


def _read_cp932_c_string_bytes(raw: bytes, offset: int) -> bytes:
    if offset < _MAIN_FILE_START or offset >= min(len(raw), _MAIN_FILE_END):
        raise ValueError(f"Dictionary source string is outside the main executable: {offset:#x}")
    end = raw.find(b"\x00", offset, min(len(raw), _MAIN_FILE_END, offset + _MAX_STRING_BYTES))
    if end < 0:
        raise ValueError(f"Dictionary source string lacks NUL terminator: {offset:#x}")
    payload = raw[offset:end + 1]
    try:
        payload[:-1].decode("cp932")
    except UnicodeDecodeError as exc:
        raise ValueError(f"Dictionary source string is not CP932 at {offset:#x}") from exc
    return payload


def _read_cp932_c_string(raw: bytes, offset: int) -> str:
    return _read_cp932_c_string_bytes(raw, offset)[:-1].decode("cp932")


def _category_descriptor_base(raw: bytes, category_index: int) -> int:
    root_offset = _va_to_file(_DICTIONARY_TEXT_ROOT_VA)
    if root_offset is None:
        raise ValueError("Dictionary text root is outside the main executable")
    mode_table_va = _read_u32(raw, root_offset + _DICTIONARY_MODE * 4, owner="Dictionary mode table")
    mode_table_offset = _va_to_file(mode_table_va)
    if mode_table_offset is None:
        raise ValueError("Dictionary mode table targets outside the main executable")
    category_table_va = _read_u32(raw, mode_table_offset + category_index * 4, owner="Dictionary category table")
    category_table_offset = _va_to_file(category_table_va)
    if category_table_offset is None:
        raise ValueError("Dictionary category descriptor table targets outside the main executable")
    return category_table_offset


def _source_row_count(raw: bytes, source_table_offset: int) -> int:
    for row_index in range(_MAX_ROWS + 1):
        value = _read_u32(raw, source_table_offset + row_index * 4, owner="Dictionary definition table")
        if value == _EOF_VA:
            return row_index
        if value != _BLANK_VA and _va_to_file(value) is None:
            raise ValueError(
                f"Dictionary definition row targets outside executable: table={source_table_offset:#x}, "
                f"row={row_index}, va={value:#x}"
            )
    raise ValueError(f"Dictionary definition table lacks EOF within {_MAX_ROWS} rows: {source_table_offset:#x}")


def definition_source_fingerprint(raw: bytes, source_table_offset: int, source_row_count: int) -> str:
    """Hash a pristine definition table plus every referenced source C-string.

    The table words preserve blank positions and pointer identity. Length-prefixing
    the referenced CP932 strings keeps the fingerprint unambiguous while allowing
    translated tables to have a different row count after English reflow.
    """

    table_size = (source_row_count + 1) * 4
    if source_table_offset < _MAIN_FILE_START or source_table_offset + table_size > min(len(raw), _MAIN_FILE_END):
        raise ValueError(f"Dictionary source table is outside the main executable: {source_table_offset:#x}")
    table = raw[source_table_offset:source_table_offset + table_size]
    words = struct.unpack(f"<{source_row_count + 1}I", table)
    if words[-1] != _EOF_VA:
        raise ValueError(f"Dictionary source table EOF mismatch: {source_table_offset:#x}")

    digest = sha256()
    digest.update(table)
    for pointer in words[:-1]:
        if pointer == _BLANK_VA:
            continue
        source_offset = _va_to_file(pointer)
        if source_offset is None:
            raise ValueError(f"Dictionary source row targets outside main executable: {pointer:#x}")
        payload = _read_cp932_c_string_bytes(raw, source_offset)
        digest.update(struct.pack("<I", len(payload)))
        digest.update(payload)
    return digest.hexdigest()


def inventory_dictionary_definition_sources(raw: bytes) -> tuple[DictionaryDefinitionSource, ...]:
    if len(raw) < _MAIN_FILE_END:
        raise ValueError("Dictionary inventory requires the complete main executable")

    terms_by_category: dict[str, list[tuple[str, int, int, str, str]]] = {key: [] for key in _DICTIONARY_CATEGORIES}
    for record in HANT_DICTIONARY_TERM_DATA:
        category = record[0].split("_")[1]
        if category not in terms_by_category:
            raise ValueError(f"Unknown Dictionary category in term manifest: {record[0]}")
        terms_by_category[category].append(record)

    sources: list[DictionaryDefinitionSource] = []
    for category_index, category in enumerate(_DICTIONARY_CATEGORIES):
        descriptor_base = _category_descriptor_base(raw, category_index)
        for term_index, term in enumerate(terms_by_category[category]):
            descriptor_offset = descriptor_base + term_index * 4
            source_table_va = _read_u32(raw, descriptor_offset, owner="Dictionary definition descriptor")
            source_table_offset = _va_to_file(source_table_va)
            if source_table_offset is None:
                raise ValueError(f"Dictionary definition descriptor targets outside main executable: {term[0]}")
            source_row_count = _source_row_count(raw, source_table_offset)
            sources.append(
                DictionaryDefinitionSource(
                    key=term[0],
                    category_index=category_index,
                    term_index=term_index,
                    descriptor_offset=descriptor_offset,
                    source_table_offset=source_table_offset,
                    source_row_count=source_row_count,
                    source_sha256=definition_source_fingerprint(raw, source_table_offset, source_row_count),
                )
            )

    if len(sources) != len(HANT_DICTIONARY_TERM_DATA) or len(sources) != 208:
        raise ValueError(f"Expected 208 Dictionary definitions, found {len(sources)}")
    if len({source.key for source in sources}) != len(sources):
        raise ValueError("Dictionary definition keys are not unique")
    if len({source.descriptor_offset for source in sources}) != len(sources):
        raise ValueError("Dictionary definition descriptor owners are not unique")
    return tuple(sources)


def _normalize_official_text(value: str) -> str:
    value = value.replace("\u3000", " ").replace("—", "-")
    value = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    value = " ".join(value.split())
    try:
        value.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError(f"Official Dictionary text contains unsupported non-ASCII text: {value!r}") from exc
    return value


def _join_official_fragments(fragments: list[str]) -> str:
    joined = ""
    for fragment in fragments:
        fragment = _normalize_official_text(fragment)
        if not fragment:
            continue
        if not joined:
            joined = fragment
        elif joined.endswith("-"):
            joined += fragment
        else:
            joined += " " + fragment
    return joined


def _wrap_official_paragraph(paragraph: str) -> tuple[str, ...]:
    """Wrap ASCII text deterministically without stdlib-version drift.

    We prefer the last space within the 21-cell body width. If a single token is
    wider than the page, it is hard-split at the cell boundary. Rows are separate
    display strings, so a hard split does not introduce a visible space.
    """

    remaining = paragraph.strip()
    if not remaining:
        return ("",)

    rows: list[str] = []
    width = DICTIONARY_DEFINITION_MAX_CELLS
    while measured_hant_cells(remaining) > width:
        # Official normalized Dictionary text is ASCII, so string indexes and
        # display-cell indexes are identical here.
        cut = remaining.rfind(" ", 0, width + 1)
        if cut <= 0:
            cut = width
        row = remaining[:cut]
        remaining = remaining[cut:]
        if remaining.startswith(" "):
            remaining = remaining[1:]
        if not row:
            raise ValueError("Dictionary deterministic wrapper produced an empty row")
        rows.append(row)

    if remaining:
        rows.append(remaining)

    for row in rows:
        if measured_hant_cells(row) > width:
            raise ValueError(f"Reflowed Dictionary row exceeds H.A.N.T width: {row!r}")
    return tuple(rows)


def _reflow_official_rows(values: tuple[str | None, ...]) -> tuple[str, ...]:
    # The PS2 Japanese tables use blank rows as layout separators, but the
    # remaster's English fragments do not preserve the same sentence boundaries.
    # Carrying every Japanese separator across can split an English sentence in
    # half (for example "world heritage" / "city"). Keep only the structural
    # title/body separator: the first nonblank row is the term title and every
    # remaining nonblank official fragment is one continuous English body.
    normalized = [
        _normalize_official_text(value)
        for value in values
        if value is not None and _normalize_official_text(value)
    ]
    if not normalized:
        raise ValueError("Dictionary definition reflow produced no English rows")

    title_rows = _wrap_official_paragraph(normalized[0])
    if len(normalized) == 1:
        return title_rows

    body = _join_official_fragments(normalized[1:])
    return (*title_rows, "", *_wrap_official_paragraph(body))


def build_official_dictionary_definitions(
    raw: bytes,
    english_rows: tuple[tuple[str, str, int], ...],
) -> tuple[OfficialDictionaryDefinition, ...]:
    by_key: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, value, offset in english_rows:
        by_key[key].append((value, offset))

    definitions: list[OfficialDictionaryDefinition] = []
    exact_nonblank_rows = 0
    for source in inventory_dictionary_definition_sources(raw):
        values: list[str | None] = []
        for row_index in range(source.source_row_count):
            pointer = _read_u32(raw, source.source_table_offset + row_index * 4, owner="Dictionary definition row")
            if pointer == _BLANK_VA:
                values.append(None)
                continue
            source_offset = _va_to_file(pointer)
            if source_offset is None:
                raise ValueError(f"Dictionary definition source row targets outside executable: {source.key}/{row_index}")
            source_text = _read_cp932_c_string(raw, source_offset)
            matches = by_key.get(source_text, ())
            if len(matches) != 1:
                raise ValueError(
                    f"Dictionary definition official match must be unique: {source.key}/{row_index}; "
                    f"matches={len(matches)}"
                )
            values.append(matches[0][0])
            exact_nonblank_rows += 1

        english = _reflow_official_rows(tuple(values))
        definitions.append(
            OfficialDictionaryDefinition(
                key=source.key,
                descriptor_offset=source.descriptor_offset,
                source_table_offset=source.source_table_offset,
                source_row_count=source.source_row_count,
                source_sha256=source.source_sha256,
                english_rows=english,
            )
        )

    if len(definitions) != 208:
        raise ValueError(f"Expected 208 official Dictionary definitions, got {len(definitions)}")
    if exact_nonblank_rows != 2073:
        raise ValueError(f"Expected 2073 unique official Dictionary row matches, got {exact_nonblank_rows}")
    return tuple(definitions)
