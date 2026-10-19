"""Build and narrowly relocate a freestanding, audited R5900 layout kernel.

The compiler emits the MIPS II subset of the EE ISA. Generic MIPS unordered
comparisons are lowered to the EE's equivalent finite-input comparisons.
No shared-library loader, GP/GOT relocation, or external runtime is involved.
"""
from functools import lru_cache
import hashlib
import io
import struct
import subprocess

from tools.r67_15k_word_wrap import KERNEL


def audit_ee_cop1(code, base=0):
    """Check raw EE dispatch encodings, not generic MIPS mnemonic aliases."""
    single = {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
              0x16, 0x18, 0x19, 0x1a, 0x1c, 0x1d, 0x1e, 0x1f,
              0x24, 0x28, 0x29, 0x30, 0x32, 0x34, 0x36}
    for offset in range(0, len(code), 4):
        word = struct.unpack_from('<I', code, offset)[0]
        if word >> 26 != 17:
            continue
        form, function = word >> 21 & 31, word & 63
        valid = (form in (0, 2, 4, 6) or
                 (form == 8 and word >> 16 & 31 in (0, 1, 2, 3)) or
                 (form == 16 and function in single) or
                 (form == 20 and function == 0x20))
        if not valid:
            raise ValueError(f'unsupported EE COP1 instruction at {base + offset:#x}: {word:#010x}')


@lru_cache(maxsize=1)
def compile_object():
    import llvmlite
    from llvmlite import binding as llvm
    if llvmlite.__version__ != '0.50.0' or llvm.llvm_version_info != (22, 1, 0):
        raise ValueError('kernel build requires llvmlite 0.50.0 / LLVM 22.1.0')
    version = subprocess.run(['clang', '--version'], check=True,
                             capture_output=True, text=True).stdout.splitlines()[0]
    if version != 'Apple clang version 21.0.0 (clang-2100.1.1.101)':
        raise ValueError(f'unpinned C frontend: {version}')
    command = ['clang', '-cc1', '-triple', 'mipsel-none-elf', '-target-cpu',
               'mips2', '-target-abi', 'o32', '-target-feature', '-fp64',
               '-target-feature', '+single-float', '-emit-llvm', '-O2',
               '-ffreestanding', '-fno-builtin', '-ffp-contract=off', '-o', '-', str(KERNEL)]
    ir = subprocess.run(command, check=True, capture_output=True, text=True).stdout
    llvm.initialize_all_targets()
    llvm.initialize_all_asmprinters()
    module = llvm.parse_assembly(ir)
    module.verify()
    machine = llvm.Target.from_triple('mipsel-none-elf').create_target_machine(
        cpu='mips2', features='-fp64,+single-float', reloc='static',
        codemodel='small', opt=2)
    return machine.emit_object(module), version


