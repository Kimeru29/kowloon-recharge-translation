from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import struct
from typing import Any


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _english_map_path(ps4_file: Path) -> Path:
    if ps4_file.suffix.upper() == ".MTX":
        name = f"{ps4_file.stem}DC.json"
    elif ps4_file.suffix.upper() == ".KSF":
        name = f"{ps4_file.name}DC.json"
    else:
        raise ValueError(f"Unsupported ADV asset kind: {ps4_file}")
    return ps4_file.parent / "EN" / name


def _read_entry_count(path: Path) -> int:
    obj = json.loads(path.read_text(encoding="utf-8"))
    keys = obj.get("keys")
    values = obj.get("values")
    if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
        raise ValueError(f"Invalid DC map: {path}")
    return len(keys)


def _contains_japanese_letter(text: str) -> bool:
    return any(
        "\u3040" <= char <= "\u30ff"
        or "\u3400" <= char <= "\u9fff"
        or "\uff66" <= char <= "\uff9f"
        for char in text
    )


def extract_japanese_literal_runs(raw: bytes, *, min_chars: int = 2) -> set[str]:
    """Extract a conservative lexical proxy for translatable MTX literals.

    ASCII terminates a run because MTX uses ASCII for its command language.
    The resulting statistic is intentionally a *lexical-run estimate*, not a
    claim that each run is one dialogue string.
    """

    if len(raw) < 2:
        raise ValueError("MTX is too small")
    header_size = struct.unpack_from("<H", raw, 0)[0] * 4
    if not (2 <= header_size <= len(raw)):
        raise ValueError(f"Invalid MTX header size: {header_size}")

    result: set[str] = set()
    current: list[str] = []

    def flush() -> None:
        if len(current) >= min_chars:
            text = "".join(current)
            if _contains_japanese_letter(text):
                result.add(text)
        current.clear()

    offset = header_size
    while offset < len(raw):
        byte = raw[offset]
        if (0x81 <= byte <= 0x9F) or (0xE0 <= byte <= 0xFC):
            if offset + 1 >= len(raw):
                flush()
                break
            pair = raw[offset:offset + 2]
            try:
                current.append(pair.decode("cp932"))
            except UnicodeDecodeError:
                flush()
            offset += 2
            continue
        if 0xA1 <= byte <= 0xDF:
            try:
                current.append(bytes((byte,)).decode("cp932"))
            except UnicodeDecodeError:
                flush()
            offset += 1
            continue

        flush()
        offset += 1

    flush()
    return result


def estimate_mtx_text_coverage(ps2_adv: Path, ps4_adv: Path) -> dict[str, Any]:
    """Estimate unique PS2 textual material by PS4 localization availability.

    This deliberately reports lexical CP932 runs rather than calling them
    dialogue lines.  It is useful for estimating how much PS2-exclusive text is
    genuinely novel while avoiding a false precision that the MTX command
    grammar does not yet justify.
    """

    ps2_adv = Path(ps2_adv)
    ps4_adv = Path(ps4_adv)
    mapped_common: set[str] = set()
    common_unmapped: set[str] = set()
    ps2_only: set[str] = set()

    for ps2_file in sorted(ps2_adv.rglob("*.MTX")):
        rel = ps2_file.relative_to(ps2_adv)
        runs = extract_japanese_literal_runs(ps2_file.read_bytes())
        ps4_file = ps4_adv / rel
        if not ps4_file.exists():
            ps2_only.update(runs)
            continue
        if _english_map_path(ps4_file).exists():
            mapped_common.update(runs)
        else:
            common_unmapped.update(runs)

    all_runs = mapped_common | common_unmapped | ps2_only
    ps2_only_reused = ps2_only & mapped_common
    ps2_only_novel = ps2_only - mapped_common
    common_unmapped_novel = common_unmapped - mapped_common

    return {
        "metric": "unique_cp932_literal_runs_min_2_chars",
        "caveat": (
            "Lexical-run estimate only; ASCII MTX controls split source text, "
            "and presence in a mapped file does not prove every run has an English DC entry."
        ),
        "all_unique_runs": len(all_runs),
        "mapped_common_unique_runs": len(mapped_common),
        "common_unmapped_unique_runs": len(common_unmapped),
        "common_unmapped_novel_runs": len(common_unmapped_novel),
        "ps2_only_unique_runs": len(ps2_only),
        "ps2_only_reused_in_mapped_common": len(ps2_only_reused),
        "ps2_only_novel_runs": len(ps2_only_novel),
        "ps2_only_novel_characters": sum(len(text) for text in ps2_only_novel),
    }


