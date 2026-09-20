from pathlib import Path
import json
import re

root = Path.home() / "repos/kowloon-recharge-translation/fixtures/DG00_00"
raw = (root / "original.KSF").read_bytes()
obj = json.loads((root / "en.ksfdc.json").read_text())

for key, value in sorted(zip(obj["keys"], obj["values"])):
    end = key
    while end < len(raw) and raw[end] != 0:
        end += 1
    source = raw[key:end]
    single = re.sub(r" +", " ", value).encode("ascii")
    print(f"key={key} source_bytes={len(source)} first_nul={end} official_ascii_bytes={len(single)} EN={value!r}")
    print("  source", repr(source.decode("cp932", "replace")))
    print("  around")
    for pos in range(key - 4, key + 44):
        print(f"    {pos}: {raw[pos]:02x}")
