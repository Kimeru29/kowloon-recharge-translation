from __future__ import annotations

import struct
from typing import Any
from hashlib import sha256

from tools.hant_ui import HANT_ENGLISH_LINES, HANT_POINTER_TABLE_OFFSET
from tools.localization import encode_ps2_english
from tools.memory_card_ui import MEMORY_CARD_MESSAGES, MEMORY_CARD_POINTER_TABLE_OFFSET, encode_memory_card_english
from tools.startup_ui import (
    KEYBOARD_ROW_PATCHES,
    NAME_DEFAULT_POINTER_OFFSETS,
    NAME_PROMPT_POINTER_TABLE_OFFSET,
    NAME_PROMPT_TEXTS,
    NAME_RUNTIME_POINTER_OFFSETS,
    TITLE_LOAD_POINTER_OFFSET,
    TITLE_LOAD_START,
    TITLE_NEW_GAME_START,
    TITLE_POINTER_TABLE_OFFSET,
)

STARTUP_GRAPHICS_PATHS: tuple[str, ...] = (
    "BLBRD/B_GP019.BIN",
    "BLBRD/B_GP088.BIN",
    *(f"BLBRD/INIT_MES/TR{index:03d}.TMX" for index in range(29)),
)

_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_SECOND_PH_OFFSET = 0x54
_TRANSLATION_VADDR = 0x00902F00
_RUNTIME_HEAP_BREAK_OFFSET = 0x650014
_EXPECTED_RUNTIME_HEAP_START = 0x00A02F00
_ADV_PATCH_WORDS = (
    (0x14FA60, 0x80430465),
    (0x14FA68, 0x00031843),
    (0x14FAA4, 0x80440463),
    (0x14FAA8, 0x0080182D),
)
_VISIBLE_PROMPT_INDICES = tuple(range(len(NAME_PROMPT_TEXTS)))


def _check(name: str, ok: bool, detail: str | None = None) -> dict[str, Any]:
    return {"name": name, "ok": bool(ok), "detail": None if ok else detail}


def _main_va_to_file(va: int) -> int:
    return va - _ELF_MAIN_VADDR + _ELF_MAIN_FILE_OFFSET


def _read_wide_at_va(raw: bytes, va: int, expected: str) -> bool:
    payload = encode_ps2_english(expected, collapse_spaces=False) + b"\x00"

    main_offset = _main_va_to_file(va)
    if 0 <= main_offset <= len(raw) - len(payload):
        if raw[main_offset:main_offset + len(payload)] == payload:
            return True

    segment = _translation_segment(raw)
    if segment is None:
        return False
    p_offset, p_vaddr, p_filesz, _p_memsz = segment
    relative = va - p_vaddr
    if relative < 0 or relative + len(payload) > p_filesz:
        return False
    target_file = p_offset + relative
    return raw[target_file:target_file + len(payload)] == payload


def _translation_segment(raw: bytes) -> tuple[int, int, int, int] | None:
    if len(raw) < _SECOND_PH_OFFSET + 32:
        return None
    p_type, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, p_flags, _p_align = struct.unpack_from(
        "<IIIIIIII", raw, _SECOND_PH_OFFSET
    )
    if (
        p_type != 1
        or p_vaddr != _TRANSLATION_VADDR
        or p_filesz <= 0
        or p_memsz < p_filesz
        or p_flags != 6
        or p_offset + p_filesz > len(raw)
    ):
        return None
    return p_offset, p_vaddr, p_filesz, p_memsz


