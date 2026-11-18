# r67m diagnostic candidate — coverage report

## Candidate identity

| Field | Value |
|---|---|
| ISO path | `/private/tmp/kowloon-recharge-r67m-diagnostic.iso` |
| ISO SHA-256 | `ebdca546d086635244d2a0336be2ce92bae26d5af57b1216efdf30a36ca0b299` |
| ISO size | 2,095,382,528 bytes (unchanged from pristine) |
| Source ISO SHA-256 | `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476` (verified unchanged) |
| ELF SHA-256 | `dec0806b1cac2636317aaea85ebdc5e842114340ee2ada9ce1baa7e78db7db73` |
| ELF size | 8,403,943 bytes |
| Serial | `SLPM-66511` (preserved) |
| Save namespace | `BISLPM-66511Save` (preserved) |
| Startup acceptance | **121/121** checks passed |
| Test suite | **133 tests OK** (7 expected skips) |

## Baseline relationship

This candidate derives from the v9 startup branch (`fix/startup-title-atlas-v9`)
with two improvements to the script-transfer tooling:

1. **CP932-boundary DC key merge** in `tools/localization.py`: Adjacent DC keys
   separated by exactly one CP932 character (single-byte control tokens like `l`,
   `p`, `N` or two-byte CP932 characters) are now correctly merged into a single
   group instead of creating a broken 1–2 byte group. This recovers 22 previously
   rejected exact MTX files.

2. **Relaxed numeric context** in `tools/structural_import.py`: Structural mapping
   now allows control sequence parameters that differ only in numeric values
   (e.g., `ch03398` vs `ch04620`) when the text content is byte-identical. This
   safely recovers speaker-name tags in structurally changed scripts.

r67.15k remains the gameplay-approved baseline. r67.15l (emotion wheel art) has
staged but uncommitted work in the `first-save-r67` worktree. Neither is modified
by this candidate. This is a separate diagnostic for script-transfer coverage.

## Coverage summary

### MTX script coverage

| Class | Files | Entries | Status |
|---|---:|---:|---|
| Exact MTX imported | 984 | 77,020 | Installed in candidate |
| Exact MTX rejected (FN02_31) | 1 | 1,294 | Indirect/dynamic — see unresolved |
| Structural MTX imported | 13 | 15,707 | Installed in candidate |
| Structural MTX rejected | 5 | 5,648 | See per-file unresolved reasons |
| **Total imported MTX** | **997** | **92,727** | |
| Previously (v9 baseline) | 969 | 58,926 | |
| **Delta** | **+28** | **+33,801** | |

### KSF coverage

| Class | Count | Status |
|---|---:|---|
| Fitting official entries | 868 | Installed in candidate |
| Overflow entries | 48 | Unresolved — see below |
| Ambiguous entries | 4 | Unresolved — fullwidth spaces |

### Overlay summary

| Layer | Files |
|---|---:|
| Exact MTX | 984 |
| Exact KSF | 144 |
| Structural MTX | 13 |
| Accepted overrides (DG00 KSF) | 1 |
| Startup graphics | 32 |
| **Total overlay files** | **1,173** |
| In place | 893 |
| Relocated | 280 |
| ROFS records patched | 1,173 |

## New content in this candidate (vs v9 baseline)

### Newly imported exact MTX (+22 files, +20,378 entries)

| File | Entries | Root cause |
|---|---:|---|
| FD/FD10_13.MTX | 66 | DC key `l` prefix merge |
| FN/FN13_12.MTX | 246 | DC key `l` prefix merge |
| MS/MS01_02.MTX | 622 | DC key `l` prefix merge |
| MS/MS02_01.MTX | 1,135 | DC key `l`/two-byte prefix merge |
| MS/MS02_02.MTX | 526 | DC key `l` prefix merge |
| MS/MS02_03.MTX | 1,093 | DC key `l` prefix merge |
| MS/MS03_03.MTX | 1,361 | DC key `l` prefix merge |
| MS/MS04_00.MTX | 40 | DC key two-byte prefix merge |
| MS/MS04_01.MTX | 2,990 | DC key `l`/two-byte prefix merge |
| MS/MS04_02.MTX | 368 | DC key two-byte prefix merge |
| MS/MS04_03.MTX | 608 | DC key `l` prefix merge |
| MS/MS06_00.MTX | 234 | DC key `l` prefix merge |
| MS/MS06_02.MTX | 810 | DC key `l` prefix merge |
| MS/MS07_01.MTX | 1,825 | DC key `l`/`p` prefix merge |
| MS/MS08_03.MTX | 1,856 | DC key `p` prefix merge |
| MS/MS09_02.MTX | 165 | DC key `p` prefix merge |
| MS/MS09_03.MTX | 919 | DC key `p` prefix merge |
| MS/MS10_01.MTX | 2,466 | DC key `p` prefix merge |
| MS/MS10_03.MTX | 2,003 | DC key `l` prefix merge |
| MS/MS12_00.MTX | 121 | DC key `l` prefix merge |
| MS/MS13_00.MTX | 668 | DC key `l` prefix merge |
| MS/MS13_03.MTX | 256 | DC key two-byte prefix merge |

### Newly imported structural MTX (+6 files, +13,423 entries)

