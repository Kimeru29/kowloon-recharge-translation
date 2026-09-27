# Kowloon Youma Gakuenki re-charge — PS2 English translation tooling

Python reverse-engineering and build tooling for backporting the official PS4 remaster English localization into the Japanese PS2 release of **Kowloon Youma Gakuenki re-charge**, then translating the small PS2/re-charge-exclusive remainder separately.

This repository intentionally contains **no game image, package, executable, extracted game asset, official bulk script data, font, texture, or generated translated game binary**. Legally obtained sources and generated artifacts stay local and are ignored by Git.

## Current status

The project can build a deterministic whole-game translation candidate from the pristine PS2 ISO. The current **startup v11-r8** candidate is a narrow runtime-polish release based on Pablo's accepted r7 improvements:

- exact MTX: **962 files / 56,642** official English entries;
- changed/template MTX: **7 files / 2,284** official entries;
- exact KSF: **868** fitting official fields; 48 overflows and 4 ambiguous entries remain fail-closed;
- startup executable UI: exact title/name/profile text, PS2-adapted Latin keyboard, translated H.A.N.T. chrome/topics/config, tutorial text/controller metadata, and the proven memory-card subset;
- **r7 preservation constraints:** name/confirmation/license centering is accepted; dialogue speaker orientation/brackets and 12px horizontal body spacing are accepted improvements; H.A.N.T. and working title anchors remain untouched in r8;
- r8 dialogue geometry: speaker remains horizontal at X=20 but moves to Y=276; the body keeps its 12px stride and moves only its transposed Y base from 114 to 312;
- r8 stone tablet: keeps the translated centered second line and adds exactly one more leading line break to lower the block;
- r8 title backing: preserves r7's `New Game` / `Load Game` anchors and `GP088_03`/`GP088_12`, but extends only the proven `GP088_08` lower menu-label backing from 70px to 150px and shifts its existing trailing marker by 80px;
- current candidate: **1,145 overlay assets**, 892 in place / 253 relocated, with all 1,145 executable ROFS records re-resolved;
- v11-r8 startup final-image acceptance: **140/140 checks passed**;
- candidate SHA-256: `c2905f8bf1ebe20defb5479591c0dbf86b2e9bfbf9c6062db37ccf6f8ba6593f`;
- dependency-free suite: **201 tests OK** (10 expected skips); Pillow-enabled suite: **201 tests OK** (one owned-corpus skip);
- deterministic repeat build is byte-for-byte identical;
- **r8 has not been launched in PCSX2**. Pablo is the runtime tester. The structural 3+3 permanent-name storage remains an explicit unresolved limitation.

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
