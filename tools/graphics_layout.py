from __future__ import annotations

from dataclasses import dataclass


Rect = tuple[int, int, int, int]
Size = tuple[int, int]


@dataclass(frozen=True)
class RegionTransfer:
    """Copy one source atlas rectangle to a translated destination position.

    ``offset`` is added to source coordinates, so a source pixel at ``(x, y)``
    lands at ``(x + dx, y + dy)``.  This makes renderer discoveries reusable as
    data rather than hard-coded image edits.
    """

    source_box: Rect
    offset: tuple[int, int]


def _validate_rgba(rgba: bytes, size: Size, *, label: str) -> None:
    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"{label} size must be positive, got {size}")
    expected = width * height * 4
    if len(rgba) != expected:
        raise ValueError(f"{label} RGBA length {len(rgba)} != expected {expected}")


def _validate_transfer(transfer: RegionTransfer, source_size: Size, target_size: Size) -> None:
    source_width, source_height = source_size
    target_width, target_height = target_size
    x0, y0, x1, y1 = transfer.source_box
    if not (0 <= x0 < x1 <= source_width and 0 <= y0 < y1 <= source_height):
        raise ValueError(f"source box is outside source image: {transfer.source_box}")
    dx, dy = transfer.offset
    if not (
        0 <= x0 + dx < x1 + dx <= target_width
        and 0 <= y0 + dy < y1 + dy <= target_height
    ):
        raise ValueError(
            f"destination box is outside target image: "
            f"{(x0 + dx, y0 + dy, x1 + dx, y1 + dy)}"
        )


def _inside(rect: Rect, x: int, y: int) -> bool:
    x0, y0, x1, y1 = rect
    return x0 <= x < x1 and y0 <= y < y1


def repack_rgba_regions(
    source_rgba: bytes,
    source_size: Size,
    target_size: Size,
    transfers: tuple[RegionTransfer, ...],
) -> bytes:
    """Build a transparent atlas from declared source-region transfers.

    Transparent source pixels do not erase prior transfers.  If two opaque
    transferred pixels overlap, the later transfer wins deterministically.
    """

    _validate_rgba(source_rgba, source_size, label="source")
    for transfer in transfers:
        _validate_transfer(transfer, source_size, target_size)

    source_width, _ = source_size
    target_width, target_height = target_size
    out = bytearray(target_width * target_height * 4)

    for transfer in transfers:
        x0, y0, x1, y1 = transfer.source_box
        dx, dy = transfer.offset
        for sy in range(y0, y1):
            for sx in range(x0, x1):
                source_offset = (sy * source_width + sx) * 4
                if source_rgba[source_offset + 3] == 0:
                    continue
                tx, ty = sx + dx, sy + dy
                target_offset = (ty * target_width + tx) * 4
                out[target_offset:target_offset + 4] = source_rgba[source_offset:source_offset + 4]

    return bytes(out)


def validate_alpha_repack(
    source_rgba: bytes,
    target_rgba: bytes,
    source_size: Size,
    target_size: Size,
    transfers: tuple[RegionTransfer, ...],
    *,
    ignore_rects: tuple[Rect, ...] = (),
    margin: int = 0,
    alpha_threshold: int = 32,
    min_dice: float = 0.8,
) -> tuple[float, ...]:
    """Prove that target atlas regions derive from the declared source layout.

    Each transfer is compared using the Dice overlap of alpha masks.  Target
    pixels inside ``ignore_rects`` are excluded so a known flattened overlay can
    be tolerated without weakening the rest of the layout proof.
    """

    _validate_rgba(source_rgba, source_size, label="source")
    _validate_rgba(target_rgba, target_size, label="target")
    if margin < 0:
        raise ValueError("margin cannot be negative")
    if not 0 <= alpha_threshold <= 255:
        raise ValueError("alpha threshold must be in range 0..255")
    if not 0.0 <= min_dice <= 1.0:
        raise ValueError("minimum Dice score must be in range 0..1")

    source_width, _ = source_size
    target_width, target_height = target_size
    scores: list[float] = []

    for index, transfer in enumerate(transfers):
        _validate_transfer(transfer, source_size, target_size)
        x0, y0, x1, y1 = transfer.source_box
        dx, dy = transfer.offset
        dest_x0 = max(0, x0 + dx - margin)
        dest_y0 = max(0, y0 + dy - margin)
        dest_x1 = min(target_width, x1 + dx + margin)
        dest_y1 = min(target_height, y1 + dy + margin)

        predicted_count = 0
        target_count = 0
        intersection = 0
        for ty in range(dest_y0, dest_y1):
            for tx in range(dest_x0, dest_x1):
                if any(_inside(rect, tx, ty) for rect in ignore_rects):
                    continue
                sx, sy = tx - dx, ty - dy
                predicted = False
                if x0 <= sx < x1 and y0 <= sy < y1:
                    source_offset = (sy * source_width + sx) * 4
                    predicted = source_rgba[source_offset + 3] > alpha_threshold
                target_offset = (ty * target_width + tx) * 4
                actual = target_rgba[target_offset + 3] > alpha_threshold
                predicted_count += int(predicted)
                target_count += int(actual)
                intersection += int(predicted and actual)

        denominator = predicted_count + target_count
        score = 1.0 if denominator == 0 else (2.0 * intersection / denominator)
        scores.append(score)
        if score < min_dice:
            raise ValueError(
                f"alpha-layout proof failed for transfer {index}: "
                f"Dice {score:.4f} < required {min_dice:.4f}"
            )

    return tuple(scores)