def verify_startup_elf(raw: bytes) -> list[dict[str, Any]]:
    """Verify translated startup renderer classes in a finished SLPM-66511 ELF.

    This intentionally checks runtime indirections rather than merely searching
    for English bytes.  It is usable both on the standalone translated ELF and
    the ELF extracted from the final ISO.
    """

    checks: list[dict[str, Any]] = []
    checks.append(_check("serial", b"SLPM-66511" in raw, "serial missing"))
    checks.append(_check("save_namespace", b"BISLPM-66511Save" in raw, "save namespace missing"))

    new_game = encode_ps2_english("New Game", collapse_spaces=False) + b"\x00"
    load_game = encode_ps2_english("Load Game", collapse_spaces=False) + b"\x00"
    checks.append(
        _check(
            "title_new_game",
            raw[TITLE_NEW_GAME_START:TITLE_NEW_GAME_START + len(new_game)] == new_game,
            "New Game wide text missing",
        )
    )
    checks.append(
        _check(
            "title_load_game",
            raw[TITLE_LOAD_START:TITLE_LOAD_START + len(load_game)] == load_game,
            "Load Game wide text missing",
        )
    )
    if len(raw) >= TITLE_POINTER_TABLE_OFFSET + 8:
        new_ptr, load_ptr = struct.unpack_from("<II", raw, TITLE_POINTER_TABLE_OFFSET)
        checks.append(
            _check(
                "title_new_pointer",
                new_ptr == _ELF_MAIN_VADDR + TITLE_NEW_GAME_START - _ELF_MAIN_FILE_OFFSET,
                f"unexpected New Game pointer {new_ptr:#x}",
            )
        )
        checks.append(
            _check(
                "title_load_pointer",
                load_ptr == _ELF_MAIN_VADDR + TITLE_LOAD_START - _ELF_MAIN_FILE_OFFSET,
                f"unexpected Load Game pointer {load_ptr:#x}",
            )
        )
    else:
        checks.extend((
            _check("title_new_pointer", False, "title pointer table outside ELF"),
            _check("title_load_pointer", False, "title pointer table outside ELF"),
        ))

    for index in _VISIBLE_PROMPT_INDICES:
        pointer_offset = NAME_PROMPT_POINTER_TABLE_OFFSET + index * 4
        ok = False
        detail = "prompt pointer outside ELF"
        if pointer_offset + 4 <= len(raw):
            target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            ok = _read_wide_at_va(raw, target_va, NAME_PROMPT_TEXTS[index])
            detail = f"prompt {index} does not resolve to wide {NAME_PROMPT_TEXTS[index]!r}"
        checks.append(_check(f"name_prompt_{index}", ok, detail))

    for name, pointer_offsets in NAME_DEFAULT_POINTER_OFFSETS.items():
        ok = all(
            offset + 4 <= len(raw)
            and _read_wide_at_va(raw, struct.unpack_from("<I", raw, offset)[0], name)
            for offset in pointer_offsets
        )
        checks.append(_check(f"default_name_{name}", ok, f"default {name} pointer does not resolve to wide text"))
    for name, pointer_offsets in NAME_RUNTIME_POINTER_OFFSETS.items():
        ok = all(
            offset + 4 <= len(raw)
            and _read_wide_at_va(raw, struct.unpack_from("<I", raw, offset)[0], name)
            for offset in pointer_offsets
        )
        checks.append(_check(f"runtime_name_{name}", ok, f"runtime {name} pointer does not resolve to wide text"))

    keyboard_ok = True
    for patch in KEYBOARD_ROW_PATCHES:
        expected = encode_ps2_english(patch.text, collapse_spaces=False)
        if raw[patch.offset:patch.offset + len(expected)] != expected:
            keyboard_ok = False
            break
    checks.append(_check("latin_name_keyboard", keyboard_ok, "one or more keyboard rows are not wide Latin"))

    adv_ok = all(
        offset + 4 <= len(raw) and struct.unpack_from("<I", raw, offset)[0] == expected
        for offset, expected in _ADV_PATCH_WORDS
    )
    checks.append(_check("adv_horizontal_layout", adv_ok, "ADV axis/normalization patch missing"))

    segment = _translation_segment(raw)
    checks.append(_check("translation_segment", segment is not None, "translation PT_LOAD is not active/valid"))
    heap_break_ok = (
        _RUNTIME_HEAP_BREAK_OFFSET + 4 <= len(raw)
        and struct.unpack_from("<I", raw, _RUNTIME_HEAP_BREAK_OFFSET)[0] == _EXPECTED_RUNTIME_HEAP_START
    )
    checks.append(
        _check(
            "runtime_heap_break",
            heap_break_ok,
            "libkernel heap break still overlaps the translation PT_LOAD",
        )
    )
    hant_ok = segment is not None
    if segment is not None:
        p_offset, p_vaddr, p_filesz, _p_memsz = segment
        for index, english in HANT_ENGLISH_LINES.items():
            pointer_offset = HANT_POINTER_TABLE_OFFSET + index * 4
            if pointer_offset + 4 > len(raw):
                hant_ok = False
                break
            target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
            relative = target_va - p_vaddr
            expected = encode_ps2_english(english, collapse_spaces=False) + b"\x00"
            if relative < 0 or relative + len(expected) > p_filesz:
                hant_ok = False
                break
            target_file = p_offset + relative
            if raw[target_file:target_file + len(expected)] != expected:
                hant_ok = False
                break
    checks.append(_check("hant_tutorial", hant_ok, "H.A.N.T pointers do not resolve to translated wide text"))

    for index, (_source_offset, _source, english) in MEMORY_CARD_MESSAGES.items():
        ok = segment is not None
        detail = f"memory-card entry {index} does not resolve to official English"
        if segment is not None:
            p_offset, p_vaddr, p_filesz, _p_memsz = segment
            pointer_offset = MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4
            if pointer_offset + 4 > len(raw):
                ok = False
            else:
                target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
                relative = target_va - p_vaddr
                expected = encode_memory_card_english(english) + b"\x00"
                if relative < 0 or relative + len(expected) > p_filesz:
                    ok = False
                else:
                    target_file = p_offset + relative
                    ok = raw[target_file:target_file + len(expected)] == expected
        checks.append(_check(f"memory_card_{index}", ok, detail))
    return checks


