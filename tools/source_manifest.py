from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


def _file_identity(path: Path) -> dict[str, Any]:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": str(path.resolve()),
        "size": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def build_source_manifest(
    ps2_archive: Path,
    ps2_iso: Path,
    ps2_adv_root: Path,
    ps4_pkg: Path,
    ps4_adv_root: Path,
) -> dict[str, Any]:
    for path in (ps2_archive, ps2_iso, ps4_pkg):
        if not path.is_file():
            raise FileNotFoundError(path)
    for path in (ps2_adv_root, ps4_adv_root):
        if not path.is_dir():
            raise NotADirectoryError(path)

    ps2_archive_identity = _file_identity(ps2_archive)
    ps2_iso_identity = _file_identity(ps2_iso)
    ps4_pkg_identity = _file_identity(ps4_pkg)
    ps2_iso_identity["serial"] = "SLPM-66511"
    ps4_pkg_identity["title_id"] = "CUSA27034"

    return {
        "schema_version": 1,
        "invariants": {
            "serial": "SLPM-66511",
            "save_directory": "BISLPM-66511Save",
        },
        "ps2_archive": ps2_archive_identity,
        "ps2_iso": ps2_iso_identity,
        "ps2_adv_root": str(ps2_adv_root.resolve()),
        "ps4_pkg": ps4_pkg_identity,
        "ps4_adv_root": str(ps4_adv_root.resolve()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Record local source identity for reproducible Kowloon builds")
    parser.add_argument("--ps2-archive", type=Path, required=True)
    parser.add_argument("--ps2-iso", type=Path, required=True)
    parser.add_argument("--ps2-adv", type=Path, required=True)
    parser.add_argument("--ps4-pkg", type=Path, required=True)
    parser.add_argument("--ps4-adv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = build_source_manifest(
        args.ps2_archive,
        args.ps2_iso,
        args.ps2_adv,
        args.ps4_pkg,
        args.ps4_adv,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"output={args.output}")
    print(f"ps2_iso_sha256={manifest['ps2_iso']['sha256']}")
    print(f"ps4_pkg_sha256={manifest['ps4_pkg']['sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
