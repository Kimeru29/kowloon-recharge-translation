from __future__ import annotations

import unittest

from tools.graphics_layout import RegionTransfer, repack_rgba_regions, validate_alpha_repack


def _rgba(width: int, height: int, opaque: set[tuple[int, int]]) -> bytes:
    out = bytearray(width * height * 4)
    for x, y in opaque:
        off = (y * width + x) * 4
        out[off:off + 4] = bytes((10, 20, 30, 255))
    return bytes(out)


class GraphicsLayoutTests(unittest.TestCase):
    def test_repack_transfers_only_declared_regions_to_transparent_canvas(self) -> None:
        source = _rgba(8, 6, {(2, 1), (3, 1), (6, 4)})
        transfers = (
            RegionTransfer((2, 1, 4, 3), (1, 2)),
            RegionTransfer((6, 4, 8, 6), (-4, -3)),
        )
        out = repack_rgba_regions(source, (8, 6), (8, 6), transfers)

        alpha = out[3::4]
        opaque = {(i % 8, i // 8) for i, value in enumerate(alpha) if value}
        self.assertEqual({(3, 3), (4, 3), (2, 1)}, opaque)

    def test_alpha_validator_accepts_layout_and_ignores_flattened_overlay(self) -> None:
        source = _rgba(8, 8, {(2, y) for y in range(1, 7)} | {(5, y) for y in range(1, 7)})
        transfers = (
            RegionTransfer((2, 1, 3, 7), (1, 0)),
            RegionTransfer((5, 1, 6, 7), (1, 0)),
        )
        target_opaque = {(3, y) for y in range(1, 7)} | {(6, y) for y in range(1, 7)}
        target_opaque |= {(x, 4) for x in range(8)}  # flattened overlay not present in source
        target = _rgba(8, 8, target_opaque)

        scores = validate_alpha_repack(
            source,
            target,
            (8, 8),
            (8, 8),
            transfers,
            ignore_rects=((0, 4, 8, 5),),
            margin=0,
            min_dice=0.95,
        )
        self.assertEqual((1.0, 1.0), scores)

        with self.assertRaisesRegex(ValueError, "alpha-layout proof"):
            validate_alpha_repack(
                source,
                bytes(len(target)),
                (8, 8),
                (8, 8),
                transfers,
                ignore_rects=((0, 4, 8, 5),),
                margin=0,
                min_dice=0.95,
            )


if __name__ == "__main__":
    unittest.main()
