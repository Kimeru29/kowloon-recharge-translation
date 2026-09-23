# AI handoff — Kowloon re-charge PS2 English translation

## Mission

Create a high-quality English translation of the Japanese PS2 **Kowloon Youma Gakuenki re-charge** by backporting the official PS4 remaster English wherever correspondence is provable, then translate PS2/re-charge-exclusive material separately. Pablo supervises; the agent performs reverse engineering, tooling, builds, validation, documentation and Git work.

## Non-negotiable rules

1. Never alter pristine PS2/PS4 sources; derive outputs from copies/pristine inputs.
2. Never commit copyrighted game binaries, extracted assets, official bulk localization data, fonts, textures, ISO/PKG/CVM files or executable fixtures.
3. Automatic import is fail-closed. Ambiguous correspondence remains Japanese and is reported; never guess merely to increase coverage.
4. Preserve `SLPM-66511` and `BISLPM-66511Save` across builds.
5. **Do not launch PCSX2 until the exact expected visible result for that build has been stated to Pablo and Pablo explicitly approves the launch.** Static analysis/builds need no approval.
6. Pablo authorized autonomous implementation/documentation/Git decisions. Do not stop for routine approvals.

## Canonical workspace

- Repo: `/Users/juan.pena/repos/kowloon-recharge-translation`
- Private GitHub: `https://github.com/Kimeru29/kowloon-recharge-translation` (`main`)
- PS2 pristine ISO: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
  - SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`
  - size: `2,095,382,528`
- PS2 ADV: `/private/tmp/khc-ps2-assets/ADV`
- CVM payload ISO: `/private/tmp/kowloon-recharge-inspect/DATA_payload.iso`
- PS4 PKG: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
  - SHA-256: `054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`
  - title ID: `CUSA27034`
- PS4 extracted root: `/private/tmp/khc-ps4-extracted/CUSA27034`
- PS4 ADV: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV`
- PS4 BLBRD bundles: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/BLBRD`
- PCSX2: `/Users/juan.pena/Desktop/Emulators/PCSX2-v2.7.514.app`

Machine-specific generated evidence lives under ignored `local/`.

## Runtime history

### v1 broad candidate — failed

The first broad candidate updated ISO9660 but not the executable's internal ROFS file table. Runtime therefore loaded old Japanese extents. The title patch also wrote single-byte ASCII into a two-byte glyph renderer, producing roughly 4–5 meaningless glyphs.

Proven fixes:

- `SLPM_665.11` ROFS records store size at `filename-14` and sector extent at `filename-6`; generic builds patch and revalidate them atomically with ISO9660.
- title text uses the PS2 two-byte glyph path.

### v2 runtime — useful but failed the clarified startup acceptance scope

The ROFS/title fixes were brought to runtime. Before the first dialogue Pablo observed Japanese startup screens: a Solomon quotation, Japanese name-entry prompts/keyboard/buttons, and a title where the constrained `NewGame` label was visibly clipped. Pablo then clarified that the **first acceptance test must cover everything from the beginning of the game through the first old-man dialogue**.

Do not treat v2 as accepted.

## v5 runtime — renderer-class discovery, failed acceptance

v5 was launched and is **not accepted**. Runtime established these class-level facts:

- all 29 opening quote textures rendered correctly in English;
- `New Game` / `Load Game` rendered correctly;
- B_GP019 name-entry control graphics rendered correctly;
- the Latin name keyboard rendered correctly;
- name/profile prompts and default names were garbage because v5 wrote single-byte ASCII into another two-byte-glyph renderer;
- ADV dialogue English glyphs were present but laid out vertically because the Japanese renderer maps script line/byte-position fields to vertical columns;
- the H.A.N.T. tutorial remained Japanese and is a separate executable pointer-table text class.

These are now modeled as reusable automator classes rather than screenshot-specific fixes.

## Last runtime-tested candidate — startup v6

Candidate:

- path: `/private/tmp/kowloon-recharge-startup-en-v6.iso`
- SHA-256: `beaaa53bbfe3a60cd3af6749d4113cd4d91e81d804b122f80b85c347bded761b`
- 1,143 overlay assets
- 890 in place / 253 relocated
- +900 embedded sectors
- 17 shifted outer files
- 1,143/1,143 executable ROFS records patched/re-resolved
- finished ISO size unchanged at 2,095,382,528 bytes
- final ELF size: 8,401,977 bytes; it still fits the original outer ISO sector allocation
- final post-ROFS ELF SHA-256: `2dacea600e06c4db29311402ae5a1ae0880be23bfab2cfb3e8b0e1a811831922`
- reproducible final-image startup acceptance: **96/96 checks passed** (`local/startup-acceptance-v6.json`)
- Pillow-enabled suite: **121/121 tests pass**
- runtime was executed after explicit approval; it passed through `Enter last name.` but exposed the name-entry defects below.

## v7 runtime result — improved name entry, still failed

- path: `/private/tmp/kowloon-recharge-startup-en-v7.iso`
- SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`
- static acceptance: **98/98**

