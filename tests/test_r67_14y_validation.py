import copy
import struct
import unittest
from tools.memory_card_ui import encode_memory_card_english
from tools.r67_14y_validation import scoped_startup,verify_message


class ScopedStartupTests(unittest.TestCase):
    def fixture(self,text='\nSaving...\nDo not remove/insert\nmemory card (PS2) or\nturn off the power.'):
        b = bytearray(0x407500)
        value = encode_memory_card_english(text)+b'\0'
        b[0x100:0x100+len(value)] = value
        struct.pack_into('<I',b,0x407460,0x100+0xFFF80)
        return bytes(b)

    def test_explicit_exception_retains_raw_failure(self):
        raw = dict(checks_total=2,checks_passed=1,checks=[
            dict(name='serial',ok=True,detail=None),
            dict(name='memory_card_8',ok=False,detail='legacy bytes differ')])
        original = copy.deepcopy(raw)
        b = self.fixture()
        scoped = scoped_startup(raw,b,b)
        self.assertEqual(raw,original)
        self.assertEqual(scoped['raw_checks_passed'],1)
        self.assertEqual(scoped['checks_passed'],2)
        self.assertEqual(len(scoped['explicit_legacy_wording_exceptions']),1)

    def test_unrelated_failures_are_never_masked(self):
        raw = dict(checks_total=1,checks_passed=0,checks=[dict(name='serial',ok=False,detail='bad')])
        with self.assertRaisesRegex(ValueError,'unexpected startup'):
            scoped_startup(raw,self.fixture(),self.fixture())

    def test_save_payload_drift_and_overflow_rejected(self):
        expected = self.fixture()
        with self.assertRaisesRegex(ValueError,'differs'):
            verify_message(self.fixture('Saving changed'),expected,8)
        for s in ('A'*22,'\n'*6+'Saving'):
            b = self.fixture(s)
            with self.assertRaisesRegex(ValueError,'layout'):
                verify_message(b,b,8)


if __name__ == '__main__':
    unittest.main()
