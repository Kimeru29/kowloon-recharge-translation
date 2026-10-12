"""Bounded, text-only r67.14y inspection/save transform.

Accepts t/x-derived ELFs with unrelated dialogue edits and appended helpers.
Only registered data pointer words and PT_LOAD.p_filesz may change. No native
instructions, atlas, card, serialization, original strings or geometry change.
Five warning rows equal the pristine native warning's row count; this is NOT
pixel/line-pitch or gameplay acceptance. Main owns the separate button atlas.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import struct
import unicodedata

from tools.localization import encode_ps2_english
from tools.memory_card_ui import MEMORY_CARD_MESSAGES, encode_memory_card_english

FO, VA, RESERVE, BIAS = 0x803150, 0x902F00, 0x100000, 0xFFF80
CORPUS_SHA256 = "b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b"
CORPUS_PATH = "/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes"
BREAK = "＠改行".encode("cp932")
EMPTY = 0x795B9C
SNAKES = (0x58A2C0, 0x58A4B0, 0x58B1C0, 0x58B1E0, 0x5910D0, 0x591EC0, 0x592A30)
RECORDS = {
    0x58A120: (0x94EED0, 0x94EEF2, 0x94EF44, 0x963090, EMPTY, 0x959B5C),
    0x590FF0: (0x94EED0, 0x94EEF2, 0x959BBA, 0x68AF78, EMPTY, 0x959B5C),
    **{o: (0x94EE0C, 0x94F0A8, 0x94F0E8, EMPTY, EMPTY, 0x959BA2) for o in SNAKES[:4]},
    **{o: (0x94EE0C, 0x94F0A8, 0x691030, EMPTY, EMPTY, 0x959BA2) for o in (0x5910D0, 0x592A30)},
    0x591EC0: (0x94EE0C, 0x94F0A8, 0x691E00, 0x691E20, EMPTY, 0x959BA2),
    0x58FD60: (0x94EE24, 0x68FCB0, EMPTY, EMPTY, EMPTY, 0x68FCC8),
    0x592CB0: (0x94EE24, 0x692C10, EMPTY, EMPTY, EMPTY, 0x68FCC8),
}


@dataclass(frozen=True)
class Field:
    key: str
    owners: tuple[int, ...]
    pointer: int
    before: str
    replacement: str
    japanese: str
    official_english: str | None
    official_offset: int | None
    provenance: str = "official_semantic_compaction"
    native_source: bool = False
    max_cells: int = 21
    max_rows: int = 1

    def preimage(self) -> bytes:
        if self.native_source:
            return self.before.encode("cp932")
        return encode_memory_card_english(self.before)


FIELDS = (
    Field("anubis_title", (0x58A120, 0x590FF0), 0x94EED0, "Statue of Anubis", "Anubis Statue", "アヌビスの像", "Statue of Anubis", 0xC4EE9, max_cells=14),
    Field("anubis_description", (0x58A124, 0x590FF4), 0x94EEF2, "　Ancient Egyptian god of the underworld.", "Egyptian death god.", "　古代エジプトの冥界の神アヌビスの石像。", "　Ancient Egyptian god of the underworld.", 0xC4F13),
    Field("anubis_fixed_base", (0x58A128,), 0x94EF44, "　The base is fixed in position.", "Base is fixed.", "　底面が固定されている。", "　The base is fixed in position.", 0xC4F81),
    Field("anubis_unusable", (0x58A12C,), 0x963090, "Cannot use.", "Cannot use.", "　動作不可。", "　Cannot be interacted with.", 0xC4FCE),
    Field("anubis_mechanism", (0x590FF8,), 0x959BBA, "　Machine on base identified.", "Mechanism in base.", "　底面に機械構造を確認。", "　Machine on base identified.", 0xCC529),
    Field("anubis_usable", (0x590FFC,), 0x68AF78, "　動作可能。", "Can be used.", "　動作可能。", "　Can be interacted with.", 0xC6067, native_source=True),
    Field("anubis_reading", (0x58A134, 0x591004), 0x959B5C, "Statue of Anubis", "", "アヌビスのぞう", "Statue of Anubis", 0xC5005, "suppress_duplicate_reading", max_cells=14),
    Field("snake_title", SNAKES, 0x94EE0C, "Snake Staff", "Snake Staff", "蛇の杖", "Snake Staff", 0xC522B, "official_exact", max_cells=14),
    Field("snake_description", tuple(o+4 for o in SNAKES), 0x94F0A8, "　Staff in the shape of a snake.", "Snake-shaped staff.", "　蛇の形をした杖。", "　Staff in the shape of a snake.", 0xC5247),
    Field("snake_moving", tuple(o+8 for o in SNAKES[:4]), 0x94F0E8, "　Movable exterior part identified.", "Moving part found.", "　外部への動作構造を確認。", "　Movable exterior part identified.", 0xC528B),
    Field("snake_fixed", (0x5910D8, 0x592A38), 0x691030, "　稼動部が固定されている。", "Moving part fixed.", "　稼動部が固定されている。", "　The mobile part is fixed in place.", 0xCC66E, native_source=True),
    Field("snake_broken", (0x591EC8,), 0x691E00, "　動力連結部が破損。", "Connector damaged.", "　動力連結部が破損。", "　Engine connector damaged.", 0xCCEFD, native_source=True),
    Field("snake_wire", (0x591ECC,), 0x691E20, "　『ワイヤー』にて修復可能。", "Repair with Wire.", "　『ワイヤー』にて修復可能。", "　Can be fixed with Wire.", 0xCCF3F, native_source=True),
    Field("snake_reading", tuple(o+20 for o in SNAKES), 0x959BA2, "Snake Staff", "", "へびのつえ", "@D", 0xC52DE, "official_deleted_reading", max_cells=14),
    Field("heaven_title", (0x58FD60, 0x592CB0), 0x94EE24, "Heaven Door", "Heaven Door", "天の扉", "Heaven Door", 0xCBB70, "official_exact", max_cells=14),
    Field("heaven_soul", (0x58FD64,), 0x68FCB0, "　魂を記憶する石。", "Records the soul.", "　魂を記憶する石。", "　Stone that records the soul.", 0xCBB8C, native_source=True),
    Field("heaven_surface", (0x592CB4,), 0x692C10, "　地上へと導く石。", "Leads to the surface.", "　地上へと導く石。", None, None, "authored_from_native_no_exact_PS4_key", True),
    Field("heaven_reading", (0x58FD74, 0x592CC4), 0x68FCC8, "てんのとびら", "", "てんのとびら", "Heaven Door", 0xCBBCE, "suppress_duplicate_reading", True, 14),
    Field("action_grasp", (0x594F84, 0x594F88), 0x795EB0, "つかむ", "Grasp", "つかむ", "Grasp", 0xD0B41, "official_exact", True, 10),
    Field("action_record", (0x594FB0,), 0x694EF0, "記録する", "Record", "記録する", "Record", 0xD0BF3, "official_exact", True, 10),
    Field("saving_warning", (0x407460,), 0x929EBE, MEMORY_CARD_MESSAGES[8][2], "\nSaving...\nDo not remove/insert\nmemory card (PS2) or\nturn off the power.", "\nセーブ中・・・＠改行メモリーカード（ＰＳ２）の抜き差しや＠改行電源を切らないでください", "\nSaving...＠改行Do not remove or reinsert the＠改行memory card (PS2) or turn off the power.", 0xC1CD2, max_rows=5),
    Field("save_complete", (0x407464,), 0x929F6E, MEMORY_CARD_MESSAGES[9][2], "\n\nData saved.", MEMORY_CARD_MESSAGES[9][1], "＠改行＠改行Data saved.", 0xC13CE, "official_exact", max_rows=3),
    Field("save_prompt", (0x407488,), 0x92A2E6, MEMORY_CARD_MESSAGES[18][2], "\n\nSave this data?", MEMORY_CARD_MESSAGES[18][1], "＠改行＠改行Save this data?", 0xC188A, "official_exact", max_rows=3),
    Field("dialog_yes", (0x338A80,), 0x793488, "はい", "Yes", "はい", "Yes", 0x223D6, "official_exact", True, 4),
    Field("dialog_no", (0x338A84,), 0x793490, "いいえ", "No", "いいえ", "No", 0x223E7, "official_exact", True, 4),
    Field("dialog_save", (0x338A88,), 0x793498, "セーブ", "Save", "セーブ", "Save", 0x223FA, "official_exact", True, 4),
    Field("dialog_load", (0x338A8C,), 0x7934A0, "ロード", "Load", "ロード", "Load", 0x2240F, "official_exact", True, 4),
)
REPLACEMENTS = {field.key: field.replacement for field in FIELDS}
# H_MSG dialog copies all four pointer bits through COP1 into stack+70..7c.
# These are data loads, not text or geometry instructions to be patched.
CONTEXTS = {
    0x2D8: (0x3C020044, 0xC4438A00, 0x3C020044, 0xC4428A04,
            0x3C020044, 0xC4418A08, 0x3C020044, 0xC4408A0C,
            0xE7A30070, 0xE7A20074, 0xE7A10078, 0xE7A0007C),
    0x7969C: (0x3C020050, 0x8C4773E0, 0x0C040468, 0),
    0x79A30: (0x3C020050, 0x8C4773E4),
    0x7AE10: (0x3C020050, 0x8C477408, 0x0C040468, 0),
    0x19B320: (0x3C020069, 0x24424F00),
}
NATIVE_SAVE_CODE_RANGE = (0x77600, 0x7DA00)


def validate_lines(lines: tuple[str, ...], *, max_cells: int, max_rows: int) -> list[int]:
    """Bound explicit native rows; prohibit controls, kana, tabs and silent wrap."""
    if not 1 <= len(lines) <= max_rows:
        raise ValueError(f"row count {len(lines)} exceeds {max_rows}")
    sizes = []
    for line in lines:
        if any(not 0x20 <= ord(c) <= 0x7E for c in line):
            raise ValueError("English rows must contain printable ASCII only")
        if len(line) > max_cells:
            raise ValueError(f"line has {len(line)} cells, maximum {max_cells}")
        if len(encode_ps2_english(line, collapse_spaces=False)) != 2 * len(line):
            raise ValueError("unexpected glyph encoding")
        sizes.append(len(line))
    return sizes


def validate_encoded(data: bytes, *, max_cells: int, max_rows: int) -> list[int]:
    """Validate actual pointed-to bytes, including future translation mutations."""
    rows = data.split(BREAK)
    decoded = []
    for row in rows:
        try:
            text = row.decode("cp932")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid CP932 glyph") from exc
        if len(row) != len(text) * 2:
            raise ValueError("non-full-width glyph or embedded control")
        ascii_text = unicodedata.normalize("NFKC", text).replace("’", "'")
        if encode_ps2_english(ascii_text, collapse_spaces=False) != row:
            raise ValueError("noncanonical English glyph")
        decoded.append(ascii_text)
    return validate_lines(tuple(decoded), max_cells=max_cells, max_rows=max_rows)


def _header(raw: bytes) -> None:
    if len(raw) < FO or raw[:6] != b"\x7fELF\x01\x01":
        raise ValueError("not the supported PS2 ELF")
    typ, fo, va, pa, size, reserve, flags, align = struct.unpack_from("<8I", raw, 0x54)
    if (typ, fo, va, pa, reserve, flags, align) != (1, FO, VA, VA, RESERVE, 7, 16) or fo+size != len(raw) or size > reserve:
        raise ValueError("translation segment layout/reservation mismatch")


def _string(raw: bytes, ptr: int) -> bytes:
    if VA <= ptr < VA + len(raw) - FO:
        pos, limit = FO + ptr - VA, len(raw)
    elif 0x100000 <= ptr < 0x799180:
        pos, limit = ptr - BIAS, 0x699200
    else:
        raise ValueError(f"string pointer outside file-backed segments: {ptr:#x}")
    end = raw.find(b"\0", pos, min(pos+512, limit))
    if end < 0:
        raise ValueError(f"unterminated string {ptr:#x}")
    return raw[pos:end]


def read_owner(raw: bytes, owner: int) -> bytes:
    if owner < 0 or owner+4 > len(raw):
        raise ValueError("owner out of bounds")
    return _string(raw, struct.unpack_from("<I", raw, owner)[0])


def validate_result(raw: bytes) -> dict:
    _header(raw)
    for record, pointers in RECORDS.items():
        for i in range(6):
            data = read_owner(raw, record+i*4)
            validate_encoded(data, max_cells=14 if i in (0, 5) else 21, max_rows=1)
            if pointers[i] == EMPTY and data:
                raise ValueError("original empty object row changed")
    for field in FIELDS:
        for owner in field.owners:
            validate_encoded(read_owner(raw, owner), max_cells=field.max_cells, max_rows=field.max_rows)
    cells = validate_encoded(read_owner(raw, 0x407460), max_cells=21, max_rows=5)
    if len(cells) != 5 or cells[0] != 0:
        raise ValueError("saving warning must preserve native five-row shape")
    return {"object_records": len(RECORDS), "save_warning_row_cells": cells,
            "max_object_body_cells": 21, "max_title_cells": 14,
            "native_pitch_and_geometry_unchanged": True, "runtime_verified": False}


def apply(source: bytes) -> tuple[bytes, dict]:
    """Fail closed at owned preimages, retaining unrelated t/x/y source bytes."""
    _header(source)
    for marker in (b"SLPM-66511", b"BISLPM-66511Save"):
        if marker not in source:
            raise ValueError("native game/save identity missing")
    for off, words in CONTEXTS.items():
        if struct.unpack_from(f"<{len(words)}I", source, off) != words:
            raise ValueError(f"native owner context drift at {off:#x}")
    for off, pointers in RECORDS.items():
        if struct.unpack_from("<6I", source, off) != pointers:
            raise ValueError(f"object record preimage drift at {off:#x}")
    if _string(source, EMPTY):
        raise ValueError("native empty row sentinel drift")
    # Direct original save strings remain intact. Proven h_mcard callers load
    # the table above; no sweeping translation of dormant Japanese literals.
    for index in (8, 9, 18):
        off, jp, _ = MEMORY_CARD_MESSAGES[index]
        if _string(source, off+BIAS) != jp.encode("cp932"):
            raise ValueError(f"native save source drift, entry {index}")
    original_rows = len(MEMORY_CARD_MESSAGES[8][1].split("＠改行"))
    if original_rows != 5:
        raise ValueError("native saving warning row topology drift")
    seen = set()
    for field in FIELDS:
        for owner in field.owners:
            if owner in seen or struct.unpack_from("<I", source, owner)[0] != field.pointer:
                raise ValueError(f"pointer preimage drift: {field.key}/{owner:#x}")
            seen.add(owner)
            if read_owner(source, owner) != field.preimage():
                raise ValueError(f"text preimage drift: {field.key}/{owner:#x}")
        validate_lines(tuple(REPLACEMENTS[field.key].split("\n")), max_cells=field.max_cells, max_rows=field.max_rows)

    result = bytearray(source)
    allowed = [(0x64, 0x68)]
    owners = []
    interned: dict[bytes, int] = {}
    for field in FIELDS:
        text = REPLACEMENTS[field.key]
        payload = encode_memory_card_english(text)
        validate_encoded(payload, max_cells=field.max_cells, max_rows=field.max_rows)
        changed = payload != field.preimage()
        pointer = field.pointer
        if changed:
            if payload not in interned:
                result.extend(b"\0" * (len(result) & 1))
                interned[payload] = VA + len(result) - FO
                result.extend(payload+b"\0")
            pointer = interned[payload]
            for owner in field.owners:
                struct.pack_into("<I", result, owner, pointer)
                allowed.append((owner, owner+4))
        owners.append({"key": field.key, "owner_offsets": list(field.owners),
                       "old_pointer": field.pointer, "new_pointer": pointer, "changed": changed,
                       "english": text, "source_japanese": field.japanese,
                       "official_english": field.official_english,
                       "official_record_offset": field.official_offset,
                       "provenance": field.provenance,
                       "cell_counts": validate_encoded(payload, max_cells=field.max_cells, max_rows=field.max_rows)})
    if len(result)-FO > RESERVE:
        raise ValueError("translation segment reservation exhausted")
    struct.pack_into("<I", result, 0x64, len(result)-FO)
    permitted = {i for lo, hi in allowed for i in range(lo, hi)}
    modified = [i for i, (a, b) in enumerate(zip(source, result)) if a != b]
    if set(modified) - permitted:
        raise ValueError("unexpected mutation outside registered pointer owners")
    output = bytes(result)
    bounds = validate_result(output)
    lo, hi = NATIVE_SAVE_CODE_RANGE
    if output[lo:hi] != source[lo:hi]:
        raise ValueError("native save code changed")
    sha = lambda b: hashlib.sha256(b).hexdigest()
    return output, {
        "release": "r67.14y", "status": "DIAGNOSTIC_TEXT_ONLY_REQUIRES_RUNTIME_ACCEPTANCE",
        "source_sha256": sha(source), "result_sha256": sha(output),
        "old_elf_size": len(source), "new_elf_size": len(output),
        "appended_bytes": len(output)-len(source), "appended_range": [len(source), len(output)],
        "changed_source_offsets": modified, "allowed_source_ranges": sorted(allowed),
        "owners": owners, "bounds": bounds, "corpus_path": CORPUS_PATH,
        "corpus_sha256": CORPUS_SHA256, "native_save_code_range": [lo, hi],
        "native_save_code_sha256": sha(source[lo:hi]), "native_save_code_unchanged": True,
        "all_native_instructions_unchanged": True, "native_original_warning_rows": original_rows,
        "native_line_pitch_changed": False, "runtime_verified": False,
        "limitations": ["Static row/cell containment; native pixel pitch and gameplay not verified.",
                        "Save/Back footer atlas belongs to the independent main-agent patch.",
                        "Any Japanese prompt persisting after table/dialog/atlas fixes needs runtime owner tracing.",
                        "Heaven surface description has no exact key in the audited PS4 corpus.",
                        "Shared Grasp/Record and Yes/No/Save/Load labels affect their other native consumers too."],
    }
