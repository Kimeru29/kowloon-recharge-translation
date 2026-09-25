from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HantLayoutProfile:
    max_cells: int
    glyph_advance: float
    line_spacing: float
    controller_gap_cells: int
    max_rows: int = 16


# Static renderer trace for the H.A.N.T. text page:
# - row staging copies at most 0x40 bytes; PS2 English is two bytes/glyph
#   (32-cell hard storage ceiling),
# - style-0 font record VA 0x005D77D0 is 16x18, so ordinary glyphs advance
#   16 logical pixels at the 1.0 scale used by this page,
# - text rows begin at X=85 in a 512-wide logical canvas,
# - row Y is 131 + 21*n.
# The visual width is therefore the tighter constraint:
# floor((512 - 85) / 16) == 26 cells.
HANT_LAYOUT_PROFILE = HantLayoutProfile(
    max_cells=26,
    glyph_advance=16.0,
    line_spacing=21.0,
    controller_gap_cells=5,
)


def _validated_spans(text: str, spans: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    ordered = tuple(sorted(spans))
    previous_end = 0
    for index, (start, end) in enumerate(ordered):
        if start < 0 or end < start or end > len(text):
            raise ValueError(f"reserved span {index} is outside text")
        if index and start < previous_end:
            raise ValueError("reserved spans overlap")
        previous_end = end
    return ordered


def measured_hant_cells(
    text: str,
    reserved_spans: tuple[tuple[int, int], ...] = (),
    controller_gap_cells: int = 5,
) -> int:
    """Measure logical H.A.N.T. cells while preserving controller-icon gaps.

    A reserved source span occupies the renderer's controller placeholder width,
    regardless of how many source characters are used to spell/pad that span.
    All other printable characters consume one logical fullwidth cell.
    """

    if controller_gap_cells < 0:
        raise ValueError("controller_gap_cells must be non-negative")
    spans = _validated_spans(text, reserved_spans)
    width = len(text)
    for start, end in spans:
        width -= end - start
        width += controller_gap_cells
    return width


def _measure_range(
    text: str,
    start: int,
    end: int,
    spans: tuple[tuple[int, int], ...],
    controller_gap_cells: int,
) -> int:
    width = end - start
    for span_start, span_end in spans:
        if span_end <= start or span_start >= end:
            continue
        if span_start < start or span_end > end:
            # Wrapping is never allowed to bisect a protected controller span.
            raise ValueError("wrap boundary intersects reserved span")
        width -= span_end - span_start
        width += controller_gap_cells
    return width


def wrap_hant_text(
    text: str,
    max_cells: int,
    reserved_spans: tuple[tuple[int, int], ...] = (),
) -> tuple[str, ...]:
    """Greedily wrap at ordinary spaces without splitting protected spans.

    The wording and punctuation are preserved exactly. Ordinary separator spaces
    become line breaks as needed; spaces inside reserved controller spans are
    never considered break points.
    """

    if max_cells <= 0:
        raise ValueError("max_cells must be positive")
    if not text:
        return ("",)

    spans = _validated_spans(text, reserved_spans)
    protected = bytearray(len(text))
    for span_start, span_end in spans:
        protected[span_start:span_end] = b"\x01" * (span_end - span_start)

    def is_breakable_space(index: int) -> bool:
        return text[index] == " " and not protected[index]

    lines: list[str] = []
    start = 0
    length = len(text)
    gap_cells = HANT_LAYOUT_PROFILE.controller_gap_cells

    while start < length:
        while start < length and is_breakable_space(start):
            start += 1
        if start >= length:
            break

        if _measure_range(text, start, length, spans, gap_cells) <= max_cells:
            lines.append(text[start:length])
            break

        best_break: int | None = None
        index = start
        while index < length:
            if not is_breakable_space(index):
                index += 1
                continue

            run_start = index
            while index < length and is_breakable_space(index):
                index += 1

            if _measure_range(text, start, run_start, spans, gap_cells) <= max_cells:
                best_break = run_start
                continue
            break

        if best_break is None:
            token_end = start
            while token_end < length and not is_breakable_space(token_end):
                token_end += 1
            token = text[start:token_end]
            if _measure_range(text, start, token_end, spans, gap_cells) > max_cells:
                raise ValueError(f"H.A.N.T token cannot fit within {max_cells} cells: {token!r}")
            # This case is only reachable for malformed spacing where a valid
            # token fits but no separator was available before an overflowing
            # protected range. Fail rather than silently alter the source.
            raise ValueError("H.A.N.T text cannot fit at a legal word boundary")

        lines.append(text[start:best_break])
        start = best_break

    if not lines:
        return ("",)
    return tuple(lines)
