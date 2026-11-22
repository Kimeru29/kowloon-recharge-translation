"""Execute the ADV caption dispatcher and both native drawing tasks."""
from __future__ import annotations

import json
import os
from pathlib import Path
from struct import pack_into, unpack_from
import unittest

from unicorn import UC_HOOK_CODE
from unicorn.mips_const import UC_MIPS_REG_PC

from tests.r67_native_text_pipeline import NATIVE_GP
from tests.test_r67o_choices_pipeline import ChoiceMachine, STATE, TASK_DATA, wide

BASELINE = Path("local/r67o-release/67.15o-cumulative-official-diagnostic.elf")
CHOICE_REPORT = Path("local/r67o-choices/report.json")
SCRIPT = 0x1101000
CAPTION_STATE = NATIVE_GP - 0x1D78


def geometry(vertices):
    return [min(v[0] for v in vertices), min(v[1] for v in vertices),
            max(v[0] for v in vertices), max(v[1] for v in vertices)]


def machine(source):
    report = json.loads(CHOICE_REPORT.read_bytes())
    segment_file, segment_va = unpack_from("<II", source, 0x58)
    start = segment_va + BASELINE.stat().st_size - segment_file
    end = segment_va + len(source) - segment_file
    report["ee_ranges"].extend(((0x250C90, 0x251470), (0x188AD0, 0x18B060),
                                (0x251F80, 0x252AE0), (0x2567F0, 0x256D90),
                                (start, end)))
    harness = ChoiceMachine(source, report)
    for lower, upper in ((0x251F80, 0x252AE0), (0x2567F0, 0x256D90)):
        harness.ee.hook_add(UC_HOOK_CODE, harness.ee_arithmetic, begin=lower, end=upper - 1)
    # The history navigator relocates a row loop containing EE-only COP1 operations.
    history_hook = harness.read32(0x253DB4)
    history_target = (history_hook & 0x03FFFFFF) << 2
    if history_hook >> 26 == 2 and start <= history_target < end:
        harness.ee.hook_add(UC_HOOK_CODE, harness.ee_arithmetic, begin=history_target, end=end - 1)

    def copy_string(_):
        raw = harness.cstring(harness.reg(5), 256)
        harness.write(harness.reg(4), raw + b"\0")
        harness.ret(harness.reg(4))

    def format_string(engine):
        assert b"%" not in harness.cstring(harness.reg(5), 256)
        copy_string(engine)

    def load_store_backing_rect(engine, pc, _size, _data):
        # This adjacent LQ/SQ pair copies all 128 bits. The generic harness
        # lowers each to 64-bit operations elsewhere.
        assert harness.reg(2) == 0x670000
        harness.write(harness.reg(29) + 0x30, harness.read(0x677420, 16))
        engine.reg_write(UC_MIPS_REG_PC, pc + 8)

    harness.ee.hook_add(UC_HOOK_CODE, load_store_backing_rect, begin=0x250DB0, end=0x250DB0)
    def append_string(_):
        dest, source = harness.reg(4), harness.reg(5)
        joined = harness.cstring(dest, 256) + harness.cstring(source, 256)
        harness.write(dest, joined + b"\0")
        harness.ret(dest)

    harness.external.update({0x39F300: append_string, 0x39F708: copy_string, 0x3A3ED0: format_string})
    context = harness.alloc(0x100)
    harness.putfloat(context + 0x80, 1.0)
    harness.external[0x1A0190] = lambda _: harness.ret(context)
    return harness


def open_caption(h, raw):
    assert len(raw) <= 100 and len(raw) % 2 == 0
    h.write(SCRIPT, b"{" + raw + b"}\0")
    h.run(0x251100)
    owner = h.run(0x2511C0, TASK_DATA).v0
    h.put32(h.read32(CAPTION_STATE), owner)
    h.write(h.read32(CAPTION_STATE) + 4, b"\x01")
    private = h.tasks[owner][3]
    history = []

    def record_caption(_):
        history.append((h.cstring(h.reg(4), 104), h.reg(5)))
        h.ret()

    for _ in range(2):
        h.set_reg(16, SCRIPT)
        h.set_reg(3, ord("{"))
        h.run(0x215994, stop_at=(0x2159B0,), extra={0x253000: record_caption})
        assert h.reg(16) == SCRIPT
    assert history == [(raw + b"}", 1)]
    assert h.read(STATE + 0x91C, 1) == b"\x06"
    assert h.read(private, 1) == b"\x01"
    h.run(0x250C90, owner)
    assert h.read(private, 1) == b"\x08"
    return owner, private, h.read32(private + 4), h.read32(private + 8)


