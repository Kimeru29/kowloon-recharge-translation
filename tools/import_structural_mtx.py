from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from tools.corpus import scan_corpus
from tools.structural_import import StructuralImportError, import_structural_mtx


def import_structural_corpus(
    ps2_adv: Path,
    ps4_adv: Path,
    output_root: Path,
    corpus: dict[str, Any],
    *,
    allowed_template_paths: set[str] | None = None,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    allowed_template_paths = allowed_template_paths or set()

    for item in corpus.get("assets", []):
        relation = item.get("relation")
        path = str(item.get("path"))
        eligible_relation = relation == "structural" or (
            relation == "template" and path in allowed_template_paths
        )
        if (
            item.get("kind") != "MTX"
            or not eligible_relation
            or item.get("localization") != "mapped"
        ):
            continue
        rel = Path(str(item["path"]))
        dc_path = ps4_adv / str(item["english_map"])
        dc = json.loads(dc_path.read_text(encoding="utf-8"))
        record: dict[str, Any] = {
            "path": rel.as_posix(),
            "english_entries": int(item["english_entries"]),
        }
        try:
            imported = import_structural_mtx(
                (ps2_adv / rel).read_bytes(),
                (ps4_adv / rel).read_bytes(),
                dc,
            )
        except (StructuralImportError, ValueError) as exc:
            record.update({"status": "rejected", "reason": str(exc)})
        else:
            destination = output_root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(imported.data)
            record.update(
                {
                    "status": "imported",
                    "groups": imported.groups_total,
                    "direct_groups": imported.direct_groups,
                    "semantic_groups": imported.semantic_groups,
                    "output_size": len(imported.data),
                    "output_sha256": sha256(imported.data).hexdigest(),
                    "spans": [asdict(span) for span in imported.spans],
                }
            )
        results.append(record)

    imported_rows = [row for row in results if row["status"] == "imported"]
    rejected_rows = [row for row in results if row["status"] == "rejected"]
    return {
        "schema_version": 1,
        "eligible_files": len(results),
        "eligible_english_entries": sum(int(row["english_entries"]) for row in results),
        "imported_files": len(imported_rows),
        "imported_english_entries": sum(int(row["english_entries"]) for row in imported_rows),
        "rejected_files": len(rejected_rows),
        "rejected_english_entries": sum(int(row["english_entries"]) for row in rejected_rows),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import fully proven structurally changed MTX localization")
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--corpus-manifest", type=Path)
    parser.add_argument(
        "--allow-template-path",
        action="append",
        default=[],
        help="Explicitly allow a proven template-classified MTX path (repeatable)",
    )
    args = parser.parse_args()

    if args.corpus_manifest is not None:
        corpus = json.loads(args.corpus_manifest.read_text(encoding="utf-8"))
    else:
        corpus = scan_corpus(args.ps2_adv, args.ps4_adv)
    report = import_structural_corpus(
        args.ps2_adv,
        args.ps4_adv,
        args.output_root,
        corpus,
        allowed_template_paths=set(args.allow_template_path),
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "results"}, sort_keys=True))
    print(f"output_root={args.output_root}")
    print(f"report={args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
