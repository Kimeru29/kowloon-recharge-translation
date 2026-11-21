from __future__ import annotations

from hashlib import sha256
import os
from pathlib import Path
import struct
import unittest

from tools import r67p_choice_geometry as choices

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ISO = ROOT / 'local/r67o-release/67.15o-cumulative-official-diagnostic.iso'
DEFAULT_ELF = ROOT / 'local/r67o-release/67.15o-cumulative-official-diagnostic.elf'
ISO = Path(os.environ.get('R67P_FINAL_ISO', DEFAULT_ISO))
ELF = Path(os.environ.get('R67P_FINAL_ELF', DEFAULT_ELF))
CUSTOM_INSTALLED = 'R67P_FINAL_ISO' in os.environ or 'R67P_FINAL_ELF' in os.environ


def _word(source: bytes, address: int) -> int:
    return struct.unpack_from('<I', source, address - choices.ELF_BIAS)[0]


def _jal_target(address: int, word: int) -> int:
    return ((address + 4) & 0xF0000000) | ((word & 0x03FFFFFF) << 2)


class StockChoiceOrientationTests(unittest.TestCase):
    def test_owner_patches_and_exact_o_preimages_or_installed_candidate(self):
        if not ELF.is_file():
            self.skipTest('Installed ELF is unavailable; set R67P_FINAL_ELF')
        source = ELF.read_bytes()
        if CUSTOM_INSTALLED:
            self.assertEqual(0x24060000, _word(source, 0x251588))
            for owner in (0x251594, 0x2516A8):
                self.assertEqual(3, _word(source, owner) >> 26, hex(owner))
                self.assertGreaterEqual(_jal_target(owner, _word(source, owner)), 0x800000)
            return

        code, patches = choices.patch(source, 0xA00000)
        self.assertEqual({0x251594 - choices.ELF_BIAS, 0x2516A8 - choices.ELF_BIAS}, set(patches))
        preimage, replacement = patches[0x251594 - choices.ELF_BIAS]
        self.assertEqual(bytes.fromhex('3c98260c'), preimage)
        self.assertEqual(choices.pack('<I', choices._jal(0xA00000)), replacement)
        setter_preimage, setter_replacement = patches[0x2516A8 - choices.ELF_BIAS]
        self.assertEqual(bytes.fromhex('d099260c'), setter_preimage)
        self.assertEqual(choices.pack('<I', choices._jal(0xA00000 + 20)), setter_replacement)
        self.assertIn(choices.pack('<I', choices._jal(choices.NATIVE_SCALE)), code)
        self.assertEqual(bytes.fromhex('00000624'), source[0x251588 - choices.ELF_BIAS:0x25158C - choices.ELF_BIAS])

    def test_rejects_changed_orientation_call_preimage(self):
        source = bytearray(DEFAULT_ELF.read_bytes())
        source[0x251594 - choices.ELF_BIAS:0x251598 - choices.ELF_BIAS] = b'nope'
        with self.assertRaisesRegex(ValueError, 'choice orientation call preimage'):
            choices.patch(bytes(source), 0xA00000)

    def test_installed_iso_contains_the_selected_elf(self):
        if not ISO.is_file() or not ELF.is_file():
            self.skipTest('Installed ISO/ELF unavailable; set R67P_FINAL_ISO and R67P_FINAL_ELF')
        from tools.r67o_inventory import Disc

        image = ISO.read_bytes()
        installed_elf = Disc(image).elf
        self.assertEqual(sha256(ELF.read_bytes()).hexdigest(), sha256(installed_elf).hexdigest())
        if not CUSTOM_INSTALLED:
            self.assertEqual('049b68c70c74f99b195975000c90e064b5106cbe18cf0dc89f87b44526081b13',
                             sha256(image).hexdigest())
            self.assertEqual('fd4760a3c96260ef0fde8cf113a9cc49d46fe732a7f7b0087357f612f1182787',
                             sha256(installed_elf).hexdigest())
