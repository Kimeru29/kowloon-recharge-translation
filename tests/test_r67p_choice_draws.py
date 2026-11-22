"""Replay the installed KSF records through the actual menu and font tasks."""

from collections import defaultdict
from hashlib import sha256
from itertools import combinations
import json
import os
from pathlib import Path
from struct import pack_into, unpack_from
import unittest

from tests.test_r67o_choices_pipeline import FAMILY, FILE, GIVEN, STATE, TASK_DATA, checked_corpus, wide
from tests.test_r67p_caption_geometry import BASELINE, CHOICE_REPORT, draw, geometry, machine
from tools.r67o_inventory import open_disc
from tools.r67p_choice_geometry import STOCK_ORIENTATION_CALL, ELF_BIAS, patch

INVENTORY = Path("local/r67o-inventory-final")


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def sample(source, report, path, payload, ordinal, family, given, test):
    h = machine(source)
    h.write(FILE, payload)
    h.put32(STATE + 0x3158, FILE)
    h.put16(STATE + 0x3150, ordinal)
    category, _, filename = path.partition("/")
    h.write(STATE + 0x3160, f"adv/{category.lower()}/{filename}".encode() + b"\0")
    h.write(FAMILY, family.ljust(32, b"\0"))
    h.write(GIVEN, given.ljust(32, b"\0"))
    words = h.run_record()
    menu = h.alloc(0x68)
    private = h.alloc(0x40)
    h.put32(menu + 0x3C, private)
    h.run(0x251470, menu)
    h.run(0x251470, menu)
    slots = []
    for index, raw in enumerate(words):
        handle = h.read32(TASK_DATA + 0x94 + index * 4)
        h.run(0x18B100, handle, 200)
        h.set_reg(8, 0xAB)
        h.run(0x18B060, handle, 0xFE, 0xDC, 0xBA)
        quads = draw(h, handle, h.tasks[handle][1])
        faces, shadows = quads[1::2], quads[::2]
        test.assertEqual(len(faces), len(shadows))
        test.assertTrue(all(vertex[8:12] == (254., 220., 186., 171.)
                            for quad in faces for vertex in quad))
        font = h.tasks[handle][3]
        slots.append({"record_value": raw.hex(), "display_value": h.cstring(font + 0x51, 102).hex(),
                      "orientation": h.read(font + 0x24, 1)[0],
                      "bounds": geometry([v for q in quads for v in q]) if quads else None,
                      "faces": [geometry(q) for q in faces]})
    pairs = [[i, j] for i, j in combinations(range(len(slots)), 2)
             if any(intersects(a, b) for a in slots[i]["faces"] for b in slots[j]["faces"])]
    for slot in slots:
        slot["glyphs"] = len(slot.pop("faces"))
    mode = h.run(report["entries"]["choice_mode"], STATE).v0
    return {"slot_count": len(slots), "mode": mode, "overlaps": pairs, "slots": slots}


@unittest.skipUnless(BASELINE.is_file() and CHOICE_REPORT.is_file()
                     and (INVENTORY / "ksf-labels.json").is_file(), "Pinned r67.15o fixtures are unavailable")
