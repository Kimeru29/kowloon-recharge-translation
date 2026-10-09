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

## Historical runtime-tested candidate — startup v6

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

## Historical static candidate — startup v9

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

`DG/DG00_00.MTX` remains the opening dialogue proof. v5 showed that the localized two-byte English itself was present, but the Japanese ADV renderer displayed it vertically. v11 ownership tracing proves file `0x14FA60` / VA `0x24F9E0` is the live coordinate constructor while `0x14EDA0` / VA `0x24ED20` is only the reveal-progress gate. The v6-v10 transform targeted the right constructor but normalized the byte position after it had already been copied into the FPU. v11 leaves both source fields and the progress callback pristine and swaps only the completed coordinate output registers immediately before the coordinate helper, so X receives `+0x465/2` and Y receives `+0x463`. The supervised v11 runtime still rendered vertically; r4 traces the single wrapper orientation owner at file `0x14E96C` / VA `0x24E8EC`, which feeds all four DG font canvases, and changes only `a2=1` to `a2=0` there so every canvas inherits horizontal advance.

### Executable long-text / H.A.N.T class

The H.A.N.T. tutorial is an executable pointer table at `0x5C8C70`; its visible strings do not safely fit their Japanese slots. The pristine ELF has a zero-sized second PT_LOAD at virtual address `0x00902F00`. The localization activates it as a reusable translation segment with a 1 MiB reserved VA window and moves all proven heap owners to `0x00A02F00`. Runtime v11 established about 336 safe horizontal pixels for the tutorial. r4 changes only the mode-4 tutorial row constructor from the existing 16px style 0 to existing 12px style 1, and r5 tightens the page-local row stride to 18px; Pablo's r5 runtime test confirms that tutorial presentation is good and must be preserved. The independently proven seven-entry H.A.N.T. chrome owner table at `0x586D20` is relocated to semantic English labels. r6 adds separately proven deeper-page owners: three Help category labels at `0x587288`, three sibling Help topic tables at `0x587430`, `0x587690`, `0x587840` totaling 55 labels, and the nine-entry Config table at `0x586EF0`. r13 adds only runtime-observed content owners: three selected Help bodies, empty-Mail text, Config enum values + 20 ringtones, three Enemy category aliases, 10 Dictionary index tabs and 208 real Dictionary term-list aliases. r14 keeps those owners and additionally relocates Help icon metadata into the 12px/16px English geometry, fixes the proven Config/Dictionary-list/Enemy renderer style/spacing, retargets the Mail count label, and promotes the two runtime-observed Dictionary definition leaves (`King Akhenaten`, `Heracleion`). r14 runtime later disproved its extra `0x190A40` style mutation: that instruction is a singleton constructor in the same mode-4 H.A.N.T. Functions path, not a proven Dictionary-definition font owner. r15 restores and permanently pins it pristine while keeping the proven row font owner at `0x190968`. r16 recovers the owned remaster `English.bytes` from CUSA27034 and proves exact official matches for all 2,073 nonblank Japanese rows across all 208 selectable Dictionary definition pages; those pages are generated fail-closed and reflowed to a conservative 21-cell body width without touching `0x190A40`. The Help-body wording remains semantic where no exact official row mapping has been established. The shared allocator additionally owns the two overflow name-reading prompts, the proven memory-card subset, and the proven long command labels `Return above ground` and `Report card`.

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
- `tools/startup_ui.py` — title arena, wide startup prompt/name relocation, Latin keyboard, fail-closed English name-flow bypass, and centered state-owned name/confirmation/license prompt geometry
- `tools/adv_layout.py` — fail-closed ADV vertical→horizontal renderer transform
- `tools/elf_translation_segment.py` — reusable second-PT_LOAD English text segment
- `tools/executable_text.py` — deterministic shared executable-text allocator with unique key/pointer ownership
- `tools/hant_layout.py`, `tools/hant_ui.py` — page-local 12px/28-cell H.A.N.T. tutorial with r7 16px row stride, relocated controller metadata, seven semantic chrome labels, all 55 Help topic labels, four promoted selected Help bodies, Config content values/ringtones, Enemy category tabs, empty-Mail state, Dictionary tabs/terms, and the shared relocation payload
- `tools/hant_content_data.py` — compact semantic content manifest for 20 ringtone titles, 10 Dictionary index tabs and 208 real Dictionary term-list aliases, pinned by pristine offsets/hashes without embedding Japanese source text
- `tools/hant_dictionary_definitions.py`, `tools/generate_hant_dictionary_definitions.py`, `tools/hant_dictionary_definitions_data.py` — fail-closed mode-1 Dictionary definition inventory/generator plus generated official English corpus for all 208 selectable pages; each pristine page is fingerprinted and official rows are deterministically reflowed to 21 cells
- `tools/hant_inventory.py` — bounded ownership inventory for the 55 `(mode=4, category, topic)` selected Help-body leaves and their independent metadata leaves
- `tools/menu_ui.py` — semantic command-label manifest, fixed labels, proven long-label relocation, unresolved preservation
- `tools/memory_card_ui.py` — fail-closed memory-card pointer-table + boot-handler alias correspondence and official English encoding
- `tools/startup_acceptance.py` — reproducible final-ISO startup/renderer-class verifier, including v11 title/ADV/H.A.N.T./menu invariants
- `tools/early_ui.py`, `tools/elf_strings.py` — executable UI build/slot handling
- `tools/graphics_port.py` — optional-Pillow indexed PS2 graphics port, including raw-RGBA atlas output
- `tools/hant_graphics.py` — deterministic, fail-closed semantic caption repaint for the baked `GP020_03` H.A.N.T. atlas
- `tools/graphics_layout.py` — generic fail-closed region-transfer / alpha-layout proof for structurally changed atlases
- `tools/startup_graphics.py` — quote, B_GP019, direct GP088, and structural GP088_12 startup graphics transforms
- `tools/translation_overlay.py` — overlay path policy/precedence and relocation planning; supports ADV scripts plus explicit startup BLBRD assets
- `tools/elf_rofs.py` — executable ROFS lookup/patching
- `tools/build_translation_iso.py` — nested CVM/ISO builder + final-image/ROFS verification
- `tools/regression.py`, `tools/check_regression.py` — cumulative accepted-artifact/identity gate
- `tools/graphics_inventory.py` — PS4 localized bundle inventory

## Latest runtime result and next gate

The latest manual runtime pass is **v11-r20**. Pablo confirms that r20 fixed the red-selector/text alignment itself and preserved the previously accepted presentation. The remaining defects are selector **size/packing**, not text ownership: Dictionary's red box spans two adjacent A/K/S/T/N/H/M/Y/R/W cells and can visually swallow the neighboring `R` tab; Enemy's red box is shorter than `Small`/`Large`/`Human`, and the category cluster still runs far enough right for `Human` to collide with the now-visible R1. Everything else in the r20 review is accepted and frozen.

r21 follows the selectors through group 20's executable resource table instead of adding another position-only workaround. Dictionary selector index `0x21` resolves uniquely to metadata file `0x364BB0`, whose intrinsic width is 24px; r21 changes only that width to 14px and keeps the r20 `300 + 12*i` selector path, tab text, UV rectangle and Dictionary detail owners unchanged. Enemy selector index `0x41` resolves uniquely to metadata file `0x3657B0`, whose intrinsic width is 40px; r21 stretches the same UV rectangle to 64px. Enemy keeps the accepted style-1 12px font, packs visible text starts to `220/282/344`, tracks them with selector `216 + 62*i`, and leaves R1 at the runtime-good pristine x=407. No font-size change is needed.

The current static/deterministic candidate is **v11-r21** at `/private/tmp/kowloon-recharge-startup-en-v11-r21.iso`, SHA-256 `08a9781ecfec5096f3d50769fabb686d7d8fa2cc82dcdca003e687dd05f9aaa7`. Its pre-ROFS translated ELF SHA-256 is `457e2c149493f01a7ffcea7cc896af9b4296a8e587f17cb3e67edbb1ad1bb3cd`; final post-ROFS ELF SHA-256 is `b2a70936d57c6750f1f54ad19d1f398a11e6c0f2444bf3edb30cfd6e99c81616`; final ELF size is 8,562,114 bytes; final-image acceptance is **150/150**; both complete suites execute **222 tests** (10 dependency-free skips / 1 Pillow-owned-corpus skip); and `/private/tmp/kowloon-recharge-startup-en-v11-r21-repeat.iso` is byte-for-byte identical.

Do not launch PCSX2 automatically. The r21 visual gate is only: cycle Dictionary A/K/S/T/N/H/M/Y/R/W and verify the red rectangle contains exactly one active letter and `R` stays visible; cycle Enemy Small/Large/Human and verify the red rectangle contains the whole word, `Human` clears R1, and R1 remains fully visible. Everything else is preservation-only.

## Resume procedure

1. `cd /Users/juan.pena/repos/kowloon-recharge-translation`
2. Read this file, `docs/BUILD.md`, `docs/DISCOVERY.md`, and `docs/REGRESSION.md`.
3. Run both test suites; graphics tests require optional Pillow.
4. Check `git status --short --branch` and recent commits.
5. Regenerate ignored `local/` evidence if implementation changed; never trust stale generated files.
6. Always build from the pristine PS2 ISO.
7. Never launch PCSX2 without the exact-visual-scope approval gate.


### v11-r22 final selector-padding polish

r21 runtime is accepted as functionally correct for Dictionary/Enemy selection tracking. r22 is a bounded visual polish only: Dictionary selector width changes 14→16px while keeping `x=300+12*i`, giving each 12px tab glyph 2px padding on both sides; Enemy keeps the accepted 64px selector and 60px labels, but shifts only the selector base 216→218 so `Small/Large/Human` also receive 2px symmetric padding without moving text or R1. All other r21 owners are frozen.

These fixes are shared by menu family, not per item. Dictionary's selector resource/index path is shared by all ten top categories, and the mode-1 Dictionary detail renderer/208 generated definitions remain common to terms that unlock later. Enemy's top selector resource is shared by Small/Large/Human, so later content inside those categories inherits the corrected header. Other H.A.N.T menu/help families may have independent body/selector owners; unlocking a new leaf does not automatically translate a separate unpromoted body table.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r22.iso`, SHA-256 `1b3a9c916ec8436af94f702138efbdde3028158c4af256ba517293a2f3f2f009`; pre-ROFS ELF `60122115b3109f0acfc0c4f895a6fa79eb18fda7a3ff7d645310c050a7cab75d`; post-ROFS ELF `f1f6c68345e806296702fdd2f290b7cfbfb602dbe00992cd62819fe2954ec8ea`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **223** tests in both suites (10 dependency-free skips / 1 Pillow skip); deterministic repeat is byte-for-byte identical. Runtime proof remains Pablo's gate.


### v11-r23 final H.A.N.T. header-clearance candidate

Pablo runtime-tested r22 and reported only two remaining H.A.N.T. issues: Dictionary's right-side R1 control is still clipped, and Enemy's red selector still covers part of the L1 arrow. r23 preserves all accepted r22 selector/text geometry and changes only Dictionary R1 x=428→424 plus Enemy L1 x=194→190. No Dictionary tab, selector, detail-page, Enemy category, Enemy selector, or R1 geometry changes.

H.A.N.T. regression protection was also tightened: final-image acceptance is now explicitly tamper-tested against every owner in `HANT_RUNTIME_LAYOUT_PATCHES`, while existing fail-closed checks continue to protect `0x588C84 = 12`, pristine `0x190A40`, selector UVs, translated content owners, and previously accepted Help/Mail/Config surfaces.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r23.iso`, SHA-256 `4465f4322fc252d1fa0cf734fc4c63697c38adbda155a90eadcaca37698a55c5`; pre-ROFS ELF `564c4268faf7f7224bc5a4dc1d67c758a2af003f2c5487a4056af8d537a2041f`; post-ROFS ELF `4b59521acbfc96b68a6a934a7eb2442b8e426288714065f96f1980aeff3516f8`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **224** tests in both suites (10 dependency-free skips / 1 Pillow skip); deterministic repeat is byte-for-byte identical. Runtime proof of these two final header nudges remains Pablo's gate. Do not launch PCSX2 automatically.


### v11-r24 Dictionary R1 final-clearance candidate

Pablo runtime-tested r23. Enemy is now accepted as perfect for the current story point and must stay frozen: L1 x=190, labels 220/282/344, selector x=218+62*i with width 64, R1 x=407, y=93/style 1. r24 adds an explicit regression test for this full reviewed Enemy geometry.

