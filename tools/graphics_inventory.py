from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


def load_asset_dictionary(path: Path) -> dict[str, str]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    keys = obj.get("keys")
    values = obj.get("values")
    if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
        raise ValueError("Asset dictionary must contain equal-length keys and values arrays")
    return {str(key): str(value) for key, value in zip(keys, values)}


def localized_bundle_aliases(mapping: Mapping[str, str]) -> tuple[str, ...]:
    """Return localization bundle aliases, excluding file-path mappings.

    AssetFileDic_en contains both logical group aliases (e.g. b_gp001 ->
    b_gp001_en) and individual source-path -> localized-path mappings.  Bundle
    aliases are the non-path localized values ending in ``_en``.
    """

    aliases = {
        value
        for key, value in mapping.items()
        if "/" not in key and "\\" not in key and "/" not in value and "\\" not in value and value.endswith("_en")
    }
    return tuple(sorted(aliases))


def inventory_bundle_files(root: Path, aliases: Sequence[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for alias in sorted(aliases):
        path = root / alias
        rows.append({
            "alias": alias,
            "exists": path.is_file(),
            "size": path.stat().st_size if path.is_file() else None,
        })
    return rows


def inventory_unity_textures(path: Path) -> list[dict[str, Any]]:
    """Read Texture2D metadata from one Unity asset/bundle.

    UnityPy is intentionally imported lazily: the repository's unit tests and
    non-graphics tooling do not require this optional reverse-engineering
    dependency.  Pixel payloads are not exported here.
    """

    try:
        import UnityPy  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on local analyst env
        raise RuntimeError("UnityPy is required for --deep graphics inventory") from exc

    env = UnityPy.load(str(path))
    textures: list[dict[str, Any]] = []
    for obj in env.objects:
        if obj.type.name != "Texture2D":
            continue
        texture = obj.read()
        textures.append({
            "name": str(getattr(texture, "m_Name", "")),
            "width": int(getattr(texture, "m_Width", 0)),
            "height": int(getattr(texture, "m_Height", 0)),
            "format": int(getattr(texture, "m_TextureFormat", -1)),
        })
    return sorted(textures, key=lambda row: row["name"])


def build_inventory(dictionary: Path, bundle_root: Path, *, deep: bool = False) -> dict[str, Any]:
    mapping = load_asset_dictionary(dictionary)
    aliases = localized_bundle_aliases(mapping)
    rows = inventory_bundle_files(bundle_root, aliases)
    texture_count = 0
    if deep:
        for row in rows:
            if not row["exists"]:
                row["textures"] = []
                continue
            textures = inventory_unity_textures(bundle_root / str(row["alias"]))
            row["textures"] = textures
            texture_count += len(textures)

    file_like = sum(1 for key, value in mapping.items() if "/" in key and "/" in value)
    return {
        "schema_version": 1,
        "dictionary_pairs": len(mapping),
        "file_like_mappings": file_like,
        "bundle_aliases": len(aliases),
        "bundles_present": sum(1 for row in rows if row["exists"]),
        "bundles_missing": sum(1 for row in rows if not row["exists"]),
        "texture2d_objects": texture_count if deep else None,
        "deep": deep,
        "bundles": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory official remaster localized graphics bundles")
    parser.add_argument("--dictionary", type=Path, required=True)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--deep", action="store_true", help="Use optional UnityPy to enumerate Texture2D metadata")
    args = parser.parse_args()

    report = build_inventory(args.dictionary, args.bundle_root, deep=args.deep)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "bundles"}, sort_keys=True))
    print(f"output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
