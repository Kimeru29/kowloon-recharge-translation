# AI handoff — Kowloon re-charge PS2 English translation

## Mission

Create a high-quality English translation of the Japanese PS2 **Kowloon Youma Gakuenki re-charge** by automatically backporting the official PS4 remaster English wherever correspondence is proven, then manually translating only PS2/re-charge-exclusive content. Pablo supervises; the agent does the technical work.

## Non-negotiable rules

1. Never alter pristine PS2/PS4 source files; work on copies/output trees only.
2. Never commit copyrighted game binaries/extracted assets to GitHub.
3. Automatic import is fail-closed: ambiguous items go to a report/manual queue, never guessed.
4. Preserve serial/save identity: `SLPM-66511`, `BISLPM-66511Save`.
5. **Do not launch PCSX2 until you have stated the exact expected visible result for that build and Pablo explicitly approves the launch.** Static analysis/building needs no approval.
6. Pablo explicitly authorized autonomous coding/documentation/Git work for the project; do not stop for routine implementation approvals.

## Current local sources

- PS2 archive: `/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z`
- PS2 pristine ISO copy: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
- PS2 extracted ADV: `/private/tmp/khc-ps2-assets/ADV`
- PS4 PKG: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
- PS4 extracted root: `/private/tmp/khc-ps4-extracted/CUSA27034`
- PS4 ADV: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV`
- Repository: `/Users/juan.pena/repos/kowloon-recharge-translation`
- PCSX2: `/Users/juan.pena/Desktop/Emulators/PCSX2-v2.7.514.app` — **do not launch without the explicit visual-test approval above**.

Source hashes are in `docs/DISCOVERY.md` and `config/sources.example.json`. `local/source-manifest.json` contains the current machine-specific paths and verified hashes.

## Current verified corpus

- PS2 MTX/KSF: 1,516 each.
- PS4 counterpart MTX/KSF: 1,067 each.
- PS2-only: 449 MTX + 449 KSF, overwhelmingly FI plus one MS file.
- Exact common MTX: 1,022; exact+English-mapped MTX: 985 / 78,314 official entries.
- Exact MTX importer currently proves **962 files / 56,642 entries** and rejects 23 files / 21,672 entries rather than guessing.
- Changed MTX: 45 total; 43 English-mapped / 22,084 entries.
- Exact common KSF: **1,010**; exact+English-mapped KSF: 144.
- Conservative KSF importer: 868 fitting entries, 48 overflows untouched, 4 ambiguous.
- Lexical PS2-only estimate: 568 unique runs occur in PS2-only files, but only **419 runs / 3,672 Japanese characters** are novel relative to mapped common MTX content.

Do not revive the old exploratory `1,019 exact KSF` count; the deterministic current scan plus independent byte comparison both prove 1,010.

## Current generated local reports

These are intentionally ignored by Git:

- `local/source-manifest.json` — source paths/sizes/hashes + serial/save identity.
- `local/corpus-manifest.json` — full MTX/KSF source relationship and map inventory plus lexical text-size estimate.
- `local/exact-import-report.json` — every exact mapped MTX import/rejection and output hash.
- `local/exact-mtx/` — generated exact-tier MTX outputs.
- `local/ksf-report.json` — exact KSF field status and output hashes.
- `local/exact-ksf/` — conservatively patched exact KSF outputs.

Regenerate these rather than trusting stale copies if source or parser code changes.

## Current implementation

- `tools/mtx.py`: parses quarter-offset MTX header, rebuilds pointer regions and relocates pointers.
- `tools/localization.py`: DC grouping, boundary-aware localized-span inference and generalized two-byte CP932 English encoder.
- `tools/corpus.py`: deterministic corpus classification and lexical PS2-only text estimate.
- `tools/exact_import.py` / `tools/import_exact_mtx.py`: fail-closed exact official-English MTX importer.
- `tools/ksf_import.py` / `tools/import_exact_ksf.py`: conservative exact KSF fixed-field proof/import.
- `tools/regression.py` / `tools/check_regression.py`: cumulative accepted-translation + save/serial regression gate.
- `tools/source_manifest.py`: reproducible local source identity manifest.
- `tools/elf_strings.py` / `tools/early_ui.py`: proven early UI fixed-string patches.
- `tools/cvm.py`, `tools/iso9660_patch.py`, `tools/build_vertical_slice_iso.py`: validated early ISO/CVM rebuild path.
- `translations/accepted.json`: artifact-level accepted regression baseline; stores hashes/provenance, not copied bulk script text.

Baseline before this phase was 34 passing tests. Run the current suite rather than relying on that number.

## Exact MTX caveat

Exact source identity is necessary but not sufficient. `FN/FN02_31.MTX` is only 604 bytes while its English DC map contains 1,294 entries with repeated/dense keys. It is byte-identical PS2↔PS4 but the map is indirect/dynamic, so the exact importer correctly rejects it. Several MS files have unresolved continuation/control-key semantics (`l`, `p`, partial anchors) and are also intentionally rejected. Do not “fix” these by blindly treating all keys as byte offsets.

## KSF caveat

The PS4 remaster applies localization externally, so an exact KSF does not prove English can fit the PS2 inline field. Current KSF import requires the observed `0x01` record marker, valid CP932 source, NUL/padding boundary and a following structural byte. Overflows stay Japanese until a relocatable KSF compiler is proven. Never truncate official text as a bulk-import strategy.

## Early vertical-slice runtime expectation from the last completed build

The existing early build was intended to show `New Game` / `Load Game`, the mapped DG00 opening conversation in English, several opening choices, and many H.A.N.T./command labels. `Media`, `Report card`, and `Return above ground` intentionally remained Japanese because mapping/capacity was not safe. This expectation is historical only: before the **next** emulator launch, restate the expectation for the actual new build and obtain fresh approval.

## Next technical phase after repository publication

1. Turn the proven exact MTX/KSF outputs into a deterministic multi-file build layer rather than isolated output trees.
2. Solve structurally changed MTX transfer using token/control-aware monotonic alignment, validating `DG13_02` first.
3. Solve template/semantic FD00 matching separately; do not raw-align remaster templates.
4. Build a relocatable KSF compiler for the 48 current overflows and changed KSF maps.
5. Locate/extract the packed PS4 localized graphics referenced by `AssetFileDic_en.txt` and backport only proven format-equivalent assets.
6. Generate the next controlled test ISO. Before launching it, state the exact expected visible English scope and wait for Pablo's explicit approval.

## Key reverse-engineering facts

- MTX first u16 × 4 = header size; header u16 values are 4-byte-unit entry offsets.
- MTX data mixes CP932 Japanese with ASCII control language; ordinary ASCII English cannot yet be injected blindly.
- Full-width/two-byte CP932 Latin is the current safe dialogue representation.
- FD00 remaster scripts are often shared templates; use semantic/template matching later, not raw offsets.
- PS4 `English.bytes` parses to 11,711 Japanese→English records; useful as terminology/translation memory, not for blind substring replacement.
- PS4 localized graphics are referenced by `AssetFileDic_en.txt`; actual localized PNG data appears packed rather than loose and still needs extraction/backport work.

## Resume procedure

1. `cd /Users/juan.pena/repos/kowloon-recharge-translation`
2. Read this file, `docs/DISCOVERY.md`, the current spec/plan, and `git log --oneline -10`.
3. Run `python3 -m unittest discover -s tests -v`.
4. Inspect/regenerate `local/` reports; they are intentionally untracked.
5. Check `git status --short --branch` and continue from the first incomplete technical item.
6. Never rebuild from the previous patched ISO; always derive from pristine sources.
7. Never launch the emulator without the fresh visual-expectation approval gate.
