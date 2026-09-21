# AI handoff — Kowloon re-charge PS2 English translation

## Mission

Create a high-quality English translation of the Japanese PS2 **Kowloon Youma Gakuenki re-charge** by backporting the official PS4 remaster English wherever correspondence is provable, then translate PS2/re-charge-exclusive material separately. Pablo supervises; the agent performs the reverse engineering, tooling, builds, validation, documentation, and Git work.

## Non-negotiable rules

1. Never alter pristine PS2/PS4 sources; always derive outputs from copies/pristine inputs.
2. Never commit copyrighted game binaries, extracted assets, official bulk localization data, fonts, textures, ISO/PKG/CVM files, or executable fixtures.
3. Automatic import is fail-closed. Ambiguous correspondence stays Japanese and is reported; never guess merely to increase coverage.
4. Preserve `SLPM-66511` and `BISLPM-66511Save` across builds.
5. **Do not launch PCSX2 until the exact expected visible result for that build has been stated to Pablo and Pablo explicitly approves the launch.** Static analysis/builds need no approval.
6. Pablo authorized autonomous implementation/documentation/Git decisions. Do not stop for routine approvals.

## Canonical workspace

- Repo: `/Users/juan.pena/repos/kowloon-recharge-translation`
- Private GitHub: `https://github.com/Kimeru29/kowloon-recharge-translation` (`main`)
- Whole-game phase implementation commit: `e1b5153` (`Build deterministic whole-game translation candidate`)
- Runtime ROFS/title bugfix commit: `6312dd4` (`Fix runtime ROFS metadata and title encoding`)
- PS2 pristine ISO: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
  - SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`
  - size: `2,095,382,528`
- PS2 ADV: `/private/tmp/khc-ps2-assets/ADV`
- PS4 PKG: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
  - SHA-256: `054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`
  - title ID: `CUSA27034`
- PS4 extracted root: `/private/tmp/khc-ps4-extracted/CUSA27034`
- PS4 ADV: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV`
- PCSX2: `/Users/juan.pena/Desktop/Emulators/PCSX2-v2.7.514.app` — **do not launch without the approval gate above**.

Machine-specific identity is regenerated into ignored `local/source-manifest.json`.

## Current milestone: v1 runtime failure diagnosed; v2 candidate statically verified

The first broad runtime candidate was launched after approval and **failed**: opening dialogue remained Japanese and the title options became 4–5 meaningless Latin-looking glyphs. Do not treat v1 as valid.

Root causes are now proven:

- `SLPM_665.11` contains the runtime ROFS file table (size at filename-14, sector extent at filename-6). The v1 generic builder relocated 253 files in ISO9660 but did not update this table, so the game read stale Japanese extents. All 1,113 overlay assets have unique pristine size+extent matches in the ELF.
- The title renderer consumes two-byte glyph codes. v1 wrote single-byte ASCII. The title now uses wide CP932 constrained labels `NewGame` and `Load`.

Current v2 candidate:

- path: `/private/tmp/kowloon-recharge-whole-en-candidate-v2.iso`
- SHA-256: `b549af9528236092631026929990fa3a1dc890451f6a9ecbcb443eed4734b97e`
- 1,113 overlay assets; 860 in place / 253 relocated
- 1,113/1,113 ELF ROFS records patched and final-runtime-path validated
- 84/84 local tests pass
- `SLPM-66511` and `BISLPM-66511Save` preserved
- **runtime re-test has NOT occurred yet; fresh explicit approval is required**

## Current corpus / import coverage

MTX:

- PS2: 1,516
- PS4 counterparts: 1,067
- PS2-only: 449
- exact common: 1,022
- exact + English-mapped: 985 / 78,314 official entries
- proven exact import: **962 files / 56,642 entries**
- rejected exact: 23 files / 21,672 entries
- changed + English-mapped: 43 / 22,084 entries
- proven changed/template import in this candidate: **7 files / 2,284 entries**

The seven changed/template MTX files emitted are:

- `DG/DG13_02.MTX` — 577 official entries, 573 semantic groups (571 direct + 2 semantic)
- `FD/FD00_31.MTX` — 29 entries
- `FN/FN13_16.MTX` — 339 entries
- `ID/ID00_21.MTX` — 45 entries
- `ID/ID00_26.MTX` — 47 entries
- `ID/ID00_41.MTX` — 50 entries
- `MS/MS05_03.MTX` — 1,197 entries

KSF:

- exact common: **1,010**; do not revive the old exploratory 1,019 count
- exact + English-mapped: 144 files
- proven fixed fields: 868 fitting official entries
- 48 overflows across 21 files remain fail-closed
- 4 entries remain ambiguous

PS2-only lexical proxy:

- 41,337 unique Japanese CP932 lexical runs overall
- 568 unique runs occur in PS2-only MTX
- only **419 runs / 3,672 Japanese characters** are novel relative to mapped common content
- this is a lexical-run estimate, not a dialogue-line percentage

## Exact-map caveat

Byte-identical source data does **not** imply every PS4 DC key is a literal PS2 text offset. Example: `FN/FN02_31.MTX` is only 604 bytes but its localization map has 1,294 entries, 1,150 unique keys, repeated keys, and keys extending far beyond the file size. Other rejected maps split semantic text on control tokens such as `l`, `px`, `pn`, and `pm`. Never make the exact importer treat every DC key as an independent literal replacement merely to increase coverage.

## Structural / FD00 status

`tools/structural_import.py` uses monotonic exact-byte alignment plus semantic/control validation and emits a changed file only when every localized semantic group is proven.

`DG/DG13_02.MTX` is the principal proof case: all official groups are safely transferred.

