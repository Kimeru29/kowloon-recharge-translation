from __future__ import annotations

import struct
import unittest

from tools.executable_text import RelocatedText, install_executable_text


def make_translation_segment_fixture(*, pointer_offsets: tuple[int, ...]) -> bytes:
    # Minimal synthetic image carrying the exact dormant-PT_LOAD/heap preimages
    # required by tools.elf_translation_segment. No copyrighted executable bytes.
    raw = bytearray(0x8030C0)
    raw[:4] = b"\x7fELF"
    struct.pack_into(
        "<IIIIIIII",
        raw,
        0x54,
        1,
        0x00802F80,
        0x00902F00,
        0x00902F00,
        0,
        0,
        6,
        0x10,
    )
    struct.pack_into("<I", raw, 0x1A0, 0x3C030090)
    struct.pack_into("<I", raw, 0x1A8, 0x24632F00)
    struct.pack_into("<I", raw, 0x250, 0x3C040090)
    struct.pack_into("<I", raw, 0x258, 0x24842F00)
    struct.pack_into("<I", raw, 0x650014, 0x00902F00)
    struct.pack_into("<I", raw, 0x8030BC, 0x00902F00)
    for pointer_offset in pointer_offsets:
        struct.pack_into("<I", raw, pointer_offset, 0xDEADBEEF)
    return bytes(raw)


def read_ptr(raw: bytes, offset: int) -> int:
    return struct.unpack_from("<I", raw, offset)[0]


class ExecutableTextTests(unittest.TestCase):
    def test_packs_once_and_repoints_all_aliases(self) -> None:
        fake_elf = make_translation_segment_fixture(pointer_offsets=(0x300, 0x304, 0x308))
        entries = (
            RelocatedText("a", b"AA\0", (0x300, 0x304)),
            RelocatedText("b", b"BBBB\0", (0x308,)),
        )

        result = install_executable_text(fake_elf, entries)

        self.assertEqual(result.target_vas["a"], read_ptr(result.raw, 0x300))
        self.assertEqual(result.target_vas["a"], read_ptr(result.raw, 0x304))
        self.assertEqual(result.target_vas["b"], read_ptr(result.raw, 0x308))
        self.assertNotEqual(result.target_vas["a"], result.target_vas["b"])
        self.assertEqual(0x00902F00, result.target_vas["a"])
        self.assertEqual(0x00902F04, result.target_vas["b"])
        self.assertEqual(b"AA\0\0BBBB\0", result.raw[result.info.file_offset:result.info.file_offset + 9])
        self.assertEqual(9, result.info.payload_size)

    def test_input_sequence_is_the_stable_payload_order(self) -> None:
        fake_elf = make_translation_segment_fixture(pointer_offsets=())
        entries = (
            RelocatedText("z", b"Z\0", ()),
            RelocatedText("a", b"A\0", ()),
        )

        result = install_executable_text(fake_elf, entries)

        self.assertLess(result.target_vas["z"], result.target_vas["a"])
        self.assertEqual(b"Z\0A\0", result.raw[result.info.file_offset:result.info.file_offset + 4])

    def test_rejects_duplicate_keys_and_pointer_ownership_conflicts(self) -> None:
        fake_elf = make_translation_segment_fixture(pointer_offsets=(0x300,))
        with self.assertRaisesRegex(ValueError, "duplicate key"):
            install_executable_text(
                fake_elf,
                (RelocatedText("a", b"A\0", ()), RelocatedText("a", b"B\0", ())),
            )

        with self.assertRaisesRegex(ValueError, "pointer ownership conflict"):
            install_executable_text(
                fake_elf,
                (RelocatedText("a", b"A\0", (0x300,)), RelocatedText("b", b"B\0", (0x300,))),
            )

    def test_rejects_pointer_outside_input_and_payload_larger_than_reserve(self) -> None:
        fake_elf = make_translation_segment_fixture(pointer_offsets=())
        with self.assertRaisesRegex(ValueError, "pointer offset"):
            install_executable_text(fake_elf, (RelocatedText("a", b"A\0", (len(fake_elf) - 2,)),))

        with self.assertRaisesRegex(ValueError, "reserve"):
            install_executable_text(
                fake_elf,
                (RelocatedText("huge", b"X" * 0x10001, ()),),
                reserve_size=0x10000,
            )


if __name__ == "__main__":
    unittest.main()
