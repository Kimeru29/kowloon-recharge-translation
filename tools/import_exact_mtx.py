from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re

from tools.corpus import scan_corpus
from tools.exact_import import ExactImportError, import_exact_mtx


def approved_synthetic_dc_rules(path: Path | None) -> dict[str, dict]:
    if path is None:
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    if obj.get("schema_version") != 1 or not isinstance(obj.get("assets"), list):
        raise ValueError("Invalid approved synthetic-DC manifest schema")
    result: dict[str, dict] = {}
    for asset in obj["assets"]:
        if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
            raise ValueError("Malformed approved synthetic-DC asset")
        name = asset["path"]
        path_parts = Path(name)
        if path_parts.is_absolute() or ".." in path_parts.parts or name in result:
            raise ValueError(f"Duplicate or unsafe approved synthetic-DC path: {name}")
        if not all(isinstance(asset.get(k), str) and re.fullmatch(r"[0-9a-f]{64}", asset[k]) for k in
                   ("ps2_sha256", "ps4_sha256", "dc_sha256", "output_sha256")):
            raise ValueError(f"Invalid approved source/output hashes: {name}")
        if not isinstance(asset.get("output_size"), int) or asset["output_size"] <= 0:
            raise ValueError(f"Invalid approved output size: {name}")
        if not isinstance(asset.get("english_entries"), int) or asset["english_entries"] <= 0:
            raise ValueError(f"Invalid approved English entry count: {name}")
        result[name] = asset
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Import provably direct exact PS4 English MTX localization")
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--approved-adjacent-dc", type=Path,
                        help="Explicit per-file source/translation SHA256 approval manifest")
    args = parser.parse_args()
    approved = approved_synthetic_dc_rules(args.approved_adjacent_dc)
    seen_approved: set[str] = set()

    corpus = scan_corpus(args.ps2_adv, args.ps4_adv)
    results: list[dict[str, object]] = []

    for item in corpus["assets"]:
        if item["kind"] != "MTX" or item["relation"] != "exact" or item["localization"] != "mapped":
            continue

        rel = Path(str(item["path"]))
        ps2_file = args.ps2_adv / rel
        ps4_file = args.ps4_adv / rel
        dc_file = args.ps4_adv / str(item["english_map"])
        ps2_raw = ps2_file.read_bytes()
        ps4_raw = ps4_file.read_bytes()
        dc_bytes = dc_file.read_bytes()
        dc = json.loads(dc_bytes)
        rule = approved.get(rel.as_posix())
        if rule is not None:
            seen_approved.add(rel.as_posix())
            for field, raw in (("ps2_sha256", ps2_raw), ("ps4_sha256", ps4_raw),
                               ("dc_sha256", dc_bytes)):
                if sha256(raw).hexdigest() != rule[field]:
                    raise ValueError(f"Approved synthetic-DC source hash drift: {rel} {field}")
            if item["english_entries"] != rule["english_entries"]:
                raise ValueError(f"Approved synthetic-DC entry count drift: {rel}")
        record: dict[str, object] = {
            "path": rel.as_posix(),
            "english_entries": item["english_entries"],
        }
        try:
            translated = import_exact_mtx(
                ps2_raw, ps4_raw, dc,
                allow_adjacent_synthetic_keys=(rule is not None),
            )
            if rule is not None and (
                sha256(translated).hexdigest() != rule["output_sha256"]
                or len(translated) != rule["output_size"]
            ):
                raise ValueError(f"Approved synthetic-DC output drift: {rel}")
        except ExactImportError as exc:
            if rule is not None:
                raise ValueError(f"Approved synthetic-DC asset failed import: {rel}") from exc
            record.update({"status": "rejected", "reason": str(exc)})
        else:
            destination = args.output_root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(translated)
            record.update(
                {
                    "status": "imported",
                    "output_size": len(translated),
                    "output_sha256": sha256(translated).hexdigest(),
                }
            )
        results.append(record)

    if seen_approved != set(approved):
        raise ValueError(f"Approved synthetic-DC assets missing: {sorted(set(approved) - seen_approved)}")

    imported = [item for item in results if item["status"] == "imported"]
    rejected = [item for item in results if item["status"] == "rejected"]
    report = {
        "schema_version": 1,
        "eligible_exact_mapped_files": len(results),
        "imported_files": len(imported),
        "rejected_files": len(rejected),
        "eligible_english_entries": sum(int(item["english_entries"]) for item in results),
        "imported_english_entries": sum(int(item["english_entries"]) for item in imported),
        "rejected_english_entries": sum(int(item["english_entries"]) for item in rejected),
        "results": results,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({key: report[key] for key in report if key != "results"}, sort_keys=True))
    print(f"report={args.report}")
    print(f"output_root={args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
