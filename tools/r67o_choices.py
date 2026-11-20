"""Package the source-proven r67.15o KSF choices beside immutable r67.15n resources."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
import json
import mmap
from pathlib import Path
import re
import struct
import subprocess
from tempfile import TemporaryDirectory

from tools.iso9660_patch import SECTOR_SIZE, find_record, index_iso
from tools.localization import encode_ps2_english
from tools.r67_15g_route_audit import DATA_CVM_HEADER_SIZE
from tools.r67_15h_item_layout import (
    APPEND_FILE_OFFSET, APPEND_VA, APPEND_RESERVE, _validate_translation_load,
    _emit_gpr_frame, _emit_fpr_frame, _float_word,
)
from tools.r67_chamber_story_text_only import Assembly, _i, _jal, _r
from tools.r67_15k_kernel import audit_ee_cop1
from tools.r67n_ksf import PAYLOAD, native_slots
from tools.r67n_ksf_structural import record_choices


BIAS = 0xFFF80
SOURCE_SHA256 = '0d5ace47c618c8c9af92f76aecad72dd0da2c4f7588410d2f9d866458a8f38bb'
PRISTINE_SHA256 = '6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794'
RESEARCH_SHA256 = '93467f5e78cd5c6bd6e413574cc56f67c4779027eadf7e91642d0e965726e4bf'
SUPPLEMENT_SHA256 = 'fd5a25976b29dc2fec00c43e9f53309a73121e401be6af479a5ec61514201a35'
INVENTORY_SHA256 = '1946a1f9e07483e932475281f2868f75adbc50aabd942fb6187f3af4f7ad5499'
FONT_TABLE_PTR = 0x5D7E20
NAME_MARKERS = {'(pm1)': b'\x01', '(pn1)': b'\x02'}
DYNAMIC_KEYS = {
    ('FN/FN06_01.KSF', 30159), ('ID/ID00_04.KSF', 25612),
    ('ID/ID00_26.KSF', 27932), ('MS/MS06_01.KSF', 302859),
}
NAME_PATTERN = re.compile(r'(\(pm1\)|\(pn1\))')
REQUEST_PATTERN = re.compile(r'(?P<kind>DG|FD|FI|FN|ID|IN|MS)/(?P=kind)\d\d_\d\d\.KSF\Z')
FLAG_OFFSET = 0x90C
ORDINAL_MAX = 0xFFFF
MAX_ROW_BYTES = 100
MAX_LOGICAL_GLYPHS = 56
LINE_WIDTH = 448
BLANK_STATUS = 'official U+3000 no-op'


@dataclass(frozen=True)
class ChoiceRow:
    path: str
    array_index: int
    key: int
    offset: int
    slot: int
    text: str
    encoded: bytes
    tokens: tuple[int, ...]
    preimage: bytes
    pristine: bytes
    status: str

    @property
    def dynamic(self) -> bool:
        return any(marker in self.encoded for marker in NAME_MARKERS.values())


@dataclass(frozen=True)
class ChoiceRecord:
    loaded_name: bytes
    ordinal: int
    offset: int
    flags: bytes
    header: bytes
    rows: tuple[ChoiceRow, ...]


@dataclass(frozen=True)
class ChoiceFile:
    path: str
    loaded_name: bytes
    installed_size: int
    installed_sha256: str
    ps2_sha256: str
    ps4_sha256: str
    dc_sha256: str


@dataclass(frozen=True)
class ChoiceCorpus:
    files: tuple[ChoiceFile, ...]
    records: tuple[ChoiceRecord, ...]
    blank_rows: tuple[ChoiceRow, ...]
    supplement_sha256: str | None = None


def _digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def _read_pinned(path: Path, expected: str, description: str) -> bytes:
    data = path.read_bytes()
    if _digest(data) != expected:
        raise ValueError(f'{description} differs from its pinned SHA-256: {path}')
    return data


def _font_table(elf: bytes, style: int = 0) -> tuple[int, ...]:
    offset = struct.unpack_from('<I', elf, FONT_TABLE_PTR - BIAS + style * 4)[0] - BIAS
    count = struct.unpack_from('<H', elf, offset)[0]
    return struct.unpack_from(f'<{count}H', elf, offset + 2)


def _encode_character(char: str) -> tuple[bytes, int]:
    if char == ' ':
        return b' ', 0xFF0A
    if char == '"':
        return b'"', 0x8168
    raw = encode_ps2_english(char)
    return raw, int.from_bytes(raw, 'big')


def _encode(text: str, indices: dict[int, int]) -> tuple[bytes, tuple[int, ...]]:
    encoded = bytearray()
    expanded_test_tokens = []
    for part in NAME_PATTERN.split(text):
        if part in NAME_MARKERS:
            encoded.extend(NAME_MARKERS[part])
            fixture = 'ABC' if part == '(pm1)' else 'Qxy'
            expanded_test_tokens.extend(indices[_encode_character(c)[1]] for c in fixture)
            continue
        for char in part:
            raw, unit = _encode_character(char)
            encoded.extend(raw)
            if unit == 0xFF0A:
                expanded_test_tokens.append(unit)
            elif unit == 0x8140:
                expanded_test_tokens.append(0xFF0B)
            else:
                expanded_test_tokens.append(indices[unit])
    if len(encoded) > MAX_ROW_BYTES or any(byte in b'\0%\n' for byte in encoded):
        raise ValueError('official choice exceeds scratch or uses an unsupported control')
    return bytes(encoded), tuple(expanded_test_tokens)


def layout_units(units: tuple[int, ...]) -> tuple[int | None, tuple[int, ...]]:
    """Return a byte-independent wrap index and logical line widths."""
    widths = [0]
    for token in units:
        widths.append(widths[-1] + (8 if token == 0xFF0A else 16))
    if not 1 <= len(units) <= MAX_LOGICAL_GLYPHS:
        raise ValueError('choice logical count is outside 1..56')
    if widths[-1] <= LINE_WIDTH:
        return None, (widths[-1],)
    for split in range(len(units) - 1, 0, -1):
        if units[split - 1] != 0xFF0A and units[split] != 0xFF0A:
            continue
        left, right = widths[split], widths[-1] - widths[split]
        if left <= LINE_WIDTH and right <= LINE_WIDTH:
            return split, (left, right)
    raise ValueError('choice needs more than two bounded lines')


def _packed_flags(raw: bytes, record: int) -> tuple[bytes, tuple[int, ...]]:
    offset = record + FLAG_OFFSET
    flags, positions = bytearray(), []
    for _ in range(4):
        flags.append(raw[offset])
        offset += 1
        if flags[-1] == 1:
            positions.append(offset)
            offset += PAYLOAD
    return bytes(flags), tuple(positions)


def _prove_file(ps2: Path, ps4: Path, image: mmap.mmap, nested: int,
                indexed: dict, entry: dict, evidence: list[dict],
                indices: dict[int, int]) -> tuple[ChoiceFile, list[ChoiceRecord], list[ChoiceRow]]:
    path = entry['path']
    match = REQUEST_PATTERN.fullmatch(path)
    if not match:
        raise ValueError(f'unsupported native KSF filename: {path}')
    loaded_name = ('adv/' + match['kind'].lower() + '/' + path.split('/')[1]).encode('ascii')
    original = _read_pinned(ps2 / path, entry['ps2_sha256'], 'pristine PS2 KSF')
    remaster = _read_pinned(ps4 / path, entry['ps4']['sha256'], 'remaster KSF')
    dc = json.loads(_read_pinned(ps4 / entry['map_path'], entry['map_sha256'], 'official KSF dictionary'))
    keys, texts = dc['keys'], dc['values']
    if len(keys) != len(texts) or len(set(keys)) != len(keys):
        raise ValueError(f'nonunique official dictionary keys: {path}')
    iso_record = indexed['ADV/' + path]
    iso_offset = nested + iso_record.extent * SECTOR_SIZE
    installed = image[iso_offset:iso_offset + iso_record.size]
    if (iso_offset != entry['iso_offset'] or len(installed) != len(original)
            or len(installed) != entry['size'] or _digest(installed) != entry['installed_sha256']):
        raise ValueError(f'installed whole KSF preimage differs: {path}')
    originals, remasters = record_choices(original), record_choices(remaster)
    installed_native = native_slots(installed)
    if installed_native != native_slots(original):
        raise ValueError(f'installed physical KSF structure differs: {path}')
    if len({index['index'] for index in evidence}) != len(evidence):
        raise ValueError(f'duplicate official array identity: {path}')
    by_ordinal = defaultdict(list)
    seen_slots = set()
    for item in evidence:
        index, offset = item['index'], item['ps2_offset']
        key, text = keys[index], texts[index]
        ordinal, slot, start, end = originals[offset]
        other_ordinal, other_slot, other_start, other_end = remasters[key]
        preimage, pristine = installed[offset:offset + PAYLOAD], original[offset:offset + PAYLOAD]
        if (
            item['loaded_name'].encode('ascii') != loaded_name
            or item['key'] != key or item['ordinal'] != ordinal or item['slot'] != slot
            or not 0 <= ordinal <= ORDINAL_MAX or (ordinal, slot) in seen_slots
            or (ordinal, slot) != (other_ordinal, other_slot)
            or original[start] != 2 or installed[start] != 2
            or original[start:end] != remaster[other_start:other_end]
            or _digest(original[start:end]) != item['record_sha256']
            or _digest(text.encode()) != item['official_sha256']
            or _digest(preimage) != item['old_payload_sha256']
            or preimage.hex() != item['old_payload_hex']
            or b'\0' not in preimage or b'\0' not in pristine
            or b'%' in pristine.split(b'\0', 1)[0]
        ):
            raise ValueError(f'native record or official array proof differs: {path}:{index}')
        encoded, tokens = _encode(text, indices)
        if tokens != tuple(item['native_style0_units']):
            raise ValueError(f'encoded choice differs from executed style-0 font indices: {path}:{index}')
        row = ChoiceRow(path, index, key, offset, slot, text, encoded, tokens, preimage, pristine, item['status'])
        if row.dynamic != ((path, key) in DYNAMIC_KEYS):
            raise ValueError(f'unproven official name template: {path}:{index}')
        seen_slots.add((ordinal, slot))
        by_ordinal[ordinal].append(row)

    records, blank = [], []
    for ordinal, items in sorted(by_ordinal.items()):
        rows = tuple(sorted(items, key=lambda row: row.slot))
        _, _, start, end = originals[rows[0].offset]
        flags, offsets = _packed_flags(installed, start)
        if (flags != _packed_flags(original, start)[0]
                or tuple(row.slot for row in rows) != tuple(range(len(offsets)))
                or tuple(row.offset for row in rows) != offsets or offsets[-1] + PAYLOAD > end):
            raise ValueError(f'incomplete or inconsistent choice record: {path}:{ordinal}')
        masked = bytearray(installed[start:end])
        for row in rows:
            field = row.offset - start
            masked[field:field + PAYLOAD] = row.pristine
        if masked != original[start:end]:
            raise ValueError(f'installed branch or event controls differ: {path}:{ordinal}')
        if all(row.status == BLANK_STATUS and set(row.text) == {'\u3000'} and row.preimage == row.pristine for row in rows):
            blank.extend(rows)
            continue
        if any(row.status == BLANK_STATUS or set(row.text) == {'\u3000'} for row in rows):
            raise ValueError(f'mixed blank/interactive choice policy: {path}:{ordinal}')
        for row in rows:
            split, _ = layout_units(row.tokens)
            if not row.dynamic and len(row.encoded) + (split is not None) > MAX_ROW_BYTES:
                raise ValueError(f'choice wrap exceeds scratch: {path}:{ordinal}')
        records.append(ChoiceRecord(loaded_name, ordinal, start, flags, original[start:start + 0x26], rows))

    file = ChoiceFile(path, loaded_name, len(installed), entry['installed_sha256'],
                      entry['ps2_sha256'], entry['ps4']['sha256'], entry['map_sha256'])
    return file, records, blank


def load_corpus(elf: bytes, pristine_elf: bytes, iso: Path, ps2_adv: Path, ps4_adv: Path,
                research: Path, inventory: Path, supplement: Path | None = None) -> ChoiceCorpus:
    if _digest(elf) != SOURCE_SHA256:
        raise ValueError('expected the unchanged r67.15n ELF')
    if _digest(pristine_elf) != PRISTINE_SHA256:
        raise ValueError('expected the unchanged pristine Japanese ELF')
    design = json.loads(_read_pinned(research, RESEARCH_SHA256, 'KSF research evidence'))
    files = {entry['path']: entry for entry in json.loads(
        _read_pinned(inventory, INVENTORY_SHA256, 'KSF file inventory'))}
    if design['elf_sha256'] != SOURCE_SHA256 or design['pristine_elf_sha256'] != PRISTINE_SHA256:
        raise ValueError('KSF research evidence has mismatched ELF owners')
    for owner in design['ranges']:
        start, end = int(owner['start'], 16), int(owner['end_exclusive'], 16)
        before = elf[start - BIAS:end - BIAS]
        if (int(owner['file_offset'], 16) != start - BIAS or _digest(before) != owner['sha256']
                or (before == pristine_elf[start - BIAS:end - BIAS]) != owner['pristine_matches']):
            raise ValueError(f"native KSF owner drift: {owner['name']}")
    indices = {}
    for index, unit in enumerate(_font_table(elf)):
        indices.setdefault(unit, index)
    evidence = defaultdict(list)
    for row in design['rows']:
        evidence[row['file']].append(row)
    proven_files, records, blank = [], [], []
    with iso.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        outer = index_iso(image)[1]
        elf_record = find_record(outer, 'SLPM_665.11')
        elf_start = elf_record.extent * SECTOR_SIZE
        if image[elf_start:elf_start + elf_record.size] != elf:
            raise ValueError('installed r67.15n ELF differs from the pinned source')
        nested = find_record(outer, 'DATA.CVM').extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        indexed = {record.path: record for record in index_iso(image, nested)[1]}
        for path, rows in sorted(evidence.items()):
            file, proven, noops = _prove_file(
                ps2_adv, ps4_adv, image, nested, indexed, files[path], rows, indices)
            proven_files.append(file)
            records.extend(proven)
            blank.extend(noops)
    result = ChoiceCorpus(tuple(sorted(proven_files, key=lambda file: file.loaded_name)),
                          tuple(sorted(records, key=lambda record: (record.loaded_name, record.ordinal))),
                          tuple(blank))
    if (len(result.files) != 159 or len(result.blank_rows) != 4
            or Counter(len(r.rows) for r in result.records) != {1: 28, 2: 253, 3: 68, 4: 76}):
        raise ValueError('official KSF coverage differs from the complete proven set')
    if supplement is None:
        return result
    return _add_supplement(result, iso, ps2_adv, ps4_adv, supplement, indices)


def _add_supplement(corpus: ChoiceCorpus, iso: Path, ps2_adv: Path, ps4_adv: Path,
                    report: Path, indices: dict[int, int]) -> ChoiceCorpus:
    from tools.r67o_choice_correspondence import project_record

    supplement = json.loads(_read_pinned(report, SUPPLEMENT_SHA256, 'supplemental KSF correspondence'))
    files = {file.loaded_name: file for file in corpus.files}
    records = {(record.loaded_name, record.ordinal): record for record in corpus.records}
    added = 0
    with iso.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        outer = index_iso(image)[1]
        nested = find_record(outer, 'DATA.CVM').extent * SECTOR_SIZE + DATA_CVM_HEADER_SIZE
        indexed = {record.path: record for record in index_iso(image, nested)[1]}
        for entry in supplement['files']:
            path = entry['path']
            match = REQUEST_PATTERN.fullmatch(path)
            if not match:
                raise ValueError(f'unsupported supplemental KSF filename: {path}')
            name = ('adv/' + match['kind'].lower() + '/' + path.split('/')[1]).encode('ascii')
            if entry['loaded_name'].encode('ascii') != name:
                raise ValueError(f'supplemental KSF request path differs: {path}')
            original = _read_pinned(ps2_adv / path, entry['ps2_sha256'], 'supplemental PS2 KSF')
            remaster = _read_pinned(ps4_adv / path, entry['ps4_sha256'], 'supplemental PS4 KSF')
            mtx = Path(path).with_suffix('.MTX')
            mtx2 = _read_pinned(ps2_adv / mtx, entry['ps2_mtx_sha256'], 'supplemental PS2 MTX')
            mtx4 = _read_pinned(ps4_adv / mtx, entry['ps4_mtx_sha256'], 'supplemental PS4 MTX')
            dc = json.loads(_read_pinned(ps4_adv / entry['map_path'], entry['map_sha256'], 'supplemental official DC'))
            iso_record = indexed['ADV/' + path]
            start = nested + iso_record.extent * SECTOR_SIZE
            installed = image[start:start + iso_record.size]
            if (start != entry['iso_offset'] or len(installed) != entry['installed_size']
                    or _digest(installed) != entry['installed_sha256']):
                raise ValueError(f'supplemental installed KSF preimage differs: {path}')
            attached = ChoiceFile(path, name, len(installed), entry['installed_sha256'],
                                  entry['ps2_sha256'], entry['ps4_sha256'], entry['map_sha256'])
            if files.setdefault(name, attached) != attached:
                raise ValueError(f'conflicting KSF file proofs: {path}')
            for proof in entry['records']:
                ordinal = proof['ordinal']
                if (name, ordinal) in records:
                    raise ValueError(f'overlapping KSF choice proofs: {path}:{ordinal}')
                projected = project_record(path, ordinal, original, remaster, installed, mtx2, mtx4,
                                           tuple(row['key'] for row in proof['rows']))
                for field, value in projected.items():
                    if field != 'rows' and proof[field] != value:
                        raise ValueError(f'supplemental KSF record proof differs: {path}:{ordinal}/{field}')
                rows = []
                for row, projection in zip(proof['rows'], projected['rows'], strict=True):
                    for field, value in projection.items():
                        if row[field] != value:
                            raise ValueError(f'supplemental KSF payload proof differs: {path}:{ordinal}/{field}')
                    index = row['index']
                    text = dc['values'][index]
                    if dc['keys'][index] != row['key'] or _digest(text.encode()) != row['official_sha256']:
                        raise ValueError(f'supplemental official array identity differs: {path}:{index}')
                    encoded, tokens = _encode(text, indices)
                    split, _ = layout_units(tokens)
                    if any(byte in encoded for byte in (b'\x01', b'\x02')) or len(encoded) + (split is not None) > MAX_ROW_BYTES:
                        raise ValueError(f'supplemental KSF label exceeds proven encoding: {path}:{index}')
                    rows.append(ChoiceRow(path, index, row['key'], row['ps2_offset'], row['slot'], text,
                                          encoded, tokens, bytes.fromhex(row['old_payload_hex']),
                                          bytes.fromhex(row['pristine_payload_hex']), 'proven native correspondence'))
                records[name, ordinal] = ChoiceRecord(
                    name, ordinal, proof['installed_record_range'][0], bytes.fromhex(proof['flags_hex']),
                    bytes.fromhex(proof['installed_header_hex']), tuple(rows))
                added += len(rows)
    if added != 37 or len(files) != 163 or len(records) != 441:
        raise ValueError('supplemental KSF census differs from the pinned proof')
    return ChoiceCorpus(tuple(files[key] for key in sorted(files)),
                        tuple(records[key] for key in sorted(records)), corpus.blank_rows, SUPPLEMENT_SHA256)


KERNEL = Path(__file__).resolve().parent / 'native/r67o_choices.c'
ACTIVATION = 0x22C388
INITIAL_PREPROCESS = 0x22C394
FONT_CTOR = 0x251594
DISPLAY_PREPROCESS = 0x251668
FONT_SETTER = 0x2516A8
ANIMATOR_CTOR = 0x2516F8
CURSOR_CTOR = 0x251A24
CURSOR_MOVE = 0x251BE0
OWNER_CALLS = {
    ACTIVATION: 0x39F708,
    INITIAL_PREPROCESS: 0x24D5A0,
    FONT_CTOR: 0x18BF10,
    DISPLAY_PREPROCESS: 0x24D5A0,
    FONT_SETTER: 0x18C1D0,
    ANIMATOR_CTOR: 0x18C670,
    CURSOR_CTOR: 0x102490,
    CURSOR_MOVE: 0x102590,
}
ANIMATOR_SIZE = 0x218
CONTEXT_SIZE = 0x388
BRIDGE_FRAME = 0x2B0
STATE_GP = -0x1DAC

@lru_cache(maxsize=4)
def _compile_object(files: int, records: int, source: bytes) -> bytes:
    import llvmlite
    from llvmlite import binding as llvm

    if llvmlite.__version__ != '0.50.0' or llvm.llvm_version_info != (22, 1, 0):
        raise ValueError('choice kernel requires llvmlite 0.50.0 / LLVM 22.1.0')
    version = subprocess.run(['clang', '--version'], check=True, capture_output=True,
                             text=True).stdout.splitlines()[0]
    if version != 'Apple clang version 21.0.0 (clang-2100.1.1.101)':
        raise ValueError(f'unpinned choice C frontend: {version}')
    command = [
        'clang', '-cc1', '-triple', 'mipsel-none-elf', '-target-cpu', 'mips2',
        '-target-abi', 'o32', '-target-feature', '-fp64', '-target-feature', '+single-float',
        '-emit-llvm', '-O2', '-ffreestanding', '-fno-builtin', '-ffp-contract=off',
        f'-DCHOICE_FILE_COUNT={files}', f'-DCHOICE_RECORD_COUNT={records}', '-x', 'c', '-o', '-', '-',
    ]
    ir = subprocess.run(command, input=source, check=True, capture_output=True).stdout
    llvm.initialize_all_targets()
    llvm.initialize_all_asmprinters()
    module = llvm.parse_assembly(ir.decode())
    module.verify()
    machine = llvm.Target.from_triple('mipsel-none-elf').create_target_machine(
        cpu='mips2', features='-fp64,+single-float', reloc='static', codemodel='small', opt=2)
    return machine.emit_object(module)


def _link_kernel(obj: bytes, base: int, absolute: dict[str, int]) -> tuple[bytes, dict, int]:
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
    from elftools.elf.elffile import ELFFile

    elf = ELFFile(BytesIO(obj))
    output = bytearray()
    locations = {}
    for index, section in enumerate(elf.iter_sections()):
        if section.name not in ('.text', '.rodata', '.rodata.cst4'):
            if section['sh_flags'] & 2 and section['sh_size'] and section.name not in ('.reginfo', '.MIPS.abiflags'):
                raise ValueError(f'unexpected choice kernel section: {section.name}')
            continue
        output.extend(bytes(-(base + len(output)) % max(4, section['sh_addralign'])))
        locations[index] = len(output)
        output.extend(section.data())
    symbols = elf.get_section_by_name('.symtab')

    def address(symbol):
        if symbol['st_shndx'] in locations:
            return base + locations[symbol['st_shndx']] + symbol['st_value']
        if symbol['st_shndx'] == 'SHN_UNDEF' and symbol.name in absolute:
            return absolute[symbol.name]
        raise ValueError(f'unresolved choice kernel symbol: {symbol.name}')

    pending = {}
    for relocations in elf.iter_sections():
        if relocations['sh_type'] != 'SHT_REL' or relocations['sh_info'] not in locations:
            continue
        target = locations[relocations['sh_info']]
        for relocation in relocations.iter_relocations():
            offset = target + relocation['r_offset']
            symbol_id = relocation['r_info_sym']
            value = address(symbols.get_symbol(symbol_id))
            old = struct.unpack_from('<I', output, offset)[0]
            kind = relocation['r_info_type']
            if kind == 4:
                destination = value + ((old & 0x3FFFFFF) << 2)
                if destination & 3 or destination >> 28 != (base + offset + 4) >> 28:
                    raise ValueError('choice kernel jump is out of range')
                new = (old & 0xFC000000) | ((destination >> 2) & 0x3FFFFFF)
            elif kind == 5:
                pending.setdefault(symbol_id, []).append((offset, old))
                continue
            elif kind == 6:
                signed = (old & 0x7FFF) - (old & 0x8000)
                for high_offset, high_word in pending.pop(symbol_id, []):
                    final = value + ((high_word & 0xFFFF) << 16) + signed
                    struct.pack_into('<I', output, high_offset,
                                     (high_word & 0xFFFF0000) | (((final + 0x8000) >> 16) & 0xFFFF))
                new = (old & 0xFFFF0000) | ((value + signed) & 0xFFFF)
            elif kind == 2:
                new = old + value
            else:
                raise ValueError(f'unapproved choice kernel relocation: {kind}')
            struct.pack_into('<I', output, offset, new)
        if pending:
            raise ValueError('unpaired choice kernel HI16 relocation')

    text = elf.get_section_by_name('.text')
    if locations[elf.get_section_index('.text')] != 0:
        raise ValueError('unexpected choice kernel text displacement')
    audit_ee_cop1(output[:text['sh_size']], base)
    legal = {
        'add.s', 'addiu', 'addu', 'and', 'andi', 'b', 'beq', 'beqz', 'bgez', 'bgtz',
        'blez', 'bltz', 'bne', 'bnez', 'j', 'jal', 'jr', 'lb', 'lbu', 'lhu',
        'lui', 'lw', 'lwc1', 'mfhi', 'mflo', 'move', 'mult', 'multu', 'negu', 'nop', 'nor', 'not', 'or', 'ori', 'sb',
        'sh', 'sll', 'sllv', 'slt', 'slti', 'sltiu', 'sltu', 'sra', 'srl',
        'srlv', 'subu', 'sw', 'swc1', 'xor', 'xori',
    }
    disassembler = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    instructions = list(disassembler.disasm(output[:text['sh_size']], base))
    if len(instructions) * 4 != text['sh_size']:
        raise ValueError('choice kernel has undecodable executable words')
    disallowed = sorted({op.mnemonic for op in instructions if op.mnemonic not in legal})
    if disallowed:
        raise ValueError(f'unaudited choice kernel instructions: {disallowed}')
    entries = {symbol.name: address(symbol) for symbol in symbols.iter_symbols()
               if symbol['st_info']['type'] == 'STT_FUNC' and symbol.name.startswith('choice_')}
    return bytes(output), entries, text['sh_size']


@lru_cache(maxsize=1)
def _cp932_name_bitmap() -> bytes:
    assigned = bytearray(1 << 13)
    for lead in (*range(0x81, 0xA0), *range(0xE0, 0xFD)):
        for trail in range(0x40, 0xFD):
            if trail == 0x7F:
                continue
            try:
                character = bytes((lead, trail)).decode('cp932', 'strict')
            except UnicodeDecodeError:
                continue
            if len(character) != 1:
                raise ValueError('CP932 pair decoded as multiple characters')
            unit = lead << 8 | trail
            assigned[unit // 8] |= 1 << (unit % 8)
    return bytes(assigned)


def _table(corpus: ChoiceCorpus, base: int) -> tuple[bytes, dict]:
    files = {file.loaded_name: index for index, file in enumerate(corpus.files)}
    if (len(files) != len(corpus.files) or list(files) != sorted(files)
            or len({(r.loaded_name, r.ordinal) for r in corpus.records}) != len(corpus.records)
            or list(corpus.records) != sorted(corpus.records, key=lambda r: (r.loaded_name, r.ordinal))):
        raise ValueError('choice file/ordinal table must be unique and sorted')
    file_table = bytearray()
    for file in corpus.files:
        if not (0 < len(file.loaded_name) < 20) or not 0 < file.installed_size < 0x1000000:
            raise ValueError(f'invalid native filename or size: {file.path}')
        file_table += struct.pack('<20sI', file.loaded_name, file.installed_size)
    record_base = base + len(file_table)
    row_base = record_base + 68 * len(corpus.records)
    records, rows = bytearray(), bytearray()
    for record in corpus.records:
        addresses = []
        for row in record.rows:
            if (len(row.preimage) != PAYLOAD or len(row.pristine) != PAYLOAD
                    or not 0 < len(row.encoded) <= MAX_ROW_BYTES or b'\0' in row.encoded):
                raise ValueError(f'unbounded choice table row: {row.path}:{row.key}')
            addresses.append(row_base + len(rows))
            rows += row.preimage + row.pristine + row.encoded + b'\0'
        addresses.extend([0] * (4 - len(addresses)))
        if len(record.header) != 0x26 or record.header[0] != 2 or len(record.flags) != 4:
            raise ValueError('choice branch header or flag bytes are unproven')
        records += struct.pack('<IHH4s38s2x4I', record.offset, files[record.loaded_name],
                               record.ordinal, record.flags, record.header, *addresses)
    return bytes(file_table + records + rows), {'choice_files': base, 'choice_records': record_base}


def _word(buffer, offset: int) -> int:
    return struct.unpack_from('<I', buffer, offset)[0]


def _patch(buffer: bytearray, offset: int, word: int) -> None:
    struct.pack_into('<I', buffer, offset, word)


def _jump(address: int) -> int:
    if address & 3 or not 0 <= address < 0x10000000:
        raise ValueError(f'unreachable choice bridge target: {address:#x}')
    return 0x08000000 | (address >> 2)


def _move(dst: int, src: int) -> int:
    return _r(src, 0, dst, 0, 0x2D)


def _begin_bridge() -> Assembly:
    m = Assembly()
    m.emit(_i(9, 29, 29, -BRIDGE_FRAME))
    _emit_gpr_frame(m, save=True)
    m.emit(_i(0x1F, 29, 30, 0x1E0))
    _emit_fpr_frame(m, save=True)
    return m


def _end_bridge(m: Assembly, target: int | None = None) -> None:
    _emit_fpr_frame(m, save=False)
    m.emit(_i(0x1E, 29, 30, 0x1E0))
    _emit_gpr_frame(m, save=False)
    m.emit(_i(9, 29, 29, BRIDGE_FRAME))
    m.emit(_jump(target) if target is not None else _r(31, 0, 0, 0, 8))
    m.emit(0)


def _finish_bridge(m: Assembly) -> bytes:
    # Resolve relative branches using the repository emitter. Tail jumps
    # restore native SP and RA, so no extra call frame or stack arguments leak.
    tail = m.words[-2]
    m.words[-2] = _r(31, 0, 0, 0, 8)
    result = bytearray(m.done())
    _patch(result, len(result) - 8, tail)
    return bytes(result)


def _call(m: Assembly, address: int, delay: int = 0) -> None:
    m.emit(_jal(address))
    m.emit(delay)


def _state(m: Assembly) -> None:
    m.emit(_i(35, 28, 4, STATE_GP))


def _row_y(m: Assembly, source: int) -> None:
    # t0 = float(22 + 39 * source); 39 is 32 + 8 - 1.
    m.emit(_r(0, source, 8, 5, 0))
    m.emit(_r(0, source, 9, 3, 0))
    m.emit(_r(8, 9, 8, 0, 0x21))
    m.emit(_r(8, source, 8, 0, 0x23))
    m.emit(_i(9, 8, 8, 22))
    m.emit(0x44880000)  # mtc1 t0,f0
    m.emit(0)
    m.emit(0x46800020)  # cvt.s.w f0,f0
    m.emit(0)
    m.emit(0x44080000)  # mfc1 t0,f0


def _bridge(kind: int, entries: dict, clones: dict) -> bytes:
    m = _begin_bridge()
    if kind == ACTIVATION:
        _state(m)
        _call(m, entries['choice_copy_source'], _move(6, 17))
        m.emit(_i(43, 29, 2, 5 * 16))
        _end_bridge(m, OWNER_CALLS[kind])
        return _finish_bridge(m)

    _state(m)
    if kind == INITIAL_PREPROCESS:
        m.emit(_i(35, 29, 6, 4 * 16))
        _call(m, entries['choice_initial_preprocess'], _move(5, 17))
    elif kind == FONT_SETTER:
        m.emit(_i(35, 29, 6, 5 * 16))
        _call(m, entries['choice_set_source'], _move(5, 18))
    elif kind in (DISPLAY_PREPROCESS, FONT_CTOR, ANIMATOR_CTOR):
        _call(m, entries['choice_view_mode'], _move(5, 16 if kind == FONT_CTOR else 18))
    elif kind == CURSOR_CTOR:
        _call(m, entries['choice_cursor_cells'])
    elif kind == CURSOR_MOVE:
        _call(m, entries['choice_moving_row'])
    else:
        raise ValueError(f'unknown choice bridge: {kind:#x}')

    if kind == FONT_CTOR:
        m.emit(_i(9, 0, 8, 1))
        m.branch(5, 2, 8, 'stock')
    else:
        m.branch(4, 2, 0, 'stock')
    m.emit(0)
    if kind in (INITIAL_PREPROCESS, DISPLAY_PREPROCESS):
        m.emit(_i(55, 29, 8, 4 * 16))
        m.emit(_i(63, 29, 8, 2 * 16))
        _end_bridge(m)
    elif kind == FONT_CTOR:
        m.emit(_i(43, 29, 0, 5 * 16))
        m.emit(_i(43, 29, 0, 6 * 16))
        m.const(8, _float_word(24.0))
        m.emit(_i(43, 29, 8, 0x200 + 12 * 4))
        _row_y(m, 16)
        m.emit(_i(43, 29, 8, 0x200 + 13 * 4))
        _end_bridge(m, OWNER_CALLS[kind])
    elif kind == FONT_SETTER:
        m.emit(_i(43, 29, 2, 5 * 16))
        m.emit(_i(35, 29, 8, 4 * 16))
        m.emit(_i(35, 8, 8, 0x3C))
        m.emit(_i(35, 8, 8, 0x0C))
        m.branch(5, 8, 0, 'pristine')
        m.emit(0)
        _end_bridge(m, clones['english_setter'])
        m.label('pristine')
        _end_bridge(m, clones['japanese_setter'])
    elif kind == ANIMATOR_CTOR:
        _end_bridge(m, clones['animator_constructor'])
    elif kind == CURSOR_CTOR:
        m.const(8, _float_word(24.0))
        m.const(9, _float_word(22.0))
        m.emit(_i(43, 29, 8, 5 * 16))
        m.emit(_i(43, 29, 9, 5 * 16 + 4))
        m.emit(_i(43, 29, 2, 6 * 16))
        _end_bridge(m, clones['cursor_constructor'])
    elif kind == CURSOR_MOVE:
        m.emit(_i(9, 0, 8, 5))
        m.branch(4, 2, 8, 'no_move')
        m.emit(0)
        m.emit(_i(9, 2, 10, -1))
        _row_y(m, 10)
        m.emit(_i(43, 29, 8, 5 * 16 + 4))
        m.const(8, _float_word(24.0))
        m.emit(_i(43, 29, 8, 5 * 16))
        _end_bridge(m, OWNER_CALLS[kind])
        m.label('no_move')
        _end_bridge(m)
    m.label('stock')
    _end_bridge(m, OWNER_CALLS[kind])
    return _finish_bridge(m)


def _cursor_update(entry: int) -> bytes:
    m = _begin_bridge()
    _call(m, 0x1025E0)
    m.emit(_i(63, 29, 2, 2 * 16))
    m.emit(_i(35, 29, 4, 4 * 16))
    _call(m, entry)
    _end_bridge(m)
    return _finish_bridge(m)


def _cursor_constructor(callback: int) -> bytes:
    # 1a1260 installs the task callbacks at +0x34 and +0x38. The
    # returned horizontal instance is the only owner whose update changes.
    m = Assembly()
    m.emit(_i(9, 29, 29, -0x20))
    m.emit(_i(63, 29, 31, 0x18))
    _call(m, 0x1029B0)
    m.branch(4, 2, 0, 'return')
    m.emit(0)
    m.emit(_i(35, 2, 3, 0x34))
    m.const(4, 0x1025E0)
    m.branch(5, 3, 4, 'return')
    m.emit(0)
    m.emit(_i(35, 2, 3, 0x38))
    m.const(4, 0x1023D0)
    m.branch(5, 3, 4, 'return')
    m.emit(0)
    m.const(3, callback)
    m.emit(_i(43, 2, 3, 0x34))
    m.label('return')
    m.emit(_i(55, 29, 31, 0x18))
    m.emit(_i(9, 29, 29, 0x20))
    m.emit(_r(31, 0, 0, 0, 8))
    m.emit(0)
    return m.done()


def _load_pair(buffer: bytearray, offset: int, register: int, address: int) -> None:
    _patch(buffer, offset, _i(15, 0, register, (address + 0x8000) >> 16))
    _patch(buffer, offset + 4, _i(9, register, register, address & 0xFFFF))


def _clone(source: bytes, start: int, end: int) -> bytearray:
    return bytearray(source[start - BIAS:end - BIAS])


def _setter_clone(source: bytes, tag: int | None) -> bytes:
    start = 0x18C1D0
    copy = _clone(source, start, 0x18C3E0)
    for address in (0x18C2B0, 0x18C2C0):
        _patch(copy, address - start, 0)
    _patch(copy, 0x18C3A8 - start, _jal(tag) if tag else 0)
    return bytes(copy)


def _word_helper_bridge(entry: int) -> bytes:
    m = _begin_bridge()
    _call(m, entry)
    # The word-returning helper can return -1. Preserve the full sign-extended
    # MIPS result rather than retaining a stale high half from the caller v0.
    m.emit(_i(63, 29, 2, 2 * 16))
    _end_bridge(m)
    return _finish_bridge(m)


def _constructor_clone(source: bytes, callback: int, init_bridge: int) -> bytes:
    start = 0x18C670
    body = _clone(source, start, 0x18C77C)
    _patch(body, 0x18C6A8 - start, _i(9, 0, 4, ANIMATOR_SIZE))
    _load_pair(body, 0x18C6F4 - start, 7, callback)
    _patch(body, 0x18C768 - start, _i(43, 2, 0, 0xF8))
    _patch(body, 0x18C770 - start, _i(0xA, 3, 2, MAX_LOGICAL_GLYPHS))
    body.extend(struct.pack('<2I', _jal(init_bridge), _move(4, 16)))
    body.extend(_clone(source, 0x18C77C, 0x18C7AC))
    return bytes(body)


def _init_bridge(entry: int) -> bytes:
    m = _begin_bridge()
    _call(m, entry)
    _end_bridge(m)
    return _finish_bridge(m)


def _animation_case_zero(base: int, entry: int, tag: int) -> bytes:
    m = Assembly()
    _call(m, entry, _move(4, 17))
    m.emit(_i(0x29, 17, 2, 0x10))  # The native owner subsequently reads this count.
    m.emit(_move(18, 0))
    m.branch(4, 2, 0, 'finish')
    m.emit(0)
    m.label('next')
    m.emit(_r(17, 18, 8, 0, 0x21))
    m.emit(_i(0x24, 8, 16, 0x1D8))  # physical index owned by animator
    m.emit(_i(35, 17, 9, 0x210))
    m.emit(_i(9, 0, 8, 1))
    m.branch(4, 9, 8, 'neutral')
    m.emit(0)
    m.emit(_i(35, 17, 4, 8))
    _call(m, tag, _move(5, 16))
    m.emit(_i(43, 29, 2, 0x38))  # unused native callback stack word
    m.emit(_i(35, 17, 4, 8))
    _call(m, 0x18E200, _move(5, 16))
    m.branch(4, 2, 0, 'not_small')
    m.emit(0)
    m.emit(_i(0x21, 17, 8, 0x10))
    m.emit(_i(9, 18, 9, 1))
    m.branch(4, 8, 9, 'not_small')
    m.emit(0)
    m.emit(_i(35, 17, 4, 8))
    _call(m, 0x18E200, _i(9, 16, 5, 1))
    m.branch(4, 0, 0, 'fallback_tag')
    m.emit(_move(7, 2))
    m.label('not_small')
    m.emit(_move(7, 0))
    m.label('fallback_tag')
    m.branch(4, 0, 0, 'child')
    m.emit(_i(35, 29, 8, 0x38))
    m.label('neutral')
    m.emit(_move(7, 0))
    m.emit(_i(9, 0, 8, -1))
    m.label('child')
    m.emit(_i(35, 17, 4, 8))
    m.emit(_move(5, 16))
    m.emit(_i(35, 17, 6, 0x14))
    _call(m, 0x18C3E0, _i(49, 17, 12, 4))
    m.emit(_r(0, 18, 8, 2, 0))
    m.emit(_r(17, 8, 8, 0, 0x21))
    m.emit(_i(43, 8, 2, 0x18))
    m.emit(_i(9, 18, 18, 1))
    m.emit(_i(0x21, 17, 8, 0x10))
    m.branch(5, 18, 8, 'next')
    m.emit(0)
    m.label('finish')
    m.emit(_jump(base + 0x18C8E8 - 0x18C7B0))
    m.emit(0)
    return _finish_bridge(m)


def _animator_callback(source: bytes, address: int, jump_table: int, entry: int, tag: int,
                       checks: int) -> bytes:
    start = 0x18C7B0
    body = _clone(source, start, 0x18CAB0)
    _load_pair(body, 0x18C7D8 - start, 3, jump_table)
    case = _animation_case_zero(address, entry, tag)
    end_case = 0x18C8E8 - start
    begin_case = 0x18C7F4 - start
    if len(case) > end_case - begin_case:
        raise ValueError('choice animator case-0 replacement exceeds its slot')
    body[begin_case:end_case] = case.ljust(end_case - begin_case, b'\0')
    # Case-2 and case-5 are entry stubs. The checks either reproduce their two
    # displaced instructions or complete a rejected zero-child animation.
    for site, check in ((0x18C8F8, checks), (0x18C9D0, checks + 0x30), (0x18CA2C, checks + 0x60)):
        _patch(body, site - start, _jump(check))
        _patch(body, site - start + 4, 0)
    return bytes(body)


def _animator_checks(source: bytes, callback: int, examine: int) -> bytes:
    result = bytearray()
    for site in (0x18C8F8, 0x18C9D0):
        m = Assembly()
        m.emit(_i(0x21, 17, 2, 0x10))
        m.branch(4, 2, 0, 'complete')
        m.emit(0)
        # Case 5 uses this branch to jump over the teardown loop initialization.
        # Preserve its native branch target explicitly when moved outside clone.
        if site == 0x18C9D0:
            m.emit(_word(source, site - BIAS))
            m.emit(_jump(callback + 0x18CA1C - 0x18C7B0))
            m.emit(0)
        else:
            m.emit(_word(source, site - BIAS))
            m.emit(_word(source, site - BIAS + 4))
            m.emit(_jump(callback + site + 8 - 0x18C7B0))
            m.emit(0)
        m.label('complete')
        m.emit(_jump(callback + 0x18C988 - 0x18C7B0))
        m.emit(0)
        data = _finish_bridge(m)
        result.extend(data.ljust(0x30, b'\0'))
    m = Assembly()
    _call(m, examine, _move(4, 17))
    m.branch(4, 2, 0, 'finish')
    m.emit(0)
    m.emit(_word(source, 0x18CA2C - BIAS))
    m.emit(_word(source, 0x18CA30 - BIAS))
    m.emit(_jump(callback + 0x18CA34 - 0x18C7B0))
    m.emit(0)
    m.label('finish')
    m.emit(_jump(callback + 0x18CA74 - 0x18C7B0))
    m.emit(0)
    result.extend(_finish_bridge(m))
    return bytes(result)


def build(source: bytes, corpus: ChoiceCorpus) -> tuple[bytes, dict]:
    """Build the offline candidate and report every existing ELF write."""
    if _digest(source) != SOURCE_SHA256:
        raise ValueError('expected unchanged r67.15n ELF')
    _validate_translation_load(source)
    out = bytearray(source)

    def current() -> int:
        out.extend(bytes(-len(out) % 16))
        return APPEND_VA + len(out) - APPEND_FILE_OFFSET

    def append(data: bytes) -> int:
        address = current()
        out.extend(data)
        return address

    table, globals_ = _table(corpus, current())
    table_address = append(table)
    globals_['choice_context'] = append(bytes(CONTEXT_SIZE))
    globals_['choice_cp932'] = append(_cp932_name_bitmap())
    obj = _compile_object(len(corpus.files), len(corpus.records), KERNEL.read_bytes())
    kernel, entries, text_size = _link_kernel(obj, current(), globals_)
    kernel_address = append(kernel)
    ee_ranges = []
    tag_bridge_data = _word_helper_bridge(entries['choice_bounded_name_tag'])
    tag_bridge = append(tag_bridge_data)
    ee_ranges.append((tag_bridge, tag_bridge + len(tag_bridge_data)))

    tag_clone = _clone(source, 0x190C90, 0x190EF0)
    _patch(tag_clone, 0x190D28 - 0x190C90, _jal(tag_bridge))
    tag_address = append(tag_clone)
    ee_ranges.append((tag_address, tag_address + len(tag_clone)))
    clones = {}
    for name, tag in (('english_setter', None), ('japanese_setter', tag_address)):
        setter = _setter_clone(source, tag)
        clones[name] = append(setter)
        ee_ranges.append((clones[name], clones[name] + len(setter)))

    protected = {}
    for function in ('choice_animation_count', 'choice_inspect_nodes'):
        bridge = _word_helper_bridge(entries[function])
        target = append(bridge)
        ee_ranges.append((target, target + len(bridge)))
        protected[function] = target

    jump_table = append(bytes(32))
    callback = current()
    checks = callback + 0x300
    callback_data = _animator_callback(
        source, callback, jump_table, protected['choice_animation_count'], tag_bridge, checks)
    if append(callback_data) != callback or current() != checks:
        raise ValueError('choice callback/checks region displacement changed')
    ee_ranges.append((callback, callback + len(callback_data)))
    append(_animator_checks(source, callback, protected['choice_inspect_nodes']))
    originals = struct.unpack_from('<8I', source, 0x77CBC0 - BIAS)
    for index, target in enumerate(originals):
        _patch(out, jump_table - APPEND_VA + APPEND_FILE_OFFSET + index * 4, callback + target - 0x18C7B0)
    init_data = _init_bridge(entries['choice_init_animator'])
    init_address = append(init_data)
    ee_ranges.append((init_address, init_address + len(init_data)))
    constructor_data = _constructor_clone(source, callback, init_address)
    clones['animator_constructor'] = append(constructor_data)
    ee_ranges.append((clones['animator_constructor'], clones['animator_constructor'] + len(constructor_data)))

    cursor_data = _cursor_update(entries['choice_fit_cursor'])
    clones['cursor_update'] = append(cursor_data)
    ee_ranges.append((clones['cursor_update'], clones['cursor_update'] + len(cursor_data)))
    clones['cursor_constructor'] = append(_cursor_constructor(clones['cursor_update']))

    owners = []
    for site, stock in OWNER_CALLS.items():
        offset = site - BIAS
        if _word(source, offset) != _jal(stock) or _word(source, offset + 4):
            raise ValueError(f'choice call owner preimage drift: {site:#x}')
        bridge = _bridge(site, entries, clones)
        address = append(bridge)
        ee_ranges.append((address, address + len(bridge)))
        _patch(out, offset, _jal(address))
        owners.append({'address': site, 'file_offset': offset, 'stock_target': stock,
                       'target': address, 'expected': source[offset:offset + 4].hex(),
                       'replacement': out[offset:offset + 4].hex()})
    if len(out) - APPEND_FILE_OFFSET > APPEND_RESERVE:
        raise ValueError('choice tables and code exceed reserved ELF/heap window')
    _patch(out, 0x64, len(out) - APPEND_FILE_OFFSET)
    allowed = {i for offset in (0x64, *(site - BIAS for site in OWNER_CALLS)) for i in range(offset, offset + 4)}
    actual = [index for index, (a, b) in enumerate(zip(source, out)) if a != b]
    if set(actual) - allowed:
        raise ValueError('choice build changed unowned ELF bytes')
    return bytes(out), {
        'source_sha256': SOURCE_SHA256,
        'result_sha256': _digest(out),
        'native_source_sha256': _digest(KERNEL.read_bytes()),
        'native_object_sha256': _digest(obj),
        'kernel': {'address': kernel_address, 'text_size': text_size, 'sha256': _digest(kernel)},
        'table': {'address': table_address, 'size': len(table), 'sha256': _digest(table),
                  'files': len(corpus.files), 'records': len(corpus.records),
                  'choices': sum(len(r.rows) for r in corpus.records), 'stock_noops': len(corpus.blank_rows),
                  'supplement_sha256': corpus.supplement_sha256},
        'entries': {**entries, **clones, 'animator_callback': callback, **globals_},
        'call_sites': owners,
        'changed_existing_offsets': actual,
        'allowed_existing_ranges': [(offset, offset + 4) for offset in sorted({0x64, *(s - BIAS for s in OWNER_CALLS)})],
        'appended_extent': [len(source), len(out)],
        'translation_reserve': APPEND_RESERVE,
        'segment_file_range': [APPEND_FILE_OFFSET, len(out)],
        'append_sha256': _digest(out[len(source):]),
        'heap_start': APPEND_VA + APPEND_RESERVE,
        'remaining_reserved_bytes': APPEND_RESERVE - (len(out) - APPEND_FILE_OFFSET),
        'ksf_installed_files': [
            {'path': file.path, 'size': file.installed_size, 'sha256': file.installed_sha256}
            for file in corpus.files
        ],
        'ee_ranges': ee_ranges,
        'runtime_verified': False,
    }


def generate(elf: Path, pristine_elf: Path, iso: Path, ps2_adv: Path, ps4_adv: Path,
             research: Path, inventory: Path, supplement: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('choose a fresh output directory for the choice-only executable')
    source = elf.read_bytes()
    corpus = load_corpus(source, pristine_elf.read_bytes(), iso, ps2_adv, ps4_adv, research, inventory, supplement)
    executable, report = build(source, corpus)
    report['layout'] = {
        'font_descriptor': 0x5D77D0,
        'text_origin': [24, 22],
        'row_pitch': 39,
        'line_pitch': 18,
        'line_width_limit': LINE_WIDTH,
        'scratch_bytes_including_nul': MAX_ROW_BYTES + 1,
        'logical_reveal_limit': MAX_LOGICAL_GLYPHS,
        'cursor_screen_x_bounds': [4, 20],
        'cursor_screen_y_offset_bounds': [0, 17],
    }
    report['source_status_counts'] = dict(Counter(
        row.status for record in corpus.records for row in record.rows))
    report['native_record_slot_counts'] = dict(Counter(len(record.rows) for record in corpus.records))
    report['held_unproven_choices'] = 6
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temporary:
        stage = Path(temporary) / 'choices'
        stage.mkdir()
        (stage / '67.15o-ksf-choice-diagnostic.elf').write_bytes(executable)
        (stage / 'report.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
        stage.rename(output)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('elf', 'pristine-elf', 'iso', 'ps2-adv', 'ps4-adv', 'research',
                     'inventory', 'supplement', 'output'):
        parser.add_argument('--' + argument, required=True, type=Path)
    result = generate(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ('source_sha256', 'result_sha256', 'table', 'appended_extent')},
                     sort_keys=True))
