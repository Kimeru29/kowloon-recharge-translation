"""Regression tests for r67.12 compact speaker/dialogue history spacing."""
from __future__ import annotations
from pathlib import Path
import struct
import unittest
from tools.r67_history_compact_spacing_probe import (
    BASE_SHA256,
    MAX_VISIBLE_RECORDS,
    PATCHES,
    apply,
    positions_for_records,
    sha,
)

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-11-history-sections.elf"
DIAGNOSTIC=ROOT/"local/r67-12-history-compact.elf"


class HistoryCompactSpacing(unittest.TestCase):
    def test_speaker_dialogue_and_next_section_are_distinct(self):
        self.assertEqual((0,25),positions_for_records(("speaker","dialogue")))
        self.assertEqual((0,25,62,87),
                         positions_for_records(("speaker","dialogue")*2))
        self.assertEqual((0,25,62,87,124,149),
                         positions_for_records(("speaker","dialogue")*3))

    def test_six_speaker_dialogue_sections_fit_compact_history(self):
        turns=("speaker","dialogue")*6
        y=positions_for_records(turns)
        self.assertEqual(MAX_VISIBLE_RECORDS,len(y))
        self.assertEqual(335,y[-1])
        self.assertEqual(12,len(set(y)))
        for index in range(0,12,2):
            self.assertEqual(25,y[index+1]-y[index])
            if index<10:
                self.assertEqual(37,y[index+2]-y[index+1])
        for count in range(1,MAX_VISIBLE_RECORDS+1):
            self.assertEqual(count,len(positions_for_records(turns[:count])))

    def test_invalid_record_kinds_and_counts_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"Unsupported"):
            positions_for_records(("speaker","unrecognized"))
        with self.assertRaisesRegex(ValueError,"Too many"):
            positions_for_records(("dialogue",)*13)

    @unittest.skipUnless(BASE.exists() and DIAGNOSTIC.exists(),
                         "private r67.11 and r67.12 ELF fixtures unavailable")
    def test_only_two_history_local_spacing_constants_change(self):
        old=BASE.read_bytes()
        patched=DIAGNOSTIC.read_bytes()
        self.assertEqual(BASE_SHA256,sha(old))
        output,report=apply(old)
        self.assertEqual(output,patched)
        self.assertEqual(len(old),len(patched))
        self.assertEqual(25,report["speaker_to_dialogue_pixels"])
        self.assertEqual(37,report["dialogue_to_next_speaker_pixels"])
        self.assertFalse(report["release_approved"])
        self.assertFalse(report["history_scrolling_runtime_verified"])
        self.assertTrue(report["hant_basic_attack_untouched"])
        self.assertTrue(report["chronological_history_logic_unchanged"])
        self.assertEqual(["0x153da4","0x153da5","0x153dd4","0x153dd5"],
                         report["modified_original_byte_offsets"])
        allowed=set()
        for at,(before,after) in PATCHES.items():
            allowed.update(range(at,at+4))
            self.assertEqual(before,struct.unpack_from("<I",old,at)[0])
            self.assertEqual(after,struct.unpack_from("<I",patched,at)[0])
        self.assertEqual(allowed.intersection({i for i,(a,b) in enumerate(zip(old,patched)) if a!=b}),
                         {0x153da4,0x153da5,0x153dd4,0x153dd5})
        for i,(a,b) in enumerate(zip(old,patched)):
            if a!=b:self.assertIn(i,allowed)

    @unittest.skipUnless(BASE.exists(),"private r67.11 ELF fixture unavailable")
    def test_tampered_input_is_rejected(self):
        original=bytearray(BASE.read_bytes())
        original[0x153da4]^=1
        with self.assertRaisesRegex(ValueError,"baseline checksum"):
            apply(bytes(original))


if __name__=="__main__":
    unittest.main()
