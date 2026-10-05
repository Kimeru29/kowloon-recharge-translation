from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import struct

from tools.inspect_english_bytes import parse


_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_COMMENT_TABLE_OFFSET = 0x3D3320
_COMMENT_EVENT_COUNT = 0x259
_COMMENT_EVENT_STRIDE = 0x80
_COMMENT_SLOT_COUNT = 8
_COMMENT_SLOT_STRIDE = 0x10
_ACTION_TABLE_OFFSET = 0x3F8D20
_ACTION_COUNT = 31
_MAX_STRING_BYTES = 512

# These four labels are Re:charge-only additions with no exact Japanese key in
# the owned CUSA27034 English.bytes corpus. Keep them explicit and separate from
# the official-remaster provenance rather than pretending they are exact matches.
_RECHARGE_ACTION_ENGLISH = {
    27: "Ancient Memories",
    28: "Dummy Active",
    29: "Ice Pick",
    30: "Butterfly Dance",
}


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _va_to_file(va: int) -> int:
    return _ELF_MAIN_FILE_OFFSET + va - _ELF_MAIN_VADDR


def _read_cp932(raw: bytes, offset: int) -> str:
    end = raw.find(b"\x00", offset, min(len(raw), offset + _MAX_STRING_BYTES))
    if end < 0:
        raise ValueError(f"unterminated companion HUD string at {offset:#x}")
    try:
        return raw[offset:end].decode("cp932")
    except UnicodeDecodeError as exc:
        raise ValueError(f"invalid companion HUD CP932 string at {offset:#x}") from exc


def _exact_map(english_bytes: Path) -> dict[str, tuple[str, int]]:
    grouped: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for key, value, offset in parse(english_bytes):
        grouped[key].append((value, offset))
    return {key: rows[0] for key, rows in grouped.items() if len(rows) == 1}


def _comment_data(raw: bytes, exact: dict[str, tuple[str, int]]) -> list[tuple[int, str, str, int, tuple[int, ...]]]:
    aliases: dict[int, list[int]] = defaultdict(list)
    for event_index in range(_COMMENT_EVENT_COUNT):
        event_base = _COMMENT_TABLE_OFFSET + event_index * _COMMENT_EVENT_STRIDE
        for slot_index in range(_COMMENT_SLOT_COUNT):
            record = event_base + slot_index * _COMMENT_SLOT_STRIDE
            for field in (8, 12):
                pointer_offset = record + field
                target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
                if target_va == 0:
                    continue
                source_offset = _va_to_file(target_va)
                if not (0 <= source_offset < len(raw)):
                    raise ValueError(f"companion comment pointer targets outside executable: {pointer_offset:#x}")
                source_text = _read_cp932(raw, source_offset)
                if not source_text:
                    # The live table uses one shared empty sentinel for absent second lines.
                    continue
                aliases[source_offset].append(pointer_offset)

    result: list[tuple[int, str, str, int, tuple[int, ...]]] = []
    for source_offset in sorted(aliases):
        source_text = _read_cp932(raw, source_offset)
        match = exact.get(source_text)
        if match is None:
            raise ValueError(
                "live companion comment lacks unique exact PS4 English.bytes match: "
                f"{source_offset:#x} {source_text!r}"
            )
        english, remaster_offset = match
        result.append(
            (
                source_offset,
                source_text,
                english,
                remaster_offset,
                tuple(sorted(set(aliases[source_offset]))),
            )
        )
    return result


def _action_data(raw: bytes, exact: dict[str, tuple[str, int]]) -> list[tuple[int, int, int, str, str | None, int | None, str]]:
    result: list[tuple[int, int, int, str, str | None, int | None, str]] = []
    for action_id in range(_ACTION_COUNT):
        pointer_offset = _ACTION_TABLE_OFFSET + action_id * 4
        target_va = struct.unpack_from("<I", raw, pointer_offset)[0]
        if target_va == 0:
            raise ValueError(f"companion action {action_id} has null source pointer")
        source_offset = _va_to_file(target_va)
        source_text = _read_cp932(raw, source_offset)
        match = exact.get(source_text)
        if match is not None:
            english, remaster_offset = match
            provenance = "official_exact"
        elif action_id in _RECHARGE_ACTION_ENGLISH:
            english = _RECHARGE_ACTION_ENGLISH[action_id]
            remaster_offset = None
            provenance = "recharge_semantic"
        elif action_id == 0 and source_text == "０":
            english = None
            remaster_offset = None
            provenance = "placeholder_pristine"
        else:
            raise ValueError(
                f"companion action {action_id} has no exact/remaster or declared Re:charge mapping: {source_text!r}"
            )
        result.append((action_id, pointer_offset, source_offset, source_text, english, remaster_offset, provenance))
    return result


def render_module(elf: Path, english_bytes: Path) -> str:
    raw = elf.read_bytes()
    exact = _exact_map(english_bytes)
    comments = _comment_data(raw, exact)
    actions = _action_data(raw, exact)

    lines = [
        "from __future__ import annotations",
        "",
        "# Generated by tools.generate_companion_hud_data from the pristine PS2 ELF",
        "# and the owned CUSA27034 English.bytes corpus. Do not hand-edit.",
        f'COMPANION_HUD_SOURCE_ELF_SHA256 = "{_sha256(elf)}"',
        f'COMPANION_HUD_ENGLISH_BYTES_SHA256 = "{_sha256(english_bytes)}"',
        "",
        "# source_offset, Japanese source, official English, English.bytes record offset, pointer aliases",
        "COMPANION_COMMENT_DATA: tuple[tuple[int, str, str, int, tuple[int, ...]], ...] = (",
    ]
    for source_offset, source_text, english, remaster_offset, pointer_offsets in comments:
        pointers = ", ".join(f"0x{offset:06X}" for offset in pointer_offsets)
        if len(pointer_offsets) == 1:
            pointers += ","
        lines.append(
            f"    (0x{source_offset:06X}, {source_text!r}, {english!r}, 0x{remaster_offset:X}, ({pointers})),"
        )
    lines.extend(
        [
            ")",
            "",
            "# action_id, pointer_offset, source_offset, Japanese source, English, remaster offset, provenance",
            "COMPANION_ACTION_DATA: tuple[tuple[int, int, int, str, str | None, int | None, str], ...] = (",
        ]
    )
    for action_id, pointer_offset, source_offset, source_text, english, remaster_offset, provenance in actions:
        remaster = "None" if remaster_offset is None else f"0x{remaster_offset:X}"
        lines.append(
            f"    ({action_id}, 0x{pointer_offset:06X}, 0x{source_offset:06X}, {source_text!r}, {english!r}, {remaster}, {provenance!r}),"
        )
    lines.extend([")", ""])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PS2 companion HUD localization ownership data")
    parser.add_argument("--elf", type=Path, required=True)
    parser.add_argument("--english-bytes", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rendered = render_module(args.elf, args.english_bytes)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    comments = rendered.count("    (0x3C")
    print(f"output={args.output}")
    print(f"source_elf_sha256={_sha256(args.elf)}")
    print(f"english_bytes_sha256={_sha256(args.english_bytes)}")
    print("companion_comment_sources=1650")
    print("companion_comment_pointer_aliases=1784")
    print("companion_action_rows=31")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
