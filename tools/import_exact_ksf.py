from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from tools.corpus import scan_corpus
from tools.ksf_import import import_exact_ksf, summarize_ksf_analyses


def import_exact_ksf_corpus(
    ps2_adv: Path, ps4_adv: Path, output_root: Path
) -> dict[str, Any]:
    corpus = scan_corpus(ps2_adv, ps4_adv)
    results: list[dict[str, Any]] = []
    totals = {"fit": 0, "overflow": 0, "ambiguous": 0}
    files_with_patches = 0

    for item in corpus["assets"]:
        if item["kind"] != "KSF" or item["relation"] != "exact" or item["localization"] != "mapped":
            continue

        rel = Path(str(item["path"]))
        ps2_file = ps2_adv / rel
        ps4_file = ps4_adv / rel
        dc_file = ps4_adv / str(item["english_map"])
        dc = json.loads(dc_file.read_text(encoding="utf-8"))
        translated, analyses = import_exact_ksf(ps2_file.read_bytes(), ps4_file.read_bytes(), dc)
        summary = summarize_ksf_analyses(analyses)
        for status in totals:
            totals[status] += summary[status]

        output_sha256: str | None = None
        if summary["fit"]:
            destination = output_root / rel
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(translated)
            output_sha256 = sha256(translated).hexdigest()
            files_with_patches += 1

        results.append(
            {
                "path": rel.as_posix(),
                "summary": summary,
                "output_sha256": output_sha256,
                "fields": [asdict(field) for field in analyses],
            }
        )

    return {
        "schema_version": 1,
        "eligible_exact_mapped_files": len(results),
        "files_with_patches": files_with_patches,
        "fit_entries": totals["fit"],
        "overflow_entries": totals["overflow"],
        "ambiguous_entries": totals["ambiguous"],
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Conservatively import exact-source PS4 KSF localization")
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    report = import_exact_ksf_corpus(args.ps2_adv, args.ps4_adv, args.output_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary = {key: value for key, value in report.items() if key != "results"}
    print(json.dumps(summary, sort_keys=True))
    print(f"report={args.report}")
    print(f"output_root={args.output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
