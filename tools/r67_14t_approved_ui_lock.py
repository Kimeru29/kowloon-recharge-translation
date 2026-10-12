"""Immutable accepted UI-owner lock for r67.14t and later staged ELF / ISO.

Protects two user-approved results:
  - Lion Statue complete enclosure (both native popup/name surfaces)
  - Anubis Stone tablet lines fully enclosed/centered, while the earlier
    Chamber of Lions Stone tablet remains unchanged.

Also verifies all 58 currently registered Stone tablet rows respect the
native full-width 21-glyph limit. Do not regenerate this manifest merely
to make a failure pass; user approval is required to change any owner.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from tools.r67_14q_approved_lock import verify_approved,extract_iso_elf,MANIFEST as Q_MANIFEST
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA
from tools.r67_14t_stone_tablet_fit import assert_all_tablets_fit,read_string
from tools.r67_lion_statue_ui import item_pointer,sha,ITEM_NAME_POINTER_OFFSET,ELF_BIAS

MANIFEST=Path(__file__).resolve().parents[1]/"translations/r67_14t_approved_ui_lock.json"

def verify_ui(elf:bytes,manifest:dict)->dict:
    if manifest.get("schema_version")!=1:
        raise ValueError("Unsupported accepted UI-lock manifest schema")
    if not elf.startswith(bytes.fromhex("7f454c46")):
        raise ValueError("Not a PS2 executable")
    for wanted in (b"SLPM-66511",b"BISLPM-66511Save"):
        if wanted not in elf:
            raise ValueError("Save identity was modified")
    verified_original=verify_approved(elf,json.loads(Q_MANIFEST.read_text()))
    ptr=item_pointer(elf)
    if ptr!=int(manifest["item_name_pointer_value"],16):
        raise ValueError("Approved Lion Statue name pointer drift")
    if hashlib.sha256(read_string(elf,ptr)).hexdigest()!=manifest["item_name_cp932_sha256"]:
        raise ValueError("Approved Lion Statue text drift")
    for raw,word in manifest["item_label_native_callsites"].items():
        site=int(raw,16)
        if struct.unpack_from("<I",elf,site-ELF_BIAS)[0]!=int(word,16):
            raise ValueError(f"Approved Lion item popup/PUSH callsite drift: {raw}")
    helper_va=int(manifest["lion_private_helper_va"],16)
    size=manifest["lion_private_helper_bytes"]
    off=ELF_SEGMENT_FO+helper_va-ELF_SEGMENT_VA
    if off<0 or off+size>len(elf):
        raise ValueError("Approved Lion fit helper missing")
    if hashlib.sha256(elf[off:off+size]).hexdigest()!=manifest["lion_private_helper_sha256"]:
        raise ValueError("Approved Lion UI size/position or native helper changed")
    for raw,word in manifest["private_helper_scale_instruction_words"].items():
        pos=ELF_SEGMENT_FO+int(raw,16)-ELF_SEGMENT_VA
        if struct.unpack_from("<I",elf,pos)[0]!=int(word,16):
            raise ValueError("Approved Lion horizontal fit scale drift")
    for raw,lock in manifest["accepted_tablet_records"].items():
        pos=int(raw,16)
        pointers=struct.unpack_from("<6I",elf,pos)
        expected=tuple(int(word,16) for word in lock["pointer_words"])
        if pointers!=expected:
            raise ValueError(f"Approved Stone tablet row/pointer alignment drift at {raw}")
        if len(lock["text_sha256"])!=5:
            raise ValueError("Missing tablet source locks")
        for i,expected_sha in enumerate(lock["text_sha256"]):
            if hashlib.sha256(read_string(elf,pointers[i])).hexdigest()!=expected_sha:
                raise ValueError(f"Approved Stone tablet content drift at {raw}/row{i}")
    fit=assert_all_tablets_fit(elf)
    if fit["registered_tablets"]!=manifest["all_stone_tablet_records"] or (
            fit["populated_tablet_rows"]!=manifest["all_populated_tablet_rows"]) or (
            fit["native_max_full_width_glyphs"]!=manifest["max_full_width_glyphs"]):
        raise ValueError("Stone tablet coverage or native width policy drift")
    return {
        "status":"PASS_VISUALLY_ACCEPTED_LION_AND_STONE_TABLET_STATIC_OWNERS",
        "lion_item_id":413,
        "lion_approved_horizontal_scale":manifest["native_horizontal_scale"],
        "lion_approved_native_callsites":len(manifest["item_label_native_callsites"]),
        "accepted_tablet_record_count":len(manifest["accepted_tablet_records"]),
        "all_registered_tablets":fit["registered_tablets"],
        "all_inscription_rows_checked":fit["populated_tablet_rows"],
        "overwide_rows":fit["overwide_rows"],
        "prior_approved_event_lock":verified_original["status"],
        "not_a_runtime_render_pixel_test":True,
        "candidate_elf_sha256":sha(elf),
    }

def main()->None:
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--elf",type=Path)
    mode.add_argument("--iso",type=Path)
    parser.add_argument("--build-report",type=Path)
    parser.add_argument("--manifest",type=Path,default=MANIFEST)
    parser.add_argument("--report",type=Path)
    a=parser.parse_args()
    manifest=json.loads(a.manifest.read_text())
    if a.elf:
        content=a.elf.read_bytes()
    else:
        if a.build_report is None:
            parser.error("--build-report is required for finished-ISO lock")
        content=extract_iso_elf(a.iso,json.loads(Q_MANIFEST.read_text()),a.build_report)
    result=verify_ui(content,manifest)
    if a.report:
        if a.report.exists():
            raise FileExistsError("Never overwrite an earlier UI lock result")
        a.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=="__main__":
    main()
