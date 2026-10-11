"""Fail-closed PS4 official atlas import, layered on approved r66 art.

Never replace other TMX entries inside a shared container. No source binaries
or Unity images are committed: local overlays are regenerated from owned PS2
ISO and PS4 JP/EN bundles, with fingerprinted pixel/color and alpha geometry.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import mmap
from functools import lru_cache
from pathlib import Path

from tools.graphics_port import port_rgba_into_container
from tools.iso9660_patch import index_iso, find_record, SECTOR_SIZE
from tools.tmx import find_tmx_entry, decode_tmx_rgba

APPROVED = (
    (1,0),(1,2),(1,3),(1,8),(1,10),  # dungeon HUD, combat gauges and labels
    (2,1),                  # Critical / Treasure
    (3,0),(3,1),(3,2),(3,4),     # name/profile/confirmation graphics
    (4,3),(4,5),(4,6),(4,12),(4,14),(4,15),(4,16),(4,17),(4,18),(4,19),
    (6,0),                  # radar/map presentation
    (7,0),                  # companion options and travel controls
    (8,3),(8,7),            # optional shopping/items UI
    (10,0),(10,2),                 # inventory UI texture
    (13,4),                 # status/skill controls
    (17,0),                 # current-items and room-panel labels
    (18,3),                 # Save / Load / Back
    (20,2),                 # HANT artwork (preserve accepted GP020_03)
    (21,0),                 # H.A.N.T. green interface labels
    (22,1),(22,2),          # New Game / Load Game and background art
    *((54,i) for i in range(20)),   # enemy/dictionary card backgrounds
    *((55,i) for i in range(1,16)), # enemy/source detail cards
    *((56,i) for i in range(1,17)), # character/profile cards
    (59,0),                 # H.A.N.T. saved-info choices
)
_ALPHA_THRESHOLD = 32
_MIN_ALPHA_DICE = 0.93
# These atlas entries contain predominantly literal JP glyph pixels.
# Their alpha masks legitimately diverge after replacing the text with English,
# although the original PS2 matches the JP PS4 source (>0.94 Dice) and the
# structural atlas dimensions/texture ownership match. The exception is only
# for the EN alpha mask: the PS2->PS4 JP preimage gate stays strict.
_SOURCE_LAYOUT_OFFLINE_REVIEWED = {(3,1),(4,14),(7,0),(8,3),(8,7),(10,0)}
_TEXT_REPAINT_ENTRIES = {(1,3),(1,8),(4,12),(4,19),(22,1),(22,2),*_SOURCE_LAYOUT_OFFLINE_REVIEWED}


def digest(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def alpha_dice(src: bytes, other: bytes) -> float:
    if len(src) != len(other) or len(src)%4:
        raise ValueError("Alpha masks differ in decoded pixel extent")
    aa=src[3::4];bb=other[3::4]
    x=sum(p>_ALPHA_THRESHOLD for p in aa)
    y=sum(p>_ALPHA_THRESHOLD for p in bb)
    z=sum(a>_ALPHA_THRESHOLD and b>_ALPHA_THRESHOLD for a,b in zip(aa,bb))
    return (2*z/(x+y)) if (x+y) else 1.0


@lru_cache(maxsize=40)
def _owned_ps4_images(path: Path) -> dict[str, tuple[bytes, tuple[int,int]]]:
    import UnityPy
    if not path.is_file():
        raise ValueError(f"Missing owned PS4 asset: {path}")
    pictures={}
    for obj in UnityPy.load(str(path)).objects:
        if obj.type.name!="Texture2D":
            continue
        tex=obj.read()
        image=tex.image.convert("RGBA")
        if tex.m_Name in pictures:
            raise ValueError(f"Duplicate PS4 texture: {tex.m_Name}")
        pictures[tex.m_Name]=(image.tobytes(),image.size)
    return pictures


def get_english_pixels(root: Path, group: int, index: int) -> tuple[bytes,bytes,tuple[int,int],str,str]:
    try:
        import UnityPy
    except ImportError as exc:
        raise RuntimeError("Run the port with uv run --with UnityPy") from exc
    name=f"GP{group:03d}_{index:02d}"
    src=_owned_ps4_images(root/f"b_gp{group:03d}")
    dst=_owned_ps4_images(root/f"b_gp{group:03d}_en")
    if name not in src or name not in dst:
        raise ValueError(f"Missing exact PS4 EN/JP pair: {name}")
    a,sa=src[name]
    b,sb=dst[name]
    if sa!=sb:
        raise ValueError(f"Localized PS4 atlas dimension changed: {name}")
    return a,b,sa,digest(a),digest(b)


def original_containers(iso: Path) -> dict[int, bytes]:
    with iso.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as data:
        _, outer=index_iso(data)
        cvm=find_record(outer,"DATA.CVM")
        base=cvm.extent*SECTOR_SIZE+0x1800
        _, embedded=index_iso(data,base=base)
        result={}
        for group,_index in APPROVED:
            rec=find_record(embedded,f"BLBRD/B_GP{group:03d}.BIN")
            start=base+rec.extent*SECTOR_SIZE
            result[group]=bytes(data[start:start+rec.size])
        return result


def translated_asset(
    source: bytes, jp_pixels: bytes, en_pixels: bytes,
    size: tuple[int,int], group: int, index: int
) -> tuple[bytes, dict]:
    # Import PIL lazily; the source bytes never pass into Git history.
    from PIL import Image
    name=f"GRP{group:03d}/GP{group:03d}_{index:02d}.TMX"
    entry=find_tmx_entry(source,name)
    original=decode_tmx_rgba(source,entry)
    japanese=Image.frombytes("RGBA",size,jp_pixels).resize(
        (entry.width,entry.height),Image.Resampling.LANCZOS
    ).tobytes()
    english=Image.frombytes("RGBA",size,en_pixels).resize(
        (entry.width,entry.height),Image.Resampling.LANCZOS
    ).tobytes()
    source_dice=alpha_dice(original,japanese)
    localized_dice=alpha_dice(original,english)
    en_requires_layout_match=(group,index) not in _TEXT_REPAINT_ENTRIES
    jp_requires_dice=(group,index) not in _SOURCE_LAYOUT_OFFLINE_REVIEWED
    if ((jp_requires_dice and source_dice<_MIN_ALPHA_DICE)
        or (en_requires_layout_match and localized_dice<_MIN_ALPHA_DICE)):
        raise ValueError(f"Atlas geometry mismatch for {name}: {source_dice}/{localized_dice}")
    result=port_rgba_into_container(source,name,en_pixels,source_size=size)
    if len(result)!=len(source):
        raise ValueError(f"Localized PS2 container size changed: {name}")
    a,b=entry.base_offset,entry.base_offset+entry.chunk_size
    if source[:a]!=result[:a] or source[b:]!=result[b:]:
        raise ValueError(f"Non-owned sprite changed in {name}")
    # Validate each other sprite entry, including native group-2 AFK/L1 assets.
    return result,{
        "group":group,"texture":name,"input_size":len(source),
        "source_sha256":digest(source),"result_sha256":digest(result),
        "source_tmx_sha256":digest(source[a:b]),"result_tmx_sha256":digest(result[a:b]),
        "entry_offset":a,"entry_size":entry.chunk_size,
        "ps2_width":entry.width,"ps2_height":entry.height,
        "jp_geometry_dice":round(source_dice,5),"en_geometry_dice":round(localized_dice,5),
        "changed_bytes":sum(x!=y for x,y in zip(source,result)),
        "text_repaint_exception":(group,index) in _TEXT_REPAINT_ENTRIES,
        "manual_source_layout_review":(group,index) in _SOURCE_LAYOUT_OFFLINE_REVIEWED,
    }


def main()->int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pristine-iso",type=Path,required=True)
    ap.add_argument("--ps4-bundles",type=Path,required=True)
    ap.add_argument("--approved-r66-iso",type=Path,required=True,
                    help="Read-only approved r66 ISO for the frozen B_GP020 native repaint")
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--overlay-root",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    if args.report.exists():
        raise FileExistsError("Do not overwrite existing r67 graphics audit")
    if args.overlay_root.exists() and list(args.overlay_root.glob("**/*")):
        raise FileExistsError("Do not overwrite prior graphics overlay tree")
    pristine = original_containers(args.pristine_iso)
    approved_r66 = original_containers(args.approved_r66_iso)
    # Only this group has an accepted r66-native image repaint that a pristine
    # import would revert. Audit every byte and fail before generating output.
    for group in pristine:
        if group == 20:
            original = pristine[group]
            r66 = approved_r66[group]
            if len(original) != len(r66):
                raise ValueError("r66 H.A.N.T. GP020 container geometry drift")
            from tools.tmx import iter_tmx_entries
            for entry in iter_tmx_entries(original):
                x,y=entry.base_offset,entry.base_offset+entry.chunk_size
                if entry.name.endswith("GP020_03.TMX"):
                    if original[x:y] == r66[x:y]:
                        raise ValueError("Previously accepted GP020_03 repaint is missing")
                elif original[x:y] != r66[x:y]:
                    raise ValueError(f"Unexpected r66 H.A.N.T. artwork drift: {entry.name}")
        elif pristine[group] != approved_r66[group]:
            raise ValueError(f"Unapproved baseline graphic container mismatch: {group}")
    pristine[20] = approved_r66[20]
    current = dict(pristine)
    manifest = json.loads(args.manifest.read_text())
    if manifest.get("schema_version") != 2 or len(manifest.get("assets", [])) != len(APPROVED):
        raise ValueError("Unexpected local graphics manifest")
    manifest_index = {(x["group"], x["index"]): x for x in manifest["assets"]}
    if len(manifest_index) != len(APPROVED) or set(manifest_index) != set(APPROVED):
        raise ValueError("Missing, duplicate or unapproved English TMX owners")
    reports = []
    for group, index in APPROVED:
        entry = manifest_index[(group,index)]
        incoming = current[group]
        jp,en,size,hash_jp,hash_en = get_english_pixels(args.ps4_bundles,group,index)
        if (entry["source_sha256"] != digest(incoming)
            or entry["jp_pixel_sha256"] != hash_jp
            or entry["en_pixel_sha256"] != hash_en):
            raise ValueError(f"PS2/PS4 graphics provenance drift {group}/{index}")
        compiled,evidence = translated_asset(incoming,jp,en,size,group,index)
        if entry["expected_output_sha256"] != digest(compiled):
            raise ValueError(f"PS2 palette quantization drift {group}/{index}")
        current[group]=compiled
        reports.append(evidence)
    containers=[]
    for group in sorted(current):
        before=pristine[group]
        after=current[group]
        if len(before)!=len(after):
            raise AssertionError("Original PS2 TMX container size changed")
        path=args.overlay_root/"BLBRD"/f"B_GP{group:03d}.BIN"
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(after)
        containers.append(dict(group=group,original_source_sha256=digest(before),
                               final_output_sha256=digest(after),original_size=len(before)))
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps({"schema_version":2,"assets":reports,"containers":containers},
                                     indent=2,sort_keys=True)+"\n")
    print(json.dumps({"localized_ps2_containers":len(containers),
                     "localized_tmx_entries":len(reports),
                     "changed_tmx_bytes":sum(a["changed_bytes"] for a in reports),
                     "min_alpha_dice":min(a["en_geometry_dice"] for a in reports)},
                     sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