Dictionary is also accepted except for a smaller remaining right-edge R1 clip. Since r23's 428→424 move reduced the clip with no regression, r24 repeats the same bounded correction once, changing only Dictionary R1 x=424→420. Tabs, 16px selector, detail-page geometry, `0x588C84 = 12`, pristine `0x190A40`, and all other accepted H.A.N.T. owners remain frozen.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r24.iso`, SHA-256 `46112aaaefb80a317dec4bed36e526d3e9f05f780dd435b4ecb0516c85e304d0`; pre/post-ROFS ELF `2242f5472f9ab228c51da4f776eb011e47b2facbfec02baf64159f3be71be58f` / `930770fdad8ac71d1291e250400e467c0258cc57a1176f1bc330aa09e8de88e5`; final-image acceptance **150/150**; both suites **225 tests**; repeat ISO byte-identical. The only runtime gate for this round is Dictionary R1 visibility. Do not launch PCSX2 automatically.


### v11-r25 Dictionary/Help final-layout candidate

Pablo runtime-tested r24. Enemy is accepted as perfect at the current story point and remains frozen exactly at L1 x=190, labels 220/282/344, selector x=218+62*i/64px, R1 x=407, y=93/style 1. r25 adds no Enemy mutations and re-pins the complete reviewed header in regression coverage.

Dictionary still shows a slight right-edge R1 clip. r25 moves the complete accepted cluster four pixels left rather than continuing with R1-only nudges: L1 x=270, tabs x=298+12*i, selector x=296+12*i with width 16, and R1 x=416. The selected-detail path, generated definitions, `0x588C84 = 12` and pristine `0x190A40` remain unchanged.

Help now has bounded presentation ownership too. Topic/category label constructors use style 1 (12px). The `ADV / Ruins / Other` category row shifts eight pixels left while retaining its 72px selector; the topic-row selector is unique group-20 index `0x22` and widens 168→268px with unchanged UVs, enough for the longest 22-cell translated topic plus 2px padding per side. This change applies to the shared Help topic family, including later-unlocked rows that use the same owner; it does not change selected Help body text.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r25.iso`, SHA-256 `8cd3e369c08f8c29609c54236e73bfb06bf62b1c9aaaa9b0529fd08a17aec6c4`; pre/post-ROFS ELF `4100ea75fd1d82819521279fbf8edfc8038f6ec0dc852e68309896db6f47ed1b` / `d0dfaa4390d6aaba4162b6a5115dfc4fb0b9e40d533737911d4c29557c6c86d5`; final-image acceptance **150/150**; **226** dependency-free tests (10 skips); **226** Pillow-enabled tests (1 skip); repeat ISO byte-identical. Runtime visual gates are Dictionary R1 and Help selector/text encapsulation only. Do not launch PCSX2 automatically.


### v11-r26 final Dictionary/Help shoulder-clearance candidate

Pablo runtime-tested r25. Dictionary is nearly perfect but still needs the complete header slightly farther left, so r26 repeats the proven rigid shift once: L1 x=266, tabs x=294+12*i, selector x=292+12*i at 16px, R1 x=412. Detail geometry, generated definitions, `0x588C84 = 12` and pristine `0x190A40` remain frozen.

Help's remaining issue is specifically the category red frame at the two shoulders. r25's 72px selector at x=192 keeps `Other` clear of R1 but reaches into L1 at `ADV`. r26 restores selector base x=200 and shrinks the shared resource to 64px, preserving right edge x=402. Labels are x=202/271/340, giving the long `Ruins`/`Other` labels 2px padding on both sides and keeping `ADV` clear of L1. The 268px topic selector and all 55 topic labels/bodies remain unchanged. Enemy stays fully frozen.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r26.iso`, SHA-256 `189434d74b98fe2b1cacb4e1a2edfad9ac6943e12b6e8b655c4a4c4884fd57b0`; pre/post-ROFS ELF `fc001382a330a43313098adf3f70dfeec4fc1d77f2e93284de2d72cd39dcf940` / `572ff87377d3c2692309da36689b38c107988eaf8442fb510f9b034d3678b7c2`; final-image acceptance **150/150**; both suites **227 tests**; repeat ISO byte-identical. Runtime gate: visually confirm Dictionary R1 clearance plus Help `ADV`/`Ruins`/`Other` selector shoulders. Do not launch PCSX2 automatically.


### v11-r27 final Help category-owner correction

Pablo's r26 runtime review accepts Enemy and Dictionary as perfect and identifies one remaining Help defect: r26 moved `Ruins` when the intended target was `ADV`. Runtime therefore corrects the owner map: `0x18C768` is `Ruins` and is restored; `0x18C778` is `ADV` and gets the -8px nudge. Help selector x=200/64px, `Other`, the 268px topic selector and all body/content owners remain frozen. Dedicated r27 tests pin the accepted Enemy and Dictionary geometry against future regressions.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r27.iso`, SHA-256 `5210dde53302c6340cc27550f0f170a31ca317907759dbc29a92839c4781fb9e`; pre/post-ROFS ELF `9a925cb3c5b930ecaea0669f85399c1ef1c3514edf8e18e656e21df81773a1ff` / `a31135de31bba5baa367925b743d48ddb6ab8a9a2d169da176440a4b3777fc27`; final-image acceptance **150/150**; both suites **228 tests**; repeat ISO byte-identical. Do not launch PCSX2 automatically.


### v11-r28 Help selector-box sizing

Pablo runtime-accepts `ADV`, `Ruins`, and `Other` text alignment and explicitly freezes those labels. r28 therefore does not move any text. It replaces only the selected category box geometry: ADV is 48px centered at x=204, Ruins is 72px centered at x=257, and Other remains 64px at x=338. The implementation uses the existing selector sprite's X/X-scale fields and bounded inter-function padding; all new callsite/helper/table words are fail-closed through the normal H.A.N.T. runtime-layout gate. Enemy and Dictionary stay frozen.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r28.iso`, SHA-256 `e7517dfafd98766733324d3b8f62dcccf29b69928e8242cf469114830e197a83`; pre/post-ROFS ELF `25bad09a73def9900addcb96bdfea01a564d3147b0544d425ac7edef11901eef` / `44ab4e4a20e11ce2162fe1e262dfa1d59e6106ab2fa89dedfa3aeafe856a2547`; final-image acceptance **150/150**; both suites **229 tests**; repeat ISO byte-identical. Runtime gate is now limited to visually confirming the ADV/Ruins red-box widths/centering. Do not launch PCSX2 automatically.


### v11-r29 dungeon HUD / SELECT text candidate

Pablo's post-r28 review closes the current H.A.N.T. polish cycle and freezes all accepted H.A.N.T. geometry. r29 changes only executable-text ownership outside that frozen scope: all 18 proven SELECT command labels now use PS2 two-byte English instead of ASCII-in-Japanese-slot text; the exploration action palette redirects its three direct-code labels to `Examine` / `Items` / `Jump`; and 446 exact item-name table owners are redirected to official-remaster English for the battle/L1 HUD path. All Japanese source strings remain pristine provenance, and unresolved `メディア` remains untouched.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r29.iso`, SHA-256 `1692b234b810bf966b94d0d3959abab07ad0c611bca469a5e022727eaac3de0e`; pre/post-ROFS ELF `8caddb81607bd1afe7d30344d2b4bc0e87e979e7df9bd8714bd2e18d27f41062` / `923bc218585f0b9d1ee1edb12ea73d5c04ca6447c653b6aff3b2b43fd30e754f`; final ELF size 8,573,437 bytes; final-image acceptance **151/151**; dependency-free suite **234 tests** (10 expected skips); Pillow-enabled suite **234 tests** (1 owned-corpus skip); `/private/tmp/kowloon-recharge-startup-en-v11-r29-repeat.iso` is byte-for-byte identical. Runtime gate is limited to the SELECT labels, both dungeon action-menu sections, and L1/battle item text. Do not launch PCSX2 automatically.

### v11-r30 companion HUD candidate

Pablo runtime-accepts r29's dungeon action HUD and SELECT/start menu as complete, so r30 freezes those owners and adds only companion HUD text. The transient `h_buddy.c` comment table contributes 1,650 unique Japanese lines through 1,784 live aliases; every live source has one unique exact CUSA27034 `English.bytes` match. Seven official `@D` deletion rows become empty second lines. The separate 31-entry companion-action table reuses 26 exact PS4 labels (including `Throw a Rock` for the observed `石を投げる`), leaves the id-0 placeholder pristine, and explicitly tags four Re:charge-only semantic labels.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r30.iso`, SHA-256 `7bed876be95e19fd7c2fe1ade882eaf9fb0518db1165510861fa69d89db63c5f`; pre/post-ROFS ELF `3da35c9939524c8e89c5df5b618c9556e721ec86051d9010dba9df0e303378ec` / `a85d899f3fd6d6ca8ce88a4c8f3b71eb02aa960577367c456ab4fbb865049d17`; final ELF size 8,642,989 bytes; final-image acceptance **153/153**; both suites execute **239 tests** (10 dependency-free skips / 1 Pillow skip); `/private/tmp/kowloon-recharge-startup-en-v11-r30-repeat.iso` is byte-for-byte identical. Runtime gate is the companion action caption plus transient companion comments only. Do not launch PCSX2 automatically.


### v11-r31 companion HUD presentation

Pablo runtime-tested r30 and accepted the companion translation itself; the remaining defect was presentation: the persistent companion action strip was too large/low and hid part of the action HUD. r31 freezes all r30 text owners and the 160x32 backing resource, switches this caption to the existing 12px style 1, places the observed `Throw a Rock` text with 8px padding on both sides, and moves the entire strip/text pair 32px upward. New fail-closed checks cover every geometry/style owner plus the backing dimensions.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r31.iso`, SHA-256 `85bbe609fbe6ee875015a3c02ba685ca0d21f40d4b65ab164e2f0d82ba850833`; pre/post-ROFS ELF `249f074d753dcedb438725847ebadd6985145fdf3dbe0d8869394982c5fe7d4e` / `ef66c365be8c7c4ed28c7b2e98893572e6fe9566e785af5b5b83e39b6fe731d1`; final-image acceptance **154/154**; both suites execute **242 tests**; repeat ISO byte-identical. Runtime gate is limited to visually confirming the companion action caption no longer overlaps the action palette. Do not launch PCSX2 automatically.


### v11-r32 companion HUD bubble alignment

Pablo runtime-accepted r31's translated companion caption, 12px font, and vertical clearance, but the fixed bubble's visible backing sat slightly to the right of the first glyph. r32 changes only the backing X owner at file `0x666F0` from `+12.0` to `+4.0`, shifting the existing 160x32 bubble/spike 8px left. Text X/Y, font style, backing Y, companion translations, action palette, H.A.N.T., Enemy and Dictionary owners remain frozen and fail-closed.

Translation policy remains PS4/remaster-first: exact owned PS4 strings must be reused before any authored translation. `Throw a Rock` is confirmed `official_exact` from CUSA27034 `English.bytes` (remaster offset 284809). Only Re:charge-exclusive text without an owned PS4 equivalent may receive context-aware authored English.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r32.iso`, SHA-256 `acbc138a1c89ab0d81979e2d531dd5706c369df2cf49ef070311014ed833cb56`; final-image acceptance **154/154**; both complete suites execute **242 tests**; repeat ISO byte-identical. Do not launch PCSX2 automatically.


### v11-r33 companion HUD horizontal down-tail bubble

Pablo's r32 runtime screenshot proved the remaining problem was not translation or text size: the old group-2 `0x18` backing is a side-tail strip, so it can never visually match the PS4 horizontal speech balloon. r33 reuses an existing pristine PS2 asset instead of drawing or approximating one: group-2 `0xC5` is a 288x80 horizontal bubble with a downward tail. Its sprite record declares pivot `(67,77)`, and direct alpha inspection shows the bottom tail-tip pixels at y=77 / x=64..68, confirming that the pivot is the tail tip. The resource switch is at executable owner `0x66728`; the accepted r32 tail-tip anchor stays `X=+4, Y=-61`. Caption X/Y become `-47/-131`, which places the existing 12px text at local inset `(16,7)` inside the larger bubble. The old 160x32 side-tail asset remains pristine and unused by this caption.

