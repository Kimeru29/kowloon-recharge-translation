"""Complete r67 H.A.N.T. Help body localization after append-only P0 executable.

Every unpromoted page has a hashed pristine descriptor, source table and icon
metadata. Original source rows and original ELF code remain untouched.
Official PS4 English is looked up from the user's own extraction at build time.
Only the 12 unmatched *unique* Japanese controller instructions are semantic.
All output rows are <=28 two-byte PS2 font cells and page lengths do not grow.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import textwrap
from typing import Any

from tools.first_save_help_inventory import inventory, _BLANK, _EOF, _offset
from tools.hant_layout import HANT_LAYOUT_PROFILE
from tools.hant_ui import HantHelpBody, _relocated_help_body_metadata
from tools.inspect_english_bytes import parse as parse_english
from tools.localization import encode_ps2_english

_R66_SRC_BASE = 0x100000
_R66_OFFSET = 0x80
_SEG_PH_OFFSET = 0x54
_SEGMENT_VA = 0x902F00
_MAX_CELLS = HANT_LAYOUT_PROFILE.max_cells

# Local-only PS2 controller strings deliberately absent from the official
# PS4 English.text asset as exact standalone keys. Indexed by the immutable
# pristine source file offset; these are human-auditable semantic mappings.
SEMANTIC_CONTROLS: dict[int, str] = {
    0x5c2f90: "Move D-pad left/right to choose.",
    0x5c30b0: "While in ADV, press START to",
    0x5c3470: "Use the directional pad to",
    0x5c3620: "(Press START to",
    0x5c57b0: "D-pad left/right: rotate.",
    0x5c5950: "Use D-pad to move the switch.",
    0x5c7350: "D-pad up/down:",
    0x5c9290: "After class, press START to",
    0x5ca430: "2. Move cursor right using D-pad.",
    0x5cb230: "1. D-pad up/down: select stat.",
    0x5cb2e0: "2. D-pad left/right: points.",
    0x5cb350: "Press START to confirm.",
}

# PS4 English repeats a long explanation three times beside three separate
# combat-button icons. Keep three commands but compact the same instruction
# so each fits its original icon-tied page geometry (semantic exception).
COMPACT_HELP_ROWS = {
    "entering_battle": {
        0x5c64f0: "Ready weapon; press again: fire",
        0x5c6520: "Switch search/fight stance",
    },
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _raw_rows(src: bytes, page: dict[str, Any]) -> list[tuple[int, bytes] | None]:
    rows: list[tuple[int, bytes] | None] = []
    for idx in range(page["rows"]):
        va = struct.unpack_from("<I", src, page["source_table_offset"] + idx*4)[0]
        if va == _BLANK:
            rows.append(None)
            continue
        ofs = _offset(va, src)
        end = src.find(b"\x00", ofs, ofs + 384)
        if end == -1:
            raise ValueError(f"Unterminated H.A.N.T row: {page['key']} {idx}")
        rows.append((ofs, src[ofs:end+1]))
    term = struct.unpack_from("<I", src, page["source_table_offset"] + page["rows"]*4)[0]
    if term != _EOF:
        raise ValueError(f"Help EOF mismatch: {page['key']}")
    return rows


def _metadata(src: bytes, page: dict[str, Any]) -> tuple[tuple[int, int, int, int], ...]:
    offset = page["source_metadata_offset"]
    return tuple(struct.unpack_from("<4h", src, offset + i*8)
                 for i in range(page["icon_records"]))


def manifest_from_owned_sources(
    src: bytes, english: list[tuple[str, str, int]], corpus_sha: str
) -> dict:
    state = inventory(src, english)
    pages = []
    for page in state["pages"]:
        if page["existing_r66_english"]:
            continue
        raw_rows = _raw_rows(src, page)
        metadata = _metadata(src, page)
        end = page["source_table_offset"] + (page["rows"] + 1)*4
        met_end = page["source_metadata_offset"] + (page["icon_records"] + 1)*8
        pages.append({
            "key": page["key"], "category": page["category"], "index": page["index"],
            "descriptor_offset": page["descriptor_offset"],
            "metadata_descriptor_offset": page["metadata_descriptor_offset"],
            "source_table_offset": page["source_table_offset"],
            "source_metadata_offset": page["source_metadata_offset"],
            "rows": page["rows"], "icon_records": page["icon_records"],
            "table_sha256": _sha(src[page["source_table_offset"]:end]),
            "metadata_sha256": _sha(src[page["source_metadata_offset"]:met_end]),
            "row_source_sha256": [
                None if row is None else _sha(row[1])
                for row in raw_rows
            ],
        })
    return {
        "schema_version": 1, "pristine_elf_sha256": _sha(src),
        "official_ps4_english_sha256": corpus_sha,
        "p0_elf_sha256": "cd5441d3c408ca31d41e682be5bd4c0a8dec723cb481b1896be071822fd3be4f",
        "approved_pages": len(pages), "max_english_cells": _MAX_CELLS,
        "pages": pages,
    }


def _normalized_english(text: str) -> str:
    text = " ".join(text.split())
    if len(text) >= 20 and set(text) <= set("-_"):
        return "-" * 20
    return text.replace("@D", "").strip()


def _icon_reservations(
    page: dict[str, Any], metadata: tuple[tuple[int, int, int, int], ...]
) -> tuple[list[set[int]], tuple[tuple[int, int, int, int], ...]]:
    """Map native controller sprites onto proven 12px/16px Help row grid.

    In r66 mode-4 the text glyph advance is 12px and line spacing 16px.
    Original sprite metadata describes the same rows using 16px/21px.  We
    reuse the accepted layout transform and reserve 5 cells at its new X/Y.
    """
    shadow = HantHelpBody(
        key=page["key"], mode=4, category_index=page["category"],
        topic_index=page["index"], descriptor_offset=page["descriptor_offset"],
        source_table_offset=page["source_table_offset"],
        metadata_descriptor_offset=page["metadata_descriptor_offset"],
        metadata_offset=page["source_metadata_offset"], source_rows=(),
        english_rows=(), metadata_records=metadata,
    )
    transformed = _relocated_help_body_metadata(shadow)[:-1]
    forbidden = [set() for _ in range(page["rows"])]
    for kind, variant, field_x, field_y in transformed:
        sx, sy = 73 + field_x, 119 + field_y
        row = round((sy - 131) / 16)
        if not (0 <= row < page["rows"]) or abs(131 + row*16 - sy) > 10:
            continue
        col = round((sx - 85) / 12)
        # The accepted five-cell controller placeholder is a conservative
        # bound; skip decorative sprites outside the actual English text box.
        forbidden[row].update(c for c in range(col, col + 5) if 0 <= c < _MAX_CELLS)
    return forbidden, transformed


def _reflow_page(
    rows: list[tuple[int, bytes] | None], official: dict[str, set[str]],
    reserved: list[set[int]], page_key: str,
) -> tuple[tuple[str, ...], list[int]]:
    """Word-preserving icon-aware reflow into exactly the original row count.

    Never put an English glyph in a controller icon's five-cell hole. No
    source word is dropped, and tokens are not split inside the PS2 font.
    Paragraph breaks are kept if they fit, otherwise only blank separators
    are eliminated; text and punctuation are never silently abbreviated.
    """
    groups: list[list[str]] = []
    current: list[str] = []
    semantic_sources: list[int] = []
    for entry in rows:
        if entry is None:
            if current:
                groups.append(current)
                current = []
            continue
        source_offset, source = entry
        jp = source[:-1].decode("cp932")
        matches = official.get(jp, set())
        if source_offset in COMPACT_HELP_ROWS.get(page_key, {}):
            translated = COMPACT_HELP_ROWS[page_key][source_offset]
            semantic_sources.append(source_offset)
        elif len(matches) == 1:
            translated = next(iter(matches))
        elif source_offset in SEMANTIC_CONTROLS:
            translated = SEMANTIC_CONTROLS[source_offset]
            semantic_sources.append(source_offset)
        else:
            raise ValueError(f"Missing unique official Help translation at {source_offset:#x}")
        current.append(_normalized_english(translated))
    if current:
        groups.append(current)
    paragraphs = [" ".join(group).split() for group in groups]
    if any(len(word) > _MAX_CELLS for group in paragraphs for word in group):
        raise ValueError("Long English word cannot fit Help's 28-cell viewport")

    def layout(keep_gaps: bool) -> tuple[str, ...] | None:
        canvas = [[" "] * _MAX_CELLS for _ in rows]
        cursor_row = 0
        cursor_col = 0
        for gi, words in enumerate(paragraphs):
            if gi > 0 and keep_gaps and cursor_col:
                cursor_row += 2
                cursor_col = 0
            elif gi > 0 and keep_gaps:
                cursor_row += 1
            for word in words:
                while True:
                    if cursor_row >= len(rows):
                        return None
                    # Maintain a visual word separator whenever the prior
                    # glyph on the current row was another part of prose.
                    prior = any(c != " " for c in canvas[cursor_row][:cursor_col])
                    col = min(_MAX_CELLS, cursor_col + int(prior))
                    while col + len(word) <= _MAX_CELLS:
                        if all(x not in reserved[cursor_row]
                               for x in range(col, col+len(word))):
                            for x, glyph in enumerate(word):
                                canvas[cursor_row][col+x] = glyph
                            cursor_col = col + len(word)
                            break
                        col += 1
                    else:
                        cursor_row += 1
                        cursor_col = 0
                        continue
                    break
        return tuple("".join(row).rstrip() for row in canvas)

    output = layout(keep_gaps=True)
    if output is None:
        output = layout(keep_gaps=False)
    if output is None:
        raise ValueError(f"Cannot fit Help English without clipping in {len(rows)} original rows")
    if len(output) != len(rows) or any(len(line) > _MAX_CELLS for line in output):
        raise AssertionError("Help source row-count/width invariant broken")
    for row, line in enumerate(output):
        for column in reserved[row]:
            if column < len(line) and line[column] != " ":
                raise AssertionError(f"Controller collision on row {row}, column {column}")
    return output, semantic_sources


def append_help_to_p0(
    source: bytes, p0: bytes, manifest: dict,
    english: list[tuple[str, str, int]], *, corpus_sha256: str
) -> tuple[bytes, dict]:
    if manifest.get("schema_version") != 1 or manifest.get("approved_pages") != 50:
        raise ValueError("Unexpected approved Help manifest")
    if _sha(source) != manifest["pristine_elf_sha256"]:
        raise ValueError("Pristine source ELF mismatch")
    if _sha(p0) != manifest["p0_elf_sha256"]:
        raise ValueError("Prior frozen r67 P0 ELF mismatch")
    if corpus_sha256 != manifest["official_ps4_english_sha256"]:
        raise ValueError("Official English corpus mismatch")

    tp, file_offset, va, _, size, reserved, flags, alignment = struct.unpack_from(
        "<8I", p0, _SEG_PH_OFFSET
    )
    if tp != 1 or flags != 7 or alignment != 16 or va != _SEGMENT_VA or reserved != 0x100000:
        raise ValueError("Translation PT_LOAD geometry mismatch")
    if file_offset + size != len(p0):
        raise ValueError("Non-tail translation PT_LOAD not supported")

    official: dict[str, set[str]] = defaultdict(set)
    for jp, translated, _position in english:
        official[jp].add(translated)
    result = bytearray(p0)
    consumed_descriptors: set[int] = set()
    report_pages: list[dict] = []
    total_semantic = 0

    def append(data: bytes, align: int = 2) -> int:
        while len(result) % align:
            result.append(0)
        where = va + len(result) - file_offset
        result.extend(data)
        return where

    def redirected_pointer(offset: int, old_va: int, new_va: int) -> None:
        if offset in consumed_descriptors:
            raise ValueError(f"Double-owned HANT descriptor: 0x{offset:x}")
        if struct.unpack_from("<I", source, offset)[0] != old_va:
            raise ValueError(f"Bad original Help descriptor: 0x{offset:x}")
        if struct.unpack_from("<I", p0, offset)[0] != old_va:
            raise ValueError(f"P0 Help descriptor already changed: 0x{offset:x}")
        consumed_descriptors.add(offset)
        struct.pack_into("<I", result, offset, new_va)

    for page in manifest["pages"]:
        key = page["key"]
        rows = _raw_rows(source, page)
        table = page["source_table_offset"]
        meta = page["source_metadata_offset"]
        t_size = (page["rows"]+1)*4
        m_size = (page["icon_records"]+1)*8
        if _sha(source[table:table+t_size]) != page["table_sha256"]:
            raise ValueError(f"Help source table SHA drift: {key}")
        if _sha(source[meta:meta+m_size]) != page["metadata_sha256"]:
            raise ValueError(f"Help icon source SHA drift: {key}")
        if [None if row is None else _sha(row[1]) for row in rows] != page["row_source_sha256"]:
            raise ValueError(f"Help individual source row SHA drift: {key}")
        metadata_source = _metadata(source, page)
        reserved_cells, transformed = _icon_reservations(page, metadata_source)
        text, overrides = _reflow_page(rows, official, reserved_cells, key)
        total_semantic += len(overrides)
        va_rows = [append(encode_ps2_english(line, collapse_spaces=False) + b"\x00")
                   if line else _BLANK for line in text]
        table_va = append(
            struct.pack("<" + "I"*(len(va_rows)+1), *va_rows, _EOF),
            align=4
        )
        redirected_pointer(
            page["descriptor_offset"],
            _R66_SRC_BASE + table - _R66_OFFSET,
            table_va
        )

        icon_map = []
        if metadata_source:
            # Relocate icons using the same accepted r66 mode-4 geometry.
            # The icon-aware English row planner deliberately leaves each
            # controller at the original page-row identity and reserves an
            # explicit five-cell gap in its translated row.
            recalculated = []
            for original, rewritten in zip(metadata_source, transformed, strict=True):
                kind, variant, _old_x, _old_y = original
                _type, _variant, translated_x, translated_y = rewritten
                if not (-32768 <= translated_x <= 32767 and -32768 <= translated_y <= 32767):
                    raise ValueError(f"Translated icon outside signed 16-bit range: {key}")
                recalculated.append((kind, variant, translated_x, translated_y))
                icon_map.append([original[2], translated_x, original[3], translated_y])
            output_meta = (*recalculated, (-1, -1, -1, -1))
            metadata_va = append(
                b"".join(struct.pack("<hhhh", *v) for v in output_meta),
                align=4
            )
            redirected_pointer(
                page["metadata_descriptor_offset"],
                _R66_SRC_BASE + meta - _R66_OFFSET,
                metadata_va
            )

        report_pages.append({
            "key": key, "rows": len(text), "translated_nonempty_rows": sum(bool(s) for s in text),
            "original_nonempty_rows": sum(row is not None for row in rows),
            "icons": len(metadata_source), "semantic_source_offsets": overrides,
            "first_line": text[0] if text else "",
            "table_va": table_va, "icon_reflow_row_map": icon_map,
        })

    if len(report_pages) != 50:
        raise ValueError("Help page cardinality drift")
    new_size = len(result) - file_offset
    if new_size > reserved:
        raise ValueError("Not enough reserved translation RAM")
    struct.pack_into("<I", result, _SEG_PH_OFFSET + 16, new_size)

    allowed = set(range(_SEG_PH_OFFSET + 16, _SEG_PH_OFFSET + 20))
    for ptr in consumed_descriptors:
        allowed.update(range(ptr, ptr + 4))
    for offset, (old, new) in enumerate(zip(p0, result)):
        if old != new and offset not in allowed:
            raise ValueError(f"Unclassified previously accepted P0 byte at 0x{offset:x}")
    return bytes(result), {
        "schema_version": 1, "source_p0_sha256": _sha(p0), "english_elf_sha256": _sha(result),
        "translated_help_pages": len(report_pages), "translated_semantic_rows": total_semantic,
        "descriptor_aliases": len(consumed_descriptors), "append_bytes": len(result) - len(p0),
        "pages": report_pages,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pristine_elf", type=Path)
    p.add_argument("existing_p0_elf", type=Path)
    p.add_argument("--official-english-bytes", type=Path, required=True)
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError("Refusing to overwrite ELF or audit report")
    english_bytes = args.official_english_bytes.read_bytes()
    manifest = json.loads(args.manifest.read_text())
    output, report = append_help_to_p0(
        args.pristine_elf.read_bytes(), args.existing_p0_elf.read_bytes(),
        manifest, parse_english(args.official_english_bytes), corpus_sha256=_sha(english_bytes)
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(output)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k:v for k,v in report.items() if k!="pages"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
