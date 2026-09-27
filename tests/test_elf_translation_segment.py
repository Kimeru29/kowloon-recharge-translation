from __future__ import annotations

import struct
import unittest
from pathlib import Path

from tests.local_fixtures import require_local_fixture
from tools.elf_translation_segment import install_translation_segment

ELF = require_local_fixture(Path(__file__).parents[1] / "fixtures" / "elf" / "SLPM_665.11")
RAW = ELF.read_bytes()


class ElfTranslationSegmentTests(unittest.TestCase):
    def test_installs_payload_in_zero_sized_second_load_and_moves_only_heap_start(self) -> None:
        payload = b"translated text\x00more\x00"
        result, info = install_translation_segment(RAW, payload, reserve_size=0x100000)

        self.assertEqual(0x902F00, info.segment_vaddr)
        self.assertEqual(0xA02F00, info.heap_vaddr)
        self.assertEqual(payload, result[info.file_offset:info.file_offset + len(payload)])
        self.assertEqual(0, info.file_offset & 0xF)

        # Second PT_LOAD now maps the appended translation bytes and reserves
        # the whole 1 MiB virtual window before the heap.
        ph = struct.unpack_from("<IIIIIIII", result, 0x54)
        self.assertEqual((1, info.file_offset, 0x902F00, 0x902F00), ph[:4])
        self.assertEqual(len(payload), ph[4])
        self.assertEqual(0x100000, ph[5])
        self.assertEqual(6, ph[6])
        self.assertEqual(0x10, ph[7])

        # BSS zero-fill must still stop at 0x902F00 or it would erase the new
        # segment.  The heap syscall alone moves to 0xA02F00.
        self.assertEqual(RAW[0x1A0:0x1AC], result[0x1A0:0x1AC])
        self.assertEqual(0x3C0400A0, struct.unpack_from("<I", result, 0x250)[0])
        self.assertEqual(0x24842F00, struct.unpack_from("<I", result, 0x258)[0])

        # Both heap metadata and the libkernel sbrk break must start after the
        # reserved translation window.  Leaving the latter at 0x902F00 lets the
        # first runtime allocation overwrite translated strings in-place.
        self.assertEqual(0xA02F00, struct.unpack_from("<I", result, 0x8030BC)[0])
        self.assertEqual(0xA02F00, struct.unpack_from("<I", result, 0x650014)[0])

    def test_fail_closes_on_unexpected_program_header_or_heap_instruction(self) -> None:
        tampered = bytearray(RAW)
        tampered[0x54 + 16] = 1  # second PT_LOAD was required to have filesz == 0
        with self.assertRaisesRegex(ValueError, "second PT_LOAD"):
            install_translation_segment(bytes(tampered), b"x\0")

        tampered = bytearray(RAW)
        tampered[0x250] ^= 1
        with self.assertRaisesRegex(ValueError, "heap-start instruction"):
            install_translation_segment(bytes(tampered), b"x\0")

        tampered = bytearray(RAW)
        tampered[0x650014] ^= 1
        with self.assertRaisesRegex(ValueError, "libkernel heap break"):
            install_translation_segment(bytes(tampered), b"x\0")

    def test_rejects_payload_larger_than_reserved_ram_window(self) -> None:
        with self.assertRaisesRegex(ValueError, "reserve"):
            install_translation_segment(RAW, b"x" * 0x101, reserve_size=0x100)


if __name__ == "__main__":
    unittest.main()
