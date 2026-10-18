"""r67.15j: relocate exact official H_Item and dungeon action labels.

Only registered pointer words and PT_LOAD.p_filesz change in the existing ELF.
Japanese source strings, native action IDs, callers, and sentinel slots remain
immutable. Layout acceptance belongs to the shared native geometry wrapper.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
from pathlib import Path

from tools.inspect_english_bytes import parse
from tools.localization import encode_ps2_english
from tools.r67_14t_stone_tablet_fit import read_string


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = Path(
    "/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"
)
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
APPEND_FILE_OFFSET = 0x803150
APPEND_VA = 0x902F00
APPEND_RESERVE = 0x100000
ELF_BIAS = 0xFFF80
PT_LOAD_FILESIZE_OFFSET = 0x64
EMPTY_POINTER = 0x795B9C


@dataclass(frozen=True)
class ActionLabel:
    key: str
    owner: int
    source_japanese: str
    english: str | None
    official_offset: int | None
    source_pointer: int | None
    patch: bool = True
    existing_native_english: str | None = None

    @property
    def english_native(self) -> str | None:
        if self.english is None:
            return None
        return encode_ps2_english(self.english, collapse_spaces=False).decode("cp932")


# Index is the native H_Item action ID. IDs 1 and 3 are already translated by
# 15e/15d and must remain pointer- and string-identical.
H_ITEM_ACTIONS = (
    ActionLabel("swap", 0x386320, "交換", "Swap", 0x461D2, 0x793660),
    ActionLabel("cant", 0x386324, "禁止", "Can't", 0x461E4, None, False, "Ｃａｎ’ｔ"),
    ActionLabel("use", 0x386328, "使う", "Use", 0x461F7, 0x793670),
    ActionLabel("compound", 0x38632C, "調合", "Compound", 0x46208, None, False,
                "Ｃｏｍｐｏｕｎｄ"),
    ActionLabel("reload", 0x386330, "リロード", "Reload", 0x4621E, 0x486258),
    ActionLabel("not_usable", 0x386334, "使用不可", "Not usable", 0x46238, 0x486268),
    ActionLabel("drink", 0x386338, "飲む", "Drink", 0x46256, 0x793680),
    ActionLabel("drink_emphatic", 0x38633C, "飲む！", "Drink!", 0x46269, 0x793688),
    ActionLabel("eat", 0x386340, "食べる", "Eat", 0x46280, 0x793690),
    ActionLabel("eat_emphatic", 0x386344, "食べる！", "Eat!", 0x46294, 0x486278),
    ActionLabel("lick", 0x386348, "なめる", "Lick", 0x462AC, 0x793698),
    ActionLabel("charge", 0x38634C, "充電", "Charge", 0x462C1, 0x7936A0),
    ActionLabel("cure", 0x386350, "治療", "Cure", 0x462D5, 0x7936A8),
    ActionLabel("use_item", 0x386354, "使用", "Use", 0x462E7, 0x7936B0),
    ActionLabel("room_storage", 0x386358, "自室収納", "Room storage", 0x462F8, 0x486288),
    ActionLabel("place", 0x38635C, "置く", "Place", 0x46318, 0x7936B8),
)

# Every live text pointer in the dungeon option block, including aliases. The
# two 0x795B9C entries are explicit empty sentinels; 0x594FBC is native-only
# Japanese because the official corpus has no exact key for 入る.
DUNGEON_ACTIONS = (
    ActionLabel("grasp_primary", 0x594F84, "つかむ", "Grasp", 0xD0B41, None,
                False, "Ｇｒａｓｐ"),
    ActionLabel("grasp_alias", 0x594F88, "つかむ", "Grasp", 0xD0B41, None,
                False, "Ｇｒａｓｐ"),
    ActionLabel("take", 0x594F8C, "取る", "Take", 0xD0B57, 0x795EB8),
    ActionLabel("open_a", 0x594F90, "開く", "Open", 0xD0B69, None, False, "Ｏｐｅｎ"),
    ActionLabel("open_b", 0x594F94, "開く", "Open", 0xD0B69, None, False, "Ｏｐｅｎ"),
    ActionLabel("unlock", 0x594F98, "開錠", "Unlock", 0xD0B7B, 0x795EC8),
    ActionLabel("use_item", 0x594FA0, "アイテムを使う", "Use Item", 0xD0B8F,
                None, False, "Ｕｓｅ　Ｉｔｅｍ"),
    ActionLabel("return_above", 0x594FA4, "地上へ帰還する", "Return Above", 0xD0BB4,
                0x694EE0),
    ActionLabel("touch_a", 0x594FA8, "触れる", "Touch", 0xD0BDD, 0x795ED0),
    ActionLabel("open_c", 0x594FAC, "開く", "Open", 0xD0B69, None, False, "Ｏｐｅｎ"),
    ActionLabel("record", 0x594FB0, "記録する", "Record", 0xD0BF3, None,
                False, "Ｒｅｃｏｒｄ"),
    ActionLabel("touch_b", 0x594FB4, "触れる", "Touch", 0xD0BDD, 0x795ED0),
    ActionLabel("enter_unresolved", 0x594FBC, "入る", None, None, 0x795ED8, False),
)

SENTINELS = {0x594F80: EMPTY_POINTER, 0x594F9C: EMPTY_POINTER}
_ALL_SPECS = (*H_ITEM_ACTIONS, *DUNGEON_ACTIONS)
ALLOWED_SOURCE_RANGES = {
    f"h_item_action_{spec.key}": ((spec.owner, spec.owner + 4),)
    for spec in H_ITEM_ACTIONS if spec.patch
}
ALLOWED_SOURCE_RANGES.update({
    f"dungeon_action_{spec.key}": ((spec.owner, spec.owner + 4),)
    for spec in DUNGEON_ACTIONS if spec.patch
})


def _validate_segment(source: bytes) -> None:
    if source[:4] != b"\x7fELF":
        raise ValueError("source is not an ELF image")
    phoff = struct.unpack_from("<I", source, 0x1C)[0]
    entry_size, count = struct.unpack_from("<HH", source, 0x2A)
    if entry_size != 32 or phoff + count * entry_size > len(source):
        raise ValueError("program-header table is invalid")
    for index in range(count):
        offset = phoff + index * entry_size
        kind, file_offset, va, _pa, file_size, memory_size = struct.unpack_from(
            "<6I", source, offset
        )
        if kind != 1 or file_offset != APPEND_FILE_OFFSET:
            continue
        if va != APPEND_VA or file_size != len(source) - APPEND_FILE_OFFSET:
            raise ValueError("translation PT_LOAD ownership or extent changed")
        if memory_size < file_size or file_size > APPEND_RESERVE:
            raise ValueError("translation PT_LOAD exceeds its reserved extent")
        return
    raise ValueError("translation PT_LOAD was not found")


def _corpus_rows() -> dict[str, tuple[str, int]]:
    raw = CORPUS_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CORPUS_SHA256:
        raise ValueError("official English.bytes corpus hash mismatch")
    by_key: dict[str, list[tuple[str, int]]] = {}
    for key, value, offset in parse(CORPUS_PATH):
        by_key.setdefault(key, []).append((value, offset))
    result: dict[str, tuple[str, int]] = {}
    for spec in _ALL_SPECS:
        found = by_key.get(spec.source_japanese, [])
        if spec.english is None:
            if found:
                raise ValueError(f"unexpected official exact match for unresolved {spec.key}")
            continue
        if len(found) != 1 or found[0] != (spec.english, spec.official_offset):
            raise ValueError(f"official exact corpus row mismatch for {spec.key}")
        result[spec.key] = found[0]
    return result


def _read_owner(source: bytes, spec: ActionLabel) -> tuple[int, str]:
    pointer = struct.unpack_from("<I", source, spec.owner)[0]
    if spec.source_pointer is not None and pointer != spec.source_pointer:
        raise ValueError(f"{spec.key} pointer preimage mismatch at {spec.owner:#x}")
    try:
        text = read_string(source, pointer).decode("cp932")
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f"{spec.key} string preimage unreadable at {spec.owner:#x}") from exc
    expected = spec.source_japanese if spec.patch else spec.existing_native_english
    if expected is not None and text != expected:
        raise ValueError(f"{spec.key} string preimage mismatch at {spec.owner:#x}")
    return pointer, text


def _append_text(output: bytearray, english: str) -> int:
    if len(output) & 1:
        output.append(0)
    pointer = APPEND_VA + len(output) - APPEND_FILE_OFFSET
    encoded = encode_ps2_english(english, collapse_spaces=False)
    if not encoded or len(encoded) % 2:
        raise ValueError("official label is not representable in the native two-byte font")
    output.extend(encoded + b"\0")
    return pointer


def build(source: bytes) -> tuple[bytes, dict]:
    """Return a composed ELF with exact official action labels appended."""
    if not isinstance(source, bytes):
        raise TypeError("source must be immutable bytes")
    _validate_segment(source)
    _corpus_rows()

    originals: dict[int, tuple[int, str]] = {}
    for spec in _ALL_SPECS:
        originals[spec.owner] = _read_owner(source, spec)
    for owner, expected in SENTINELS.items():
        if struct.unpack_from("<I", source, owner)[0] != expected:
            raise ValueError(f"dungeon action sentinel changed at {owner:#x}")

    output = bytearray(source)
    patched: list[dict] = []
    for spec in _ALL_SPECS:
        if not spec.patch:
            continue
        assert spec.english is not None and spec.english_native is not None
        pointer = _append_text(output, spec.english)
        struct.pack_into("<I", output, spec.owner, pointer)
        patched.append({
            "key": spec.key,
            "owner": hex(spec.owner),
            "source_japanese": spec.source_japanese,
            "official_english": spec.english,
            "official_record": hex(spec.official_offset),
            "new_pointer": hex(pointer),
            "layout_fit": "pending shared native geometry wrapper",
        })

    while len(output) & 3:
        output.append(0)
    segment_size = len(output) - APPEND_FILE_OFFSET
    if segment_size > APPEND_RESERVE:
        raise ValueError("action labels exceed the translation PT_LOAD reservation")
    struct.pack_into("<I", output, PT_LOAD_FILESIZE_OFFSET, segment_size)

    allowed = {offset for spans in ALLOWED_SOURCE_RANGES.values()
               for start, end in spans for offset in range(start, end)}
    allowed.update(range(PT_LOAD_FILESIZE_OFFSET, PT_LOAD_FILESIZE_OFFSET + 4))
    changed = {offset for offset, (old, new) in
               enumerate(zip(source, output)) if old != new}
    if changed - allowed:
        raise ValueError("unowned source bytes changed during action-label patch")
    result = bytes(output)

    unresolved = [{"owner": hex(spec.owner), "source_japanese": spec.source_japanese,
                   "reason": "no exact Japanese-key match in pinned official corpus"}
                  for spec in DUNGEON_ACTIONS if spec.english is None]
    inventory = [{"owner": hex(spec.owner), "source": spec.source_japanese,
                  "status": "already translated" if not spec.patch and spec.english else
                           "unresolved native source" if spec.english is None else "translated",
                  "official_english": spec.english}
                 for spec in _ALL_SPECS]
    return result, {
        "release": "r67.15j",
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "result_sha256": hashlib.sha256(result).hexdigest(),
        "official_corpus_sha256": CORPUS_SHA256,
        "h_item_action_count": len(H_ITEM_ACTIONS),
        "dungeon_action_owner_count": len(DUNGEON_ACTIONS),
        "reserved_sentinel_owners": {hex(k): hex(v) for k, v in SENTINELS.items()},
        "patched": patched,
        "unresolved": unresolved,
        "inventory": inventory,
        "modified_source_offsets": [hex(x) for x in sorted(changed)],
        "source_bytes_appended": len(result) - len(source),
        "layout_fit": "pending shared native geometry wrapper",
        "runtime_verified": False,
    }
