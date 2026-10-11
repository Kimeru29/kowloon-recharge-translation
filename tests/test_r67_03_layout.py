"""Release 67.03 regression gates for the owned first-dungeon fixes."""
import json
import struct
import unittest
from pathlib import Path

from tools.r67_03_layout import (
    apply, sha, BASE_SHA, BASIC_ATTACK, TURN_COMBAT, OBJECTS,
)
from tools.inspect_english_bytes import parse
from tools.first_save_help import _icon_reservations, _metadata

ROOT=Path(__file__).resolve().parents[1]
PRISTINE=ROOT.parent/'startup-flow-v10/fixtures/elf/SLPM_665.11'
BASE=ROOT/'local/r67-02-history.elf'
CANDIDATE=ROOT/'local/r67-03.elf'
CORPUS=Path('/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
MANIFEST=ROOT/'translations/r67_help_owners.json'

class Release6703(unittest.TestCase):
    def test_safe_fixed_help_rows(self):
        self.assertEqual(len(BASIC_ATTACK),15)
        self.assertEqual(len(TURN_COMBAT),29)
        self.assertEqual(len(OBJECTS),5)
        self.assertEqual(BASIC_ATTACK[-1],"wait until next turn.")
        self.assertIn("Ending Your Turn",TURN_COMBAT)
        self.assertNotIn("....."," ".join(TURN_COMBAT))
    @unittest.skipUnless(all(x.exists() for x in (PRISTINE,BASE,CANDIDATE,CORPUS,MANIFEST)),
                         "Local user-owned source/build unavailable")
    def test_byte_exact_owned_changes(self):
        original=PRISTINE.read_bytes()
        base=BASE.read_bytes()
        elf=CANDIDATE.read_bytes()
        self.assertEqual(sha(base),BASE_SHA)
        pages=json.loads(MANIFEST.read_text())["pages"]
        built,report=apply(original,base,parse(CORPUS),pages)
        self.assertEqual(elf,built)
        self.assertEqual(report["new_sha256"],"1913153bc67d4b2febc444cedfa5fb62fdc5aeaed94d077762416f3688cb24a8")
        self.assertEqual(len(report["owners"]),50)
        for page in pages:
            d=page["descriptor_offset"]
            self.assertEqual(elf[d:d+4],base[d:d+4])
            md=page["metadata_descriptor_offset"]
            self.assertEqual(elf[md:md+4],base[md:md+4])
        # Accepted inspection displays were not redirected.
        for source in (0x695dc0,0x695dc8,0x695c28,0x695c30,0x590dc0,0x590d00,0x590be0):
            word=struct.pack("<I",0x100000+source-0x80)
            pointers=[i for i in range(0,len(original)-4,4) if original[i:i+4]==word]
            self.assertTrue(pointers)
            for pos in pointers:
                self.assertEqual(elf[pos:pos+4],base[pos:pos+4])
        # Accepted AFK/L1 executable data and history patch are identical.
        self.assertEqual(elf[0x159d54:0x159d58],base[0x159d54:0x159d58])
        self.assertEqual(elf[0x151608:0x151618],base[0x151608:0x151618])
        for name in ("basic_attack","turn_based_combat"):
            page=next(x for x in pages if x["key"]==name)
            reservations,_=_icon_reservations(page,_metadata(original,page))
            lines=BASIC_ATTACK if name=="basic_attack" else TURN_COMBAT
            for row,text in enumerate(lines):
                self.assertFalse(any(x<len(text) and text[x]!=" " for x in reservations[row]))
    @unittest.skipUnless(all(x.exists() for x in (PRISTINE,BASE,CORPUS,MANIFEST)),
                         "Local user-owned source/build unavailable")
    def test_fail_closed(self):
        source=PRISTINE.read_bytes()
        baseline=bytearray(BASE.read_bytes())
        baseline[0x58a044]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            apply(source,bytes(baseline),parse(CORPUS),json.loads(MANIFEST.read_text())["pages"])

if __name__=="__main__":
    unittest.main()
