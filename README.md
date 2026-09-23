# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v8** candidate keeps the broad script import and fixes the v7 runtime translation-segment collision while expanding the proven startup UI/graphics classes:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact title/name/profile text, PS2-adapted Latin keyboard, H.A.N.T. long text, and a proven subset of memory-card messages relocated to official English;
- startup graphics: official English `B_GP019`, direct `B_GP088/GP088_03`, and all **29** `BLBRD/INIT_MES/TR000–TR028.TMX` quotation images;
- v7 runtime proved uppercase reachability but exposed a translation-PT_LOAD/heap collision: libkernel's live `sbrk` break still started at `0x00902F00`, corrupting the relocated reading prompt and then freezing the flow;
- v8 moves that runtime heap break to `0x00A02F00` along with the other heap metadata;
- current candidate: **1,144 overlay assets**, 891 in place / 253 relocated, with all 1,144 executable ROFS records re-resolved;
- v8 startup final-image acceptance: **120/120 checks passed**;
- candidate SHA-256: `7431f7f44eb9ed14927f2181491b02217efe8675c64c4c07789d13ad934aa550`;
- full Pillow-enabled test suite: **126 tests OK** (one owned-corpus skip);
- runtime proof for v8 is still required. The 3+3 permanent-name structure and PS2-specific packed GP088 title atlas remain explicit unresolved items.

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
