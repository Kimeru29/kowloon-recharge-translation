"""Strict whole-ISO delta gate for the r67 first-player inspection/Help polish.

r67's baseline ISO is the same user-playtested copy; all historic graphics,
r66 AFK/L1 code, save structures, ROFS unrelated records must be identical.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
from tools.iso9660_patch import find_record, index_iso, SECTOR_SIZE


def audit_iso_delta(
    baseline_path: Path, candidate_path: Path, inspection_report: dict,
    inspection_manifest: dict, help_report: dict, help_manifest: dict,
    history_report: dict | None = None,
    story_report: dict | None = None,
) -> dict:
    with baseline_path.open("rb") as f, candidate_path.open("rb") as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as base, mmap.mmap(
            g.fileno(),0,access=mmap.ACCESS_READ
        ) as updated:
            if len(base)!=len(updated):
                raise ValueError("Unexpected total ISO size change")
            _,base_entries=index_iso(base)
            _,new_entries=index_iso(updated)
            old=find_record(base_entries,"SLPM_665.11")
            new=find_record(new_entries,"SLPM_665.11")
            if old.extent!=new.extent or old.record_offset!=new.record_offset:
                raise ValueError("Executable relocated unexpectedly")
            exe=old.extent*SECTOR_SIZE
            orig=inspection_report["original_size"]
            append=inspection_report["result_size"]+help_report["appended_bytes"]
            if history_report is not None:
                if history_report["previous_size"] != append:
                    raise ValueError("History shim does not follow approved polished Help")
                if history_report["candidate_size"]-history_report["previous_size"] != history_report["helper_bytes"]:
                    raise ValueError("Unexpected dialogue history helper size")
                append=history_report["candidate_size"]
            if story_report is not None:
                if story_report["original_size"] != append:
                    raise ValueError("Story comment does not follow owned text stages")
                append=story_report["new_size"]
            if old.size!=orig or new.size!=append:
                raise ValueError(f"Unexpected ELF size: {old.size}, {new.size}, {orig}, {append}")
            if help_report["input_sha256"]!=inspection_report["result_elf_sha256"]:
                raise ValueError("Help and inspection passes not chained")
            allowed: dict[int,str] = {}
            def add(start: int,end: int,label:str):
                for i in range(start,end):
                    if i in allowed and allowed[i]!=label:
                        raise ValueError(f"Overlapping approved byte owners at {i:#x}")
                    allowed[i]=label
            add(exe+0x64,exe+0x68,"elf_segment_size")
            add(exe+old.size,exe+new.size,"appended_translation_and_help")
            add(old.record_offset+10,old.record_offset+18,"iso_record_file_size")
            for owner in inspection_report["text_owners"]:
                for ptr in owner["aliases"]:
                    add(exe+ptr,exe+ptr+4,"inspection_pointer")
            for owner in inspection_manifest["fixed_item_pickup_rows"]:
                add(exe+owner["offset"],exe+owner["offset"]+owner["slot_len"],"fixed_item_pickup")
            for page in help_manifest["pages"]:
                off=page["descriptor_offset"]
                add(exe+off,exe+off+4,"help_table_descriptor")
            if history_report is not None:
                caller = history_report["source_jal"]
                add(exe+caller,exe+caller+4,"history_modal_jal")
            if story_report is not None:
                ptr=story_report["pointer_offset"]
                add(exe+ptr,exe+ptr+4,"story_comment_pointer")
            counts: Counter[str]=Counter()
            for start in range(0,len(base),4*1024*1024):
                first=base[start:start+4*1024*1024]
                second=updated[start:start+4*1024*1024]
                if first==second:continue
                for delta,(a,b) in enumerate(zip(first,second)):
                    if a==b:continue
                    pos=start+delta
                    name=allowed.get(pos)
                    if name is None:
                        raise ValueError(f"Unclassified whole-ISO change at 0x{pos:x}")
                    counts[name]+=1
            for required in ("elf_segment_size","appended_translation_and_help",
                "iso_record_file_size","inspection_pointer",
                "fixed_item_pickup","help_table_descriptor"):
                if counts[required]<=0:
                    raise ValueError(f"Expected modified owner absent: {required}")
            if history_report is not None and counts["history_modal_jal"]<=0:
                raise ValueError("History modal trampoline callsite not installed")
            if story_report is not None and counts["story_comment_pointer"]<=0:
                raise ValueError("Expected story comment correction not present")
            return dict(
                original_iso=str(baseline_path),candidate_iso=str(candidate_path),
                previous_elf_size=old.size,new_elf_size=new.size,
                changed_bytes=dict(counts),unclassified_bytes=0
            )


def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--candidate",type=Path,required=True)
    p.add_argument("--inspection-report",type=Path,required=True)
    p.add_argument("--inspection-manifest",type=Path,required=True)
    p.add_argument("--help-report",type=Path,required=True)
    p.add_argument("--help-manifest",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--history-report",type=Path)
    p.add_argument("--story-report",type=Path)
    a=p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    out=audit_iso_delta(
        a.baseline,a.candidate,json.loads(a.inspection_report.read_text()),
        json.loads(a.inspection_manifest.read_text()),json.loads(a.help_report.read_text()),
        json.loads(a.help_manifest.read_text()),
        json.loads(a.history_report.read_text()) if a.history_report else None,
        json.loads(a.story_report.read_text()) if a.story_report else None
    )
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))


if __name__=="__main__":
    main()
