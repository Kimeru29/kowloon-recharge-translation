from __future__ import annotations

import struct

from tools.executable_text import RelocatedText
from tools.localization import encode_ps2_english

MEMORY_CARD_POINTER_TABLE_OFFSET = 0x407440
# Handler-local aliases used by the pre-title boot checks.  Static tracing shows
# H_BootMcardChk and H_EmptyMcardChk both embed table entry 1 directly instead
# of loading it through MEMORY_CARD_POINTER_TABLE_OFFSET.
MEMORY_CARD_POINTER_ALIASES: dict[int, tuple[int, ...]] = {
    1: (0x4077F0, 0x4078D0),
}
_ELF_MAIN_FILE_OFFSET = 0x80
_ELF_MAIN_VADDR = 0x00100000
_LINE_BREAK = "＠改行"


def _elf_va(file_offset: int) -> int:
    return _ELF_MAIN_VADDR + file_offset - _ELF_MAIN_FILE_OFFSET


def encode_memory_card_english(text: str) -> bytes:
    """Encode official English while preserving the PS2 executable line-break token."""

    normalized = text.replace("\n", _LINE_BREAK)
    parts = normalized.split(_LINE_BREAK)
    out = bytearray()
    for index, part in enumerate(parts):
        if index:
            out.extend(_LINE_BREAK.encode("cp932"))
        if part:
            out.extend(encode_ps2_english(part, collapse_spaces=False))
    return bytes(out)


# Proven correspondence between the PS2/re:charge memory-card pointer table and
# the official remaster localization dictionary.  Entries whose re:charge-only
# semantics have no proven official counterpart are intentionally absent.
# Each item is pointer-index -> (PS2 source file offset, PS2 source, English).
MEMORY_CARD_MESSAGES: dict[int, tuple[int, str, str]] = {
    0: (0x406B20, "＠改行＠改行データ処理を選択してください。", "＠改行＠改行Select data function."),
    1: (0x406B50, "＠改行＠改行メモリーカード差込口１を＠改行＠改行チェック中です。", "\nChecking memory card\nslot 1"),
    2: (0x406BA0, "＠改行メモリーカード差込口１に＠改行＠改行メモリーカード（ＰＳ２）が＠改行＠改行差されてません。", "\nNo memory card＠改行(PS2) inserted＠改行in slot 1."),
    3: (0x406C10, "＠改行＠改行セーブを中断して宜しいですか？", "＠改行＠改行Cancel the save?"),
    4: (0x406BA0, "＠改行メモリーカード差込口１に＠改行＠改行メモリーカード（ＰＳ２）が＠改行＠改行差されてません。", "\nNo memory card＠改行(PS2) inserted＠改行in slot 1."),
    5: (0x406C40, "＠改行メモリーカード差込口１に差されている＠改行＠改行のは、メモリーカード（ＰＳ２）では＠改行＠改行ありません。", "\nMemory card in slot 1 is＠改行not a PS2 memory card."),
    6: (0x406CC0, "＠改行＠改行処理中に問題が発生しました。＠改行", "＠改行＠改行An error has occurred during processing.＠改行"),
    7: (0x406CF0, "＠改行このメモリーカード（ＰＳ２）は＠改行フォーマットされていません。＠改行フォーマットしますか？＠改行", "\nThis memory card is＠改行not formatted.＠改行Format it now?"),
    8: (0x406D60, "＠改行セーブ中・・・＠改行メモリーカード（ＰＳ２）の＠改行抜き差しをしたり、電源を切ったり＠改行しないでください。", "\nSaving...＠改行Do not remove or reinsert the＠改行memory card (PS2) or turn off the power."),
    9: (0x406DE0, "＠改行＠改行セーブが完了しました。", "＠改行＠改行Data saved."),
    10: (0x406E10, "＠改行フォーマット中・・・＠改行メモリーカード（ＰＳ２）の＠改行抜き差しをしたり、電源を切ったり＠改行しないでください。", "\nFormatting...＠改行Do not remove or reinsert the＠改行memory card (PS2) or turn off the power."),
    12: (0x406EF0, "＠改行ロード中・・・＠改行メモリーカード（ＰＳ２）の＠改行抜き差しをしたり、電源を切ったり＠改行しないでください。", "\nLoading...＠改行Do not remove or reinsert the＠改行memory card (PS2) or turn off the power."),
    13: (0x406F70, "＠改行＠改行ロードが完了しました。", "＠改行＠改行Data loaded."),
    14: (0x406FA0, "＠改行既にファイルが存在します。＠改行＠改行上書きして宜しいですか？", "＠改行File already exists.＠改行＠改行Overwrite the file?"),
    15: (0x406FF0, "＠改行＠改行メモリーカード差込口１に＠改行＠改行メモリーカード（ＰＳ２）が＠改行＠改行差さっていません。", "＠改行＠改行No memory card (PS2)＠改行＠改行is inserted."),
    16: (0x407060, "＠改行＠改行データを正しくセーブ出来ませんでした。＠改行＠改行データが壊れている可能性があります。", "＠改行＠改行Unable to save correctly.＠改行＠改行The data may be corrupted."),
    17: (0x4070D0, "＠改行＠改行ロード中にエラーが発生しました。＠改行＠改行データが壊れている可能性があります。", "＠改行＠改行A loading error has occurred.＠改行＠改行The data may be corrupted."),
    18: (0x407130, "＠改行＠改行データをセーブして宜しいですか？", "＠改行＠改行Save this data?"),
    26: (0x407410, "＠改行このまま始めて宜しいですか？", "＠改行Go ahead and start the game?"),
}


def validate_memory_card_sources(raw: bytes) -> None:
    for index, (source_offset, source, _english) in MEMORY_CARD_MESSAGES.items():
        encoded = source.encode("cp932")
        if raw[source_offset:source_offset + len(encoded)] != encoded or raw[source_offset + len(encoded)] != 0:
            raise ValueError(f"Memory-card source preimage mismatch for entry {index}")
        pointer_offset = MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4
        if pointer_offset + 4 > len(raw):
            raise ValueError("Memory-card pointer table is outside executable")
        actual = struct.unpack_from("<I", raw, pointer_offset)[0]
        expected = _elf_va(source_offset)
        if actual != expected:
            raise ValueError(
                f"Memory-card pointer preimage mismatch for entry {index}: expected {expected:#x}, got {actual:#x}"
            )

        for alias_offset in MEMORY_CARD_POINTER_ALIASES.get(index, ()):
            if alias_offset + 4 > len(raw):
                raise ValueError("Memory-card pointer alias is outside executable")
            alias = struct.unpack_from("<I", raw, alias_offset)[0]
            if alias != expected:
                raise ValueError(
                    f"Memory-card pointer alias preimage mismatch for entry {index} at {alias_offset:#x}: "
                    f"expected {expected:#x}, got {alias:#x}"
                )


def relocated_memory_card_entries(raw: bytes) -> tuple[RelocatedText, ...]:
    """Return validated memory-card translations in stable pointer-table order."""

    validate_memory_card_sources(raw)
    entries: list[RelocatedText] = []
    for index in sorted(MEMORY_CARD_MESSAGES):
        _source_offset, _source, english = MEMORY_CARD_MESSAGES[index]
        pointers = (
            MEMORY_CARD_POINTER_TABLE_OFFSET + index * 4,
            *MEMORY_CARD_POINTER_ALIASES.get(index, ()),
        )
        entries.append(
            RelocatedText(
                key=f"memory_card_{index}",
                encoded=encode_memory_card_english(english) + b"\x00",
                pointer_offsets=pointers,
            )
        )
    return tuple(entries)
