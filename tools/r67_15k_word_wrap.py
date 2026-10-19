"""Host adapter for the same freestanding C kernel installed in the EE image."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import struct
import subprocess
import tempfile

KERNEL = Path(__file__).with_name('native') / 'r67_description_wrap.c'


class Context(ctypes.Structure):
    _fields_ = [('fonts', ctypes.c_uint32 * 4), ('count', ctypes.c_uint32),
                ('flags', ctypes.c_uint32), ('left', ctypes.c_float),
                ('top', ctypes.c_float), ('width', ctypes.c_float),
                ('height', ctypes.c_float), ('space_ratio', ctypes.c_float),
                ('factor', ctypes.c_float), ('rows', ctypes.c_uint32)]


@lru_cache(maxsize=1)
def host_kernel():
    directory = tempfile.TemporaryDirectory(prefix='kowloon-wrap-')
    library = Path(directory.name) / 'wrap.dylib'
    subprocess.run(['clang', '-shared', '-O2', '-ffreestanding', '-fno-builtin',
                    '-ffp-contract=off', str(KERNEL), '-o', str(library)], check=True)
    loaded = ctypes.CDLL(str(library))
    function = loaded.r67_description_wrap
    function.argtypes = [ctypes.c_void_p, ctypes.POINTER(Context)]
    function.restype = ctypes.c_int
    # Keep the library and private temporary directory alive with the function.
    function._resources = (directory, loaded)
    return function


@dataclass(frozen=True)
class Quad:
    left: float
    top: float
    right: float
    bottom: float


@dataclass(frozen=True)
class Result:
    lines: tuple[str, ...]
    quads: tuple[Quad, ...]
    factor: float


def fixture(paragraphs, *, width, height, scale, space_ratio=1.,
            font_width=16, font_height=18, tracking=0., line_gap=0., soft=False):
    """Build native-shaped nodes without replacing the native-parser tests."""
    if not 1 <= len(paragraphs) <= 4:
        raise ValueError('one to four fields required')
    ram = bytearray(0x2000000)
    context = Context(count=len(paragraphs), flags=int(soft), width=width,
                      height=height, space_ratio=space_ratio)
    cursor = 0x10000
    visible = []
    for index, text in enumerate(paragraphs):
        font, descriptor = 0x2000 + index * 0x300, 0x4000 + index * 8
        context.fonts[index] = font
        struct.pack_into('<I', ram, font + 4, cursor)
        struct.pack_into('<I', ram, font + 0x10, descriptor)
        ram[descriptor + 4:descriptor + 6] = bytes((font_width, font_height))
        struct.pack_into('<ff', ram, font + 0x28, tracking, line_gap)
        struct.pack_into('<ff', ram, font + 0x48, scale, scale)
        for char in text + '\0':
            control = {' ': 0xffffff0b, '　': 0xffffff0b,
                       '\n': 0xffffff0e, '\0': 0xffffff0f}.get(char, 0x5000)
            struct.pack_into('<I', ram, cursor, control)
            struct.pack_into('<I', ram, cursor + 0x120,
                             cursor + 0x130 if char != '\0' else 0)
            if control == 0x5000:
                visible.append((cursor, char))
            cursor += 0x130
    return ram, context, visible


def invoke(ram, context):
    buffer = (ctypes.c_ubyte * len(ram)).from_buffer(ram)
    return host_kernel()(buffer, ctypes.byref(context))


def layout_text(paragraphs, **metrics):
    ram, context, visible = fixture(paragraphs, **metrics)
    if not invoke(ram, context):
        raise ValueError('unsupported native layout input')
    quads, lines = [], []
    last_y, last_node = None, None
    for node, char in visible:
        x, y = struct.unpack_from('<ff', ram, node + 0x10)
        right, bottom = struct.unpack_from('<ff', ram, node + 0xd0)
        quads.append(Quad(x, y, right, bottom))
        if y != last_y:
            lines.append(char)
        else:
            # Fixture nodes are sequential; intervening nodes are separators.
            lines[-1] += (' ' if node != last_node + 0x130 else '') + char
        last_y, last_node = y, node
    return Result(tuple(lines), tuple(quads), context.factor)
