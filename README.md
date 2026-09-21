# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, or texture**. Legally obtained sources stay local and generated game binaries are ignored.

## Current status

A deterministic whole-game PS2 candidate can now be generated from the pristine ISO. The current local candidate combines **1,113 translated ADV assets** plus the proven early ELF UI patch while preserving PS2 serial/save identity and validating the finished nested ISO/CVM image.

Verified live-corpus snapshot:

- exact MTX: 962 files / 56,642 official English entries proven and imported;
- changed/template MTX: 7 files / 2,284 official entries proven and imported;
- exact KSF: 868 fitting fields imported; 48 overflows and 4 ambiguous entries stay fail-closed;
- current whole-game candidate: 860 in-place replacements + 253 append-relocations, same total ISO size as pristine;
- current candidate SHA-256: `8fc57b8b295a414e15ebb5d2d762114e3106282564f38ae30a7f63bc10a06362`;
- PS4 English graphics bundles have been located and inventoried; PS2 TMX re-encoding/repacking is the remaining graphics blocker.

Exact file identity is deliberately not treated as sufficient proof: indirect/dynamic localization maps are rejected until understood.

## Start here

For a new human or AI session, read [`docs/HANDOFF.md`](docs/HANDOFF.md) first.

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Local proprietary-fixture tests skip cleanly when the user-owned sources are absent.

## Runtime-test rule

Do not launch PCSX2 for a new build until the expected visible English scope has been stated to Pablo and he has explicitly approved that launch.
