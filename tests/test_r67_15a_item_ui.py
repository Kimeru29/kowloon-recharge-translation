"""r67.15a item name / original Lion preservation / official UI atlas ownership.

Static constraints are not runtime screenshot approval. Full finished-ISO
classification is independently verified by release auditor.
"""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_15a_item_width import (
    apply as new_names, helper, GENERIC_NARROW_SITES,GENERIC_WIDE_SITE,
    NARROW_CELLS,WIDE_CELLS,LION_SCALE,
)
from tools.r67_15a_items_art import (
    FOOTER_RECTANGLES,OFFICIAL_INDICES,paint_footer,FONT,
    apply as new_art,
)
from tools.r67_15a_iso_release import audit,Z_ISO,A_ISO,preflight
from tools.r67_14q_approved_lock import verify_approved,MANIFEST as Q
from tools.r67_14t_approved_ui_lock import verify_ui,MANIFEST as T
from tools.r67_lion_statue_ui import ITEM_NAME_POINTER_OFFSET,CALL_SITES
from tools.r67_14t_stone_tablet_fit import read_string
from tools.tmx import find_tmx_entry,_decode_indices

ROOT=Path(__file__).resolve().parents[1]
BEFORE=ROOT/'local/r67-14z-storeroom-tablet.elf'
AFTER=ROOT/'local/r67-15a-item-width.elf'
SOURCE_ART=ROOT/'local/r67-15a-analysis/current-B_GP004.BIN'
CAND_ART=ROOT/'local/r67-15a-analysis/B_GP004-translated-v2.BIN'
OLD_SHA="c644becb11d07e5de4f1cfc78b64d87f2792073e59bcb7e2150666f6c50e46d2"

@unittest.skipUnless(BEFORE.exists() and AFTER.exists(),"Requires ignored z/15a staged ELF")
class ItemUIRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=BEFORE.read_bytes()
        cls.candidate=AFTER.read_bytes()

    def test_deterministic_exact_approved_source(self):
        actual,report=new_names(self.original,OLD_SHA,0x963FD0)
        self.assertEqual(actual,self.candidate)
        self.assertEqual(len(report["helper_owners"]),2)

    def test_exact_original_500_item_catalog_pointers_are_unchanged(self):
        self.assertEqual(self.candidate[0x3912B4:0x3912B4+500*4],
                         self.original[0x3912B4:0x3912B4+500*4])

    def test_all_mapped_names_use_two_byte_glyph_cells(self):
        from tools.dungeon_item_names_data import DUNGEON_ITEM_NAME_DATA
        self.assertEqual(len(DUNGEON_ITEM_NAME_DATA),446)
        for item, *_ in DUNGEON_ITEM_NAME_DATA:
            p=struct.unpack_from("<I",self.candidate,0x3912B4+item*4)[0]
            s=read_string(self.candidate,p)
            self.assertEqual(len(s)%2,0,(item,p))
            self.assertGreater(len(s),0)

    def test_Hydrochloric_Acid_and_Aqua_Regia_fit_relative_width(self):
        for item,boundary in ((274,17),(264,10)):
            p=struct.unpack_from("<I",self.candidate,0x3912B4+item*4)[0]
            s=read_string(self.candidate,p)
            glyphs=len(s)//2
            self.assertEqual(glyphs,boundary)
            self.assertLessEqual(glyphs*min(1.0,NARROW_CELLS/glyphs),NARROW_CELLS)
            self.assertLessEqual(glyphs*min(1.0,WIDE_CELLS/glyphs),WIDE_CELLS)

    def test_original_accepted_lion_scale_preserved(self):
        self.assertEqual(LION_SCALE,0.72)
        p=struct.unpack_from("<I",self.candidate,ITEM_NAME_POINTER_OFFSET)[0]
        s=read_string(self.candidate,p)
        self.assertEqual(s.decode("cp932"),"Ｌｉｏｎ　Ｓｔａｔｕｅ")
        self.assertEqual(self.candidate[0x803150+0x963FD0-0x902F00:
                                        0x803150+0x963FD0-0x902F00+112],
                         self.original[0x803150+0x963FD0-0x902F00:
                                       0x803150+0x963FD0-0x902F00+112])

    def test_unmodified_q_t_approved_regions_after_exact_in_memory_exception(self):
        repaired=bytearray(self.candidate)
        for site in (*GENERIC_NARROW_SITES,GENERIC_WIDE_SITE):
            o=site-0xfff80
            repaired[o:o+4]=self.original[o:o+4]
        self.assertEqual(verify_approved(bytes(repaired),json.loads(Q.read_text()))["approved_regions"],4)
        self.assertEqual(verify_ui(bytes(repaired),json.loads(T.read_text()))["all_registered_tablets"],58)

    def test_any_extra_approved_old_elf_change_cannot_pass_preflight(self):
        b=bytearray(self.original)
        b[0x3912B4+264*4]^=1
        with self.assertRaises(ValueError):
            new_names(bytes(b),OLD_SHA,0x963FD0)

    def test_two_generic_name_budgets_reject_overtly_unbounded_names(self):
        self.assertEqual((NARROW_CELLS,WIDE_CELLS),(8,15))
        self.assertGreater(len(helper(0x92cbca,8,lion_exception=True)),0)
        self.assertGreater(len(helper(0x92cbca,15,lion_exception=False)),0)

