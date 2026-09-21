from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
from typing import Any

from tools.localization import DcGroup, DcLocalization
from tools.mtx import MtxFile, MtxReplacement


class StructuralImportError(ValueError):
    pass


@dataclass(frozen=True)
class StructuralSpan:
    first_group: int
    last_group: int
    ps4_start: int
    ps4_end: int
    ps2_start: int
    ps2_end: int
    mode: str
    similarity: float


@dataclass(frozen=True)
class StructuralImportResult:
    data: bytes
    english_entries: int
    groups_total: int
    direct_groups: int
    semantic_groups: int
    spans: tuple[StructuralSpan, ...]


def _matching_blocks(ps4_raw: bytes, ps2_raw: bytes):
    use_autojunk = max(len(ps4_raw), len(ps2_raw)) > 4096
    return SequenceMatcher(None, ps4_raw, ps2_raw, autojunk=use_autojunk).get_matching_blocks()


def _map_offset(blocks, offset: int) -> int | None:
    """Map an offset through an exact SequenceMatcher block."""

    candidates: list[tuple[int, int]] = []
    for block in blocks:
        if block.size <= 0:
            continue
        if block.a <= offset <= block.a + block.size:
            candidates.append((block.size, block.b + (offset - block.a)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    mapped = {item[1] for item in candidates if item[0] == candidates[0][0]}
    if len(mapped) != 1:
        return None
    return next(iter(mapped))


def _ascii_left_signature(raw: bytes, offset: int, limit: int = 16) -> bytes:
    start = offset
    while start > 0 and offset - start < limit and raw[start - 1] < 0x80:
        start -= 1
    return raw[start:offset]


def _ascii_right_signature(raw: bytes, offset: int, limit: int = 16) -> bytes:
    end = offset
    while end < len(raw) and end - offset < limit and raw[end] < 0x80:
        end += 1
    return raw[offset:end]


def _normalize_control_context(value: bytes) -> bytes:
    # NUL bytes are alignment padding between MTX control/text regions and are
    # known to differ between otherwise equivalent PS2/PS4 scripts.
    return value.replace(b"\x00", b"")


def _right_control_delimiter(value: bytes) -> bytes:
    value = _normalize_control_context(value)
    for marker in (b"wc", b"}w", b"r", b"ds", b"sbr", b"_"):
        if value.startswith(marker):
            return marker
    return value


def _boundary_context_matches(ps4_raw: bytes, ps2_raw: bytes, ps4_offset: int, ps2_offset: int) -> bool:
    left4 = _normalize_control_context(_ascii_left_signature(ps4_raw, ps4_offset))
    left2 = _normalize_control_context(_ascii_left_signature(ps2_raw, ps2_offset))
    if left4 != left2:
        return False
    right4 = _normalize_control_context(_ascii_right_signature(ps4_raw, ps4_offset))
    right2 = _normalize_control_context(_ascii_right_signature(ps2_raw, ps2_offset))
    return right4 == right2 or _right_control_delimiter(right4) == _right_control_delimiter(right2)


def _decode_semantic_span(raw: bytes) -> str | None:
    try:
        text = raw.replace(b"r", b"").decode("cp932")
    except UnicodeDecodeError:
        return None
    # PS2 scripts sometimes retain ruby source markup (`l漢字(かな)`) that the
    # remaster source simplified. Ruby pronunciation is presentation metadata;
    # compare the underlying base text when deciding semantic equivalence.
    text = re.sub(r"l([^()]+)\([^)]*\)", r"\1", text)
    return text.replace("\x00", "")


def _semantic_similarity(left: bytes, right: bytes) -> float:
    a = _decode_semantic_span(left)
    b = _decode_semantic_span(right)
    if a is None or b is None or not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def _cluster_is_line_sequence(ps4_raw: bytes, groups: tuple[DcGroup, ...]) -> bool:
    for previous, current in zip(groups, groups[1:]):
        if ps4_raw[previous.replace_end:current.anchor] != b"r":
            return False
    return True


def _mapped_span(
    ps4_raw: bytes,
    ps2_raw: bytes,
    blocks,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    mapped_start = _map_offset(blocks, start)
    mapped_end = _map_offset(blocks, end)
    if mapped_start is None or mapped_end is None or mapped_end <= mapped_start:
        return None
    if not _boundary_context_matches(ps4_raw, ps2_raw, start, mapped_start):
        return None
    if not _boundary_context_matches(ps4_raw, ps2_raw, end, mapped_end):
        return None
    return mapped_start, mapped_end


def _mapped_direct_span_with_prefix_insertion(
    ps4_raw: bytes,
    ps2_raw: bytes,
    blocks,
    start: int,
    end: int,
) -> tuple[int, int] | None:
    """Allow PS2-only controls immediately before a long exact matching block.

    This is intentionally narrow: the exact block must start at the localized
    PS4 span, continue at least eight bytes beyond that span, and the trailing
    control delimiter must still agree. It covers a PS2-only setup-command
    prefix without weakening ordinary interior boundary checks.
    """
    for block in blocks:
        if block.size <= 0 or block.a != start or end > block.a + block.size:
            continue
        if block.size < (end - start) + 8:
            continue
        mapped_start = block.b
        mapped_end = block.b + (end - start)
        right4 = _normalize_control_context(_ascii_right_signature(ps4_raw, end))
        right2 = _normalize_control_context(_ascii_right_signature(ps2_raw, mapped_end))
        if right4 == right2 or _right_control_delimiter(right4) == _right_control_delimiter(right2):
            return mapped_start, mapped_end
    return None


def import_structural_mtx(
    ps2_raw: bytes,
    ps4_raw: bytes,
    dc: dict[str, Any],
    *,
    min_semantic_similarity: float = 0.90,
) -> StructuralImportResult:
    if ps2_raw == ps4_raw:
        raise StructuralImportError("Structural tier requires non-identical PS2/PS4 sources")
    try:
        localization = DcLocalization.from_json(ps4_raw, dc)
        ps2_mtx = MtxFile.parse(ps2_raw)
        MtxFile.parse(ps4_raw)
    except ValueError as exc:
        raise StructuralImportError(str(exc)) from exc

    groups = localization.groups
    blocks = _matching_blocks(ps4_raw, ps2_raw)
    replacements: list[MtxReplacement] = []
    spans: list[StructuralSpan] = []
    resolved = [False] * len(groups)
    direct_groups = 0
    semantic_groups = 0

    for index, group in enumerate(groups):
        mapped = _mapped_span(ps4_raw, ps2_raw, blocks, group.anchor, group.replace_end)
        if mapped is None:
            mapped = _mapped_direct_span_with_prefix_insertion(
                ps4_raw, ps2_raw, blocks, group.anchor, group.replace_end
            )
        if mapped is None:
            continue
        start, end = mapped
        if ps4_raw[group.anchor:group.replace_end] != ps2_raw[start:end]:
            continue
        replacements.append(MtxReplacement(start, end, group.encoded_replacement()))
        spans.append(
            StructuralSpan(index, index, group.anchor, group.replace_end, start, end, "direct", 1.0)
        )
        resolved[index] = True
        direct_groups += 1

    index = 0
    while index < len(groups):
        if resolved[index]:
            index += 1
            continue
        end_index = index
        while end_index + 1 < len(groups) and not resolved[end_index + 1]:
            gap = ps4_raw[groups[end_index].replace_end:groups[end_index + 1].anchor]
            if gap != b"r":
                break
            end_index += 1

        cluster = groups[index:end_index + 1]
        if not _cluster_is_line_sequence(ps4_raw, cluster):
            index = end_index + 1
            continue
        ps4_start = cluster[0].anchor
        ps4_end = cluster[-1].replace_end
        mapped = _mapped_span(ps4_raw, ps2_raw, blocks, ps4_start, ps4_end)
        if mapped is None:
            index = end_index + 1
            continue
        ps2_start, ps2_end = mapped
        ps4_span = ps4_raw[ps4_start:ps4_end]
        ps2_span = ps2_raw[ps2_start:ps2_end]
        # Individual DC groups can themselves contain `r` line breaks when the
        # remaster merged Japanese display lines into one localized sentence.
        # Require PS2 and PS4 to preserve the same break topology rather than
        # assuming one break per adjacent DC group.
        if ps4_span.count(b"r") != ps2_span.count(b"r"):
            index = end_index + 1
            continue
        similarity = _semantic_similarity(ps4_span, ps2_span)
        if similarity < min_semantic_similarity:
            index = end_index + 1
            continue
        data = b"r".join(group.encoded_replacement() for group in cluster)
        replacements.append(MtxReplacement(ps2_start, ps2_end, data))
        spans.append(
            StructuralSpan(
                index,
                end_index,
                ps4_start,
                ps4_end,
                ps2_start,
                ps2_end,
                "semantic-cluster",
                similarity,
            )
        )
        for resolved_index in range(index, end_index + 1):
            resolved[resolved_index] = True
        semantic_groups += len(cluster)
        index = end_index + 1

    unresolved = [groups[i].anchor for i, is_resolved in enumerate(resolved) if not is_resolved]
    if unresolved:
        sample = ", ".join(str(value) for value in unresolved[:10])
        raise StructuralImportError(
            f"Structural import could not prove {len(unresolved)}/{len(groups)} groups; anchors: {sample}"
        )

    try:
        rebuilt = ps2_mtx.apply_replacements(tuple(replacements)).compile()
        MtxFile.parse(rebuilt)
    except ValueError as exc:
        raise StructuralImportError(f"Structural MTX compile failed: {exc}") from exc

    ordered = sorted(spans, key=lambda span: span.ps2_start)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.ps2_end > current.ps2_start:
            raise StructuralImportError("Mapped structural spans overlap on the PS2 source")

    return StructuralImportResult(
        data=rebuilt,
        english_entries=sum(1 + len(group.synthetic_keys) for group in groups),
        groups_total=len(groups),
        direct_groups=direct_groups,
        semantic_groups=semantic_groups,
        spans=tuple(sorted(spans, key=lambda span: span.first_group)),
    )
