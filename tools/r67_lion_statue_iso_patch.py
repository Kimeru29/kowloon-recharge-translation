"""Reflink-clone the approved r67.14q ISO and install only r67.14r ELF deltas.

The shipped ELF has already had ROFS record rewrites applied during the
original r67.14q ISO build. Never replace it wholesale with the staged ELF:
only transfer the precisely whitelisted Lion Statue callsites, ELF PT_LOAD
size and appended private helper. Preserve the original 2GB image and its
entire embedded DATA.CVM byte for byte.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import shutil
import subprocess

from tools.iso9660_patch import (
    SECTOR_SIZE, find_record, index_iso, patch_directory_record,
)
from tools.r67_lion_statue_ui import (
    APPROVED_ELF_SHA256, CALL_SITES, ELF_BIAS, apply, sha,
)

APPROVED_ISO_SHA256 = "3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96"
APPROVED_INSTALLED_ELF_SHA256 = "c9bc345b7cc5353da9180c13785c9331adcfb286387edc56b8afbfbb0a76f5fe"


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build(baseline_iso: Path, source_elf: bytes, candidate_elf: bytes,
          candidate_report: dict, original_build_report: dict,
          output_iso: Path) -> tuple[dict, dict]:
    if output_iso.exists() or output_iso.with_suffix(".incomplete").exists():
        raise FileExistsError("Never overwrite a previous candidate")
    if sha_file(baseline_iso) != APPROVED_ISO_SHA256:
        raise ValueError("Not the exact approved r67.14q ISO")
    expected_candidate, expected_report = apply(source_elf)
    if sha(source_elf) != APPROVED_ELF_SHA256 or expected_candidate != candidate_elf:
        raise ValueError("Unrecognized staged ELF delta")
    if candidate_report != expected_report:
        raise ValueError("Candidate patch report drift")
    if original_build_report["elf_sha256"] != APPROVED_INSTALLED_ELF_SHA256:
        raise ValueError("Original r67.14q ISO build report mismatch")
    changed_positions = [
        i for i, (a, b) in enumerate(zip(source_elf, candidate_elf)) if a != b
    ]
    permitted = set(range(0x64, 0x68))
    for site in CALL_SITES:
        permitted.update(range(site - ELF_BIAS, site - ELF_BIAS + 4))
    if not changed_positions or not set(changed_positions) <= permitted:
        raise ValueError("Unexpected staged executable modification")
    temp = output_iso.with_suffix(".incomplete")
    try:
        clone = subprocess.run(
            ["cp", "-c", str(baseline_iso), str(temp)],
            capture_output=True, text=True, check=False,
        )
        if clone.returncode:
            shutil.copyfile(baseline_iso, temp)
        with temp.open("r+b") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_WRITE) as iso:
            volume, recs = index_iso(iso)
            entry = find_record(recs, "SLPM_665.11")
            if (entry.extent, entry.size) != (
                original_build_report["elf_output_extent"],
                len(source_elf),
            ):
                raise ValueError("Approved executable extent or size changed")
            offset = entry.extent * SECTOR_SIZE
            installed = bytes(iso[offset:offset + entry.size])
            if sha(installed) != APPROVED_INSTALLED_ELF_SHA256:
                raise ValueError("Shipped r67.14q ELF metadata mismatched")
            if (len(candidate_elf) + SECTOR_SIZE - 1) // SECTOR_SIZE != entry.sectors:
                raise ValueError("Diagnostic ELF would require sector relocation")
            # Transfer exact changes only, retaining relocated ROFS metadata.
            for pos in changed_positions:
                if installed[pos] != source_elf[pos]:
                    raise ValueError(f"Shipped ELF preimage drift at {pos:#x}")
                iso[offset + pos] = candidate_elf[pos]
            tail = candidate_elf[len(source_elf):]
            if any(iso[offset + len(source_elf):offset + len(candidate_elf)]):
                raise ValueError("ELF extension would overwrite nonzero ISO bytes")
            iso[offset + len(source_elf):offset + len(candidate_elf)] = tail
            patch_directory_record(iso, entry.record_offset, size=len(candidate_elf))
            new_volume, new_recs = index_iso(iso)
            new_entry = find_record(new_recs, "SLPM_665.11")
            if volume != new_volume or new_entry.extent != entry.extent or new_entry.size != len(candidate_elf):
                raise ValueError("ISO9660 executable record changed unexpectedly")
            installed_candidate = bytes(iso[offset:offset + len(candidate_elf)])
            embedded_sha = sha(installed_candidate)
            if b"SLPM-66511" not in installed_candidate or b"BISLPM-66511Save" not in installed_candidate:
                raise ValueError("ISO save identity mismatch")
            iso.flush()
        if temp.stat().st_size != baseline_iso.stat().st_size:
            raise ValueError("Finished ISO size changed")
        iso_hash = sha_file(temp)
        temp.rename(output_iso)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    full = dict(original_build_report)
    full["elf_size"] = len(candidate_elf)
    full["elf_sha256"] = embedded_sha
    full["output_size"] = output_iso.stat().st_size
    full["output_sha256"] = iso_hash
    full["lion_statue_ui_diagnostic"] = {
        "baseline_iso_sha256": APPROVED_ISO_SHA256,
        "r67_14q_installed_elf_sha256": APPROVED_INSTALLED_ELF_SHA256,
        "elf_native_delta_offsets": [hex(pos) for pos in changed_positions],
        "new_private_helper_bytes": len(tail),
        "iso_record_changed": True,
        "original_rofs_metadata_preserved": True,
        "not_gameplay_approved": True,
    }
    report = {
        "status": "DIAGNOSTIC_PENDING_GAMEPLAY_APPROVAL",
        "baseline_iso_sha256": APPROVED_ISO_SHA256,
        "candidate_iso_sha256": iso_hash,
        "embedded_elf_sha256": embedded_sha,
        "elf_extent": entry.extent,
        "new_elf_size": len(candidate_elf),
        "source_elf_modified_positions": list(map(hex, changed_positions)),
        "appended_helper_bytes": len(tail),
        "original_iso_untouched": True,
        "data_cvm_untouched": True,
        "runtime_verified": False,
        "save_compatibility_runtime_verified": False,
    }
    return report, full


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("baseline-iso", "source-elf", "candidate-elf", "candidate-report",
                "baseline-build-report", "output-iso", "report", "build-report"):
        parser.add_argument("--" + arg, required=True, type=Path)
    a = parser.parse_args()
    if a.report.exists() or a.build_report.exists():
        raise FileExistsError("Do not overwrite prior ISO reports")
    summary, new_build = build(
        a.baseline_iso, a.source_elf.read_bytes(), a.candidate_elf.read_bytes(),
        json.loads(a.candidate_report.read_text()),
        json.loads(a.baseline_build_report.read_text()), a.output_iso,
    )
    a.report.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    a.build_report.write_text(json.dumps(new_build, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
