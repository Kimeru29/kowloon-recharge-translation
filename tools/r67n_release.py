"""Compose the fingerprinted r67.15n delta on the immutable cumulative m disc."""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path

from tools.iso9660_patch import find_record, index_iso
from tools.r67m_cumulative import build, sha_file
from tools.translation_overlay import collect_overlay

BASELINE_SHA256 = "3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f"
WHEEL_SHA256 = "d92a980c945b355f270bef75d759c20b95afe3a3f514158a1937ebea41c0e7ee"
GROUP4_SHA256 = "9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def validate_inputs(source: Path, overlay_root: Path, manifest: dict,
                    ps2_adv: Path, ps4_adv: Path):
    """Bind every write to the source disc, owned sources, map and producer hash."""
    if sha_file(source) != BASELINE_SHA256:
        raise ValueError("Cumulative m baseline identity changed")
    if manifest.get("baseline_iso_sha256") != BASELINE_SHA256:
        raise ValueError("Manifest baseline identity changed")
    assets = manifest["assets"]
    rows = {row["path"]: row for row in assets}
    if len(rows) != len(assets):
        raise ValueError("Duplicate manifest asset")
    overlay = collect_overlay([("r67n-proven-script-and-safety-delta", overlay_root)])
    if {entry.path for entry in overlay.entries} != set(rows):
        raise ValueError("Overlay inventory differs from provenance manifest")
    with source.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
        _, records = index_iso(image, base)
        for entry in overlay.entries:
            row = rows[entry.path]
            if entry.sha256 != row["output_sha256"]:
                raise ValueError(f"Overlay output drift: {entry.path}")
            record = find_record(records, entry.embedded_path)
            start = base + record.extent * 2048
            if digest(image[start:start + record.size]) != row["before_sha256"]:
                raise ValueError(f"Installed preimage drift: {entry.path}")
            for root, name, expected in (
                (ps2_adv, entry.path, row["ps2_sha256"]),
                (ps4_adv, entry.path, row["ps4_sha256"]),
                (ps4_adv, row["map_path"], row["map_sha256"]),
            ):
                if sha_file(root / name) != expected:
                    raise ValueError(f"Owned source or map drift: {entry.path}")
    return overlay


def verify_installed(candidate: Path, overlay, original_elf: bytes, graphics: Path) -> tuple[dict, bytes]:
    from tools import r67_15k_approved_lock as approved
    from tools import r67_15g_iso_release as preservation
    from tools.startup_acceptance import verify_startup_candidate

    installed_assets = []
    with candidate.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        exe = find_record(outer, "SLPM_665.11")
        elf = bytes(image[exe.extent * 2048:exe.extent * 2048 + exe.size])
        base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
        _, records = index_iso(image, base)
        for path, expected in (("BLBRD/B_GP001.BIN", WHEEL_SHA256),
                               ("BLBRD/B_GP004.BIN", GROUP4_SHA256)):
            record = find_record(records, path)
            start = base + record.extent * 2048
            data = bytes(image[start:start + record.size])
            if digest(data) != expected:
                raise ValueError(f"Accepted artwork changed: {path}")
            if path.endswith("B_GP004.BIN"):
                approved.verify_installed(elf, data, checksums=False)
        for entry in overlay.entries:
            record = find_record(records, entry.embedded_path)
            start = base + record.extent * 2048
            if digest(image[start:start + record.size]) != entry.sha256:
                raise ValueError(f"Installed script differs from producer: {entry.path}")
            installed_assets.append({"path": entry.path, "iso_offset": start,
                                     "size": record.size, "sha256": entry.sha256})
    locks = preservation._verify_static_locks(original_elf, elf)
    raw_startup = verify_startup_candidate(candidate, graphics)
    static = preservation._static_reports(elf, raw_startup, original_elf)
    if static["startup_scoped"]["checks_passed"] != 155:
        raise ValueError("Startup checks failed")
    return {"installed_assets": installed_assets, "static_locks": locks,
            "static_reports": static, "elf_sha256": digest(elf),
            "wheel_sha256": WHEEL_SHA256, "group4_sha256": GROUP4_SHA256}, elf


def release(source: Path, output_dir: Path, overlay_root: Path, manifest_path: Path,
            ps2_adv: Path, ps4_adv: Path, graphics: Path) -> dict:
    from tools import r67_15k_approved_lock as approved
    from tools.r67_15h_rofs_audit import audit as rofs_audit

    if output_dir.exists():
        raise ValueError("Output directory exists; preserve historical artifacts")
    manifest = json.loads(manifest_path.read_text())
    approved.verify_sources()
    approved.verify_historical_report()
    overlay = validate_inputs(source, overlay_root, manifest, ps2_adv, ps4_adv)
    output_dir.mkdir(parents=True)
    candidate = output_dir / "67.15n-official-script-diagnostic.iso"
    report = build(source, candidate, overlay)
    installed, elf = verify_installed(candidate, overlay, approved.ELF.read_bytes(), graphics)
    report.update(installed)
    report.update(release="r67.15n-official-script-diagnostic", candidate_iso=str(candidate),
                  manifest_sha256=sha_file(manifest_path),
                  rofs=rofs_audit(source, candidate),
                  assets=manifest["assets"], summary=manifest["summary"],
                  runtime_verified=False, gameplay_approved=False)
    if report["rofs"]["mismatches"]:
        raise ValueError("Installed ROFS audit failed")
    (output_dir / "67.15n-official-script-diagnostic.elf").write_bytes(elf)
    (output_dir / "release-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output-dir", "overlay-root", "manifest", "ps2-adv", "ps4-adv", "graphics"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = release(args.source, args.output_dir, args.overlay_root, args.manifest,
                     args.ps2_adv, args.ps4_adv, args.graphics)
    print(json.dumps({k: report[k] for k in ("candidate_iso", "candidate_iso_sha256", "summary")}, indent=2))


if __name__ == "__main__":
    main()
