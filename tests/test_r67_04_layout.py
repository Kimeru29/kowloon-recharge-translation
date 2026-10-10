"""67.04 fixed prompt, compact item header and conservative Help regressions."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from tools.first_save_help import _icon_reservations, _metadata
from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english
from tools.r67_04_layout import (
    apply, sha, BASE_SHA, BASIC_ATTACK, NATIVE_ROTATE_SLOT,
    ROTATE_SLOT_SIZE, ROTATE_ENGLISH,
)

ROOT = Path(__file__).resolve().parents[1]
PRISTINE = ROOT.parent / "startup-flow-v10/fixtures/elf/SLPM_665.11"
BASE = ROOT / "local/r67-03.elf"
CURRENT = ROOT / "local/r67-04.elf"
OFFICIAL = Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
MANIFEST = ROOT / "translations/r67_help_owners.json"

class Release6704(unittest.TestCase):
    def test_basic_attack_holes_and_historical_freeze(self):
        self.assertEqual(15, len(BASIC_ATTACK))
        self.assertEqual("wait until next turn.", BASIC_ATTACK[-1])
        self.assertEqual("Change target", ROTATE_ENGLISH)
        page = next(p for p in json.loads(MANIFEST.read_text())["pages"] if p["key"]=="basic_attack")
        if not PRISTINE.exists():
            self.skipTest("Private PS2 source unavailable")
        reserved, _ = _icon_reservations(page, _metadata(PRISTINE.read_bytes(), page))
        for row, text in enumerate(BASIC_ATTACK):
            self.assertLessEqual(len(text), 28)
            self.assertFalse(any(i < len(text) and text[i] != " " for i in reserved[row]))

    @unittest.skipUnless(all(p.exists() for p in (PRISTINE, BASE, CURRENT, OFFICIAL, MANIFEST)),
                         "Private ELF, corpus and static candidate required")
    def test_locked_approved_surfaces_and_exact_elf(self):
        pristine = PRISTINE.read_bytes()
        prior = BASE.read_bytes()
        current = CURRENT.read_bytes()
        self.assertEqual(BASE_SHA, sha(prior))
        pages = json.loads(MANIFEST.read_text())["pages"]
        built, report = apply(pristine, prior, parse(OFFICIAL), pages)
        self.assertEqual(current, built)
        self.assertEqual("202857c06918bd5e4f96ea22c4b3480263c429021c57d88a36a145994da64c83",
                         report["sha256"])
        self.assertFalse(report["renderer_geometry_modified"])
        self.assertFalse(report["save_namespace_modified"])
        self.assertEqual(3, len(report["open_runtime_issues"]))
        self.assertEqual(
            current[NATIVE_ROTATE_SLOT:NATIVE_ROTATE_SLOT + ROTATE_SLOT_SIZE],
            (encode_ps2_english(ROTATE_ENGLISH, collapse_spaces=False) + b"\0").ljust(ROTATE_SLOT_SIZE, b"\0"),
        )
        for source in (
            0x695DC0, 0x695DC8, 0x695C28, 0x695C30,  # approved door/tablet
            0x695C48, 0x58B560, 0x58B580,           # approved container and vase
            0x58A010, 0x58A030, 0x589FF8,           # approved physical lion statue
            0x58AC88, 0x58ACA0, 0x590E80,           # approved pedestal
            0x594F50,                               # Use Item existing translation
        ):
            needle = struct.pack("<I", 0x100000 + source - 0x80)
            offsets = [i for i in range(0, len(pristine) - 3, 4)
                       if pristine[i:i+4] == needle]
            for i in offsets:
                self.assertEqual(prior[i:i+4], current[i:i+4],
                                 f"Approved inspection text owner changed: {source:#x}/{i:#x}")
        self.assertEqual(prior[0x58A040:0x58A058], current[0x58A040:0x58A058])
        for key in ("turn_based_combat", "entering_battle"):
            page = next(p for p in pages if p["key"]==key)
            for name in ("descriptor_offset", "metadata_descriptor_offset"):
                p = page[name]
                self.assertEqual(prior[p:p+4], current[p:p+4])
            fo, va = struct.unpack_from("<II", prior, 0x58)
            ptr = struct.unpack_from("<I", prior, page["descriptor_offset"])[0]
            offset = fo + ptr - va
            size = 4 * (page["rows"] + 1)
            self.assertEqual(prior[offset:offset+size],current[offset:offset+size])
        basic = next(p for p in pages if p["key"]=="basic_attack")
        fo, va = struct.unpack_from("<II", prior, 0x58)
        offset = fo + struct.unpack_from("<I", prior,basic["descriptor_offset"])[0]-va
        self.assertEqual(prior[offset+60:offset+92],current[offset+60:offset+92])
        self.assertEqual(prior[0x159D54:0x159D58],current[0x159D54:0x159D58])

        broken = bytearray(prior)
        broken[0x594FA0] ^= 1
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            apply(pristine,bytes(broken),parse(OFFICIAL),pages)

if __name__ == "__main__":
    unittest.main()
