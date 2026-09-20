from __future__ import annotations

from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class MtxReplacement:
    start: int
    end: int
    data: bytes

    def __post_init__(self) -> None:
        if self.start < 0 or self.end <= self.start:
            raise ValueError(f"Invalid MTX replacement range {self.start}..{self.end}")


@dataclass(frozen=True)
class MtxFile:
    pointer_words: tuple[int, ...]
    data: bytes

    @property
    def header_size(self) -> int:
        return self.pointer_words[0] * 4

    @property
    def pointer_offsets(self) -> tuple[int, ...]:
        return tuple(value * 4 for value in self.pointer_words)

    @classmethod
    def parse(cls, raw: bytes) -> "MtxFile":
        if len(raw) < 4:
            raise ValueError("MTX is too small")

        first_word = struct.unpack_from("<H", raw, 0)[0]
        if first_word == 0:
            raise ValueError("MTX first pointer cannot be zero")

        header_size = first_word * 4
        if header_size > len(raw):
            raise ValueError("MTX header extends beyond the file")
        if header_size % 2:
            raise ValueError("MTX header size is not u16 aligned")

        word_count = header_size // 2
        pointer_words = struct.unpack_from(f"<{word_count}H", raw, 0)
        for value in pointer_words:
            if value and value * 4 > len(raw):
                raise ValueError(f"MTX pointer {value} points beyond the file")

        return cls(tuple(pointer_words), raw[header_size:])

    def compile(self) -> bytes:
        header = struct.pack(f"<{len(self.pointer_words)}H", *self.pointer_words)
        if len(header) != self.header_size:
            raise ValueError("MTX pointer table no longer matches its encoded header size")
        return header + self.data

    def apply_replacements(self, replacements: tuple[MtxReplacement, ...]) -> "MtxFile":
        if not replacements:
            return self

        raw = self.compile()
        ordered = tuple(sorted(replacements, key=lambda item: (item.start, item.end)))
        previous_end = self.header_size
        for replacement in ordered:
            if replacement.start < self.header_size:
                raise ValueError("MTX replacement overlaps pointer header")
            if replacement.start < previous_end:
                raise ValueError("MTX replacements overlap")
            if replacement.end > len(raw):
                raise ValueError("MTX replacement extends beyond file")
            previous_end = replacement.end

        region_starts = sorted({value * 4 for value in self.pointer_words if value})
        if not region_starts or region_starts[0] != self.header_size:
            raise ValueError("MTX first pointer must address the start of the data region")
        region_ends = region_starts[1:] + [len(raw)]

        replacements_by_region: dict[int, list[MtxReplacement]] = {start: [] for start in region_starts}
        for replacement in ordered:
            containing = [
                start
                for start, end in zip(region_starts, region_ends)
                if start <= replacement.start and replacement.end <= end
            ]
            if len(containing) != 1:
                raise ValueError(
                    f"MTX replacement {replacement.start}..{replacement.end} crosses a pointer region boundary"
                )
            replacements_by_region[containing[0]].append(replacement)

        body = bytearray()
        relocated: dict[int, int] = {}
        for region_start, region_end in zip(region_starts, region_ends):
            relocated[region_start] = self.header_size + len(body)
            source = raw[region_start:region_end]
            region_out = bytearray()
            cursor = region_start
            for replacement in replacements_by_region[region_start]:
                region_out.extend(raw[cursor:replacement.start])
                region_out.extend(replacement.data)
                cursor = replacement.end
            region_out.extend(raw[cursor:region_end])

            padding = (-len(region_out)) % 4
            if padding:
                # DG/MTX pointer regions terminate with '_' and optional NUL padding.
                # Extending that padding is safe and keeps every entry point quarter-aligned.
                if not source.rstrip(b"\x00").endswith(b"_"):
                    raise ValueError(
                        f"MTX pointer region {region_start}..{region_end} needs alignment padding but has no safe '_' terminator"
                    )
                region_out.extend(b"\x00" * padding)
            body.extend(region_out)

        new_words: list[int] = []
        for word in self.pointer_words:
            if word == 0:
                new_words.append(0)
                continue
            old_offset = word * 4
            try:
                new_offset = relocated[old_offset]
            except KeyError as exc:
                raise ValueError(f"MTX pointer target {old_offset} is not a compiled region boundary") from exc
            if new_offset % 4:
                raise ValueError(f"Relocated MTX pointer {new_offset} is not 4-byte aligned")
            new_word = new_offset // 4
            if new_word > 0xFFFF:
                raise ValueError(f"Relocated MTX pointer exceeds u16 quarter-offset range: {new_offset}")
            new_words.append(new_word)

        result = MtxFile(tuple(new_words), bytes(body))
        # Reparse as a structural assertion before returning generated binary data.
        MtxFile.parse(result.compile())
        return result
