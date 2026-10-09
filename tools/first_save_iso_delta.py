"""Strict read-only ISO diff gate: approved r66 vs first-save r67 candidate.

Only the approved first-save literal pointers, the PT_LOAD length, newly
appended texts and ELF's outer ISO9660 size fields may differ.  This pins
the entire accepted AFK/L1 renderer and unrelated game data byte-for-byte.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path

from tools.iso9660_patch import index_iso, find_record, SECTOR_SIZE


def classify_iso_delta(
    r66_path: Path, candidate_path: Path, report: dict,
    help_report: dict | None = None, help_manifest: dict | None = None,
) -> dict:
    with r66_path.open("rb") as base_file, candidate_path.open("rb") as candidate_file:
        with (
            mmap.mmap(base_file.fileno(), 0, access=mmap.ACCESS_READ) as r66,
            mmap.mmap(candidate_file.fileno(), 0, access=mmap.ACCESS_READ) as new,
        ):
            if len(r66) != len(new):
                raise ValueError("Whole-game ISO size drift")
            _, older = index_iso(r66)
            _, newer = index_iso(new)
            first = find_record(older, "SLPM_665.11")
            second = find_record(newer, "SLPM_665.11")
            if first.extent != second.extent or first.record_offset != second.record_offset:
                raise ValueError("Executable extent or ISO record moved")
            expected_append = report["appended_bytes"]
            if (help_report is None) != (help_manifest is None):
                raise ValueError("Help report and approved manifest must be supplied together")
            if help_report is not None:
                if help_report["source_p0_sha256"] != report["new_elf_sha256"]:
                    raise ValueError("Help pass starts from wrong P0")
                if help_report["translated_help_pages"] != len(help_manifest["pages"]):
                    raise ValueError("Help approved page cardinality mismatch")
                expected_append += help_report["append_bytes"]
            if second.size - first.size != expected_append:
                raise ValueError("Executable size drift from approved append")
            executable_start = first.extent * SECTOR_SIZE
            if report["append_offset"] != first.size:
                raise ValueError("Manifest does not start at r66 ELF EOF")
            allowed = {
                "exe_segment_size": (executable_start + 0x54 + 16,
                                     executable_start + 0x54 + 20),
                "new_english_payload": (executable_start + first.size,
                                        executable_start + second.size),
                "iso9660_file_size": (first.record_offset + 10,
                                      first.record_offset + 18),
            }
            ptrs = {
                executable_start + ptr + delta
                for owner in report["owners"]
                for ptr in owner["owner_offsets"]
                for delta in range(4)
            }
            help_ptrs: set[int] = set()
            if help_manifest is not None:
                for page in help_manifest["pages"]:
                    owners = [page["descriptor_offset"]]
                    if page["icon_records"]:
                        owners.append(page["metadata_descriptor_offset"])
                    for ptr in owners:
                        help_ptrs.update(executable_start + ptr + delta for delta in range(4))
                if len(help_ptrs) != 4 * help_report["descriptor_aliases"]:
                    raise ValueError("Help alias whitelist count mismatch")
                if ptrs & help_ptrs:
                    raise ValueError("P0 and Help pointer ownership collision")
            counts: Counter[str] = Counter()
            for block_start in range(0, len(r66), 4 << 20):
                old_block = r66[block_start:block_start + (4 << 20)]
                new_block = new[block_start:block_start + (4 << 20)]
                if old_block == new_block:
                    continue
                for byte_index, (before, after) in enumerate(zip(old_block, new_block)):
                    if before == after:
                        continue
                    offset = block_start + byte_index
                    if offset in ptrs:
                        classification = "approved_text_pointer"
                    elif offset in help_ptrs:
                        classification = "approved_help_descriptor"
                    else:
                        classification = next((
                            label for label, (start, end) in allowed.items()
                            if start <= offset < end
                        ), "")
                    if not classification:
                        raise ValueError(f"Unclassified r66/r67 ISO byte drift at 0x{offset:X}")
                    counts[classification] += 1
            for necessary in allowed:
                if counts[necessary] == 0:
                    raise ValueError(f"Missing expected ISO difference: {necessary}")
            if help_report is not None and not counts["approved_help_descriptor"]:
                raise ValueError("No Help descriptor changes in ISO")
            if counts["approved_text_pointer"] == 0:
                raise ValueError("No changed translation pointers")
            return {
                "r66": str(r66_path), "candidate": str(candidate_path),
                "r66_elf_size": first.size, "new_elf_size": second.size,
                "approved_pointer_count": report["pointer_count"],
                "approved_help_descriptors": len(help_ptrs)//4,
                "changed_byte_counts": dict(counts),
                "unclassified_bytes": 0,
            }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("approved_r66", type=Path)
    p.add_argument("candidate", type=Path)
    p.add_argument("--elf-report", type=Path, required=True)
    p.add_argument("--help-report", type=Path)
    p.add_argument("--help-manifest", type=Path)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    audit = classify_iso_delta(
        args.approved_r66, args.candidate, json.loads(args.elf_report.read_text()),
        json.loads(args.help_report.read_text()) if args.help_report else None,
        json.loads(args.help_manifest.read_text()) if args.help_manifest else None
    )
    if args.report.exists():
        raise FileExistsError(args.report)
    args.report.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
