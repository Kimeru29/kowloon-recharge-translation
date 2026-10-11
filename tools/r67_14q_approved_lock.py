"""Reusable visual-acceptance lock for r67.14q automatic companion comments.

Verifies protected *owners*, not the whole ISO: future independent Lion Statue
UI fixes may change other bytes without invalidating r67.14q gameplay approval.

Usage:
  python3 -m tools.r67_14q_approved_lock --elf path/to/next.elf
  python3 -m tools.r67_14q_approved_lock --iso path/to/next.iso --build-report path/to/next-build.json

Do not regenerate translations/r67_14q_approved_lock.json to make failing checks
pass. A genuine user-approved change requires an explicit reviewed amendment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from tools.localization import encode_ps2_english
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO, ELF_SEGMENT_VA

MANIFEST = Path(__file__).resolve().parents[1] / "translations/r67_14q_approved_lock.json"


def verify_approved(elf: bytes, manifest: dict) -> dict:
    """Fail closed on drift to known approved automatic-event, renderer or AFK owners."""
    if manifest.get("schema_version") != 1:
        raise ValueError("Unknown r67 approved lock schema")
    required = {"regions", "approved_words", "wide_text_by_pointer_alias"}
    if not required.issubset(manifest):
        raise ValueError("Incomplete approved lock")
    if len(elf) < manifest["baseline_elf_size"]:
        raise ValueError("Approved native executable was truncated")
    if elf[:4] != b"\x7fELF":
        raise ValueError("Not a valid ELF image")

    checked_regions = 0
    for region in manifest["regions"]:
        name = region["name"]
        offset, size = region["file_offset"], region["byte_length"]
        if offset < 0 or size <= 0 or offset + size > len(elf):
            raise ValueError(f"Approved {name} owner is outside the ELF")
        actual = hashlib.sha256(memoryview(elf)[offset:offset + size]).hexdigest()
        if actual != region["sha256"]:
            raise ValueError(f"Approved {name} owner drifted at ELF offset {offset:#x}")
        checked_regions += 1

    for raw, expected in manifest["approved_words"].items():
        offset = int(raw, 16)
        if offset < 0 or offset + 4 > len(elf):
            raise ValueError(f"Approved native word {raw} outside the ELF")
        actual = struct.unpack_from("<I", elf, offset)[0]
        if actual != int(expected, 16):
            raise ValueError(f"Approved native word drift at {raw}: {actual:#x} != {expected}")

    for raw_alias, line in manifest["wide_text_by_pointer_alias"].items():
        alias = int(raw_alias, 16)
        pointer = struct.unpack_from("<I", elf, alias)[0]
        offset = ELF_SEGMENT_FO + pointer - ELF_SEGMENT_VA
        expected = encode_ps2_english(line, collapse_spaces=False) + b"\x00"
        if offset < 0 or offset + len(expected) > len(elf):
            raise ValueError(f"Approved dialogue {raw_alias} pointer outside the ELF")
        if elf[offset:offset + len(expected)] != expected:
            raise ValueError(f"Approved dialogue text drift at alias {raw_alias}")

    for identity in (b"SLPM-66511", b"BISLPM-66511Save"):
        if identity not in elf:
            raise ValueError(f"Approved game/save identity is missing: {identity!r}")

    return {
        "status": "PASS_R67_14Q_VISUALLY_APPROVED_OWNERS",
        "approved_regions": checked_regions,
        "approved_native_words": len(manifest["approved_words"]),
        "approved_dialogue_lines": len(manifest["wide_text_by_pointer_alias"]),
        "elf_sha256": hashlib.sha256(elf).hexdigest(),
        "approved_baseline_elf_sha256": manifest["baseline_elf_sha256"],
        "whole_elf_is_baseline": hashlib.sha256(elf).hexdigest() == manifest["baseline_elf_sha256"],
        "other_unrelated_ui_changes_are_allowed": True,
    }


def extract_iso_elf(iso_path: Path, manifest: dict, build_report: Path | None = None) -> bytes:
    """Read embedded ELF without scanning/rewriting the 2GB ISO."""
    if build_report is not None:
        report = json.loads(build_report.read_text())
        extent, size = report["elf_output_extent"], report["elf_size"]
    else:
        extent, size = manifest["baseline_iso_elf_extent"], manifest["baseline_elf_size"]
    if not isinstance(extent, int) or not isinstance(size, int) or extent <= 0 or size < manifest["baseline_elf_size"]:
        raise ValueError("Invalid ISO ELF extent/length")
    with iso_path.open("rb") as stream:
        if extent * 2048 + size > stream.seek(0, 2):
            raise ValueError("ISO ELF extent exceeds end of image")
        stream.seek(extent * 2048)
        elf = stream.read(size)
    if len(elf) != size or elf[:4] != b"\x7fELF":
        raise ValueError("Embedded ELF not present at the reported ISO extent")
    return elf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--elf", type=Path)
    mode.add_argument("--iso", type=Path)
    parser.add_argument("--build-report", type=Path,
                        help="Required for future ISOs if their ELF extent/size changes.")
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    options = parser.parse_args()
    manifest = json.loads(options.manifest.read_text())
    if options.elf is not None:
        content = options.elf.read_bytes()
    else:
        content = extract_iso_elf(options.iso, manifest, options.build_report)
    print(json.dumps(verify_approved(content, manifest), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