def draw(h, handle, entry):
    h.submitted.clear()
    h.run(entry, handle)
    return h.submitted.copy()


@unittest.skipUnless(BASELINE.is_file() and CHOICE_REPORT.is_file(), "Pinned r67.15o fixtures are unavailable")
class CaptionGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = BASELINE.read_bytes()
        supplied = os.getenv("R67P_FINAL_ELF")
        if supplied:
            cls.candidate = Path(supplied).read_bytes()
        elif os.getenv("R67P_CAPTION_BASELINE_RED"):
            cls.candidate = cls.baseline
        else:
            from tools.r67p_caption_geometry import patch
            candidate = bytearray(cls.baseline)
            file, va = unpack_from("<II", candidate, 0x58)
            code, writes = patch(cls.baseline, va + len(candidate) - file)
            for offset, (expected, replacement) in writes.items():
                assert candidate[offset:offset + len(expected)] == expected
                candidate[offset:offset + len(expected)] = replacement
            candidate.extend(code)
            pack_into("<I", candidate, 0x64, len(candidate) - file)
            cls.candidate = bytes(candidate)

    def test_dispatch_preserves_complete_wrapped_caption_and_full_fade(self):
        raw = wide("In Front of the Metropolitan Police Department")
        h = machine(self.candidate)
        owner, private, font, backing = open_caption(h, raw)
        # State 8 drives both the raw font colour and the backing alpha for 100 frames.
        for _ in range(10):
            h.run(0x250C90, owner)
        self.assertTrue(all(v[11] == 25. for q in draw(h, font, 0x18B9B0)[1::2] for v in q))
        self.assertEqual([v[11] for v in draw(h, backing, 0x2567F0)[0]], [0., 25., 0., 25.])
        for _ in range(90):
            h.run(0x250C90, owner)
        quads = draw(h, font, 0x18B9B0)
        expected_glyphs = len(raw) // 2 - raw.count(b"\x81\x40")
        self.assertEqual(len(quads), 2 * expected_glyphs)
        text = h.cstring(h.tasks[font][3] + 0x51)
        self.assertEqual(text.replace(b"\n", b"\x81\x40"), raw)
        self.assertEqual(text.count(b"\n"), 1)
        self.assertEqual(len({quad[0][1] for quad in quads[1::2]}), 2)
        self.assertEqual(set((shadow[0][0] - face[0][0], shadow[0][1] - face[0][1])
                             for shadow, face in zip(quads[::2], quads[1::2], strict=True)), {(1., 1.)})
        ink = geometry([vertex for quad in quads for vertex in quad])
        backing_quad = draw(h, backing, 0x2567F0)
        self.assertEqual(len(backing_quad), 1)
        self.assertEqual([v[11] for v in backing_quad[0]], [0., 255., 0., 255.])
        x1, y1, x2, y2 = geometry(backing_quad[0])
        self.assertTrue(0 <= x1 < ink[0] < ink[2] < x2 <= 512)
        self.assertTrue(0 <= y1 < ink[1] < ink[3] < y2 <= 447)
        self.assertLessEqual(abs((ink[0] + ink[2]) / 2 - 256), 1)
        self.assertEqual(h.read(private + 0xC, 2), b"d\x00")
        h.run(0x250C90, owner)
        self.assertEqual(h.read(private, 1), b"\x09")

    def test_japanese_caption_keeps_stock_geometry_and_bytes(self):
        raw = "九龍妖魔學園紀".encode("cp932")
        outputs = []
        for source in (self.baseline, self.candidate):
            h = machine(source)
            owner, _, font, backing = open_caption(h, raw)
            h.run(0x250C90, owner)
            outputs.append((draw(h, font, 0x18B9B0),
                            draw(h, backing, 0x2567F0), h.cstring(STATE + 0x8B4)))
        self.assertEqual(*outputs)

    def test_hard_wrap_keeps_all_fifty_glyphs(self):
        h = machine(self.candidate)
        raw = wide("A" * 50)
        owner, _, font, _ = open_caption(h, raw)
        h.run(0x250C90, owner)
        quads = draw(h, font, 0x18B9B0)
        self.assertEqual(len(quads), 100)
        self.assertEqual(h.cstring(h.tasks[font][3] + 0x51, 102).replace(b"\n", b""), raw)
        self.assertLessEqual(geometry([v for quad in quads for v in quad])[2], 496)

    def test_owner_preimages_and_negative_hook_mutation(self):
        from tools.r67p_caption_geometry import TEXT_CALL, BACKING_CALL, patch
        from tools.r67_chamber_story_text_only import ELF_BIAS

        file, va = unpack_from("<II", self.baseline, 0x58)
        for call in (TEXT_CALL, BACKING_CALL):
            altered = bytearray(self.baseline)
            altered[call - ELF_BIAS] ^= 1
            with self.assertRaisesRegex(ValueError, "Caption owner preimage"):
                patch(bytes(altered), va + len(altered) - file)
        mutated = bytearray(self.candidate)
        offset = BACKING_CALL - ELF_BIAS
        mutated[offset:offset + 4] = self.baseline[offset:offset + 4]
        h = machine(bytes(mutated))
        owner, _, font, backing = open_caption(h, wide("Scene title"))
        h.run(0x250C90, owner)
        glyph = geometry([v for q in draw(h, font, 0x18B9B0) for v in q])
        panel = geometry(draw(h, backing, 0x2567F0)[0])
        self.assertGreater(panel[0], glyph[0])

    def test_fade_out_dispatch_resume_release_and_reopen(self):
        h = machine(self.candidate)
        owner, private, font, backing = open_caption(h, wide("Scene one"))
        for _ in range(251):
            h.run(0x250C90, owner)
        self.assertEqual(h.read(private, 1), b"\x0a")
        self.assertEqual(h.read(private + 0xC, 2), b"c\x00")
        h.run(0x250C90, owner)
        self.assertEqual(h.read(h.tasks[font][3] + 0x37, 1), b"\x00")
        self.assertTrue(all(v[11] == 0. for v in draw(h, backing, 0x2567F0)[0]))
        h.run(0x250C90, owner)
        self.assertEqual(h.read(private, 1), b"\x0c")
        for expected in (SCRIPT, SCRIPT + len(wide("Scene one")) + 2):
            h.set_reg(16, SCRIPT)
            h.set_reg(3, ord("{"))
            h.run(0x215994, stop_at=(0x2159B0,))
            self.assertEqual(h.reg(16), expected)
        h.run(0x251070, owner)
        self.assertFalse(h.tasks[font][-1])
        self.assertFalse(h.tasks[backing][-1])
        self.assertIn(private, h.freed)
        h.run(0x251150)
        self.assertEqual(h.read32(CAPTION_STATE), 0)
        self.assertNotEqual(open_caption(h, "再開".encode("cp932"))[0], owner)
        h.assert_canaries(self)

    def test_installed_corpus(self):
        from hashlib import sha256

        from tools.localization import _cp932_boundaries
        from tools.r67o_inventory import open_disc, pointer_regions
        from tools.r67p_caption_geometry import latin_cells

        supplied = os.getenv("R67P_FINAL_ISO")
        baseline_iso = BASELINE.with_suffix(".iso")
        if not supplied and not baseline_iso.is_file():
            self.skipTest("Pinned r67.15o ISO is unavailable")
        lock = json.loads(Path("translations/r67o_release_lock.json").read_bytes())
        inventory = Path("local/r67o-inventory-final/entries.json").read_bytes()
        self.assertEqual(sha256(inventory).hexdigest(), lock["inventory_sha256"]["entries.json"])
        English = {(r["installed_asset"], r["installed_offset"]): r for r in json.loads(inventory)
                   if r["status"] == "official English installed"}
        report = []
        english_count = stock_count = baseline_overflow_count = 0
        table = latin_cells(self.baseline)
        with open_disc(Path(supplied) if supplied else baseline_iso) as disc:
            if supplied:
                self.assertEqual(disc.elf, self.candidate)
            else:
                self.assertEqual(sha256(disc.image).hexdigest(), lock["iso_sha256"])
            for path in sorted(disc.records):
                if not path.endswith(".MTX"):
                    continue
                absolute, asset = disc.asset(path)
                if b"{" not in asset:
                    continue
                for begin, end, slots in pointer_regions(asset):
                    region = asset[begin:end]
                    for offset in sorted(_cp932_boundaries(region, 0)):
                        if region[offset:offset + 1] != b"{":
                            continue
                        start = offset + 1
                        limit = next((i for i in range(start, len(region), 2)
                                      if region[i] in (0, 0x7D)), len(region))
                        with self.subTest(path=path, offset=begin + start):
                            self.assertLess(limit, len(region))
                            self.assertEqual(region[limit], 0x7D)
                            raw = region[start:limit]
                            self.assertLessEqual(len(raw), 100)
                            decoded = raw.decode("cp932")
                            self.assertEqual(sum(ord(ch) > 127 for ch in decoded) * 2, len(raw))
                            classes = [table[int.from_bytes(raw[i:i + 2], "big") - 0x8100]
                                       if raw[i] in (0x81, 0x82) else 0 for i in range(0, len(raw), 2)]
                            english = all(classes) and 2 in classes
                            row = English.get((path, begin + start))
                            if english:
                                self.assertIsNotNone(row)
                                self.assertEqual(row["installed_length"], len(raw))
                                self.assertEqual(row["installed_bytes_sha256"], sha256(raw).hexdigest())
                                english_count += 1
                            else:
                                stock_count += 1

                            captures = []
                            for elf in (self.baseline, self.candidate):
                                h = machine(elf)
                                owner, _, font, backing = open_caption(h, raw)
                                h.run(0x250C90, owner)
                                quads = draw(h, font, 0x18B9B0)
                                panel = draw(h, backing, 0x2567F0)
                                captures.append((quads, panel))
                            old, new = captures
                            unchanged = old == new
                            rect = geometry([v for q in new[0] for v in q]) if new[0] else []
                            old_rect = geometry([v for q in old[0] for v in q]) if old[0] else []
                            if english:
                                self.assertFalse(unchanged)
                                self.assertEqual(len(old[0]), len(new[0]))
                                self.assertTrue(16 <= rect[0] < rect[2] <= 496)
                                self.assertTrue(6 < rect[1] < rect[3] < 66)
                                self.assertEqual(geometry(new[1][0]), [0., 6., 512., 66.])
                                self.assertLessEqual(abs((rect[0] + rect[2]) / 2 - 256), 2)
                                before_text = h.cstring(STATE + 0x8B4)
                                after_text = h.cstring(h.tasks[font][3] + 0x51, 102)
                                self.assertIn(before_text, (after_text.replace(b"\n", b"\x81\x40"),
                                                            after_text.replace(b"\n", b"")))
                                baseline_overflow_count += old_rect[3] > 447
                            else:
                                self.assertTrue(unchanged)
                            report.append({"asset": path, "pointer_slots": slots,
                                           "iso_offset": absolute + begin + start,
                                           "dc_key": row["dc_key"] if english else None,
                                           "owner": "English horizontal caption" if english else "stock caption",
                                           "baseline_face_and_shadow": old_rect, "face_and_shadow": rect,
                                           "face_quads": len(new[0]) // 2, "payload_sha256": sha256(raw).hexdigest()})
        self.assertEqual((english_count, stock_count, baseline_overflow_count), (202, 25, 110))
        if evidence := os.getenv("R67P_CAPTION_EVIDENCE"):
            Path(evidence).write_text(json.dumps(report, indent=2) + "\n")
