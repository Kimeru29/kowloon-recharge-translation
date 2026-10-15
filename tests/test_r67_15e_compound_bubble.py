"""r67.15e: preserve all approved r67.15d behaviour outside two owners.

The tests assert immutable approved 15d input hashes, every previous ELF
byte except the exact pointer and native branch, read-only group4 art,
official PS4 Can't mapping, and dedicated horizontal sprite scale behavior.
Native MIPS helper execution is tested in Unicorn on disposable memory.
"""
from __future__ import annotations
import json,struct,unittest
from pathlib import Path
from tools.r67_15e_compound_action_bubble import (
    apply,build_helper,sha,_j,BASE_SHA,FO,VA,BIAS,RESUME,
    JUMP_SITE,JUMP_ORIGINAL,ACTION_PTR_OFF,COMPOUND_ACTION_ID,
    SPRITE_X_SCALE_OFFSET,TARGET_X_SCALE,ACTION_NAME_EN
)
from tools.r67_15e_iso_release import (
    PREVIOUS_ISO,CANDIDATE_ISO,SOURCE_ELF,CANDIDATE_ELF,
    PREVIOUS_SHA,audit
)
from tools.r67_14t_stone_tablet_fit import read_string
from tools.r67_14y_release import verify_save_identity
from tools.r67_14y_inspection_save import validate_result
from tools.r67_history_layout_lock import verify_bytes,read_lock

try:
    from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
    from unicorn.mips_const import UC_MIPS_REG_S0,UC_MIPS_REG_A1
    UNICORN_AVAILABLE=True
except ImportError:
    UNICORN_AVAILABLE=False

ROOT=Path(__file__).resolve().parents[1]
APPROVED_15D_ISO=PREVIOUS_SHA
APPROVED_15D_ELF=BASE_SHA

@unittest.skipUnless(SOURCE_ELF.exists() and CANDIDATE_ELF.exists(),"Requires local 15d and 15e ELF fixtures")
class ImmutableApproved15dTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before=SOURCE_ELF.read_bytes()
        cls.after=CANDIDATE_ELF.read_bytes()

    def test_source_sha_matches_approved_playtested_15d(self):
        self.assertEqual(sha(self.before),APPROVED_15D_ELF)

    def test_new_elf_is_deterministic_from_exact_approved_15d_source(self):
        actual,report=apply(self.before)
        self.assertEqual(actual,self.after)
        self.assertEqual(report['only_compound_action_id'],3)

    def test_native_q_t_y_gold_chains_synthesis_text_and_item_catalog_immutable(self):
        allowed=set(range(0x64,0x68))
        for off in (ACTION_PTR_OFF,JUMP_SITE-BIAS):allowed.update(range(off,off+4))
        for i,(a,b) in enumerate(zip(self.before,self.after)):
            if a!=b:self.assertIn(i,allowed,hex(i))

    def test_exact_white_bubble_branch_is_only_original_native_code_change(self):
        off=JUMP_SITE-BIAS
        self.assertEqual(struct.unpack_from('<I',self.before,off)[0],JUMP_ORIGINAL)
        self.assertEqual(struct.unpack_from('<I',self.after,off)[0],
                         _j(int(json.loads((ROOT/'local/r67-15e-compound-bubble.json').read_text())['helper_va'],16)))
        self.assertEqual(self.before[off+4:off+8],b'\0'*4)
        self.assertEqual(self.after[off+4:off+8],b'\0'*4)

    def test_official_ps4_cant_is_native_fullwidth_and_adjacent_actions_preserved(self):
        p=struct.unpack_from('<I',self.after,ACTION_PTR_OFF)[0]
        self.assertEqual(read_string(self.after,p).decode('cp932'),'Ｃａｎ’ｔ')
        self.assertEqual(len(read_string(self.after,p)),2*len(ACTION_NAME_EN))
        for neighbor in (0x386320,0x386328,0x38632c,0x386330,0x386334):
            self.assertEqual(self.before[neighbor:neighbor+4],self.after[neighbor:neighbor+4])

    def test_save_descriptors_and_registered_inspections_are_still_exact(self):
        self.assertEqual(verify_save_identity(self.after),verify_save_identity(self.before))
        self.assertEqual(validate_result(self.after),validate_result(self.before))
        self.assertEqual(len(verify_bytes(self.after,read_lock())),4)

    def test_source_byte_mutation_cannot_qualify_as_approved_release(self):
        altered=bytearray(self.before)
        altered[0x58A9F4]^=1
        with self.assertRaisesRegex(ValueError,'SHA'):apply(bytes(altered))

    def test_native_helper_only_writes_compound_sprite_xscale(self):
        body=build_helper()
        self.assertEqual(len(body),44)
        self.assertEqual(struct.unpack_from('<I',body,8)[0],0x15090006)
        self.assertEqual(struct.unpack_from('<I',body,20)[0],0x11000003)
        self.assertEqual(struct.unpack_from('<I',body,32)[0],0xAD090060)
        self.assertEqual(struct.unpack_from('<I',body,36)[0],_j(RESUME))