Translation policy remains unchanged: exact owned PS4/remaster text always wins. `Throw a Rock` remains `official_exact`; r33 changes presentation only. Regression coverage freezes the resource index, tail-tip anchor, caption placement/style, 0xC5 dimensions/pivot, and final-image acceptance semantics.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r33.iso`, SHA-256 `c9e31bccfe87c8fe9356107be9e572c6764dd9ed303268bf04f70058f1f13d19`; pre/post-ROFS ELF `75c1bba7ef9331cc60919715e620acba4605ea44d88969cabf96ee7d9b8e1a6a` / `0345ed3f1ffece03384db78347b3369f62cfb0d817ce92e3e74bdeeb779fca5e`; final-image acceptance **154/154**; both complete suites execute **242 tests**; repeat ISO byte-identical. Do not launch PCSX2 automatically.


### v11-r34 companion HUD bubble resource correction

Pablo's r33 runtime screenshot showed the caption text but no backing. The root cause is now proven: the r33 geometry was read from metadata file `0x350B40` / VA `0x450AC0`, but that metadata is owned by group-2 index `0x68`, not `0xC5`. Group-2's resource table starts at file `0x380AF0`; record `0x380E30` (index `0x68`) is exactly `(0x00450AC0, 1)`. By contrast, index `0xC5` resolves to unrelated metadata file `0x353CF0` (32x248, pivot -56/-22), which explains why the expected speech bubble disappeared. r34 corrects only the immediate at file `0x66728` to group-2 index `0x68`; the r33 tail-tip anchor, 12px text geometry, translations, and all other accepted HUD owners stay frozen. Static and final-image acceptance now validate both the selected immediate and the group-2 resource-table record.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r34.iso`, SHA-256 `ba4cc8e6949aa2331c9f043256b0418d6383c454f72762e1a87255662c61155a`; pre/post-ROFS ELF `6e5091fba3c2940fd76ced4757d46c9d038509703460bd0aaacfdbf80c6cc232` / `06427d9d35390eca95d3a749b01023975cd1d141e7f8515dde971aebf514fe8b`; final-image acceptance **154/154**; both complete suites execute **242 tests**; repeat ISO byte-identical. Translation policy remains PS4/remaster-first and `Throw a Rock` remains the exact official string. Do not launch PCSX2 automatically.


### v11-r35 compact companion action bubble

Pablo runtime-accepted r34's visible horizontal/down-tail bubble but found it too tall and too wide. r35 preserves the proven group-2 `0x68` resource, official PS4/remaster text, style-1 12px font, and tail-tip anchor. It scales only the live bubble metadata from pristine **288x80 / pivot 67,77** to **224x48 / pivot 52,45** and repositions the caption from anchor -47/-131 to **-36/-99**, retaining 12px left and 7px top padding. The 224px target is slightly narrower than the ~230px runtime-measured combined span of the three lower HUD boxes, so the bubble gains deliberate separation from the right action palette. The current persistent action-label table contains no line breaks, so 48px is explicitly the one-line geometry; transient companion comments remain a separate untouched renderer.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r35.iso`, SHA-256 `2acae913416507008e0b6ec7e881b98c04f257f6ceef01f51534b8c74eb7bf04`; pre/post-ROFS ELF `129bf17c53fa92ae7c072db1ff7c92e8a2b415d721595d05676efe36a4e72199` / `3ce090549ae6113210fd246ffadde1a80ff0d7dffddf9ca243818ee5e6cda063`; final-image acceptance **154/154**; both complete suites execute **242 tests**; repeat ISO byte-identical. Metadata preimages, target geometry, executable placement owners, and the r34 resource-table mapping are all fail-closed. Translation policy remains PS4/remaster-first. Do not launch PCSX2 automatically.


### v11-r36 generic companion action layout

The companion action bubble is now generic across the entire current 31-id action table rather than tuned to `Throw a Rock`. A single wrapping/layout policy is generated from each action's final English string: 17 cells per row, fixed safe width 224px, base height 48px, +16px for each additional row, down-tail pivot adjusted with height, and text-Y derived from the same geometry. Current official strings produce 1-3 rows; the implementation fails closed above four rows instead of silently clipping. Examples: `Throw a Rock` = 1 row / 48px; `Smoking an Aroma Stick` = 2 rows / 64px; `Secret Technique: Reverse Waterfall Blade` = 3 rows / 80px. There are no per-label geometry overrides.

Runtime selection is also generic: a 96-byte MIPS hook in the translation PT_LOAD reads the live action id at HUD-object +0x2D0, bounds-checks the 31-entry table, writes the generated height/pivot-Y and text-Y state, selects proven group-2 bubble `0x68`, and returns to the original renderer. The accepted r35 one-line appearance remains the startup/default state. The full composite build's translation PT_LOAD is executable (RWX flags 7) for this hook; lower-level/default translation installs remain RW flags 6. PS4/remaster-first translation policy is unchanged; `Throw a Rock` and other official matches remain official strings, with authored English only for proven Re:charge-exclusive labels.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r36.iso`, SHA-256 `4f61745be89ada402af35368169e2e6a5097367713f847a54fd1df78e963b9e9`; pre/post-ROFS ELF `f67c67eec2d3bd5e64811ad30375af8722579fa31d54832d727aefbd8309d4c8` / `2fbf9d214437c588aad08f88f799587f2e06c4511942d4c483449d696710abf5`; final-image acceptance **154/154**; both complete suites execute **243 tests**; repeat ISO byte-identical. Do not launch PCSX2 automatically.


### v11-r37 companion slot/action-id correction

Pablo runtime-accepted r36's one-line `Throw a Rock` appearance. A subsequent question about the second companion slot triggered deeper tracing and disproved one r36 implementation assumption: HUD-object `+0x2D0` is not the action id. It is the 0/1 companion-slot selector for the pristine two-entry position table at file `0x3F8E80` / VA `0x4F8E00`: slot 1 `(172,407)`, slot 2 `(230,407)`. r37 leaves that path and table pristine, so the bubble continues to follow whichever companion slot is selected.

The actual action id comes from the game's existing getter at VA `0x0012FEE0` with key `0x8000`, followed by the same low-16 normalization used by the original caption renderer. r37 replaces r36's 96-byte selector with a 132-byte hook that reuses that getter, bounds-checks the 31-entry generated layout table, applies height/pivot-Y/text-Y, restores the group-2 `0x68` bubble arguments, and returns. The generic text policy is unchanged: 17 cells/row, width 224px, 48/64/80px for the current 1/2/3-line corpus, fail closed above four rows, no per-label geometry overrides.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r37.iso`, SHA-256 `69ece655ce0700a88ace5444334f0570a69568fdd1de140ef1e5efdff19a0c9b`; pre/post-ROFS ELF `ef7f6cd3100560ded37e4ad0aedb1919f0b09bf48a76a77339a7a6b212b04604` / `0eb2cd74ad0341685e5c942ad0e37ab875eaf0165855cfb84c35e1391d74a959`; final-image acceptance **154/154**; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip); repeat ISO is byte-for-byte identical. Runtime proof remains pending for slot 2 and for 2/3-line action labels because the current save/story state cannot expose them yet. Do not launch PCSX2 automatically.


### v11-r38 slot-aware companion bubble

r38 resolves the second-companion placement problem without moving the whole bubble to the second companion's X coordinate. The game already contains the correct sibling resource pair: group-2 `0x68` has pristine 288x80 pivot `(67,77)` and group-2 `0x69` has pristine 288x80 pivot `(125,77)`. The 58px pivot delta exactly matches the two companion anchors. r38 scales them to 224x48 with pivots `(52,45)` and `(97,45)`; as a result, slot 2 shifts the body/text only ~13px right while the tail tracks the full 58px anchor difference. Slot-aware text-X is `-36` / `-81`. The accepted slot-1 `Throw a Rock` appearance, 12px font, 224px width, and generic 1/2/3-line action wrapping remain frozen.

Action id and companion slot are explicitly independent. The 188-byte hook fetches action id through VA `0x0012FEE0` / key `0x8000`, reads slot separately from HUD `+0x2D0`, bounds-checks both, applies per-action height/pivot-Y/text-Y, selects `0x68 + slot`, writes slot-aware text-X, and returns to the original renderer. Invalid values fall back safely to action 0 / slot 0. Tests fail closed on both sibling resource-table mappings, all sprite metadata, runtime patch owners, and the declared pristine mutation regions.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r38.iso`, SHA-256 `e7d4c62df8157f00d8748b8e3bc93624705dacb19f8ae108d04683551c706a59`; pre/post-ROFS ELF `06a27d655951d86c55ae3c8b218450ac474074cbbf1f066f38e11c60114c22d7` / `6b60a13db20c5de99e03258ae70d3a5f4a4d2e442ffba934dc7aef04021f3303`; final-image acceptance **154/154**; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip); repeat ISO byte-for-byte identical. Runtime verification remains for the actual slot-2 visual and later 2/3-line action labels. Do not launch PCSX2 automatically.


### v11-r40 AFK-only companion fix

After r39 was reverted because the 8+8 name experiment broke runtime, Pablo explicitly chose to keep the original PS2 3+3 name behavior. r40 therefore starts from the restored r38 tree and changes only companion/acceptance ownership; the name implementation and name-specific tests are byte-identical to r38.

AFK chatter still appeared in Japanese because r30 covered all 1,784 pointers inside the 601-event `h_buddy.c` table but not ten direct aliases elsewhere in the executable. r40 adds exactly those ten owners, for 1,794 total direct companion-comment pointers, all resolving to the already-owned exact PS4/remaster English. A whole-ELF regression scan requires exact equality between discovered and modeled aliases.

The AFK bubble was also misplaced because r38 resized shared group-2 `0x68/0x69`, which passive chatter also uses. r40 restores those shared records to pristine 288x80 geometry and gives the active L1 renderer private compact clones `0xA4/0xA5` through a relocated group-2 table. This preserves r38's active 224px slot-aware bubble without altering the passive renderer's shared assets.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r40.iso`, SHA-256 `7693f45672ca510320911faef6108fd27521f8d2e865069b9da632d045643528`; pre/post-ROFS ELF `22e5b157164fbac32bfb905ab7295059c1a271b44fadf03ec34971aab763e498` / `01c9fd338ce37b11a69fa9456717770a27d9de2c2e0a508de46c7fc86e98453f`; final-image acceptance **154/154**; both complete suites execute **244 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. Runtime confirmation remains required only for AFK English/layout and preservation of the accepted active-action appearance. Do not launch PCSX2 automatically.

### v11-r41 AFK text-only hotfix after r40 runtime break

Pablo runtime-rejected r40 because the game consistently breaks at the `Heracleion` transition immediately before the first old-man dialogue / first H.A.N.T. interaction. The suspect/risky owner was r40's relocation of the entire group-2 speech-resource table into the translation PT_LOAD. Static checks validated the copied records but did not prove that every runtime consumer accepts a relocated group table. r41 removes that change completely.

r41 restores all r38 companion-action resource/layout/runtime owners exactly and keeps the intentionally frozen original 3+3 name system. The only functional change over r38 is translation pointer ownership: ten direct aliases outside the original `h_buddy.c` event table now point to the same exact PS4/remaster English strings already used by the 1,650-line corpus. Total companion-comment pointer ownership is 1,794.

The strongest regression is a direct reference build comparison. A detached r38 worktree was rebuilt from the same pristine fixture and compared byte-for-byte with r41's pre-ROFS ELF. Sizes are identical (8,643,556 bytes). Exactly ten 32-bit pointer locations differ and they are exactly the ten new aliases; no group-2 resource table, action hook, H.A.N.T., old-man dialogue, `Heracleion Shrine`, startup/name, or translation-segment payload bytes differ from r38.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r41.iso`, SHA-256 `fe04b2070efd647dfd657d6dbdc973646f1e69c559e234835fb57c7d2f113f4d`; pre/post-ROFS ELF `9361623fa72cf61500dc3547c83a0b1f8df06ed0cd0d54b44182523535a9b63a` / `3c8faabc1e1870e3b1650ae332f7476e179d9faa7ce1d3ae8548775420ba1cb9`; final-image acceptance **154/154**; both complete suites execute **244 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. Runtime test order: (1) reach the first old man and first H.A.N.T. interaction without corruption; (2) later idle long enough to trigger passive companion comments and confirm English. Do not launch PCSX2 automatically.

### v11-r42 safe rollback / AFK investigation reset

Pablo runtime-rejected both r40 and r41 at the same pre-H.A.N.T. transition. r40 had an invasive group-2 resource-table relocation; r41 removed that relocation but kept ten whole-ELF 'aliases'. Direct inspection proves the alias-discovery heuristic itself was unsafe: several matched words are embedded in unrelated packed data, and `0x576778` is literally part of the ASCII command token `FOUT_CMD_PNL`. These were value collisions, not proven companion-text owners.

