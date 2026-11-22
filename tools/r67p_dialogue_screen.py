"""Project installed ADV spans onto the distinct caption, header and body geometry."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re

from tools.r67o_inventory import open_disc

HEADER_START, HEADER_END = bytes.fromhex("8179"), bytes.fromhex("817a")

BODY_WIDTH = 488
STATIC_ADVANCE = 24


def estimate(raw: bytes, name_profile: int):
    if name_profile not in (3, 15):
        raise ValueError("Choose a native editor or legacy-field envelope")
    # Name tokens appear as ASCII in installed DC rows. Splitting a CP932
    # stream by bytes can confuse a glyph trail byte for the token's p.
    text = raw.decode("cp932")
    tokens = re.findall(r"p(?:myh|nyh|m1|n1|m|n|x)", text)
    fixed = re.sub(r"p(?:myh|nyh|m1|n1|m|n|x)", "", text)
    if any(ord(ch) < 128 for ch in fixed):
        raise ValueError("Unexpected ASCII inside an inventoried ADV text span")
    cells = len(fixed) + sum(1 if token[2:] in ("1", "yh") else name_profile for token in tokens)
    spaces = fixed.count("　")
    return cells, spaces, tokens


def body_envelope(cells, spaces):
    width = STATIC_ADVANCE * cells
    if width <= BODY_WIDTH or cells == spaces:
        return width, width, 1.
    compact = 8 if spaces > 30 else 12
    glyphs = cells - spaces
    tracking = -4 if spaces > 30 else 0
    scale = min(1., (BODY_WIDTH - spaces * compact - tracking * (glyphs - 1)) / (STATIC_ADVANCE * glyphs))
    guarded_width = (glyphs * STATIC_ADVANCE * scale + tracking * (glyphs - 1) + spaces * compact)
    return width, guarded_width, scale


def screen(iso, inventory):
    summary = json.loads((inventory / "summary.json").read_bytes())
    entries = json.loads((inventory / "entries.json").read_bytes())
    spans = defaultdict(list)
    owners = Counter()
    widths = Counter()
    risks = []
    with open_disc(iso) as disc:
        if sha256(disc.image).hexdigest() != summary["iso_sha256"]:
            raise ValueError("Geometry screen inventory is bound to another ISO")
        for row in entries:
            if row["status"] != "official English installed":
                continue
            address = row["installed_iso_offset"]
            end = address + row["installed_length"]
            raw = disc.image[address:end]
            if sha256(raw).hexdigest() != row["installed_bytes_sha256"]:
                raise ValueError("Installed geometry input identity changed")
            before, after = disc.image[address - 1:address], disc.image[end:end + 1]
            if before == b"{" and after == b"}":
                owner = "scene_caption"
            elif raw.startswith(HEADER_START) and raw.endswith(HEADER_END) and after == b"r":
                owner = "bracket_header_candidate"
            else:
                owner = "body_candidate"
            owners[owner] += 1
            spans[row["installed_asset"]].append((address, end, owner))

            cells, spaces, tokens = estimate(raw, 3)
            if tokens:
                widths["name_bearing_rows"] += 1
            if owner != "body_candidate":
                continue
            legacy_cells, _, _ = estimate(raw, 15)
            scenarios = {}
            for label, count in (("editor_3_cell_example", cells), ("legacy_15_cell_envelope", legacy_cells)):
                before_fit, fitted, scale = body_envelope(count, spaces)
                if before_fit > BODY_WIDTH:
                    widths[label + "_would_spill_at_unit_scale"] += 1
                    scenarios[label] = {
                        "expanded_cells": count, "unit_scale_right_edge_including_shadow": 20 + before_fit,
                        "projected_fitted_right_edge": round(20 + fitted, 4),
                        "x_scale": round(scale, 7), "within_native_100_byte_row": count <= 50,
                    }
                if count > 50:
                    widths[label + "_over_100_byte_row"] += 1
            if scenarios:
                risks.append({"asset": row["installed_asset"], "dc_key": row["dc_key"],
                              "iso_offset": address, "marker_types": tokens, "scenarios": scenarios})

        page_runs = Counter()
        for file_spans in spans.values():
            run = []
            for start, end, owner in sorted(file_spans):
                if run and (start != run[-1][0] + 1 or disc.image[start - 1:start] != b"r"):
                    page_runs[(len(run), run[0][1])] += 1
                    run.clear()
                run.append((end, owner))
            if run:
                page_runs[(len(run), run[0][1])] += 1
    return {
        "iso_sha256": summary["iso_sha256"], "owner_counts": dict(owners),
        "native_body_profile": {"constructor": "0x24E8A0 → 0x24F660 → 0x18BF10",
                                "text_setter_call": "0x24EA20", "reveal_call": "0x24EA58",
                                "glyph_advance": STATIC_ADVANCE, "glyph_height": 26,
                                "body_origins": [[20, 300], [20, 316], [20, 332]],
                                "primary_font_handles": 3, "safe_fit_width": BODY_WIDTH},
        "width_risk_counts": dict(widths), "width_risks": risks,
        "native_r_lexical_runs": [{"spans": count, "first_owner": owner, "runs": runs}
                                  for (count, owner), runs in sorted(page_runs.items())],
        "limits": [
            "Body estimates use the measured primary style-2 owner, including fullwidth versus compact spaces. "
            "Rows with unsupported native controls require their own replay.",
            "Header candidates prove lexical boundaries. Dispatch proof comes from the speaker probe.",
            "Name bounds are examples. The editor provides three cells per field. Speaker-selected px aliases "
            "can vary by context. Legacy envelopes describe stored fields, not input-editor or ADV-parser acceptance.",
            "String adjacency does not count unmapped or event-script rows. The native replay checks rendered rows.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("iso", type=Path)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    report = screen(args.iso, args.inventory)
    with args.report.open("x") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(report["owner_counts"], report["width_risk_counts"])


if __name__ == "__main__":
    main()
