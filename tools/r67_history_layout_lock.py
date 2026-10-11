"""Fail-closed regression guard for the user-approved r67.12 START-history layout.

Checks the four immutable history-rendering owners by SHA-256; unrelated ELF
bytes are allowed to change so other r67 fixes can proceed independently.

Usage:
  python3 -m tools.r67_history_layout_lock --elf local/r67-12-history-compact.elf
  python3 -m tools.r67_history_layout_lock --iso local/r67-candidates/67.12-history-compact-diagnostic.iso

For any *new* r67 ISO, run the second command against THAT candidate before
sharing it or merging its code. This only protects approved rendering bytes;
it does not prove long-history pagination, wrapping, or a completed release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
from typing import Any

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "translations/r67_history_layout_lock.json"
LOCK_ID = "r67.12-approved-start-history-layout"


class HistoryLayoutDriftError(ValueError):
    """The approved history layout has changed without new user approval."""


def read_lock(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != 1 or lock.get("lock_id") != LOCK_ID:
        raise HistoryLayoutDriftError("Unknown or malformed history lock manifest")
    regions = lock.get("locked_regions")
    if not isinstance(regions, list) or len(regions) != 4:
        raise HistoryLayoutDriftError("History lock must protect all four rendering owners")
    previous_end = 0
    names: set[str] = set()
    for region in sorted(regions, key=lambda r: r["offset"]):
        offset, size, digest = region["offset"], region["size"], region["sha256"]
        if (
            not isinstance(offset, int)
            or not isinstance(size, int)
            or offset < previous_end
            or size <= 0
            or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest)
            or region["name"] in names
        ):
            raise HistoryLayoutDriftError("Invalid, duplicated or overlapping history region")
        names.add(region["name"])
        previous_end = offset + size
    return lock


def verify_bytes(executable: bytes | mmap.mmap | memoryview, lock: dict[str, Any]) -> list[str]:
    """Verify locked history owners, deliberately permitting unrelated ELF edits."""
    approved: list[str] = []
    for region in lock["locked_regions"]:
        offset, length = region["offset"], region["size"]
        if len(executable) < offset + length:
            raise HistoryLayoutDriftError(
                f"History lock violation: missing {region['name']} bytes at {offset:#x}"
            )
        actual = hashlib.sha256(executable[offset:offset + length]).hexdigest()
        if actual != region["sha256"]:
            raise HistoryLayoutDriftError(
                f"History lock violation in {region['name']} "
                f"(ELF offset {offset:#x}): {actual} != {region['sha256']}"
            )
        approved.append(region["name"])
    return approved


def verify_elf_file(path: Path, lock: dict[str, Any]) -> list[str]:
    with path.open("rb") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as exe:
            return verify_bytes(exe, lock)


def verify_iso_file(path: Path, lock: dict[str, Any]) -> list[str]:
    """Check the installed executable in the ISO, not a possibly stale staged ELF."""
    with path.open("rb") as file:
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as iso:
            _, entries = index_iso(iso)
            executable = find_record(entries, "SLPM_665.11")
            base = executable.extent * SECTOR_SIZE
            end = base + executable.size
            if end > len(iso):
                raise HistoryLayoutDriftError("ISO executable extent is outside the disc")
            # Slicing a memoryview prevents accidentally hashing unrelated ISO
            # content and avoids making a full copy of the 2GB disc.
            view = memoryview(iso)[base:end]
            try:
                return verify_bytes(view, lock)
            finally:
                view.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--iso", type=Path)
    args = parser.parse_args()
    if not args.elf and not args.iso:
        parser.error("Pass at least one candidate via --elf or --iso")
    lock = read_lock(args.manifest)
    for kind, path, fn in (
        ("ELF", args.elf, verify_elf_file),
        ("ISO", args.iso, verify_iso_file),
    ):
        if path is None:
            continue
        names = fn(path, lock)
        print(f"{kind}: PASS {lock['lock_id']} ({len(names)}/{len(lock['locked_regions'])} regions)")
    print("NOTE: protects the approved single-dialogue layout only; history pagination remains unverified.")


if __name__ == "__main__":
    main()
