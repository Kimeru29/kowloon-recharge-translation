import json
import os
import struct
import unittest
from pathlib import Path

from unicorn import UC_HOOK_CODE

from tests.test_r67o_choices_pipeline import ChoiceMachine, STATE, TASK_DATA
from tools.r67_chamber_story_text_only import ELF_BIAS, ELF_SEGMENT_FO, ELF_SEGMENT_VA
from tools.r67o_inventory import open_disc
from tools.r67p_speaker_geometry import patch


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "local/r67p-speaker-evidence"
OWNER_CALL = 0x250010


def machine(elf: bytes) -> ChoiceMachine:
    report = json.loads((ROOT / "local/r67o-choices/report.json").read_bytes())
    harness = ChoiceMachine(elf, report)
    for low, high in ((0x188AD0, 0x189E40), (0x251F80, 0x2525E0)):
        for address in range(low, high, 4):
            word = harness.read32(address)
            opcode = word >> 26
            if opcode in (30, 31):
                harness.put32(address, (word & 0x03FFFFFF) | ((55 if opcode == 30 else 63) << 26))
    harness.ee.hook_add(UC_HOOK_CODE, harness.ee_arithmetic, begin=0x251FC4, end=0x2525DF)
    return harness


def draw(elf: bytes, text: str) -> tuple[list, bytes]:
    harness = machine(elf)
    harness.write(STATE + 0x198, text.encode("cp932") + b"\0")
    harness.set_reg(16, TASK_DATA)
    handle = harness.run(0x24FFC8, stop_at=(0x250004,)).v0
    harness.run(OWNER_CALL, handle, 200, stop_at=(0x250018,))
    harness.run(0x18B9B0, handle)
    font_data = harness.tasks[handle][3]
    return harness.submitted[1::2], harness.cstring(font_data + 0x51, 102)


class SpeakerGeometryNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline_iso = ROOT / "local/r67o-release/67.15o-cumulative-official-diagnostic.iso"
        baseline_elf = ROOT / "local/r67o-release/67.15o-cumulative-official-diagnostic.elf"
        cls.baseline = baseline_elf.read_bytes()
        with open_disc(baseline_iso) as disc:
            if disc.elf != cls.baseline:
                raise AssertionError("Pinned r67.15o ELF differs from its installed ISO")
        appended_offset = (len(cls.baseline) + 15) & ~15
        base = ELF_SEGMENT_VA + appended_offset - ELF_SEGMENT_FO
        helper, cls.changes = patch(cls.baseline, base)
        candidate = bytearray(cls.baseline + b"\0" * (appended_offset - len(cls.baseline)) + helper)
        for offset, (expected, replacement) in cls.changes.items():
            if candidate[offset:offset + len(expected)] != expected:
                raise AssertionError(f"unexpected owner preimage at {offset:#x}")
            candidate[offset:offset + len(expected)] = replacement
        struct.pack_into("<I", candidate, 0x64, len(candidate) - 0x803150)
        cls.candidate = bytes(candidate)
        final_iso = os.environ.get("R67P_FINAL_ISO")
        final_elf = os.environ.get("R67P_FINAL_ELF")
        if bool(final_iso) != bool(final_elf):
            raise AssertionError("Set both R67P_FINAL_ISO and R67P_FINAL_ELF together")
        if final_iso:
            cls.installed = Path(final_elf).read_bytes()
            with open_disc(Path(final_iso)) as disc:
                if disc.elf != cls.installed:
                    raise AssertionError("R67P_FINAL_ELF differs from the executable installed in R67P_FINAL_ISO")
        else:
            cls.installed = cls.candidate
        cls.candidates = tuple(dict.fromkeys((cls.candidate, cls.installed)))
        cls.header_results = json.loads((EVIDENCE / "baseline-header-draws.json").read_bytes())["results"]

    def test_owner_scale_change_fits_measured_headers_and_preserves_complete_text(self):
        self.assertEqual(set(self.changes), {OWNER_CALL - ELF_BIAS})
        self.assertEqual(self.changes[OWNER_CALL - ELF_BIAS][0], self.baseline[OWNER_CALL - ELF_BIAS:OWNER_CALL - ELF_BIAS + 4])
        for row in self.header_results:
            baseline_quads, baseline_text = draw(self.baseline, row["text"])
            for candidate in self.candidates:
                quads, rendered = draw(candidate, row["text"])
                vertices = [vertex for quad in quads for vertex in quad]
                self.assertEqual(rendered, baseline_text)
                self.assertEqual(len(quads), len(baseline_quads), row["text"])
                self.assertTrue(vertices, row["text"])
                self.assertGreaterEqual(min(vertex[0] for vertex in vertices), 0, row["text"])
                self.assertLessEqual(max(vertex[0] for vertex in vertices), 511, row["text"])
                self.assertLessEqual(max(vertex[1] for vertex in vertices), 293, row["text"])
                self.assertGreaterEqual(min(vertex[1] for vertex in vertices), 276, row["text"])

    def test_negative_owner_preimage_mutation_is_rejected(self):
        altered = bytearray(self.baseline)
        altered[OWNER_CALL - ELF_BIAS] ^= 1
        with self.assertRaisesRegex(ValueError, "Speaker owner preimage differs"):
            patch(bytes(altered), ELF_SEGMENT_VA + ((len(altered) + 15) & ~15) - ELF_SEGMENT_FO)

    def test_short_japanese_header_keeps_exact_baseline_geometry(self):
        for label in ("【Maya】", "【声】"):
            baseline_quads, baseline_text = draw(self.baseline, label)
            for candidate in self.candidates:
                candidate_quads, candidate_text = draw(candidate, label)
                self.assertEqual(candidate_text, baseline_text)
                self.assertEqual(candidate_quads, baseline_quads)


if __name__ == "__main__":
    unittest.main()