Runtime proved that folding uppercase into the seven PS2-reachable keyboard rows works. The structural 3+3 name limit remained visible as expected. The next reading-input screen, however, rendered only `Enter` even though the final ELF contained the full relocated `Enter reading for last name.` string, and finishing that state froze again. The pre-title memory-card/status panel and packed title artwork also still contained Japanese.

Static tracing after this run found the freeze/truncation root cause: v6/v7 moved the startup heap instruction and ELF heap metadata to `0x00A02F00`, but libkernel's live `sbrk` heap-break word at file offset `0x650014` still contained `0x00902F00`, the translation PT_LOAD base. Normal allocations could therefore overwrite the relocated prompt/H.A.N.T. payload in RAM.

## Current static candidate — startup v9

- path: `/private/tmp/kowloon-recharge-startup-en-v9.iso`
- SHA-256: `6770862cbde8edf301afdef7778d440c0d2eab99806d732724afc6ef5a279d76`
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`
- final ELF size: 8,403,943 bytes
- 1,144 overlays; 891 in place / 253 relocated
- executable relocated from outer extent 288 to 1,013,782 through the tested builder path
- 1,144/1,144 ROFS records patched/re-resolved
- final-image startup acceptance: **121/121**
- dependency-free suite: **130 tests OK** (8 expected skips)
- Pillow-enabled suite: **130 tests OK** (1 owned-corpus skip)
- runtime status: **not yet tested**; use `docs/LOCALIZATION_STATUS.md` as the authoritative checklist.

v9 retains the v8 heap/memory-card fixes and adds the proven structural GP088_12 title-atlas repack. The two pristine GP088_03→GP088_12 transforms score 0.8758/0.8765 Dice after excluding the flattened banner band. The generated packed atlas uses only official-English `Kowloon High School Chronicle` / `Huanglong High School Chronicle` title regions; the official English remaster omits the old flattened gold `re:charge` banner. Structural 3+3 name storage remains unresolved.

## Startup renderer/storage classes

### Opening quotations

The pre-title quote is not runtime CP932 text. The title module selects a random index modulo 29 and loads:

`BLBRD/INIT_MES/TR%03d.TMX`

There are exactly `TR000.TMX`–`TR028.TMX`; PS2 files are 512×512 standalone 8-bit indexed TMX and 263,232 bytes each. Official PS4 English equivalents are 1152×1152 Texture2D objects in bundle `BLBRD/tr_en`.

All 29 official English images are now downscaled/quantized/repacked into same-size PS2 TMX outputs under ignored `local/startup-graphics/BLBRD/INIT_MES/`.

Evidence (`local/startup-quotes-report.json`):

- 29/29 generated;
- every file retains pristine byte size;
- maximum mean absolute RGBA error versus the downscaled official image: **0.5594 / 255**;
- every final candidate quote file hashes to its overlay and has a valid final ROFS record.

### Title

The exact official labels are now `New Game` and `Load Game`, not the clipped `NewGame` workaround. A verified 40-byte source arena at `0x5CBDE8..0x5CBE10` holds both two-byte strings; `Load Game` is moved to `0x5CBDFC` and its pointer at `0x5CBE54` is updated. The third title pointer/blank string remains untouched.

### Name/profile flow

The v5 runtime proved that these prompts/names are also a two-byte-glyph renderer. v6 therefore packed official English as wide CP932 into verified module-local arenas and repointed the existing prompt/name tables rather than writing ASCII into the original slots. The class covers `Enter last name.`, `Enter first name.`, confirmation/license messages, `Heracleion Shrine`, and protagonist/default names (`Habaki`, `Kuro`, `Hiyuu`, `Tatsuma`).

v6 incorrectly blanked the two reading prompts while leaving their input states active. Runtime therefore entered an unlabeled input screen. The official remaster dictionary explicitly contains `Enter reading for last name.` and `Enter reading for first name.`. v7 relocates those two prompts into the shared translation PT_LOAD. Default/runtime kana-reading display strings remain blank where the remaster data does not provide an English reading value.

The keyboard data has 14 rows, but static MIPS tracing proves this PS2 input flow only indexes row pointers 0..6; R1/L1 changes the name-field cursor and does not switch to rows 7..13. v6 therefore exposed only lowercase Latin characters at runtime. v7 folds both lower- and uppercase Latin letters, digits, and punctuation into the seven reachable rows while preserving the two-byte 20-cell row geometry.

The visible 3+3 name limit is also structural, not a string-capacity bug. The name-input routine has two permanent 6-byte buffers (three two-byte glyphs each), a six-position field cursor split at position 3, and delete/copy/layout branches keyed to that split. The reading buffers are separately 12 bytes each. v7 deliberately does not patch these constants until a direct-Latin/buffer-safe design is proven.

### Name-entry button graphics

The visible Japanese control captions are baked into `BLBRD/B_GP019.BIN`, especially `GRP019/GP019_01.TMX`. The official PS4 English bundle is `BLBRD/b_gp019_en`. Both relevant official PNGs are ported into a same-size PS2 container:

- local output: `local/startup-graphics/BLBRD/B_GP019.BIN`
- output size: 264,640 (unchanged)
- output SHA-256: `529aa604ba3d1e987d062daceb3e8045566d47e43b81665f8d7fa9b831b01227`

### ADV dialogue layout

`DG/DG00_00.MTX` remains the opening dialogue proof. v5 showed that the localized two-byte English itself was present, but the Japanese ADV renderer displayed it vertically. Static code/data tracing proved the script compiler stores line index in record field `+0x463` and byte position in `+0x465`, while the renderer used `+0x463` as X and `+0x465/2` as Y. v6 performs a fail-closed four-instruction renderer transform so X uses `+0x465/2` and Y uses `+0x463`. This is a renderer-class patch and therefore applies to ADV dialogue generally, not only DG00.

### Executable long-text / H.A.N.T class

The H.A.N.T. tutorial is an executable pointer table at `0x5C8C70`; its visible strings do not safely fit their Japanese slots. The pristine ELF has a zero-sized second PT_LOAD at virtual address `0x00902F00`. The localization activates it as a reusable translation segment with a 1 MiB reserved VA window and moves the heap start to `0x00A02F00`. v7 runtime proved that moving only the startup heap instruction/ELF metadata was insufficient: libkernel's live `sbrk` break at file `0x650014` still pointed at the segment and corrupted it. v8 patches all three heap ownership sites. The shared segment now carries H.A.N.T., the two overflow name-reading prompts, and the proven memory-card English pointer-table subset.

## Current corpus/import coverage

MTX:

- PS2: 1,516
- PS4 counterparts: 1,067
- PS2-only: 449
- byte-identical common: 1,022
- exact + English-mapped: 985 / 78,314 official entries
- proven exact import: **962 files / 56,642 entries**
- rejected exact: 23 files / 21,672 entries
- changed + English-mapped: 43 / 22,084 entries
- proven changed/template import: **7 files / 2,284 entries**

Seven structural/template outputs: `DG13_02`, `FD00_31`, `FN13_16`, `ID00_21`, `ID00_26`, `ID00_41`, `MS05_03`.

KSF:

- exact common: **1,010** (do not revive old exploratory 1,019)
- exact + English-mapped: 144 files
- fitting official entries: 868
- overflow: 48
- ambiguous: 4

PS2-only lexical proxy:

- 41,337 unique Japanese lexical runs overall
- 568 occur in PS2-only MTX
- only **419 runs / 3,672 Japanese characters** are novel relative to mapped common content
- this is an estimator, not a dialogue-line percentage.

## Known unsolved areas

- 23 exact MTX maps use indirect/dynamic localization semantics and remain rejected.
- 25/26 consolidated FD00 template files fail the generic structural proof; only FD00_31 passes. A dedicated semantic/template interpreter is required.
- KSF overflow relocation is unproven; 48 official strings remain untouched unless a reviewed constrained override exists.
- Broad graphics backport beyond the startup slice is not done. The PS4 assets are located; PS2 TMX encoding/repacking is now proven for normal indexed startup cases, but special-layout assets need per-format proof.
- Cross-build memory-card save compatibility still needs a real runtime create/load test. Savestates are not compatibility targets.

## Current implementation map

- `tools/mtx.py` — MTX script compiler plus named/standalone indexed TMX helpers
- `tools/localization.py` — DC grouping + safe two-byte CP932 English encoder
- `tools/exact_import.py`, `tools/import_exact_mtx.py` — fail-closed exact MTX importer
- `tools/ksf_import.py`, `tools/import_exact_ksf.py` — conservative KSF importer
- `tools/structural_import.py`, `tools/import_structural_mtx.py` — changed-source MTX importer
- `tools/startup_ui.py` — title arena, wide startup prompt/name relocation and Latin keyboard
- `tools/adv_layout.py` — fail-closed ADV vertical→horizontal renderer transform
- `tools/elf_translation_segment.py` — reusable second-PT_LOAD English text segment
- `tools/hant_ui.py` — shared startup translation-segment payload: H.A.N.T., overflow name-reading prompts, and proven memory-card text
- `tools/memory_card_ui.py` — fail-closed memory-card pointer-table correspondence + official English encoding
- `tools/startup_acceptance.py` — reproducible final-ISO startup/renderer-class verifier
- `tools/early_ui.py`, `tools/elf_strings.py` — executable UI build/slot handling
- `tools/graphics_port.py` — optional-Pillow indexed PS2 graphics port, including raw-RGBA atlas output
- `tools/graphics_layout.py` — generic fail-closed region-transfer / alpha-layout proof for structurally changed atlases
- `tools/startup_graphics.py` — quote, B_GP019, direct GP088, and structural GP088_12 startup graphics transforms
- `tools/translation_overlay.py` — overlay path policy/precedence and relocation planning; supports ADV scripts plus explicit startup BLBRD assets
- `tools/elf_rofs.py` — executable ROFS lookup/patching
- `tools/build_translation_iso.py` — nested CVM/ISO builder + final-image/ROFS verification
- `tools/regression.py`, `tools/check_regression.py` — cumulative accepted-artifact/identity gate
- `tools/graphics_inventory.py` — PS4 localized bundle inventory

## Latest runtime result and next gate

v7 was runtime-tested after explicit approval. It proved uppercase reachability and kept the accepted startup/name-entry surfaces, but the relocated reading prompt was truncated to `Enter` and finishing the state froze. Static reverse engineering identified the stale libkernel heap-break collision described above.

v9 is statically verified with the allocator fix, proven memory-card UI, direct GP088_03 backport, and structural GP088_12 English atlas. Before launching v9, state the exact checklist in `docs/LOCALIZATION_STATUS.md` and wait for Pablo's explicit approval. Do not claim the freeze fixed until runtime advances beyond the reading/confirmation flow.

## Resume procedure

1. `cd /Users/juan.pena/repos/kowloon-recharge-translation`
2. Read this file, `docs/BUILD.md`, `docs/DISCOVERY.md`, and `docs/REGRESSION.md`.
3. Run both test suites; graphics tests require optional Pillow.
4. Check `git status --short --branch` and recent commits.
5. Regenerate ignored `local/` evidence if implementation changed; never trust stale generated files.
6. Always build from the pristine PS2 ISO.
7. Never launch PCSX2 without the exact-visual-scope approval gate.
