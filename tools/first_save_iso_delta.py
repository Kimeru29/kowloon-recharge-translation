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
    interaction_report: dict | None = None, interaction_manifest: dict | None = None,
    graphics_report: dict | None = None,
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
            if (interaction_report is None) != (interaction_manifest is None):
                raise ValueError("Interaction report and manifest must be supplied together")
            if interaction_report is not None:
                if help_report is None:
                    raise ValueError("Interactions require the approved Help translation base")
                if interaction_report["source_help_sha256"] != help_report["english_elf_sha256"]:
                    raise ValueError("Interaction input does not match frozen Help ELF")
                if len(interaction_manifest["owners"]) != len(interaction_report["owners"]):
                    raise ValueError("Interaction manifest/report cardinality drift")
                expected_append += interaction_report["appended_bytes"]
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
            interaction_ptrs: set[int] = set()
            if interaction_manifest is not None:
                for owner in interaction_manifest["owners"]:
                    interaction_ptrs.update(
                        executable_start + ptr + byte
                        for ptr in owner["approved_pointer_offsets"]
                        for byte in range(4)
                    )
                if len(interaction_ptrs) != 4 * interaction_report["aliases"]:
                    raise ValueError("Interaction pointer whitelist count drift")
                if interaction_ptrs & (ptrs | help_ptrs):
                    raise ValueError("Interaction owner overlaps accepted earlier pointers")
            graphic_spans: list[tuple[int,int,str]] = []
            if graphics_report is not None:
                assets=graphics_report.get("assets",[])
                containers=graphics_report.get("containers",[])
                if graphics_report.get("schema_version")!=2 or len(assets)!=85 or len(containers)!=18:
                    raise ValueError("Unexpected approved graphics source cardinality")
                grouped={}
                for entry in assets:
                    grouped.setdefault(entry["group"],[]).append(entry)
                if set(grouped)!={c["group"] for c in containers}:
                    raise ValueError("Graphics container owners diverge")
                _, outer_old=index_iso(r66)
                _, outer_new=index_iso(new)
                cvm_old=find_record(outer_old,"DATA.CVM")
                cvm_new=find_record(outer_new,"DATA.CVM")
                if cvm_old.extent!=cvm_new.extent:
                    raise ValueError("Original CVM extent changed")
                nested=cvm_old.extent*SECTOR_SIZE+0x1800
                _, records_old=index_iso(r66,base=nested)
                _, records_new=index_iso(new,base=nested)
                for container in containers:
                    group=container["group"]
                    path=f"BLBRD/B_GP{group:03d}.BIN"
                    old_rec=find_record(records_old,path)
                    new_rec=find_record(records_new,path)
                    if old_rec.extent!=new_rec.extent or old_rec.size!=new_rec.size:
                        raise ValueError("Graphic container extent/size changed: "+path)
                    loc=nested+old_rec.extent*SECTOR_SIZE
                    pristine=r66[loc:loc+old_rec.size]
                    localized=new[loc:loc+new_rec.size]
                    if hashlib.sha256(pristine).hexdigest()!=container["original_source_sha256"]:
                        raise ValueError("Graphics pristine container SHA mismatch: "+path)
                    if hashlib.sha256(localized).hexdigest()!=container["final_output_sha256"]:
                        raise ValueError("Graphics English container SHA mismatch: "+path)
                    by_index=grouped[group]
                    spans=[]
                    for entry in by_index:
                        o=entry["entry_offset"]
                        end=o+entry["entry_size"]
                        if o<0 or end>len(pristine):
                            raise ValueError("Approved TMX entry out of bounds: "+path)
                        spans.append((o,end))
                        graphic_spans.append((loc+o,loc+end,path))
                    for ia,(a,b) in enumerate(spans):
                        if any(a<c1 and c0<b for c0,c1 in spans[:ia]):
                            raise ValueError("Overlapping graphics TMX ownership")
                    covered=bytearray(len(pristine))
                    for a,b in spans:covered[a:b]=b"\x01"*(b-a)
                    if any(a!=b and not covered[ix] for ix,(a,b) in enumerate(zip(pristine,localized))):
                        raise ValueError("Unapproved pixel/data modification: "+path)
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
                    elif offset in interaction_ptrs:
                        classification = "approved_interaction_pointer"
                    elif any(a<=offset<b for a,b,_path in graphic_spans):
                        classification = "official_english_graphic"
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
            if interaction_report is not None and not counts["approved_interaction_pointer"]:
                raise ValueError("No interaction pointers changed")
            if graphics_report is not None and not counts["official_english_graphic"]:
                raise ValueError("No official English graphic changes found")
            if counts["approved_text_pointer"] == 0:
                raise ValueError("No changed translation pointers")
            return {
                "r66": str(r66_path), "candidate": str(candidate_path),
                "r66_elf_size": first.size, "new_elf_size": second.size,
                "approved_pointer_count": report["pointer_count"],
                "approved_help_descriptors": len(help_ptrs)//4,
                "approved_interaction_pointers": len(interaction_ptrs)//4,
                "approved_graphic_tmx_entries": len(graphic_spans),
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
    p.add_argument("--interaction-report", type=Path)
    p.add_argument("--interaction-manifest", type=Path)
    p.add_argument("--graphics-report", type=Path)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    audit = classify_iso_delta(
        args.approved_r66, args.candidate, json.loads(args.elf_report.read_text()),
        json.loads(args.help_report.read_text()) if args.help_report else None,
        json.loads(args.help_manifest.read_text()) if args.help_manifest else None,
        json.loads(args.interaction_report.read_text()) if args.interaction_report else None,
        json.loads(args.interaction_manifest.read_text()) if args.interaction_manifest else None,
        json.loads(args.graphics_report.read_text()) if args.graphics_report else None
    )
    if args.report.exists():
        raise FileExistsError(args.report)
    args.report.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
    print(json.dumps(audit, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
