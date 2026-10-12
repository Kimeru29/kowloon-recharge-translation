"""Exhaustive game-wide stone-tablet width regression tests (58 native records)."""
from __future__ import annotations
import json
from pathlib import Path
import struct
import unittest
from tools import r67_14t_stone_tablet_fit as tablet
from tools import r67_14s_lion_final_fit as lion
from tools.r67_14q_approved_lock import MANIFEST,verify_approved

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/"local/r67-14s-lion-final-fit.elf"
R=ROOT/"local/r67-14r-lion-statue-ui.elf"

@unittest.skipUnless(S.exists() and R.exists(),"Needs ignored staged r67.14r/r67.14s ELFs")
class StoneTabletWidthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=S.read_bytes()
        cls.result,cls.report=tablet.apply(cls.source)

    def test_exactly_58_tablets_discovered_gamewide(self):
        records=tablet.tablet_registry(self.result)
        self.assertEqual(len(records),58)
        self.assertEqual(records[0],0x58A250)
        self.assertEqual(records[-1],0x594420)
        self.assertIn(0x590F30,records)
        self.assertIn(0x590FB0,records)

    def test_all_160_inscription_rows_are_bounded(self):
        state=tablet.assert_all_tablets_fit(self.result)
        self.assertEqual(state["populated_tablet_rows"],160)
        self.assertEqual(state["overwide_rows"],0)
        self.assertLessEqual(state["maximum_current_glyph_count"],21)

    def test_six_unbounded_translation_rows_are_exact_expected_owners(self):
        over=[r for r in tablet.tablet_rows(self.source) if r["cell_count"]>tablet.MAX_GLYPH_CELLS]
        owners={r["record_offset"]+4*r["row_index"] for r in over}
        self.assertEqual(owners,set(tablet.COMPACT_INSCRIPTION_TEXT))
        self.assertEqual(len(owners),6)
        for off in owners:
            old=struct.unpack_from("<I",self.source,off)[0]
            new=struct.unpack_from("<I",self.result,off)[0]
            self.assertNotEqual(old,new)
            content=tablet.read_string(self.result,new)
            self.assertTrue(content.startswith(tablet.PREFIX[off]))
            self.assertTrue(content.endswith(tablet.SUFFIX.get(off,b"")) or
                (not tablet.SUFFIX.get(off)))
            self.assertLessEqual(len(content.decode("cp932")),21)
            self.assertEqual(content+b"\0",tablet.replacement_at(off))

    def test_all_56_other_tablet_records_are_byte_identical(self):
        for record in tablet.tablet_registry(self.source):
            if record not in (0x590F30,0x590FB0):
                self.assertEqual(self.result[record:record+24],self.source[record:record+24])

    def test_no_old_elf_mutations_outside_tablet_aliases_and_size(self):
        allow=set(range(0x64,0x68))
        for off in tablet.COMPACT_INSCRIPTION_TEXT:allow.update(range(off,off+4))
        changed={i for i,(a,b) in enumerate(zip(self.source,self.result)) if a!=b}
        self.assertTrue(changed)
        self.assertFalse(changed-allow)
        self.assertEqual(self.result[0x391928:0x39192c],self.source[0x391928:0x39192c])
        for site in (0x2A2A6C,0x2A6060):
            off=site-0xFFF80
            self.assertEqual(self.result[off:off+4],self.source[off:off+4])

    def test_reject_future_oversized_stone_tablet_row(self):
        modified=bytearray(self.result)
        # Restore an old English line (29+ cells) into a DIFFERENT tablet.
        struct.pack_into("<I",modified,0x591098,0x94EC76)
        with self.assertRaisesRegex(ValueError,"Oversized stone tablet"):
            tablet.assert_all_tablets_fit(bytes(modified))

    def test_reject_missing_or_reclassified_native_tablet_owner(self):
        modified=bytearray(self.result)
        struct.pack_into("<I",modified,0x594420,0)
        with self.assertRaisesRegex(ValueError,"Tablet registry drift"):
            tablet.tablet_registry(bytes(modified))

    def test_approved_q_lock_and_lion_refinement_survive(self):
        self.assertEqual(
            verify_approved(self.result,json.loads(MANIFEST.read_text()))["status"],
            "PASS_R67_14Q_VISUALLY_APPROVED_OWNERS"
        )
        lion_elf,lion_report=lion.apply(R.read_bytes())
        self.assertEqual(lion_elf,self.source)
        self.assertEqual(lion_report["scale_after"],0.72)

    def test_reject_unknown_candidate_repatch(self):
        with self.assertRaisesRegex(ValueError,"Expected exact"):
            tablet.apply(self.result)


if __name__=="__main__":unittest.main()
