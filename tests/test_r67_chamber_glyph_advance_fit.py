"""r67.14j native post-layout horizontal-only glyph coordinate regression."""
from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tools.r67_chamber_glyph_advance_fit import (
    patch, horizontal_glyph_helper, INPUT_SHA256, WRAPPERS,
    COMMENT_GLYPH_ADVANCE_FRACTION, SCALE_STORE, PRESERVE_S7, MAX_NODES
)
from tools.r67_chamber_restore_argument import RESTORE_T0_FROM_STACK
from tools.r67_chamber_story_text_only import (
    ELF_BIAS, ELF_SEGMENT_FO, ELF_SEGMENT_VA, _jal
)
from tools.r67_chamber_pre_glyph_font_target import sha
from tools.r67_chamber_runtime_probe import StateMemory,snapshot

ROOT=Path(__file__).resolve().parents[1]
I=ROOT/'local/r67-14i-restore-t0.elf'
J=ROOT/'local/r67-14j-glyph-x-only.elf'
ACTUAL=ROOT/'local/r67-14g-20261011-slot1-genuine-bubble-copy.p2s'

class GlyphFit(unittest.TestCase):
    def test_helper_performs_original_scale_store_and_only_modifies_glyph_node_x(self):
        words=struct.unpack('<'+'I'*(len(horizontal_glyph_helper())//4),horizontal_glyph_helper())
        self.assertEqual(SCALE_STORE,words[0])
        self.assertIn(0xE5440010,words)  # swc1 f4,0x10(t2)
        self.assertNotIn(0xE5440014,words) # no write to glyph y
        self.assertNotIn(0xAD490014,words)
        self.assertIn(0x8D4A0120,words) # lw t2,0x120(t2)
        self.assertIn(0x8D0A0004,words) # lw t2,4(t0) list head
        self.assertIn(0xC5000014,words) # lwc1 f0,0x14(t0) glyph origin
        self.assertIn(0x44891000,words) # mtc1 t1,f2
        self.assertIn(0x46022102,words) # mul.s f4,f4,f2
        self.assertEqual((0x03E00008,0),words[-2:])
        self.assertGreaterEqual(MAX_NODES,29)

    @unittest.skipUnless(I.exists() and J.exists(),'private ELF artifacts missing')
    def test_exact_two_matched_callsite_jals_and_appended_private_code_only(self):
        before=I.read_bytes()
        self.assertEqual(sha(before),INPUT_SHA256)
        after,metadata=patch(before)
        self.assertEqual(after,J.read_bytes())
        self.assertEqual(len(after),len(before)+len(horizontal_glyph_helper()))
        self.assertFalse(metadata['release_approved'])
        self.assertFalse(metadata['runtime_verified'])
        helper_va=int(metadata['helper_va'],16)
        oldchanged={i for i,(x,y) in enumerate(zip(before,after)) if x!=y}
        allowed=set(range(0x64,0x68))
        for wrapper,site in WRAPPERS:
            ofs=ELF_SEGMENT_FO+site-ELF_SEGMENT_VA
            allowed.update(range(ofs,ofs+4))
            self.assertEqual(struct.unpack_from('<2I',before,ofs),(SCALE_STORE,PRESERVE_S7))
            self.assertEqual(struct.unpack_from('<2I',after,ofs),(_jal(helper_va),PRESERVE_S7))
            # Native renderer argument preserved by r67.14i.
            renderer_delay=ELF_SEGMENT_FO+wrapper+144-ELF_SEGMENT_VA
            self.assertEqual(struct.unpack_from('<I',before,renderer_delay)[0],RESTORE_T0_FROM_STACK)
            self.assertEqual(struct.unpack_from('<I',after,renderer_delay)[0],RESTORE_T0_FROM_STACK)
            # Both unmatched paths branch directly to the unchanged s7 restore.
            self.assertEqual(struct.unpack_from('<I',before,ofs+4)[0],PRESERVE_S7)
        self.assertFalse(oldchanged-allowed)

    @unittest.skipUnless(ACTUAL.exists(),'user captured original glyph coordinates unavailable')
    def test_coordinate_model_preserves_y_and_compresses_horizontal_spacing(self):
        state=StateMemory(ACTUAL)
        nodes=snapshot(state)['text_owners'][0]['nodes']
        originals=[(node['x'],node['y']) for node in nodes if 'x' in node]
        self.assertGreaterEqual(len(originals),3)
        origin=originals[0][0]
        compressed=[(origin+(x-origin)*COMMENT_GLYPH_ADVANCE_FRACTION,y) for x,y in originals]
        for old,new in zip(originals,compressed,strict=True):
            self.assertEqual(old[1],new[1]) # no vertical changes
        self.assertLess(compressed[-1][0]-compressed[0][0],
                        originals[-1][0]-originals[0][0])
        # Two longest official text lines contain 29 full-width codepoints.
        for line in ("Make sure you're always ready","to switch into battle mode at"):
            self.assertEqual(len(line),29)
        self.assertLess(origin+28*16*COMMENT_GLYPH_ADVANCE_FRACTION, 440)

    @unittest.skipUnless(I.exists(),'r67.14i baseline unavailable')
    def test_wrong_or_already_patched_elf_refused(self):
        raw=I.read_bytes()
        with self.assertRaisesRegex(ValueError,'non-approved'):
            patch(raw[:-1])
        changed,_=patch(raw)
        with self.assertRaisesRegex(ValueError,'non-approved'):
            patch(changed)

if __name__=='__main__':unittest.main()
