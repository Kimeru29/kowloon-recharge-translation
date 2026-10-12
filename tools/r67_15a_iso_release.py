"""r67.15a full finished ISO packager and exact-byte delta gate.

Creates a versioned 2GB diagnostic by applying one SHA-pinned staged ELF
transformation plus the one validated, same-size B_GP004 translated container
inside DATA.CVM. The original approved z ISO, q/t/y resources and original
memory cards are never modified. Any unknown byte fails the entire-disc audit.
"""
from __future__ import annotations
import json,mmap,shutil,struct,subprocess
from collections import Counter
from pathlib import Path
from tools.iso9660_patch import index_iso,find_record,patch_directory_record
from tools.r67_lion_statue_iso_patch import sha_file
from tools.r67_lion_statue_ui import sha
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T
from tools.r67_14y_release import verify_save_identity
from tools.r67_14y_inspection_save import validate_result as validate_inspections
from tools.tmx import find_tmx_entry
from tools.r67_15a_item_width import apply as update_elf
from tools.r67_15a_items_art import apply as update_art

ROOT=Path(__file__).resolve().parents[1]
Z_ISO=ROOT/'local/r67-candidates/67.14z-storeroom-inscription.iso'
Z_STAGE=ROOT/'local/r67-14z-storeroom-tablet.elf'
A_STAGE=ROOT/'local/r67-15a-item-width.elf'
Z_ART=ROOT/'local/r67-15a-analysis/current-B_GP004.BIN'
A_ART=ROOT/'local/r67-15a-analysis/B_GP004-translated-v2.BIN'
A_ISO=ROOT/'local/r67-candidates/67.15a-item-storage-ui.iso'
REPORT=ROOT/'local/r67-15a-build.json'
AUDIT=ROOT/'local/r67-15a-whole-iso-audit.json'
Z_ISO_SHA="18b390bcb230a9a69ccff284eeea39a0d00dfc6502b2526ee9895f5f38c423a6"
Z_STAGE_SHA="c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2"
Z_INSTALLED_SHA="28d66006774f282c74299e41794341e424e14d16eb4da971b9b9f085021cb6d9"
NATIVE_SITES=(0x2A2A6C,0x2A6060,0x29DC44)
ELF_BIAS=0xfff80
ART_INDICES=(3,5,15,16,17,18,19)

def preflight():
    if sha_file(Z_ISO)!=Z_ISO_SHA:raise ValueError("Approved z ISO fingerprint drift")
    old=Z_STAGE.read_bytes()
    if sha(old)!=Z_STAGE_SHA:raise ValueError("Approved z ELF fingerprint drift")
    new=A_STAGE.read_bytes()
    expected,meta=update_elf(old,Z_STAGE_SHA,0x963FD0)
    if new!=expected:raise ValueError("Candidate ELF is not deterministic source transform")
    art0=Z_ART.read_bytes()
    art1=A_ART.read_bytes()
    if sha(art0)!= "732a68c2c4e7e22a2d0e553ddd066d2c1c3b96a6ed15bc73edc89d988a3816b4":
        raise ValueError("Group-4 approved source atlas changed")
    if art1!=update_art(art0)[0]:raise ValueError("Atlas differs from PS4 source + bounded caption port")
    allowed=set(range(0x64,0x68))
    for site in NATIVE_SITES:allowed.update(range(site-ELF_BIAS,site-ELF_BIAS+4))
    changed={i for i,(a,b) in enumerate(zip(old,new)) if a!=b}
    if not changed or changed-allowed:raise ValueError(f"Unauthorized approved z ELF bytes: {changed-allowed}")
    # The accepted Lion executable/data is unchanged except both exact JALs.
    recovered=bytearray(new)
    for site in NATIVE_SITES:
        pos=site-ELF_BIAS
        recovered[pos:pos+4]=old[pos:pos+4]
    if not verify_approved(bytes(recovered),json.loads(Q.read_text()))["status"].startswith("PASS"):
        raise ValueError("Original q lock failed")
    if not verify_ui(bytes(recovered),json.loads(T.read_text()))["status"].startswith("PASS"):
        raise ValueError("Original t lock failed")
    validate_inspections(new)
    verify_save_identity(new)
    return old,new,art0,art1,meta,changed

