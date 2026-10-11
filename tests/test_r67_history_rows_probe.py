"""Regression tests for horizontal dialogue history row-coordinate routing."""
from __future__ import annotations
import struct
import unittest
from pathlib import Path
from tools.r67_history_rows_probe import EXPECTED,INPUT_SHA256,sha,apply
from tools.r67_history_direction_probe import FACTORY_START_VA,FACTORY_END_VA,VA_MINUS_OFFSET

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"local/r67-08-history-direction.elf"
OUTPUT=ROOT/"local/r67-10-history-rows.elf"

class HistoryRows(unittest.TestCase):
    @unittest.skipUnless(BASE.exists() and OUTPUT.exists(),"private ISO-stage ELF absent")
    def test_bounded_position_only_and_horizontal_direction_preserved(self):
        original=BASE.read_bytes()
        result=OUTPUT.read_bytes()
        self.assertEqual(INPUT_SHA256,sha(original))
        generated,info=apply(original)
        self.assertEqual(generated,result)
        self.assertEqual(len(original),len(result))
        self.assertFalse(info["approved_release"])
        self.assertEqual(["0x153d68","0x153d6c"],info["changed_byte_offsets"])
        for at,(old,new) in EXPECTED.items():
            self.assertEqual(struct.unpack_from("<I",original,at)[0],old)
            self.assertEqual(struct.unpack_from("<I",result,at)[0],new)
        factory=FACTORY_START_VA-VA_MINUS_OFFSET
        self.assertEqual(original[factory:factory+FACTORY_END_VA-FACTORY_START_VA],
                         result[factory:factory+FACTORY_END_VA-FACTORY_START_VA])
        allowed={i for at in EXPECTED for i in range(at,at+4)}
        for at,(x,y) in enumerate(zip(original,result)):
            if x!=y:self.assertIn(at,allowed)
    @unittest.skipUnless(BASE.exists(),"private baseline ELF absent")
    def test_checksum_drift_fails_closed(self):
        original=bytearray(BASE.read_bytes())
        original[0x155f08]^=1
        with self.assertRaisesRegex(ValueError,"checksum mismatch"):
            apply(bytes(original))
if __name__=="__main__":
    unittest.main()