def _sha256_file(path) -> str:
    digest = sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_startup_candidate(candidate, startup_graphics_root) -> dict[str, Any]:
    """Verify the startup acceptance slice from the final ISO bytes."""
    import mmap
    from pathlib import Path

    from tools.cvm import HEADER_SIZE
    from tools.elf_rofs import find_rofs_record
    from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso

    candidate = Path(candidate)
    startup_graphics_root = Path(startup_graphics_root)
    checks: list[dict[str, Any]] = []

    with candidate.open("rb") as handle:
        image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            _, outer_records = index_iso(image)
            elf_record = find_record(outer_records, "SLPM_665.11")
            elf = bytes(
                image[
                    elf_record.extent * SECTOR_SIZE:
                    elf_record.extent * SECTOR_SIZE + elf_record.size
                ]
            )
            checks.extend(verify_startup_elf(elf))

            cvm = find_record(outer_records, "DATA.CVM")
            embedded_base = cvm.extent * SECTOR_SIZE + HEADER_SIZE
            _, embedded_records = index_iso(image, embedded_base)

            graphics_found = 0
            for rel in STARTUP_GRAPHICS_PATHS:
                expected_path = startup_graphics_root / rel
                ok = expected_path.is_file()
                detail = f"missing expected startup overlay {expected_path}"
                if ok:
                    expected = expected_path.read_bytes()
                    try:
                        record = find_record(embedded_records, rel)
                    except ValueError as exc:
                        ok = False
                        detail = str(exc)
                    else:
                        actual = bytes(
                            image[
                                embedded_base + record.extent * SECTOR_SIZE:
                                embedded_base + record.extent * SECTOR_SIZE + record.size
                            ]
                        )
                        ok = actual == expected
                        detail = f"finished payload differs for {rel}"
                        if ok:
                            graphics_found += 1
                        try:
                            find_rofs_record(elf, rel, record.size, record.extent)
                        except ValueError as exc:
                            checks.append(_check(f"rofs_{rel}", False, str(exc)))
                        else:
                            checks.append(_check(f"rofs_{rel}", True))
                checks.append(_check(f"graphics_{rel}", ok, detail))
            checks.append(
                _check(
                    "startup_graphics_count",
                    graphics_found == len(STARTUP_GRAPHICS_PATHS),
                    f"resolved {graphics_found}/{len(STARTUP_GRAPHICS_PATHS)} startup graphics",
                )
            )

            # Keep the structurally repacked title atlas independently visible in
            # acceptance reports even though the whole B_GP088 container is also
            # compared byte-for-byte above.
            from tools.tmx import find_tmx_entry

            gp088_expected_path = startup_graphics_root / "BLBRD/B_GP088.BIN"
            packed_ok = gp088_expected_path.is_file()
            packed_detail = f"missing expected GP088 container {gp088_expected_path}"
            if packed_ok:
                expected_gp088 = gp088_expected_path.read_bytes()
                gp088_record = find_record(embedded_records, "BLBRD/B_GP088.BIN")
                actual_gp088 = bytes(
                    image[
                        embedded_base + gp088_record.extent * SECTOR_SIZE:
                        embedded_base + gp088_record.extent * SECTOR_SIZE + gp088_record.size
                    ]
                )
                try:
                    expected_entry = find_tmx_entry(expected_gp088, "GRP088/GP088_12.TMX")
                    actual_entry = find_tmx_entry(actual_gp088, "GRP088/GP088_12.TMX")
                except ValueError as exc:
                    packed_ok = False
                    packed_detail = str(exc)
                else:
                    expected_chunk = expected_gp088[
                        expected_entry.base_offset:expected_entry.base_offset + expected_entry.chunk_size
                    ]
                    actual_chunk = actual_gp088[
                        actual_entry.base_offset:actual_entry.base_offset + actual_entry.chunk_size
                    ]
                    packed_ok = actual_chunk == expected_chunk
                    packed_detail = "finished GP088_12 packed title differs from generated English atlas"
            checks.append(_check("graphics_gp088_12_packed_title", packed_ok, packed_detail))

            dg00_mtx_record = find_record(embedded_records, "ADV/DG/DG00_00.MTX")
            dg00_mtx = bytes(
                image[
                    embedded_base + dg00_mtx_record.extent * SECTOR_SIZE:
                    embedded_base + dg00_mtx_record.extent * SECTOR_SIZE + dg00_mtx_record.size
                ]
            )
            for text in (
                "Old man's voice",
                "Hey, over here.",
                "Old merchant Salah",
                "This is the Heracleion temple.",
                "First, it would be a good idea to",
                "check H.A.N.T.",
            ):
                encoded = encode_ps2_english(text)
                checks.append(_check(f"dg00_{text}", encoded in dg00_mtx, f"missing DG00 English {text!r}"))
            for japanese in ("老人の声", "おい、こっちだ。"):
                encoded = japanese.encode("cp932")
                checks.append(
                    _check(
                        f"dg00_removed_{japanese}",
                        encoded not in dg00_mtx,
                        f"Japanese DG00 source still present: {japanese}",
                    )
                )
            try:
                find_rofs_record(elf, "ADV/DG/DG00_00.MTX", dg00_mtx_record.size, dg00_mtx_record.extent)
            except ValueError as exc:
                checks.append(_check("rofs_ADV/DG/DG00_00.MTX", False, str(exc)))
            else:
                checks.append(_check("rofs_ADV/DG/DG00_00.MTX", True))

            dg00_ksf_record = find_record(embedded_records, "ADV/DG/DG00_00.KSF")
            dg00_ksf = bytes(
                image[
                    embedded_base + dg00_ksf_record.extent * SECTOR_SIZE:
                    embedded_base + dg00_ksf_record.extent * SECTOR_SIZE + dg00_ksf_record.size
                ]
            )
            for text in ("Look around the area", "Stand here", "Pick up device on the ground", "Say no"):
                checks.append(_check(f"ksf_{text}", text.encode("ascii") in dg00_ksf, f"missing KSF English {text!r}"))

        finally:
            image.close()

    passed = sum(1 for check in checks if check["ok"])
    return {
        "schema_version": 2,
        "candidate": str(candidate),
        "sha256": _sha256_file(candidate),
        "checks_total": len(checks),
        "checks_passed": passed,
        "checks": checks,
    }


def main() -> int:
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Verify Kowloon startup translation from final ISO bytes")
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--startup-graphics-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = verify_startup_candidate(args.candidate, args.startup_graphics_root)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "checks"}, sort_keys=True))
    failures = [check for check in report["checks"] if not check["ok"]]
    for failure in failures:
        print(f"FAIL {failure['name']}: {failure['detail']}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
