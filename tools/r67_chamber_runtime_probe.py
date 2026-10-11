"""Read-only PCSX2 PINE proof of the live Chamber text owner and glyph positions.

This is a diagnostic, not a game patch. The previous r67.14f/g/h binaries
changed different native font-layout stages yet produced missing/out-of-bubble
text. Static checks do not prove which function actually ran. Inspect active
EE RAM while the *automatic old-man comment* is on screen, before proposing
another renderer mutation. No PINE writes, state loading, or PCSX2 launch.
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import zipfile
from pathlib import Path

CALLSITES = (0x1661BC, 0x16628C, 0x189ED8, 0x18E004)
SOURCE_PTR_RECORDS = (0x4D33B8, 0x4D33BC, 0x4D33C8)
KNOWN_OFFICIAL_PTRS = (0x92D0C8, 0x92D104, 0x92D140)
TASK_ADDRESS = 0xE11C80  # previously recorded chamber task; may vary
EE_SIZE = 0x2000000
NODE_LIMIT = 48

class StateMemory:
    def __init__(self, state: Path):
        with zipfile.ZipFile(state) as z:
            self.ee = z.read("eeMemory.bin")
        if len(self.ee) != EE_SIZE:
            raise ValueError("Unexpected EE memory size")
    def read32(self, address: int) -> int:
        if not 0 <= address <= EE_SIZE - 4 or address % 4:
            raise ValueError(f"EE pointer out of range: {address:#x}")
        return struct.unpack_from("<I", self.ee, address)[0]

class LiveMemory:
    """PINE op 2 = Read32. NEVER sends Read/Write other than Read32."""
    READ32 = 0x02
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
    def read32(self, address: int) -> int:
        if not 0 <= address <= EE_SIZE - 4 or address % 4:
            raise ValueError(f"EE pointer out of range: {address:#x}")
        payload = bytes((self.READ32,)) + struct.pack("<I", address)
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
            conn.settimeout(3.0)
            conn.connect(str(self.socket_path))
            conn.sendall(struct.pack("<I", len(payload)+4) + payload)
            count_data = recv_exact(conn, 4)
            count = struct.unpack("<I", count_data)[0]
            if count != 9:
                raise RuntimeError(f"Unexpected PINE response size: {count}")
            response = recv_exact(conn, 5)
        if response[0] != 0:
            raise RuntimeError(f"PINE failed Read32({address:#x}): {response.hex()}")
        return struct.unpack("<I", response[1:])[0]

def recv_exact(sock: socket.socket, count: int) -> bytes:
    parts = []
    while count:
        part = sock.recv(count)
        if not part:
            raise ConnectionError("PINE closed response prematurely")
        parts.append(part)
        count -= len(part)
    return b"".join(parts)

def f32(value: int) -> float:
    return struct.unpack("<f", struct.pack("<I", value))[0]

def plausible(address: int) -> bool:
    return 0x800000 <= address <= EE_SIZE - 0x130 and address % 4 == 0

def describe_text(reader, owner_address: int) -> dict:
    result = {"owner": hex(owner_address), "font": None, "nodes": []}
    if not plausible(owner_address):
        result["error"] = "owner pointer absent/out of EE range"
        return result
    font = reader.read32(owner_address + 0x3C)
    result["font"] = hex(font)
    if not plausible(font):
        result["error"] = "font pointer absent/out of EE range"
        return result
    result["font_origin_x"] = f32(reader.read32(font + 0x14))
    result["font_origin_y"] = f32(reader.read32(font + 0x18))
    result["orientation_low_byte"] = reader.read32(font + 0x24) & 0xFF
    result["font_scale_x"] = f32(reader.read32(font + 0x48))
    result["font_scale_y"] = f32(reader.read32(font + 0x4C))
    node = reader.read32(font + 0x04)
    seen = set()
    for _ in range(NODE_LIMIT):
        if not node:
            break
        if not plausible(node) or node in seen:
            result["node_walk_stopped"] = "invalid or cyclic pointer"
            break
        seen.add(node)
        tag = reader.read32(node)
        item = {"address": hex(node), "tag": hex(tag)}
        if tag >> 16 == 0xEA:
            item.update(x=f32(reader.read32(node+0x10)),
                        y=f32(reader.read32(node+0x14)))
        result["nodes"].append(item)
        node = reader.read32(node+0x120)
    if node and len(result["nodes"]) == NODE_LIMIT:
        result["node_walk_stopped"] = "cap reached"
    return result

def snapshot(reader, task: int = TASK_ADDRESS) -> dict:
    sites = {hex(site): hex(reader.read32(site)) for site in CALLSITES}
    pointers = [reader.read32(address) for address in SOURCE_PTR_RECORDS]
    result = {
        "status": "DIAGNOSTIC_ONLY_NOT_RUNTIME_ACCEPTANCE",
        "callsite_words": sites,
        "source_pointers": [hex(ptr) for ptr in pointers],
        "official_source_ptrs_match": tuple(pointers) == KNOWN_OFFICIAL_PTRS,
        "task": hex(task),
        "comment_index": None,
        "comment_line": None,
        "text_owners": [],
    }
    if not plausible(task):
        result["task_warning"] = "provisional task address invalid"
        return result
    result["comment_index"] = reader.read32(task+0x04) & 0xFFFF
    result["comment_line"] = (reader.read32(task+0x08) >> 16) & 0xFFFF
    for offset in (0x28, 0x2C):
        owner = reader.read32(task+offset)
        value = describe_text(reader, owner)
        value["task_offset"] = hex(offset)
        result["text_owners"].append(value)
    return result

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--socket", type=Path, help="existing active PCSX2 PINE socket; read-only")
    g.add_argument("--state", type=Path, help="existing savestate for OFFLINE reference only")
    p.add_argument("--task", type=lambda s:int(s,0), default=TASK_ADDRESS)
    p.add_argument("--output", type=Path, required=True)
    args=p.parse_args()
    if args.output.exists():
        raise FileExistsError("Refusing overwrite of existing runtime diagnostic")
    reader=LiveMemory(args.socket) if args.socket else StateMemory(args.state)
    result=snapshot(reader,args.task)
    result["source"]="live_pine_read_only" if args.socket else "saved_state_not_live"
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("Diagnostic written:",args.output,"source:",result["source"])

if __name__ == "__main__":
    main()
