from pathlib import Path
import json

root = Path.home() / "repos/kowloon-recharge-translation/fixtures/DG00_00"
raw = (root / "original.KSF").read_bytes()
obj = json.loads((root / "en.ksfdc.json").read_text())
print("ksf_size", len(raw))
for key, value in sorted(zip(obj["keys"], obj["values"])):
    print("KEY", key, repr(value))
    print("HEX", raw[key-32:key+128].hex(" "))
    print("TEXT", repr(raw[key:key+96].decode("cp932", "backslashreplace")))
