from __future__ import annotations

from pathlib import Path
import struct
import sys

PATH = Path('/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes')


def take_utf8_codepoints(data: bytes, offset: int, count: int) -> tuple[str, int]:
    start = offset
    seen = 0
    while seen < count:
        if offset >= len(data):
            raise ValueError(f'EOF while reading {count} codepoints at {start:#x}')
        b = data[offset]
        if b < 0x80:
            width = 1
        elif b & 0xE0 == 0xC0:
            width = 2
        elif b & 0xF0 == 0xE0:
            width = 3
        elif b & 0xF8 == 0xF0:
            width = 4
        else:
            raise ValueError(f'invalid UTF-8 lead {b:#x} at {offset:#x}')
        chunk = data[offset:offset + width]
        if len(chunk) != width:
            raise ValueError('truncated UTF-8')
        chunk.decode('utf-8')
        offset += width
        seen += 1
    return data[start:offset].decode('utf-8'), offset


def parse(path: Path) -> list[tuple[str, str, int]]:
    data = path.read_bytes()
    offset = 0
    rows: list[tuple[str, str, int]] = []
    while offset < len(data):
        record_offset = offset
        if offset + 4 > len(data):
            raise ValueError(f'trailing bytes at {offset:#x}')
        key_chars = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        if key_chars > 100000:
            raise ValueError(f'implausible key char count {key_chars} at {record_offset:#x}')
        key, offset = take_utf8_codepoints(data, offset, key_chars)
        if offset + 4 > len(data):
            raise ValueError(f'missing value length after {record_offset:#x}')
        value_chars = struct.unpack_from('<I', data, offset)[0]
        offset += 4
        if value_chars > 100000:
            raise ValueError(f'implausible value char count {value_chars} at {record_offset:#x}')
        value, offset = take_utf8_codepoints(data, offset, value_chars)
        rows.append((key, value, record_offset))
    return rows


def main() -> None:
    rows = parse(PATH)
    print(f'parsed_records={len(rows)} file_size={PATH.stat().st_size}')
    for key, value, offset in rows[:20]:
        print(f'{offset:08x} {key!r} -> {value!r}')

    queries = sys.argv[1:] or ['H.A.N.T', 'HANT', 'Status', 'Item', 'Mail', 'Memo', 'Map', 'System', 'Save', 'Load']
    for query in queries:
        q = query.casefold()
        matches = [(k, v, o) for k, v, o in rows if q in k.casefold() or q in v.casefold()]
        print(f'\n== {query!r}: {len(matches)} matches ==')
        for key, value, offset in matches[:200]:
            print(f'{offset:08x} {key!r} -> {value!r}')


if __name__ == '__main__':
    main()