The remaster consolidates the FD00 family into small shared templates. A deliberate probe allowed all 26 mapped `template` files through the structural matcher:

- only `FD/FD00_31.MTX` passed
- the other **25/26 template files were rejected**

Therefore raw offset alignment is explicitly not the FD00 solution. The remaining family needs a dedicated semantic/template interpreter using speaker/text/control/sequence identity.

Ignored evidence: `local/fd00-template-probe-report.json`.

## KSF overflow status

KSF overflow relocation is **not solved** and must not be claimed as solved.

Evidence:

- all 48 overflows are in fields whose current conservative parser proves as inline fixed fields following the observed record marker/layout;
- searching each overflow DC key as little/big-endian 16/32-bit numeric values throughout its KSF found zero internal numeric-key occurrences;
- absence of numeric references is evidence only, not proof that following binary structures can be shifted safely;
- PS2↔PS4 changed KSF data does not expose a simple universal relocation scheme.

Current rule: fitting fields are patched; overflow fields remain Japanese unless there is an explicit reviewed constrained override such as the two DG00 choice strings. Never bulk-truncate official text.

Ignored evidence: `local/ksf-overflow-research.json`.

## Localized graphics status — extraction blocker is solved

`AssetFileDic_en.txt` has 1,167 pairs: 1,127 file-like localized mappings + 40 logical bundle aliases.

The actual English graphics are packed as Unity AssetBundles under:

`/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/BLBRD/`

`tools/graphics_inventory.py` can inventory them. With optional UnityPy (`uv run --with UnityPy ... --deep`):

- 40 English bundle aliases are declared
- **39 bundles are physically present**; only logical `bg_en` has no same-named file
- the 39 bundles expose **1,181 Texture2D objects**
- examples: `panel_item_en` = 450 item textures, `letter_en` = 160, `memo_en` = 50, `b_gp001_en` = 11

PS4 localized texture dimensions often map cleanly to PS2 TMX. Across the currently matched `B_GPxxx` sample:

- 246 same-name PS2/PS4 assets were compared across 31 groups
- **235/246 have exactly 9/4 (2.25×) PS4 dimensions in both axes**
- 11 have special/non-uniform layouts and need per-asset handling
- `GP001_00`, for example, is PS2 512×256 vs PS4 English 1152×576

The remaining graphics blocker is no longer finding/extracting the English art. It is implementing and proving deterministic downscale + indexed PS2 TMX palette encoding + container repacking. Graphics are **not included in the current runtime candidate**.

Ignored evidence:

- `local/graphics-inventory.json`
- `local/graphics-scale-report.json`

## Current implementation map

- `tools/elf_rofs.py`: parses/patches the executable ROFS size+sector-extent records used for runtime CVM asset lookup.

- `tools/mtx.py` — MTX pointer-region parser/compiler
- `tools/localization.py` — DC grouping + CP932 safe English encoder
- `tools/exact_import.py`, `tools/import_exact_mtx.py` — fail-closed exact MTX importer
- `tools/ksf_import.py`, `tools/import_exact_ksf.py` — conservative fixed-field KSF importer
- `tools/structural_import.py`, `tools/import_structural_mtx.py` — changed-source semantic/structural MTX importer
- `tools/translation_overlay.py` — deterministic overlay precedence/provenance + relocation planning
- `tools/build_translation_iso.py` — generic whole-game nested ISO/CVM builder + finished-image validation
- `tools/accepted_overrides.py` — explicit reviewed KSF exceptions
- `tools/early_ui.py`, `tools/elf_strings.py` — fixed-size ELF UI patches
- `tools/regression.py`, `tools/check_regression.py` — cumulative accepted-artifact and identity gate
- `tools/graphics_inventory.py` — PS4 localized graphics bundle inventory; UnityPy imported lazily
- `tools/decode_tmx_preview.py` — PS2 TMX preview decoder (research utility)

## Runtime gate for this candidate

Before launching `/private/tmp/kowloon-recharge-whole-en-candidate-v2.iso`, state the exact visible expectations to Pablo and wait for a fresh explicit approval. At minimum the expected opening scope must include the historical accepted slice (`NewGame`, `Load`, and the DG00 opening conversation; test further choices/UI only after this minimal proof passes), while explicitly warning that baked Japanese graphics and rejected/unsupported scripts can still appear Japanese.

## What comes after the first successful runtime test

1. Establish a golden in-game memory-card save and prove cross-build loading; back up the card before automated runtime tests. Treat emulator savestates as build-specific.
2. Investigate any rendering/control regressions observed in the broad 1,113-file candidate before increasing coverage.
3. Solve the 23 rejected exact MTX maps by modeling dynamic placeholders/semantic line grouping rather than broadening offset heuristics.
4. Build the dedicated FD00 semantic/template importer.
5. Implement PS4 Texture2D -> PS2 TMX downscale/quantize/repack, beginning with a simple exact-name 2.25× group such as GP001.
6. Continue KSF format research; leave overflow text untouched until shifting/references are proven.
7. Finally translate the small novel PS2-only queue with official terminology/style reuse.

## Resume procedure

1. `cd /Users/juan.pena/repos/kowloon-recharge-translation`
2. Read this file, `docs/DISCOVERY.md`, `docs/BUILD.md`, and the current spec/plan.
3. Run `python3 -m unittest discover -s tests -v`.
4. Check `git status --short --branch` and `git log --oneline -10`.
5. Regenerate `local/` reports if parser/importer code changed; never trust stale local artifacts after code changes.
6. Always build from the pristine PS2 ISO, never from a prior translated ISO.
7. Never launch PCSX2 without the exact-visual-scope approval gate.
