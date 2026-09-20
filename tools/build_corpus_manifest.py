from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.corpus import estimate_mtx_text_coverage, scan_corpus


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic PS2/PS4 ADV corpus manifest")
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = scan_corpus(args.ps2_adv, args.ps4_adv)
    manifest["text_coverage_estimate"] = estimate_mtx_text_coverage(args.ps2_adv, args.ps4_adv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    for kind, stats in manifest["summary"].items():
        print(kind, json.dumps(stats, sort_keys=True))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
