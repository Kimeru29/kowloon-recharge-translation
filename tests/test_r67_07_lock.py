"""67.07 containment regression suite. Never unfreeze Basic Attack."""
import json
from pathlib import Path
import unittest
import hashlib
from tools.r67_07_lock import apply,sha,BASE_SHA
from tools.r67_06_layout import TARGET_X,ROTATE_SLOT,ROTATE_LENGTH,render_text
R=Path(__file__).resolve().parents[1]
A=R/'local/r67-06-candidate.elf'
B=R/'local/r67-05.elf'
C=R/'local/r67-07-containment.elf'
P=R/'translations/r67_help_owners.json'

class Feedback6707(unittest.TestCase):
    @unittest.skipUnless(all(p.exists() for p in (A,B,C)), "private ELF fixtures unavailable")
    def test_approved_basic_attack_frozen_and_rejected_geometry_reversed(self):
        raw=A.read_bytes();old=B.read_bytes();current=C.read_bytes()
        self.assertEqual(BASE_SHA,sha(raw))
        expected,report=apply(raw,old,json.loads(P.read_text()))
        self.assertEqual(expected,current)
        self.assertTrue(report["frozen_basic_attack"])
        self.assertEqual(render_text("Target").ljust(ROTATE_LENGTH,b"\0"),
                         current[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH])
        for pos in TARGET_X:
            self.assertEqual(current[pos:pos+4],old[pos:pos+4])
        self.assertEqual('7d154da2785f49a649df5754a2146085af8fdf2af1a2928d49a2f642ef2c1d4e',
                         report["sha256"])
        self.assertFalse(report["gameplay_approved"])
        self.assertEqual(4,len(report["unresolved"]))

    @unittest.skipUnless(all(p.exists() for p in (A,B)), "private ELF fixtures unavailable")
    def test_fails_closed_on_wrong_input(self):
        raw=bytearray(A.read_bytes())
        raw[0x853670]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint mismatch"):
            apply(bytes(raw),B.read_bytes(),json.loads(P.read_text()))

if __name__=="__main__":unittest.main()
