"""Fail-closed whole-disc delta audit from gameplay-approved r67.14q to r67.14r.

Compares ALL ISO bytes (not just ELF) and permits ONLY the two verified
item-name callsite JALs, ELF PT_LOAD file size, appended private helper, and
the ISO9660 ELF record's 32-bit LE/BE file-size fields.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.r67_lion_statue_ui import (
    APPROVED_ELF_SHA256, CALL_SITES, ELF_BIAS, sha,
)
from tools.r67_lion_statue_iso_patch import (
    APPROVED_INSTALLED_ELF_SHA256, APPROVED_ISO_SHA256, sha_file,
)


def audit(original: Path, candidate: Path, patch_report: dict, build_report: dict) -> dict:
    if sha_file(original) != APPROVED_ISO_SHA256:
        raise ValueError("Not the exact approved r67.14q original ISO")
    with original.open("rb") as old, candidate.open("rb") as new:
        with mmap.mmap(old.fileno(), 0, access=mmap.ACCESS_READ) as a, mmap.mmap(
            new.fileno(), 0, access=mmap.ACCESS_READ
        ) as b:
            if len(a) != len(b):
                raise ValueError("Finished ISO file size changed")
            _, old_recs = index_iso(a)
            _, new_recs = index_iso(b)
            old_exe = find_record(old_recs, "SLPM_665.11")
            new_exe = find_record(new_recs, "SLPM_665.11")
            if (old_exe.extent, old_exe.record_offset) != (
                new_exe.extent, new_exe.record_offset
            ):
                raise ValueError("Executable extent or record location changed")
            if (new_exe.size, old_exe.size) != (
                build_report["elf_size"], patch_report["new_elf_size"] - patch_report["appended_helper_bytes"]
            ):
                raise ValueError("ELF size report or ISO9660 record drift")
            base = old_exe.extent * SECTOR_SIZE
            allowed: dict[int, str] = {}

            def permit(start: int, end: int, owner: str) -> None:
                for pos in range(start, end):
                    if pos in allowed:
                        raise ValueError(f"Overlapping declared owners at {pos:#x}")
                    allowed[pos] = owner

            permit(old_exe.record_offset + 10, old_exe.record_offset + 18, "iso9660_elf_size")
            permit(base + 0x64, base + 0x68, "elf_pt_load_size")
            for site in CALL_SITES:
                permit(base + site - ELF_BIAS, base + site - ELF_BIAS + 4, f"item_name_call_{site:#x}")
            permit(base + old_exe.size, base + new_exe.size, "new_private_helper")
            differences = Counter()
            examples: dict[str, list[str]] = {}
            for block in range(0, len(a), 8 * 1024 * 1024):
                lhs = a[block:block + 8 * 1024 * 1024]
                rhs = b[block:block + 8 * 1024 * 1024]
                if lhs == rhs:
                    continue
                for index, (before, after) in enumerate(zip(lhs, rhs)):
                    if before == after:
                        continue
                    absolute = block + index
                    owner = allowed.get(absolute)
                    if owner is None:
                        raise ValueError(
                            f"Unclassified finished-ISO difference at {absolute:#x}: "
                            f"{before:#04x}->{after:#04x}"
                        )
                    differences[owner] += 1
                    sample = examples.setdefault(owner, [])
                    if len(sample) < 16:
                        sample.append(hex(absolute))
            required = {"iso9660_elf_size", "elf_pt_load_size", "new_private_helper"}
            required.update(f"item_name_call_{site:#x}" for site in CALL_SITES)
            if any(differences[r] == 0 for r in required):
                raise ValueError(f"Expected native delta owner missing: {differences}")
            if bytes(a[base:base + 4]) != bytes.fromhex("7f454c46") or bytes(b[base:base + 4]) != bytes.fromhex("7f454c46"):
                raise ValueError("ELF image identity drift")
            if sha(bytes(a[base:base + old_exe.size])) != APPROVED_INSTALLED_ELF_SHA256:
                raise ValueError("Original installed ELF hash drift")
            new_elf = bytes(b[base:base + new_exe.size])
            if sha(new_elf) != build_report["elf_sha256"]:
                raise ValueError("Candidate installed ELF hash drift")
            return {
                "status": "PASS_NO_UNCLASSIFIED_WHOLE_ISO_DIFFERENCES",
                "baseline_iso_sha256": APPROVED_ISO_SHA256,
                "candidate_iso_sha256": sha_file(candidate),
                "baseline_elf_size": old_exe.size,
                "candidate_elf_size": new_exe.size,
                "original_iso_size": len(a),
                "candidate_iso_size": len(b),
                "changed_bytes_by_owner": dict(differences),
                "changed_byte_examples_by_owner": examples,
                "unclassified_bytes": 0,
                "runtime_verified": False,
                "release_approved": False,
            }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "patch-report", "build-report", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    options = parser.parse_args()
    if options.output.exists():
        raise FileExistsError("Never replace an existing audit")
    result = audit(
        options.baseline, options.candidate,
        json.loads(options.patch_report.read_text()),
        json.loads(options.build_report.read_text()),
    )
    options.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
