"""Full r67.15c item UI semantic owner and ISO regression gates."""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_15c_synthesis_prompts import apply as synthesis,PAIRS,OWNERS,encoded_formatted,sha
from tools.r67_15c_details_footer import apply as details
from tools.r67_15c_iso_release import audit,BASE,DEST,PREV_ELF,PREV_ELF_SHA,OUT_ELF
from tools.tmx import find_tmx_entry,_decode_indices
from tools.r67_15a_items_art import FOOTER_RECTANGLES,OFFICIAL_INDICES
from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL_ART=ROOT/'local/r67-15a-analysis/B_GP004-translated-v4.BIN'

class SynthesisOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src=PREV_ELF.read_bytes()
        cls.dst=OUT_ELF.read_bytes()

    def test_synthesis_rebuilds_same_result(self):
        actual,report=synthesis(self.src,PREV_ELF_SHA)
        self.assertEqual(actual,self.dst)
        self.assertEqual(len(report["owners"]),3)

    def test_official_english_only_and_exact_native_format_directives(self):
        for off,source,ps4,en,source_row in PAIRS:
            result=encoded_formatted(en)
            self.assertEqual(result.count(b'%s'),source.count('%s'))
            self.assertTrue(result.endswith(b'\0'))
            self.assertEqual(result.count(b'\0'),1)
            self.assertEqual(result.count(b'%s'),en.count('{'))

    def test_native_three_source_japanese_strings_stay_intact(self):
        for off,source,ps4,en,source_row in PAIRS:
            expected=source.encode('cp932')+b'\0'
            self.assertEqual(self.src[off:off+len(expected)],expected)
            self.assertEqual(self.dst[off:off+len(expected)],expected)

    def test_original_item_catalog_kept_entirely(self):
        self.assertEqual(self.src[0x3912B4:0x3912B4+500*4],
                         self.dst[0x3912B4:0x3912B4+500*4])
        self.assertEqual(len(DUNGEON_ITEM_NAME_DATA),446)

    def test_source_preimage_mutation_must_fail(self):
        damaged=bytearray(self.src)
        damaged[0x386238]^=1
        with self.assertRaisesRegex(ValueError,'preimage'):
            synthesis(bytes(damaged),PREV_ELF_SHA)

    def test_only_three_documented_original_owners_and_pt_load_changed(self):
        allowed=set(range(0x64,0x68))
        for off,raw,*_ in PAIRS:
            info=OWNERS[off]
            for at in info[1:]:
                allowed.update(range(at,at+4))
        edited={i for i,(x,y) in enumerate(zip(self.src,self.dst)) if x!=y}
        self.assertTrue(edited)
        self.assertFalse(edited-allowed)

    def test_the_native_mips_sprintf_marker_is_ascii(self):
        for original,jp,ps4,en,record in PAIRS[:2]:
            match=encoded_formatted(en)
            self.assertIn(b'%s',match)
            self.assertNotIn(b'\x81\x93\x82\x93',match)

@unittest.skipUnless(ORIGINAL_ART.exists(),"Requires approved 15b art fixture")
class ItemFooterDetailsTests(unittest.TestCase):
    def test_official_details_pixel_changes_limited_to_its_one_action_tile(self):
        original=ORIGINAL_ART.read_bytes()
        result,proof=details(original)
        entry=find_tmx_entry(original,'GRP004/GP004_19.TMX')
        self.assertEqual(find_tmx_entry(result,entry.name),entry)
        o=_decode_indices(original,entry);n=_decode_indices(result,entry)
        diffs=[(i%128,i//128) for i,(x,y) in enumerate(zip(o,n)) if x!=y]
        self.assertTrue(diffs)
        self.assertTrue(all(0<=x<48 and 0<=y<32 for x,y in diffs))
        self.assertEqual(proof["official_caption"],"Details")

    def test_unmodified_storage_header_only_15b_variant(self):
        source=ORIGINAL_ART.read_bytes()
        result,_=details(source)
        for idx in (*OFFICIAL_INDICES,):
            e=find_tmx_entry(source,f'GRP004/GP004_{idx:02}.TMX')
            self.assertEqual(source[e.base_offset:e.base_offset+e.chunk_size],
                             result[e.base_offset:e.base_offset+e.chunk_size])

@unittest.skipUnless(DEST.exists(),"Requires finished 15c 2GB diagnostic")
class FinalFullDiscItemsTests(unittest.TestCase):
    def test_full_disc_three_owners_and_zero_unknown_delta(self):
        proof=audit(BASE,DEST)
        self.assertEqual(proof["status"],"PASS_FULL_DISC_EXACT_OWNED_CHANGES")
        self.assertEqual(proof["unexplained_bytes"],0)
        self.assertEqual(proof["english_synthesis_owner_count"],3)
        self.assertGreater(proof["full_iso_bytes_compared"],2_000_000_000)

if __name__=='__main__':unittest.main()
