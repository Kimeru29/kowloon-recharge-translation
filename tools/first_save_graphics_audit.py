"""Read-only PS4 JP-vs-English texture inventory; no source assets exported.

PNG names in AssetFileDic_en are not proof of first-save reachability.
This produces a georeferenced per-bundle pixel fingerprint inventory and
highlights untranslated PS2 bundle families for static scene-owner tracing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def audit(japanese_bundle_root: Path, dictionary: Path, ps2_port_root: Path) -> dict:
    try:
        import UnityPy
    except ImportError as exc:
        raise RuntimeError("uv run --with UnityPy ... is required for graphics audit") from exc

    mapping = json.loads(dictionary.read_text())
    paired = sorted(
        (key, val)
        for key, val in zip(mapping["keys"], mapping["values"])
        if key.startswith("b_gp") and val == key + "_en"
    )

    def fingerprint_bundle(path: Path) -> dict:
        result = {}
        for obj in UnityPy.load(str(path)).objects:
            if obj.type.name != "Texture2D":
                continue
            img = obj.read()
            bitmap = img.image.convert("RGBA")
            result[img.m_Name] = {
                "size": list(bitmap.size),
                "decoded_pixel_sha256": hashlib.sha256(bitmap.tobytes()).hexdigest(),
            }
        return result

    groups = []
    for jp, english in paired:
        source = japanese_bundle_root / jp
        target = japanese_bundle_root / english
        if not source.is_file() or not target.is_file():
            groups.append({
                "group": jp, "japanese_exists": source.exists(),
                "english_exists": target.exists(), "status": "missing_resource",
            })
            continue
        japanese = fingerprint_bundle(source)
        localized = fingerprint_bundle(target)
        common = sorted(set(japanese) & set(localized))
        changed = [
            {"name": name, "jp_size": japanese[name]["size"],
             "en_size": localized[name]["size"],
             "jp_sha256": japanese[name]["decoded_pixel_sha256"],
             "en_sha256": localized[name]["decoded_pixel_sha256"]}
            for name in common
            if japanese[name]["decoded_pixel_sha256"] != localized[name]["decoded_pixel_sha256"]
        ]
        group_name = "B_GP" + jp.removeprefix("b_gp") + ".BIN"
        local = ps2_port_root / "BLBRD" / group_name
        groups.append({
            "group": jp, "ps2_container": "BLBRD/" + group_name,
            "localized_ps2_overlay": local.is_file(),
            "jp_textures": len(japanese), "en_textures": len(localized),
            "common_textures": len(common), "changed_textures": changed,
            "japanese_only_names": sorted(set(japanese) - set(localized)),
            "english_only_names": sorted(set(localized) - set(japanese)),
        })
        print(f"{jp}: {len(changed)}/{len(common)} changed textures, "
              f"PS2 overlay={'yes' if local.is_file() else 'NO'}",flush=True)
    return {
        "schema_version": 1, "localized_bundle_pairs": len(paired),
        "bundles_with_differences": sum(bool(g.get("changed_textures")) for g in groups),
        "unported_localized_bundle_families": [
            g["group"] for g in groups
            if g.get("changed_textures") and not g.get("localized_ps2_overlay")
        ],
        "reachability_verified": False,
        "groups": groups,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ps4-bundles", type=Path, required=True)
    p.add_argument("--dictionary", type=Path, required=True)
    p.add_argument("--ps2-port-overlays", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    if args.report.exists():
        raise FileExistsError(args.report)
    result = audit(args.ps4_bundles, args.dictionary, args.ps2_port_overlays)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="groups"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
