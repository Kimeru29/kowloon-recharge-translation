"""Diagnostic execution harness for the native r67 item-text pipeline.

The ELF's EE instructions remain the source of truth. This harness reports
external calls instead of pretending to model them; callbacks can be added
only when a concrete execution proves they are required.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import struct
import zipfile
from typing import Callable

from unicorn import (
    Uc, UcError, UC_ARCH_MIPS, UC_HOOK_CODE, UC_HOOK_MEM_INVALID,
    UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64,
)
from unicorn import mips_const as reg


ROOT = Path(__file__).resolve().parents[1]
ELF = ROOT / "local/r67-15j-generic-text-bounds.elf"
BIAS = 0xFFF80
TEXT_FILE_OFFSET = 0x803150
TEXT_VA = 0x902F00
CONSTRUCTOR = 0x189E40
CONVERTER = 0x1952F0
NODE_BUILDER = 0x192400
GLYPH_BUILDER = 0x18CB50
NATIVE_GP = 0x79B1F0
DETAILS_TABLE = 0x974EA8
MEMCPY = 0x39C3B8
RUNTIME_SNAPSHOT = ROOT / "local/r67-14o-user-slot03-forensic.p2s"
RUNTIME_FONT_16X18 = 0x00FE4C80
OUTPUT = 0x1110000
RETURN = 0x1F00000
STACK = 0x1F08000
NATIVE_NODE_ALLOC = 0x1051F0
NATIVE_RESOURCE_ACQUIRE = 0x354FF0
NATIVE_RESOURCE_RELEASE = 0x354BE0


def _word(source: bytes, address: int) -> int:
    return struct.unpack_from("<I", source, address - BIAS)[0]


def direct_calls(source: bytes, start: int, end: int) -> tuple[tuple[int, int], ...]:
    """Return real JAL sites and targets from an ELF virtual-address range."""
    found = []
    for pc in range(start, end, 4):
        instruction = _word(source, pc)
        if instruction >> 26 == 3:
            target = ((pc + 4) & 0xF0000000) | ((instruction & 0x03FFFFFF) << 2)
            found.append((pc, target))
    return tuple(found)


@dataclass
class Execution:
    returned: bool
    pc: int
    v0: int
    calls: list[tuple[int, int, int, int]] = field(default_factory=list)
    steps: int = 0
    tail: tuple[int, ...] = ()
    watched: list[tuple[int, int, int, int, int]] = field(default_factory=list)


class NativeTextPipeline:
    """Run unmodified ELF routines with explicitly supplied external stubs."""

    def __init__(self, source: bytes | None = None, runtime_ee: bytes | None = None,
                 lower_ranges=()):
        self.source = source if source is not None else ELF.read_bytes()
        if self.source[:4] != b"\x7fELF" or len(self.source) < TEXT_FILE_OFFSET:
            raise ValueError("expected the complete 15j ELF")
        if struct.unpack_from("<I", self.source, 0x58)[0] != TEXT_FILE_OFFSET:
            raise ValueError("unexpected text segment file offset")
        if struct.unpack_from("<I", self.source, 0x5C)[0] != TEXT_VA:
            raise ValueError("unexpected text segment virtual address")
        self.uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
        self.uc.mem_map(0x100000, 0x900000)
        self.uc.mem_map(0x1100000, 0x100000)
        self.uc.mem_map(0x1F00000, 0x10000)
        self.uc.mem_write(0x100000, self.source[0x80:TEXT_FILE_OFFSET])
        self.uc.mem_write(TEXT_VA, self.source[TEXT_FILE_OFFSET:])
        # Unicorn does not implement EE LQ/SQ. This matches the established
        # geometry harness: lower only these opcodes in the private image copy.
        for start, end in ((CONSTRUCTOR, 0x18A300), (NODE_BUILDER, 0x193180),
                           (CONVERTER, 0x196000), (GLYPH_BUILDER, 0x18E1F4),
                           (0x9765DC, 0x976A48), (0x188420, 0x188940), *lower_ranges):
            for address in range(start, end, 4):
                word = struct.unpack("<I", self.uc.mem_read(address, 4))[0]
                opcode = word >> 26
                if opcode in (0x1E, 0x1F):
                    lowered_opcode = 55 if opcode == 0x1E else 63
                    lowered = (word & 0x03FFFFFF) | (lowered_opcode << 26)
                    self.uc.mem_write(address, struct.pack("<I", lowered))
        if runtime_ee is not None:
            if len(runtime_ee) != 0x2000000:
                raise ValueError("expected a 32 MiB historical EE memory image")
            # Keep the fixture's live resource heaps while the current j ELF
            # remains the code/data image in the lower EE ranges.
            self.uc.mem_map(0xA00000, 0x700000)
            self.uc.mem_map(0x1200000, 0xD00000)
            self.uc.mem_map(0x1F10000, 0xF0000)
            for start, end in ((0xA00000, 0x1100000),
                               (0x1200000, 0x1F00000)):
                self.uc.mem_write(start, runtime_ee[start:end])
            # The ELF contains zeroed runtime resource fields here; retain the
            # initialized 16x18/12x12 descriptor records from this save only.
            self.uc.mem_write(0x5D77D0, runtime_ee[0x5D77D0:0x5D7DA0])
        self.uc.reg_write(reg.UC_MIPS_REG_SP, STACK)
        self.uc.reg_write(reg.UC_MIPS_REG_RA, RETURN)
        # The native text conversion routines use GP-relative static tables.
        self.uc.reg_write(reg.UC_MIPS_REG_GP, NATIVE_GP)

    def execute(self, start: int, *, args: tuple[int, int, int, int] = (0, 0, 0, 0),
                stop_at: tuple[int, ...] = (),
                external: dict[int, Callable[[Uc], None]] | None = None,
                watch_addresses: tuple[int, ...] = (),
                instruction_limit: int = 250_000) -> Execution:
        """Execute native code; only explicitly listed addresses are stubbed.

        A stop address is observed before its instruction executes. Every
        non-stop call target is allowed to execute from the same ELF image.
        """
        callbacks = external or {}
        calls: list[tuple[int, int, int, int]] = []
        watched: list[tuple[int, int, int, int, int]] = []
        steps = 0
        stopped = False
        recent: list[int] = []
        invalid: list[tuple[int, int, int, int]] = []
        accumulator = 0.0

        def hook(engine: Uc, address: int, _size: int, _data: object) -> None:
            nonlocal steps, stopped, accumulator
            steps += 1
            recent.append(address)
            if len(recent) > 12:
                del recent[0]
            if address == RETURN or address in stop_at:
                stopped = True
                engine.emu_stop()
                return
            instruction = struct.unpack('<I', engine.mem_read(address, 4))[0]
            if NODE_BUILDER <= address < 0x193180 and instruction >> 26 == 0 and instruction & 63 == 24:
                # EE MULT rd,rs,rt also writes the low signed word to rd.
                # MIPS64's ordinary MULT ignores rd; emulate this one opcode.
                rs, rt, rd = (instruction >> n & 31 for n in (21, 16, 11))
                if rd:
                    def signed_word(value):
                        return struct.unpack('<i', struct.pack('<I', value & 0xFFFFFFFF))[0]
                    product = signed_word(engine.reg_read(reg.UC_MIPS_REG_0 + rs)) * signed_word(engine.reg_read(reg.UC_MIPS_REG_0 + rt))
                    lo, hi = signed_word(product), signed_word(product >> 32)
                    engine.reg_write(reg.UC_MIPS_REG_0 + rd, lo & 0xFFFFFFFFFFFFFFFF)
                    engine.reg_write(reg.UC_MIPS_REG_LO, lo & 0xFFFFFFFFFFFFFFFF)
                    engine.reg_write(reg.UC_MIPS_REG_HI, hi & 0xFFFFFFFFFFFFFFFF)
                    engine.reg_write(reg.UC_MIPS_REG_PC, address + 4)
                    return
            if address in (0x18E010, 0x18E014):
                def fp(index):
                    return struct.unpack('<f', struct.pack('<I', engine.reg_read(reg.UC_MIPS_REG_F0 + index) & 0xFFFFFFFF))[0]
                if address == 0x18E010:
                    if instruction != 0x46190018:
                        raise AssertionError('native ADDA.S preimage changed')
                    accumulator = fp(0) + fp(25)
                else:
                    if instruction != 0x4601D81C:
                        raise AssertionError('native MADD.S preimage changed')
                    value = accumulator + fp(27) * fp(1)
                    engine.reg_write(reg.UC_MIPS_REG_F0, struct.unpack('<I', struct.pack('<f', value))[0])
                engine.reg_write(reg.UC_MIPS_REG_PC, address + 4)
                return
            if address in callbacks:
                calls.append((address, *(engine.reg_read(r) & 0xFFFFFFFF for r in (
                    reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1,
                    reg.UC_MIPS_REG_A2, reg.UC_MIPS_REG_A3))))
                callbacks[address](engine)
            elif address in watch_addresses:
                watched.append((address, *(engine.reg_read(r) & 0xFFFFFFFF for r in (
                    reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1,
                    reg.UC_MIPS_REG_A2, reg.UC_MIPS_REG_A3))))

        hook_id = self.uc.hook_add(UC_HOOK_CODE, hook)
        invalid_id = self.uc.hook_add(
            UC_HOOK_MEM_INVALID,
            lambda _engine, access, address, size, value, _data:
            invalid.append((access, address, size, value)) or False,
        )
        try:
            for register, value in zip((reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1,
                                        reg.UC_MIPS_REG_A2, reg.UC_MIPS_REG_A3), args):
                self.uc.reg_write(register, value)
            self.uc.reg_write(reg.UC_MIPS_REG_SP, STACK)
            self.uc.reg_write(reg.UC_MIPS_REG_RA, RETURN)
            self.uc.reg_write(reg.UC_MIPS_REG_GP, NATIVE_GP)
            try:
                self.uc.emu_start(start, RETURN, count=instruction_limit)
            except UcError as error:
                pc = self.uc.reg_read(reg.UC_MIPS_REG_PC) & 0xFFFFFFFF
                trail = ", ".join(hex(address) for address in recent)
                observed = {
                    name: hex(self.uc.reg_read(register) & 0xFFFFFFFF)
                    for name, register in (("a0", reg.UC_MIPS_REG_A0),
                                           ("a1", reg.UC_MIPS_REG_A1),
                                           ("a2", reg.UC_MIPS_REG_A2),
                                           ("a3", reg.UC_MIPS_REG_A3),
                                           ("t0", reg.UC_MIPS_REG_T0),
                                           ("v0", reg.UC_MIPS_REG_V0),
                                           ("v1", reg.UC_MIPS_REG_V1),
                                           ("gp", reg.UC_MIPS_REG_GP))
                }
                raise RuntimeError(f"native execution stopped at {pc:#x}: {error}; "
                                   f"last instructions: {trail}; regs: {observed}; "
                                   f"invalid memory: {invalid}") from error
        finally:
            self.uc.hook_del(hook_id)
            self.uc.hook_del(invalid_id)
        pc = self.uc.reg_read(reg.UC_MIPS_REG_PC)
        return Execution(stopped or pc == RETURN, pc,
                         self.uc.reg_read(reg.UC_MIPS_REG_V0) & 0xFFFFFFFF,
                         calls, steps, tuple(recent), watched)


def load_historical_ee_memory() -> bytes:
    """Read the historical resource fixture without changing the saved state."""
    if not RUNTIME_SNAPSHOT.is_file():
        raise FileNotFoundError(RUNTIME_SNAPSHOT)
    with zipfile.ZipFile(RUNTIME_SNAPSHOT) as archive:
        return archive.read('eeMemory.bin')


def source_strings(source: bytes) -> dict[int, str]:
    """Read official corpus samples through the existing native catalogue map."""
    from tools.r67_15g_item_details import (
        CORPUS_PATH, collect_catalogue, load_official_rows,
        map_official_descriptions,
    )

    # 15j redirects the constructor hook; catalogue discovery needs the
    # pristine call word while retaining the 15j descriptor and table bytes.
    catalogue_view = bytearray(source)
    struct.pack_into("<I", catalogue_view, 0x1520C, 0x0C062790)
    records = collect_catalogue(bytes(catalogue_view))
    mapped, _unresolved = map_official_descriptions(
        records, load_official_rows(CORPUS_PATH)
    )
    wanted = (20, 68, 334, 339)
    return {item_id: mapped[item_id] for item_id in wanted}


def detail_string_addresses(source: bytes, item_ids: tuple[int, ...]) -> dict[int, int]:
    """Resolve actual sparse Details pointers from the 15j native table."""
    from tools.r67_15i_item_details import _va_to_offset

    table = _va_to_offset(source, DETAILS_TABLE)
    if table is None:
        raise ValueError("15j Details pointer table is not file-backed")
    result = {}
    for item_id in item_ids:
        pointer = struct.unpack_from("<I", source, table + item_id * 4)[0]
        if pointer == 0 or _va_to_offset(source, pointer) is None:
            raise ValueError(f"Details item {item_id} has no native string pointer")
        result[item_id] = pointer
    return result

def detail_string_byte_lengths(source: bytes, item_ids: tuple[int, ...]) -> dict[int, int]:
    from tools.r67_15i_item_details import _va_to_offset

    addresses = detail_string_addresses(source, item_ids)
    result = {}
    for item_id, address in addresses.items():
        offset = _va_to_offset(source, address)
        end = source.find(b"\0", offset, min(len(source), offset + 4096))
        if end < 0:
            raise ValueError(f"Details item {item_id} has no bounded native terminator")
        result[item_id] = end - offset
    return result


def decode_native_units(uc: Uc, address: int, *, maximum: int = 512) -> list[int]:
    """Read the converter's NUL-terminated 16-bit output without normalizing it."""
    result = []
    for index in range(maximum):
        value = struct.unpack("<H", uc.mem_read(address + index * 2, 2))[0]
        if value == 0:
            return result
        result.append(value)
    raise ValueError("native converter output exceeded the diagnostic bound")