@unittest.skipUnless(SOURCE_ART.exists() and CAND_ART.exists(),"Requires local group4 fixture")
class ItemArtworkRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE_ART.read_bytes()
        cls.result=CAND_ART.read_bytes()

    def test_frozen_native_art_and_reproducible_official_english(self):
        dest,report=new_art(self.source)
        self.assertEqual(dest,self.result)
        self.assertEqual(tuple(x["official_en_index"] for x in report["official_ps4_art"]),
                         (3,5,15,16,17,18))

    def test_only_exact_owned_texture_chunks_change(self):
        allowed=[]
        for idx in (*OFFICIAL_INDICES,19):
            a=find_tmx_entry(self.source,f"GRP004/GP004_{idx:02}.TMX")
            b=find_tmx_entry(self.result,a.name)
            self.assertEqual(a,b)
            allowed.append((a.base_offset,a.base_offset+a.chunk_size))
        self.assertTrue(any(x!=y for x,y in zip(self.source,self.result)))
        for i,(a,b) in enumerate(zip(self.source,self.result)):
            if a!=b:self.assertTrue(any(lo<=i<hi for lo,hi in allowed),hex(i))

    def test_item_footer_all_labels_have_independent_nonoverlapping_cells(self):
        self.assertEqual(len(FOOTER_RECTANGLES),5)
        occupied=set()
        for x0,y0,x1,y1,label in FOOTER_RECTANGLES:
            self.assertLessEqual(len(label)*6-1,(x1-x0)-6)
            self.assertLessEqual(14,y1-y0-6)
            self.assertFalse(set(label)-set(FONT))
            for y in range(y0,y1):
                for x in range(x0,x1):
                    self.assertNotIn((x,y),occupied)
                    occupied.add((x,y))

    def test_footer_mutation_cannot_cross_into_unapproved_texture(self):
        art,report=paint_footer(self.source)
        t=find_tmx_entry(self.source,'GRP004/GP004_19.TMX')
        a,b=_decode_indices(self.source,t),_decode_indices(art,t)
        self.assertEqual(len(a),len(b))
        self.assertTrue(any(i!=j for i,j in zip(a,b)))
        self.assertEqual(report['captions'],['INFO','COMPOUND','SWAP','DISCARD','RECYCLE'])

@unittest.skipUnless(A_ISO.exists(),"Requires built full diagnostic")
class FinishedItemISOAuditTests(unittest.TestCase):
    def test_complete_two_gigabyte_iso_owned_differences(self):
        audit_report=audit(Z_ISO,A_ISO)
        self.assertEqual(audit_report["unexplained_bytes"],0)
        self.assertEqual(audit_report["status"],"PASS_ZERO_UNEXPLAINED_FINISHED_ISO_BYTES")
        self.assertGreater(audit_report["modified_bytes"],300_000)

if __name__=="__main__": unittest.main()
