import unittest

from tools.r67n_ksf_structural import transfer
from tools.r67n_ksf import native_slots


def rec(labels=(), opcode=2):
    header = bytes([opcode]) + bytes(0x90b)
    return header + b''.join(b'\1'+s.encode('cp932').ljust(30,b'\0') for s in labels) + bytes(4-len(labels))


def scene(*records):
    return len(records).to_bytes(2,'little') + b''.join(records)


class StructuralChoiceTests(unittest.TestCase):
    def setUp(self):
        self.ps2 = scene(rec(),rec(['見る','話す']),rec())
        self.ps4 = scene(rec(['別']),rec(['見る','話す']),rec())
        self.keys = list(native_slots(self.ps4))[1:]
        self.dc = {'keys':self.keys, 'values':['Look  around','a'*30]}

    def test_shifted_offsets_same_ordinal_and_record_transfer_only_safe_label(self):
        out,rows=transfer(self.ps2,self.ps4,self.dc,self.ps2)
        key=list(native_slots(self.ps2))[0]
        self.assertNotEqual(key,self.keys[0]); self.assertEqual(out[key:key+30],b'Look around'.ljust(30,b'\0'))
        self.assertEqual(out[:key]+out[key+30:],self.ps2[:key]+self.ps2[key+30:])
        self.assertEqual(rows[1]['status'],'overflow')

    def test_changed_header_or_choice_rejects_every_label_in_the_record(self):
        for record in (rec(['見る','話す'],0),rec(['話す','見る'])):
            ps2=scene(rec(),record,rec())
            out,rows=transfer(ps2,self.ps4,self.dc,ps2)
            self.assertEqual(out,ps2);self.assertTrue(all(r['status']=='record mismatch' for r in rows))

    def test_reordered_record_cannot_be_matched_by_text(self):
        ps2=scene(rec(['見る','話す']),rec(),rec())
        out,rows=transfer(ps2,self.ps4,self.dc,ps2)
        self.assertEqual(out,ps2);self.assertTrue(all(r['status']=='record mismatch' for r in rows))

    def test_duplicate_or_nonlabel_key_and_installed_drift_rejected(self):
        for keys in ([self.keys[0]]*2,[self.keys[0]+1,self.keys[1]]):
            with self.assertRaises(ValueError):transfer(self.ps2,self.ps4,dict(keys=keys,values=['x','y']),self.ps2)
        with self.assertRaisesRegex(ValueError,'installed'):
            transfer(self.ps2,self.ps4,self.dc,self.ps2[:-1]+b'z')
