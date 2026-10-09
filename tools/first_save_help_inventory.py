"""Inventory early-accessible H.A.N.T. Help bodies; never modify the ELF.

The Help category/topic labels are already English in r66. Body text, icon
metadata and descriptor pointers are separate owners. This diagnostic
identifies real body tables versus ADV placeholder pointers and measures
unique exact official English row correspondence.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct

from tools.hant_ui import (
    HANT_ADV_HELP_TOPICS, HANT_EXPLORATION_HELP_TOPICS, HANT_HELP_TOPICS,
    _HANT_BLANK_VA, _HANT_EOF_VA,
)
from tools.inspect_english_bytes import parse as parse_english

_CATEGORIES = (
    (HANT_ADV_HELP_TOPICS, 0x5C4390, 0x5C4340),
    (HANT_EXPLORATION_HELP_TOPICS, 0x5C8A50, 0x5C8A00),
    (HANT_HELP_TOPICS, 0x5CBAB0, 0x5CBA60),
)
_BLANK = _HANT_BLANK_VA
_EOF = _HANT_EOF_VA
_FILE_MAIN_VA = 0x100000
_FILE_MAIN_OFFSET = 0x80
_ALREADY_LOCALIZED = {"adv_controls", "exploration_controls", "moving_in_ruins", "shop", "hant_functions"}


def _offset(va: int, raw: bytes) -> int:
    offset = va - _FILE_MAIN_VA + _FILE_MAIN_OFFSET
    if offset < 0 or offset >= len(raw):
        raise ValueError(f"Invalid original Help address: {va:#x}")
    return offset


def inventory(raw: bytes, english_rows: list[tuple[str, str, int]]) -> dict:
    dictionary: dict[str, set[str]] = {}
    for japanese, english, _row in english_rows:
        dictionary.setdefault(japanese, set()).add(english)
    pages = []
    for cat, (topics, descriptor_start, metadata_start) in enumerate(_CATEGORIES):
        for index, topic in enumerate(topics):
            descriptor = descriptor_start + index*4
            metadata_descriptor = metadata_start + index*4
            table = _offset(struct.unpack_from("<I", raw, descriptor)[0], raw)
            metadata = _offset(struct.unpack_from("<I", raw, metadata_descriptor)[0], raw)
            rows = 0
            nonblank = 0
            uniquely_official = 0
            unresolved: list[int] = []
            source_text_bytes = bytearray()
            for row in range(160):
                ptr = struct.unpack_from("<I", raw, table + row*4)[0]
                if ptr == _EOF:
                    break
                rows += 1
                if ptr == _BLANK:
                    continue
                src_offset = _offset(ptr, raw)
                terminator = raw.find(b"\x00", src_offset, min(len(raw), src_offset + 384))
                if terminator < 0:
                    raise ValueError(f"Unterminated original Help row: {topic.key}/{row}")
                source = raw[src_offset:terminator+1]
                try:
                    jp = source[:-1].decode("cp932")
                except UnicodeDecodeError as exc:
                    raise ValueError(f"Invalid CP932 Help row: {topic.key}/{row}") from exc
                nonblank += 1
                source_text_bytes.extend(source)
                if len(dictionary.get(jp, ())) == 1:
                    uniquely_official += 1
                else:
                    unresolved.append(row)
            else:
                raise ValueError(f"Help table has no EOF within 160 rows: {topic.key}")
            icons = 0
            for record in range(100):
                fields = struct.unpack_from("<4h", raw, metadata + record*8)
                if fields == (-1, -1, -1, -1):
                    break
                icons += 1
            else:
                raise ValueError(f"Help metadata has no terminator: {topic.key}")
            pages.append(dict(
                key=topic.key, category=cat, index=index,
                descriptor_offset=descriptor, metadata_descriptor_offset=metadata_descriptor,
                source_table_offset=table, source_metadata_offset=metadata,
                rows=rows, japanese_rows=nonblank, exact_official_rows=uniquely_official,
                unresolved_row_indices=unresolved, icon_records=icons,
                source_sha256=hashlib.sha256(source_text_bytes).hexdigest(),
                existing_r66_english=topic.key in _ALREADY_LOCALIZED,
            ))
    meaningful = [page for page in pages if page["japanese_rows"] > 0]
    unknown = [page for page in meaningful if not page["existing_r66_english"]]
    # Fifteen ADV topics share one single-row in-game placeholder, with
    # translated PS4 wording; they are not actually empty pages.
    placeholder_hash = next(page["source_sha256"] for page in pages if page["key"] == "adv_06")
    placeholders = [page["key"] for page in pages if (
        page["category"] == 0 and page["rows"] == 1
        and page["source_sha256"] == placeholder_hash
    )]
    return dict(
        schema_version=1, total_topics=len(pages), empty_pages=len(pages)-len(meaningful),
        shared_one_line_placeholder_pages=placeholders,
        meaningful_pages=len(meaningful),
        already_translated_pages=len(meaningful)-len(unknown),
        outstanding_pages=len(unknown),
        meaningful_source_rows=sum(p["japanese_rows"] for p in meaningful),
        exact_official_rows=sum(p["exact_official_rows"] for p in meaningful),
        pages=pages,
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pristine_elf", type=Path)
    p.add_argument("--official-english-bytes", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    result = inventory(args.pristine_elf.read_bytes(), parse_english(args.official_english_bytes))
    if args.report.exists():
        raise FileExistsError(args.report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "pages"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
