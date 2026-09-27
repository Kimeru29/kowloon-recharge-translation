# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v11-r7** candidate is driven by Pablo's r6 runtime feedback and preserves the translated content that already worked while correcting measured presentation owners:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact title/name/profile text, PS2-adapted Latin keyboard, seven semantic H.A.N.T. chrome labels, three Help category labels, all **55** Help-topic labels, nine Config labels, H.A.N.T. tutorial text/controller metadata, and the proven memory-card subset;
- r7 dialogue layout: the bracket-derived speaker now reaches a truly horizontal generic-font orientation, is placed as a separate header, and the transposed DG body uses the actual 12px style-1 advance instead of the old 26px Japanese column stride;
- r7 startup polish: name/confirmation/license prompt X owners are centered for English, the stone-tablet status gets additional top padding with `slot 1` centered under the first line, and the H.A.N.T. tutorial keeps its 12px font while tightening only its page-local row stride to 16px;
- H.A.N.T. baked graphics: `GRP020/GP020_03.TMX` remains the proven six-tile semantic-English atlas (`HELP`, `CONFIG`, `MAIL`, `DICTIONARY`, `ENEMY`, `MEMO`, `RESET DEFAULTS`, `DELETE`, `PAGE`); the long Help tab `Exploration` is shortened to `Ruins` on its proven three-tab text owner;
- title graphics: r7 deliberately preserves r6's recentered `New Game` / `Load Game` anchors and pristine packed-title scale. The remaining black-backing coverage is **known unresolved** because `GP088_08` is a multi-region title-chrome atlas and the exact live sampled subregion has not been proven;
- startup graphics: official English `B_GP019`, semantic-English `B_GP020`, direct `B_GP088/GP088_03`, structurally repacked English `B_GP088/GP088_12`, and all **29** `BLBRD/INIT_MES/TR000–TR028.TMX` quotation images;
- current candidate: **1,145 overlay assets**, 892 in place / 253 relocated, with all 1,145 executable ROFS records re-resolved;
- v11-r7 startup final-image acceptance: **140/140 checks passed**;
- candidate SHA-256: `2b64165f820ec208ff9d721b9fbf30d8ee17bb78b9556e7ebe540c83b27221b4`;
- dependency-free suite: **199 tests OK** (8 expected skips); Pillow-enabled suite: **199 tests OK** (one owned-corpus skip);
- deterministic repeat build is byte-for-byte identical;
- **r7 has not been launched in PCSX2**. Pablo manually tested r6; r7 remains static/deterministic until he accepts its target screens. The structural 3+3 permanent-name storage remains an explicit unresolved limitation.

Exact file identity is deliberately not treated as sufficient proof. Indirect/dynamic localization maps, KSF overflows, ambiguous structural mappings, and unproven graphics-atlas transformations remain untouched until correspondence/layout is proven.

## Start here

For a new human or AI session, read [`docs/HANDOFF.md`](docs/HANDOFF.md) first, then [`docs/BUILD.md`](docs/BUILD.md) and [`docs/DISCOVERY.md`](docs/DISCOVERY.md).

Normal dependency-free tests:

```bash
python3 -m unittest discover -s tests -v
```

Full graphics tests:

```bash
uv run --with pillow python -m unittest discover -s tests -v
```

Local proprietary-fixture tests skip cleanly when user-owned sources are absent.

## Runtime-test rule

Do not launch PCSX2 for a new build until the exact expected visible scope has been stated to Pablo and he has explicitly approved that launch.
