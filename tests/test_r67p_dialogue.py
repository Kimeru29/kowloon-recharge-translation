"""Native primary dialogue, name expansion and START-history regression probes."""
from __future__ import annotations

import os
from pathlib import Path
from struct import pack_into, unpack_from
import unittest

from unicorn import UC_HOOK_CODE

from tests.r67_native_text_pipeline import NATIVE_GP
from tests.test_r67o_choices_pipeline import FAMILY, GIVEN, STATE, TASK_DATA, wide
from tests.test_r67p_caption_geometry import BASELINE, CHOICE_REPORT, SCRIPT, draw, geometry, machine


def add_scope(h, low, high):
    for address in range(low, high, 4):
        word = h.read32(address)
        if word >> 26 in (30, 31):
            h.put32(address, (word & 0x3FFFFFF) | ((55 if word >> 26 == 30 else 63) << 26))
    h.ee.hook_add(UC_HOOK_CODE, h.ee_arithmetic, begin=low, end=high - 1)


def play_body(source, rows, family, given, test, *, check_canaries=False):
    h = machine(source)
    for low, high in ((0x24D0A0, 0x24D5A0), (0x24D970, 0x251000),
                      (0x251EC0, 0x251F80), (0x252B80, 0x253730)):
        add_scope(h, low, high)
    h.font_atlas(1)
    h.put32(NATIVE_GP - 0x1D74, h.alloc(0x80))
    h.write(FAMILY, family.ljust(32, b"\0"))
    h.write(GIVEN, given.ljust(32, b"\0"))
    h.write(SCRIPT, b"r".join(rows) + b"rwc\0")
    h.run(0x24E690, TASK_DATA, SCRIPT)
    owner = next(handle for handle, task in h.tasks.items() if task[1] == 0x24E920)
    h.run(0x24E920, owner)
    handles = [handle for handle, task in h.tasks.items() if task[1] == 0x18B9B0]
    handles = [handle for handle in handles if h.cstring(h.tasks[handle][3] + 0x51, 102)]
    test.assertEqual(len(handles), len(rows))
    animators = [handle for handle, task in h.tasks.items() if task[1] == 0x18C7B0
                 and h.read32(task[3] + 8) in handles]
    test.assertEqual(len(animators), len(rows))
    for _ in range(5):
        for animator in animators:
            h.run(0x18C7B0, animator)

    captures = []
    for handle in handles:
        font = h.tasks[handle][3]
        h.run(0x18B100, handle, 200)
        h.set_reg(8, 255)
        h.run(0x18B060, handle, 255, 255, 255)
        quads = draw(h, handle, 0x18B9B0)
        captures.append((h.cstring(font + 0x51, 102), len(quads) // 2,
                         geometry([v for quad in quads for v in quad])))
    if check_canaries:
        h.assert_canaries(test)
    return captures


