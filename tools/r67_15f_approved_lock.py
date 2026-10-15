"""Immutable gameplay-approval lock for r67.15f.

The gameplay-approved image is a historical baseline, not an input to patch in
place. Changes to its native executable, UI atlas, or release-generator code
must be explicitly reviewed and re-approved before the lock may be updated.
The validator does not accept blanket exclusions or regenerate expected hashes.
"""
from __future__ import annotations

import hashlib
import json
import mmap
from pathlib import Path

from tools.iso9660_patch import index_iso, find_record
from tools.tmx import find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/R67_15F_APPROVED_LOCK.json"
ISO = ROOT / "local/r67-candidates/67.15f-item-panel-layout.iso"
BUFFER_SIZE = 16 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_manifest() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest["release"] != "r67.15f" or manifest["approval_status"] != "gameplay-approved":
        raise ValueError("Unrecognized approved presentation baseline")
    return manifest


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(BUFFER_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_source_owners() -> dict:
    """Reject undocumented changes to source that generates accepted UI."""
    manifest = load_manifest()
    for name, expected in manifest["tool_sha256"].items():
        actual = hash_file(ROOT / name)
        if actual != expected:
            raise ValueError(f"Approved r67.15f implementation changed: {name}")
    return manifest["tool_sha256"]


def verify_elf_and_art(elf: bytes, atlas: bytes) -> dict:
    """Verify exact approved output plus protected sprite texture owners."""
    manifest = load_manifest()
    if sha256(elf) != manifest["installed_elf_sha256"]:
        raise ValueError("Approved r67.15f native executable changed")
    if sha256(atlas) != manifest["installed_group4_sha256"]:
        raise ValueError("Approved r67.15f Group-4 UI artwork changed")
    for name, expected in manifest["protected_tmx_sha256"].items():
        entry = find_tmx_entry(atlas, name)
        fragment = atlas[entry.base_offset:entry.base_offset + entry.chunk_size]
        if sha256(fragment) != expected:
            raise ValueError(f"Approved UI sprite changed: {name}")
    for offset, expected in manifest["native_hook_words"].items():
        loc = int(offset, 16)
        actual = elf[loc:loc + 4].hex()
        if actual != expected:
            raise ValueError(f"Approved r67.15f native owner changed at {offset}")
    return {"installed_elf": manifest["installed_elf_sha256"],
            "installed_group4": manifest["installed_group4_sha256"],
            "protected_textures": len(manifest["protected_tmx_sha256"])}


def verify_approved_iso(path: Path = ISO) -> dict:
    """Stream the entire disc SHA; then inspect installed executable and art."""
    manifest = load_manifest()
    if path.stat().st_size != manifest["iso_size_bytes"]:
        raise ValueError("Approved ISO physical size changed")
    actual = hash_file(path)
    if actual != manifest["iso_sha256"]:
        raise ValueError("Approved r67.15f ISO SHA-256 mismatch")
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, outer = index_iso(image)
        executable = find_record(outer, "SLPM_665.11")
        cvm = find_record(outer, "DATA.CVM")
        cvm_start = cvm.extent * 2048 + 0x1800
        _, inside = index_iso(image, cvm_start)
        group = find_record(inside, "BLBRD/B_GP004.BIN")
        elf_start = executable.extent * 2048
        art_start = cvm_start + group.extent * 2048
        return {"iso": actual, **verify_elf_and_art(
            bytes(image[elf_start:elf_start + executable.size]),
            bytes(image[art_start:art_start + group.size]))}


def assert_unchanged_from_approved(
    baseline_elf: bytes, proposed_elf: bytes,
    baseline_art: bytes, proposed_art: bytes,
) -> None:
    """Fail closed. User and reviewer must approve a new lock for new owners."""
    verify_elf_and_art(baseline_elf, baseline_art)
    if proposed_elf != baseline_elf:
        raise ValueError("Proposed build modifies approved r67.15f executable")
    if proposed_art != baseline_art:
        raise ValueError("Proposed build modifies approved r67.15f item UI artwork")