class InstalledChoiceDraws(unittest.TestCase):
    def test_all_stock_and_dynamic_fallback_records(self):
        baseline = BASELINE.read_bytes()
        final_elf = os.getenv("R67P_FINAL_ELF")
        selected_iso = Path(os.getenv("R67P_FINAL_ISO", str(BASELINE.with_suffix(".iso"))))
        if final_elf:
            candidate = Path(final_elf).read_bytes()
        else:
            candidate = bytearray(baseline)
            candidate.extend(bytes(-len(candidate) % 16))
            file, va = unpack_from("<II", baseline, 0x58)
            blob, edits = patch(baseline, va + len(candidate) - file)
            for offset, (old, new) in edits.items():
                self.assertEqual(candidate[offset:offset + len(old)], old)
                candidate[offset:offset + len(old)] = new
            candidate.extend(blob)
            pack_into("<I", candidate, 0x64, len(candidate) - file)
            candidate = bytes(candidate)
        stock = defaultdict(list)
        inventory = json.loads((INVENTORY / "ksf-labels.json").read_bytes())
        files = {row["path"]: row for row in json.loads((INVENTORY / "files.json").read_bytes())}
        for row in inventory:
            if row.get("operative_owner") != "SLPM_665.11":
                stock[row["file"], row["record"]].append(row)
        self.assertEqual(len(stock), 23)

        guarded = [record for record in checked_corpus(True).records if any(row.dynamic for row in record.rows)]
        self.assertEqual(len(guarded), 4)
        report = json.loads(CHOICE_REPORT.read_bytes())
        evidence = {"iso_sha256": None, "elf_sha256": sha256(candidate).hexdigest(), "stock": [], "legacy": []}
        with open_disc(selected_iso) as disc:
            self.assertEqual(disc.elf, candidate if final_elf else baseline)
            evidence["iso_sha256"] = sha256(disc.image).hexdigest()

            def run(source, path, ordinal, names):
                absolute, payload = disc.asset(path)
                self.assertEqual(sha256(payload).hexdigest(), files[path]["installed_sha256"])
                return sample(source, report, path, payload, ordinal, *names, self)

            default = (wide("Hab"), wide("Kur"))
            for (path, ordinal), labels in sorted(stock.items()):
                with self.subTest(file=path, ordinal=ordinal):
                    before = run(baseline, path, ordinal, default)
                    after = run(candidate, path, ordinal, default)
                    self.assertEqual(after["slot_count"], len(labels))
                    self.assertFalse(after["overlaps"])
                    self.assertTrue(all(slot["orientation"] == 1 for slot in after["slots"]))
                    self.assertEqual([slot["display_value"] for slot in after["slots"]],
                                     [slot["display_value"] for slot in before["slots"]])
                    evidence["stock"].append({"file": path, "record": ordinal, "baseline": before,
                                              "candidate": after})
            self.assertEqual(sum(bool(row["baseline"]["overlaps"]) for row in evidence["stock"]), 22)
            self.assertEqual(sum(slot["glyphs"] > 0 for row in evidence["stock"]
                                 for slot in row["candidate"]["slots"]), 53)

            for record in guarded:
                path, ordinal = record.rows[0].path, record.ordinal
                self.assertEqual(run(baseline, path, ordinal, default), run(candidate, path, ordinal, default))
                glyph = "〇".encode("cp932")
                cells = "　".encode("cp932")
                for family, given in ((glyph, wide("N")), (glyph * 15, wide("N") * 15),
                                      (glyph + cells * 14, cells * 14 + wide("N")),
                                      (b"\x82", wide("N"))):
                    with self.subTest(file=path, ordinal=ordinal, family=family.hex(), given=given.hex()):
                        before = run(baseline, path, ordinal, (family, given))
                        after = run(candidate, path, ordinal, (family, given))
                        self.assertFalse(after["overlaps"])
                        for old, new in zip(before["slots"], after["slots"], strict=True):
                            self.assertEqual(new["record_value"], old["record_value"])
                            self.assertEqual(new["display_value"], old["display_value"])
                            self.assertEqual(new["glyphs"], old["glyphs"])
                            if bounds := new["bounds"]:
                                self.assertTrue(0 <= bounds[0] < bounds[2] <= 512.)
                                self.assertTrue(0 <= bounds[1] < bounds[3] <= 447.)
                        evidence["legacy"].append({"file": path, "record": ordinal,
                                                   "family_sha256": sha256(family).hexdigest(),
                                                   "given_sha256": sha256(given).hexdigest(),
                                                   "baseline": before, "candidate": after})

            offset = STOCK_ORIENTATION_CALL - ELF_BIAS
            mutation = bytearray(candidate)
            mutation[offset:offset + 4] = baseline[offset:offset + 4]
            path, ordinal = "FD/FD00_02.KSF", 0
            self.assertTrue(run(bytes(mutation), path, ordinal, default)["overlaps"])

        if output := os.getenv("R67P_CHOICE_EVIDENCE"):
            Path(output).write_text(json.dumps(evidence, indent=2) + "\n")
