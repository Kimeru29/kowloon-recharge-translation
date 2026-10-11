"""r67.11 chronological START history grouping and safety regressions."""
from __future__ import annotations
from pathlib import Path
import struct
import unittest

from tools.r67_history_sections_probe import (
    BASE_SHA, PREIMAGES, REPLACEMENTS,
    RING_CAPACITY, MAX_VISIBLE,
    _jal, apply, chronological_slots, helper, sha
)
from tools.r67_history_rows_probe import EXPECTED as ROW_POSITION_PATCHES
from tools.r67_history_direction_probe import FACTORY_START_VA,FACTORY_END_VA,VA_MINUS_OFFSET

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-10-history-rows.elf"
CANDIDATE=ROOT/"local/r67-11-history-sections.elf"

class HistorySections(unittest.TestCase):
    def test_visible_story_order_after_one_turn_and_multiple_turns(self):
        self.assertEqual((0,1),chronological_slots(2,2))
        self.assertEqual((0,1,2,3),chronological_slots(4,4))
        self.assertEqual(tuple(range(12)),chronological_slots(12,12))
        self.assertEqual(tuple(range(7,19)),chronological_slots(19,12))
        self.assertEqual(tuple(range(243,255)),chronological_slots(255,12))
        self.assertEqual(tuple(range(250,255))+tuple(range(7)),
                         chronological_slots(262,12))
        self.assertEqual((254,),chronological_slots(255,1))
        for n in (1,2,4,12,25,254,255,256,262,510,1024):
            for visible in range(1,min(n,MAX_VISIBLE)+1):
                result=chronological_slots(n,visible)
                self.assertEqual(len(set(result)),visible)
                for a,b in zip(result,result[1:]):
                    self.assertEqual((a+1)%RING_CAPACITY,b)

    def test_invalid_history_windows_rejected(self):
        for count,visible in ((0,1),(5,0),(1,2),(20,13),(-1,1)):
            with self.subTest(count=count,visible=visible):
                with self.assertRaisesRegex(ValueError,"Invalid count"):
                    chronological_slots(count,visible)

    def test_helper_has_exact_12_mips_instructions_no_external_calls(self):
        blob=helper()
        self.assertEqual(48,len(blob))
        words=struct.unpack("<12I",blob)
        self.assertEqual(words[5],0x240300FF)
        self.assertEqual(words[-2:],(0x03E00008,0))
        self.assertFalse(any(w>>26 in (2,3) for w in words))

    @unittest.skipUnless(BASE.exists() and CANDIDATE.exists(),
                         "r67 private generated ELF fixtures absent")
    def test_change_is_bounded_to_history_index_grouping_and_ptload(self):
        original=BASE.read_bytes()
        generated, metadata=apply(original)
        after=CANDIDATE.read_bytes()
        self.assertEqual(BASE_SHA,sha(original))
        self.assertEqual(generated,after)
        self.assertEqual(48,metadata["helper_bytes"])
        self.assertFalse(metadata["release_approved"])
        self.assertFalse(metadata["full_history_paging_verified"])
        self.assertTrue(metadata["protected_basic_attack_untouched"])
        self.assertTrue(metadata["normal_dialogue_untouched"])
        self.assertEqual(len(after),len(original)+len(helper()))
        allowed=set(range(0x64,0x68))
        for at in PREIMAGES:allowed.update(range(at,at+4))
        diffs=[at for at,(a,b) in enumerate(zip(original,after)) if a!=b]
        self.assertTrue(diffs)
        self.assertFalse(set(diffs)-allowed)
        for at,(old,new) in ROW_POSITION_PATCHES.items():
            self.assertEqual(struct.unpack_from("<I",original,at)[0],new)
            self.assertEqual(struct.unpack_from("<I",after,at)[0],new)
        # Shared native constructor, including the approved style-direction selector, is pristine.
        factory=FACTORY_START_VA-VA_MINUS_OFFSET
        n=FACTORY_END_VA-FACTORY_START_VA
        self.assertEqual(original[factory:factory+n],after[factory:factory+n])
        self.assertEqual(original[0x155F08:0x155F0C],after[0x155F08:0x155F0C])
        # The r67.10 cloned history constructor is also unchanged.
        self.assertEqual(original[8797344:8797920],after[8797344:8797920])
        for off,new in REPLACEMENTS.items():
            self.assertEqual(struct.unpack_from("<I",original,off)[0],PREIMAGES[off])
            self.assertEqual(struct.unpack_from("<I",after,off)[0],new)

    @unittest.skipUnless(BASE.exists(),"r67.10 baseline unavailable")
    def test_fails_closed_on_wrong_elf_or_changed_history_code(self):
        data=bytearray(BASE.read_bytes())
        data[0x153B68]^=1
        with self.assertRaisesRegex(ValueError,"SHA drift"):
            apply(bytes(data))

if __name__=="__main__":
    unittest.main()
