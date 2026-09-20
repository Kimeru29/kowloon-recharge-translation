from pathlib import Path
import json
import struct

root = Path.home() / "repos/kowloon-recharge-translation/fixtures/DG00_00"
raw = (root / "original.KSF").read_bytes()
obj = json.loads((root / "en.ksfdc.json").read_text())
for key, value in sorted(zip(obj["keys"], obj["values"])):
    patterns = {
        "u16le": struct.pack("<H", key),
        "u16be": struct.pack(">H", key),
        "u32le": struct.pack("<I", key),
        "u32be": struct.pack(">I", key),
    }
    print(f"key={key} EN={value!r}")
    for name, pattern in patterns.items():
        hits = []
        start = 0
        while True:
            pos = raw.find(pattern, start)
            if pos < 0:
                break
            if pos != key:
                hits.append(pos)
            start = pos + 1
        print(f"  {name}: {hits}")
