"""67.03: verified PS2 object text and in-place HANT row corrections.

Applied after 67.02, without changing AFK/L1 renderer, game saves,
ISO graphic containers, or approved inspection and HANT pages.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import struct

from tools.localization import encode_ps2_english
from tools.inspect_english_bytes import parse
from tools.first_save_help import _icon_reservations, _metadata, _MAX_CELLS
from tools.companion_hud_data import COMPANION_COMMENT_DATA

BASE_SHA = "c65270ff6ff8dcfcd80dcfdcf4e49cb8171080c8e29b710941aad356af586eb8"
OBJECTS = {
    0x58A030: "",                    # Lion Statue phonetic subtitle
    0x58A010: "Stone lion statue.",  # lion description
    0x590E80: "Mechanism inside.",   # pedestal state
    0x58A100: "Cannot use.",         # 44 aliases of generic state
    0x594F50: "Use Item",            # circle-button label
}
OLDMAN_OFFSET = 0x3C1A50
OLDMAN_TEXT = "  Eerie place."
BASIC_ATTACK = (
    "Basic Attack", "",
    "1. Approach the enemy.", "",
    "2. Ready your weapon.",
    "               Equip.",
    "3. Aim at your target.",
    "Use the R Stick to aim.",
    "        Point at target.",
    "4. Fire ready weapon.",
    "Attacks consume AP.", "",
    "5. End your turn.",
    "If AP is depleted,",
    "wait until next turn.",
)
TURN_COMBAT = (
    "Turn-Based Combat", "",
    "You and enemies act",
    "in alternating turns.", "", "",
    "Action Points (AP)", "",
    "Moves and attacks use AP.",
    "Each action spends AP.", "",
    "With no AP remaining,",
    "you cannot act.", "", "", "",
    "Recovering AP", "",
    "AP resets when your",
    "next turn begins.", "",
    "Some items restore AP.", "", "",
    "Ending Your Turn", "",
    "Press         to end turn.",
    "Your turn ends.", "",
)

def sha(b): return hashlib.sha256(b).hexdigest()

def apply(pristine, baseline, official_rows, pages):
    if sha(baseline) != BASE_SHA:
        raise ValueError("67.02 ELF fingerprint mismatch")
    _, fo, va, _, length, reserve, flags, _ = struct.unpack_from("<8I", baseline, 0x54)
    if fo + length != len(baseline) or va != 0x902F00 or reserve != 0x100000 or flags != 7:
        raise ValueError("Unexpected translation segment")
    official = defaultdict(set)
    for jp, en, _ in official_rows:
        official[jp].add(en)
    output = bytearray(baseline)
    whitelist = set(range(0x64, 0x68))
    changed = []

    def append(text):
        if len(output) % 2:
            output.append(0)
        target = va + len(output) - fo
        output.extend(encode_ps2_english(text, collapse_spaces=False) + b"\0")
        return target

    def patch(pointers, text, name):
        if not pointers or len({struct.unpack_from("<I", baseline, i)[0] for i in pointers}) != 1:
            raise ValueError("Alias drift " + name)
        target = append(text)
        for offset in pointers:
            struct.pack_into("<I", output, offset, target)
            whitelist.update(range(offset, offset + 4))
        changed.append(dict(name=name, english=text, pointers=pointers))

    lookup = {struct.unpack_from("<I", pristine, i)[0]: [] for i in range(0)}
    sources = set(OBJECTS) | {OLDMAN_OFFSET}
    want = {0x100000 + src - 0x80: src for src in sources}
    references = {src: [] for src in sources}
    for i in range(0, len(pristine) - 4, 4):
        ref = struct.unpack_from("<I", pristine, i)[0]
        if ref in want:
            references[want[ref]].append(i)

    for src, text in OBJECTS.items():
        end = pristine.find(b"\0", src, src + 160)
        jp = pristine[src:end].decode("cp932")
        translations = official[jp]
        if len(translations) != 1:
            raise ValueError("PS4 English owner ambiguous: " + hex(src))
        if len(text) > 20:
            raise ValueError("Unbounded inspection text")
        if not text and next(iter(translations)) != "@D":
            raise ValueError("Unsafe phonetic removal")
        patch(references[src], text, "object_" + hex(src))
    rec = next(r for r in COMPANION_COMMENT_DATA if r[0] == OLDMAN_OFFSET)
    if rec[2] not in official[rec[1]] or tuple(references[OLDMAN_OFFSET]) != rec[4]:
        raise ValueError("Old-man line ownership changed")
    pointer = references[OLDMAN_OFFSET][0]
    prior = struct.unpack_from("<I", baseline, pointer)[0]
    off = fo + prior - va
    expected = encode_ps2_english("Eerie place.") + b"\0"
    if baseline[off:off+len(expected)] != expected:
        raise ValueError("Old-man previous text changed")
    patch(references[OLDMAN_OFFSET], OLDMAN_TEXT, "oldman_left_margin")

    for page_name, lines in (("basic_attack", BASIC_ATTACK), ("turn_based_combat", TURN_COMBAT)):
        page = next(p for p in pages if p["key"] == page_name)
        if len(lines) > page["rows"]:
            raise ValueError("Help page row cardinality")
        reserved, _ = _icon_reservations(page, _metadata(pristine, page))
        descriptor = page["descriptor_offset"]
        table_va = struct.unpack_from("<I", baseline, descriptor)[0]
        table_off = fo + table_va - va
        for row, content in enumerate(lines):
            if len(content) > _MAX_CELLS or any(
                x < len(content) and content[x] != " " for x in reserved[row]
            ):
                raise ValueError("Help icon or glyph overlap " + page_name + ":" + str(row))
            pos = table_off + 4*row
            if struct.unpack_from("<I", baseline, pos)[0] == 0xffffffff:
                raise ValueError("Unexpected Help EOF")
            patch([pos], content, "help_" + page_name + "_" + str(row))
        if output[table_off+len(lines)*4:table_off+(page["rows"]+1)*4] != baseline[table_off+len(lines)*4:table_off+(page["rows"]+1)*4]:
            raise ValueError("Unowned page rows/EOF changed")
        if output[descriptor:descriptor+4] != baseline[descriptor:descriptor+4]:
            raise ValueError("Live page descriptor changed")
        meta = page["metadata_descriptor_offset"]
        if output[meta:meta+4] != baseline[meta:meta+4]:
            raise ValueError("Controller sprite metadata changed")

    struct.pack_into("<I", output, 0x64, len(output)-fo)
    if len(output)-fo > reserve:
        raise ValueError("Translation PT_LOAD exhausted")
    for i, (a,b) in enumerate(zip(baseline,output)):
        if a != b and i not in whitelist:
            raise ValueError("Unexpected 67.03 executable change " + hex(i))
    return bytes(output), dict(
        previous_sha256=sha(baseline), new_sha256=sha(output),
        previous_size=len(baseline), new_size=len(output),
        appended_bytes=len(output)-len(baseline), owners=changed
    )

def main():
    parser=argparse.ArgumentParser()
    for key in ("pristine", "baseline", "official", "manifest", "output", "report"):
        parser.add_argument("--"+key, type=Path, required=True)
    a=parser.parse_args()
    if a.output.exists() or a.report.exists():
        raise FileExistsError("Refusing output overwrite")
    result, report=apply(
        a.pristine.read_bytes(), a.baseline.read_bytes(), parse(a.official),
        json.loads(a.manifest.read_text())["pages"]
    )
    a.output.write_bytes(result)
    a.report.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print("67.03", report["new_sha256"], "modified owners", len(report["owners"]))
if __name__ == "__main__":
    main()
