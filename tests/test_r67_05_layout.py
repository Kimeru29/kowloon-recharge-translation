"""67.05 frozen previous approvals, icon-aligned Help and bounded caption tests."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import unittest
from tools.first_save_help import _metadata, _icon_reservations
from tools.localization import encode_ps2_english
from tools.r67_05_layout import apply, BASE_SHA, HANT_ROWS, ROTATE_SLOT, ROTATE_LENGTH, VISIBLE, sha

ROOT=Path(__file__).resolve().parents[1]
PRISTINE=ROOT.parent/"startup-flow-v10/fixtures/elf/SLPM_665.11"
PREV=ROOT/"local/r67-04.elf"
NEXT=ROOT/"local/r67-05.elf"
PAGES=json.loads((ROOT/"translations/r67_help_owners.json").read_text())["pages"]

class Release6705(unittest.TestCase):
    def test_no_controller_is_isolated_and_target_fits(self):
        self.assertEqual("Target",VISIBLE)
        self.assertLessEqual(len(VISIBLE),9)
        self.assertEqual(22,len(HANT_ROWS))
        for row in (16,19):
            self.assertTrue(HANT_ROWS[row].strip())
            self.assertTrue(HANT_ROWS[row+1].strip())
        if not PRISTINE.exists():
            self.skipTest("Owned source PS2 ELF not available")
        page=next(p for p in PAGES if p["key"]=="basic_attack")
        reserved,_=_icon_reservations(page,_metadata(PRISTINE.read_bytes(),page))
        for row,words in enumerate(HANT_ROWS):
            self.assertLessEqual(len(words),28)
            self.assertTrue(all(i>=len(words) or words[i]==" " for i in reserved[row]))

    @unittest.skipUnless(all(x.exists() for x in (PRISTINE,PREV,NEXT)),
                         "Local PS2 source / staged builds unavailable")
    def test_byte_exact_build_and_strict_previous_acceptance(self):
        src,old,new=(x.read_bytes() for x in (PRISTINE,PREV,NEXT))
        result,report=apply(src,old,PAGES)
        self.assertEqual(result,new)
        self.assertEqual(report["prior_sha256"],BASE_SHA)
        self.assertEqual(report["sha256"],"a1e5665be7ee71d1ad6b5b9f442d8155abc313a8303537962dc4b4ebe61a8f92")
        self.assertEqual(report["fixed_slot"][2],"Target")
        self.assertFalse(report["save_namespace_modified"])
        self.assertFalse(report["geometric_renderer_changes"])
        # Both approved pedestal interaction and physical statue inspection,
        # plus every other non-owned ELF byte, remain unchanged via fail-closed
        # original stage hash and complete changed-byte classification.
        for region in (
            (0x594FA0,0x594FA4),   # pedestal Use/Push Item target
            (0x58A040,0x58A058),   # physical statue names/descriptions
            (0x3D3428,0x3D343C),   # dungeon-entry story comment owners
            (0x391928,0x39192C),   # pickup item canonical official name
            (0x159D54,0x159D58),   # experimental history hook unchanged
            (0x350BA0,0x350C40),   # companion AFK graphics
            (0x3F8E1C,0x3F8E70),   # AFK geometry
        ):
            start,end=region
            self.assertEqual(old[start:end],new[start:end],hex(start))
        self.assertEqual(
            new[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH],
            (encode_ps2_english(VISIBLE,collapse_spaces=False)+b"\0").ljust(ROTATE_LENGTH,b"\0"),
        )
        page=next(p for p in PAGES if p["key"]=="basic_attack")
        off=struct.unpack_from("<I",old,0x58)[0]+struct.unpack_from("<I",old,page["descriptor_offset"])[0]-struct.unpack_from("<I",old,0x5C)[0]
        for index in (15,18,21,22):
            self.assertEqual(old[off+index*4:off+index*4+4],new[off+index*4:off+index*4+4])
        for index in (16,17,19,20):
            self.assertNotEqual(old[off+index*4:off+index*4+4],new[off+index*4:off+index*4+4])
        broken=bytearray(old)
        broken[0x594FA0]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            apply(src,bytes(broken),PAGES)
if __name__=="__main__":
    unittest.main()
