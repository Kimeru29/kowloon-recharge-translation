"""Page-local reflow for the four crowded r67 H.A.N.T. Help bodies.

Only the four page descriptors and their current table/metadata preimages are
owned here. Text and icon rows are appended to the existing translation
PT_LOAD; the native 16-row Help viewport and scrolling code are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import struct
import unicodedata
from typing import Any

from tools.first_save_help_inventory import _BLANK, _EOF
from tools.localization import encode_ps2_english

_SEGMENT_VA = 0x902F00
_VIEW_ROWS = 16
_TEXT_X = 85
_TEXT_Y = 131
_GLYPH_W = 12
_GLYPH_H = 12
_ROW_H = 16
_BLANK_VA = 0x795FB8
_EOF_VA = 0x795FBC
_OFFICIAL_CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"


@dataclass(frozen=True)
class PageOwner:
    key: str
    descriptor_offset: int
    metadata_descriptor_offset: int
    table_sha256: str
    metadata_sha256: str
    text_sha256: str
    table_va: int
    metadata_va: int
    table_rows: int
    icon_count: int


_OWNERS = (
    PageOwner("item_synthesis", 0x5CBADC, 0x5CBA8C,
              "65d0d4095239c4045a54766d7655e8bbaa1dffc13b7c1e1e95852186539e6016",
              "8deb0776b04175b342f04cea646098f06ff32eae776d56c456adb62688dc0088",
              "2af3fb7c7a7207f3e057378d7575309ad33f9c17760773702e39c19ae2814bb4",
              0x962020, 0x958EF4, 20, 5),
    PageOwner("save_load", 0x5CBAE8, 0x5CBA98,
              "fd0e0bae58ba5f88151779f7c07bbde107894d4879527c77c1bfefc1a3392f00",
              "d831058c20326283e1cd0290962600869276fcb437ced822d40d5c3aab401a9f",
              "eb63cccfe1d5f2b1293ef6c55d33ae48fc3be53357f819abf653bdb5df6b7ef1",
              0x962BA0, 0x959B34, 18, 1),
    PageOwner("wire_gun", 0x5C8A90, 0x5C8A40,
              "a20b533abf38e4f8d18b7e466bc22055ec689f8c4b56e062793a184c945b0d65",
              "779812d2d0835591545903b06fdbb0858921564dbd235c3f0d47246e0272c50c",
              "5f529e117391030e98cca3788ff255c0a388b6660e0f81c3e29d976db615bb04",
              0x95DDCC, 0x95470C, 28, 7),
    PageOwner("jumping", 0x5C8A8C, 0x5C8A3C,
              "088d2e113d98875540c4434582227dd2ced2e034ee738c72853bb3c19967ccaf",
              "2d6c42e0838d801627dbfc571ce44007d1fcebe87a4667e3ad26025edfafff09",
              "55ff24753cb35bd392249e90ac493cd513d0050cc89de0c8188a4c9683a86760",
              0x95D9C4, 0x9542D8, 39, 9),
)
PAGE_OWNERS: dict[str, dict[str, Any]] = {
    owner.key: {
        "descriptor_offset": owner.descriptor_offset,
        "metadata_descriptor_offset": owner.metadata_descriptor_offset,
        "table_sha256": owner.table_sha256,
        "metadata_sha256": owner.metadata_sha256,
        "text_sha256": owner.text_sha256,
        "table_va": owner.table_va,
        "metadata_va": owner.metadata_va,
        "table_rows": owner.table_rows,
        "icon_count": owner.icon_count,
    }
    for owner in _OWNERS
}

# Bindings are in native metadata order. The first two fields are the exact
# button/sprite identity consumed by the PS2 renderer; anchors keep each glyph
# with its intended official instruction after row movement.
_RAW_BINDINGS: dict[str, tuple[tuple[int, int, str, str], ...]] = {
    "item_synthesis": (
        (0, 3, "1st item", "button"),
        (0, 3, "2nd item", "button"),
        (38, 10, "cannot be compounded", "warning"),
        (38, 10, "compounding guide", "warning"),
        (0, 5, "compounding guide", "button"),
    ),
    "save_load": ((38, 10, "Rockford Adventure", "warning"),),
    "wire_gun": (
        (38, 11, "wire gun", "diagram"),
        (0, 3, "show the grid", "button"),
        (0, 3, "fire the wire gun", "button"),
        (38, 1, "Move the pointer", "dpad"),
        (38, 16, "show the grid", "diagram"),
        (38, 17, "scale the wire", "diagram"),
        (38, 10, "range", "warning"),
    ),
    "jumping": (
        (0, 3, "press the button to jump", "button"),
        (0, 3, "make the pointer appear", "button"),
        (38, 1, "Move the pointer", "dpad"),
        (0, 3, "designated grid", "button"),
        (38, 18, "make the pointer appear", "diagram"),
        (38, 19, "Move the pointer", "diagram"),
        (38, 28, "designated grid", "diagram"),
        (38, 10, "obstruction", "warning"),
        (38, 10, "range", "warning"),
    ),
}

# Native group entries are at VA 0x480A70 (file 0x380AF0); each first frame is
# a 0x30-byte record with W/H and pivot X/Y at +4. Hashes pin the exact source
# entry and frame so layout never relies on a guessed or remaster-era extent.
_SPRITE_FRAME_PREIMAGES = {
    1: ("0cb4320466cd75c26112b343a2b9b04f369845a8ccbbbc3d2cf48e4f42dde5b0", (16, 16, -11, -15)),
    3: ("29242092e863825a05faaecbe253ffe003b9eab39f8630d32e0f70b12d25f8b8", (24, 24, -6, -12)),
    5: ("5e2cba89259ea34cea9a8734c586589971371ef20666c951c33d0314b60eaa89", (24, 24, -6, -12)),
    10: ("b6772e927a88e60ee96c1af56829789119307cd33bdb4629c1718604eb7d86d0", (24, 24, -6, -12)),
    11: ("078c4f283cb623e8e13aba73e416306ca8fddb1fe8fec678fcb573337a1f4a80", (24, 24, -6, -12)),
    16: ("87754f6429ada6c21a3bd377093b35a620c668e6c7588722cda7043c5ae3aeae", (64, 64, 32, 32)),
    17: ("d46234d99e819461d64529e9f12adfb7b99d426ac7b287aaec577fdcca2282bf", (80, 64, 40, 25)),
    18: ("7a360a40cd4110b8c6c84384885ae2bdf23df9683b3463db13bc0a90fd9f713c", (48, 32, 24, 48)),
    19: ("1b09c0c2e9a4670028e38f1d027f212d66f4de07a5558e7f2cc184f63de3b0a4", (120, 96, 60, -25)),
    28: ("9c2beb419e134ebbacbbd57c0543c9b196174f9512139ce1c54c72f2848bea33", (144, 104, 2, 0)),
}

ICON_BINDINGS: dict[str, tuple[dict[str, Any], ...]] = {
    owner.key: tuple(
        {
            "identity": (kind, variant),
            "anchor": anchor,
            "role": role,
            "bounds": _SPRITE_FRAME_PREIMAGES[variant][1][:2],
            "pivot": _SPRITE_FRAME_PREIMAGES[variant][1][2:],
        }
        for kind, variant, anchor, role in _RAW_BINDINGS[owner.key]
    )
    for owner in _OWNERS
}

PERMITTED_EXISTING_RANGES = (
    (0x5CBADC, 0x5CBAE0), (0x5CBA8C, 0x5CBA90),
    (0x5CBAE8, 0x5CBAEC), (0x5CBA98, 0x5CBA9C),
    (0x5C8A90, 0x5C8A94), (0x5C8A40, 0x5C8A44),
    (0x5C8A8C, 0x5C8A90), (0x5C8A3C, 0x5C8A40),
)


def _sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _load_segments(raw: bytes) -> list[tuple[int, int, int]]:
    if raw[:4] != b"\x7fELF":
        raise ValueError("ELF preimage is malformed")
    phoff = struct.unpack_from("<I", raw, 28)[0]
    entsize, count = struct.unpack_from("<HH", raw, 42)
    if entsize != 32 or phoff + entsize * count > len(raw):
        raise ValueError("ELF program-header preimage is malformed")
    return [
        (offset, va, file_size)
        for index in range(count)
        for kind, offset, va, _pa, file_size, _mem_size, _flags, _align in [
            struct.unpack_from("<8I", raw, phoff + index * entsize)
        ]
        if kind == 1
    ]


def _va_to_offset(raw: bytes, address: int) -> int:
    for offset, base, length in _load_segments(raw):
        if base <= address < base + length:
            return offset + address - base
    raise ValueError(f"unmapped H.A.N.T. pointer {address:#x}")


def _validate_sprite_frames(raw: bytes) -> dict[int, tuple[int, int, int, int]]:
    frames = {}
    for group, (expected_sha, expected_geometry) in _SPRITE_FRAME_PREIMAGES.items():
        entry_address = 0x480A70 + group * 8
        entry_offset = _va_to_offset(raw, entry_address)
        frame_address, frame_count = struct.unpack_from("<II", raw, entry_offset)
        if frame_count < 1:
            raise ValueError(f"native sprite group {group} has no first frame")
        frame_offset = _va_to_offset(raw, frame_address)
        owner_bytes = raw[entry_offset:entry_offset + 8] + raw[frame_offset:frame_offset + 0x30]
        if _sha(owner_bytes) != expected_sha:
            raise ValueError(f"native sprite frame preimage mismatch: group {group}")
        width, height, pivot_x, pivot_y = struct.unpack_from("<4f", raw, frame_offset + 4)
        geometry = tuple(int(value) for value in (width, height, pivot_x, pivot_y))
        if geometry != expected_geometry or width <= 0 or height <= 0:
            raise ValueError(f"native sprite frame geometry mismatch: group {group}")
        frames[group] = geometry
    return frames


def _map_pages(raw: bytes, *, validate_preimage: bool = True) -> dict[str, dict[str, Any]]:
    pages = {}
    for owner in _OWNERS:
        d = PAGE_OWNERS[owner.key]
        table_va = struct.unpack_from("<I", raw, owner.descriptor_offset)[0]
        meta_va = struct.unpack_from("<I", raw, owner.metadata_descriptor_offset)[0]
        if validate_preimage and (table_va != owner.table_va or meta_va != owner.metadata_va):
            raise ValueError(f"{owner.key} descriptor owner preimage mismatch")
        table = _va_to_offset(raw, table_va)
        metadata = _va_to_offset(raw, meta_va)
        table_count = owner.table_rows if validate_preimage else next(
            (index + 1 for index in range(256)
             if struct.unpack_from("<I", raw, table + index * 4)[0] == _EOF_VA),
            0,
        )
        icon_count = owner.icon_count if validate_preimage else next(
            (index for index in range(32)
             if struct.unpack_from("<4h", raw, metadata + index * 8) == (-1, -1, -1, -1)),
            -1,
        )
        if not table_count or icon_count < 0:
            raise ValueError(f"{owner.key} row/icon terminator missing")
        table_size = table_count * 4
        metadata_size = (icon_count + 1) * 8
        if validate_preimage and _sha(raw[table:table + table_size]) != owner.table_sha256:
            raise ValueError(f"{owner.key} table owner preimage mismatch")
        if validate_preimage and _sha(raw[metadata:metadata + metadata_size]) != owner.metadata_sha256:
            raise ValueError(f"{owner.key} metadata owner preimage mismatch")
        rows: list[str] = []
        for row in range(table_count - 1):
            pointer = struct.unpack_from("<I", raw, table + row * 4)[0]
            if pointer == _BLANK_VA:
                rows.append("")
            elif pointer in (_EOF_VA, _BLANK):
                raise ValueError(f"{owner.key} table terminator moved")
            else:
                start = _va_to_offset(raw, pointer)
                end = raw.find(b"\0", start, min(len(raw), start + 384))
                if end < 0:
                    raise ValueError(f"{owner.key} row {row} is unterminated")
                rows.append(raw[start:end].decode("cp932"))
        if struct.unpack_from("<I", raw, table + (table_count - 1) * 4)[0] != _EOF_VA:
            raise ValueError(f"{owner.key} EOF owner preimage mismatch")
        records = tuple(
            struct.unpack_from("<4h", raw, metadata + index * 8)
            for index in range(icon_count)
        )
        if struct.unpack_from("<4h", raw, metadata + icon_count * 8) != (-1, -1, -1, -1):
            raise ValueError(f"{owner.key} icon terminator moved")
        if validate_preimage and tuple(record[:2] for record in records) != tuple(
            entry["identity"] for entry in ICON_BINDINGS[owner.key]
        ):
            raise ValueError(f"{owner.key} button/sprite identity preimage mismatch")
        if validate_preimage:
            text_preimage = b"".join(
                row.encode("cp932") + b"\0" if row else b"\xff"
                for row in rows
            )
            if _sha(text_preimage) != owner.text_sha256:
                raise ValueError(f"{owner.key} source English text preimage mismatch")
        pages[owner.key] = {
            **d, "table_offset": table, "metadata_offset": metadata,
            "rows": rows, "metadata": records,
        }
    return pages


def _normalize_row(row: str) -> str:
    return unicodedata.normalize("NFKC", row).replace("\u3000", " ").strip()


def _paragraphs(rows: list[str]) -> list[str]:
    paragraphs = []
    current = []
    for row in rows:
        text = _normalize_row(row)
        if not text:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(text)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def _wrap(text: str, max_cells: int = 28) -> list[str]:
    words = text.split()
    output: list[str] = []
    line = ""
    for word in words:
        if len(word) > max_cells:
            raise ValueError(f"Help word exceeds {max_cells}-cell viewport: {word!r}")
        candidate = word if not line else f"{line} {word}"
        if len(candidate) <= max_cells:
            line = candidate
        else:
            output.append(line)
            line = word
    if line:
        output.append(line)
    return output


def _binding_paragraphs(key: str, paragraphs: list[str]) -> list[int]:
    indices = []
    for binding in ICON_BINDINGS[key]:
        matches = [index for index, paragraph in enumerate(paragraphs)
                   if binding["anchor"].casefold() in paragraph.casefold()]
        if not matches:
            raise ValueError(f"{key} icon anchor not found: {binding['anchor']}")
        indices.append(matches[0])
    return indices


def _reflow(key: str, rows: list[str], metadata: tuple[tuple[int, int, int, int], ...]):
    paragraphs = _paragraphs(rows)
    icon_paragraphs = _binding_paragraphs(key, paragraphs)
    icons_by_paragraph: dict[int, list[int]] = {}
    for icon_index, paragraph_index in enumerate(icon_paragraphs):
        icons_by_paragraph.setdefault(paragraph_index, []).append(icon_index)

    canvas: list[str] = []
    moved_icons: list[dict[str, Any] | None] = [None] * len(metadata)
    for paragraph_index, paragraph in enumerate(paragraphs):
        if canvas:
            canvas.append("")
        for icon_index in icons_by_paragraph.get(paragraph_index, []):
            binding = ICON_BINDINGS[key][icon_index]
            icon_row = len(canvas)
            canvas.append("")
            width, height = binding["bounds"]
            pivot_x, pivot_y = binding["pivot"]
            reserved_rows = max(1, math.ceil((height + 2 * abs(pivot_y)) / _ROW_H))
            canvas.extend([""] * (reserved_rows - 1))
            moved_icons[icon_index] = {
                "identity": binding["identity"], "role": binding["role"],
                "anchor": binding["anchor"], "icon_row": icon_row,
                "instruction_row": -1, "width": width, "height": height,
                "bounds": binding["bounds"], "pivot": binding["pivot"],
            }
        for icon_index in icons_by_paragraph.get(paragraph_index, []):
            assert moved_icons[icon_index] is not None
            moved_icons[icon_index]["instruction_row"] = len(canvas)
        canvas.extend(_wrap(paragraph))

    translated_metadata = []
    for icon, record in zip(moved_icons, metadata, strict=True):
        assert icon is not None
        kind, variant, _x, _y = record
        _width, _height = icon["bounds"]
        pivot_x, pivot_y = icon["pivot"]
        translated_metadata.append((kind, variant,
                                    _TEXT_X + abs(pivot_x) - 73,
                                    _TEXT_Y + icon["icon_row"] * _ROW_H
                                    + abs(pivot_y) - 119))
    translated_metadata.append((-1, -1, -1, -1))
    return canvas, tuple(translated_metadata), [icon for icon in moved_icons if icon is not None], paragraphs


def _table_data(raw: bytes, owner: PageOwner) -> tuple[int, list[str]]:
    table = _va_to_offset(raw, struct.unpack_from("<I", raw, owner.descriptor_offset)[0])
    rows = []
    for row in range(160):
        pointer = struct.unpack_from("<I", raw, table + row * 4)[0]
        if pointer == _EOF_VA:
            return table, rows
        if pointer == _BLANK_VA:
            rows.append("")
        else:
            start = _va_to_offset(raw, pointer)
            end = raw.find(b"\0", start, min(len(raw), start + 384))
            if end < 0:
                raise ValueError("unterminated Help row")
            rows.append(raw[start:end].decode("cp932"))
    raise ValueError("Help page has no EOF")


def _rect_intersects(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> bool:
    lx, ly, lw, lh = left
    rx, ry, rw, rh = right
    return lx < rx + rw and rx < lx + lw and ly < ry + rh and ry < ly + lh


def page_geometry(raw: bytes, *, legacy: bool = False) -> dict[str, dict[str, Any]]:
    frame_geometry = _validate_sprite_frames(raw)
    pages = _map_pages(raw, validate_preimage=False)
    result = {}
    for key, page in pages.items():
        rows = page["rows"]
        if legacy:
            icon_rects = []
            for kind, variant, x, y in page["metadata"]:
                width, height, pivot_x, pivot_y = frame_geometry[variant]
                icon_rects.append((73 + x - abs(pivot_x), 119 + y - abs(pivot_y),
                                   width + 2 * abs(pivot_x),
                                   height + 2 * abs(pivot_y)))
            glyph_rows = rows
        else:
            icon_rects = []
            glyph_rows = rows
            for binding, record in zip(ICON_BINDINGS[key], page["metadata"], strict=True):
                kind, variant, x, y = record
                width, height, pivot_x, pivot_y = frame_geometry[variant]
                icon_rects.append((73 + x - abs(pivot_x), 119 + y - abs(pivot_y),
                                   width + 2 * abs(pivot_x),
                                   height + 2 * abs(pivot_y)))

        glyph_rects = []
        glyph_widths = []
        for row_index, row in enumerate(glyph_rows):
            norm = _normalize_row(row)
            glyph_widths.append(len(norm))
            if norm:
                glyph_rects.append((
                    _TEXT_X, _TEXT_Y + row_index * _ROW_H,
                    len(norm) * _GLYPH_W, _GLYPH_H,
                ))
        intersections = []
        max_scroll = max(0, len(rows) - _VIEW_ROWS)
        for scroll in range(max_scroll + 1):
            scroll_y = scroll * _ROW_H
            for icon_index, icon in enumerate(icon_rects):
                viewport_icon = (icon[0], icon[1] - scroll_y, icon[2], icon[3])
                if viewport_icon[1] >= _TEXT_Y + _VIEW_ROWS * _ROW_H or viewport_icon[1] + viewport_icon[3] <= _TEXT_Y:
                    continue
                for glyph_index, glyph in enumerate(glyph_rects):
                    viewport_glyph = (glyph[0], glyph[1] - scroll_y, glyph[2], glyph[3])
                    if _rect_intersects(viewport_icon, viewport_glyph):
                        intersections.append({"icon": icon_index, "glyph_row": glyph_index,
                                              "scroll_row": scroll})
                        break
        result[key] = {
            "intersections": intersections,
            "glyph_widths": glyph_widths,
            "icon_rectangles": icon_rects,
            "max_scroll_row": max_scroll,
        }
    return result


def apply(source: bytes, official_english_bytes: bytes) -> tuple[bytes, dict[str, Any]]:
    """Append reflowed pages to the existing 15f ELF; reject any owner drift."""
    _load_segments(source)
    phoff = struct.unpack_from("<I", source, 28)[0]
    phentsize, phcount = struct.unpack_from("<HH", source, 42)
    loads = [
        (index, *struct.unpack_from("<8I", source, phoff + index * phentsize))
        for index in range(phcount)
        if struct.unpack_from("<I", source, phoff + index * phentsize)[0] == 1
    ]
    target = [entry for entry in loads if entry[3] == _SEGMENT_VA]
    if len(target) != 1:
        raise ValueError("translation PT_LOAD owner preimage mismatch")
    index, kind, file_offset, va, _pa, file_size, mem_size, flags, align = target[0]
    if (file_offset != 0x803150 or mem_size != 0x100000 or flags != 7
            or align != 16 or file_offset + file_size != len(source)):
        raise ValueError("translation PT_LOAD geometry preimage mismatch")
    pages = _map_pages(source)
    sprite_frames = _validate_sprite_frames(source)

    # Parse as a provenance gate; fullwidth page text is retained exactly after
    # normalization, and each output paragraph remains a sequence of source
    # words. The corpus digest is included for the integrated audit trail.
    corpus_sha = _sha(official_english_bytes)
    if corpus_sha != _OFFICIAL_CORPUS_SHA256:
        raise ValueError("official English corpus preimage mismatch")
    out = bytearray(source)
    page_reports = {}

    def append(data: bytes, alignment: int = 4) -> int:
        while len(out) % alignment:
            out.append(0)
        address = va + len(out) - file_offset
        out.extend(data)
        return address

    for owner in _OWNERS:
        page = pages[owner.key]
        text_rows, metadata_rows, moved_icons, source_paragraphs = _reflow(
            owner.key, page["rows"], page["metadata"]
        )
        encoded_rows = [encode_ps2_english(row, collapse_spaces=False) + b"\0"
                        if row else None for row in text_rows]
        pointers = [append(data, 2) if data is not None else _BLANK_VA
                    for data in encoded_rows]
        table_va = append(struct.pack("<" + "I" * (len(pointers) + 1),
                                      *pointers, _EOF_VA), 4)
        metadata_va = append(b"".join(struct.pack("<4h", *record)
                                       for record in metadata_rows), 4)
        for descriptor, pointer in (
            (owner.descriptor_offset, table_va),
            (owner.metadata_descriptor_offset, metadata_va),
        ):
            struct.pack_into("<I", out, descriptor, pointer)

        page_reports[owner.key] = {
            "rows": len(text_rows), "source_paragraphs": len(source_paragraphs),
            "icons": [dict(item) for item in moved_icons],
            "max_scroll_row": max(0, len(text_rows) - _VIEW_ROWS),
            "last_row": unicodedata.normalize("NFKC", text_rows[-1]),
            "end_reachable": len(text_rows) > 0,
            "table_va": table_va, "metadata_va": metadata_va,
        }

    new_size = len(out) - file_offset
    if new_size > mem_size:
        raise ValueError("translation PT_LOAD memory reservation exceeded")
    struct.pack_into("<I", out, phoff + index * phentsize + 16, new_size)
    report = {
        "schema_version": 1,
        "source_sha256": _sha(source),
        "corpus_sha256": corpus_sha,
        "permitted_existing_ranges": [list(span) for span in PERMITTED_EXISTING_RANGES],
        "separately_audited_metadata_ranges": [[0x64, 0x68]],
        "appended_extent": [len(source), len(out)],
        "page_count": len(page_reports),
        "pages": page_reports,
        "sprite_frame_table_va": 0x480A70,
        "sprite_frames": {str(group): list(values)
                           for group, values in sprite_frames.items()},
        "sprite_frame_preimages": {
            str(group): expected[0]
            for group, expected in _SPRITE_FRAME_PREIMAGES.items()
        },
        "mapping_failures": [],
        "runtime_assumptions": [
            "native mode-4 Help viewport displays at most 16 rows and scrolls through the recorded row count",
            "no emulator/runtime acceptance was performed",
        ],
    }
    return bytes(out), report
