"""User-approved r67.15k image and source lock.

This record supplements the immutable diagnostic report; it does not mutate
the release artifact or rewrite the recorded pre-approval test evidence.
Only explicitly approved replacement releases may establish a new baseline.
"""
from __future__ import annotations

import hashlib
import json
import mmap
from pathlib import Path

from tools.iso9660_patch import find_record, index_iso
from tools.tmx import find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/R67_15K_APPROVED_LOCK.json"
ISO = ROOT / "local/r67-candidates/67.15k-description-word-wrap.iso"
ELF = ROOT / "local/r67-15k-description-word-wrap.elf"
REPORT = ROOT / "local/r67-15k-description-word-wrap.json"
CHUNK_SIZE = 16 * 1024 * 1024


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest() -> dict:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if (data.get("release"), data.get("approval_status")) != ("r67.15k", "gameplay-approved"):
        raise ValueError("The r67.15k approval identity was changed")
    return data


def verify_sources() -> dict:
    """Prevent unreviewed changes to any g-k producer or existing regression."""
    hashes = manifest()["source_sha256"]
    for relative_path, expected in hashes.items():
        file = ROOT / relative_path
        if sha256_file(file) != expected:
            raise ValueError(f"Approved source or regression changed: {relative_path}")
    return {"verified_source_files": len(hashes)}


def verify_installed(elf: bytes, group4: bytes, *, checksums: bool = True) -> dict:
    """Assert exact executable and atlas, including individual protected owners."""
    expected = manifest()
    if checksums and sha256(elf) != expected["installed_elf_sha256"]:
        raise ValueError("Gameplay-approved r67.15k executable changed")
    if checksums and sha256(group4) != expected["installed_group4_sha256"]:
        raise ValueError("Gameplay-approved r67.15k UI artwork changed")
    for offset, original in expected["protected_native_call_words"].items():
        actual = elf[int(offset, 16):int(offset, 16) + 4].hex()
        if actual != original:
            raise ValueError(f"Approved r67.15k text callback changed at {offset}")
    for name, hash_value in expected["protected_tmx_sha256"].items():
        entry = find_tmx_entry(group4, name)
        chunk = group4[entry.base_offset:entry.base_offset + entry.chunk_size]
        if sha256(chunk) != hash_value:
            raise ValueError(f"Protected sprite {name} changed")
    return {
        "elf_sha256": sha256(elf),
        "group4_sha256": sha256(group4),
        "locked_native_calls": len(expected["protected_native_call_words"]),
        "locked_tmx": len(expected["protected_tmx_sha256"]),
    }


def verify_historical_report() -> dict:
    """Historical build evidence stays immutable; new approval is separate."""
    expected = manifest()
    if sha256_file(REPORT) != expected["original_build_report_sha256"]:
        raise ValueError("Historical r67.15k build report changed")
    report = json.loads(REPORT.read_text())
    if report["candidate_elf_sha256"] != expected["installed_elf_sha256"]:
        raise ValueError("Original build report executable identity mismatched")
    if report["candidate_iso_sha256"] != expected["iso_sha256"]:
        raise ValueError("Original build report ISO identity mismatched")
    if (report["gameplay_approved"], report["runtime_verified"]) != (False, False):
        raise ValueError("Historical diagnostic evidence was rewritten after approval")
    proof = report["whole_iso_audit"]
    if (proof["complete_disc_bytes_compared"], proof["unexplained_bytes"]) != (2_095_382_528, 0):
        raise ValueError("Full-image release audit is missing or incomplete")
    if report["startup_scoped"]["checks_passed"] != 155:
        raise ValueError("Accepted bounded startup validation changed")
    if (len(report["history"]["verified_regions"]),
        report["save"]["native_save_descriptors"]) != (4, 15):
        raise ValueError("Historical save or story-layout proof changed")
    if not proof["data_cvm_byte_identical"] or not proof["all_art_and_adv_resources_unchanged"]:
        raise ValueError("Approved visual resources were not preserved")
    return {"historical_report_unchanged": True, "approved_2gb_audit": True,
            "startup": "155/155 scoped; raw 154/155 documented legacy warning",
            "save_descriptors": 15, "history_regions": 4}


def verify_approved_iso() -> dict:
    expected = manifest()
    if ISO.stat().st_size != expected["iso_size_bytes"]:
        raise ValueError("Approved r67.15k ISO length mismatch")
    if sha256_file(ISO) != expected["iso_sha256"]:
        raise ValueError("Approved r67.15k ISO checksum mismatch")
    with ISO.open("rb") as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as image:
        _, records = index_iso(image)
        exe = find_record(records, "SLPM_665.11")
        cvm = find_record(records, "DATA.CVM")
        nested_start = cvm.extent * 2048 + 0x1800
        _, nested = index_iso(image, nested_start)
        group = find_record(nested, "BLBRD/B_GP004.BIN")
        elf_start = exe.extent * 2048
        art_start = nested_start + group.extent * 2048
        installed_elf = bytes(image[elf_start:elf_start + exe.size])
        installed_art = bytes(image[art_start:art_start + group.size])
    if installed_elf != ELF.read_bytes():
        raise ValueError("Installed game executable is not the approved staged executable")
    return {"iso_sha256": expected["iso_sha256"], **verify_installed(installed_elf, installed_art)}


def assert_preserved(*, original_elf: bytes, modified_elf: bytes,
                     original_art: bytes, modified_art: bytes) -> None:
    """A new build cannot silently modify r67.15k's approved presentation."""
    verify_installed(original_elf, original_art)
    if modified_elf != original_elf:
        raise ValueError("Candidate changed gameplay-approved r67.15k executable; needs new approval")
    if modified_art != original_art:
        raise ValueError("Candidate changed gameplay-approved r67.15k UI artwork; needs new approval")
