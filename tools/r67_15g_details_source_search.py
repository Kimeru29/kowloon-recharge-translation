"""Read-only search for unresolved item Details keys in recovered PS4 assets."""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
from typing import Iterable, Mapping

from tools.inspect_english_bytes import parse
from tools.r67_15g_item_details import (
    CORPUS_PATH,
    ROOT,
    collect_catalogue,
    load_official_rows,
    map_official_descriptions,
)


ASSET_ROOT = Path(
    "/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/Media/StreamingAssets"
)
SEARCH_EXTENSIONS = {
    ".bytes", ".ksf", ".kes", ".esf", ".json", ".txt", ".tmx", ".mtx",
    ".map", ".wrd", ".itm", ".eve", ".enm",
}
PatternOwners = Mapping[bytes, set[tuple[int, str]]]


def _automaton(patterns: list[bytes]) -> tuple[list[dict[int, int]], list[int], list[set[int]]]:
    if any(not pattern for pattern in patterns):
        raise ValueError("empty raw-search pattern")
    transitions: list[dict[int, int]] = [{}]
    failures = [0]
    outputs: list[set[int]] = [set()]
    for pattern_index, pattern in enumerate(patterns):
        state = 0
        for byte in pattern:
            next_state = transitions[state].get(byte)
            if next_state is None:
                next_state = len(transitions)
                transitions[state][byte] = next_state
                transitions.append({})
                failures.append(0)
                outputs.append(set())
            state = next_state
        outputs[state].add(pattern_index)

    pending = deque(transitions[0].values())
    while pending:
        state = pending.popleft()
        for byte, next_state in transitions[state].items():
            pending.append(next_state)
            fallback = failures[state]
            while fallback and byte not in transitions[fallback]:
                fallback = failures[fallback]
            failures[next_state] = transitions[fallback].get(byte, 0)
            outputs[next_state].update(outputs[failures[next_state]])
    return transitions, failures, outputs


def scan_raw_assets(
    assets: Iterable[tuple[str, bytes]],
    pattern_owners: PatternOwners,
) -> tuple[dict[int, set[str]], set[int], int]:
    """Find raw byte substrings, returning line hits, full-paragraph hits, bytes scanned."""
    patterns = list(pattern_owners)
    transitions, failures, outputs = _automaton(patterns)
    line_hits: dict[int, set[str]] = {}
    paragraph_hits: set[int] = set()
    byte_count = 0
    for asset_name, data in assets:
        byte_count += len(data)
        state = 0
        for byte in data:
            while state and byte not in transitions[state]:
                state = failures[state]
            state = transitions[state].get(byte, 0)
            for pattern_index in outputs[state]:
                for item_id, kind in pattern_owners[patterns[pattern_index]]:
                    if kind == "full_paragraph":
                        paragraph_hits.add(item_id)
                    elif kind == "line_key":
                        line_hits.setdefault(item_id, set()).add(asset_name)
                    else:
                        raise ValueError(f"unknown raw-search owner kind: {kind}")
    return line_hits, paragraph_hits, byte_count


def find_exact_keys(
    keys_by_item: Mapping[int, set[str]],
    candidate_keys: set[str],
) -> dict[int, list[str]]:
    """Return only complete exact key intersections, never raw substrings."""
    return {
        item_id: sorted(keys & candidate_keys)
        for item_id, keys in keys_by_item.items()
        if keys & candidate_keys
    }


def _candidate_files(asset_root: Path) -> list[Path]:
    return sorted(
        path for path in asset_root.rglob("*")
        if path.is_file() and (
            path.suffix.lower() in SEARCH_EXTENSIONS
            or path.name.startswith("AssetFileDic")
        )
    )


def _read_assets(paths: Iterable[Path]) -> Iterable[tuple[str, bytes]]:
    for path in paths:
        try:
            yield str(path), path.read_bytes()
        except OSError:
            continue


def build_report(
    *, asset_root: Path = ASSET_ROOT,
    elf_path: Path = ROOT / "local/r67-15f-item-panel-layout.elf",
    corpus_path: Path = CORPUS_PATH,
) -> dict:
    """Search recovered assets using the verified native catalogue and corpus."""
    records = collect_catalogue(elf_path.read_bytes())
    english_rows = load_official_rows(corpus_path)
    fully_mapped, unresolved = map_official_descriptions(records, english_rows)
    pattern_owners: dict[bytes, set[tuple[int, str]]] = {}
    for record in unresolved:
        for key in record.source_lines:
            for encoding in ("cp932", "utf-8"):
                pattern_owners.setdefault(key.encode(encoding), set()).add(
                    (record.item_id, "line_key")
                )
        for encoding in ("cp932", "utf-8"):
            pattern_owners.setdefault(record.source_text.encode(encoding), set()).add(
                (record.item_id, "full_paragraph")
            )

    files = _candidate_files(asset_root)
    raw_line_hits, full_paragraph_hits, scanned_bytes = scan_raw_assets(
        _read_assets(files), pattern_owners
    )
    unresolved_keys = {
        record.item_id: set(record.source_lines) for record in unresolved
    }
    parsed_bytes_exact: dict[str, dict[int, list[str]]] = {}
    for path in sorted(asset_root.rglob("*.bytes")):
        try:
            rows = parse(path)
        except (OSError, ValueError, UnicodeError):
            continue
        exact = find_exact_keys(unresolved_keys, {key for key, _value, _offset in rows})
        if exact:
            parsed_bytes_exact[path.name] = exact

    return {
        "official_corpus": str(corpus_path),
        "official_corpus_records": len(english_rows),
        "fully_mapped_records": len(fully_mapped),
        "unresolved_ids": [record.item_id for record in unresolved],
        "asset_root": str(asset_root),
        "candidate_files": len(files),
        "candidate_bytes": scanned_bytes,
        "full_paragraph_raw_hits": sorted(full_paragraph_hits),
        "raw_line_key_asset_hits": {
            str(item_id): sorted(paths) for item_id, paths in raw_line_hits.items()
        },
        "parsed_bytes_exact_keys": parsed_bytes_exact,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path, default=ASSET_ROOT)
    parser.add_argument(
        "--elf", type=Path, default=ROOT / "local/r67-15f-item-panel-layout.elf"
    )
    parser.add_argument("--corpus", type=Path, default=CORPUS_PATH)
    args = parser.parse_args(argv)
    report = build_report(
        asset_root=args.asset_root,
        elf_path=args.elf,
        corpus_path=args.corpus,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
