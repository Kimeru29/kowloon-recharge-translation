"""67.06 candidate: precisely owned target-control placement and Help reflow."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import unittest

from tools.r67_06_layout import (
    apply, sha, BASE_SHA, CAPTION_RESTORED, TARGET_X,
    HANT_REPLACEMENTS, ROTATE_SLOT, ROTATE_LENGTH, render_text,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent/'startup-flow-v10/fixtures/elf/SLPM_665.11'
PRIOR = ROOT/'local/r67-05.elf'
CANDIDATE = ROOT/'local/r67-06-candidate.elf'
MANIFEST = ROOT/'translations/r67_help_owners.json'

class Candidate6706(unittest.TestCase):
    def test_restores_full_caption_and_moves_sprites_as_one_group(self):
        self.assertEqual('Change target', CAPTION_RESTORED)
        self.assertEqual(4,len(TARGET_X))
        self.assertEqual(2,len(HANT_REPLACEMENTS))
        self.assertEqual([17,20],sorted(HANT_REPLACEMENTS))
        # Position origins are a matched group: two sprite anchors, backing
        # and text all move together by exactly 100.0 in native coordinates.
        from struct import unpack
        shifts=[]
        for old,new in TARGET_X.values():
            aa=unpack('>f',(old&65535).to_bytes(2,'big')+b'\0\0')[0]
            bb=unpack('>f',(new&65535).to_bytes(2,'big')+b'\0\0')[0]
            shifts.append(aa-bb)
        self.assertEqual([100.0]*4,shifts)

    @unittest.skipUnless(all(p.exists() for p in (SOURCE,PRIOR,CANDIDATE)),
                         "Private executable inputs unavailable")
    def test_byte_exact_candidate_preserves_every_accepted_owner(self):
        pristine,prior,current=(p.read_bytes() for p in (SOURCE,PRIOR,CANDIDATE))
        self.assertEqual(BASE_SHA,sha(prior))
        pages=json.loads(MANIFEST.read_text())['pages']
        actual,report=apply(pristine,prior,pages)
        self.assertEqual(actual,current)
        self.assertEqual('0b6786e9e69b490117306df543247871ff688ba791a1a7c698580476a78a36ed',
                         report['sha256'])
        self.assertFalse(report['visual_acceptance'])
        self.assertFalse(report['save_namespace_modified'])
        self.assertEqual(
            render_text('Change target').ljust(ROTATE_LENGTH,b'\0'),
            current[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH]
        )
        # Screens explicitly frozen by Pablo after his 67.05 playtest:
        for start,end in (
            (0x594FA0,0x594FA4), # Stone Pedestal Push/Use Item
            (0x58A040,0x58A058), # physical lion inspection
            (0x3D3428,0x3D343C), # independent old-man story comments
            (0x391928,0x39192C), # full official item catalog name
            (0x159D54,0x159D58), # history hook, not yet understood
            (0x14E96C,0x14E970), # accepted ordinary dialogue orientation
            (0x150050,0x150054), # accepted dialogue geometry
        ):
            self.assertEqual(prior[start:end],current[start:end],hex(start))
        bad=bytearray(prior)
        bad[0x3D3438]^=1
        with self.assertRaisesRegex(ValueError, '67.05 executable drift'):
            apply(pristine,bytes(bad),pages)

if __name__=='__main__':
    unittest.main()
