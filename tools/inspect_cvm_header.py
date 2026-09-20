from __future__ import annotations

from pathlib import Path
import struct
import sys

path = Path(sys.argv[1])
with path.open("rb") as fh:
    raw = fh.read(0x1800)
total_size = path.stat().st_size
payload_size = total_size - 0x1800
sector = 2048
values = {
    "total_size": total_size,
    "payload_size": payload_size,
    "total_sectors": total_size // sector,
    "payload_sectors": payload_size // sector,
    "header_sectors": 0x1800 // sector,
}

print(f"path={path}")
print(f"header_len={len(raw)}")
for name, value in values.items():
    print(f"{name}={value} hex={value:#x}")

print("\nASCII/chunk signatures:")
for offset in range(0, len(raw) - 3):
    chunk = raw[offset:offset+4]
    if all(0x20 <= b <= 0x7E for b in chunk):
        text = chunk.decode('ascii')
        if text.isalpha() or text in {"CVMH", "ZONE", "ROFS", "ISO ", "DATA"}:
            print(f"  {offset:#06x}: {text!r}")

print("\nExact numeric matches (LE/BE u32):")
for name, value in values.items():
    le = struct.pack('<I', value & 0xFFFFFFFF)
    be = struct.pack('>I', value & 0xFFFFFFFF)
    le_hits = [i for i in range(len(raw)-3) if raw[i:i+4] == le]
    be_hits = [i for i in range(len(raw)-3) if raw[i:i+4] == be]
    print(f"  {name}: LE={le_hits} BE={be_hits}")

print("\nNonzero u32 words by 0x800 block (first 80 each):")
for base in range(0, len(raw), 0x800):
    words = []
    for offset in range(base, min(base+0x800, len(raw)), 4):
        value = struct.unpack_from('<I', raw, offset)[0]
        if value:
            words.append((offset, value))
    print(f"block {base:#06x}: nonzero={len(words)}")
    for offset, value in words[:80]:
        printable = raw[offset:offset+4]
        ascii_text = printable.decode('ascii', 'replace')
        print(f"  {offset:#06x}: le={value:#010x} be={struct.unpack('>I', printable)[0]:#010x} bytes={printable.hex(' ')} ascii={ascii_text!r}")
