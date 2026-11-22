"""Replay the three installed post-caption speaker routes through the native dispatcher."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
from unicodedata import normalize

from tests.r67_native_text_pipeline import NATIVE_GP
from tests.test_r67o_speakers_native import SpeakerNative
from tests.test_r67p_caption_geometry import (
    BASELINE, SCRIPT, STATE, TASK_DATA, geometry, machine, open_caption,
)
from tests.test_r67p_dialogue import add_scope
from tests.test_r67p_header_inventory import capture
from tools.r67o_inventory import open_disc

SCRIPT_STATE = NATIVE_GP - 0x1D74
SPEAKER_PARSER = 0x250530
ROUTES = {
    ("MS/MS07_03.MTX", 39661): (b"w30mr9mi100", 41),
    ("MS/MS08_03.MTX", 19170): (b"w30", 35),
    ("MS/MS08_03.MTX", 19278): (b"w30", 35),
}


def replay(elf, parser, full, title, caption_end, header_start, prefix, expected_tick):
    h = machine(elf)
    for start, end in ((0x215860, 0x215AA0), (0x226FA0, 0x228E00),
                       (0x230600, 0x231170), (0x250530, 0x250C90)):
        add_scope(h, start, end)

    def compare(_):
        length = h.reg(6)
        h.ret(int(h.read(h.reg(4), length).lower() != h.read(h.reg(5), length).lower()))

    def decimal(_):
        start = h.reg(4)
        raw = h.cstring(start)
        assert h.reg(6) == 10 and raw.isdigit(), raw
        h.put32(h.reg(5), start + len(raw))
        h.ret(int(raw))

    requests = []

    def request_audio(_):
        # Observed at the actual effect call boundary. The audio system is
        # external to this ADV fixture and its return value is unused.
        requests.append((h.reg(4), h.reg(5)))
        h.ret()

    h.external.update({0x39FB08: compare, 0x3A1190: decimal,
                       0x168DF0: request_audio, 0x253000: h.noop})
    h.put32(SCRIPT_STATE, h.alloc(0x80))
    h.write(STATE + 0x27E, b"\x03")
    owner, private, _, _ = open_caption(h, title)
    h.write(SCRIPT, full + b"\0")
    # Advance the registered caption task through the normal wait, fade and
    # completion so ADV reads the state it would receive on the live route.
    for _ in range(253):
        h.run(0x250C90, owner)
    assert h.read(private, 1) == b"\x0c"
    cursor = SCRIPT
    progress, wait_frames = [], []
    for tick in range(80):
        step = h.run(0x215860, TASK_DATA, cursor, stop_at=(SPEAKER_PARSER,))
        if step.pc == SPEAKER_PARSER:
            assert tick == expected_tick and h.reg(4) == SCRIPT + header_start
            break
        if step.v0 != cursor:
            progress.append((tick, cursor - SCRIPT, step.v0 - SCRIPT))
        cursor = step.v0
        state = h.read(STATE + 0x31B8, 1)
        if state == b"\x02":
            wait_frames.append(h.read16(STATE + 0x31C6))
    else:
        raise AssertionError("ADV did not dispatch the installed bracket to the speaker parser")
    assert progress[0] == (1, 0, caption_end)
    assert wait_frames == list(range(30, 0, -1)), wait_frames
    assert requests == ([(9, 100)] if prefix.endswith(b"mr9mi100") else [])
    # Use the stock parser fixture from the installed dispatch input. It runs
    # the native actor and alias lookups with scalar libc paths.
    header = h.read(h.reg(4), len(full) - header_start - 1)
    identity, parsed = parser.extract(header)
    assert parsed == header
    quads, drawn_text = capture(h, parsed)
    assert drawn_text == parsed
    return {"dispatch_tick": tick, "cursor_progress": progress, "wait_frames": wait_frames,
            "audio_requests": requests, "actor_alias_identity": identity, "glyph_count": len(quads) // 2,
            "drawn_text_sha256": sha256(drawn_text).hexdigest(),
            "quad_bounds": geometry([v for quad in quads for v in quad])}


def run(candidate, baseline_probe):
    rows = json.loads(baseline_probe.read_bytes())["results"]
    lock = json.loads(Path("translations/r67o_release_lock.json").read_bytes())
    baseline = BASELINE.with_suffix(".iso")
    results = []
    with open_disc(baseline) as old, open_disc(candidate) as new:
        assert sha256(old.image).hexdigest() == lock["iso_sha256"]
        assert sha256(old.elf).hexdigest() == lock["installed_elf_sha256"]
        iso_hash = sha256(new.image).hexdigest()
        elf_hash = sha256(new.elf).hexdigest()
        baseline_parser, candidate_parser = SpeakerNative(old.elf), SpeakerNative(new.elf)
        for group in rows:
            for row in group["occurrences"]:
                identifier = row["owner"], row["key"]
                if identifier not in ROUTES:
                    continue
                prefix, tick = ROUTES[identifier]
                header_offset = row["iso_offset"]
                source_offset, source_file = old.asset(row["owner"])
                installed_offset, installed_file = new.asset(row["owner"])
                assert source_offset == installed_offset and source_file == installed_file
                caption_end = header_offset - len(prefix)
                assert old.image[caption_end - 1:header_offset] == b"}" + prefix
                caption_start = old.image.rfind(b"{", max(source_offset, caption_end - 102), caption_end)
                assert caption_start >= source_offset
                header_end = header_offset + group["cells"] * 2
                assert header_end < source_offset + len(source_file)
                assert normalize("NFKC", old.image[header_offset:header_end].decode("cp932")) == group["text"]
                assert old.image[header_end:header_end + 1] == b"r"
                path = old.image[caption_start:header_end + 1]
                args = (path, old.image[caption_start + 1:caption_end - 1],
                        caption_end - caption_start, header_offset - caption_start, prefix, tick)
                before = replay(old.elf, baseline_parser, *args)
                after = replay(new.elf, candidate_parser, *args)
                assert before["actor_alias_identity"] == after["actor_alias_identity"]
                assert before["drawn_text_sha256"] == after["drawn_text_sha256"]
                assert before["glyph_count"] == after["glyph_count"]
                assert before["cursor_progress"] == after["cursor_progress"]
                assert before["quad_bounds"][2] > 512 >= after["quad_bounds"][2]
                results.append({"asset": row["owner"], "key": row["key"],
                                "command_prefix": prefix.decode("ascii"),
                                "span_sha256": sha256(path).hexdigest(),
                                "baseline": before, "candidate": after})
    assert {(row["asset"], row["key"]) for row in results} == set(ROUTES)
    return {"iso_sha256": iso_hash, "installed_elf_sha256": elf_hash, "routes": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True)
    parser.add_argument("--baseline-probe", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.iso, args.baseline_probe)
    with args.report.open("x") as stream:
        stream.write(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
