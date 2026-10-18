"""Test-only Unicorn harness for Kowloon's native EE glyph geometry builder.

The renderer instructions come from the supplied ELF and execute from
0x18CB50 through the return delay slot at 0x18E1F0. The harness only supplies a
render-context getter stub, input memory, and bounded EE compatibility for
SQ/LQ and the two COP1X accumulator instructions at 0x18E010/0x18E014.
It is an instruction-level static harness, not a PS2/GPU/rendering emulator.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from pathlib import Path
from typing import Sequence

from capstone import CS_ARCH_MIPS, CS_MODE_LITTLE_ENDIAN, CS_MODE_MIPS32, Cs
from unicorn import (UC_ARCH_MIPS, UC_HOOK_CODE, UC_HOOK_MEM_INVALID,
                     UC_MODE_LITTLE_ENDIAN, UC_MODE_MIPS64, Uc, UcError)
from unicorn import mips_const as reg


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = ROOT / "local/r67-15i-hant-text-item-details.elf"
ELF_BIAS = 0xFFF80
ELF_FIRST_FILE_OFFSET = 0x80
ELF_TRANSLATION_FILE_OFFSET = 0x803150
ELF_TRANSLATION_VA = 0x902F00
BUILDER_START = 0x18CB50
BUILDER_END = 0x18E1F4  # exclusive; includes jr ra and its delay slot
CONTEXT_GETTER = 0x1A0190
DEPTH_GLOBAL = 0x8DE238
FONT_DESCRIPTOR = 0x5D77D0

PRIVATE = 0x1101000
NODES = 0x1110000
UV_RECORDS = 0x1120000
CONTEXT = 0x1130000
STACK = 0x1F08000
RETURN = 0x1F00000
NODE_STRIDE = 0x130
TERMINATOR = 0xFFFFFF0F
MAX_INPUT_NODES = 512
MAX_INSTRUCTIONS = 250_000


@dataclass(frozen=True)
class Quad:
    left: float
    top: float


@dataclass(frozen=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class NodeSnapshot:
    address: int
    control: int
    quads: tuple[Quad, Quad, Quad, Quad]
    next_address: int


@dataclass(frozen=True)
class RenderResult:
    bounds: Bounds
    cursor_x: float
    cursor_y: float
    nodes: tuple[NodeSnapshot, ...]
    native_private: dict[int, int | float]
    getter_calls: int
    instruction_count: int


def _fword(value: float) -> int:
    return struct.unpack("<I", struct.pack("<f", value))[0]


def _float_at(uc: Uc, address: int) -> float:
    return struct.unpack("<f", uc.mem_read(address, 4))[0]


def _float_reg(uc: Uc, register: int) -> float:
    return struct.unpack("<f", struct.pack("<I", uc.reg_read(register) & 0xFFFFFFFF))[0]


def _instruction_word(raw: bytes, address: int) -> int:
    offset = address - ELF_BIAS
    if offset < 0 or offset + 4 > len(raw):
        raise ValueError(f"Native instruction address outside ELF: {address:#x}")
    return struct.unpack_from("<I", raw, offset)[0]


def _input_nodes(codes: str | Sequence[int]) -> list[int]:
    values = [
        0xFFFFFF0E if character == "\n" else 0xFFFFFF0B if character == " " else ord(character)
        for character in codes
    ] if isinstance(codes, str) else list(codes)
    if len(values) + 1 > MAX_INPUT_NODES:
        raise ValueError(f"At most {MAX_INPUT_NODES - 1} glyph/control inputs are supported")
    nodes: list[int] = []
    for value in values:
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"Input entries must be nonnegative codepoints or control words: {value!r}")
        if value > 0xFFFF and (value & 0xFFFFFF00) == 0xFFFFFF00:
            nodes.append(value & 0xFFFFFFFF)
        elif value > 0x10FFFF:
            raise ValueError(f"Not a Unicode codepoint or native control word: {value:#x}")
        else:
            nodes.append(value)
    nodes.append(TERMINATOR)
    return nodes


def _load_native_image(uc: Uc, raw: bytes) -> None:
    if len(raw) < ELF_TRANSLATION_FILE_OFFSET or raw[:4] != b"\x7fELF":
        raise ValueError("Expected the full r67 i ELF")
    if struct.unpack_from("<I", raw, 0x58)[0] != ELF_TRANSLATION_FILE_OFFSET:
        raise ValueError("Unexpected native ELF segment file offset")
    if struct.unpack_from("<I", raw, 0x5C)[0] != ELF_TRANSLATION_VA:
        raise ValueError("Unexpected native translation segment address")
    uc.mem_write(0x100000, raw[ELF_FIRST_FILE_OFFSET:ELF_TRANSLATION_FILE_OFFSET])
    uc.mem_write(ELF_TRANSLATION_VA, raw[ELF_TRANSLATION_FILE_OFFSET:])


def _lower64_sq_lq_compat(uc: Uc) -> tuple[int, ...]:
    """Map EE LQ/SQ opcodes to MIPS64 LD/SD in the private code copy.

    Only low 64-bit lanes are represented. Upper 64-bit vector lanes and
    vector-register side effects are deliberately outside this harness.
    """
    changed: list[int] = []
    for address in range(BUILDER_START, BUILDER_END, 4):
        word = struct.unpack("<I", uc.mem_read(address, 4))[0]
        opcode = word >> 26
        if opcode in (0x1E, 0x1F):
            replacement = (55 if opcode == 0x1E else 63) << 26 | (word & 0x03FFFFFF)
            uc.mem_write(address, struct.pack("<I", replacement))
            changed.append(address)
    return tuple(changed)


def _set_input_memory(uc: Uc, codes: list[int], *, scale_x: float, scale_y: float,
                      origin: tuple[float, float], letter_spacing: float,
                      line_spacing: float, orientation: int, font_descriptor: int) -> tuple[int, ...]:
    node_addresses = tuple(NODES + index * NODE_STRIDE for index in range(len(codes)))
    for index, (node, value) in enumerate(zip(node_addresses, codes, strict=True)):
        next_node = node_addresses[index + 1] if index + 1 < len(node_addresses) else 0
        is_control = value >= 0xFFFFFF00
        if is_control:
            glyph_pointer = value
            codepoint = 0xFFFF
        else:
            glyph_pointer = UV_RECORDS + index * 8
            codepoint = value & 0xFFFF
            # The native routine reads U,V as ushort values from the resource
            # pointer. Coordinates are varied deterministically but are not
            # interpreted as a proxy for glyph width.
            u = (index * 7) & 0xFF
            v = (index * 11) & 0xFF
            uc.mem_write(glyph_pointer, struct.pack("<HH", u, v))
        uc.mem_write(node, struct.pack("<I", glyph_pointer))
        uc.mem_write(node + 0x120, struct.pack("<I", next_node))
        uc.mem_write(node + 0x12E, struct.pack("<h", codepoint if codepoint < 0x8000 else codepoint - 0x10000))
        if not is_control:
            uc.mem_write(node + 0x110, struct.pack("<4f", 1.0, 1.0, 1.0, 1.0))

    uc.mem_write(PRIVATE + 0x04, struct.pack("<I", node_addresses[0]))
    uc.mem_write(PRIVATE + 0x10, struct.pack("<I", font_descriptor))
    uc.mem_write(PRIVATE + 0x14, struct.pack("<f", origin[0]))
    uc.mem_write(PRIVATE + 0x18, struct.pack("<f", origin[1]))
    uc.mem_write(PRIVATE + 0x24, struct.pack("<i", orientation))
    uc.mem_write(PRIVATE + 0x28, struct.pack("<f", letter_spacing))
    uc.mem_write(PRIVATE + 0x2C, struct.pack("<f", line_spacing))
    uc.mem_write(PRIVATE + 0x30, struct.pack("<f", 0.0))
    uc.mem_write(PRIVATE + 0x34, struct.pack("<I", 0xFFFFFFFF))
    uc.mem_write(PRIVATE + 0x48, struct.pack("<f", scale_x))
    uc.mem_write(PRIVATE + 0x4C, struct.pack("<f", scale_y))
    uc.mem_write(DEPTH_GLOBAL, struct.pack("<f", 0.0))
    uc.mem_write(CONTEXT + 0x80, struct.pack("<f", 1.0))
    return node_addresses


def render(raw: bytes, codes: str | Sequence[int], *, scale_x: float = 0.5,
           scale_y: float = 0.5, origin: tuple[float, float] = (26.0, 16.0),
           letter_spacing: float = 0.0, line_spacing: float = -9.0,
           orientation: int = 0, font_descriptor: int = FONT_DESCRIPTOR) -> RenderResult:
    """Execute the complete native glyph builder and return its actual writes.

    ``codes`` may be a string of Unicode codepoints, or integer codepoints
    mixed with native controls 0xFFFFFF0A/B/E/F. A terminator is appended.
    This input format creates the same linked-node representation consumed by
    the native routine; it does not compute glyph advances or quad positions.
    """
    if not all(math.isfinite(value) for value in (scale_x, scale_y, *origin, letter_spacing, line_spacing)):
        raise ValueError("Geometry controls must be finite floats")
    if orientation not in (0, 1):
        raise ValueError("Only the native horizontal and vertical orientations are modeled")
    values = _input_nodes(codes)
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS64 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0x100000, 0x900000)
    uc.mem_map(0x1100000, 0x100000)
    uc.mem_map(0x1F00000, 0x10000)
    _load_native_image(uc, raw)
    addresses = _set_input_memory(
        uc, values, scale_x=scale_x, scale_y=scale_y, origin=origin,
        letter_spacing=letter_spacing, line_spacing=line_spacing,
        orientation=orientation, font_descriptor=font_descriptor,
    )
    sq_lq_sites = _lower64_sq_lq_compat(uc)

    # The only external native dependency is the renderer-context getter.
    # It returns a small struct whose +0x80 field is the native divisor.
    uc.mem_write(CONTEXT_GETTER, struct.pack("<II", 0x03E00008, 0))  # jr ra; nop
    uc.reg_write(reg.UC_MIPS_REG_A0, PRIVATE)
    uc.reg_write(reg.UC_MIPS_REG_A1, orientation)
    uc.reg_write(reg.UC_MIPS_REG_S6, orientation)
    uc.reg_write(reg.UC_MIPS_REG_SP, STACK + 0x800)
    uc.reg_write(reg.UC_MIPS_REG_RA, RETURN)

    accumulator = 0.0
    getter_calls = 0
    instruction_count = 0
    unsupported: list[tuple[int, int]] = []
    final_cursor = (0.0, 0.0)
    invalid_memory: list[tuple[int, int, int]] = []

    def hook(engine: Uc, address: int, size: int, _data: object) -> None:
        nonlocal accumulator, getter_calls, instruction_count, final_cursor
        instruction_count += 1
        if address == RETURN:
            engine.emu_stop()
            return
        if address == 0x18E198:
            final_cursor = (
                _float_reg(engine, reg.UC_MIPS_REG_F21),
                _float_reg(engine, reg.UC_MIPS_REG_F20),
            )
        if address == CONTEXT_GETTER:
            getter_calls += 1
            engine.reg_write(reg.UC_MIPS_REG_V0, CONTEXT)
            engine.reg_write(reg.UC_MIPS_REG_PC, engine.reg_read(reg.UC_MIPS_REG_RA))
            return
        if address == 0x18E010:
            word = _instruction_word(raw, address)
            if word != 0x46190018:
                unsupported.append((address, word))
                engine.emu_stop()
                return
            accumulator = _float_reg(engine, reg.UC_MIPS_REG_F0) + _float_reg(engine, reg.UC_MIPS_REG_F25)
            engine.reg_write(reg.UC_MIPS_REG_PC, address + 4)
            return
        if address == 0x18E014:
            word = _instruction_word(raw, address)
            if word != 0x4601D81C:
                unsupported.append((address, word))
                engine.emu_stop()
                return
            value = accumulator + _float_reg(engine, reg.UC_MIPS_REG_F27) * _float_reg(engine, reg.UC_MIPS_REG_F1)
            engine.reg_write(reg.UC_MIPS_REG_F0, _fword(value))
            engine.reg_write(reg.UC_MIPS_REG_PC, address + 4)
            return
        if address < BUILDER_START or address >= BUILDER_END:
            unsupported.append((address, struct.unpack("<I", engine.mem_read(address, 4))[0]))
            engine.emu_stop()
            return

    uc.hook_add(UC_HOOK_CODE, hook)
    def invalid_hook(engine: Uc, _access: int, address: int, size: int,
                     _value: int, _data: object) -> bool:
        invalid_memory.append((engine.reg_read(reg.UC_MIPS_REG_PC), address, size))
        return False

    uc.hook_add(UC_HOOK_MEM_INVALID, invalid_hook)
    try:
        uc.emu_start(BUILDER_START, RETURN + 4, count=MAX_INSTRUCTIONS)
    except UcError as error:
        if invalid_memory:
            pc, address, size = invalid_memory[-1]
            raise RuntimeError(
                f"Native read/write fault at PC {pc:#x}, address {address:#x}, size {size}"
            ) from error
        raise RuntimeError(f"Native EE execution fault at PC {uc.reg_read(reg.UC_MIPS_REG_PC):#x}") from error
    if unsupported:
        address, word = unsupported[0]
        raise RuntimeError(f"Unexpected native instruction/dependency at {address:#x}: {word:#010x}")
    if instruction_count >= MAX_INSTRUCTIONS:
        raise RuntimeError("Native builder exceeded its instruction budget")
    expected_getters = sum(value < 0xFFFFFF00 for value in values)
    if getter_calls != expected_getters:
        raise RuntimeError(f"Expected {expected_getters} native context lookups, observed {getter_calls}")
    if not sq_lq_sites:
        raise RuntimeError("No EE SQ/LQ instructions were mapped in the native builder")

    snapshots: list[NodeSnapshot] = []
    points: list[Quad] = []
    for address in addresses:
        control = struct.unpack("<I", uc.mem_read(address, 4))[0]
        quads = tuple(
            Quad(*struct.unpack("<ff", uc.mem_read(address + offset, 8)))
            for offset in (0x10, 0x50, 0x90, 0xD0)
        )
        next_address = struct.unpack("<I", uc.mem_read(address + 0x120, 4))[0]
        snapshots.append(NodeSnapshot(address, control, quads, next_address))
        if control < 0xFFFFFF00:
            points.extend(quads)
    bounds = Bounds(
        min(point.left for point in points), min(point.top for point in points),
        max(point.left for point in points), max(point.top for point in points),
    ) if points else Bounds(origin[0], origin[1], origin[0], origin[1])
    private_values: dict[int, int | float] = {
        0x04: struct.unpack("<I", uc.mem_read(PRIVATE + 0x04, 4))[0],
        0x10: struct.unpack("<I", uc.mem_read(PRIVATE + 0x10, 4))[0],
        0x14: _float_at(uc, PRIVATE + 0x14),
        0x18: _float_at(uc, PRIVATE + 0x18),
        0x24: struct.unpack("<i", uc.mem_read(PRIVATE + 0x24, 4))[0],
        0x28: _float_at(uc, PRIVATE + 0x28),
        0x2C: _float_at(uc, PRIVATE + 0x2C),
        0x30: _float_at(uc, PRIVATE + 0x30),
        0x34: struct.unpack("<I", uc.mem_read(PRIVATE + 0x34, 4))[0],
        0x48: _float_at(uc, PRIVATE + 0x48),
        0x4C: _float_at(uc, PRIVATE + 0x4C),
    }
    return RenderResult(
        bounds, *final_cursor,
        tuple(snapshots), private_values, getter_calls, instruction_count,
    )


def disassemble_builder(raw: bytes) -> tuple[str, ...]:
    """Return Capstone's listing for diagnosis; never used to synthesize layout."""
    decoder = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    decoder.skipdata = True
    start = BUILDER_START - ELF_BIAS
    end = BUILDER_END - ELF_BIAS
    return tuple(
        f"{instruction.address:08x}: {instruction.mnemonic} {instruction.op_str}".rstrip()
        for instruction in decoder.disasm(raw[start:end], BUILDER_START)
    )