@unittest.skipUnless(BASELINE.is_file() and CHOICE_REPORT.is_file(), "Pinned r67.15o fixtures are unavailable")
class AdvBodyGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = BASELINE.read_bytes()
        if supplied := os.getenv("R67P_FINAL_ELF"):
            cls.candidate = Path(supplied).read_bytes()
        elif os.getenv("R67P_DIALOGUE_BASELINE_RED"):
            cls.candidate = cls.baseline
        else:
            from tools.r67p_dialogue_geometry import patch
            candidate = bytearray(cls.baseline)
            file, va = unpack_from("<II", candidate, 0x58)
            code, writes = patch(cls.baseline, va + len(candidate) - file)
            for offset, (expected, replacement) in writes.items():
                assert candidate[offset:offset + len(expected)] == expected
                candidate[offset:offset + len(expected)] = replacement
            candidate.extend(code)
            pack_into("<I", candidate, 0x64, len(candidate) - file)
            cls.candidate = bytes(candidate)

    def test_three_rows_with_name_substitution_long_body_and_mixed_glyphs(self):
        rows = (wide("Hello ") + b"pm" + wide(" and ") + b"pn" + wide("!"),
                wide("A" * 38), "混合".encode("cp932") + wide(" English"))
        for family, given in ((wide("Hab"), wide("Kur")), (wide("Max"), wide("Ace"))):
            with self.subTest(name_cells=len(family) // 2):
                baseline = play_body(self.baseline, rows, family, given, self)
                result = play_body(self.candidate, rows, family, given, self, check_canaries=True)
                self.assertEqual([row[:2] for row in result], [row[:2] for row in baseline])
                self.assertEqual(result[0][0], wide("Hello ") + family + wide(" and ") + given + wide("!"))
                self.assertEqual(result[1][0], rows[1])
                self.assertEqual(result[2], baseline[2])
                self.assertEqual([row[2][1] for row in result], [300., 316., 332.])
                self.assertEqual(baseline[1][2][2], 932.)
                self.assertTrue(all(row[2][2] <= 510. for row in result))

    def test_large_padded_row_fits_without_altering_glyphs(self):
        word = wide("A" * 10 + " " * 20 + "Z" * 10)
        original = play_body(self.baseline, (word,), b"", b"", self)[0]
        fitted = play_body(self.candidate, (word,), b"", b"", self, check_canaries=True)[0]
        self.assertEqual(fitted[:2], original[:2])
        self.assertEqual(fitted[1], 20)
        self.assertLessEqual(fitted[2][2], 510.)

    def test_short_and_long_primary_reveal_allocation_and_negative_mutation(self):
        from tools.r67p_dialogue_geometry import REVEAL_CALL
        from tools.r67_chamber_story_text_only import ELF_BIAS

        rows = (wide("A" * 38),)
        result = play_body(self.candidate, rows, b"", b"", self, check_canaries=True)
        self.assertEqual(result[0][1], 38)
        altered = bytearray(self.candidate)
        offset = REVEAL_CALL - ELF_BIAS
        altered[offset:offset + 4] = self.baseline[offset:offset + 4]
        with self.assertRaises(AssertionError):
            play_body(bytes(altered), rows, b"", b"", self, check_canaries=True)


@unittest.skipUnless(BASELINE.is_file() and CHOICE_REPORT.is_file(), "Pinned r67.15o fixtures are unavailable")
class HistoryNavigationProbe(unittest.TestCase):
    """Record the live initial layout and scroll transition outside the approved example."""

    def test_initial_chronology_and_older_page_reconstruction(self):
        import json
        from unicodedata import normalize

        source = Path(os.getenv("R67P_FINAL_ELF", str(BASELINE))).read_bytes()
        evidence = {}
        for count in (6, 18):
            h = machine(source)
            for lo, hi in ((0x252F80, 0x256B00), (0x963A50, 0x963CC0), (0x24D970, 0x24E680)):
                add_scope(h, lo, hi)
            for style in (3, 4, 5):
                h.font_atlas(style)
            # Rendering tasks run; audible navigation and the decorative history
            # indicator are outside the text-view harness.
            h.external.update({0x1697B0: h.noop, 0x256040: h.noop, 0x256400: h.noop, 0x255EA0: h.noop})
            for index in range(count):
                prefix = wide("Speaker" if index % 2 == 0 else "Body")
                mixed = "混合".encode("cp932") if index % 5 == 0 else b""
                raw = prefix + mixed + wide(f" {index:02}") + b"r\0"
                address = h.alloc(len(raw))
                h.write(address, raw)
                h.run(0x253000, address, 1)
            owner, private = h.alloc(0x44), h.alloc(0x1C0)
            h.put32(owner + 0x3C, private)
            constructor_callers = set()

            def record_constructor_caller(_engine, _address, _size, _data):
                constructor_callers.add(h.reg(31) - 8)

            # Observe the native history row constructor entry and derive the
            # caller from live RA, since q relocates this call into its helper.
            h.ee.hook_add(UC_HOOK_CODE, record_constructor_caller,
                          begin=0x255E10, end=0x255E10)

            def current_rows():
                rows = []
                for i in range(h.read16(private + 0x7A)):
                    font = h.tasks[h.read32(private + 0x20 + i * 4)][3]
                    text = normalize("NFKC", h.cstring(font + 0x51).decode("cp932"))
                    x, y = h.floats(font + 0x14, 2)
                    rows.append({"record": int(text[-2:]), "x": x, "y": y})
                return rows

            h.run(0x253840, owner)  # state 0
            h.run(0x253840, owner)  # build visible handles
            self.assertTrue(constructor_callers, "history row constructor was not reached")
            initial = current_rows()
            first_visible = max(0, count - 12)
            self.assertEqual([row["record"] for row in initial], list(range(first_visible, count)))
            self.assertEqual({row["x"] for row in initial}, {20.})
            h.put16(0x7A39D2, 0x2000)
            h.run(0x253840, owner)
            h.put16(0x7A39D2, 0)
            h.run(0x253840, owner)
            scrolled = current_rows()
            if count > 12:
                self.assertIn(first_visible - 1, [row["record"] for row in scrolled])
            evidence[count] = {"initial": initial, "after_older": scrolled,
                               "native_callback": "0x253840",
                               "new_record_constructor_callers": sorted(hex(address)
                                                                         for address in constructor_callers)}
        if report := os.getenv("R67P_HISTORY_EVIDENCE"):
            Path(report).write_text(json.dumps(evidence, indent=2) + "\n")
