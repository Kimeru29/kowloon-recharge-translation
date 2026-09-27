# Kowloon Youma Gakuenki re-charge — English PS2 translation

I'm working on bringing the official English localization from the modern remaster back to the original Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**.

The goal is to keep the PS2 game feeling like the PS2 game: same presentation, same UI, same timing and quirks, just actually playable in English. The remaster gives me a very good official translation to work from, but this is not a simple copy/paste job. A lot of the data moved or changed between versions, some PS2 content does not exist in the remaster, and several menus and renderers were built specifically around Japanese text.

This repository is where I'm building the tools and documenting the reverse-engineering needed to make that work reliably.

## Where it is now

The project is well past the proof-of-concept stage. It can build a deterministic translated PS2 image from a pristine source, and most of the script content that has a proven remaster counterpart is already imported.

Right now most of my work is on the parts that need actual runtime polish rather than more bulk translation: title/startup screens, dialogue layout, H.A.N.T. menus, name entry, memory-card messages and the smaller PS2-only pieces.

A few structural limitations are still known, especially the original 3+3-character permanent-name storage and a small set of KSF fields that cannot safely fit the English text yet. I would rather leave something untouched than guess at a mapping and silently corrupt another part of the game.

For the exact current build, hashes, test counts and runtime findings, see [`docs/LOCALIZATION_STATUS.md`](docs/LOCALIZATION_STATUS.md). That file is intentionally much more technical than this README.

## How I'm approaching the translation

- Use the official English text whenever I can prove the PS2/remaster correspondence.
- Keep PS2- or re-charge-exclusive material separate instead of pretending it came from the remaster.
- Make binary changes fail closed when an expected preimage or layout no longer matches.
- Keep builds reproducible and verify the finished ISO, not only intermediate files.
- Treat emulator screenshots as the final word for visual work. A static check can prove that I changed what I intended; it cannot prove that the game actually looks right.

That last point has mattered a lot. Several technically correct-looking changes turned out to be wrong once the game rendered them, so I now keep static verification and runtime acceptance deliberately separate.

## What is in this repository

Mostly Python tooling, tests and reverse-engineering notes for:

- importing exact and structurally changed script data;
- rebuilding constrained KSF text safely;
- patching executable-owned UI strings and layout code;
- porting/repacking indexed PS2 graphics;
- rebuilding the nested CVM/ISO image;
- re-resolving executable ROFS records after relocation; and
- checking regressions against already accepted work.

If you want the technical entry point, start with [`docs/HANDOFF.md`](docs/HANDOFF.md), then [`docs/BUILD.md`](docs/BUILD.md) and [`docs/DISCOVERY.md`](docs/DISCOVERY.md).

## Game files are not included

This repository does **not** contain the game ISO, executable, extracted game assets, official bulk script data, fonts, textures or generated translated binaries.

Those inputs come from legally obtained copies and stay local. The build outputs and proprietary working data are ignored by Git as well.

## Tests

The normal suite has no optional graphics dependency:

```bash
python3 -m unittest discover -s tests -v
```

The full graphics suite uses Pillow:

```bash
uv run --with pillow python -m unittest discover -s tests -v
```

Tests that require my local game fixtures skip cleanly when those files are not present.

## Status

This is still a work in progress. I runtime-test each candidate in PCSX2 before I consider visual changes accepted, and I keep the detailed checkpoint history in [`docs/LOCALIZATION_STATUS.md`](docs/LOCALIZATION_STATUS.md).
