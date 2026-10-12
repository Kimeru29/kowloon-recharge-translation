import unittest
from pathlib import Path
from tools.iso9660_patch import IsoRecord
from tools.r67_14y_release import check_growth, preserve_installed_metadata, verify_save_identity


class ReleaseSafetyTests(unittest.TestCase):
    def test_identity_guard_rejects_descriptor_mutation(self):
        p = Path(__file__).resolve().parents[1]/'local/r67-14t-lion-and-tablets.elf'
        if not p.exists():
            self.skipTest('local t ELF missing')
        b = bytearray(p.read_bytes())
        self.assertEqual(verify_save_identity(b)['native_save_descriptors'],15)
        b[0x406771] ^= 1
        with self.assertRaisesRegex(ValueError,'namespace'):
            verify_save_identity(b)

    def test_preserves_installed_metadata_but_rejects_collisions(self):
        result, offsets = preserve_installed_metadata(b'abc',b'aBc',b'abcDEF')
        self.assertEqual(result,b'aBcDEF')
        self.assertEqual(offsets,[1])
        with self.assertRaisesRegex(ValueError,'collides'):
            preserve_installed_metadata(b'abc',b'aBc',b'aXcDEF')

    def test_growth_requires_unallocated_zero_sectors(self):
        e = IsoRecord('SLPM_665.11',1,2048,0,0)
        data = bytearray(8192)
        check_growth(data,e,(e,),3000)
        occupied = IsoRecord('OTHER',2,2048,0,0)
        with self.assertRaisesRegex(ValueError,'overlaps'):
            check_growth(data,e,(e,occupied),3000)
        data[4096] = 1
        with self.assertRaisesRegex(ValueError,'nonzero'):
            check_growth(data,e,(e,),3000)

    def test_growth_cannot_escape_volume_or_shrink(self):
        e = IsoRecord('SLPM_665.11',1,2048,0,0)
        for length in (1000,7000):
            with self.assertRaisesRegex(ValueError,'outside'):
                check_growth(bytes(8192),e,(e,),length)


if __name__ == '__main__':
    unittest.main()