def build_kernel(base):
    from elftools.elf.elffile import ELFFile
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
    obj, version = compile_object()
    elf = ELFFile(io.BytesIO(obj))
    output = bytearray()
    locations = {}
    for index, section in enumerate(elf.iter_sections()):
        if section.name not in ('.text', '.rodata.cst4'):
            if (section['sh_flags'] & 2 and section['sh_size'] and
                    section.name not in ('.reginfo', '.MIPS.abiflags')):
                raise ValueError(f'unexpected allocated section {section.name}')
            continue
        alignment = max(4, section['sh_addralign'])
        output.extend(bytes(-(base + len(output)) % alignment))
        locations[index] = len(output)
        output.extend(section.data())
    symbols = elf.get_section_by_name('.symtab')
    pending, count = {}, 0
    for section in elf.iter_sections():
        if section['sh_type'] != 'SHT_REL' or section['sh_info'] not in locations:
            continue
        target = locations[section['sh_info']]
        for relocation in section.iter_relocations():
            count += 1
            offset = target + relocation['r_offset']
            symbol_id = relocation['r_info_sym']
            symbol = symbols.get_symbol(symbol_id)
            if symbol['st_shndx'] not in locations:
                raise ValueError(f'unresolved kernel symbol: {symbol.name}')
            value = base + locations[symbol['st_shndx']] + symbol['st_value']
            word = struct.unpack_from('<I', output, offset)[0]
            kind = relocation['r_info_type']
            if kind == 4:  # R_MIPS_26: local absolute jumps
                destination = value + ((word & 0x3ffffff) << 2)
                if destination & 3 or destination >> 28 != (base + offset + 4) >> 28:
                    raise ValueError('jump relocation out of range')
                word = (word & 0xfc000000) | ((destination >> 2) & 0x3ffffff)
            elif kind == 5:  # R_MIPS_HI16, paired with signed LO16
                pending.setdefault(symbol_id, []).append((offset, word))
                continue
            elif kind == 6:
                low = (word & 0x7fff) - (word & 0x8000)
                highs = pending.pop(symbol_id, [])
                if not highs:
                    raise ValueError('unpaired LO16 relocation')
                for high_offset, high_word in highs:
                    full = value + ((high_word & 0xffff) << 16) + low
                    struct.pack_into('<I', output, high_offset,
                                     (high_word & 0xffff0000) | (((full + 0x8000) >> 16) & 0xffff))
                word = (word & 0xffff0000) | ((value + low) & 0xffff)
            else:
                raise ValueError(f'unsupported relocation type {kind}')
            struct.pack_into('<I', output, offset, word)
    if pending:
        raise ValueError('unpaired HI16 relocation')
    text = elf.get_section_by_name('.text')
    text_index = elf.get_section_index('.text')
    text_offset = locations[text_index]
    comparisons = 0
    for offset in range(text_offset, text_offset + text['sh_size'], 4):
        word = struct.unpack_from('<I', output, offset)[0]
        if word >> 26 == 17 and word >> 21 & 31 == 16 and word & 63 in (0x35, 0x37):
            # EE LT/LE are 34/36. 3C/3E exist on generic MIPS but not on EE.
            # Layout metrics are finite; unordered and ordered predicates agree.
            function = (word & 63) - 1
            struct.pack_into('<I', output, offset, (word & ~63) | function)
            comparisons += 1
    audit_ee_cop1(output[text_offset:text_offset + text['sh_size']], base + text_offset)
    legal = {'addiu', 'addu', 'and', 'andi', 'b', 'bc1f', 'bc1t', 'beq', 'beqz',
             'bne', 'bnez', 'j', 'jr', 'lbu', 'lhu', 'lui', 'lw', 'lwc1', 'move',
             'nop', 'or', 'ori', 'sll', 'slt', 'slti', 'sltiu', 'sltu', 'srl',
             'subu', 'sw', 'swc1', 'xor', 'xori', 'mtc1', 'mfc1', 'add.s',
             'sub.s', 'mul.s', 'mov.s', 'cvt.s.w', 'c.eq.s', 'c.olt.s', 'c.ole.s'}
    disassembler = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
    instructions = list(disassembler.disasm(output[text_offset:text_offset + text['sh_size']],
                                            base + text_offset))
    if len(instructions) * 4 != text['sh_size']:
        raise ValueError('kernel contains undecodable instructions')
    bad = [(hex(i.address), i.mnemonic, i.op_str) for i in instructions if i.mnemonic not in legal]
    if bad:
        raise ValueError(f'kernel contains unaudited instructions: {bad[:8]}')
    stacks = [(-struct.unpack('<h', struct.pack('<H', int.from_bytes(i.bytes, 'little') & 0xffff))[0])
              for i in instructions if i.mnemonic == 'addiu' and i.op_str.startswith('$sp, $sp, -')]
    if len(stacks) != 1 or stacks[0] > 1024:
        raise ValueError('unexpected kernel stack frame')
    entry = symbols.get_symbol_by_name('r67_description_wrap')[0]
    return bytes(output), {
        'entry_va': base + locations[entry['st_shndx']] + entry['st_value'],
        'source_sha256': hashlib.sha256(KERNEL.read_bytes()).hexdigest(),
        'object_sha256': hashlib.sha256(obj).hexdigest(),
        'code_sha256': hashlib.sha256(output).hexdigest(),
        'frontend': version, 'backend': 'llvmlite 0.50.0 / LLVM 22.1.0',
        'isa': 'MIPS II subset with EE finite comparisons',
        'relocations': count, 'unresolved_symbols': [], 'ee_comparisons': comparisons,
        'stack_bytes': stacks[0], 'text_size': text['sh_size'], 'size': len(output)}
