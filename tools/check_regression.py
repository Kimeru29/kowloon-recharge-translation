from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.regression import RegressionError, RegressionResult, compare_manifests


def check_regression_files(baseline_path: Path, current_path: Path) -> RegressionResult:
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    current = json.loads(Path(current_path).read_text(encoding="utf-8"))
    return compare_manifests(baseline, current)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check cumulative translation regression manifest")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("current", type=Path)
    args = parser.parse_args()

    try:
        result = check_regression_files(args.baseline, args.current)
    except RegressionError as exc:
        print(f"REGRESSION: {exc}")
        return 2

    print(
        json.dumps(
            {
                "added": result.added,
                "changed": result.changed,
                "removed": result.removed,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
