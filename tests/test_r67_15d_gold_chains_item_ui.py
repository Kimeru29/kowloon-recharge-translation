"""r67.15d targeted native owners, visual cell budgets and ISO regression."""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path

from tools.r67_15d_gold_chains_compound import (
    apply as patch_native,OWNERS,OFFICIAL,SOURCE_SHA,EMPTY,sha,
)
from tools.r67_15d_visible_art import (
    apply as patch_art,BASE_C_SHA,OFFICIAL_V2_SHA,STORAGE,FOOTER,
    LIVE_SECOND_SLOT,
)
from tools.r67_15d_iso_release import (
    OLD,NEW,ELF_BEFORE,ELF_AFTER,ART_BEFORE,ART_AFTER,PS4_EN,audit,
)
from tools.r67_14t_stone_tablet_fit import read_string
from tools.tmx import find_tmx_entry,_decode_indices

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(ELF_BEFORE.exists() and ELF_AFTER.exists(),"Requires ignored staged local ELFs")
class GoldChainsAndSynthesisRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=ELF_BEFORE.read_bytes()
        cls.after=ELF_AFTER.read_bytes()

    def test_exact_15c_preimage_and_deterministic_gold_chains_patch(self):
        self.assertEqual(sha(self.before),SOURCE_SHA)
        built,proof=patch_native(self.before)
        self.assertEqual(built,self.after)
        self.assertEqual(len(proof["owned_native_pointer_records"]),6)

    def test_title_and_three_semantically_complete_rows_are_bounded(self):
        rows=[]
        for field in (0x58A9F0,0x58A9F4,0x58A9F8,0x58A9FC):
            ptr=struct.unpack_from('<I',self.after,field)[0]
            data=read_string(self.after,ptr)
            decoded=data.decode('cp932')
            self.assertEqual(len(data),len(decoded)*2)
            self.assertLessEqual(len(decoded),14 if field==0x58A9F0 else 21)
            rows.append(decoded)
        self.assertEqual(len(rows),4)
        self.assertIn('Ｇｏｌｄ　Ｃｈａｉｎｓ',rows[0])
        self.assertIn('ｐｕｒｅ',rows[2])
        self.assertIn('ｄｏｏｒ',rows[3])

    def test_japanese_furigana_suppressed_and_reserved_empty_owner_preserved(self):
        self.assertEqual(struct.unpack_from('<I',self.after,0x58AA04)[0],EMPTY)
        self.assertEqual(struct.unpack_from('<I',self.after,0x58AA00)[0],EMPTY)

    def test_synthesis_floating_label_picks_exact_official_compound(self):
        new=struct.unpack_from('<I',self.after,0x38632C)[0]
        self.assertEqual(read_string(self.after,new).decode('cp932'),'Ｃｏｍｐｏｕｎｄ')
        self.assertEqual(OFFICIAL[0x46208],('調合','Compound'))

    def test_reject_any_previously_approved_native_text_mutation(self):
        bad=bytearray(self.before);bad[0x58A9F0]^=1
        with self.assertRaisesRegex(ValueError,'preimage'):patch_native(bytes(bad))

    def test_only_six_exact_owned_pointer_words_and_elf_size_change(self):
        allowed=set(range(0x64,0x68))
        for owner in OWNERS:allowed.update(range(owner,owner+4))
        actual={i for i,(old,new) in enumerate(zip(self.before,self.after)) if old!=new}
        self.assertTrue(actual)
        self.assertFalse(actual-allowed)

    def test_existing_nontranslated_inspections_and_item_catalog_byte_intact(self):
        for start,end in [(0x3912B4,0x3912B4+500*4),(0x58A120,0x58A150),
                          (0x58A2C0,0x58A2D8),(0x407460,0x407490)]:
            with self.subTest(start=hex(start)):
                self.assertEqual(self.before[start:end],self.after[start:end])

@unittest.skipUnless(ART_BEFORE.exists() and ART_AFTER.exists(),"Requires verified local group4")
class EnglishArtworkNativeCellRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=ART_BEFORE.read_bytes()
        cls.new=ART_AFTER.read_bytes()
        cls.official=PS4_EN.read_bytes()

    def test_exact_previous_art_and_official_english_fingerprints(self):
        self.assertEqual(sha(self.old),BASE_C_SHA)
        self.assertEqual(sha(self.official),OFFICIAL_V2_SHA)
        expected,meta=patch_art(self.old,self.official)
        self.assertEqual(expected,self.new)
        self.assertTrue(meta['header']['exact_official_ps4_title_and_vest'])

    def test_original_ps4_choose_storage_and_vest_and_room_are_unchanged(self):
        record=find_tmx_entry(self.old,STORAGE)
        a=_decode_indices(self.new,record)
        b=_decode_indices(self.official,record)
        for idx,(x,y) in enumerate(zip(a,b)):
            col,row=idx%256,idx//256
            if not(130<=col<205 and 7<=row<25):
                self.assertEqual(x,y,idx)

    def test_all_other_group4_texture_regions_immutable(self):
        intervals=[]
        for name in (STORAGE,FOOTER):
            t=find_tmx_entry(self.old,name)
            self.assertEqual(t,find_tmx_entry(self.new,name))
            intervals.append((t.base_offset,t.base_offset+t.chunk_size))
        for i,(a,b) in enumerate(zip(self.old,self.new)):
            if a!=b:self.assertTrue(any(lo<=i<hi for lo,hi in intervals),hex(i))

    def test_official_compound_renders_all_eight_letters_inside_48px_uv(self):
        orig=find_tmx_entry(self.old,FOOTER)
        b=_decode_indices(self.new,orig)
        from tools.r67_15a_items_art import FOOTER_NATIVE_GOLD,FOOTER_NATIVE_TRANSPARENT
        x0,y0,x1,y1=LIVE_SECOND_SLOT
        active=[(i%128,i//128) for i,color in enumerate(b)
                if color==FOOTER_NATIVE_GOLD and x0<=i%128<x1 and y0<=i//128<y1]
        self.assertTrue(active)
        self.assertGreaterEqual(min(x for x,y in active),48)
        self.assertLess(max(x for x,y in active),96)
        self.assertLessEqual(max(x for x,y in active)-min(x for x,y in active)+1,39)

    def test_sibling_items_actions_unchanged(self):
        e=find_tmx_entry(self.old,FOOTER)
        before=_decode_indices(self.old,e)
        after=_decode_indices(self.new,e)
        for i,(x,y) in enumerate(zip(before,after)):
            col,row=i%128,i//128
            if not(48<=col<124 and 0<=row<32):self.assertEqual(x,y,i)

@unittest.skipUnless(NEW.exists(),"Requires finished 15d ISO")
class FinishedDiscChangeAudit(unittest.TestCase):
    def test_complete_disc_has_no_unexplained_bytes(self):
        proof=audit(OLD,NEW)
        self.assertEqual(proof['unexplained_bytes'],0)
        self.assertEqual(proof['physical_iso_bytes_compared'],2095382528)
        self.assertEqual(proof['status'],'PASS_ZERO_UNEXPLAINED_15D_FINISHED_ISO_BYTES')

if __name__=='__main__':unittest.main()
