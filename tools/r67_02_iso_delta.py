"""Fail-closed whole-ISO ownership audit for numeric prerelease 67.02.

Compares 67.01 to 67.02 and accepts ONLY source-verified inspection/comment
pointer records, 15 Basic Attack text pointers, two fixed pickup slots, one
independent START dialogue constructor JAL, appended PT_LOAD text/shim, and
ISO9660/ELF file-length words. Never whitelist r66 AFK/L1 geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso

BASE_SHA = "bff7786abd7dc21c85e4a8e75502442a0ad63ed776c9ca14ce0a72277110755f"

def audit(base_path:Path,new_path:Path,text:dict,history:dict)->dict:
    if history["previous_sha256"]!=text["sha256"]:
        raise ValueError("History renderer not chained after 67.02 text")
    if history["candidate_size"]!=text["new_length"]+history["helper_bytes"]+3:
        # In this build ELF file length is 8794697 (mod 4 = 1), plus 3 padding.
        raise ValueError("History native helper size/padding changed")
    with base_path.open("rb") as fa,new_path.open("rb") as fb:
        with mmap.mmap(fa.fileno(),0,access=mmap.ACCESS_READ) as a, mmap.mmap(fb.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):raise ValueError("ISO size mismatch")
            _,ar=index_iso(a);_,br=index_iso(b)
            p=find_record(ar,"SLPM_665.11");q=find_record(br,"SLPM_665.11")
            if p.extent!=q.extent or p.record_offset!=q.record_offset or p.size!=text["prior_length"] or q.size!=history["candidate_size"]:
                raise ValueError("PS2 executable record changed unexpectedly")
            exe=p.extent*SECTOR_SIZE
            allowed:dict[int,str]={}
            def take(start:int,end:int,key:str):
                for x in range(start,end):
                    prior=allowed.setdefault(x,key)
                    if prior!=key: raise ValueError(f"Whitelist overlaps: {prior} != {key} at {x:#x}")
            take(exe+0x64,exe+0x68,"elf_ptload_size")
            take(exe+text["prior_length"],exe+history["candidate_size"],"approved_append")
            take(p.record_offset+10,p.record_offset+18,"iso9660_file_size")
            for owner in text["changes"]:
                key="fixed_item" if owner["name"].startswith("pickup_") else "localized_pointer"
                for offset in owner["pointer_offsets"]:
                    take(exe+offset,exe+offset+(24 if key=="fixed_item" else 4),key)
            for offset in text["basic_pointer_offsets"]:
                take(exe+offset,exe+offset+4,"basic_help_pointer")
            take(exe+history["source_jal"],exe+history["source_jal"]+4,"start_history_jal")
            changed=Counter()
            for start in range(0,len(a),4*1024*1024):
                va=a[start:start+4*1024*1024];vb=b[start:start+4*1024*1024]
                if va==vb:continue
                for delta,(x,y) in enumerate(zip(va,vb)):
                    if x==y:continue
                    pos=start+delta
                    label=allowed.get(pos)
                    if label is None:
                        raise ValueError(f"Unexplained 67.02 ISO mutation at {pos:#x}")
                    changed[label]+=1
            for required in ("elf_ptload_size","approved_append","iso9660_file_size","localized_pointer","fixed_item","basic_help_pointer","start_history_jal"):
                if not changed[required]:
                    raise ValueError(f"67.02 expected owner unchanged: {required}")
            return dict(baseline=str(base_path),candidate=str(new_path),original_size=p.size,new_size=q.size,
                delta_bytes=dict(changed),unexplained_changes=0)

def main():
    p=argparse.ArgumentParser()
    for n in ("baseline","candidate","text-report","history-report","report"):
        p.add_argument("--"+n,type=Path,required=True)
    o=p.parse_args()
    if o.report.exists():raise FileExistsError(o.report)
    report=audit(o.baseline,o.candidate,json.loads(o.text_report.read_text()),json.loads(o.history_report.read_text()))
    o.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print(json.dumps(report,sort_keys=True))
if __name__=="__main__": main()
