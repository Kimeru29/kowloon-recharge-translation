import mmap
from pathlib import Path
import struct
import tempfile
import unittest

from tests.test_build_translation_iso import both_u32, dir_record, make_nested_iso, put_dir
from tools.build_translation_iso import build_translation_iso
from tools.iso9660_patch import find_record, index_iso
from tools.r67o_iso import audit_candidate, validate_native_delta
from tools.translation_overlay import collect_overlay


class CumulativeNativeISOAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source.iso'
        self.target = self.root / 'target.iso'
        make_nested_iso(self.source)
        folder = self.root / 'overlay/DG'
        folder.mkdir(parents=True)
        (folder / 'A.MTX').write_bytes(b'E' * 3000)
        self.overlay = collect_overlay([('exact-source-owned-script', folder.parent)])

    def test_independent_disc_audit_accepts_custom_executable_and_resource_growth(self):
        raw = self.source.read_bytes()
        _, records = index_iso(raw)
        exe = find_record(records, 'SLPM_665.11')
        native = raw[exe.extent * 2048:exe.extent * 2048 + exe.size] + b'NATIVE' * 400
        path = self.root / 'native.elf'
        path.write_bytes(native)
        build_translation_iso(self.source, self.target, self.overlay, path)
        report = audit_candidate(self.source, self.target, self.overlay, native)
        self.assertEqual(report['unexplained_bytes'], 0)
        self.assertEqual(report['complete_disc_bytes_compared'], len(raw))
        self.assertTrue(report['elf_relocated'])

    def test_rejects_unowned_code_payload_padding_and_outer_changes(self):
        build_translation_iso(self.source, self.target, self.overlay)
        original = self.target.read_bytes()
        _, records = index_iso(original)
        exe = find_record(records, 'SLPM_665.11')
        for location in (0, exe.extent * 2048 + 40, exe.extent * 2048 + exe.size + 2):
            with self.subTest(location=location):
                changed = bytearray(original)
                changed[location] ^= 1
                self.target.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, 'Unexpected'):
                    audit_candidate(self.source, self.target, self.overlay)

    def test_audits_tail_extension_after_growth_and_rejects_its_padding_mutation(self):
        raw = bytearray(self.source.read_bytes()[:72 * 2048])
        native = bytes(raw[22 * 2048:22 * 2048 + 128]) + b'N' * 2872
        raw[68 * 2048:69 * 2048] = raw[22 * 2048:23 * 2048]
        raw[22 * 2048:23 * 2048] = bytes(2048)
        raw[16 * 2048 + 80:16 * 2048 + 88] = both_u32(72)
        put_dir(raw, 0, 20, [dir_record(b'SLPM_665.11;1', 68, 128),
                            dir_record(b'DATA.CVM;1', 24, 43 * 2048),
                            dir_record(b'SYSTEM.CNF;1', 67, 64)])
        self.source.write_bytes(raw)
        elf = self.root / 'tail.elf'
        elf.write_bytes(native)
        build_translation_iso(self.source, self.target, self.overlay, elf)
        report = audit_candidate(self.source, self.target, self.overlay, native)
        self.assertTrue(report['elf_extended_in_place'])
        self.assertFalse(report['elf_relocated'])
        self.assertEqual(report['elf_output_extent'], 70)
        changed = bytearray(self.target.read_bytes())
        changed[70 * 2048 + len(native)] ^= 1
        self.target.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            audit_candidate(self.source, self.target, self.overlay, native)


class NativeOwnerBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / 'local/r67n-release/67.15n-official-script-diagnostic.elf'
        if not path.exists():
            raise unittest.SkipTest('Owned pinned n ELF unavailable')
        cls.source = path.read_bytes()

    def extended(self):
        raw = bytearray(self.source + b'\0' * 16)
        offset, base = struct.unpack_from('<II', self.source, 0x58)
        struct.pack_into('<I', raw, 0x64, len(raw) - offset)
        destination = base + len(self.source) - offset
        struct.pack_into('<I', raw, 0x22c388 - 0xfff80, (3 << 26) | (destination >> 2))
        return raw

    def test_only_owned_jals_and_load_size_can_change(self):
        report = validate_native_delta(self.source, bytes(self.extended()))
        self.assertEqual(report['changed_hook_addresses'], [0x22c388])
        self.assertEqual(report['appended_bytes'], 16)

    def test_rejects_original_code_data_header_or_non_call_mutations(self):
        for offset in (0x1000, 0x4d7ed0, 0x5c):
            with self.subTest(offset=offset):
                raw = self.extended()
                raw[offset] ^= 1
                with self.assertRaises(ValueError):
                    validate_native_delta(self.source, bytes(raw))
        raw = self.extended()
        struct.pack_into('<I', raw, 0x22c388 - 0xfff80, 0)
        with self.assertRaisesRegex(ValueError, 'JAL'):
            validate_native_delta(self.source, bytes(raw))

    def test_rejects_call_outside_owned_append_and_heap_reserve_expansion(self):
        raw = self.extended()
        struct.pack_into('<I', raw, 0x22c388 - 0xfff80, (3 << 26) | (0x200000 >> 2))
        with self.assertRaisesRegex(ValueError, 'append'):
            validate_native_delta(self.source, bytes(raw))
        raw = self.extended()
        struct.pack_into('<I', raw, 0x68, 0x200000)
        with self.assertRaises(ValueError):
            validate_native_delta(self.source, bytes(raw))


if __name__ == '__main__':
    unittest.main()
