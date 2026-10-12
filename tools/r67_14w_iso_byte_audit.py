"""Whole-finished-ISO 2GB byte audit for r67.14t -> r67.14w.

Classifies every changed byte: two precise companion event-Y wrapper callsites,
private new Y adaption helpers, ELF PT_LOAD file size, ISO9660 ELF size pair.
Zero changes to established Lion UI, tablet text, graphics, save data or native
AFK state are acceptable.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json,mmap
from collections import Counter
from tools.iso9660_patch import index_iso,find_record,SECTOR_SIZE
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_14w_iso_patch import SOURCE_ISO_SHA,SOURCE_INSTALLED_ELF_SHA
from tools.r67_lion_statue_ui import sha
from tools.r67_14w_scoped_approval_lock import validate_scoped
from tools.r67_14w_restore_opening_bubble_shape import ORIGINAL_RECONSTRUCTION_STORE_VA
from tools.r67_chamber_story_text_only import ELF_BIAS

def audit(baseline:Path,candidate:Path,build:dict)->dict:
    if sha_file(baseline)!=SOURCE_ISO_SHA:raise ValueError("Wrong accepted baseline r67.14t ISO")
    new_hash=sha_file(candidate)
    if new_hash!=build["output_sha256"]:raise ValueError("Candidate SHA differs from build report")
    with baseline.open("rb") as old,candidate.open("rb") as new:
        with mmap.mmap(old.fileno(),0,access=mmap.ACCESS_READ) as a,mmap.mmap(
            new.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):raise ValueError("Finished ISO physical size changed")
            _,old_dirs=index_iso(a);_,new_dirs=index_iso(b)
            x=find_record(old_dirs,"SLPM_665.11");y=find_record(new_dirs,"SLPM_665.11")
            if (x.extent,x.record_offset)!=(y.extent,y.record_offset):
                raise ValueError("Executable extent or record relocated")
            if y.size!=build["elf_size"]:raise ValueError("ELF file size record mismatch")
            base=x.extent*SECTOR_SIZE
            old_elf=bytes(a[base:base+x.size]);new_elf=bytes(b[base:base+y.size])
            if sha(old_elf)!=SOURCE_INSTALLED_ELF_SHA:raise ValueError("Original embedded ELF SHA drift")
            if sha(new_elf)!=build["elf_sha256"]:raise ValueError("New embedded ELF SHA drift")
            scoped=validate_scoped(new_elf,old_elf)
            permitted={}
            def include(start,end,owner):
                for pos in range(start,end):
                    if pos in permitted:raise ValueError(f"Unintended owner overlap at {pos:#x}")
                    permitted[pos]=owner
            include(x.record_offset+10,x.record_offset+18,"iso9660_executable_record_length")
            include(base+0x64,base+0x68,"elf_pt_load_length")
            for va in (ORIGINAL_RECONSTRUCTION_STORE_VA,):
                at=base+va-ELF_BIAS
                include(at,at+4,f"opening_event_bubble_reconstruction_{va:#x}")
            include(base+x.size,base+y.size,"private_opening_bubble_geometry_helper")
            changes=Counter()
            for start in range(0,len(a),8*1024*1024):
                lhs=a[start:start+8*1024*1024];rhs=b[start:start+8*1024*1024]
                if lhs==rhs:continue
                for offset,(first,second) in enumerate(zip(lhs,rhs)):
                    if first==second:continue
                    absolute=start+offset
                    if absolute not in permitted:
                        raise ValueError(f"Unexpected ISO byte {absolute:#x} {first:#04x}->{second:#04x}")
                    changes[permitted[absolute]]+=1
            expected={"iso9660_executable_record_length","elf_pt_load_length",
                      "private_opening_bubble_geometry_helper"}
            expected.update(f"opening_event_bubble_reconstruction_{p[0]:#x}" for p in ((ORIGINAL_RECONSTRUCTION_STORE_VA,),))
            if not all(changes[k]>0 for k in expected):
                raise ValueError("A required bounded change was not applied")
            return {
                "status":"PASS_ALL_WHOLE_ISO_BYTES_ACCOUNTED",
                "approved_prior_iso_sha256":SOURCE_ISO_SHA,
                "candidate_iso_sha256":new_hash,
                "old_elf_size":x.size,"new_elf_size":y.size,
                "physical_iso_bytes_compared":len(a),
                "changed_byte_classification":dict(sorted(changes.items())),
                "unexplained_modified_bytes":0,
                "scoped_existing_approval_preservation":scoped,
                "save_resources_modified":False,
                "runtime_gameplay_verified":False
            }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    for field in ("baseline","candidate","build-report","output"):
        parser.add_argument("--"+field,type=Path,required=True)
    p=parser.parse_args()
    if p.output.exists():raise FileExistsError("Never overwrite previous ISO audit")
    result=audit(p.baseline,p.candidate,json.loads(p.build_report.read_text()))
    p.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="scoped_existing_approval_preservation"},sort_keys=True))
if __name__=="__main__":main()