r42 therefore abandons the speculative AFK changes entirely and restores the executable-producing source/test path to r38. The generated pre-ROFS ELF, post-ROFS ELF and complete ISO all match the corresponding r38 hashes exactly. The original 3+3 name behavior and accepted active companion-action bubble are unchanged.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r42.iso`, SHA-256 `e7d4c62df8157f00d8748b8e3bc93624705dacb19f8ae108d04683551c706a59`; final-image acceptance **154/154**; both full suites execute **243 tests**; repeat ISO byte-for-byte identical. AFK Japanese comments are still an open issue. Future work must identify the actual idle-chatter renderer/data owner through runtime tracing or a structurally bounded table, never by scanning arbitrary aligned words for matching pointer values.

### v11-r43 actual AFK/free-talk owner + context-aware Re:charge translation

After r40/r41 were rejected, the AFK problem was retraced from Pablo's screenshot instead of from value collisions. The visible line is `む？迷ったかの？`, stored at file `0x3D20D0`; its real owner is pointer field `0x3F5028`. Expanding from that structural anchor reveals the complete dedicated free-talk table at `0x3E5FA0..0x3F8BA0`: exactly 30 companion ids, 20 records each, 0x80-byte stride, text fields at `+8/+0xC`, 999 live fields, 952 unique source strings. This table is distinct from the earlier 601-event `h_buddy.c` corpus.

The remaster omits most of this Re:charge-only corpus. r43 therefore uses exact PS4 English for the four fields that genuinely match and authored English for the remainder, with terminology/voice calibrated against the PS4 localization. The translation data lives in `tools/companion_afk_data.py`; tuple order is strict by companion id then record. Validation hashes the pristine table and full source corpus, validates every owner/id/sentinel, enforces <=38 characters, validates PS2 glyph support, and rejects conflicting English for reused source pointers.

r43 is text-only relative to r42/r38 runtime/layout. No speech-resource relocation, no private resource ids, no action-hook change, no geometry change, no name change. A direct r42-vs-r43 pre-ROFS comparison proves all 999 AFK pointer fields change and the only other old-file change is the translation PT_LOAD `p_filesz` metadata at `0x64..0x66`; 44,257 new bytes are appended. This is the release invariant that replaces the unsafe whole-ELF heuristic from r41.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r43.iso`, SHA-256 `6d52f43224744bb24fe22c19f5cf0047b65ccfddc7815e44d909bd3aa3546165`; pre/post-ROFS ELF `517e6249a78f79bfb5c474445627df056487757aef2ae90babeb0965d9e4faef` / `fe34ee64b1ea2a1966604cc5cb9bbca2e50736238ee1bfe589221f54b284f129`; final-image acceptance **155/155**; both full suites execute **246 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. Runtime test order: (1) pass `Heracleion` -> old man -> first H.A.N.T.; (2) trigger Salah or another companion's passive free-talk and verify English; (3) confirm the active L1 action bubble remains r38 behavior. AFK bubble position is intentionally not changed in r43.

### v11-r44 AFK speech temporarily owns the companion HUD

Pablo accepts r43's translated free-talk at runtime. r44 resolves the screenshot where the AFK bubble and persistent L1 action bubble appeared simultaneously. The design choice is intentionally conservative: AFK keeps its own native renderer; the L1 action renderer is merely hidden while AFK speech objects are alive.

Tracing `H_TalkBuddyTask` gives a deterministic native predicate. `s0+0x04` is the current contiguous talk-record index; `0x259` is the boundary after the 601 original `h_buddy` records and therefore the first Re:charge free-talk record. `s0+0x20/+0x24/+0x28/+0x2C` are the native speech render handles. The existing L1 path at `0x666BC` already skips the entire action callout when its guard is zero, so r44 replaces only that guard computation with a 76-byte predicate. Original `s0+0x2C8 == 0` behavior is preserved. Otherwise, AFK record + live speech handle returns zero; all other states return the original nonzero guard.

Callsite after finalization: `0x666BC = jal visibility_hook`, `0x666C0 = nop`, `0x666C4 = beq v0,zero,+0x73`, preserving target VA `0x00166814`. The predicate uses only caller-saved `v0/t0/t1` and performs no nested calls or writes. The existing action layout hook, `0x68/0x69` resources, geometry, slot anchors, action-id getter, r43 AFK table/pointers, and 3+3 name system are unchanged.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r44.iso`, SHA-256 `ec0f35ff63bacff5f9d7f40ead7f29da59919fb81926489ecdd24bf29788b48c`; pre/post-ROFS ELF `e190a6399ebb6aabdf737b19861a355a6cbf1041df995a01e4e501b1b4508857` / `b1c13ddc0c9ed571a053dc867a9d2b9e2d106f013757a0d8f4275d255ef14b32`; acceptance **155/155**; both full suites execute **247 tests**; repeat ISO byte-for-byte identical. Binary delta against r43 is restricted to translation `p_filesz`, the 12-byte L1 guard/callsite, and 79 appended bytes. Runtime test: while AFK speaks, only AFK bubble should be visible; L1 bubble should automatically return after speech ends.

### v11-r45 native AFK composition and speaker-aware presentation

r44's runtime screenshot changed the ownership model. The visible green/blue stack is not simply two unrelated HUD systems: Re:charge AFK itself composes a slot-specific green `0x68/0x69` layer with a blue `0x6A` panel. This matters because the green layer is useful—it is the native speaker pointer/tail. r45 therefore does not attempt to erase all green speech resources or route AFK text into the L1 action renderer.

Speaker selection is proven in the native selector at `0x67A80..0x67C68`. It runs once per slot, derives the companion's 20-record AFK block, stores the chosen companion id at task `+0x338`, writes the final free-talk record index to task `+0x04`, and enters state 9. AFK-specific constructors later read `+0x338`. After the panel/text objects are constructed the task sets state 11; teardown progresses through 12/13 and returns to 8. The r45 visibility hook therefore uses `record>=0x259 && state in [11,13]`, not r44's render-handle OR. The original `+0x2C8` action visibility condition remains first and authoritative.

The AFK blue panel is data-driven. Resource `0x6A` table record `0x380E40` points to three metadata frames at VA `0x00450B20` / file `0x350BA0`, originally 288×56 with pivot X=67 and pivot Y=74/75/76. The only structured `(2,0x6A)` placement rows are the two AFK slots at `0x3F8E44` and `0x3F8E58`. r45 changes those frames to 224×56, pivot X=52, pivot Y=45/46/47, leaves slot 0 at x=172, and shifts slot 1 to x=185. This mirrors the already accepted 13px body displacement of compact `0x68/0x69`; the green resource still carries the 58px tail displacement to the correct companion slot.

Do not generalize this into a group-2 table relocation. r40 already proved that invasive resource ownership changes can break unrelated scenes. r45 edits only the proven `0x6A` metadata/placement owners and the existing visibility-hook payload. r43 English free-talk pointers, r38 action resources and action-id selector, H.A.N.T., title/name/startup, and original 3+3 name behavior remain frozen.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r45.iso`, SHA-256 `8828ce028ef6b18ffe0525ada81925ef6ca8ff2b48a7d46141e54c959cb806ab`; pre/post-ROFS ELF `1e8aa69d63eb1056b0a319f417abaa14627165029e0d0e4470cf35e603b0f000` / `2f3a849ef82eb3a2bd4d266955652fbc07266565ac653b9b3f6a41b5e19d23e3`; final-image acceptance **155/155**; both complete suites execute **249 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. r44→r45 is same-size and only 44 bytes differ, all inside the declared `0x6A` layout owners or the existing visibility-hook body.

### v11-r46 safe AFK panel restoration after r45 runtime rejection

Pablo runtime-rejected r45's AFK geometry change: the blue-tinted native free-talk panel disappeared entirely, leaving only the green companion-shaped layer. The r45 ownership trace is still useful, but the conclusion that `0x6A` could be safely compacted was wrong. r46 keeps the trace and discards the geometry mutation.

`patch_companion_afk_layout` is now validation-only. It verifies the native `0x6A` resource-table record, all three native metadata frames and both structured AFK placement rows, then returns the input bytes unchanged. `COMPANION_AFK_PANEL_LAYOUT_PATCH_OFFSETS` is intentionally empty. A separate validation-owner inventory is used by final-image tamper tests so these bytes are still fail-closed even though they are no longer legal mutations.

The r45 state-driven L1 predicate is preserved exactly. It keeps the original `s0+0x2C8` action visibility guard, checks `task+0x04 >= 0x259`, and hides the independent action callout only for native `H_TalkBuddyTask` states 11..13. This is stronger than r44's render-handle inference and does not alter AFK resources.

Binary proof: r45->r46 changes only 10 one-byte ranges, all restoring the ten r45 `0x6A` geometry/placement words; the relocated 76-byte visibility hook is byte-identical. r44->r46 differs only inside that visibility-hook body (34 bytes across 10 ranges), while the full native `0x6A` metadata/placement regions match r44 byte-for-byte. All three executables are the same size: 8,687,892 bytes.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r46.iso`, SHA-256 `f2ee41dbc82bb8499786094de501093ff62e81d6d0c6e8d127ce1caba1536d7a`; pre/post-ROFS ELF `3e217f69399acbd66527d83345f1fa8405db7fb5ac8007ce68185b31b2d65b2d` / `f847aca18d1d6741b6f23579951f5cfd39f19c70e538d20bc228a07099ccfa82`; final-image acceptance **155/155**; both complete suites execute **249 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. Runtime test: blue AFK panel must return; independent L1 action callout should disappear only during AFK states 11..13 and return afterward.


### v11-r47 shared companion bubble split by runtime consumer

r47 supersedes the static-geometry model used from r38 through r46. The green companion resources `0x68/0x69` are genuinely shared: normal L1 actions need the accepted compact 224px geometry, while native Re:charge AFK expects the original 288×80 outer bubble around its 288×56 blue `0x6A` inner panel. The finished ELF therefore leaves `0x68/0x69` pristine and changes geometry only immediately before the corresponding consumer constructs a callout.

For normal L1, the accepted action selector still resolves action id, slot and row count exactly as before. Its fixed 188-byte owner remains at the same translated VA, but its old return tail now jumps into a newly appended 72-byte extension. That extension computes slot*0x30, targets metadata `0x00450AC4/0x00450AF4`, writes width=224, chooses pivot-X=52 or 97, then performs the original stack/RA restoration and returns with `a0=2`. Existing action-specific height/pivot-Y/text positioning is unchanged.

For AFK, the owner at file `0x66050` is redirected to a 112-byte native-geometry helper. It first preserves the original `lh v0,4(s0)` semantics, requires a Re:charge record (>=0x259) and a valid slot from `s0+0x2F8`, then restores the selected shared resource to width=288, height=80, pivot-Y=77 and pivot-X=67/125. It recomputes `v1=v0<<7` before returning, preserving the original instruction contract. Blue resource `0x6A` and its placements are validation-only and unchanged.

The text-fit mechanism is record-generic. Native AFK style 0 advances 16px per wide glyph; text X=117 against body left X=105 gives 12px left padding. With symmetric right padding the usable width is 264px / 16.5 cells. The build derives one scale for each of all 600 AFK records from the longest non-empty translated row, `min(1,16.5/longest_chars)`, stores those values in an appended 600-float table, and loads the same record scale into f16 before constructing either AFK row. The ordinary h_buddy callsites keep their original f16=1.0 setup. Current corpus range is 1.0 down to 0.4342105263; every live field satisfies the bound.

Payload ordering is a compatibility invariant. r47's scale table, scale hook, AFK native-geometry hook and L1 geometry extension are appended after the existing r46 visibility hook. Direct binary audit confirms the 999 free-talk pointer values, visibility-hook bytes and every old translated payload address remain stable. The only old translated code mutation is the final action-hook return tail, which now jumps to the extension.

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r47.iso`, SHA-256 `c81013599fa3b504670f630c8644f35c0c8bcccf36bc5967a3866183387a73aa`; pre/post-ROFS ELF `94f055aa0a659be822cfc2f097cd873929e6d89b0022d4fc72b57a3514787039` / `02b713ef36cd3daa641208c029743ea069f254a759277a49755f19d06dcac9d7`; final-image acceptance **155/155**; focused suite **38/38**; both complete suites execute **250 tests**; deterministic repeat ISO is byte-for-byte identical. Runtime proof of the final geometry/scale behavior is pending.


### v11-r48 AFK text opacity/X-scale correction

r47 geometry is runtime-accepted by Pablo's screenshot: the AFK bubble now presents the intended blue/green native-sized composition. The missing text is a separate regression caused by misidentifying caller `f16` as an X-scale parameter.

The specialized free-talk constructor at `0x001950A0` passes caller `f16` through the generic object constructor as the fourth clamped RGBA component. r47 therefore scaled text alpha down with the per-record fit table. r48 restores both specialized AFK `f16=1.0` owners exactly and moves the fit to the proven horizontal transform: renderer code reads text-object `+0x48` and multiplies it into horizontal glyph coordinates; `+0x4C` is the separate vertical transform.

