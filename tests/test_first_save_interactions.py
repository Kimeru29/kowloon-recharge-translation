"""Fail-closed optional first-dungeon label and inspection relocation checks."""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import struct
import unittest

from tools.first_save_interactions import append_first_dungeon_inspections, digest
from tools.inspect_english_bytes import parse as parse_english

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/"startup-flow-v10/fixtures/elf/SLPM_665.11"
PS4=Path("/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes")
HELP=ROOT/"local/r67-help-icon-safe.elf"
OUTPUT=ROOT/"local/r67-early-interactions.elf"
MANIFEST=ROOT/"translations/r67_early_interaction_owners.json"
OUTPUT_GOLDEN="174c6fdf2a8c7c0a2554f3a9896cd9ac08667b890809032c74d92bd6c894b9c1"


class EarlyInteractionOwnerTests(unittest.TestCase):
    @unittest.skipUnless(all(p.exists() for p in (SOURCE,PS4,HELP,OUTPUT)),
                         "Original PS2, PS4 corpus, or ignored ELF outputs not available")
    def test_exact_replay_and_pointer_protection(self):
        original=SOURCE.read_bytes()
        help_elf=HELP.read_bytes()
        official_bytes=PS4.read_bytes()
        manifest=json.loads(MANIFEST.read_text())
        expected, report=append_first_dungeon_inspections(
            original,help_elf,manifest,parse_english(PS4),digest(official_bytes)
        )
        self.assertEqual(9,len(report["owners"]))
        self.assertEqual(78,report["aliases"])
        self.assertEqual(237,report["appended_bytes"])
        self.assertEqual(OUTPUT_GOLDEN,digest(expected))
        self.assertEqual(expected,OUTPUT.read_bytes())
        self.assertEqual(original,SOURCE.read_bytes())
        for entry in report["owners"]:
            with self.subTest(owner=entry["key"]):
                for pos in entry["pointer_offsets"]:
                    self.assertEqual(entry["target_va"],struct.unpack_from("<I",expected,pos)[0])
                    self.assertNotEqual(expected[pos:pos+4],help_elf[pos:pos+4])
        for i,(a,b) in enumerate(zip(help_elf,expected)):
            if a==b:continue
            writable={*range(0x54+16,0x54+20),
                      *(byte for ent in report["owners"]
                        for ptr in ent["pointer_offsets"] for byte in range(ptr,ptr+4))}
            self.assertIn(i,writable)

    @unittest.skipUnless(all(p.exists() for p in (SOURCE,PS4,HELP)),
                         "Owned local sources unavailable")
    def test_source_and_official_corpus_mismatch_fail_closed(self):
        source=SOURCE.read_bytes()
        help_elf=HELP.read_bytes()
        corpus=PS4.read_bytes()
        manifest=json.loads(MANIFEST.read_text())
        bad=json.loads(json.dumps(manifest))
        bad["owners"][0]["approved_pointer_offsets"].pop()
        with self.assertRaisesRegex(ValueError,"alias drift"):
            append_first_dungeon_inspections(
                source,help_elf,bad,parse_english(PS4),digest(corpus)
            )
        with self.assertRaisesRegex(ValueError,"Official PS4 English SHA mismatch"):
            append_first_dungeon_inspections(
                source,help_elf,manifest,parse_english(PS4),"bad-hash"
            )

if __name__=="__main__":
    unittest.main()
