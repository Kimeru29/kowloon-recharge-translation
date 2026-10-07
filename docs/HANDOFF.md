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


### v11-r39 8+8 name editor and passive companion chatter

Pablo's r38 runtime review accepts the active L1 companion-action bubble but exposes two separate remaining surfaces. The name editor still behaves as pristine 3+3 (`Hab` / `Kur`) even though the PS4/remaster English implementation uses eight characters per surname/given-name field. r39 ports that contract structurally rather than changing a single cap: the already-skipped kana-reading object storage becomes two 32-byte arenas, the second visible field moves to the widened owner at +0x68, and every observed append/delete/init/commit/split owner is patched fail-closed. Static regression now verifies the remaster-aligned 8+8 contract and final-image acceptance includes it as a named gate.

The AFK screenshot also explains why r38's passive bubble was misplaced: the active action patch had modified shared group-2 `0x68/0x69` metadata. r39 leaves those shared resources pristine for idle chatter and gives the active renderer private compact clones `0xA4/0xA5` through a relocated group-2 table, retaining the accepted r38 active geometry. Translation ownership is expanded independently: the original r30 event-table inventory remains 1,650 exact PS4-matched sources / 1,784 event aliases, while a whole-ELF pointer scan finds ten extra direct aliases that r30 did not own. All ten are now repointed to the same exact PS4 strings, producing 1,794 total direct comment owners; a regression scan proves there are no other direct 32-bit aliases to those sources, and no adjacent MIPS absolute-address materializations were found.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r39.iso`, SHA-256 `ccac5ecd4d8f889482ce3750c8141adca68c5eff545d3266c5f72f75745ea88c`; pre/post-ROFS ELF `96add4d1385882b3ca43962eb277a0a6c451f19596da2d67688d08b4e30b3fec` / `3eb2c83ac708fd450232b8df55fe99f1446e397c921e1e4c7a974f683dd00795`; final ELF size 8,644,980 bytes; final-image acceptance **155/155**; both complete suites execute **246 tests** (10 dependency-free skips / 1 Pillow skip); repeat ISO byte-for-byte identical. Runtime confirmation remains required for 8+8 typing/deleting/committing and AFK English/layout. The active L1 presentation is intended to remain visually identical to r38. Do not launch PCSX2 automatically.
