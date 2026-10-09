"""Regression barriers for runtime-observed r67 Help and inspection defects."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import unittest

from tools.first_save_help import _icon_reservations,_metadata
from tools.inspect_english_bytes import parse
from tools.r67_playtest_help import (
    READABLE_ICON_PAGES, append_polished_help, reflow_readable,
)
from tools.r67_playtest_inspections import COMPACT_PICKUP_ROWS, append_inspection_fixes
from tools.r67_playtest_history import append_history_layout, JAL_FILE_OFFSET, JAL_PREIMAGE, shim_bytes
from tools.localization import encode_ps2_english

ROOT=Path(__file__).resolve().parents[1]
PRISTINE=ROOT.parent/'startup-flow-v10/fixtures/elf/SLPM_665.11'
OFFICIAL=Path('/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
P0=ROOT/'local/r67-early-interactions.elf'
OLD_HELP=ROOT/'local/r67-help-icon-safe.elf'
INSPECTIONS=ROOT/'local/r67-playtest-inspections-v2.elf'
POLISHED=ROOT/'local/r67-playtest-help-v2.elf'
INSPECTION_MANIFEST=ROOT/'translations/r67_playtest_inspection_owners.json'
HELP_MANIFEST=ROOT/'translations/r67_help_owners.json'
HISTORY=ROOT/'local/r67-playtest-history-v2.elf'
PREVIOUS_MANIFEST=ROOT/'translations/first_save_pointer_owners.json'


class R67PlaytestPolishTests(unittest.TestCase):
    def test_manual_help_instruction_pages_fit_and_preserve_icons(self):
        self.assertEqual(18,len(READABLE_ICON_PAGES["entering_battle"]))
        self.assertEqual(22,len(READABLE_ICON_PAGES["basic_attack"]))
        for key,rows in READABLE_ICON_PAGES.items():
            self.assertTrue(any("Combat" in t or "Attack" in t for t in rows))
            self.assertFalse(any("--------" in line for line in rows))
            self.assertTrue(all(len(line)<=28 for line in rows))

    @unittest.skipUnless(all(p.exists() for p in (
        PRISTINE,OFFICIAL,P0,OLD_HELP,INSPECTIONS,POLISHED
    )), "Private user-owned PS2/PS4 corpus and built ELF needed")
    def test_official_inspections_fully_owned_and_item_pickup_fixed(self):
        source=PRISTINE.read_bytes()
        baseline=P0.read_bytes()
        manifest=json.loads(INSPECTION_MANIFEST.read_text())
        official=OFFICIAL.read_bytes()
        output,report=append_inspection_fixes(
            source,baseline,manifest,
            json.loads(PREVIOUS_MANIFEST.read_text()),parse(OFFICIAL),
            hashlib.sha256(official).hexdigest()
        )
        self.assertEqual(INSPECTIONS.read_bytes(),output)
        self.assertEqual(17,report["updated_origins"])
        self.assertEqual(43,report["changed_pointer_owners"])
        self.assertEqual(2,report["fixed_item_rows"])
        self.assertEqual(
            "01918e4c5edd23220dfdedfa33701baa610f6fda3e427024c5e0193d80e6ca11",
            report["result_elf_sha256"]
        )
        for line,english in zip((0x596010,0x596028),COMPACT_PICKUP_ROWS,strict=True):
            self.assertNotEqual(source[line:line+24],output[line:line+24])
            self.assertTrue(
                output[line:line+24].startswith(encode_ps2_english(english)+b"\0")
            )
        for owner in manifest["owners"]:
            for pointer in owner["aliases"]:
                self.assertNotEqual(baseline[pointer:pointer+4],output[pointer:pointer+4])

        tampered=bytearray(source)
        tampered[manifest["owners"][0]["offset"]] ^= 1
        with self.assertRaisesRegex(ValueError,"Pristine"):
            append_inspection_fixes(
                bytes(tampered),baseline,manifest,
                json.loads(PREVIOUS_MANIFEST.read_text()),parse(OFFICIAL),
                hashlib.sha256(official).hexdigest()
            )

    @unittest.skipUnless(all(p.exists() for p in (
        PRISTINE,OFFICIAL,OLD_HELP,INSPECTIONS,POLISHED
    )), "Private user-owned PS2/PS4 corpus and built ELF needed")
    def test_all_50_readable_pages_frozen_source_and_icon_safe(self):
        source=PRISTINE.read_bytes()
        original_help=OLD_HELP.read_bytes()
        baseline=INSPECTIONS.read_bytes()
        manifest=json.loads(HELP_MANIFEST.read_text())
        official=parse(OFFICIAL)
        output,report=append_polished_help(
            source,original_help,baseline,manifest,official,
            hashlib.sha256(baseline).hexdigest()
        )
        self.assertEqual(POLISHED.read_bytes(),output)
        self.assertEqual(50,report["pages"])
        self.assertEqual(32,report["changed_pages"])
        self.assertEqual(529,report["changed_rows"])
        self.assertEqual(hashlib.sha256(output).hexdigest(),report["output_sha256"])
        entries={}
        for jp,en,_ in official:entries.setdefault(jp,set()).add(en)
        _typ,fo,va,*_=struct.unpack_from("<8I",output,0x54)
        for spec in manifest["pages"]:
            with self.subTest(topic=spec["key"]):
                lines=reflow_readable(source,spec,entries)
                reserved,_=_icon_reservations(spec,_metadata(source,spec))
                self.assertEqual(spec["rows"],len(lines))
                for i,line in enumerate(lines):
                    self.assertLessEqual(len(line),28)
                    self.assertNotIn("--------",line)
                    for column in reserved[i]:
                        if column<len(line):
                            self.assertEqual(" ",line[column])
                ptr=struct.unpack_from("<I",output,spec["descriptor_offset"])[0]
                self.assertGreaterEqual(ptr,0x902F00)
                self.assertEqual(
                    original_help[spec["metadata_descriptor_offset"]:spec["metadata_descriptor_offset"]+4],
                    output[spec["metadata_descriptor_offset"]:spec["metadata_descriptor_offset"]+4],
                )
        self.assertIn("Recovering AP", "\n".join(reflow_readable(
            source,next(x for x in manifest["pages"] if x["key"]=="turn_based_combat"),entries
        )))

    @unittest.skipUnless(POLISHED.exists() and HISTORY.exists(),
                         "Local staged dialogue-history ELF unavailable")
    def test_history_modal_horizontal_shim_does_not_touch_frozen_adv(self):
        source=POLISHED.read_bytes()
        localized, report=append_history_layout(source)
        self.assertEqual(HISTORY.read_bytes(),localized)
        self.assertEqual(72, len(shim_bytes()))
        self.assertEqual(0x0C062FC4, JAL_PREIMAGE)
        self.assertEqual(JAL_PREIMAGE,struct.unpack_from("<I",source,JAL_FILE_OFFSET)[0])
        self.assertNotEqual(JAL_PREIMAGE,struct.unpack_from("<I",localized,JAL_FILE_OFFSET)[0])
        self.assertEqual(72,len(localized)-len(source))
        self.assertEqual("horizontal",report["new_orientation"])
        self.assertEqual((20,276),report["speaker_xy"])
        self.assertEqual((20,300),report["body_xy"])
        self.assertEqual(
            "80ba16336921a4054636806978de140e7c2eb64787c6d85f75caa68cc8187d2a",
            report["candidate_sha256"]
        )
        # The r66-accepted inline speaker, DG and AFK/L1 functions and data
        # are frozen in exactly their earlier executable bytes.
        for start,end in ((0x14E940,0x14E980),(0x14F8F0,0x14F9D0),
                          (0x150030,0x150090),(0x1514F0,0x151740),
                          (0x66200,0x66A00)):
            self.assertEqual(source[start:end],localized[start:end])
        corrupted=bytearray(source)
        struct.pack_into("<I",corrupted,JAL_FILE_OFFSET,0)
        with self.assertRaisesRegex(ValueError,"Unexpected r67"):
            append_history_layout(bytes(corrupted))


if __name__=="__main__":
    unittest.main()
