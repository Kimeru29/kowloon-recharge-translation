from __future__ import annotations

from dataclasses import dataclass
import re
import struct


_NAME_RE = re.compile(rb"GRP(\d{3})/GP\1_(\d{2})\.TMX\x00")


@dataclass(frozen=True)
class TmxEntry:
    name: str
    name_offset: int
    base_offset: int
    chunk_size: int
    width: int
    height: int
    image_psm: int
    palette_count: int
    palette_psm: int
    palette_offset: int
    palette_entries: int
    palette_bytes: int
    pixel_offset: int
    pixel_bytes: int


def _alpha_from_ps2(value: int) -> int:
    return min(255, value * 2)


def _alpha_to_ps2(value: int) -> int:
    if not 0 <= value <= 255:
        raise ValueError(f"RGBA alpha out of range: {value}")
    return min(0x80, (value + 1) // 2)


def _swizzle_clut_8(palette: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    """Convert between stored PSMT8 CLUT order and logical palette order.

    The middle two 8-color blocks in each 32-entry group are exchanged. The
    transform is its own inverse, so the same routine is used for decode/encode.
    """

    if len(palette) != 256:
        raise ValueError(f"8-bit TMX palette must contain 256 colors, got {len(palette)}")
    out = palette[:]
    for base in range(0, 256, 32):
        out[base + 8:base + 16], out[base + 16:base + 24] = (
            palette[base + 16:base + 24],
            palette[base + 8:base + 16],
        )
    return out


def iter_tmx_entries(blob: bytes) -> tuple[TmxEntry, ...]:
    entries: list[TmxEntry] = []
    for match in _NAME_RE.finditer(blob):
        name = match.group(0)[:-1].decode("ascii")
        tmx = blob.find(b"TMX0", match.end(), min(len(blob), match.end() + 0x1000))
        if tmx < 8:
            raise ValueError(f"{name}: TMX0 not found near container name")
        base = tmx - 8
        ident, chunk_size = struct.unpack_from("<II", blob, base)
        if ident != 2:
            raise ValueError(f"{name}: unexpected TMX chunk id {ident}")
        if base + chunk_size > len(blob):
            raise ValueError(f"{name}: TMX chunk extends outside container")

        palette_count = blob[tmx + 8]
        palette_psm = blob[tmx + 9]
        width, height = struct.unpack_from("<HH", blob, tmx + 10)
        image_psm = blob[tmx + 14]
        if palette_count != 1 or palette_psm != 0:
            raise ValueError(
                f"{name}: unsupported palette count/PSM {palette_count}/{palette_psm:#x}"
            )
        if image_psm == 0x13:
            palette_entries = 256
            pixel_bytes = width * height
        elif image_psm == 0x14:
            palette_entries = 16
            if width * height % 2:
                raise ValueError(f"{name}: odd 4-bit pixel count")
            pixel_bytes = width * height // 2
        else:
            raise ValueError(f"{name}: unsupported image PSM {image_psm:#x}")
        palette_bytes = palette_entries * 4
        expected = 0x40 + palette_bytes + pixel_bytes
        if chunk_size != expected:
            raise ValueError(f"{name}: chunk size {chunk_size} != expected {expected}")
        palette_offset = base + 0x40
        pixel_offset = palette_offset + palette_bytes
        entries.append(
            TmxEntry(
                name=name,
                name_offset=match.start(),
                base_offset=base,
                chunk_size=chunk_size,
                width=width,
                height=height,
                image_psm=image_psm,
                palette_count=palette_count,
                palette_psm=palette_psm,
                palette_offset=palette_offset,
                palette_entries=palette_entries,
                palette_bytes=palette_bytes,
                pixel_offset=pixel_offset,
                pixel_bytes=pixel_bytes,
            )
        )
    return tuple(entries)


def find_tmx_entry(blob: bytes, name: str) -> TmxEntry:
    matches = [entry for entry in iter_tmx_entries(blob) if entry.name == name]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one TMX entry named {name}, found {len(matches)}")
    return matches[0]


def parse_standalone_tmx(blob: bytes, name: str = "standalone.TMX") -> TmxEntry:
    """Parse a TMX file whose single indexed image chunk starts at byte zero."""

    if len(blob) < 0x40 or blob[8:12] != b"TMX0":
        raise ValueError(f"{name}: standalone TMX header is missing")
    ident, chunk_size = struct.unpack_from("<II", blob, 0)
    if ident != 2 or chunk_size != len(blob):
        raise ValueError(f"{name}: standalone file must contain exactly one TMX chunk")
    palette_count = blob[16]
    palette_psm = blob[17]
    width, height = struct.unpack_from("<HH", blob, 18)
    image_psm = blob[22]
    if palette_count != 1 or palette_psm != 0:
        raise ValueError(
            f"{name}: unsupported palette count/PSM {palette_count}/{palette_psm:#x}"
        )
    if image_psm == 0x13:
        palette_entries = 256
        pixel_bytes = width * height
    elif image_psm == 0x14:
        palette_entries = 16
        if width * height % 2:
            raise ValueError(f"{name}: odd 4-bit pixel count")
        pixel_bytes = width * height // 2
    else:
        raise ValueError(f"{name}: unsupported image PSM {image_psm:#x}")
    palette_bytes = palette_entries * 4
    expected = 0x40 + palette_bytes + pixel_bytes
    if chunk_size != expected:
        raise ValueError(f"{name}: chunk size {chunk_size} != expected {expected}")
    return TmxEntry(
        name=name,
        name_offset=-1,
        base_offset=0,
        chunk_size=chunk_size,
        width=width,
        height=height,
        image_psm=image_psm,
        palette_count=palette_count,
        palette_psm=palette_psm,
        palette_offset=0x40,
        palette_entries=palette_entries,
        palette_bytes=palette_bytes,
        pixel_offset=0x40 + palette_bytes,
        pixel_bytes=pixel_bytes,
    )


def _decode_palette(blob: bytes, entry: TmxEntry) -> list[tuple[int, int, int, int]]:
    raw: list[tuple[int, int, int, int]] = []
    for offset in range(entry.palette_offset, entry.palette_offset + entry.palette_bytes, 4):
        r, g, b, a = blob[offset:offset + 4]
        raw.append((r, g, b, _alpha_from_ps2(a)))
    return _swizzle_clut_8(raw) if entry.image_psm == 0x13 else raw


def _decode_indices(blob: bytes, entry: TmxEntry) -> bytes:
    payload = blob[entry.pixel_offset:entry.pixel_offset + entry.pixel_bytes]
    if entry.image_psm == 0x13:
        return payload
    indices = bytearray(entry.width * entry.height)
    for i, value in enumerate(payload):
        indices[2 * i] = value & 0x0F
        indices[2 * i + 1] = value >> 4
    return bytes(indices)


def decode_tmx_rgba(blob: bytes, entry: TmxEntry | str) -> bytes:
    if isinstance(entry, str):
        entry = find_tmx_entry(blob, entry)
    palette = _decode_palette(blob, entry)
    indices = _decode_indices(blob, entry)
    rgba = bytearray(entry.width * entry.height * 4)
    for i, index in enumerate(indices):
        rgba[i * 4:i * 4 + 4] = bytes(palette[index])
    return bytes(rgba)


def _replace_entry_indexed(
    blob: bytes,
    entry: TmxEntry,
    palette: list[tuple[int, int, int, int]],
    indices: bytes,
) -> bytes:
    name = entry.name
    if len(palette) != entry.palette_entries:
        raise ValueError(
            f"{name}: palette needs {entry.palette_entries} entries, got {len(palette)}"
        )
    expected_indices = entry.width * entry.height
    if len(indices) != expected_indices:
        raise ValueError(f"{name}: needs {expected_indices} indices, got {len(indices)}")
    if any(index >= entry.palette_entries for index in indices):
        raise ValueError(f"{name}: palette index exceeds {entry.palette_entries - 1}")

    logical = []
    for color in palette:
        if len(color) != 4 or any(not 0 <= value <= 255 for value in color):
            raise ValueError(f"{name}: invalid RGBA palette entry {color!r}")
        logical.append(tuple(int(value) for value in color))
    stored = _swizzle_clut_8(logical) if entry.image_psm == 0x13 else logical

    palette_bytes = bytearray()
    for r, g, b, a in stored:
        palette_bytes.extend((r, g, b, _alpha_to_ps2(a)))

    if entry.image_psm == 0x13:
        pixel_bytes = indices
    else:
        pixel_bytes = bytes(
            (indices[i] & 0x0F) | ((indices[i + 1] & 0x0F) << 4)
            for i in range(0, len(indices), 2)
        )

    if len(palette_bytes) != entry.palette_bytes or len(pixel_bytes) != entry.pixel_bytes:
        raise AssertionError("TMX replacement payload length changed")
    out = bytearray(blob)
    out[entry.palette_offset:entry.palette_offset + entry.palette_bytes] = palette_bytes
    out[entry.pixel_offset:entry.pixel_offset + entry.pixel_bytes] = pixel_bytes
    if len(out) != len(blob):
        raise AssertionError("TMX container size changed")
    return bytes(out)


def replace_tmx_indexed(
    blob: bytes,
    name: str,
    palette: list[tuple[int, int, int, int]],
    indices: bytes,
) -> bytes:
    entry = find_tmx_entry(blob, name)
    out = _replace_entry_indexed(blob, entry, palette, indices)
    if find_tmx_entry(out, name) != entry:
        raise AssertionError("TMX metadata changed while replacing indexed pixels")
    return out


def replace_standalone_tmx_indexed(
    blob: bytes,
    palette: list[tuple[int, int, int, int]],
    indices: bytes,
    *,
    name: str = "standalone.TMX",
) -> bytes:
    entry = parse_standalone_tmx(blob, name)
    out = _replace_entry_indexed(blob, entry, palette, indices)
    if parse_standalone_tmx(out, name) != entry:
        raise AssertionError("Standalone TMX metadata changed while replacing indexed pixels")
    return out
