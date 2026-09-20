from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tools.corpus import scan_corpus
from tools.exact_import import ExactImportError, import_exact_mtx


def main() -> int:
    parser = argparse.ArgumentParser(description="Import provably direct exact PS4 English MTX localization")
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    corpus = scan_corpus(args.ps2_adv, args.ps4_adv)
    results: list[dict[str, object]] = []

    for item in corpus["assets"]:
        if item["kind"] != "MTX" or item["relation"] != "exact" or item["localization"] != "mapped":
            continue

        rel = Path(str(item["path"]))
        ps2_file = args.ps2_adv / rel
        ps4_file = args.ps4_adv / rel
        dc_file = args.ps4_adv / str(item["english_map"])
        dc = json.loads(dc_file.read_text(encoding="utf-8"))
        record: dict[str, object] = {
            "path": rel.as_posix(),
            "english_entries": item["english_entries"],
        }
        try:
            translated = import_exact_mtx(ps2_file.read_bytes(), ps4_file.read_bytes(), dc)
        except ExactImportError as exc:
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
