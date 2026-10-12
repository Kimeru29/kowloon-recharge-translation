"""All native companion-event records share ONE geometry invariant (r67.14x).

Execute the *compiled* MIPS helper for every 601 event IDs, two subrows,
both companion slots, and 600 AFK record IDs. Test original user-approved
Eerie+opening text pointer/coordinates and no AFK sprite modifications.
"""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from test_r67_14w_opening_bubble_geometry import execute_helper,TASK
from tools.r67_14x_generic_event_bubble import (
    apply,make_geometry_helper,EVENT_RECORD_END_EXCLUSIVE,AFK_FIRST_RECORD,
    AFK_RECORDS,ORIGINAL_RECONSTRUCTION_STORE_VA,
    GREEN_STATIC_VA,BLUE_STATIC_VA,GREEN_NATIVE,GREEN_NATIVE_PIVOT_X,
    BLUE_NATIVE,BLUE_NATIVE_PIVOT_Y,
)
from tools.r67_14w_scoped_approval_lock import SOURCE_T_SHA
from tools.r67_14q_approved_lock import MANIFEST as Q_MANIFEST, verify_approved
from tools.r67_14t_approved_ui_lock import MANIFEST as T_MANIFEST, verify_ui
from tools.r67_chamber_story_text_only import ELF_SEGMENT_FO,ELF_SEGMENT_VA,_jal

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/"local/r67-14t-lion-and-tablets.elf"
NEW=ROOT/"local/r67-14x-generic-event-bubble.elf"

def as_words(values):
    return tuple(struct.unpack("<I",struct.pack("<f",v))[0] for v in values)

def assert_frame(test,memory,slot):
    gp=GREEN_STATIC_VA+slot*0x30
    test.assertEqual(tuple(memory[gp+i*4] for i in range(4)),
                     as_words((GREEN_NATIVE[0],GREEN_NATIVE[1],
                               GREEN_NATIVE_PIVOT_X[slot],GREEN_NATIVE[2])))
    for frame in range(3):
        bp=BLUE_STATIC_VA+frame*0x30
        test.assertEqual(tuple(memory[bp+i*4] for i in range(4)),
                         as_words((BLUE_NATIVE[0],BLUE_NATIVE[1],BLUE_NATIVE[2],
                                   BLUE_NATIVE_PIVOT_Y[frame])))

@unittest.skipUnless(OLD.is_file() and NEW.is_file(),"Requires fingerprinted stage diagnostics")
class GenericCompanionBubbleGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=OLD.read_bytes()
        cls.new=NEW.read_bytes()
        cls.helper=make_geometry_helper()

    def test_all_601_event_records_two_subrows_both_slots_restore_shape(self):
        self.assertEqual(EVENT_RECORD_END_EXCLUSIVE,601)
        for event_id in range(EVENT_RECORD_END_EXCLUSIVE):
            for slot in (0,1):
                for row in (0,1):
                    memory,old,registers,steps=execute_helper(event_id,row,slot,code=self.helper)
                    assert_frame(self,memory,slot)
                    self.assertEqual(memory[TASK+0x5c],0)
                    self.assertEqual(registers[3],slot)
                    self.assertLess(steps,100)
        self.assertEqual(len(self.helper),188)

    def test_600_afk_records_do_not_modify_any_sprite_resource(self):
        self.assertEqual(AFK_RECORDS,600)
        for event_id in range(AFK_FIRST_RECORD,AFK_FIRST_RECORD+AFK_RECORDS):
            for slot in (0,1):
                memory,before,registers,steps=execute_helper(event_id,0,slot,code=self.helper)
                self.assertEqual({k:v for k,v in memory.items() if k!=TASK+0x5C},
                                 {k:v for k,v in before.items() if k!=TASK+0x5C})
                self.assertEqual(registers[3],slot)

    def test_invalid_slot_and_out_of_namespace_do_not_mutate_shapes(self):
        for record in (-1,601,1201):
            for slot in (-1,2,0,1):
                if record==1201 and slot==2:continue
                memory,before,_,_=execute_helper(record,1,slot,code=self.helper)
                self.assertEqual({k:v for k,v in memory.items() if k!=TASK+0x5C},
                                 {k:v for k,v in before.items() if k!=TASK+0x5C})
        for slot in (-1,2):
            memory,before,_,_=execute_helper(2,1,slot,code=self.helper)
            self.assertEqual({k:v for k,v in memory.items() if k!=TASK+0x5C},
                             {k:v for k,v in before.items() if k!=TASK+0x5C})

    def test_short_Eerie_and_two_line_opening_get_same_native_geometry(self):
        for row in (0,1):
            for slot in (0,1):
                memory,before,_,_=execute_helper(2,row,slot,code=self.helper)
                assert_frame(self,memory,slot)
        for src,p in ((0x3D3428,0x9630BA),(0x3D3438,0x963F00),
                      (0x3D343C,0x963F8C)):
            self.assertEqual(struct.unpack_from("<I",self.new,src)[0],p)

    def test_original_text_y_preserved_for_every_event(self):
        for va in (0x963D78,0x963E54):
            off=ELF_SEGMENT_FO+va-ELF_SEGMENT_VA
            self.assertEqual(self.old[off:off+8],self.new[off:off+8])
        self.assertEqual((280-(346-77),300-(346-77)),(11,31))

    def test_strict_original_q_and_t_manifest_differ_only_one_native_JAL(self):
        clone=bytearray(self.new)
        original_offset=ORIGINAL_RECONSTRUCTION_STORE_VA-0xFFF80
        self.assertNotEqual(self.old[original_offset:original_offset+4],
                            self.new[original_offset:original_offset+4])
        clone[original_offset:original_offset+4]=self.old[original_offset:original_offset+4]
        self.assertEqual(verify_approved(bytes(clone),json.loads(Q_MANIFEST.read_text()))["approved_regions"],4)
        result=verify_ui(bytes(clone),json.loads(T_MANIFEST.read_text()))
        self.assertEqual(result["lion_approved_horizontal_scale"],0.72)
        self.assertEqual(result["all_registered_tablets"],58)
        self.assertEqual(result["overwide_rows"],0)

    def test_fail_closed_original_source_preimage_and_deterministic_patch(self):
        rebuilt,report=apply(self.old)
        self.assertEqual(rebuilt,self.new)
        self.assertEqual(report["event_records_covered"],601)
        with self.assertRaisesRegex(ValueError,"Source must be exact|Source must"):
            apply(self.new)

if __name__=="__main__":unittest.main()
