"""Whole-image 67.02 -> 67.03 fail-closed binary ownership audit."""
import argparse
from collections import Counter
import json
import mmap
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE,find_record,index_iso

def audit(baseline_path,candidate_path,report):
    with baseline_path.open("rb") as old_file,candidate_path.open("rb") as new_file:
        with mmap.mmap(old_file.fileno(),0,access=mmap.ACCESS_READ) as old,\
             mmap.mmap(new_file.fileno(),0,access=mmap.ACCESS_READ) as new:
            if len(old)!=len(new):
                raise ValueError("Unexpected ISO length change")
            _,a=index_iso(old)
            _,b=index_iso(new)
            first=find_record(a,"SLPM_665.11")
            second=find_record(b,"SLPM_665.11")
            if first.extent!=second.extent or first.record_offset!=second.record_offset:
                raise ValueError("Unowned game-executable relocation")
            if first.size!=report["previous_size"] or second.size!=report["new_size"]:
                raise ValueError("Unexpected translated executable length")
            base=first.extent*SECTOR_SIZE
            allowed={}
            def add(start,end,label):
                for offset in range(start,end):
                    if allowed.setdefault(offset,label)!=label:
                        raise ValueError("Owner overlap at "+hex(offset))
            add(base+0x64,base+0x68,"elf_size")
            add(base+first.size,base+second.size,"appended_text")
            add(first.record_offset+10,first.record_offset+18,"iso_file_size")
            for record in report["owners"]:
                for pos in record["pointers"]:
                    add(base+pos,base+pos+4,record["name"])
            count=Counter()
            for start in range(0,len(old),4*1024*1024):
                a=old[start:start+4*1024*1024]
                b=new[start:start+4*1024*1024]
                if a==b:
                    continue
                for delta,(x,y) in enumerate(zip(a,b)):
                    if x==y:
                        continue
                    label=allowed.get(start+delta)
                    if label is None:
                        raise ValueError("Unowned 67.03 ISO byte "+hex(start+delta))
                    count[label]+=1
            if len(count)<10:
                raise ValueError("Missing expected translated owners")
            return dict(unexplained_changes=0,changed_bytes=sum(count.values()),
                        owners=dict(count),prior_size=first.size,new_size=second.size)
def main():
    parser=argparse.ArgumentParser()
    for label in ("baseline","candidate","owner-report","report"):
        parser.add_argument("--"+label,type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.baseline,args.candidate,json.loads(args.owner_report.read_text()))
    if args.report.exists():
        raise FileExistsError(args.report)
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("67.03 ISO audit:",result["changed_bytes"],"known bytes, 0 unexplained")
if __name__=="__main__":
    main()
