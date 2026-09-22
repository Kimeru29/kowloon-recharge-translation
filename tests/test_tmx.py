from __future__ import annotations

import struct
import unittest

from tools.tmx import (
    decode_tmx_rgba,
    find_tmx_entry,
    parse_standalone_tmx,
    replace_standalone_tmx_indexed,
    replace_tmx_indexed,
)


def make_container(*, psm: int = 0x13, width: int = 4, height: int = 2) -> bytes:
    name = b"GRP999/GP999_00.TMX\x00"
    prefix = bytearray(0x100)
    prefix[: len(name)] = name

    palette_entries = 256 if psm == 0x13 else 16
    palette_bytes = palette_entries * 4
    pixel_bytes = width * height if psm == 0x13 else width * height // 2
    chunk_size = 0x40 + palette_bytes + pixel_bytes
    tmx = bytearray(chunk_size)
    struct.pack_into("<II", tmx, 0, 2, chunk_size)
    tmx[8:12] = b"TMX0"
    tmx[16] = 1
    tmx[17] = 0
    struct.pack_into("<HH", tmx, 18, width, height)
    tmx[22] = psm

    payload = 0x40
    for i in range(palette_entries):
        # PS2 raw alpha 0x80 -> decoded 255.
        struct.pack_into("BBBB", tmx, payload + i * 4, i, 0, 0, 0x80)
    if psm == 0x13:
        tmx[payload + palette_bytes:payload + palette_bytes + pixel_bytes] = bytes(range(width * height))
    else:
        vals = list(range(width * height))
        packed = bytes((vals[i] & 0xF) | ((vals[i + 1] & 0xF) << 4) for i in range(0, len(vals), 2))
        tmx[payload + palette_bytes:payload + palette_bytes + pixel_bytes] = packed
    return bytes(prefix + tmx + b"TAIL")


class TmxTests(unittest.TestCase):
    def test_finds_named_entry_and_decodes_8bit(self) -> None:
        blob = make_container()
        entry = find_tmx_entry(blob, "GRP999/GP999_00.TMX")
        self.assertEqual((4, 2, 0x13), (entry.width, entry.height, entry.image_psm))
        rgba = decode_tmx_rgba(blob, entry)
        self.assertEqual(4 * 2 * 4, len(rgba))
        self.assertEqual((0, 0, 0, 255), tuple(rgba[:4]))

    def test_replaces_8bit_palette_and_indices_without_changing_container_size(self) -> None:
        blob = make_container()
        palette = [(0, 0, 0, 0)] * 256
        palette[1] = (10, 20, 30, 255)
        indices = bytes([1] * 8)
        out = replace_tmx_indexed(blob, "GRP999/GP999_00.TMX", palette, indices)
        self.assertEqual(len(blob), len(out))
        entry = find_tmx_entry(out, "GRP999/GP999_00.TMX")
        rgba = decode_tmx_rgba(out, entry)
        self.assertEqual([(10, 20, 30, 255)] * 8, [tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)])
        self.assertEqual(b"TAIL", out[-4:])

    def test_replaces_4bit_palette_and_indices(self) -> None:
        blob = make_container(psm=0x14, width=4, height=2)
        palette = [(0, 0, 0, 0)] * 16
        palette[3] = (1, 2, 3, 255)
        out = replace_tmx_indexed(blob, "GRP999/GP999_00.TMX", palette, bytes([3] * 8))
        entry = find_tmx_entry(out, "GRP999/GP999_00.TMX")
        rgba = decode_tmx_rgba(out, entry)
        self.assertEqual([(1, 2, 3, 255)] * 8, [tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)])


    def test_parses_and_replaces_standalone_indexed_tmx(self) -> None:
        container = make_container(width=4, height=2)
        # Synthetic named container stores the standalone chunk at 0x100.
        standalone = container[0x100:-4]
        entry = parse_standalone_tmx(standalone, "TR028.TMX")
        self.assertEqual((0, len(standalone), 4, 2, 0x13), (
            entry.base_offset, entry.chunk_size, entry.width, entry.height, entry.image_psm
        ))
        palette = [(0, 0, 0, 0)] * 256
        palette[7] = (200, 30, 40, 255)
        out = replace_standalone_tmx_indexed(standalone, palette, bytes([7] * 8), name="TR028.TMX")
        self.assertEqual(len(standalone), len(out))
        rewritten = parse_standalone_tmx(out, "TR028.TMX")
        rgba = decode_tmx_rgba(out, rewritten)
        self.assertEqual([(200, 30, 40, 255)] * 8, [tuple(rgba[i:i+4]) for i in range(0, len(rgba), 4)])

    def test_rejects_standalone_tmx_with_trailing_or_wrong_chunk_size(self) -> None:
        standalone = make_container(width=4, height=2)[0x100:-4]
        with self.assertRaisesRegex(ValueError, "exactly one TMX chunk"):
            parse_standalone_tmx(standalone + b"tail", "TR000.TMX")

    def test_rejects_wrong_palette_or_index_count(self) -> None:
        blob = make_container()
        with self.assertRaises(ValueError):
            replace_tmx_indexed(blob, "GRP999/GP999_00.TMX", [(0, 0, 0, 0)] * 16, bytes([0] * 8))
        with self.assertRaises(ValueError):
            replace_tmx_indexed(blob, "GRP999/GP999_00.TMX", [(0, 0, 0, 0)] * 256, bytes([0] * 7))


if __name__ == "__main__":
    unittest.main()