The same r47 600-float table is retained byte-for-byte. The same 64-byte relocated hook slot is reused at the same VA. Instead of running before construction, it runs after each AFK text object is returned, stores the selected record scale to object `+0x48`, and restores the native continuation value expected by each callsite. Nothing is appended, relocated, or resized relative to r47.

Binary safety is unusually strong: r47 and r48 pre-ROFS ELFs are both 8,690,540 bytes with identical translation-segment size. Only 80 bytes across 15 ranges differ, all in the two restored alpha setups, two post-construction hook sites, or the existing scale-hook body. All 999 AFK pointers, the scale table, green/blue metadata, AFK placements, geometry hook, visibility hook, normal action hook and action-geometry extension are unchanged.

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r48.iso`, SHA-256 `f91f14d34052a73a10f425cbbcd7c85c8b37d99aad0284de0e60257229cb319a`; pre/post-ROFS ELF `793d6a3c28dd894bfe85d4c16dfe1792ee70e5f36e607e9b98b4e3bbb301d49a` / `350477c63701e5a8eaa1efee9af05e6384dbcd84743f51bb55ef781b24521695`; final-image acceptance **155/155**; focused suite **38/38**; both complete suites execute **250 tests**; repeat ISO byte-for-byte identical. Runtime proof of text visibility and long-line fit remains pending.


### v11-r49 generic AFK multiline / upward-growth candidate

Pablo runtime-tested r48 and confirmed the blue-tinted companion free-talk composition and English opacity are fixed. The remaining r48 failure is long English escaping the bubble horizontally. r49 replaces horizontal scaling with native multiline wrapping and record-specific vertical growth.

The AFK source converter at VA `0x00195960` explicitly maps raw `0x0A` to internal newline command `0xFF0E`. r49 therefore wraps all 999 live AFK fields to at most 16 style-0 cells (256px inside the 264px body), hard-splitting oversized tokens if needed. There is no artificial line-count limit; only the game's native <0x1FE-byte source-buffer capacity is enforced fail-closed.

A 600-record layout table controls height/pivot/Y. Extra rows add 18px each. Green and blue widths remain 288px; X pivots remain native; height and pivot-Y grow together, so bottom edges and slot-specific speaker tails remain anchored while the bubble extends upward. The post-construction text hook fixes object +0x48 at 1.0 and changes only object +0x18 Y. Constructor f16 remains 1.0 alpha.

Current corpus row-count distribution is 44/162/166/179/47/2 records for 1/2/3/4/5/6 rows respectively. Maximum current vertical growth is 72px (green 152px, blue 128px). 726 AFK fields receive native newline controls. Because current breaks replace spaces, all r48 AFK allocation sizes and all 999 pointer words remain unchanged.

r49 is append-compatible with r48: +19,496 bytes = 19,200-byte layout table +184 geometry hook +112 text hook. Old r48 payload VAs/content stay intact. The common-prefix audit found 16,622 changed bytes across 1,328 ranges, all classified as one segment-size word, three callsite retargets, or wrapped AFK payload bytes; no unknown ranges.

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r49.iso`, SHA-256 `6fdcc8b7c4fe5e004c448a77b007cb39085f2d79eb6ac486ce01f791dd465321`; pre/post-ROFS ELF `084f09b0be4f181626fe4cf9205b939ba3368b3b178c75bb0ceacb4edf362e0e` / `c499b25f1142d9f4c4ae9791443cb20f38ccfa62d3335869f45e4279f2fe07bf`; focused suite **39/39**; both complete suites execute **251 tests**; final-image acceptance **155/155**; repeat ISO byte-for-byte identical. Runtime proof of multiline rendering/upward growth remains pending. Do not launch PCSX2 automatically.


### v11-r50 AFK anchor/multiline and L1 blue-panel correction

Pablo runtime-tested r49. Native multiline breaks are visibly active and horizontal overflow is materially improved, but long records still expose later rows below the AFK body. The whole AFK callout also remains low enough to collide with the left status HUD. Separately, normal L1 shows the accepted compact green action bubble in the correct upper band while the blue `0x6A` tint stays behind at the old AFK geometry/position.

r50 keeps r49's <=16-cell wrapping and translated payloads unchanged, but replaces the r49 18px vertical budget with a runtime-calibrated **32px** embedded-row budget. AFK placement moves from Y=381 to **Y=346** for both green and blue layers. Base text baselines are now 278/310. Record-specific height/pivot-Y still grow together, so every additional row extends the callout upward while preserving the lower edge/tail relationship.

Blue `0x6A` is now explicitly consumer-specific. The new 212-byte AFK helper applies 288px width, record-specific height/pivot-Y and slot-specific pivot-X 67/125 to both the green slot resource and all three blue frames. The new 136-byte L1 extension applies 224px width, action-specific height/pivot-Y and slot-specific pivot-X 52/97 to green and all three blue frames. This should make the tint fill whichever speech bubble is active instead of lagging behind at AFK geometry.

