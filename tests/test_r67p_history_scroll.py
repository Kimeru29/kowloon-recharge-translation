"""Native START-history paging and ring-window regression probes."""
from __future__ import annotations

import os
from pathlib import Path
import re
from unicodedata import normalize
import unittest

from tests.test_r67o_choices_pipeline import wide
from tests.test_r67p_caption_geometry import BASELINE, machine
from tests.test_r67p_dialogue import add_scope


def candidate_elf() -> bytes:
    """Use an explicitly supplied q ELF, otherwise compose it from pinned p."""
    supplied = os.getenv("R67Q_FINAL_ELF")
    if supplied:
        return Path(supplied).read_bytes()
    from tools import r67q_release

    if not r67q_release.BASELINE.is_file():
        raise unittest.SkipTest("Pinned r67.15p ISO fixture is unavailable")

    source = r67q_release.baseline_elf(r67q_release.BASELINE)
    return r67q_release.compose_native(source)[0]


def replay(elf: bytes, count: int, *, speaker_pairs: bool = False,
           actions: tuple[int, ...] = ()):
    if not 0 <= count <= 300:
        raise ValueError("History fixture count must be between 0 and 300")
    h = machine(elf)
    for lo, hi in ((0x252F80, 0x256B00), (0x963A50, 0x963CC0),
                   (0x24D970, 0x24E680)):
        add_scope(h, lo, hi)
    for style in (3, 4, 5):
        h.font_atlas(style)
    # Scrollbar and row-highlight behavior have separate evidence.
    # The three animation/decorative callees are outside this text-window probe.
    h.external.update({0x1697B0: h.noop, 0x256040: h.noop,
                       0x256400: h.noop, 0x255EA0: h.noop})

    for index in range(count):
        is_speaker = speaker_pairs and index % 3 == 0
        label = "Speaker" if is_speaker else "Body"
        text = wide(f"{label} {index:03}")
        if not is_speaker and index % 3 == 2:
            text += "混合".encode("cp932")
        payload = text + b"\0"
        if is_speaker:
            if len(payload) - 1 > 29:
                raise ValueError("Inline speaker text exceeds native 29-byte capacity")
            address = h.alloc(len(payload))
            h.write(address, payload)
            h.run(0x2531A0, 10, address)
        else:
            payload = text + b"r\0"
            address = h.alloc(len(payload))
            h.write(address, payload)
            h.run(0x253000, address, 1)

    owner, private = h.alloc(0x44), h.alloc(0x1C0)
    h.put32(owner + 0x3C, private)

    def rows():
        result = []
        visible = h.read16(private + 0x7A)
        for slot in range(visible):
            handle = h.read32(private + 0x20 + slot * 4)
            assert handle in h.tasks and h.tasks[handle][-1], (slot, handle)
            font = h.tasks[handle][3]
            value = normalize("NFKC", h.cstring(font + 0x51, 102).decode("cp932"))
            found = re.search(r"\d{3}", value)
            assert found is not None, value
            x, y = h.floats(font + 0x14, 2)
            result.append({"slot": slot, "record": int(found[0]), "text": value,
                           "handle": handle, "x": x, "y": y})
        return result

    # Native state 0 initializes this display instance; state 1 creates rows.
    h.run(0x253840, owner)
    h.run(0x253840, owner)
    snapshots = [rows()]
    for action in actions:
        if isinstance(action, int):
            h.put16(0x7A39D2, action)
        else:
            pad, input_mode, direction = action
            h.put16(0x7A39D2, pad)
            h.put16(0x7A39CC, input_mode)
            h.put16(0x7A39CE, direction)
        h.run(0x253840, owner)
        h.put16(0x7A39D2, 0)
        h.put16(0x7A39CC, 0)
        h.put16(0x7A39CE, 0)
        for _ in range(3):
            h.run(0x253840, owner)
        snapshots.append(sorted(rows(), key=lambda row: row["y"]))
    return h, owner, private, snapshots


class HistoryScrollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf = candidate_elf()

    def assert_window(self, window, expected, *, expected_x=20.0):
        self.assertEqual([row["record"] for row in window], expected)
        if expected_x is not None:
            self.assertTrue(all(row["x"] == expected_x for row in window))
        ys = [row["y"] for row in window]
        self.assertTrue(all(left < right for left, right in zip(ys, ys[1:])))
        if ys:
            self.assertGreaterEqual(ys[0], 0.0)
            self.assertLess(ys[-1], 448.0)

    def test_older_and_newer_page_clamp_and_restore_chronology(self):
        for count in (6, 18):
            with self.subTest(records=count):
                actions = (0x2000,) * 8 + (0x8000,) * 8
                _, _, _, frames = replay(self.elf, count, actions=actions)
                oldest = max(0, count - 12)
                expected_initial = list(range(oldest, count))
                self.assert_window(frames[0], expected_initial)
                for page in range(1, 9):
                    oldest = max(0, oldest - 1)
                    self.assert_window(frames[page], list(range(oldest, oldest + min(count, 12))))
                for page in range(9, 17):
                    oldest = min(max(0, count - 12), oldest + 1)
                    self.assert_window(frames[page], list(range(oldest, oldest + min(count, 12))))
                self.assert_window(frames[-1], expected_initial)

    def test_mixed_speaker_body_rows_keep_real_text_and_fresh_handles(self):
        h, _, _, frames = replay(self.elf, 18, speaker_pairs=True,
                                 actions=(0x2000, 0x8000))
        initial, older, returned = frames
        self.assert_window(initial, list(range(6, 18)), expected_x=None)
        self.assert_window(older, list(range(5, 17)), expected_x=None)
        self.assert_window(returned, list(range(6, 18)), expected_x=None)
        # Native type-10 headers keep their stock centered X; body rows keep
        # their left-aligned X. These are the pinned native history coordinates.
        for window in (initial, older, returned):
            for row in window:
                expected_x = 59.0 if row["record"] % 3 == 0 else 20.0
                self.assertEqual(expected_x, row["x"], row)
        self.assertTrue(any("Speaker" in row["text"] for row in older))
        self.assertTrue(any("Body" in row["text"] for row in older))
        self.assertTrue(any("混合" in row["text"] for row in older))
        # Each row table entry must still point at a live task whose text came
        # from the newly selected records, including the mixed CP932 body row.
        self.assertEqual(len({row["handle"] for row in older}), len(older))
        for row in initial:
            self.assertIn(row["handle"], h.tasks)
            self.assertFalse(h.tasks[row["handle"]][-1], "old row child was not destroyed")
        self.assertTrue(all(row["handle"] in h.tasks for row in returned))
        self.assertTrue(all(h.tasks[row["handle"]][-1] for row in returned))
        for row in older:
            expected_label = "Speaker" if row["record"] % 3 == 0 else "Body"
            self.assertIn(expected_label, row["text"])
            self.assertEqual("混合" in row["text"], row["record"] % 3 == 2)
        for left, right in zip(older, older[1:]):
            expected_spacing = 25.0 if left["record"] % 3 == 0 else 37.0
            self.assertEqual(expected_spacing, right["y"] - left["y"])
        initial_positions = {row["record"]: (row["x"], row["y"]) for row in initial}
        returned_positions = {row["record"]: (row["x"], row["y"]) for row in returned}
        self.assertEqual(initial_positions, returned_positions)

    def test_ring_wraparound_preserves_order_and_page_round_trip(self):
        _, _, _, frames = replay(self.elf, 258,
                                 actions=(0x2000,) * 3 + (0x8000,) * 3)
        expected = list(range(246, 258))
        self.assert_window(frames[0], expected)
        for index in range(1, 4):
            self.assert_window(frames[index], list(range(246 - index, 258 - index)))
        for index in range(4, 7):
            self.assert_window(frames[index], list(range(246 - (6 - index), 258 - (6 - index))))
        self.assert_window(frames[-1], expected)

    def test_fast_modifier_paging_moves_one_complete_window(self):
        _, _, _, direct = replay(self.elf, 40, actions=(0x0008, 0x0004))
        self.assert_window(direct[0], list(range(28, 40)))
        self.assert_window(direct[1], list(range(16, 28)))
        self.assert_window(direct[2], list(range(28, 40)))

        _, _, _, modified = replay(
            self.elf, 40,
            actions=((0x0000, 0x0010, 0x2000),
                     (0x0000, 0x0010, 0x8000)))
        self.assert_window(modified[0], list(range(28, 40)))
        self.assert_window(modified[1], list(range(16, 28)))
        self.assert_window(modified[2], list(range(28, 40)))


if __name__ == "__main__":
    unittest.main()