def installed_new(oldstage:bytes,newstage:bytes,oldinstalled:bytes)->bytes:
    if sha(oldinstalled)!=Z_INSTALLED_SHA or len(oldinstalled)!=len(oldstage):
        raise ValueError("Installed native ROFS relocated preimage changed")
    result=bytearray(oldinstalled)
    changes={i for i,(a,b) in enumerate(zip(oldstage,newstage)) if a!=b}
    for pos in changes:
        if oldinstalled[pos]!=oldstage[pos]:
            raise ValueError(f"New patch collided with independently relocated ELF byte {pos:#x}")
        result[pos]=newstage[pos]
    result.extend(newstage[len(oldstage):])
    b=bytes(result)
    # Existing q/t fixed records preserve their original contents apart
    # from the two authorized JAL changes (reconstructed IN MEMORY ONLY).
    original=bytearray(b)
    for site in NATIVE_SITES:
        pos=site-ELF_BIAS
        original[pos:pos+4]=oldinstalled[pos:pos+4]
    verify_approved(bytes(original),json.loads(Q.read_text()))
    verify_ui(bytes(original),json.loads(T.read_text()))
    verify_save_identity(b)
    validate_inspections(b)
    return b

def offsets(container:bytes)->list[tuple[int,int,int]]:
    return [(idx,find_tmx_entry(container,f"GRP004/GP004_{idx:02}.TMX").base_offset,
             find_tmx_entry(container,f"GRP004/GP004_{idx:02}.TMX").chunk_size)
            for idx in ART_INDICES]

def locate(iso):
    _,outer=index_iso(iso)
    exe=find_record(outer,'SLPM_665.11')
    cvm=find_record(outer,'DATA.CVM')
    cvm_base=cvm.extent*2048+0x1800
    _,inside=index_iso(iso,cvm_base)
    group=find_record(inside,'BLBRD/B_GP004.BIN')
    return exe,exe.extent*2048,cvm_base+group.extent*2048,group

def audit(previous:Path,new:Path,preflight_result=None)->dict:
    if preflight_result is None:preflight_result=preflight()
    old,newstage,original_art,new_art,meta,changed=preflight_result
    if sha_file(previous)!=Z_ISO_SHA:raise ValueError("Approved z ISO changed during build")
    with previous.open('rb') as f,new.open('rb') as g:
        with mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as lhs,mmap.mmap(
            g.fileno(),0,access=mmap.ACCESS_READ) as rhs:
            if len(lhs)!=len(rhs):raise ValueError("Whole disc physical size changed")
            e,at,artat,grp=locate(lhs);q,based,artaddr,group=locate(rhs)
            if (e.extent,e.record_offset,at,artat)!=(q.extent,q.record_offset,based,artaddr):
                raise ValueError("Native executable or group4 relocated")
            oldins=bytes(lhs[at:at+e.size])
            exp=installed_new(old,newstage,oldins)
            if bytes(rhs[at:at+len(exp)])!=exp or q.size!=len(exp):
                raise ValueError("Candidate executable differs from deterministic patch")
            if lhs[artat:artat+len(original_art)]!=original_art or group.size!=len(new_art):
                raise ValueError("Approved group4 material not found at expected extent")
            if bytes(rhs[artat:artat+len(new_art)])!=new_art:
                raise ValueError("Localized group4 not installed exactly")
            expected={}
            allowed_original={i:"native_item_width_hook" for i in changed if i>=0x80}
            allowed_original.update({i:"elf_pt_load_size" for i in changed if i<0x80})
            for i in changed:
                if lhs[at+i]!=exp[i]:
                    expected[at+i]=(exp[i],allowed_original[i])
            for i in range(len(old),len(exp)):
                if lhs[at+i]!=exp[i]:
                    expected[at+i]=(exp[i],"append_private_item_width_helpers")
            owned_art=set()
            for idx,begin,size in offsets(original_art):
                for i in range(begin,begin+size):
                    owned_art.add(i)
            for i,(a,b) in enumerate(zip(original_art,new_art)):
                if a!=b:
                    if i not in owned_art:raise ValueError(f"Unexpected translated art chunk {i:#x}")
                    expected[artat+i]=(b,"group4_localized_item_art")
            size_pair=struct.pack('<I',len(exp))+struct.pack('>I',len(exp))
            for k,v in enumerate(size_pair):
                pos=e.record_offset+10+k
                if lhs[pos]!=v:expected[pos]=(v,"iso9660_executable_size")
            result=Counter()
            for start in range(0,len(lhs),8*1024*1024):
                a=lhs[start:start+8*1024*1024];b=rhs[start:start+8*1024*1024]
                if a==b:continue
                for k,(u,v) in enumerate(zip(a,b)):
                    if u==v:continue
                    pos=start+k
                    if pos not in expected or expected[pos][0]!=v:
                        raise ValueError(f"UNEXPLAINED finished-disc byte {pos:#x}: {u:#x}->{v:#x}")
                    result[expected[pos][1]]+=1
            if sum(result.values())!=len(expected):
                raise ValueError("Required owned whole-ISO changes absent")
            return dict(status="PASS_ZERO_UNEXPLAINED_FINISHED_ISO_BYTES",
                approved_previous_z_sha256=Z_ISO_SHA,
                candidate_iso_sha256=sha_file(new),
                iso_size_bytes=len(lhs),
                original_approved_z_elf_sha256=Z_STAGE_SHA,
                installed_candidate_elf_sha256=sha(exp),
                modified_bytes=sum(result.values()),
                changes_by_owner=dict(sorted(result.items())),
                unexplained_bytes=0,
                native_save_paths_modified=False,
                user_visual_approval=False)