r50 is append-only relative to r49: +348 bytes exactly. The old r49 geometry/text hooks, visibility hook, historical action extension and all translated VAs remain at their previous addresses. The 600-record layout table VA is unchanged and only its vertical values are recalculated. All 999 AFK pointer words and all 999 relocated AFK text payloads are byte-identical to r49. Binary classification accounts for every changed common-prefix byte.

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r50.iso`; SHA-256 `2ec30aeb6738666a62faa643332166ebf5bd578e9729b366d706ce22f922459e`; pre/post-ROFS ELF `38001ec73c0ad2236090bf636c2e466d5ae814d166396874be72c3b6aee02e15` / `3010b80d910c96b9ad3ca439b7e151e5432bb7ebbfd460fc3bca0ad2f307c57e`. Focused suite **39/39**, both full suites **251 tests**, final-image acceptance **155/155**, deterministic repeat ISO byte-for-byte identical. Runtime proof remains pending. Do not launch PCSX2 automatically.

### r51 rejected; r52 recovery checkpoint

r51 screenshots establish a permanent large blue-tinted window independent of a live bubble and absent AFK text. The 72-byte independent L1 blue sprite constructor and task+0x2F4 sprite-destructor patch were unsafe because task lifetime does not establish synchronized sprite visibility. r52 reverts every r51 runtime change to the r50 baseline and appends only one 84-byte AFK Y helper; it updates both f13 and the native sp+0x1A4 argument spill before constructor 0x1950A0, unlike r51.

Runtime gate for manually-tested r52 ISO: confirm blue rectangle is gone; inspect both short and long AFK text and both companion slots, comparing to the accepted r50 green+blue bubble; verify unchanged native r50 L1 green bubble/action text. L1 blue fill is deliberately not attempted again until an authoritative visibility owner is proven. Never auto-launch PCSX2 or alter unrelated accepted content.

r52 measured static result: pre-ROFS ELF size 8,710,468 (+84 relative to r50), pre-ROFS ELF SHA-256 a649750384106b21d48ceecd2e29e532f70a41364e510f26a5ac8d31f64d16b8; post-ROFS ELF SHA-256 06de06af119b8a45a593cf8bdf6fc4e7c0a22d7dcacaae5e0b94ea1597a3a6df. r50->r52 post-ROFS ELF exact diff: nine old-prefix bytes, one translation p_filesz byte at 0x64 and four bytes each at the two AFK pretext callsites 0x66250/0x66320; zero unclassified changes. All 600 AFK pointer records, old translation payloads, r50 L1 constructor/cleanup, wrapped-text/layout, all accepted prior geometry and old segment content are byte-identical. Appended helper SHA-256 01f91b3c0dcc837b4f110676f40df84672c004e77141d53f0adf50427ac6d75c.

Candidate and repeat: /private/tmp/kowloon-recharge-startup-en-v11-r52.iso and /private/tmp/kowloon-recharge-startup-en-v11-r52-repeat.iso; SHA-256 c24d4585d905b304b27b0e4aa12a9a2080b0653b63c2c0f47093a35e32f58ee6, verified byte-identical. Focused suite 40/40, dependency-free full 252 tests (10 expected skips), Pillow-enabled full 252 tests (1 expected skip), final ISO acceptance 155/155. No PCSX2 run; runtime visual gate still unverified.

### r53 candidate pending runtime validation

r52 screenshots: AFK text absent; L1 blue displaced below green action callout; occasional small AFK blue overflow. r53 preserves t0..t3 (including constructor-saved t1) by using t4..t6 in the original f13+stack Y hook. It also creates L1 blue at green X/Y, initially transparent, mirroring the native three green sprite-alpha transitions and cleaning both task exit paths. AFK blue is horizontally inset 3px and green/tail geometry unchanged. All accepted English strings, 999 AFK pointers, wrapping, H.A.N.T., story UI and frozen 3+3 name entry remain intact.

Manually test r53 in PCSX2: English AFK text visible and contained for short/long records and both speaker slots; blue AFK panel contained at all tested sizes; L1 blue inside its green action callout and hidden when the callout disappears. Static tests and final-image checks cannot certify the renderer. Never launch PCSX2 automatically.

r53 deterministic release report: pre-ROFS ELF 8,710,632 bytes, SHA-256 d137e9b6444d1ffeaf530049fe9e608ecc6acf643fd23c45cfce589fa48808c9; post-ROFS ELF SHA-256 678327a0ea3ac826a11a028c5b02b82088001a6e764b4c7e606fc007a117be15. Full r52->r53 ELF increase +164 bytes = 100-byte L1 blue constructor + 32-byte show helper + 32-byte hide helper. Only declared old-prefix regions differ: p_filesz, both AFK blue placement X words, AFK-only blue width immediate, the existing 84-byte AFK argument-preserving helper, and seven explicitly owned L1 create/visibility/cleanup sites. ZERO unclassified differences. All 600 AFK records/999 structural pointer words, accepted green sprite geometry, frozen H.A.N.T/story/name surfaces are unchanged. New 164-byte append SHA-256 6acb8fd0f9b26fee26142995f84ac6caafa808bb3a1e58ed25912d2b9359a145.

ISO candidate: /private/tmp/kowloon-recharge-startup-en-v11-r53.iso; repeat: /private/tmp/kowloon-recharge-startup-en-v11-r53-repeat.iso. Both byte-identical; SHA-256 880db188a4c9d154ca18d61ce5312c4b64f46aad6f6bee2807f8c6a51539f338. Focused tests 40/40, dependency-free full suite 252 tests (10 expected skips), Pillow full suite 252 tests (1 expected skip), final-image acceptance 155/155. Runtime PCSX2 screenshot approval PENDING: static validation does not prove graphics/timing; test AFK and L1 bubbles before accepting visually.

### r54 candidate: two L1 blue windows and long AFK text overflow

Pablo's r53 test proves AFK English is restored, but four-row AFK still spills text at bottom and L1 renders two displaced blueish panels. Native AFK sprite at task+0x5C is the old lower blue; separately injected r53 L1 sprite lives at task+0x2F4. r54 hides the old sprite during each L1 native alpha transition rather than destroying a native handle, and places the new L1 sprite using the constructed green sprite's actual X/Y stored at object+0x3C/+0x40. For AFK, the second native text object is adjusted upward 18 units per additional embedded row; bubble geometry and translated contents untouched. Record487 is the known regression case; record480 is the short control case.

Runtime pass requires a single L1 tint precisely contained inside the green bubble with no lower/upward ghost, and no text or blue overflow for four-row AFK. Both slots, alpha show/hide and the old stable UI must be manually verified; do not claim runtime success from static tests. Never auto-launch PCSX2. Get reviewed changes to origin/main only after final static binary audit and reproducible builds.

r54 measured binary/static results: pre-ROFS executable 8,710,720 bytes, SHA-256 04c7db20180545d5c4799a5810ec556dd9826d35e323c7c149b80435e7bda4; post-ROFS executable SHA-256 07beeaf3569b70d61ce13ed6a4d64c35964ef482378dbe5ad89fae11129c8c78. Exact r53->r54 ELF growth +88 bytes, from 100->156-byte L1 blue constructor and 32->48-byte show/hide hooks. Common-prefix classifier: 1 byte p_filesz, 1 byte each at three native green show/hide JALs, 335 changed AFK per-record second-text-Y float records (every other byte in each 600x32-byte table record untouched), and 74 changed bytes inside the former L1 helper payload region; ZERO unclassified bytes. All 999 translated AFK text pointers, 600 original AFK record headers, 0x68/0x69 green metadata, AFK blue geometry/placement, and prior accepted content remain identical to r53. Appended combined L1 helper SHA-256 796d258c2fd90aa0e463d9337d67ccdc7b86761ab0c9651c76dfee9d040f7d24.

Candidate r54 ISO: /private/tmp/kowloon-recharge-startup-en-v11-r54.iso. ISO SHA-256 efc6c316e03c909781acbf51088873a03afa2c34f77cd6f6c6a65a0d0981d901. Focused suite 40/40; dependency-free full suite 252 with 10 expected skips; Pillow-enabled suite 252 with 1 expected skip; final ISO acceptance 155/155. Repeat ISO reproducibility is a separate required gate. PCSX2 must still manually validate L1 and both AFK lengths and companion slots; never auto-launch.

### r55 build checkpoint — L1 single native sprite and large AFK blue trim

r54 runtime proves L1 still has TWO blue panels. Repeatedly trying to hide a second new object did not solve it. r55 removes the extra allocation completely and reuses the single existing native AFK resource0x6A at task+0x5C for normal L1 actions. Move its actual instance X/Y to the green +0x2D8 instance's real X/Y, set its depth between green and text and mirror the original green alpha visibility, without early native resource destruction. Restore original +0x2F4 destructor to its correct pre-r51 behavior. Blue for larger (>2-row) AFK messages is trimmed by 3 game units ONLY at its bottom edge; all AFK text is frozen and confirmed correct by r54 screenshots.

Never auto-launch PCSX2. Runtime still must confirm exactly one blue layer inside the L1 bubble that disappears with L1 and AFK blue contained inside green for all tested sizes. Do not claim successful graphics until Pablo's screenshot proof. Continue to preserve frozen 3+3 name entry and all other accepted surfaces.

r55 measured validation: pre-ROFS ELF size 8,710,720 and SHA-256 81c8a61719ac62238063a7f3eb4496f2c65a5aaa9d43894d7bd3ff8db4c2604d; post-ROFS SHA-256 6db8c10fb8aed9cb5c178641e39800521c5999e3d716fc84ef7f401b7adb25b2. The r54→r55 strict post-ROFS audit classifies 394 byte differences in only the multiline AFK blue-height entries of the unchanged 600x32 layout table, 156 bytes in the existing L1 blue helper region, and 6 changed bytes reverting both native task+0x2F4 destructor callsites. **Zero unclassified differences.** All 600 AFK owner records (including 999 pointers), green/blue metadata, original AFK placement records and text translations are unchanged. ELF size and relocation addresses do not grow.

r55 primary and repeat ISO images are verified byte-identical; SHA-256 8ddcb764c6150dc652fc71af87f8d3d0eeb7c320f8f2c66c11a8fd04103ae16d. Paths /private/tmp/kowloon-recharge-startup-en-v11-r55.iso and /private/tmp/kowloon-recharge-startup-en-v11-r55-repeat.iso. Focused tests 40/40; full dependency-free suite 252 (10 expected skips), Pillow-enabled full suite 252 (1 expected skip), final-ISO acceptance 155/155. Runtime manually tested? NO; next user screenshots must confirm.

## r56 candidate — native live-sprite pool owner, AFK gap/bottom adjustment

Pablo's r55 PCSX2 screenshots prove AFK English is visible and short bubbles are accepted. L1 still has no blue fill inside green, with an old blue window visible below; r55's task+0x5C object pointer was not authoritative for the lower sprite. Long AFK screenshots (notably record487, "Ruins and people / both / grow richer with / age.") show a larger-than-usual gap between the TWO native text objects and a small lower blue overhang. The embedded line breaks inside one text object use the game's 32-unit renderer step; do not globally modify that renderer or font.

Tracing native sprite allocation at VA0x107D60 and pool manager VA0x107E00..0x108050 proves live sprites are stored in a 512-record pool at VA0x007A5060 with stride0x94, active byte+0x93, group halfword+0x82, resource halfword+0x84, constructed X/Y floats+0x3C/+0x40, Z float+0x68, vertex alphas+0x23,+0x27,+0x2B,+0x2F. r56 uses those NATIVE allocation records to locate group2/resource0x6A, rather than the task-local +0x5C pointer. The existing 156-byte action helper at file0x66740 searches the pool without allocating or destroying a new sprite, copies the ACTUAL green speech sprite's constructed X/Y from task+0x2D8 into the located blue sprite, sets depth242.5, and caches that exact located pointer in a reserved four-byte RWX word at the end of the existing helper (VA helper+0x98). Both existing 48-byte native green show/hide callbacks use that cached instance to mirror four-vertex alpha. The caller's displaced f12 for next resource remains untouched. If no live group2/resource0x6A is present, the pointer remains null; no speculative allocation or unrelated UI mutation occurs. Native AFK lifecycle retains ownership and disposal.

For AFK, the long-multiline blue-height bottom-only trim increases conservatively from 3 to 6 game units. First text object's Y, all accepted green geometry, blue X/width and pivot, texture data, all translated words and native slot anchors remain unchanged. For AFK records whose first text object spans multiple lines and the second object is present, move ONLY the second object's Y 9 units upward, eliminating the observed extra separation between native text objects; record487 text2_y moves 260->251 while short record480 and 'Easy, easy!' record485 are unchanged. The native within-one-object newline step remains the original 32, because changing this global renderer would risk unrelated accepted screens.

This remains a STATIC-CHECKED r56 candidate, NOT a runtime-proven rendering fix. Manual PCSX2 confirmation is mandatory: one blue panel INSIDE L1 green with no lower panel, disappearance with L1, long AFK line spacing/bottom fit and unchanged short AFK in both companion slots. Never auto-launch PCSX2.

r56 measurements: pre-ROFS ELF 8,710,720 bytes, SHA-256 0610ef1fbef96e964fa217e7d23a83816dbb5289ba4eb3e2962bd775973ca9cb. Post-ROFS executable SHA-256 c0838f8019d5d07b6db80f789fe9cb5d6fca41d8153d6cbe9ea6263551755482. Compared with r55, EXACT same ELF size and relocation owner addresses. Classified common-prefix changes: 394 changed bytes across eligible AFK blue-height floats; 261 changed bytes across eligible AFK second-text-Y floats; 163 changed bytes in existing append-only L1 native-pool helper region; **ZERO unclassified differences**. All 600 native AFK records and 999 translated text owner pointers, green/blue resource geometry metadata and screen placements remain byte-identical; no previous translated content altered.

Candidate ISO: /private/tmp/kowloon-recharge-startup-en-v11-r56.iso, SHA-256 e7adad161c2296981af0f02a44c0f0a2e9ad06a2b7bbac2f44f6f456b42a095e. Focused 40/40; dependency-free full 252 (10 expected skips); Pillow full 252 (1 expected skip); final ISO acceptance 155/155. Deterministic repeat ISO comparison performed separately. PCSX2 NOT launched; no visual result certified.

## r57 — defer L1 native blue lookup to visibility animation; four-row-only AFK blue trim

Pablo's r56 PCSX2 screenshots showed the L1 green action bubble unchanged with no blueish fill, while some four-row AFK bubbles still had a slightly overflowing blue bottom. AFK two/three-row text and tint look nearly or fully correct. The preceding r56 task-constructor hook executes just once, potentially BEFORE a separately owned native group2/resource0x6A blue sprite is allocated; its one-time scan can therefore cache NULL and all later alpha callbacks miss it. This is a timing hypothesis based on the observed absence of rendering changes, NOT verified by a live memory trace.

r57 retains the non-allocating 512x0x94 native sprite-pool scanner from r56 but also invokes it at EACH native green action alpha-transition callback (show at ELF file0x65A88, hide0x65B40 and fade-hide0x65C5C) before mirroring the alpha onto the resolved blue. The native green vertex-alpha byte is written first, then the callback saves/restores RA, v0 and f12 on a 32-byte aligned stack frame around JAL-to-scanner. It rescans and synchronizes live green X/Y, blue depth242.5 and exact blue pointer so a resource allocated after the original action constructor can still be found. These helpers grow from 48 to 80 bytes each; the original 156-byte non-allocating scanner does not change. As before, the hook allocates NO extra sprite and does not touch ownership/destructors. Native caller JAL delay slots and preexisting layout/text payloads are untouched. The static verifier matches exact relocated scanner+alpha helper bytes and rejects any corruption. Runtime PCSX2 must show ONE blue layer inside L1 and no displaced panel before the change can be accepted.

For AFK, preserve all r56 text positions, word spacing, native per-string newline advance and 2/3-row blue heights exactly. For 4+ rows ONLY, additionally trim the blue rect's bottom by 6 game units: previous >2-row trim6, so >=4 rows now trim12. Do NOT alter green frame/pivot, AFK first/second text objects, translations, source word wrapping, blue X/width/pivot, resource placements or any unrelated UI. Four-row example 'Ruins and people / both / grow richer with / age.' has blue height102 (formerly r56 108), green height144 and unchanged text1 Y214/text2 Y251; the three-row 'Easy, easy! / This is nothing / to me.' remains blue82 and short two-row 'Come now, this / way.' remains blue56. These are structural/size checks, NOT visual confirmation.

r57 measured release: post-ROFS executable bytes grew from 8,710,720 to 8,710,784 (+64 exactly, two 32-byte alpha extensions); SHA-256 c6db724ac461de39ac308641291c2365f94cdd3122d63ef6e115c5082ee926d4. Pre-ROFS ELF SHA-256 60e5362ab1d06fc82062f9ccf1cf2b22dba290b2fed46675c3fc8ca206d7119f. Strict r56→r57 ELF audit: p_filesz two bytes; L1 hide/fade-hide JAL one byte each, 228 changed bytes in eligible AFK blue-height floats, 80 modified bytes in existing L1 hook payload region; ZERO unclassified changes. 600 native AFK record headers with all 999 translated text/pointer owners, accepted static blue/green metadata, name entry and all other translations remain byte-identical. Focused 40/40; 252 full suite (10 skips); 252 Pillow suite (1 skip); final-image acceptance 155/155. ISO /private/tmp/kowloon-recharge-startup-en-v11-r57.iso, SHA-256 6a9f64b6bacf18699363c36a0b66317943ae37b6c9c62ab0187e178ac7e1ba47. PCSX2 was not launched automatically. The repeat ISO byte-equality check is a separate release gate.

Manual runtime gate: test L1 green action bubble shows exactly one blue tint inside, no blue below or above and no leftover tint when disappearing; test two, three, four and longer AFK rows in BOTH slots, verifying text visibility and no tint overflow. Static acceptance alone is not graphics acceptance.

## r58 candidate: fix group2/0x6A native compositor placement

Pablo's r57 PCSX2 screenshots still show green L1 bubble correctly in the upper band but blue tinted panel displaced below. r53-r57 task-local and sprite-pool instance X/Y changes produced no visible improvement. r58 targets a different and concrete data owner: static group2 resource0x6A composition placement records at ELF 0x3F8E44/0x3F8E58, XY at 0x3F8E50/0x3F8E54 and 0x3F8E64/0x3F8E68, runtime VA0x004F8DD0 +20*slot.

The r50 action-geometry extension executes after the native green bubble is constructed and retains selected slot in t5. r58 replaces its return with a tail jump to a new 64-byte helper, copying the real constructed green sprite XY from task+0x2D8 object+0x3C/+0x40 into the selected global blue placement XY. This does not create any sprite or touch the native 0x6A group/resource metadata. The prior animation alpha hooks remain intact. Previous attempts modified the wrong sprite-instance geometry; this change directly targets the untouched compositor placement instead. This is a technically motivated hypothesis, NOT a runtime-proven visual solution.

Free-talk reuses 0x6A, so r58 adds a tail call from the existing r50 AFK geometry helper to a 112-byte AFK-only placement restorer. It writes the accepted per-slot blue X175/233; the selected green metadata height at VA0x00450AC8 +48*slot chooses Y346 for <=3 rows (height<144), and Y344 for 4+ rows (height>=144), a modest 2px upward correction for remaining 4-line blue overhang. An invalid slot safely uses slot0. Green geometry, all text/spacing, prior AFK width/height/pivot logic and translated bytes remain unchanged. If screenshots show the 4-line overhang persists, do not blindly trim heights again: obtain a live GS frame capture.

Validation: r57->r58 post-ROFS executable grows exactly 176 bytes (new 64-byte action and 112-byte AFK helpers). Strict binary audit reports only segment p_filesz and the two original tail-J words changed in the common prefix, ZERO unclassified byte changes; all 600 native AFK owner records and all 999 translated text/pointer fields, previously accepted static geometry/placements and unrelated screens remain byte-identical. Focused 41/41; full 253 with 10 expected skips; Pillow 253 with 1 skip; final ISO acceptance 155/155. r58 ISO /private/tmp/kowloon-recharge-startup-en-v11-r58.iso SHA-256 be2847190e4609e6ea9c43457d12b633beefd62255b00d7cb79c79d7842ff938. Runtime PCSX2 was not launched; visual success is PENDING.

Manual gate: L1 must have one blue fill inside the green action bubble, no displaced upper/lower tint before or after callout; AFK 4+ lines must fit with no blue overflow, accepted <=3-line AFK remain unchanged, and both slots/action alpha transitions must be tested. Do not mark visuals accepted from static tests.

## r59: actual L1 group2/0x78 background, plus green-relative AFK text

The user tested r58: L1 green speech bubble was still correct in the upper band but the blue-tinted background was still below at its old position; four-line AFK also left a small blue overhang, and the first text line moved visually closer to the green top border than in short AFK bubbles. The user explicitly requested that text be positioned relative to the GREEN bubble, not the blue layer. Previous r53–r58 fixes unsuccessfully targeted group2/0x6A, the native AFK background. Do not repeat this mistake.

**Root-cause code and metadata:** Original H_TalkBuddyTask `SLPM_665.11` at VA0x1666A8–0x1666E0 constructs the green action sprite (`group2/id0x18` originally, now slot-specific `0x68/0x69`) at `0x1666B4` and saves it to task+0x2D8. Immediately afterward, the game constructs **its actual action background sprite `group2/id0x78`** at `0x1666D8`, saving the result to task+0x2E0. Both calls receive the same constructor XY from stack+0x178 and use native depths243 and241, respectively. The group2 metadata record is at ELF0x380EB0 (VA0x004513F0, three frames, stride0x30); the original three action background frames are **152x32**, with pivotX **-6**, pivotY **-1/0/1**. For comparison, the original action green id0x18 is 160x32 pivot0, while the accepted translated green resources 0x68/0x69 are compact 224x48 with pivots52/97 and45. This mismatched image origin/geometry fully explains why L1's native background stayed near its original position. All r53–r58 blue scans/placement writes altered **AFK id0x6A**, not the native action id0x78.

**Minimal L1 fix:** r59 changes one immediate in the existing consumer-specific `r50` action geometry hook: it now sets the metadata pointer to VA `0x004513F4` (group2/id0x78 frame0 width) rather than `0x00450B24` (AFK id0x6A frame0 width). Its existing three-frame dynamic width/height/pivot writes therefore resize the real L1 background alongside the already accepted green 0x68/0x69 action speech bubbles. The game's own 0x78 sprite creation/visibility/teardown and original 0x68/0x69 geometries remain unchanged. Existing appended experiments stay allocated only for address stability; no new helper or segment growth. The known r58 AFK restorer is left unchanged. Static tests explicitly identify native id0x78/three frames and fail closed on the one-word action geometry target. **Runtime screenshots are still required to prove the new geometry is visually correct.**

**AFK text anchored to green:** For every AFK record compute the green's actual top from the native anchor Y346 minus its dynamic green pivotY (77+32 per row above two). The original two-row top text inset is 278-(346-77)=9 game units. r59 explicitly sets text1 Y to green top plus this stable inset; for >=4 rows it increases only the green-relative top clearance by 6 game units, addressing screenshots showing crowded text at the upper border. The second text object's Y is computed from this text1 Y so BOTH move together while their existing inter-line/object spacing remains unchanged. Blue background is independent: for >=4 rows only, trim its previously accepted dynamic height by another three units at its lower edge; <=3-row AFK text, green geometry, blue geometry and placements are unchanged. The r58 >=4-row conditional blue Y344 remains in place. This is a small measured candidate rather than an assertion of graphical success.

**Validation:** Focused 42/42; both full 254-test suites pass (expected skips only). Strict r58->r59 post-ROFS ELF audit: ELF size unchanged at 8,710,960 bytes, only one L1 `0x78` metadata pointer instruction and layout table blue-height/text1-Y/text2-Y entries differ, **ZERO unclassified bytes**. All 600 AFK native owner records/999 translated source pointers and all original green/action/AFK resource metadata/other accepted UI remain byte-identical. Build produced ISO `/private/tmp/kowloon-recharge-startup-en-v11-r59.iso`; final-image acceptance and repeat determinism are release gates. PCSX2 already happens to be running on user's Mac, but it was NOT launched, controlled, debugged, or interrupted by this work.

**Manual PCSX2 gate:** Verify L1 blue tint is now inside the correctly positioned green bubble (not below or duplicated), for both companion slots and during appearance/disappearance; check 2/3-row AFK unchanged; check four-row AFK blue fully contained and first text row has comfortable green-border padding. Do not equate static acceptance with proven visual correctness.

## r60: freeze user-accepted AFK; native L1 0x78 pre-constructor geometry

Pablo's r59 screenshots: the L1 blue rectangle is now singular and close to the green bubble but floats ABOVE its border. Pablo explicitly accepted the entire AFK appearance and asked that future edits never regress it. Original H_TalkBuddyTask constructs group2/id0x78 at VA0x1666D8. Previous r59 per-consumer geometry write at VA0x166724 runs AFTER this construction, likely leaving native cached pivotY -1/0/1 while later draw metadata has the action's 45+ pivot. That constructor ordering explains the approximate one-line vertical displacement and motivated r60; graphical confirmation remains pending.

The r56 scanner is called at VA0x1666C0, before native 0x78 constructor, and also runs from green-alpha callbacks. r60 changes only scanner's existing tail JR to a jump into an appended 220-byte helper. Its branch gate compares original native constructor return RA=0x1666C8 (JAL at 0x1666C0 +8); callbacks fast-return without touching blue metadata. The early call saves RA/SP, obtains action ID with native getter VA0x12FEE0, falls back safely for invalid action IDs/companion slots, reads action layout table, writes width224, dynamic action height/pivotY and slot X pivot52/97 to ALL THREE id0x78 frames at VA0x004513F4 +48*frame, restores RA/SP and native v0/f12 for the following constructor, and resumes at VA0x1666C8. Late r59 action layout continues unchanged. No extra sprite or new alpha/destructor behavior.

Frozen AFK regression test pins literal SHA256 of nine independently extracted areas from user-approved r59 ISO: all 600*32 dynamic layouts; AFK r50 geometry hook, AFK constructor pretext and text hooks, AFK compositor restore, 600 native records/999 pointer fields, green/blue metadata and placements. Representative 2/3/4-row Y and blue heights also have literal assertions. The new L1 helper is tested byte-for-byte, checks native return-address gate and metadata instructions, and fails closed on tampered instructions.

Strict r59->r60 post-ROFS ELF audit: EXACTLY +220 append bytes and only segment p_filesz and scanner tail jump changed in common prefix (ZERO unclassified byte changes); therefore ALL user-accepted AFK rendering and text code/data are byte-for-byte identical to r59. Focused44/44, full256 (10 expected skips), Pillow256 (1 expected skip), final image155/155. Candidate ISO /private/tmp/kowloon-recharge-startup-en-v11-r60.iso SHA256 799f3c3fcc14004d65a347176be7fa25bf08184226a310400268a422823c10e9. PCSX2 was not started or controlled. Runtime visuals of L1 still PENDING. Do not reopen AFK unless Pablo explicitly requests it.

## r61 — small native L1 blue alignment candidate; approved AFK frozen

Pablo's r60 PCSX2 screenshot shows the correct single group2/id0x78 blue fill almost inside the green L1 bubble, but slightly right and behind it. r61 shifts ONLY the actual already-constructed native id0x78 object (task+0x2E0) relative to live green object (task+0x2D8) world XY at sprite+0x3C/+0x40. Blue X = green X minus 2.0 game units; blue Y = green Y plus 1.0 game units. Approximately 6.5px left and 3.25px down at screenshot scale, avoiding any further change to green, action text, AFK layout or shared resource geometry. PCSX2 visual alignment is still UNCONFIRMED.

Implementation: append a 96-byte helper; the previous r58 L1-only compositor helper retains all its original instructions except its final JR changes to a tail J into r61. After native L1 sprite construction and existing r60 geometry initialization, r61 null-checks both object pointers, preserves F0/F2 on a 16-byte aligned stack frame, executes two single-precision add/sub instructions, writes only the native blue world XY, and restores F0/F2/SP/RA. It does not modify native alpha/teardown, action text, green bubbles, or group2/id0x6A AFK resources.

Frozen AFK regression barrier: nine literal SHA256 golden fixtures from the user-accepted r59 post-ROFS executable cover 600 dynamic layout records, native AFK geometry/pretext/text hooks, AFK compositor restore, 600 native records/999 translated pointers, green/blue native frames and placements. Strict r60->r61 post-ROFS diff confirms +96 bytes appended, with only segment p_filesz (2 changed bytes) and one L1 r58 tail jump (4 changed bytes) in the existing ELF; ZERO unexplained changes. All AFK code/data and translated strings are byte-identical to approved r60.

Validation: focused45/45; full257 expected10 skips; Pillow257 expected1 skip; final ISO acceptance155/155; repeat ISO byte-identical. ISO /private/tmp/kowloon-recharge-startup-en-v11-r61.iso SHA256 7fa9eaa0ab2aaabf9d8393ec9bb2b1dcf8d9a5e36c4354855525d5a5a3e0e8a9. Offline Unicorn MIPS execution confirms native green coordinates (175,346) produce blue (173,347), null-path safety and preserved F0/F2/RA/SP. PCSX2 was NOT started or controlled.

Manual gate: one blue L1 tint fully contained in the green outline for both companions and short/long action labels; AFK remains fully approved and frozen. Static tests do not prove visual success.

## r62 — native L1 inset geometry candidate, awaiting visual approval

Pablo's r61 screenshot shows the single L1 action blue tint still subtly displaced despite r61's post-constructor sprite X/Y nudge. AFK has been explicitly approved and MUST NOT be touched. The observed ineffectiveness of r61 implies that last-minute object XY is not the final geometry owner.

r62 changes only the true native L1 group2/id0x78 panel geometry at its r60 pre-construction owner. It appends a separate per-action blue geometry table after all r61 payloads, sets width 220 instead of green's 224, height to green-height minus four, pivot-X to green pivot-X minus two (slot0 50, slot1 95), pivot-Y to green pivot-Y minus two. By standard sprite origin/pivot rectangle arithmetic the blue panel's top/left/right/bottom edges are each inset two game units from the green bubble BODY at unchanged native XY. All 31 labels and both slots obey these bounds in tests. The r59 later blue metadata writes to the old green-size 224 are replaced with NOPs (green writes unchanged), and r61's ineffective post-construction live XY tail is replaced by normal return; allocated historical helpers retained to preserve all preceding relocated addresses. Unlike r61's nudge, this fixes the geometry at the actual constructor rather than after initialization, so subsequent geometry writes cannot undo it.

Strict r61->r62 post-ROFS audit finds only ELF segment size, 12 L1 post-constructor blue metadata stores disabled, an L1-only tail return, and the L1-only pre-constructor inset table+width/X pivots changed. ZERO unexplained changes; every native AFK hook/layout, original record, translated text and pointer remains byte-for-byte unchanged, including all nine independent SHA256 golden fixtures from user-approved r59. Focused46/46, two 258-test full suites (expected skips only), final image acceptance155/155. Emulator instruction-level MIPS test exercises all 31 action IDs x 2 slots plus invalid action/slot cases and all 64 alpha fast returns; real frame0/1/2 metadata matches inset geometry and no AFK metadata changes. Repeated ISO build is byte-for-byte identical.

Candidate ISO: /private/tmp/kowloon-recharge-startup-en-v11-r62.iso. No in-game visual verification has been performed by the assistant. The user specifically requested NO updates to main until visual confirmation. Keep this change local on feature branch fix/r62-l1-layer-alignment-investigation and do not push or merge without explicit approval.

## r63 — L1 native blue right/bottom-only trim (local candidate)

User tested r62 and reported it still misaligned and worse than r60/r61. In r62 screenshot, the blue fill's left gap is visibly larger than its right gap. r62's symmetric 2-game-unit inset caused this asymmetry, possibly compounded by intrinsic alpha padding in the native blue id0x78 texture (UV .375-.96875, .6875-.8125). Postconstructor sprite XY corrections in r61 did not improve the rendered position.

r63 restores the closer r60 blue left/top to match accepted green (X pivots 52/97, Y pivot same action value), while trimming only 2 native game units from the right and bottom (blue width222 vs green224; blue height green−2). The accepted native 0x78 geometry is patched before constructor and 12 later blue geometry overwrites remain disabled; r61 live XY nudge remains dormant. Green action bubble, all text, resource metadata and all AFK code/data untouched. This is a screenshot-motivated geometry hypothesis, not in-game proof.

Strict r62->r63 executable audit finds exactly 3 L1 blue preconstructor immediate changes and 62 L1-only per-action blue table floats; no other bytes changed. Nine user-approved AFK golden SHA256 tests remain enforced. Focused46/46, full258 expected10 skips, Pillow258 expected1 skip, final ISO155/155; offline MIPS emulator executes all 31 actions for 2 slots plus invalid inputs and alpha fast-return paths. Candidate ISO /private/tmp/kowloon-recharge-startup-en-v11-r63.iso SHA256 67b30d2df92a665a537588f34f190696f3dd3bca3359529ab6d70ee8271e2d19.

User expressly prohibits pushing/merging/updating main until runtime screenshot confirmation. Keep local branch fix/r63-l1-asymmetric-blue-bounds only, do not change main; do not launch or disturb running PCSX2. If further visual correction is needed, capture actual native draw primitive bounds/texture UV rather than blindly adjusting offsets.

## r64 — user-directed L1 blue left expansion and bottom shortening (LOCAL ONLY)

Latest PCSX2 r63 screenshot: blue L1 layer fills X+ but X- has an unfilled strip; Y+ improved but Y- still overflows green. AFK perfect/frozen. r64 retains r63 blue TOP and RIGHT exactly, extends only the left by 2 native game units, and shortens blue bottom by 2 more. Resource is native action group2/id0x78, not AFK id0x6A.

For all 31 actions/two speakers: blue width224 (r63 222); blue pivotX slot0 54 vs r63 52 and slot1 99 vs r63 97. At unchanged anchor, screen-left 2 units farther left while screen-right remains EXACTLY r63. Blue Y pivot untouched, preserving r63 top. Blue height = green height−4 (r63 green−2), trimming bottom by two. No green, action text, or AFK changes. r62 native preconstructor owner remains; late blue writes and r61 ineffective live XY stay disabled. Screenshot-guided candidate requires graphical confirmation.

Focused46/46; full258 (10 expected skips); Pillow258 (1 expected skip); final image155/155; offline Unicorn64/64 constructors and64/64 alpha callbacks. Strict r63->r64 post-ROFS binary audit: only 3 native L1 width/pivotX immediates and one blue-only height float for each of 31 action layouts changed. Zero unclassified differences. All AFK hooks/data, user-approved green sprites, text pointer records unchanged; nine independent AFK SHA256 golden tests pass. Repeat ISO byte-for-byte identical.

ISO /private/tmp/kowloon-recharge-startup-en-v11-r64.iso SHA-256 4ee5bd6d6fbabd515947a53eee365da0b3094dcd9f687df11b522570475299b6. User explicitly prohibits changes to main until visual confirmation: keep local feature branch fix/r64-l1-expand-left-trim-bottom ONLY; do not push or merge. PCSX2 not controlled or restarted. Visual result pending.

## r65 — final 1-unit L1 blue-edge calibration (LOCAL candidate; requires visual signoff)

Pablo tested r64 with two screen crops and confirms the L1 blue background is much closer, but there is still a slight X-minus/left gap and Y-minus/bottom overflow. He specifically wants the blue tint to fill the complete green dialogue body. r65 makes only the two independent edge adjustments requested, conservatively one more native game unit in each direction, without moving accepted right/top edges.

Real native action group2/resource0x78 geometry is initialized BEFORE the sprite constructor. r64 blue width224, pivotX54/99 becomes r65 width225, pivotX55/100 for speaker slot0/1: left edge moves ONE native unit left while its right edge is mathematically identical. Its action-specific blue height is reduced from green−4 to green−5, preserving the same pivotY/upper edge and moving only the blue bottom ONE native unit upward. All 31 action IDs and both slots are explicitly checked against green body bounds. AFK uses separate resource0x6A and is user-approved; do not touch it.

Validation: focused46/46; full258 tests (expected skips); Pillow258 tests with one expected skip; ISO acceptance155/155. Strict r64->r65 post-ROFS binary audit reports exactly three native L1 blue width/pivotX immediates and the 31 action-only blue height floats changed, ZERO unrelated/unclassified differences. All AFK hooks, resources, pointer records, translated text, green geometry, and nine user-approved r59 golden AFK SHA256 snapshots are unchanged. Offline Unicorn MIPS executed 64 native constructor cases and 64 alpha callbacks, preserving FPU/GPR state and AFK data. ISO /private/tmp/kowloon-recharge-startup-en-v11-r65.iso SHA256 92edf5a82f9bbc2603666dcfe9ed6e55995b705cae61556aa27f5dfd55d7b8a5, with deterministic byte-identical repeat build.

User constraint is still active: DO NOT push, merge, or update main without explicit visual confirmation. Keep changes in local feature branch fix/r65-l1-final-left-bottom-calibration. PCSX2 was not started or controlled. The graphical result remains UNCONFIRMED pending the user's test screenshot.


## r66 — generic L1 action/speaker edge adjustment (LOCAL candidate, not visually approved)

Pablo's r65 screenshot shows very slight remaining X− underfill and Y− overflow on L1 callout; right/top are approved. Adjust ACTUAL native group2/id0x78 blue geometry in its pre-constructor code without touching accepted green geometry/text or ANY AFK data. Compared with r65: blue width225→226, blue pivotX slot0 55→56 and slot1 100→101. The blue left edge moves one game unit left; because width and pivot change together, the RIGHT edge is mathematically identical. Blue height green−5→green−6, keeping pivotY unchanged; the bottom moves one game unit UP while top stays identical.

**Generic scope**: r66 does not hardcode "Throw a Rock." It operates on the same dynamic blue layout table for ALL 31 currently defined native L1 action IDs, with native companion slot selection 0/1. Unit tests independently verify green-relative X−/X+/Y+/Y− bounds on all 31 records and both slots, including action-specific heights, and MIPS32 emulation checks all 62 valid action/slot combinations plus invalid action/slot fallbacks and alpha-callback fast paths (64 cases of each). Thus it covers every CURRENT supported L1 action for a companion occupying either native slot. New action IDs or a future third native slot would require extending the table/validation; do not claim these unimplemented cases automatically work.

AFK is PERFECT and explicitly user-approved from r59. Nine independent post-ROFS SHA256 golden fixtures continue to protect its 600 layouts, original owner records/pointers, text, geometry, sprite resources and placements. Strict r65→r66 binary comparison found exactly three L1 width/X-pivot immediate bytes and 31 blue-only action height floats changed, ZERO unclassified changes; all AFK bytes, green geometry, localized pointers, text and unrelated UI byte-identical.

Candidate /private/tmp/kowloon-recharge-startup-en-v11-r66.iso, SHA256 1e818e50283ea1f8d9480293aecc5cd8dcc95b32fe128b430d7445ef1718d5e5. Focused46/46, full258 (10 expected skips), final image155/155, offline MIPS constructor64/64 and alpha64/64 passed. Repeat-build and Pillow suite are separately validated. Visual PCSX2 test STILL REQUIRED; no claim of perfect alignment until Pablo confirms. User explicitly forbids changing/pushing/merging main before approval. Keep r66 on unpushed LOCAL feature branch fix/r66-l1-edge-final-tuning, preserving main at e55e29c.


## Latest authoritative checkpoint: r66 accepted — release hardening

As of 2026-10-08, Pablo directly confirmed the **r66 AFK and L1 bubble backgrounds
both work in PCSX2**. The prior local-only/no-merge restriction has been
satisfied for this specific candidate. Earlier r62–r65 observations and
hypotheses are historical; do not confuse them with current runtime status.

- r66 ISO: `/private/tmp/kowloon-recharge-startup-en-v11-r66.iso`
- ISO SHA256: `1e818e50283ea1f8d9480293aecc5cd8dcc95b32fe128b430d7445ef1718d5e5`
- Native AFK group2/id0x6A: user-approved, unchanged since r59 layout.
- Native L1 group2/id0x78: user-approved r66; 31 known L1 actions by 2
  companion slots; blue width226, X pivots56/101, blue height green−6,
  pivotY equal to green. All existing active green/text owners are untouched.
- Six *independent literal* golden SHA256 L1 owners now join the nine
  literal accepted AFK goldens; final-image verifier additionally locks the
  action-selector bytes. Test names:
  `test_r66_user_approved_l1_binary_owners_are_frozen` and
  `test_r60_freezes_user_accepted_r59_afk_layout_and_runtime_bytes`.
- Save static gate:
  `test_approved_memory_card_save_namespace_and_paths_are_unchanged`
  freezes all 15 original `BISLPM-66511Save` path/descriptor windows.
- A new ISO remains unapproved unless Pablo sees and accepts its intended
  runtime differences. Do not disturb PCSX2 without approval.

### Recommended next work — incremental, save-compatible by design

**Do not declare the PS4-derived translation complete.** Current corpus
status in `docs/LOCALIZATION_STATUS.md` shows 962 exact MTX files/56,642
English entries imported but 23 indirect/dynamic mapped MTX files/21,672
entries rejected, 7 structurally changed MTX files/2,284 entries imported,
only FD00_31 proven in the special 26-file FD00 family, KSF 868 fitting
entries imported but 48 overflow and 4 ambiguous, PS2-exclusive text, and
unmapped gameplay/UI graphics. The repo has substantial discovery but NOT
sufficient proven remaster correspondence to auto-import every remaining
string without risk. Do not extrapolate from lexical similarities.

Ship vertical slices, preserving prior accepted presentation at every slice:
(1) inventory/reconciling unproven PS4 exact/indirect MTX mappings and their
dynamic ownership, (2) structurally changed FD00 and selected remaining KSF
with bounds/overflow solutions, (3) later gameplay/ADV/DG routes plus
unpromoted H.A.N.T./Mail/Help and remaining title/UI graphics, then
(4) independent PS2/Re:charge-only content with marked provenance.
Before each iteration choose one bounded class/chapter, inventory source/PS4
mapping, change only proven owners, add exact fail-closed tests, build
deterministically, run final-image acceptance, and request focused PCSX2
visual review.

**Save compatibility is a release gate.** Preserve
`SLPM-66511`/`BISLPM-66511Save`, serialization, story IDs/flags, item
indexes and transitions. Work on copies of a real ordinary PS2 memory card:
boot r66 and the new ISO separately, load same older checkpoint, verify state,
advance/save/restart/reload on candidate. Do not rely on savestates. Static
names/path tests cannot guarantee runtime save compatibility; this smoke test
is still pending and is the next non-translation acceptance infrastructure
task. Never alter the original memory card as the test artifact.

A safe offline snapshot helper and manual cross-release checklist are in
`tools/save_compatibility.py` and `docs/SAVE_COMPATIBILITY.md` (six focused
unit tests). The existing Mac Mcd001 image was copied to a checksummed
**unverified** reference under ignored `local/save-compat/`; presence of an
actual Kowloon save and runtime cross-release compatibility remain unproven.
Neither PCSX2 nor any original memory-card image was modified.

## r67 objective reset — first Soul Well memory-card save, NOT MS04_00 (2026-10-09)

Pablo explicitly defines r67 as "Everything from New Game through the first
successful Soul Well save is in English", including mandatory/optional screens.
The previously proposed `MS04_00` candidate (PR #34) is later-game and
**must not** be treated as r67 or merged for this milestone.

Implementation is in `.worktrees/first-save-r67`,
`feat/first-save-r67`. See `docs/R67_FIRST_SAVE.md` for commands, exact
owners, proof, and remaining release-blocking work. Current **P0 partial**
candidate SHA256 `57897c2ff1c4d84161bbb988318a00df5a75e2f20bc55c5fe82b6db612f487fb`
statically covers 29 original executable string owners and 148 pointers,
including the early rooms, Soul Well, puzzle inscriptions, and object
inspection texts. This is an append-only post-r66 ELF modification. ISO
acceptance **155/155**, whole-image r66-delta audit **zero unexplained bytes**;
AFK/L1 r66 binary code and text remain frozen. No PCSX2 was launched.

**Still blocking completion:** 50 H.A.N.T. Help pages remain unpromoted; a
full static texture, interactions, combat/status, UI and English text-layout
audit is also required. The 55-page indexed inventory found 759 original
nonblank body rows, 737 with unique PS4 matches. Fifteen ADV page slots share
one actual Japanese one-line easter-egg placeholder ("Saitama, Saitama!"
in the official remaster), *not* empty pages. The translated H.A.N.T.
topic **labels** are not evidence that body pages are translated.
Do not invite Pablo to play an allegedly English-complete release yet.

Once static English coverage is complete, Pablo himself runs New Game through
the Soul Well, reports untranslated content, and repeated fixes must close
those gaps before any r67 milestone acceptance. Only **then** will he make
the first genuine permanent in-game memory-card save (cross-release golden).
