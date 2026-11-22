"""Replay distinct installed speaker payloads through the header font task."""

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from struct import pack_into, unpack_from
import unittest

from tests.test_r67o_choices_pipeline import STATE, TASK_DATA
from tests.test_r67p_caption_geometry import BASELINE, CHOICE_REPORT, draw, geometry, machine
from tools.r67o_inventory import open_disc
from tools.r67p_speaker_geometry import patch

INVENTORY = Path("local/r67o-inventory-final")


def capture(h, raw):
    h.write(STATE + 0x198, raw + b"\0")
    h.set_reg(16, TASK_DATA)
    handle = h.run(0x24FFC8, stop_at=(0x250004,)).v0
    h.run(0x250010, handle, 200, stop_at=(0x250018,))
    quads = draw(h, handle, 0x18B9B0)
    text = h.cstring(h.tasks[handle][3] + 0x51, 102)
    return quads, text


@unittest.skipUnless(BASELINE.is_file() and CHOICE_REPORT.is_file()
                     and (INVENTORY / "speakers.json").is_file(), "Pinned r67.15o fixtures are unavailable")
class InstalledHeaderInventory(unittest.TestCase):
    def test_complete_distinct_header_payloads_fit_and_preserve_native_nodes(self):
        lock = json.loads(Path("translations/r67o_release_lock.json").read_bytes())
        baseline = BASELINE.read_bytes()
        self.assertEqual(sha256(baseline).hexdigest(), lock["installed_elf_sha256"])
        supplied = os.getenv("R67P_FINAL_ELF")
        iso = Path(os.getenv("R67P_FINAL_ISO", str(BASELINE.with_suffix(".iso"))))
        if supplied:
            final = Path(supplied).read_bytes()
        else:
            final = bytearray(baseline)
            final.extend(bytes(-len(final) % 16))
            file, va = unpack_from("<II", baseline, 0x58)
            blob, edits = patch(baseline, va + len(final) - file)
            for offset, (expected, replacement) in edits.items():
                self.assertEqual(final[offset:offset + 4], expected)
                final[offset:offset + 4] = replacement
            final.extend(blob)
            pack_into("<I", final, 0x64, len(final) - file)
            final = bytes(final)

        sources = Counter()
        with open_disc(iso) as disc:
            self.assertEqual(disc.elf, final if supplied else baseline)
            entries = (INVENTORY / "entries.json").read_bytes()
            speakers = (INVENTORY / "speakers.json").read_bytes()
            self.assertEqual(sha256(entries).hexdigest(), lock["inventory_sha256"]["entries.json"])
            self.assertEqual(sha256(speakers).hexdigest(), lock["inventory_sha256"]["speakers.json"])
            for row in json.loads(entries):
                if row["status"] != "official English installed":
                    continue
                start = row["installed_iso_offset"]
                end = start + row["installed_length"]
                raw = disc.image[start:end]
                if raw.startswith(b"\x81\x79") and raw.endswith(b"\x81\x7a") and disc.image[end:end + 1] == b"r":
                    self.assertEqual(sha256(raw).hexdigest(), row["installed_bytes_sha256"])
                    sources[raw] += 1
            self.assertEqual((len(sources), sum(sources.values())), (218, 34334))
            for row in json.loads(speakers)["occurrences"]:
                start = row["installed_iso_offset"]
                length = row["output_span"][1] - row["output_span"][0]
                raw = disc.image[start:start + length]
                self.assertEqual(sha256(raw).hexdigest(), row["output_span_sha256"])
                sources[raw] += 1

        before, after = machine(baseline), machine(final)
        report = []
        for raw, occurrences in sorted(sources.items()):
            with self.subTest(body_sha256=sha256(raw).hexdigest()):
                old_quads, old_display = capture(before, raw)
                new_quads, new_display = capture(after, raw)
                self.assertEqual(new_display, old_display)
                self.assertEqual(len(new_quads), len(old_quads))
                old_rect = geometry([v for q in old_quads for v in q])
                new_rect = geometry([v for q in new_quads for v in q])
                self.assertTrue(20 <= new_rect[0] < new_rect[2] <= 512.)
                self.assertTrue(276 <= new_rect[1] < new_rect[3] < 300.)
                if old_rect[2] <= 511:
                    self.assertEqual(new_quads, old_quads)
                else:
                    self.assertLess(new_rect[2], old_rect[2])
                report.append({"source_sha256": sha256(raw).hexdigest(), "occurrences": occurrences,
                               "glyph_quads": len(new_quads) // 2, "baseline_rect": old_rect, "rect": new_rect})
        before.assert_canaries(self)
        after.assert_canaries(self)
        self.assertEqual(sum(row["occurrences"] for row in report), 34334 + 7402)
        if evidence := os.getenv("R67P_HEADER_INVENTORY_EVIDENCE"):
            Path(evidence).write_text(json.dumps(report, indent=2) + "\n")