def scan_corpus(ps2_adv: Path, ps4_adv: Path) -> dict[str, Any]:
    """Return a deterministic inventory of PS2 ADV assets versus the PS4 remaster.

    Source relationship and localization-map availability are intentionally
    independent fields.  This keeps an exact-but-unmapped source distinct from
    a PS2-only source and prevents file-overlap statistics from masquerading as
    translation-coverage statistics.
    """

    ps2_adv = Path(ps2_adv)
    ps4_adv = Path(ps4_adv)
    assets: list[dict[str, Any]] = []

    ps4_hash_frequency: Counter[tuple[str, str]] = Counter()
    ps4_info: dict[tuple[str, str], tuple[Path, str, int]] = {}
    for kind in ("MTX", "KSF"):
        for path in sorted(ps4_adv.rglob(f"*.{kind}")):
            rel = path.relative_to(ps4_adv).as_posix()
            digest = _digest(path)
            ps4_info[(kind, rel)] = (path, digest, path.stat().st_size)
            ps4_hash_frequency[(kind, digest)] += 1

    for kind in ("MTX", "KSF"):
        for ps2_file in sorted(ps2_adv.rglob(f"*.{kind}")):
            rel = ps2_file.relative_to(ps2_adv).as_posix()
            ps2_digest = _digest(ps2_file)
            ps2_size = ps2_file.stat().st_size
            counterpart = ps4_info.get((kind, rel))

            record: dict[str, Any] = {
                "path": rel,
                "kind": kind,
                "ps2": {"size": ps2_size, "sha256": ps2_digest},
            }

            if counterpart is None:
                record.update(
                    {
                        "ps4": None,
                        "relation": "ps2-only",
                        "localization": "not-applicable",
                        "english_map": None,
                        "english_entries": 0,
                    }
                )
                assets.append(record)
                continue

            ps4_file, ps4_digest, ps4_size = counterpart
            record["ps4"] = {"size": ps4_size, "sha256": ps4_digest}

            if ps2_digest == ps4_digest and ps2_size == ps4_size:
                relation = "exact"
            elif ps4_hash_frequency[(kind, ps4_digest)] > 1:
                relation = "template"
            else:
                relation = "structural"
            record["relation"] = relation

            dc = _english_map_path(ps4_file)
            if dc.exists():
                record["localization"] = "mapped"
                record["english_map"] = dc.relative_to(ps4_adv).as_posix()
                record["english_entries"] = _read_entry_count(dc)
            else:
                record["localization"] = "unmapped"
                record["english_map"] = None
                record["english_entries"] = 0

            assets.append(record)

    assets.sort(key=lambda item: (item["kind"], item["path"]))

    summary: dict[str, dict[str, int]] = {}
    for kind in ("MTX", "KSF"):
        rows = [item for item in assets if item["kind"] == kind]
        relation_counts = Counter(item["relation"] for item in rows)
        mapped = [item for item in rows if item["localization"] == "mapped"]
        summary[kind] = {
            "ps2_total": len(rows),
            "common": sum(1 for item in rows if item["ps4"] is not None),
            "exact": relation_counts["exact"],
            "structural": relation_counts["structural"],
            "template": relation_counts["template"],
            "ps2-only": relation_counts["ps2-only"],
            "mapped": len(mapped),
            "unmapped": sum(1 for item in rows if item["localization"] == "unmapped"),
            "english_entries": sum(item["english_entries"] for item in mapped),
        }

    return {"schema_version": 1, "assets": assets, "summary": summary}
