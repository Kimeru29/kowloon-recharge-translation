"""r67.14t exhaustive WHOLE 2-GB finished-ISO difference audit against approved q.

The only legal deltas are ELF length, two Lion item-name callsites,
six Stone tablet inscription pointer owners, appended native helper/strings,
and both endian copies of the ISO9660 executable size. Fail closed everywhere.
"""
from __future__ import annotations
import argparse,hashlib,json,mmap
from collections import Counter
from pathlib import Path
from tools.iso9660_patch import SECTOR_SIZE,index_iso,find_record
from tools.r67_lion_statue_iso_patch import APPROVED_ISO_SHA256,APPROVED_INSTALLED_ELF_SHA256,sha_file
from tools.r67_lion_statue_ui import CALL_SITES,ELF_BIAS,sha
from tools.r67_14t_stone_tablet_fit import COMPACT_INSCRIPTION_TEXT,assert_all_tablets_fit
from tools.r67_14q_approved_lock import MANIFEST,verify_approved

def audit(previous:Path,latest:Path,build_report:dict)->dict:
    if sha_file(previous)!=APPROVED_ISO_SHA256:raise ValueError("Approved q SHA drift")
    expected=build_report["output_sha256"]
    candidate_hash=sha_file(latest)
    if candidate_hash!=expected:raise ValueError("Candidate ISO does not match build report")
    with previous.open("rb") as before,latest.open("rb") as after:
        with mmap.mmap(before.fileno(),0,access=mmap.ACCESS_READ) as a,mmap.mmap(
            after.fileno(),0,access=mmap.ACCESS_READ) as b:
            if len(a)!=len(b):raise ValueError("ISO total file size changed")
            _,a_records=index_iso(a);_,b_records=index_iso(b)
            old=find_record(a_records,"SLPM_665.11");new=find_record(b_records,"SLPM_665.11")
            if (old.extent,old.record_offset)!=(new.extent,new.record_offset):
                raise ValueError("ELF extent or directory record moved")
            if new.size!=build_report["elf_size"]:raise ValueError("New ELF size mismatch")
            start=old.extent*SECTOR_SIZE
            if sha(bytes(a[start:start+old.size]))!=APPROVED_INSTALLED_ELF_SHA256:
                raise ValueError("Original installed ELF SHA drift")
            updated_elf=bytes(b[start:start+new.size])
            if sha(updated_elf)!=build_report["elf_sha256"]:
                raise ValueError("New installed ELF SHA drift")
            verify_approved(updated_elf,json.loads(MANIFEST.read_text()))
            fit=assert_all_tablets_fit(updated_elf)
            allowed={}
            def permit(begin,end,owner):
                for pos in range(begin,end):
                    if pos in allowed:raise ValueError(f"Allowed-owner overlap {pos:#x}")
                    allowed[pos]=owner
            permit(old.record_offset+10,old.record_offset+18,"iso9660_executable_size")
            permit(start+0x64,start+0x68,"elf_pt_load_size")
            for site in CALL_SITES:
                permit(start+site-ELF_BIAS,start+site-ELF_BIAS+4,
                    f"lion_label_native_owner_{site:#x}")
            for pos in COMPACT_INSCRIPTION_TEXT:
                permit(start+pos,start+pos+4,f"stone_tablet_record_{pos:#x}")
            permit(start+old.size,start+new.size,"new_lion_helper_and_tablet_strings")
            differences=Counter()
            for block in range(0,len(a),8*1024*1024):
                v=a[block:block+8*1024*1024];w=b[block:block+8*1024*1024]
                if v==w:continue
                for i,(old_byte,new_byte) in enumerate(zip(v,w)):
                    if old_byte==new_byte:continue
                    absolute=block+i
                    if absolute not in allowed:
                        raise ValueError(f"UNEXPLAINED whole ISO byte {absolute:#x}: {old_byte:#x}->{new_byte:#x}")
                    differences[allowed[absolute]]+=1
            required=["iso9660_executable_size","elf_pt_load_size",
                "new_lion_helper_and_tablet_strings"]
            required += [f"lion_label_native_owner_{site:#x}" for site in CALL_SITES]
            required += [f"stone_tablet_record_{site:#x}" for site in COMPACT_INSCRIPTION_TEXT]
            if any(differences[x]==0 for x in required):
                raise ValueError("Expected native owner delta absent")
            return {
                "status":"PASS_ZERO_UNCLASSIFIED_FINISHED_ISO_BYTES",
                "approved_q_sha256":APPROVED_ISO_SHA256,
                "new_t_sha256":candidate_hash,
                "baseline_iso_bytes":len(a),"candidate_iso_bytes":len(b),
                "approved_elf_size":old.size,"new_elf_size":new.size,
                "changed_bytes_by_owner":dict(sorted(differences.items())),
                "unclassified_bytes":0,
                "gamewide_tablet_width_gate":fit,
                "gameplay_approved":False,"save_cross_release_runtime_verified":False
            }

def main():
    p=argparse.ArgumentParser()
    for arg in ("baseline","candidate","build-report","output"):
        p.add_argument("--"+arg,required=True,type=Path)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError("Existing ISO delta report")
    data=audit(a.baseline,a.candidate,json.loads(a.build_report.read_text()))
    a.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    print(json.dumps(data,sort_keys=True))

if __name__=="__main__":main()
