# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v7** candidate keeps the broad script import and the proven startup renderer/graphics work, then fixes two defects exposed by the v6 runtime test:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact `New Game` / `Load Game`, all eight name/profile prompts, protagonist names, PS2-adapted Latin name-entry keyboard, and first-dungeon label;
- startup graphics: official English `B_GP019` name-entry controls plus all **29** random `BLBRD/INIT_MES/TR000–TR028.TMX` quotation images;
- current candidate: **1,143 overlay assets**, 890 in place / 253 relocated, with all 1,143 executable ROFS records re-resolved against the finished ISO;
- v7 startup static acceptance: **98/98 checks passed**;
- candidate SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`;
- full Pillow-enabled test suite: **122/122**;
- v6 runtime proved the opening/title/name graphics and exposed name-entry defects; v7 still requires explicit runtime approval/proof. The structural PS2 3+3 permanent-name limit remains intentionally unresolved.

Exact file identity is deliberately not treated as sufficient proof. Indirect/dynamic localization maps, KSF overflows, and ambiguous structural mappings remain Japanese until their correspondence/layout is proven.

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
