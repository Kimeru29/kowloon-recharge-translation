from __future__ import annotations

from dataclasses import dataclass
import re
import struct
from typing import Any


_PUNCTUATION = {
    "!": "！",
    "'": "’",
    ",": "，",
    ".": "．",
    "?": "？",
}


def encode_ps2_english(text: str) -> bytes:
    """Encode localized English without emitting MTX ASCII opcode bytes.

    Kowloon's MTX scripts use ordinary ASCII for their control language.  The
    PS2 font already contains the full-width/JIS Latin repertoire, so printable
    ASCII is converted to its full-width equivalent and every emitted glyph is
    required to occupy exactly two bytes in CP932.  Official remaster runs of
    spaces are collapsed because their double spacing is presentation data,
    not semantic text.
    """

    normalized = re.sub(r" +", " ", text)
    converted: list[str] = []
    for char in normalized:
        codepoint = ord(char)
        if char == " ":
            target = "\u3000"
        elif char == "'":
            # Match the punctuation glyph already proven by the vertical slice.
            target = "’"
        elif 0x21 <= codepoint <= 0x7E:
            target = chr(codepoint + 0xFEE0)
        elif char == "—":
            # U+2014 is not directly encodable in CP932; U+2015 is the JIS
            # horizontal bar used by the official corpus and the PS2 font.
            target = "―"
        else:
            target = char

        try:
            encoded = target.encode("cp932")
        except UnicodeEncodeError as exc:
            raise ValueError(
                f"Unsupported PS2 English character U+{codepoint:04X}: {char!r}"
            ) from exc
        if len(encoded) != 2:
            raise ValueError(
                f"Localized glyph escaped the two-byte JIS font bank: {char!r} -> {target!r}"
            )
        converted.append(target)

    return b"".join(char.encode("cp932") for char in converted)


def _cp932_boundaries(raw: bytes, start: int) -> set[int]:
    boundaries: set[int] = {start}
    offset = start
    while offset < len(raw):
        boundaries.add(offset)
        byte = raw[offset]
        if (0x81 <= byte <= 0x9F) or (0xE0 <= byte <= 0xFC):
            if offset + 1 >= len(raw):
                raise ValueError(f"Truncated Shift-JIS lead byte at {offset}")
            offset += 2
        else:
            offset += 1
    boundaries.add(len(raw))
    return boundaries


@dataclass(frozen=True)
class DcGroup:
    anchor: int
    lines: tuple[str, ...]
    synthetic_keys: tuple[int, ...]
    replace_end: int

    def encoded_replacement(self) -> bytes:
        return b"r".join(encode_ps2_english(line) for line in self.lines)


@dataclass(frozen=True)
class DcLocalization:
    groups: tuple[DcGroup, ...]

    @classmethod
    def from_json(cls, raw: bytes, obj: dict[str, Any]) -> "DcLocalization":
        keys = obj.get("keys")
        values = obj.get("values")
        if not isinstance(keys, list) or not isinstance(values, list) or len(keys) != len(values):
            raise ValueError("DC JSON must contain equal-length keys and values arrays")
        if len(raw) < 2:
            raise ValueError("MTX is too small")

        header_size = struct.unpack_from("<H", raw, 0)[0] * 4
        boundaries = _cp932_boundaries(raw, header_size)
        pairs = sorted((int(key), str(value)) for key, value in zip(keys, values))

        grouped: list[dict[str, Any]] = []
        for key, value in pairs:
            if key not in boundaries:
                if not grouped:
                    raise ValueError(f"Synthetic DC key {key} has no preceding anchor")
                grouped[-1]["lines"].append(value)
                grouped[-1]["synthetic_keys"].append(key)
                continue
            grouped.append({"anchor": key, "lines": [value], "synthetic_keys": []})

        anchors = [entry["anchor"] for entry in grouped]
        result: list[DcGroup] = []
        for index, entry in enumerate(grouped):
            anchor = entry["anchor"]
            next_anchor = anchors[index + 1] if index + 1 < len(anchors) else len(raw)
            if not (header_size <= anchor < next_anchor <= len(raw)):
                raise ValueError(f"Invalid DC anchor range {anchor}..{next_anchor}")

            segment = raw[anchor:next_anchor]
            marker_positions: list[int] = []

            def first_boundary_marker(marker: bytes) -> int | None:
                search_from = 0
                while True:
                    position = segment.find(marker, search_from)
                    if position < 0:
                        return None
                    if anchor + position in boundaries:
                        return position
                    search_from = position + 1

            if segment.endswith(b"r") and anchor + len(segment) - 1 in boundaries:
                marker_positions.append(len(segment) - 1)
            for marker in (b"wc", b"}w"):
                position = first_boundary_marker(marker)
                if position is not None:
                    marker_positions.append(position)

            # Less common scripts terminate localized text immediately before
            # another control sequence rather than wc/}w.  Accept only control
            # markers that begin on a decoded CP932 boundary; this prevents a
            # marker-looking trail byte from becoming a false text boundary.
            if not marker_positions:
                for marker in (b"}", b"rds", b"ds"):
                    position = first_boundary_marker(marker)
                    if position is not None:
                        marker_positions.append(position)
                if segment.endswith(b"c"):
                    position = len(segment) - 1
                    if anchor + position in boundaries:
                        marker_positions.append(position)

            if not marker_positions:
                raise ValueError(
                    f"Unable to infer localized span terminator for DC anchor {anchor}"
                )
            replace_end = anchor + min(marker_positions)

            if replace_end <= anchor:
                raise ValueError(f"Empty localized span at DC anchor {anchor}")

            result.append(
                DcGroup(
                    anchor=anchor,
                    lines=tuple(entry["lines"]),
                    synthetic_keys=tuple(entry["synthetic_keys"]),
                    replace_end=replace_end,
                )
            )

        return cls(tuple(result))

    def group_at(self, anchor: int) -> DcGroup:
        for group in self.groups:
            if group.anchor == anchor:
                return group
        raise KeyError(anchor)
