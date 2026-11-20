"""Reproduce the scoped r67.15n partial MTX payloads and provenance."""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from tools.r67n_partial import PartialImportResult, import_partial_mtx, verify_partial_mtx


MACROS = re.compile(r"\((px|pn1|pm1)\)")
PATHS = (
    *(Path(f"MS/{name}.MTX") for name in ("MS00_01", "MS01_00", "MS01_03", "MS06_03", "MS13_02")),
    *(Path(f"FD/FD00_{num:02d}.MTX") for num in (*range(24), 29)),
)
MAX_CELLS = 39
MAX_GROUP_ROWS = 3


def _layout_for(result: PartialImportResult, ps2: bytes, dc: dict[str, Any]) -> dict[str, Any]:
    values = dict(zip(dc["keys"], dc["values"], strict=True))
    rows: Counter[int] = Counter()
    runtime_review = []
    for span in result.spans:
        original = ps2[span.ps2_start:span.ps2_end].decode("cp932")
        prefix_start = max(span.ps2_region[0], span.ps2_start - 24)
        prefix = ps2[prefix_start:span.ps2_start]
        contexts = []
        if original.startswith("【") and original.endswith("】"):
            contexts.append("bracketed_speaker_label")
        if original.startswith(("第", "［", "《")) or re.search(rb"w\d{2}\{$", prefix):
            contexts.append("possible_scene_title")
        if (b"ds" in (prefix[-8:], bytes.fromhex(span.right_delimiter_hex))
                or re.search(rb"(?:ds|sbr)\d{2,}$", prefix)):
            contexts.append("possible_choice_or_branch_context")
        if span.ps2_start == span.ps2_region[0]:
            contexts.append("pointer_entry")
        entries = []
        for entry in span.entries:
            dynamic_name_count = len(MACROS.findall(values[entry.entry_id]))
            static_cells = (entry.output_end - entry.output_start) // 2 - dynamic_name_count
            rows[static_cells] += 1
            entries.append({
                "entry_id": entry.entry_id,
                "static_cells": static_cells,
                "name_controls": dynamic_name_count,
                "output_start": entry.output_start,
                "output_end": entry.output_end,
            })
        maximum = max(e["static_cells"] for e in entries)
        if (maximum > MAX_CELLS or len(entries) > MAX_GROUP_ROWS
                or contexts or span.name_controls):
            runtime_review.append({
                "ps2_start": span.ps2_start,
                "ps4_anchor": span.ps4_start,
                "output_start": span.output_start,
                "pointer_slots": span.pointer_slots,
                "prefix_start": prefix_start,
                "prefix_hex": prefix.hex(),
                "right_delimiter_hex": span.right_delimiter_hex,
                "possible_contexts": contexts,
                "group_rows": len(entries),
                "exceeds_cell_triage_threshold": maximum > MAX_CELLS,
                "exceeds_group_rows_threshold": len(entries) > MAX_GROUP_ROWS,
                "entries": entries,
            })
    return {
        "metric": "encoded two-byte glyph cells excluding dynamic name expansion",
        "review_threshold_cells": MAX_CELLS,
        "review_threshold_group_rows": MAX_GROUP_ROWS,
        "maximum_static_cells": max(rows, default=0),
        "maximum_group_rows": max((len(s.entries) for s in result.spans), default=0),
        "static_cells_histogram": dict(sorted(rows.items())),
        "rows_over_threshold": sum(count for cells, count in rows.items() if cells > MAX_CELLS),
        "groups_over_row_threshold": sum(len(s.entries) > MAX_GROUP_ROWS for s in result.spans),
        "dynamic_name_rows": sum(e["name_controls"] > 0 for s in runtime_review for e in s["entries"]),
        "records_for_runtime_review": runtime_review,
    }



def _record(relative: Path, dc_relative: Path, ps2: bytes, ps4: bytes, dc_raw: bytes,
            dc: dict[str, Any], result: PartialImportResult) -> dict[str, Any]:
    unresolved_english_entries = sum(len(group.entry_ids) for group in result.unresolved)
    if result.english_entries + unresolved_english_entries != len(dc["keys"]):
        raise ValueError(f"Official entry accounting differs for {relative}")
    if not result.spans and result.data != ps2:
        raise ValueError(f"Unresolved file would change original PS2 bytes at {relative}")
    return {
        "path": "ADV/" + relative.as_posix(),
        "official_map": "ADV/" + dc_relative.as_posix(),
        "ps2_sha256": result.ps2_sha256,
        "ps4_sha256": result.ps4_sha256,
        "official_map_sha256": sha256(dc_raw).hexdigest(),
        "dc_sha256": result.dc_sha256,
        "output_sha256": result.output_sha256,
        "ps2_size": len(ps2),
        "ps4_size": len(ps4),
        "output_size": len(result.data),
        "groups": len(result.spans) + len(result.unresolved),
        "proven_groups": len(result.spans),
        "unresolved_groups": len(result.unresolved),
        "official_english_entries": len(dc["keys"]),
        "english_entries": result.english_entries,
        "unresolved_english_entries": unresolved_english_entries,
        "unresolved_reasons": dict(sorted(Counter(g.reason for g in result.unresolved).items())),
        "spans": [asdict(s) for s in result.spans],
        "unresolved": [asdict(g) for g in result.unresolved],
        "regions": [asdict(r) for r in result.regions],
        "layout": _layout_for(result, ps2, dc),
    }


def build_corpus(ps2_adv: Path, ps4_adv: Path, output_dir: Path) -> dict[str, Any]:
    """Generate verified partial MTX overlays and evidence for the fixed scope."""
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    overlay = output_dir / "overlay"
    results = []
    payloads = {}
    for relative in PATHS:
        ps2 = (ps2_adv / relative).read_bytes()
        ps4 = (ps4_adv / relative).read_bytes()
        dc_relative = relative.parent / "EN" / f"{relative.stem}DC.json"
        dc_raw = (ps4_adv / dc_relative).read_bytes()
        try:
            dc = json.loads(dc_raw)
            result = import_partial_mtx(ps2, ps4, dc)
            verify_partial_mtx(ps2, ps4, dc, result)
            results.append(_record(relative, dc_relative, ps2, ps4, dc_raw, dc, result))
        except ValueError as exc:
            raise ValueError(f"{relative}: {exc}") from exc
        if result.spans:
            payloads[relative] = result.data

    report = {
        "schema_version": 1,
        "ps2_source_root": str(ps2_adv),
        "ps4_source_root": str(ps4_adv),
        "overlay_root": str(overlay),
        "files_examined": len(results),
        "files_with_proven_groups": len(payloads),
        "english_entries": sum(row["english_entries"] for row in results),
        "unresolved_english_entries": sum(row["unresolved_english_entries"] for row in results),
        "proven_groups": sum(row["proven_groups"] for row in results),
        "unresolved_groups": sum(row["unresolved_groups"] for row in results),
        "results": results,
    }
    output_dir.mkdir(parents=True)
    overlay.mkdir()
    for relative, payload in payloads.items():
        destination = overlay / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)

    staged = output_dir / "report.tmp"
    staged.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    staged.replace(output_dir / "report.json")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build_corpus(args.ps2_adv, args.ps4_adv, args.output_dir)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
