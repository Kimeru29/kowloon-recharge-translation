from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.ksf import KsfFixedStringPatch, patch_fixed_strings


def apply_ksf_override_manifest(raw: bytes, manifest: dict[str, Any]) -> bytes:
    rows = manifest.get("ksf")
    if not isinstance(rows, list):
        raise ValueError("Override manifest must contain a ksf array")
    patches: list[KsfFixedStringPatch] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("KSF override rows must be objects")
        patches.append(
            KsfFixedStringPatch(
                offset=int(row["offset"]),
                capacity=int(row["capacity"]),
                text=str(row["text"]),
                constrained=bool(row.get("constrained", False)),
            )
        )
    return patch_fixed_strings(raw, tuple(patches))


def build_dg00_override(
    *,
    manifest_path: Path,
    ps2_adv: Path,
    exact_ksf_root: Path | None,
    output_root: Path,
) -> Path:
    rel = Path("DG/DG00_00.KSF")
    preferred = exact_ksf_root / rel if exact_ksf_root is not None else None
    base = preferred if preferred is not None and preferred.exists() else ps2_adv / rel
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    result = apply_ksf_override_manifest(base.read_bytes(), manifest)
    destination = output_root / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Build accepted manual overlay exceptions")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--exact-ksf-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    destination = build_dg00_override(
        manifest_path=args.manifest,
        ps2_adv=args.ps2_adv,
        exact_ksf_root=args.exact_ksf_root,
        output_root=args.output_root,
    )
    print(f"output={destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
