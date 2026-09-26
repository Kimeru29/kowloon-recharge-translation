# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v11-r5** candidate preserves the accepted title/tablet geometry and adds only the four runtime-defect corrections requested after the r4 screenshots:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact title/name/profile text, PS2-adapted Latin keyboard, H.A.N.T. tutorial text/controller metadata, seven semantic H.A.N.T. chrome labels, the 15 proven Help-topic aliases, and the proven memory-card subset;
- r5 runtime-layout deltas: the separate speaker-name canvas now uses horizontal advance; the H.A.N.T. tutorial keeps the 12px style but tightens its page-local row stride `21→18px`; the pre-title memory-card line is split as `Checking memory card` / `slot 1`; and the H.A.N.T. Help/topic owners are translated rather than left as unresolved aliases;
- H.A.N.T. baked graphics: `GRP020/GP020_03.TMX` is the proven six-tile atlas owner; nine caption regions are repainted to semantic English (`HELP`, `CONFIG`, `MAIL`, `DICTIONARY`, `ENEMY`, `MEMO`, `RESET DEFAULTS`, `DELETE`, `PAGE`) while every pixel outside those fail-closed regions remains unchanged. This artwork is **semantic**, not claimed as official-remaster art because the owned PS4 extraction does not currently expose a localized GP020 bundle;
- startup graphics: official English `B_GP019`, semantic-English `B_GP020`, direct `B_GP088/GP088_03`, structurally repacked English `B_GP088/GP088_12`, and all **29** `BLBRD/INIT_MES/TR000–TR028.TMX` quotation images;
- current candidate: **1,145 overlay assets**, 892 in place / 253 relocated, with all 1,145 executable ROFS records re-resolved;
- v11-r5 startup final-image acceptance: **137/137 checks passed**;
- candidate SHA-256: `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`;
- dependency-free suite: **191 tests OK** (8 expected skips); Pillow-enabled suite: **191 tests OK** (one owned-corpus skip);
- deterministic repeat build is byte-for-byte identical;
- **r5 has not been launched in PCSX2**. Pablo will perform the runtime checks manually; static acceptance is not treated as runtime proof. The structural 3+3 permanent-name storage remains an explicit unresolved limitation.

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
