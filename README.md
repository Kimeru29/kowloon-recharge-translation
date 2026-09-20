# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python tooling and reverse-engineering notes for importing the official English localization from the PS4 remaster into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating PS2-exclusive content separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, font, texture, or copied script binary**. You must provide legally obtained source files locally.

## Current status

The project can parse/rebuild PS2 MTX pointer regions, patch proven fixed ELF/KSF fields, rebuild the CVM/ISO vertical slice, classify the full ADV corpus, import exact official-English MTX entries fail-closed, conservatively patch exact KSF fields, and enforce cumulative translation/save-identity regressions.

Verified live-corpus snapshot:

- PS2: 1,516 MTX + 1,516 KSF; PS4 counterpart set: 1,067 of each; PS2-only: 449 of each.
- MTX: 1,022 byte-identical common files. 985 are both exact and English-mapped, containing 78,314 official English entries.
- Exact MTX importer currently proves and imports **962 files / 56,642 English entries**; 23 files / 21,672 entries are rejected rather than guessed.
- KSF: 144 exact English-mapped files; **868 entries fit proven fixed fields**, 48 overflow and remain untouched, 4 are ambiguous.
- MTX lexical-run estimate: 41,337 unique Japanese CP932 runs (2+ chars), with only **419 novel runs / 3,672 characters** found exclusively in PS2-only content relative to mapped common content. This is a lexical estimate, not a dialogue-line count.

Exact file identity is deliberately not treated as sufficient proof: indirect/dynamic DC maps are rejected until understood.

## Start here

For a new human or AI session, read [`docs/HANDOFF.md`](docs/HANDOFF.md) first.

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

Local fixture-dependent tests skip cleanly when the proprietary fixtures are absent.

## Runtime-test rule

Do not launch PCSX2 for a new build until the expected visible English scope has been stated to Pablo and he has explicitly approved that launch.
