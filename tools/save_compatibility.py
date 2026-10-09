"""Prepare and verify disposable PS2 memory-card images for cross-release tests.

Never writes to the source card, never launches PCSX2, and does not claim
that a card contains a valid in-game save. Runtime verification is manual.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from pathlib import Path


MAGIC = b"Sony PS2 Memory Card Format "
CHUNK_BYTES = 1024 * 1024


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def _card_header(path: Path) -> None:
    with path.open("rb") as stream:
        if not stream.read(len(MAGIC)).startswith(MAGIC):
            raise ValueError(f"Not a formatted PS2 memory-card image: {path}")


def _same_file_state(before: os.stat_result, after: os.stat_result) -> bool:
    return (
        before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns
    ) == (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns
    )


def snapshot(source: Path, destination: Path) -> dict:
    """Create an immutable reference and independent writable clones.

    The destination must not exist; this function never overwrites a prior
    reference or PCSX2 test save. Source is read-only throughout.
    """
    if source.is_symlink() or not source.is_file():
        raise ValueError("Source must be an existing, non-symlink card image")
    _card_header(source)
    initial_stat = source.stat()
    initial_hash = digest(source)
    if destination.exists():
        raise FileExistsError(f"Snapshot already exists: {destination}")

    destination.mkdir(parents=True, exist_ok=False)
    reference = destination / "reference.ps2"
    original_clone = destination / "r66.ps2"
    candidate_clone = destination / "candidate.ps2"

    try:
        with source.open("rb") as input_file, reference.open("xb") as output_file:
            shutil.copyfileobj(input_file, output_file, CHUNK_BYTES)
        if digest(reference) != initial_hash:
            raise OSError("Reference copy does not match source SHA-256")
        for clone in (original_clone, candidate_clone):
            with reference.open("rb") as input_file, clone.open("xb") as output_file:
                shutil.copyfileobj(input_file, output_file, CHUNK_BYTES)
            if digest(clone) != initial_hash:
                raise OSError(f"Clone does not match source SHA-256: {clone}")

        if not _same_file_state(initial_stat, source.stat()) or digest(source) != initial_hash:
            raise OSError("Source card changed while the snapshot was created")

        reference.chmod(0o400)
        manifest = {
            "schema": 1,
            "source_path": str(source.absolute()),
            "source_sha256_at_snapshot": initial_hash,
            "size_bytes": initial_stat.st_size,
            "reference": reference.name,
            "r66_test_card": original_clone.name,
            "candidate_test_card": candidate_clone.name,
            "game_save_verified": False,
            "runtime_cross_release_verified": False,
        }
        with (destination / "manifest.json").open("x", encoding="utf-8") as output_file:
            json.dump(manifest, output_file, indent=2, sort_keys=True)
            output_file.write("\n")
        return manifest
    except BaseException:
        # Cleanup touches only the newly created destination.
        shutil.rmtree(destination)
        raise


def verify(destination: Path, *, preflight: bool = False) -> dict:
    """Verify immutable baseline; optionally verify both unused clones.

    After PCSX2 saves to a clone, it is expected to have a different hash.
    """
    manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("Unknown save-compatibility manifest schema")
    expected_hash = manifest["source_sha256_at_snapshot"]
    reference = destination / manifest["reference"]
    if digest(reference) != expected_hash or reference.stat().st_size != manifest["size_bytes"]:
        raise ValueError("Golden reference card has changed")
    if preflight:
        for key in ("r66_test_card", "candidate_test_card"):
            if digest(destination / manifest[key]) != expected_hash:
                raise ValueError(f"Disposable clone was already modified: {key}")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("snapshot", help="Copy a quiescent formatted card")
    make.add_argument("--source", type=Path, required=True)
    make.add_argument("--destination", type=Path, required=True)
    check = commands.add_parser("verify", help="Check golden reference integrity")
    check.add_argument("--destination", type=Path, required=True)
    check.add_argument("--preflight", action="store_true",
                       help="Also require both disposable cards to match reference")
    args = parser.parse_args()
    manifest = (snapshot(args.source, args.destination) if args.command == "snapshot"
                else verify(args.destination, preflight=args.preflight))
    print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
