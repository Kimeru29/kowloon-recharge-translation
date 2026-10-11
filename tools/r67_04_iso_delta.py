"""Exhaustive byte-difference classifier for the complete 67.03 -> 67.04 ISOs."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.r67_04_layout import NATIVE_ROTATE_SLOT,ROTATE_SLOT_SIZE

def audit(baseline: Path, current: Path, info: dict) -> dict:
    with baseline.open("rb") as fa, current.open("rb") as fb:
        with mmap.mmap(fa.fileno(),0,access=mmap.ACCESS_READ) as a,\
             mmap.mmap(fb.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):
                raise ValueError("Complete ISO image length changed")
            _,prev=index_iso(a)
            _,now=index_iso(b)
            pa=find_record(prev,"SLPM_665.11");pb=find_record(now,"SLPM_665.11")
            if pa.extent!=pb.extent or pa.record_offset!=pb.record_offset:
                raise ValueError("Translated game ELF moved unexpectedly")
            if pa.size!=info["previous_size"] or pb.size!=info["new_size"]:
                raise ValueError("Executable size drifted")
            exe=pa.extent*SECTOR_SIZE
            permitted={}
            def allow(lo:int,hi:int,label:str):
                for pos in range(lo,hi):
                    if pos in permitted:
                        raise ValueError("Ownership collision")
                    permitted[pos]=label
            allow(exe+0x64,exe+0x68,"PT_LOAD_filesz")
            allow(exe+NATIVE_ROTATE_SLOT,exe+NATIVE_ROTATE_SLOT+ROTATE_SLOT_SIZE,"rotation_prompt")
            for row in info["basic_attack_rows"]:
                pos=exe+int(row["owner"],16)
                allow(pos,pos+4,f"Basic_Attack_{row['row']}")
            allow(exe+pa.size,exe+pb.size,"appended_text")
            allow(pa.record_offset+10,pa.record_offset+18,"ISO9660_size")
            counts=Counter()
            for block in range(0,len(a),4*1024*1024):
                before=a[block:block+4*1024*1024]
                after=b[block:block+4*1024*1024]
                if before==after:continue
                for j,(x,y) in enumerate(zip(before,after)):
                    if x!=y:
                        at=block+j;label=permitted.get(at)
                        if label is None:
                            raise ValueError(f"Unowned changed ISO byte {at:#x}")
                        counts[label]+=1
            if not counts["rotation_prompt"] or not counts["ISO9660_size"]:
                raise ValueError("Expected localized owners absent")
            if not counts["appended_text"]:
                raise ValueError("Missing new translated text")
            return dict(unclassified_bytes=0,changed_bytes=sum(counts.values()),
                        owner_counts=dict(counts),original_size=pa.size,new_size=pb.size)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ("baseline","candidate","owner-report","report"):
        p.add_argument("--"+field,type=Path,required=True)
    args=p.parse_args()
    if args.report.exists():raise FileExistsError(args.report)
    result=audit(args.baseline,args.candidate,json.loads(args.owner_report.read_text()))
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(f"{result['changed_bytes']} owned ISO bytes, 0 unexplained")
if __name__=="__main__":
    main()