def build():
    tmp=A_ISO.with_suffix('.incomplete')
    for file in (A_ISO,tmp,REPORT,AUDIT):
        if file.exists():raise FileExistsError(f"Never overwrite prior diagnostic: {file}")
    src=preflight()
    old,newstage,original_art,newart,meta,changed=src
    copy=subprocess.run(['cp','-c',str(Z_ISO),str(tmp)],capture_output=True)
    if copy.returncode:shutil.copyfile(Z_ISO,tmp)
    try:
        with tmp.open('r+b') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_WRITE) as image:
            exe,at,artat,group=locate(image)
            current=bytes(image[at:at+exe.size])
            target=installed_new(old,newstage,current)
            if exe.sectors!=(len(target)+2047)//2048:
                raise ValueError("Executable extra helper requires relocation")
            if any(image[at+len(current):at+len(target)]):
                raise ValueError("New ELF helper collides with nonzero disc data")
            if bytes(image[artat:artat+group.size])!=original_art:
                raise ValueError("Wrong approved group4 source")
            image[at:at+len(target)]=target
            image[artat:artat+len(newart)]=newart
            patch_directory_record(image,exe.record_offset,size=len(target))
            image.flush()
        diff=audit(Z_ISO,tmp,src)
        manifest=dict(release="r67.15a",
            status="DIAGNOSTIC_AWAITING_GAMEPLAY_SCREENSHOTS",
            baseline_z_iso_sha256=Z_ISO_SHA,
            candidate_iso_sha256=diff["candidate_iso_sha256"],
            candidate_elf_sha256=sha(newstage),
            installed_elf_sha256=diff["installed_candidate_elf_sha256"],
            elf_output_extent=exe.extent,elf_size=len(target),
            allowed_original_code_site_vas=list(map(hex,NATIVE_SITES)),
            output_path=str(A_ISO),
            save_runtime_compatibility_verified=False,
            gameplay_approved=False)
        REPORT.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
        AUDIT.write_text(json.dumps(diff,indent=2,sort_keys=True)+"\n")
        tmp.rename(A_ISO)
        print(json.dumps(dict(output=str(A_ISO),
            sha256=diff["candidate_iso_sha256"],
            modified_bytes=diff["modified_bytes"],unexplained=0),sort_keys=True))
    except:
        raise

if __name__=="__main__":
    build()
