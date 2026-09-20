from pathlib import Path
import json
import re

root = Path.home() / "repos/kowloon-recharge-translation/fixtures/DG00_00"
data = (root / "original.MTX").read_bytes()
obj = json.loads((root / "en.mtxdc.json").read_text())
pairs = sorted(zip(obj["keys"], obj["values"]))

source_total = 0
dst_double = 0
dst_single = 0
for i, (key, value) in enumerate(pairs):
    next_key = pairs[i + 1][0] if i + 1 < len(pairs) else len(data)
    segment = data[key:next_key]
    if next_key > key and data[next_key - 1:next_key] == b"r":
        end = next_key - 1
    else:
        candidates = [x for x in (segment.find(b"wc"), segment.find(b"}w"), segment.find(b"\x00")) if x >= 0]
        end = key + (min(candidates) if candidates else len(segment))
    source_total += end - key
    dst_double += len(value.encode("cp932"))
    dst_single += len(re.sub(r" {2,}", " ", value).encode("cp932"))

print(f"source_translatable={source_total}")
print(f"official_dc={dst_double} delta={dst_double - source_total}")
print(f"single_space={dst_single} delta={dst_single - source_total}")
print(f"mtx_original={len(data)}")
print(f"projected_official={len(data) - source_total + dst_double}")
print(f"projected_single={len(data) - source_total + dst_single}")
