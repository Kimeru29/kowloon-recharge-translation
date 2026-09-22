# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v5** candidate adds the complete statically identified boot-to-first-dialogue slice on top of the broad script import:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact `New Game` / `Load Game`, name/profile prompts, protagonist names, Latin name-entry keyboard, and first-dungeon label;
- startup graphics: official English `B_GP019` name-entry controls plus all **29** random `BLBRD/INIT_MES/TR000–TR028.TMX` quotation images;
- current candidate: **1,143 overlay assets**, 890 in place / 253 relocated, with all 1,143 executable ROFS records re-resolved against the finished ISO;
- startup static acceptance: **114/114 checks passed**;
- candidate SHA-256: `f8d65c029f86ce871f9d9930f76d12b6f6a95c79c4152a0437b19ceef1fd20b5`;
- runtime validation of v5 is still pending the explicit launch-approval gate.

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