@unittest.skipUnless(UNICORN_AVAILABLE,"Install unicorn for native MIPS helper runtime tests")
class NativeCompoundBubbleMipsTests(unittest.TestCase):
    def test_all_16_action_ids_and_null_sprite_in_native_mips(self):
        from tools.r67_15e_compound_action_bubble import RESUME
        raw=CANDIDATE_ELF.read_bytes()
        manifest=json.loads((ROOT/'local/r67-15e-compound-bubble.json').read_text())
        helper_va=int(manifest['helper_va'],16)
        data=raw[FO+helper_va-VA:FO+helper_va-VA+44]
        self.assertEqual(data,build_helper())
        for index in range(16):
            for null in (False,True):
                with self.subTest(action=index,null=null):
                    uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
                    uc.mem_map(0x900000,0x100000)
                    uc.mem_map(0x110000,0x10000)
                    uc.mem_map(0x200000,0x20000)
                    uc.mem_write(helper_va,data)
                    uc.mem_write(RESUME,b'\0'*8)
                    owner=0x210000
                    sprite=0x211000
                    uc.mem_write(owner,struct.pack('<I',0 if null else sprite))
                    uc.mem_write(owner+0x18,struct.pack('<I',index))
                    uc.mem_write(sprite+0x60,struct.pack('<f',1.0))
                    uc.mem_write(sprite+0x64,struct.pack('<f',1.0))
                    uc.reg_write(UC_MIPS_REG_S0,owner)
                    uc.reg_write(UC_MIPS_REG_A1,0)
                    reached=[]
                    def stop_at_resume(engine,address,size,data):
                        if address==RESUME:
                            reached.append(address);engine.emu_stop()
                    uc.hook_add(UC_HOOK_CODE,stop_at_resume)
                    uc.emu_start(helper_va,RESUME+4,count=15)
                    self.assertEqual(reached,[RESUME])
                    x=struct.unpack('<f',uc.mem_read(sprite+0x60,4))[0]
                    y=struct.unpack('<f',uc.mem_read(sprite+0x64,4))[0]
                    self.assertEqual(x,2.0 if index==COMPOUND_ACTION_ID and not null else 1.0)
                    self.assertEqual(y,1.0)
                    self.assertEqual(uc.reg_read(UC_MIPS_REG_A1),0)

@unittest.skipUnless(CANDIDATE_ISO.exists(),"Requires finished 15e ISO")
class FullFinishedReleaseAuditTests(unittest.TestCase):
    def test_full_two_gigabyte_disc_only_owns_bubble_and_cant(self):
        check=audit(PREVIOUS_ISO,CANDIDATE_ISO)
        self.assertEqual(check['status'],'PASS_EXACT_15D_BASELINE_ZERO_UNEXPLAINED')
        self.assertEqual(check['complete_disc_bytes_compared'],2095382528)
        self.assertEqual(check['unexplained_bytes'],0)
        self.assertTrue(check['all_previous_15d_group4_graphics_identical'])

if __name__=='__main__':unittest.main()