| File | Entries | Root cause |
|---|---:|---|
| MS/MS05_01.MTX | 1,379 | DC key merge enabled structural proof |
| MS/MS06_01.MTX | 2,051 | DC key merge enabled structural proof |
| MS/MS08_01.MTX | 2,648 | Relaxed numeric context for speaker tags |
| MS/MS11_01.MTX | 2,582 | Relaxed numeric context for speaker tags |
| MS/MS11_03.MTX | 2,631 | DC key merge enabled structural proof |
| MS/MS12_01.MTX | 2,132 | Relaxed numeric context for speaker tags |

## Per-file unresolved reasons

### FN/FN02_31.MTX (1,294 entries) — indirect/dynamic mapping

The 604-byte PS2 file has DC keys that extend far beyond its actual size.
This is a dynamic localization table, not a literal byte-offset map.
**Evidence needed:** Model the runtime dynamic text-selection semantics.

### MS/MS00_01.MTX (43 entries) — completely different structure

All 42 DC groups fail structural mapping. PS2 and PS4 have fundamentally
different script structures for this file.

### MS/MS01_00.MTX (2,541 entries) — single genuinely different text

2,505 of 2,506 groups are proven (99.96%). The single failure at anchor
19092 maps to a genuinely different PS2 text passage (PS4 condensed a
list of ghost story titles). The current architecture requires 100% group
proof before emitting a file.
**Evidence needed:** Safe partial-emission policy or manual override.

### MS/MS01_03.MTX (226 entries) — completely different structure

All 222 DC groups fail structural mapping. PS2 and PS4 have fundamentally
different script structures for this file.

### MS/MS06_03.MTX (1,734 entries) — partial structural differences

1,664 of 1,693 groups proven (98.3%). 29 unresolved groups.
**Evidence needed:** Per-group investigation of the failing anchors.

### MS/MS13_02.MTX (1,104 entries) — partial structural differences

1,070 of 1,101 groups proven (97.2%). 31 unresolved groups.
**Evidence needed:** Per-group investigation of the failing anchors.

### FD00 template family (25 files, ~725 entries)

PS4 collapsed all FD00 scripts into a shared 604-byte template. PS2 has
unique per-character scripts (1.7–9.1 KB each). The template Japanese
text does not match the PS2 Japanese — only FD00_31 (already proven) has
matching content.
**Evidence needed:** Semantic character-identity matching with PS2 dialogue.

### KSF overflow (48 entries)

Official English text exceeds the PS2 fixed-field capacity by 1–11 bytes.
The KSF format's reference/relocation semantics are unproven.
**Evidence needed:** KSF record-structure research or reviewed abbreviations.

### KSF ambiguous (4 entries in MS/MS09_03.KSF)

Official text contains only fullwidth spaces (U+3000), not ASCII. These
appear to be blank separator labels, not translatable content.

### PS2-only files (449 files)

No PS4 counterpart exists. Lexical proxy estimates 419 novel Japanese runs
(3,672 characters) that don't appear in any mapped common content. Requires
original translation.

## Gameplay checklist

This candidate has **not** been runtime-tested. The following checklist
should be verified when runtime testing is approved:

- [ ] English opening quotation appears (any of 29)
- [ ] Memory-card stone-panel reads `Checking memory card slot 1`
- [ ] Red-sky/title shows English title artwork (GP088_03/GP088_12)
- [ ] `New Game` / `Load Game` render correctly
- [ ] `Enter last name.` renders; lowercase and uppercase keyboard work
- [ ] 3+3 name field limit is still present (known structural limit)
- [ ] `Enter reading for last name.` shows complete (not just `Enter`)
- [ ] `Enter first name.` / `Enter reading for first name.` show complete
- [ ] `Is this fine?` / `Yes / No` screen appears (no freeze)
- [ ] License verification messages appear
- [ ] `Heracleion Shrine` label appears
- [ ] H.A.N.T. tutorial shows English text
- [ ] First old-man dialogue is English and horizontal
- [ ] DG00 English choices appear
- [ ] Navigate to later chapters — newly translated MS/FN/FD/ID files
- [ ] Save and load work with `BISLPM-66511Save` namespace
- [ ] No Japanese text appears in any translated dialogue file
- [ ] No vertical English text appears
- [ ] No truncated or corrupted text appears

## Deterministic reproduction

```bash
# 1. Extract PS2 ISO
7z e "/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z" \
  -o/private/tmp/khc-ps2

# 2. Extract PS2 ADV from CVM
python3 -c "..." # (see docs/BUILD.md extraction script)

# 3. Link PS4 sources
PS4_SA=".worktrees/first-save-r67/local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets"
mkdir -p /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data
ln -sf "$PWD/$PS4_SA/data/ADV" /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV
ln -sf "$PWD/$PS4_SA/data/English.bytes" /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/English.bytes

# 4. Regenerate overlays
rm -rf local/exact-mtx local/exact-ksf local/structural-mtx
python3 -m tools.import_exact_mtx --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output-root local/exact-mtx --report local/exact-import-report.json
python3 -m tools.import_exact_ksf --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output-root local/exact-ksf --report local/ksf-report.json
python3 -m tools.import_structural_mtx --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output-root local/structural-mtx --report local/structural-import-report.json \
  --allow-template-path FD/FD00_31.MTX
python3 -m tools.build_early_ui_elf

# 5. Build ISO
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-r67m-diagnostic.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/r67m-build-report.json

# 6. Verify
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-r67m-diagnostic.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/r67m-acceptance-report.json
python3 -m unittest discover -s tests -v
```

## Environment

- Python 3.14 (`/opt/homebrew/bin/python3`)
- macOS Darwin 25.6.0
- 7z from Homebrew
- No external Python dependencies required for core build (Pillow optional for graphics)
