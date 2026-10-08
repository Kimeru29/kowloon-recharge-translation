# Verified discoveries

## Source identity

- PS2 archive SHA-256: `e5ff46e62846758cda33bd5a4ef98d12d6bdfe2f76cdd6ac73145a76f68a3fec`.
- Pristine PS2 ISO SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`.
- PS4 PKG SHA-256: `054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`, title `CUSA27034`.
- PS2 boot executable: `SLPM_665.11`; serial invariant `SLPM-66511`; save namespace `BISLPM-66511Save`.

## ADV corpus

Generated evidence: `local/corpus-manifest.json`.

### MTX

- PS2: 1,516.
- PS4 counterparts: 1,067.
- Byte-identical common: 1,022.
- PS2-only: 449.
- English-mapped PS2 files: 1,028 / 100,398 official DC entries.
- Exact + English-mapped: 985 / 78,314 entries.
- Structurally changed + English-mapped: 43 / 22,084 entries.
- Common but English-unmapped: 39.

Exact importer result:

- **962 files / 56,642 entries imported**;
- **23 files / 21,672 entries rejected fail-closed**.

Byte-identical source is not sufficient proof that every DC key is a literal byte offset. `FN/FN02_31.MTX`, for example, is only 604 bytes while its English map has 1,294 entries/keys extending beyond the file. Such indirect/dynamic maps remain rejected until their semantics are modeled.

Changed-source importer result:

- **7 files / 2,284 official entries** fully proven and emitted: `DG13_02`, `FD00_31`, `FN13_16`, `ID00_21`, `ID00_26`, `ID00_41`, `MS05_03`.
- `DG13_02` transfers all 577 official entries.
- the consolidated FD00 family is not solved generically: only `FD00_31` passes; 25 other mapped template files are rejected.

### KSF

- PS2: 1,516.
- PS4 counterparts: 1,067.
- Byte-identical common: **1,010** (correct count; do not revive exploratory 1,019).
- PS2-only: 449.
- English-mapped: 164 / 1,089 official entries.
- Exact + mapped: 144 files.

Conservative fixed-field importer:

- **868** fitting entries patched;
- **48** overflows left untouched;
- **4** ambiguous entries left untouched.

Overflow relocation remains unproven. Searching overflow keys as common LE/BE integer widths found no simple KSF-local reference table, but that is not proof that following data can be shifted safely.

## PS2-only translation-size proxy

A deterministic CP932 lexical-run scan reports:

- 41,337 unique Japanese runs across all PS2 MTX;
- 568 unique runs appear in PS2-only files;
- 149 of those also occur in mapped common content;
- only **419 novel PS2-only runs / 3,672 Japanese characters** remain by this proxy.

This is not a line/word percentage; ASCII controls split MTX text and presence in a mapped file does not prove every occurrence is localized. It does show that the 449-file count dramatically overstates unique PS2-only writing.

## MTX text encoding

MTX combines Japanese text and an ASCII-like command language. The port therefore converts printable English ASCII to the game's two-byte CP932/full-width glyph bank. Straight apostrophe maps to the proven right-quote glyph; em dash maps to CP932 horizontal bar. Every emitted dialogue glyph must occupy exactly two CP932 bytes.

`SYSFONTALL.FNT` and `ADVFONTALL.FNT` already contain Latin letters/digits, so no new glyph drawing is required for ordinary Latin text.

## Runtime ROFS table — critical discovery

The first broad whole-game candidate failed in runtime even though ISO9660 pointed to translated files. `SLPM_665.11` contains a separate ROFS table used by the game for CVM reads. For the proven record layout:

- byte size is at `filename_offset - 14`;
- sector extent is at `filename_offset - 6`.

Example: pristine `DG00_00.MTX` is size 5,852 at extent 320192. The failed builder moved the translated 9,956-byte file to extent 1008110 but left the executable table unchanged, so the game loaded the stale Japanese copy.

The generic builder now patches ISO9660 and ROFS together and then re-opens the finished image to prove every overlay asset resolves through the executable to the same final size/extent/payload.

## Title renderer and exact labels

Runtime proved the title renderer consumes two-byte glyph units: writing 8/9 single-byte ASCII characters produced roughly 4/5 meaningless glyphs. A later constrained wide label `NewGame` rendered but was visibly clipped.

Static reverse engineering then found a safe 40-byte source arena at `0x5CBDE8..0x5CBE10`. The current startup patch stores exact two-byte `New Game` and `Load Game`; `Load Game` moves to `0x5CBDFC` and its pointer is repointed. The third title pointer and following blank string remain untouched.

v11 ownership tracing ties the title menu backing to the bounded `m_title.c` sprite table rather than the generic text renderer. File `0x5CBE60..0x5CBFB4` is exactly 17 20-byte `(group,index,depth,x,y)` records from groups 88/91, copied and instantiated by the title-state constructor. Records 11 and 12, at `0x5CBF3C` and `0x5CBF50`, are the only two `(88,12)` instances and resolve to `GRP088/GP088_12.TMX`. They are placed at `(64,296)` and `(376,296)`, while the two title-label anchors are `(68,299)` and `(380,299)`: the same `+4,+3` inset for both menu choices. The title state initializes both backing instances with X scale 0, attaches the same scale-animation helper to them immediately before constructing the two label objects, and later presents both at X scale 1.

A fuller trace also disproved the earlier `(2,0x8E)` backing hypothesis. The label renderer does create one `(2,0x8E)` sprite before its `(2,0x8C)` glyph loop, but state 3 repeatedly updates that object's X coordinate as text reveal advances. It is therefore a moving reveal marker, not the static `New Game` / `Load Game` backing. v11 Task 5 operates on the paired `(88,12)` / `GP088_12` owner and preserves neighboring title records. Full bounded evidence is recorded in ignored `local/title-layout-v11.json`.

## Name/profile startup flow

Executable data contains the pre-dialogue prompts, protagonist/default names and name keyboard. Proven startup patches cover:

- last/first-name prompts and reading prompts;
- confirmation (`Is this fine?`, `Yes / No`);
- license verification messages;
- first-dungeon label `Heracleion Shrine`;
- protagonist/default names (`Habaki`, `Kuro`, `Hiyuu`, `Tatsuma`), with kana readings suppressed like the official English remaster.

The keyboard consists of 14 fixed 48-byte rows. Runtime input logic copies two bytes per selected cell; each logical row has 20 selectable cells arranged as four groups of five with non-selectable visual spacers. The English port therefore keeps two-byte glyph geometry and replaces kana with Latin lower/uppercase letters, digits and punctuation.

## Name-entry control graphics

The visible Japanese button/control labels on the name-entry screen are not executable text. They are baked into:

`BLBRD/B_GP019.BIN`

with entries:

- `GRP019/GP019_00.TMX` — 32×32, 4-bit indexed;
- `GRP019/GP019_01.TMX` — 512×512, 8-bit indexed.

Official English artwork is in PS4 bundle `BLBRD/b_gp019_en` as `GP019_00` / `GP019_01` Texture2D objects. The port downsizes/requantizes them into the PS2 container without changing its 264,640-byte size.

Current local output SHA-256:
`529aa604ba3d1e987d062daceb3e8045566d47e43b81665f8d7fa9b831b01227`.

## Random opening quotations

The Japanese quotation shown before the title is not CP932 text. The title state machine computes a random index modulo 29 and loads:

`BLBRD/INIT_MES/TR%03d.TMX`

PS2 has exactly `TR000.TMX`–`TR028.TMX`:

- each 263,232 bytes;
- each standalone `TMX0`;
- 512×512;
- 8-bit indexed.

PS4 bundles `BLBRD/tr` and `BLBRD/tr_en` each contain 29 same-name 1152×1152 Texture2D objects. `tr_en` contains the official English quotations, including the Solomon Proverbs image Pablo encountered in the previous test.

All 29 English textures are now ported to same-size PS2 TMX files. `local/startup-quotes-report.json` records:

- 29/29 generated;
- all output sizes unchanged;
- maximum mean absolute RGBA error versus the downscaled official image: **0.5594/255**.

v7 runtime repeatedly showed the same quotation, but this is not an overlay duplication: the 29 generated TMXs have 29 distinct SHA-256 values. Static MIPS tracing at `0x2AD0B8` calls the game PRNG, divides by `0x1D`, and uses the remainder as the `TR%03d` index. Repetition is therefore a seed/runtime-behavior question, not a localization asset defect.

## Indexed TMX graphics format/tooling

Proven PS2 indexed formats:

- PSM `0x13`: 8-bit indexed, 256-color CLUT;
- PSM `0x14`: 4-bit indexed, 16-color CLUT.

`tools/tmx.py` parses named chunks inside billboard containers and standalone TMX. 8-bit CLUT logical/stored ordering requires the known middle-two-eight-color-block swap within each 32-entry group. PS2 alpha is converted to/from the 0x80-scale representation.

`tools/graphics_port.py` uses optional Pillow to resize RGBA artwork, quantize to the target palette size, and rewrite only palette/pixel data. Structural metadata and file/container size are asserted unchanged.

## Broader localized graphics inventory

Official English artwork is packed in Unity AssetBundles under `Media/StreamingAssets/BLBRD`. `AssetFileDic_en.txt` has 1,167 pairs: 1,127 file-like mappings plus 40 logical bundle aliases. Thirty-nine English bundle files are physically present and expose 1,181 Texture2D objects in aggregate.

Across a matched `B_GPxxx` sample, 235/246 same-name assets are exactly 2.25× PS2 dimensions in both axes; 11 are special layouts. Startup proves the normal PS4 Texture2D → PS2 indexed-TMX path, but broad graphics still require per-group validation for outliers.

## Save system

The executable contains `BISLPM-66511Save` and normal memory-card paths. Normal memory-card saves are the compatibility target across builds; savestates are build-specific. A real create-save/load-save cross-build test is still pending after startup runtime acceptance succeeds.

## Startup v5 runtime result — renderer classification

v5 passed its static data checks but failed the runtime acceptance scope. Runtime proved:

- quote TMX backports work;
- title wide strings work;
- B_GP019 English graphics work;
- the wide Latin keyboard works;
- ASCII startup prompts/names are invalid for the name/profile renderer;
- ADV uses a vertical Japanese layout even when localized English data is loaded;
- H.A.N.T tutorial text is a separate executable pointer-table class.

This is why static byte-presence checks alone are insufficient: acceptance now verifies renderer-class transformations and still requires runtime proof.

## Name/profile wide-string relocation

The prompt table at `0x586AD0` points into `m_name.c` text around `0x5869C0`. Six official wide English prompts fit the verified `0x5869C0..0x586AD0` arena. The two longer reading prompts do not fit there together with the rest; v7 relocates `Enter reading for last name.` and `Enter reading for first name.` into the shared translation PT_LOAD and repoints prompt entries 2/3 there. Default/runtime protagonist name pointers are redirected to wide `Habaki`, `Kuro`, `Hiyuu`, `Tatsuma`; reading-value strings remain blank. The original runtime name records are preserved.

## ADV horizontal-renderer transform

Reverse engineering connected the script record writer and the ADV glyph-layout subsystem:

- record `+0x463` stores line index;
- record `+0x465` stores byte position within the line;
- the coordinate constructor at VA `0x24F9E0` consumes `+0x463` for the horizontal coordinate and `+0x465 / 2` for the vertical coordinate in the pristine Japanese layout;
- a second consumer at VA `0x24ED20` reads the same fields, but static tracing now proves that it gates glyph reveal/progress rather than computing X/Y coordinates.

v11 Task 2 traced the ownership chain rather than classifying by field pattern alone. The script-byte dispatcher at VA `0x215860` routes ordinary text through `0x24E690`; that driver calls wrapper `0x24E8A0`, which calls constructor `0x24F660`. The constructor computes glyph coordinates around `0x24F9E0`, creates the glyph/sprite objects, and registers callback `0x24E920`. The `0x24ED20` consumer lives inside that callback and compares line/position fields against reveal-progress state. Therefore exactly one known consumer is the ADV/DG layout owner: file `0x14FA60` / VA `0x24F9E0`; file `0x14EDA0` / VA `0x24ED20` is the progress gate.

The v6-v10 four-word patch targeted the correct constructor but contains a concrete sequencing defect. It changes the first load to `+0x465` and places `sra v1,v1,1` at VA `0x24F9E8`, **after** VA `0x24F9E4` has already copied `v1` into `f0` with `mtc1`. The float X calculation therefore receives the unhalved byte position. This explains why the static `adv_horizontal_layout` check could pass while the v10 DG00 runtime presentation remained wrong. v11 Task 3 fixes the proven constructor output sequence and does not mutate the `0x24ED20` progress gate.

The supervised v11 runtime then disproved a second assumption: even with the coordinate transpose, the old-man text remained vertical. Follow-up disassembly shows wrapper VA `0x24E8A0` passes one orientation argument through the DG object constructor, which creates **four** font canvases and forwards that same value to each canvas constructor. The r3 experiment cleared the flag only at one downstream canvas and therefore could not guarantee speaker/body canvases were horizontal. v11-r4 moves the fix to the unique upstream owner: file `0x14E96C` / VA `0x24E8EC` changes only `addiu a2,zero,1` to `addiu a2,zero,0`. All four canvases then inherit horizontal advance while the reveal/progress callback remains pristine.

`tools/adv_layout.py` fail-closes on the exact consumer and ownership-chain preimages. Detailed local evidence is emitted to ignored `local/adv-renderer-ownership-v11.json`.

## Executable translation segment / H.A.N.T. tutorial

The H.A.N.T. startup tutorial pointer table is at `0x5C8C70`. The pristine ELF's second PT_LOAD is zero-sized at virtual address `0x00902F00`; localization activates it as a reusable translated-text segment and reserves a 1 MiB VA window through `0x00A02F00`.

v7 runtime exposed an allocator invariant that the original implementation missed. The startup heap instruction and ELF heap metadata had been moved to `0x00A02F00`, but libkernel's live `sbrk` break word at file offset `0x650014` still contained `0x00902F00`. The allocator routine at `0x387E60` reads/advances that word, so normal allocations could overwrite the translation PT_LOAD. This explains the v7 reading prompt degrading from the statically correct full string to visible `Enter` and the later freeze. v8 validates and moves all known heap ownership sites to `0x00A02F00`.

The shared segment now carries H.A.N.T., the two overflow name-reading prompts, the proven subset of executable memory-card UI strings, and the ownership-proven long command labels. v11 Task 9 routes these through one `install_executable_text` call: entries retain explicit input order, each starts on a 2-byte boundary, pointer aliases cannot be double-owned, and callers must validate their source/pointer preimages before allocation. The H.A.N.T. table remains a structured entry patched with the final row VAs after that single PT_LOAD installation.

v11 Task 6 adds a bounded ownership inventory before expanding H.A.N.T. translation. The `0x5C8C70` table is exactly 17 slots: text at indices `0,2,3,4,7,8,9,10,12,13,14`, and blank/EOF control slots at `1,5,6,11,15,16`. A main-executable pointer scan also surfaces 10 additional CP932 strings containing the fullwidth `Ｈ．Ａ．Ｎ．Ｔ` token outside that table; they remain ownership candidates rather than being silently treated as tutorial text. Generic occurrences of words such as `情報` are not enough evidence by themselves.

The official remaster `English.bytes` corpus was not present at its expected local extraction path during this inventory pass. Following the fail-closed rule, text entries are therefore recorded as `unresolved` with `official_english: null`; no new English mapping is inferred from memory or from the already-patched runtime strings. The committed `translations/hant_ui.json` contains only the 17 proven tutorial slots, while the broader candidate evidence is kept in ignored `local/hant-inventory-v11.json`. The documented PS2 `方向キー` / remaster `方向ボタン` semantic join is implemented but only activates when a matching official corpus row is supplied.

v11 Task 7 traces the tutorial presentation path far enough to separate storage limits from visible geometry. Resolver VA `0x2A9FE0` reaches the startup tutorial through descriptor tuple `(mode=4,page=2,subpage=0)`; the leaf descriptor word is file `0x5CBAB0`, which points to the pristine table VA `0x006C8BF0`. This matters because the renderer's absolute source-index hooks at rows 5/7/18 belong to mode 2 and do not execute for the mode-4 tutorial. The mode-4 row walk is EOF-sentinel-driven and materializes at most 16 rows. Its parallel metadata owner is a separate 8-byte-record list at VA `0x006C8A20` with its own negative sentinel, so the text table is not required to retain one-for-one row alignment with that auxiliary data.

Each resolved H.A.N.T. row is copied through the bounded helper at VA `0x39FCC0` into a 64-byte staging field, so 32 two-byte English glyph cells remain the hard storage ceiling. Runtime v11 evidence established the tighter presentation boundary: style 0 advances 16 pixels per English glyph and only about 21 cells, roughly 336 pixels, were safely visible before right-side clipping. Disassembly also proves the separate `20.0` constructor argument is stored as text-object depth (`+0x30`) rather than glyph spacing, so r4 deliberately leaves it alone. The generic renderer already provides style 1 at 12×12; the mode-4 tutorial row loop selected style 0 at file `0x190968`. v11-r4 changes that one page-local style instruction to 1, giving a conservative `336 / 12 = 28` visible cells without changing global fonts or injecting a scale setter. Row Y remains `131 + 21*n`.

At 28 cells the accepted tutorial wording reflows into 14 rows rather than filling the 16-row cap. The controller holes land on rows 6, 9, and 12 at columns 10, 6, and 10. The parallel resolver at VA `0x2A9FA0` still owns the independent controller metadata list selected by file `0x5CBA60`; r4 regenerates that list as `(0,5,130,138)`, `(38,1,78,200)`, `(0,0,129,263)`, plus the unchanged negative sentinel, preserving each icon's offset relative to its placeholder while moving it with the new text row. The original 17-entry tutorial table and original metadata remain byte-identical provenance; only their leaf descriptors target the new 14-row-plus-EOF table and relocated metadata.

A separate trace resolves the Japanese H.A.N.T. chrome that remained visible in the v11 screenshots. Seven source strings are selected by one pointer table at file `0x586D20`; renderer VA `0x2881B0` indexes that table and passes the selected pointer directly to the text object at `0x2881C0`. r4 therefore relocates exactly those seven labels without changing action dispatch: `【Main Menu】`, `【Mail】`, `【Dictionary】`, `【Enemy】`, `【Memo】`, `【Help】`, and `【Config】`. The owned PS4 extraction does not contain the localized TextAsset/`English.bytes` needed to prove exact official wording, so these seven mappings are explicitly tagged `provenance="semantic"`; they are not represented as official-remaster text. Other Task-6 H.A.N.T. candidates remain unpromoted. Final-image acceptance adds `hant_tutorial_font_style` and `hant_chrome_labels` to the existing H.A.N.T. ownership/layout gates.

## Semantic command-menu label ownership

v11 Task 8 replaces the old tuple-only menu patch list with `MenuLabelSpec` records. The 19 known executable labels are all pointer-owned by one 21-entry command-label table at file `0x3BC8B0` / VA `0x004BC830` (two entries alias `Leave room`, two alias `Collection`). Renderer state paths at VAs `0x150C68` and `0x150FEC` load `table[command_id]` and pass that pointer to the text-object constructor at VA `0x1529E0`. The manifest therefore records the stable command-label id and every exact pointer-table alias for each source string rather than treating the source slot itself as its runtime owner.

A whole-ELF 32-bit pointer scan plus MIPS address-materialization scan proves the two overflow labels are relocation-safe at this ownership boundary. `地上へ脱出` / `Return above ground` has one consuming source pointer, file `0x3BC8F4` (command-label id 17). `成績表` / `Report card` has one, file `0x3BC8B8` (id 2); with ELF `gp=0x0079B1F0`, the compact-label GP-relative scan finds no direct source access. Neither source VA is otherwise materialized directly by code. They are therefore classified `storage=relocated,status=proven`. In v11-r4 the shared base payload also contains the seven H.A.N.T. chrome labels, so `Return above ground` starts at segment `+0xADE`, `Report card` at `+0xAF2`, and the final composite payload is 2814 bytes. The original compact source slots remain byte-identical provenance.

`メディア` is different: its runtime owner is proven as command-label id 12 / pointer file `0x3BC8E0`, but there is still no exact accepted official English mapping while `English.bytes` is absent. It remains `storage=pristine,status=unresolved` and cannot be redirected through `patch_menu_labels`. Full local scan evidence is written to ignored `local/menu-ownership-v11.json`.

## Startup v6 static candidate

Candidate: `/private/tmp/kowloon-recharge-startup-en-v6.iso`

SHA-256: `beaaa53bbfe3a60cd3af6749d4113cd4d91e81d804b122f80b85c347bded761b`

Evidence:

- 1,143 overlay files; 890 in place / 253 relocated;
- +900 embedded sectors; 17 shifted outer files remain byte-identical;
- 1,143 executable ROFS records patched/re-resolved;
- translated ELF size 8,401,977 bytes and remains at outer extent 288;
- final post-ROFS ELF SHA-256 `2dacea600e06c4db29311402ae5a1ae0880be23bfab2cfb3e8b0e1a811831922`;
- `tools/startup_acceptance.py` verifies final ISO bytes, not intermediate artifacts;
- `local/startup-acceptance-v6.json`: **96/96** final-image checks;
- Pillow-enabled suite: **121/121** tests pass.

v6 was subsequently runtime-tested after explicit approval. The opening quotation, title, name-entry English graphics, `Enter last name.` and lowercase keyboard were correct. Runtime then exposed: (1) the original two 3-glyph permanent-name fields, (2) unreachable uppercase rows because PS2 code only indexes keyboard rows 0..6, (3) a blank active reading-input state caused by v6 suppressing its prompt, and (4) an apparent freeze after completing that hidden flow.

Static tracing after that run proves R1/L1 changes the field-position cursor, not a keyboard page. It also proves the 3+3 limit is embedded in buffer sizes, field split/layout, append gates, and delete logic; it is not safe to solve by changing a single limit constant. v7 therefore restores both official reading prompts and folds uppercase into rows 0..6, but intentionally leaves 3+3 unchanged pending a buffer-safe direct-Latin design.

## Startup v7 runtime result

Candidate: `/private/tmp/kowloon-recharge-startup-en-v7.iso`

- SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`;
- static acceptance: **98/98**.

Runtime proved the uppercase-folding design: lowercase and uppercase are visible/selectable in the seven reachable rows. The original 3+3 permanent-name geometry remained. The next reading-input screen rendered only `Enter` even though the full official prompt was present in the final ELF, and finishing that state froze. The same run also exposed Japanese memory-card/title startup content.

## Memory-card executable UI

The startup stone-panel message belongs to a 27-entry executable pointer table at file offset `0x407440`. The observed entry is the PS2 memory-card-slot-1 checking state. `English.bytes` contains a structurally aligned official memory-card sequence (`Checking memory card slot 1`, `Loading...`, `Data loaded`, save/format/error prompts, etc.). v8 relocated the proven corresponding table entries into the shared translation segment, while eight re:charge-specific clear-data entries without proven official counterparts remained untouched.

The later log-confirmed v8 runtime still showed Japanese, proving table relocation alone was insufficient. Static reference tracing found two handler-local aliases of entry 1: file `0x4077F0` immediately precedes `H_BootMcardChk`, and file `0x4078D0` immediately precedes `H_EmptyMcardChk`; both pristine words are `0x00506AD0`, the VA of the entry-1 Japanese source at file `0x406B50`. v10 promotes this into a general rule: every proven alias of a relocated executable message must validate the same source preimage and move to the same translation-segment target.

## GP088 startup/title graphics

The red-sky/title startup scene uses `BLBRD/B_GP088.BIN`. The official English bundle `b_gp088_en` has a direct same-name/same-purpose counterpart for `GP088_03`. Static tracing also proved that title-state records instantiate sprite `(88,12)` twice and group 88 index 12 resolves directly to `BLBRD/GRP088/GP088_12`, so GP088_12 is a real startup renderer asset rather than a visual guess.

GP088_12 repacks the same two vertical title variants found in GP088_03. Alpha-layout alignment proves source boxes `(300,0)-(355,410)` and `(365,0)-(425,410)` at offsets `(-223,+14)` and `(-87,+14)`; with the flattened banner band `y=245..324` excluded, Dice scores are 0.8758 and 0.8765. v9 promotes that relationship into the generic `RegionTransfer` atlas-repack class. The original gold `re:charge` banner is flattened together with Japanese glyphs and has no clean source texture; the official English remaster GP088 art omits that banner, so v9 rebuilds GP088_12 transparently from only the official-English GP088_03 title regions rather than synthesizing missing art. GP088_13 is already an English `re:charge` badge and is unchanged.

## Startup v8 static candidate

Candidate: `/private/tmp/kowloon-recharge-startup-en-v8.iso`

- SHA-256: `7431f7f44eb9ed14927f2181491b02217efe8675c64c4c07789d13ad934aa550`;
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`;
- final ELF size: 8,403,943 bytes;
- 1,144 overlays; 891 in place / 253 relocated;
- translated ELF relocated by the tested builder from outer extent 288 to 1,013,782;
- 1,144 executable ROFS records patched/re-resolved;
- final-image startup acceptance: **120/120**;
- dependency-free suite: **126 tests OK** (6 expected skips);
- Pillow-enabled suite: **126 tests OK** (1 owned-corpus skip).

The final-image verifier now checks the live libkernel heap break, all eight name prompts, the proven memory-card English pointers/text, 32 startup graphics including B_GP020/B_GP088, H.A.N.T., ADV layout, ROFS resolution and the DG00 text/choice slice. Runtime proof remains mandatory.


## Startup v9 static candidate

Candidate: `/private/tmp/kowloon-recharge-startup-en-v9.iso`

- SHA-256: `6770862cbde8edf301afdef7778d440c0d2eab99806d732724afc6ef5a279d76`;
- same 1,144-overlay / 891-in-place / 253-relocated plan as v8;
- final ELF size 8,403,943 bytes, post-ROFS SHA-256 `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`;
- final-image startup acceptance: **121/121**, including a named GP088_12 chunk check;
- dependency-free suite: **130 tests OK** (8 expected skips);
- Pillow-enabled suite: **130 tests OK** (1 owned-corpus skip).

A later PCSX2 log proved the supervised runtime session actually booted v8. Because v8 and v9 share the same final executable SHA, the observed memory-card and name-flow failures apply to both executable builds; v9's GP088_12 graphics remain runtime-unproven.

## English name-flow transition

The normal PS2 name editor already handles both permanent fields: positions 0..2 are the surname and 3..5 the given name. After the normal-name confirmation, the dispatcher calls the same transition routine used after the reading pass. At file `0x186A68` state 9 supplies flag `0` (`0x0000282D`) immediately before `jal 0x285E20` at `0x186A6C`; at file `0x186A8C` state 11 supplies flag `1` (`0x24050001`) before the same call at `0x186A90`. Flag 0 builds the PS2 kana-reading editor; flag 1 follows the existing commit/finalization path.

The reading editor is semantically Japanese-specific: it is backed by `name/namedic.bin`, and its character classifier accepts the pristine kana readings while Latin test values such as `Hab`/`Kur` classify as having no valid reading characters. The official remaster deletes/suppresses the kana reading defaults (`@D`), which matches the existing English executable patch that redirects the reading buffers to the module's blank wide string. v10 therefore patches only the state-9 flag word from 0 to 1 and validates all four dispatcher words before doing so; it does not weaken the kana validator, alter buffer sizes, or synthesize phonetic readings.

## Startup v10 runtime-tested checkpoint

Candidate: `/private/tmp/kowloon-recharge-startup-en-v10.iso`

- SHA-256: `24d425433af97b1617e820cac05aa2a4d9389aa9fa19c1767a57eb763812da8e`;
- final ELF size 8,403,943 bytes, post-ROFS SHA-256 `e276442dc435034c59d471f6aad4b1eab7c0a4679f68717d4a3a5a3808b345a0`;
- same 1,144-overlay / 891-in-place / 253-relocated geometry as v9; 1,144 ROFS records patched;
- +900 embedded sectors; 17 shifted outer files; final ISO size unchanged;
- final-image startup acceptance: **123/123**, adding named checks for both entry-1 boot aliases and the name-flow skip-reading instruction invariant;
- dependency-free suite: **134 tests OK** (8 expected skips);
- Pillow-enabled suite: **134 tests OK** (1 owned-corpus skip);
- a second build from the pristine ISO has the same SHA-256 and is byte-for-byte identical.

Runtime evidence now establishes the v10 presentation baseline. Proven observations: the startup/name flow advances into the first old-man scene; opening quotations vary across restarts; `New Game` / `Load Game` text is correct but exceeds the original purple backing; the first old-man DG00 content is English but still rendered vertically; H.A.N.T. is partially translated and clips; menu labels are mixed translated/awkward/unresolved; and the structural 3+3 name behavior remains.

v11 Task 2 resolves the two-consumer ambiguity. Proven static ownership is: file `0x14FA60` / VA `0x24F9E0` is the ADV/DG glyph-layout constructor path, while file `0x14EDA0` / VA `0x24ED20` is the registered glyph-progress gate. The call/data chain is `0x215860` script-byte dispatcher → `0x24E690` message driver → `0x24E8A0` wrapper → `0x24F660` constructor; the constructor registers `0x24E920`, which contains the progress consumer. Exactly one consumer is therefore classified `dg_dialogue`.

The v10 runtime failure does not disprove that ownership: the old four-word patch itself is malformed. Its `/2` normalization at VA `0x24F9E8` executes after `mtc1` at VA `0x24F9E4`, so the float X calculation still receives unhalved byte positions. v11 Task 3 patches only the proven `0x24F9E0` layout output sequence and leaves the progress gate unchanged.


## Startup v11 static/deterministic candidate

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11.iso`

- SHA-256: `4150414b817fe54cf90ac28887568a37c6910995d7f8bc46e6887a6c4f6ef516`;
- translated ELF SHA-256 before ROFS rewrite: `edfca4471122c3f05c35c23a0d8c728ff45cc207b021ea2efca8af02c7003fac`;
- final ELF size 8,403,944 bytes, post-ROFS SHA-256 `9771bd9c031d7bcdb5e716c458d059feac6bdb2e31dd2fca6f4de7ca7f38e088`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 executable ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; final ISO size remains 2,095,382,528 bytes;
- final-image startup acceptance: **130/130** (`local/startup-acceptance-v11.json`);
- dependency-free suite: **177 tests OK** (8 expected skips);
- Pillow-enabled suite: **177 tests OK** (1 owned-corpus skip);
- independent repeat build has the same SHA-256 and is byte-for-byte identical by `cmp`.

The original v11 executable encoded the first renderer-ownership pass but its supervised runtime disproved the ADV-orientation and H.A.N.T.-geometry assumptions. It remains historical evidence rather than the current candidate.

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r4.iso`

- SHA-256: `3566b2395165cf4ba4b34ebed874ba405f17c0d452753786cfc116ed80c494bb`;
- translated ELF SHA-256 before ROFS rewrite: `4501cee41d3941d40c687f9806b51aa0196f6c206132fd6614f3bbe8ee461a43`;
- final ELF size 8,404,046 bytes, post-ROFS SHA-256 `54690aed73a68d19e8b1fcd787e346086fbd3bb30dd9dea9b39b99acf93d3d9f`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 executable ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; final ISO size remains 2,095,382,528 bytes;
- final-image startup acceptance: **132/132** (`local/startup-acceptance-v11-r4.json`);
- dependency-free suite: **182 tests OK** (8 expected skips);
- Pillow-enabled suite: **182 tests OK** (1 owned-corpus skip);
- `/private/tmp/kowloon-recharge-startup-en-v11-r4-repeat.iso` is byte-for-byte identical by `cmp`.

r4 preserves the accepted title/tablet geometry and changes only the four active defect owners: license-completion X, upstream all-canvas DG orientation, H.A.N.T. tutorial style/reflow, and the seven pointer-owned H.A.N.T. chrome labels. The memory-card wrapping experiment is not included. PCSX2 has not been launched for r4, so all four remain static/deterministic candidate fixes pending supervised runtime proof.


## Startup v11-r5 correction evidence

The r4 screenshots split the remaining defects into separate owners. The old-man body path was horizontal, but the speaker label still advanced vertically. Static tracing identifies a second constructor in the speaker state machine at VA `0x251470`: it reads speaker state from global `+0x444`, creates the speaker canvas through VA `0x18BF10`, then writes the resolved speaker text at VA `0x2516A8`. File `0x151608` / VA `0x251588` passes `a2=1`; r5 changes only that word to `a2=0`.

H.A.N.T. row Y is owned independently of its 12px font style. VA `0x2907E4` / file `0x190864` materializes the page-local 21.0f stride used by `Y = 131 + stride*row`. r5 changes only that constant to 18.0f and recalculates the three controller metadata records from the pristine 21px source geometry to the 18px target geometry. The 15 visible Help index strings are separately owned by the contiguous pointer table at `0x587840..0x587878`; r5 promotes those exact aliases to semantic English and removes only that now-proven owner from the unresolved H.A.N.T. set.

The six H.A.N.T. main-menu tile captions are not executable strings. The six-item sprite loop uses group `0x14`, indices `0x10..0x15`, and extraction proves `BLBRD/B_GP020.BIN` / `GRP020/GP020_03.TMX` is the baked atlas containing `ヘルプ`, `コンフィグ`, `メール`, `用語辞典`, `敵`, and `睡院メモ`, plus `初期設定に戻す`, `削除`, and `ページ`. The current owned PS4 extraction does not expose a localized GP020 bundle, so r5 uses a deliberately semantic indexed-pixel repaint. Nine exact source rectangles are SHA-256 pinned; only existing RGB `(19,204,58)` palette-family pixels inside those rectangles are cleared/redrawn. Pristine container SHA-256 is `9d1df3ecd45a1344b2517827636d2ce1a4f3fffd151292b6f4685b06f4f5b7a0`; generated local overlay SHA-256 is `d18a05bc7d3952a100c3c4f5efc499f076b9c92716a5c2942a3aab0f80ccebc7`; both are 1,054,208 bytes and exactly 5,646 bytes differ, all inside the declared caption regions.

The pre-title stone message keeps the previously proven memory-card entry/aliases but uses the existing executable line-break token to render `Checking memory card` and `slot 1` on separate lines. No memory-card table ownership changes.

The deterministic r5 candidate is `/private/tmp/kowloon-recharge-startup-en-v11-r5.iso`, SHA-256 `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`; pre-ROFS ELF `6e385c38fd012d8d11a5e3f0f20220412506ed6aa43b75b8bd712035365a28fa`; post-ROFS ELF `c3b228c946df9bae9d8aec81058a04801de1483191c28d5077087e1d9c2d3eee`; **137/137** final-image checks; **191** tests in both suites (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip); repeat ISO byte-for-byte identical. Pablo subsequently runtime-tested r5: GP020 top-level tiles and the 12px/18px tutorial layout are good; the stone message is improved; title composition remains bad; the visible dialogue speaker remains structurally wrong despite a horizontal body line; and deeper H.A.N.T. labels remain Japanese.

## Startup v11-r6 ownership corrections

r5 runtime disproved the assumption that file `0x151608` alone owned the visible inline speaker. The DG dispatcher recognizes the CP932 opening bracket `(0x81,0x79)`, routes through the speaker parser, stores the resolved name at global `+0x198`, and the live renderer at file `0x15007C` passes that exact buffer to the generic text constructor. File `0x15006C` supplies text mode `2`; constructor tracing shows mode `1` uses the same horizontal mesh path as ordinary dialogue while mode `2` takes the alternate path. r6 therefore changes only `0x15006C` from mode 2 to mode 1 and retains the r5 `0x151608` orientation change as a separate record-label owner. Both ownership chains are fail-closed.

The r5 title screenshot also disproved the `GP088_12` backing interpretation. `GP088_12` is packed title artwork, so horizontally scaling its paired instances distorts the composition. r6 restores the pristine `(1,1)` target and pristine third-object animation call. The two label anchors themselves are independently proven at X=68 and X=380. With 16-pixel two-byte glyph advance, `New Game` is eight glyphs and `Load Game` is nine; preserving the original Japanese label centers yields X=36 and X=340. r6 mutates only those two anchor words and leaves the packed title art scale untouched.

H.A.N.T. deeper-page tracing found three distinct presentation owner classes beyond the runtime-good GP020 atlas/tutorial. The Help category renderer indexes a three-entry label table at file `0x587288`. A separate descriptor vector at `0x587890` selects three sibling Help topic tables at `0x587430`, `0x587690`, and `0x587840`, totaling 55 labels. Config uses its own nine-entry live table at `0x586EF0`. r6 relocates exactly these proven aliases to semantic English while preserving source bytes and menu actions. The owned PS4 extraction still lacks the localized text corpus for these PS2 owners, so none of these mappings is represented as official-remaster wording.

Further inventory deliberately remains fail-closed. The 20-entry ringtone-title table is live-owner proven but contains music/proper titles without owned official English provenance; dictionary kana/index tables and mail subjects are content rather than simple chrome; the enemy category table was located statically but its executable owner was not proven in this pass. They remain untouched.

Historical deterministic r6 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r6.iso`, SHA-256 `dbd25ff8ada4724d6c280a32199dd3ef7fc49442923d904db56359ed02ef32a4`; pre-ROFS ELF `06b76b01e9ef1364f5c67473edaf1b68b367512ba0af7dd1ad533f726b64ecfa`; post-ROFS ELF `0fe52d198679c9c2eb4784cab12a554f4569488af018fd9778c3b72ca031b0eb`; size 8,405,736 bytes; **139/139** final-image checks; **198** tests in both suites (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r6-repeat.iso` is byte-for-byte identical and has the same SHA-256. PCSX2 was not launched by the agent for r6, but Pablo later manually tested r6; its presentation findings drive r7 below.

## Startup v11-r7 runtime-driven presentation corrections

Pablo's r6 runtime pass changed the ground truth again. The title labels were materially better but their black backing still did not cover the full English text; the stone tablet was translated but needed more centering/padding; name/license prompts were visibly off-center; dialogue still did not resemble the PS4 horizontal speaker/body block; H.A.N.T. deeper submenus were translated but the long submenu title looked awkward and the page rows were too loose. r7 treats those observations as the active presentation defects and keeps every r6 content/ownership win.

The r6 speaker change from text mode 2 to mode 1 was not the orientation owner. Static tracing of the exact bracket-derived call chain shows generic text constructor VA `0x190A50` overwrites `a2` with `1` immediately before font construction; the font constructor stores that value at the live font object's `+0x24`, and glyph rendering at VA `0x18DFFC` advances Y whenever that byte is nonzero. r7 replaces the hardcoded `a2=1` with `sltu a2,zero,s0`, where `s0` is the saved text mode, preserving pristine vertical behavior for every existing nonzero mode. Only the inline bracket speaker moves to direct mode 0, making its font orientation horizontal. Its fixed origin moves to X=20/Y=80 so it reads as a header above the existing transposed body origin X=20/Y=114. The separate r5 record-label orientation patch remains intact.

The body had a second independent spacing defect. After the r6 axis transpose, the body formula still multiplied the script byte-position by 26 pixels, the original Japanese column stride. The exact body-fragment constructor at file `0x14FB70` uses font style 1, whose profile at file `0x4D7884` is 12x12. r7 therefore leaves the proven `/2` byte-to-glyph normalization and coordinate transpose unchanged but changes only the live body X multiplier at file `0x14FAC8` from 26.0f to 12.0f. This removes the visible fragmentation without changing the reveal/progress gate.

The startup/name renderer uses one 16-pixel wide-glyph prompt object and repositions it by state before selecting from the prompt pointer table. r7 fail-closes and patches six exact X owners: last/first-name shared state to X=124, reading-prompt shared state to X=28, `Is this fine?` to X=152, `Yes / No` to X=192, `Verifying license ID...` to X=72 and `ID verification complete.` to X=56. The paired shared-state values are the midpoint of their two exact English centers, limiting either prompt to an 8-pixel center error; the single prompts are exactly centered in the 512-pixel logical view.

The pre-title memory-card owner is unchanged; only its already-proven English payload becomes `\n\nChecking memory card\n       slot 1`, adding one top row and horizontally centering `slot 1` beneath the 20-character first line. H.A.N.T. keeps the runtime-good 12px font but tightens only the page-local row stride from 18px to 16px; controller metadata is recalculated from the same source geometry. The proven three-tab Help category owner also shortens semantic `Exploration` to `Ruins`, while the 55 translated topic labels and nine Config labels remain unchanged.

The title was intentionally **not** changed in r7. Further tracing proves the title-state records at logical centers 100/412 own `GP088_09` and `GP088_08`; decoded `GP088_08` does contain large black alpha regions, but it is a multi-region title-chrome atlas rather than one isolated scalable backing. Without proving which subregion the live sprite samples, scaling or repainting it would repeat the r5 ownership error. r7 therefore preserves r6's X=36/340 label recentering and pristine packed-title scale; black-backing coverage remains a known runtime issue for a later atlas-region proof.

Current deterministic candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r7.iso`, SHA-256 `2b64165f820ec208ff9d721b9fbf30d8ee17bb78b9556e7ebe540c83b27221b4`; pre-ROFS ELF `318f666a1c7cb990ec2cec91be32513c9abd8ddb16f5da4ffe186cb3976cdf7e`; post-ROFS ELF `e520a919dd7e2a69c148f4cbe317b8f3ef2d729faa6f36e529a6b536b929b4bc`; size 8,405,744 bytes; **140/140** final-image checks; **199** tests in both suites (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r7-repeat.iso` is byte-for-byte identical and has the same SHA-256. PCSX2 has not been launched for r7; runtime success remains Pablo's gate.

## Startup v11-r8 runtime-polish ownership

Pablo's r7 runtime test narrows the remaining presentation work to geometry. Name/license centering is accepted and frozen. Dialogue orientation is now proven correct at runtime: `[Old man's voice]` renders horizontally with brackets and the 12px body spacing is readable. The remaining dialogue mismatch is vertical location. r8 therefore leaves every r7 orientation/stride instruction intact and changes only file `0x150050` (speaker Y 80→276) and file `0x14FA78` (transposed body base Y 114→312). This places the block near the lower remaster-style dialogue area while retaining X=20 and the existing reveal logic.

The boot tablet has no independent proven X/Y instruction owner in the handler aliases; they are message-pointer records. r8 therefore performs the minimal safe vertical adjustment in the already-proven English message itself: one additional leading line break. The centered seven-space `slot 1` line is unchanged.

Title backing ownership is now isolated in `GRP088/GP088_08.TMX`. Its pristine lower region is an exact 70x22 dark strip at x1..70/y25..46, followed by a six-pixel transparent gap and a small green trailing marker at x77..82/y29..35. That width matches four 16px Japanese glyphs plus six pixels of chrome. r8 extends only that lower strip to 150px (nine English glyphs × 16 + 6), preserves the unrelated 470px upper strip, and moves the existing marker to x157..162. The transformation is fail-closed and changed 923 bytes only inside `GP088_08`; the r7 `GP088_03` and `GP088_12` chunks remain outside this transformation. Finished-ISO inspection confirms the expected 150px strip, six-pixel gap, and shifted marker.

Current deterministic candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r8.iso`, SHA-256 `c2905f8bf1ebe20defb5479591c0dbf86b2e9bfbf9c6062db37ccf6f8ba6593f`; pre-ROFS ELF `62d68ec47255d37eb372f75d074815159b352367096e488247d699ed54043200`; post-ROFS ELF `d19d03a728aba3fff0102b076cc53d045e3329de7b421b4ef4c8ec54a5eb5712`; size 8,405,750 bytes; **140/140** final-image checks; **201** tests in both suites (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r8-repeat.iso` is byte-for-byte identical. Pablo later runtime-tested r8: the tablet and speaker/name placement were accepted, while the title backing remained too short and the dialogue body remained too far below the speaker. Those findings drive r9 below.

## Startup v11-r9 runtime follow-up

r8 runtime supplies two useful measurements. First, the speaker/name at X=20/Y=276 is now visually correct and must not move again, while the body at Y=312 starts too far below it. With the existing 18px speaker line, moving only the body base to Y=300 gives a compact header/body separation without touching horizontal orientation, reveal logic, or the proven 12px body stride.

Second, r8 proves the `GP088_08` lower dark strip is live because widening its source pixels changes the title backing, but 150 texture pixels still render substantially shorter than the 128/144 logical-pixel English labels. The runtime screenshot is consistent with roughly half-width presentation of that strip. r9 therefore doubles the target to 300 texture pixels (about 150 logical pixels), keeps the six-pixel texture gap, and relocates the exact existing trailing marker to the new edge. The unrelated 470px upper strip and accepted title art remain untouched.

Current deterministic candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r9.iso`, SHA-256 `0abe223df878c181da784247fe112553abe030a4f7db240f972285b5aa7696d0`; pre-ROFS ELF `06e364c79be9db69a6b0490d0a2368725ea29d29753aa68e5cd5370a812bf2ca`; post-ROFS ELF `61520a390a50de641096514fe219062f7059a382b3e1a6b9cc231ba4069c3ee6`; size 8,405,750 bytes; **140/140** final-image checks; **201** tests in both suites. The repeat ISO is byte-for-byte identical. PCSX2 has not been launched for r9.

## Startup v11-r10 runtime-root-cause corrections

r9 runtime disproves the remaining two geometry assumptions and reveals one confirmation-selection assumption. The title texture extension was not the final presentation constraint: the title label renderer itself constructs two black/chrome primitives using a hard-coded 64px half-width before VA `0x188AD0`. The same path proves a 16px glyph advance. Therefore `New Game` is exactly 8×16=128px and `Load Game` is 9×16=144px, while the pristine primitive is only 128px wide. r10 changes only those two renderer half-width constants from 64 to 80, producing a 160px backing: 16px side padding around New Game and 8px around Load Game. The accepted X=36/340 text origins and packed title art stay unchanged.

The name confirmation renderer has a separate selected-state path. Its Japanese Yes branch highlights the first three child slots and then resets child 2 because the original visible sequence placed the separator there after a two-glyph Yes. With English `Yes / No`, spaces allocate no glyph children, so the visible child sequence is `Yes/No`: child 2 is `s` and the separator is child 3. That exactly matches r9 runtime, where focused Yes leaves only the middle `e` clearly visible. r10 moves the selected-Yes X from 208 to the accepted English prompt X=192 and resets child 3 instead. The accepted focused-No X=272 is explicitly pinned unchanged.

The r9 dialogue screenshot proves the previous body-Y patch changed the wrong operand. At file `0x14FA68..0x14FA8C`, the live formula is `39 - line*114`: 39 is the row-zero base and 114 is the signed Japanese column stride. r8/r9 changed 114, so line zero necessarily stayed near the top. r10 changes the transposed formula to `300 - line*16`, preserving the accepted speaker X=20/Y=276, horizontal orientation, reveal path and 12px horizontal body glyph stride.

Measured r10 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r10.iso`, SHA-256 `a4f629fb22b2b095fe374eab384d86365ff881038fc37d4fa1e590297d5f928d`; pre-ROFS ELF `711ddca9d7813efaf34fc9788407fd0245a198b3ac8d08e925b851051c7b30c5`; post-ROFS ELF `76f335855ce03615f216cff575dfa63ff978b46660b7380d5954825499425a10`; size 8,405,750 bytes; **141/141** final-image checks; **205** dependency-free tests. The repeat ISO is byte-for-byte identical. Pablo later runtime-tested r10: the confirmation-focus fix is accepted, while the title-backing and primary-body owner hypotheses are disproven and drive r11 below.

## Startup v11-r11 owner corrections after r10 runtime

r10 runtime accepts the confirmation-focus correction but disproves its other two presentation hypotheses. The generic text-canvas 64→80px constants at file `0x19AB38`/`0x19ABD8` do not control the visible title backing, and the later ADV fragment formula near `0x14FA70`/`0x14FA78` does not control the visible primary dialogue body. r11 restores/pins both disproven sites to pristine and traces the actual owners instead.

For the title, the two title-state records `(group 88,index 12)` at file `0x5CBF3C`/`0x5CBF50` resolve through the group-88 resource table (VA `0x485240`) to metadata VA `0x478720`. That metadata selects texture ordinal 8, `GRP088/GP088_08.TMX`, with pristine geometry width 72, height 24, U extent 72/512, and V extent 24/64. The Japanese four-glyph label is 64px wide, so the 72px backing establishes 4px side padding. The longest English label, `Load Game`, is 9×16=144px; preserving that padding yields a shared 152px backing. r11 changes width 72→152, U 72/512→152/512, and moves the two backing left edges 64/376→24/336 so their centers remain aligned with the accepted English labels at X=36/340. The shared reveal-animation scale and separately repacked `GP088_12` title artwork remain untouched.

For dialogue, r10 runtime proves the later `39 - line*114` loop is a secondary fragment path rather than the visible primary body origin. Static tracing reaches the upstream wrapper at VA `0x24E8A0`, which supplies base X=90/Y=20 to constructor VA `0x24F660`. That constructor creates three primary body canvases at X=base, base-39, base-78 with common Y=base. r11 transposes that Japanese column geometry into English rows: wrapper base X=20/Y=300, then row offsets 0/16/32 produce primary origins X=20,Y=300/316/332. The already-proven secondary axis transpose and 12px style-1 fragment spacing remain intact, as does the runtime-accepted speaker/name at X=20/Y=276.

Measured r11 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r11.iso`, SHA-256 `c99f43b6f4047f63d3b0f4fd228fb893556933d3c1a65cb46e112ba6395325de`; pre-ROFS ELF `2776fe5598074dea7f72faf941130e4fe623d9bc11c79bd6a3bc862df95d6646`; post-ROFS ELF `5db2a259210ccb0ad8ca68047b5102c9b52301ba4d99c18af75fa7e7b130382c`; size 8,405,750 bytes; **141/141** final-image checks; **205** tests in both suites. The repeat ISO is byte-for-byte identical. Pablo later manually runtime-tested r11 and accepted its title/backing and ADV presentation corrections; that runtime pass also proved that H.A.N.T. selected Help bodies are not owned by the translated topic-label tables.

## H.A.N.T. selected Help-body ownership after r11 runtime

The r11 runtime observation is now reproduced statically. The Help list renderer around VA `0x28C65C..0x28C69C` uses the descriptor vector at file `0x587890` only to select one of the three topic-**label** tables (`0x587430`, `0x587690`, `0x587840`). Confirming a topic follows a different path: the Help handler around VA `0x28D210..0x28D24C` calls the generic page constructor with `(mode=4, category, topic)`.

The selected body and auxiliary metadata are separate three-level pointer trees. Text resolver VA `0x2A9FE0` indexes root VA `0x006CBAC0`; metadata resolver VA `0x2A9FA0` indexes root VA `0x006CBAA0`. A new bounded inventory follows exactly the proven Help cardinalities—20 ADV topics, 20 Ruins topics, 15 Other topics—for **55 selected-body leaves**, requiring every text table to reach the `0x00795FBC` EOF sentinel and every metadata list to reach a negative sentinel.

This model explains the runtime exception exactly. `HELP → OTHERS → H.A.N.T Functions` is `(4,2,0)`: text descriptor file `0x5CBAB0` resolves to file `0x5C8C70`, the same tutorial table already translated and runtime-accepted. Its metadata descriptor is `0x5CBA60`, resolving to the three-record controller list at `0x5C8AA0`. By contrast, neighboring `Command Thumbnails` `(4,2,1)` resolves through descriptor `0x5CBAB4` to a separate 55-row Japanese table at `0x5C9180` plus two metadata records, so its English menu label never implied an English selected page.

The first safe body expansion is `HELP → OTHERS → About the Shop` `(4,2,5)`. Its text descriptor is file `0x5CBAC4`, pristine seven-row table file `0x5C9B80`, metadata descriptor `0x5CBA74`, and metadata leaf `0x698968`. That metadata leaf begins with the negative sentinel, so the page has no controller/icon records to realign. r12 preserves the Japanese source table, strings, metadata descriptor, and metadata sentinel byte-identically, writes a new word-aligned EOF-terminated English table into the shared translation PT_LOAD, and redirects only the proven text descriptor. The owned PS4 extraction still lacks `English.bytes`, so this new wording is explicitly `semantic`; no official-remaster wording is claimed.

Measured r12 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r12.iso`, SHA-256 `ef65129b13b9b49a705a03bc8d83d434a16c76915d5024da597ba1f559f96916`; pre-ROFS ELF `3faa98a1585bc0d55ffb41a5dfbc6cbf8ae3cb0c03742dc7214fcd5f5e21407a`; post-ROFS ELF `3844b03e7fc5bc0d9464a3e9d9d256b0c7b6783c1aa90ff09afd32d83e3cf8f0`; size 8,405,990 bytes; **142/142** final-image checks; **208** tests in both suites. `/private/tmp/kowloon-recharge-startup-en-v11-r12-repeat.iso` is byte-for-byte identical. Pablo later runtime-tested r12 broadly: everything before H.A.N.T. and the H.A.N.T. main/navigation remained accepted, while its screenshots exposed the Japanese H.A.N.T.-internal content owners that define r13. `About the Shop` itself was not explicitly reported in that pass.

## Startup v11-r13 H.A.N.T. runtime-content expansion

Pablo's r12 screenshots preserve the entire pre-H.A.N.T. acceptance baseline and the H.A.N.T. main/chrome/navigation presentation, but isolate multiple independent Japanese content datasets. The selected bodies for `ADV Controls`, `Exploration Controls`, and `Moving in Ruins` are separate mode-4 body leaves at `(4,0,0)`, `(4,1,0)`, and `(4,1,1)`. Their pristine body descriptors/tables are respectively `0x5C4390/0x5C2E30`, `0x5C8A50/0x5C4650`, and `0x5C8A54/0x5C4B20`. Unlike `About the Shop`, these pages carry 8, 14, and 34 controller/icon metadata records. r13 preserves every metadata descriptor and record byte-for-byte, preserves the original row cardinality, and redirects only each proven text descriptor to an English table in the shared PT_LOAD.

The same runtime pass proves Config labels alone are insufficient. The live Stereo/Mono aliases are at file `0x6958C8/0x6958CC`; Japanese/English values are at `0x6958E0/0x6958E4`; and the 20-entry ringtone table at file `0x5871E0` is referenced by two code paths materializing VA `0x00687160`. r13 translates all of these values semantically, with ringtone labels constrained to at most 14 English cells to avoid replacing Japanese with clipped English.

The empty Mail state has one proven alias at file `0x695BD8` pointing to source `0x589960`; r13 redirects it to `No mail received.`. Enemy's L1/R1 category selector is the three-entry table at file `0x5899F8`, whose live renderer materializes VA `0x00689978`; r13 relocates exactly those three aliases to `Small`, `Large`, and `Human`.

Dictionary presentation splits again into index tabs, selectable term lists, and definition pages. The ten kana index aliases at file `0x5878C0` are directly referenced by renderer materialization of VA `0x00687840`; r13 changes them to `A/K/S/T/N/H/M/Y/R/W`. The ten term tables contain **208 real selectable entries** plus placeholder slots. r13 redirects only those 208 real pointers to semantic English/romanized names and leaves every placeholder pristine. To avoid committing bulk Japanese source text, the manifest pins each original NUL-terminated CP932 source by file offset and SHA-256 plus the exact pointer-table offset. The definition page selected after choosing a term is a separate 208-leaf descriptor class and is intentionally not claimed translated by r13.

Measured r13 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r13.iso`, SHA-256 `53bf85f051ff3f3c8714e41be134dbd5fa9fcd0fd4ba2e3bd58091bf2acc1648`; pre-ROFS ELF `a0b9b3fcb83c6579d5d2f93ab74749636d62fd0cb7aae7f8b0bd5a365d15b2bf`; post-ROFS ELF `062d0380ba7f8ee094ac4230799ffee5a4f1029b7230734bca2caafd9d4b6b6f`; size 8,414,614 bytes; **146/146** final-image checks; **212** tests in both suites (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r13-repeat.iso` is byte-for-byte identical. PCSX2 has not been launched for r13.


## Startup v11-r14 H.A.N.T. runtime-layout and Dictionary-detail repair

Pablo's r13 runtime screenshots prove the translated owners are live but separate text ownership from presentation ownership. The three promoted Help bodies render English, while their controller/icon metadata still follows the pristine Japanese 21px row / 16px glyph grid. r14 relocates each non-empty Help metadata leaf and applies the same measured transform used by the English text: 21→16 vertical spacing and 16→12 horizontal advance, preserving icon kind/variant and terminating each relocated leaf with the original negative sentinel.

Config and Dictionary list/tab rows still pass style 0 into their text constructors at file offsets `0x18BC84`, `0x18BF14`, `0x18E2CC`, and `0x18E408`; Enemy uses style 0 at `0x195D5C`. r14 changes only those proven call-site arguments to existing style 1. Enemy's three category X owners at `0x195CB4/0x195CD0/0x195CEC` are widened from the r13 40px cadence to a non-overlapping English layout. Empty Mail is a fixed fifth row, so r14 uses the observed row geometry instead of treating it as an arbitrary centered string and separately retargets the direct LUI/ADDIU count/status label at `0x1936C0/0x1936C4` to `Mail (New)`.

The r13 runtime pass also proves Dictionary term lists and selected definition pages are separate content classes. The observed `King Akhenaten` and `Heracleion` pages resolve through descriptors `0x5AB380` and `0x5B9780` to independent EOF-terminated row tables. r14 promotes only those two observed leaves, preserving every Japanese source row/table as provenance. r14 then made an incorrect renderer inference: `0x190968` is the already-proven mode-4 H.A.N.T. body-row style owner, while `0x190A40` is a distinct singleton constructor in that same mode-4 function. Changing `0x190A40` to style 1 causes the r14 `H.A.N.T Functions` blank/trapped-state regression. r15 restores and fail-closes `0x190A40` pristine. The two definition table relocations remain valid ownership-wise, but their actual font-style owner is unresolved; the other 206 definition leaves remain fail-closed and untranslated.

Measured r14 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r14.iso`, SHA-256 `2d543df1367dea4b9b9b31d77cf246d959f2e5c0b23a8726e6b001be611ce795`; pre-ROFS ELF `29be2791d014be9730d5d8107d8d3c4990132bf3fd6d25c227fc6a97b768c08a`; post-ROFS ELF `36ac6bfa4e0b995bc94163e728eaa5787110d17f250777c52ccf602830676041`; size 8,416,234 bytes; **150/150** final-image checks; **214** tests in both suites (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r14-repeat.iso` is byte-for-byte identical. PCSX2 has not been launched automatically for r14.


## Startup v11-r15 H.A.N.T Functions recovery after r14 runtime

Pablo's r14 runtime pass preserves the entire pre-H.A.N.T. baseline and main H.A.N.T. menu. It also validates most of the Help metadata geometry change: Exploration's ordinary icons/text are aligned, and Moving in Ruins is acceptable. Two defects remain in the reviewed scope. First, the Exploration night-vision warning icon overlaps its English text because the translated rows removed the Japanese two-cell gutter. r15 keeps the r14 icon metadata transform and changes only those three rows to reserve two leading cells; each remains within the 28-cell English budget.

Second, and more importantly, `H.A.N.T Functions` is blank in r14 and entering it can leave the entire H.A.N.T. UI blank/trapped on return. Diff isolation shows the only new r14 mutation inside the already-runtime-proven `(4,2,0)` mode-4 H.A.N.T Functions renderer is `0x190A40: move a1,zero -> addiu a1,zero,1`. That word sits in the same function as the accepted row constructor at `0x190968` but creates a different singleton object. r14's Dictionary-definition attribution is therefore rejected by runtime evidence. r15 leaves `0x190968` style 1, restores `0x190A40` to pristine style 0, and makes pristine preservation of `0x190A40` part of both source validation and final-image `hant_tutorial_font_style` acceptance.

Measured r15 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r15.iso`, SHA-256 `e4cf331c90470e99c2c0db1728673a7ddcdab358182f8d1ba7927b6dbbf387f6`; pre-ROFS ELF `dcdd2f0c4a22bb74f280ec285fc43a061dd475c07ce10a00e31498849a274f86`; post-ROFS ELF `306cfa21e720328c269c505995c5041b0d4b77496329ecbf22bdf14b5eef1a68`; size 8,416,238 bytes; **150/150** final-image checks; **215** tests in both suites (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r15-repeat.iso` is byte-for-byte identical. Runtime acceptance is pending.


## Startup v11-r16 H.A.N.T. completion pass after r15 runtime

Pablo's r15 runtime pass confirms the r14 emergency regression is fixed: `H.A.N.T Functions` is visible/usable again, ADV Controls is good, Moving in Ruins is acceptable, Config is perfect, and all pre-H.A.N.T./main-H.A.N.T. accepted presentation remains intact. Four reviewed defects remain: the final Exploration warning icon is still slightly too close to its copy; Mail is translated but its header/count line and empty state are misaligned; Dictionary's top tabs overlap L1/R1, its `No data.` state is off-center, and opened definitions such as Cairo are Japanese/misaligned; Enemy categories overlap the L1/R1 row.

r16 traces each as a separate owner. Exploration changes only the final metadata record by -6px X. Mail's Japanese `通（未読　　通）` source is a count suffix with two externally rendered numeric cells, not a free-standing title; r16 therefore uses `msgs  new` while preserving the two count positions and adjusts the empty text padding. Dictionary tabs retain style 1 but change their proven origin/advance owners to 260px/14px. Enemy keeps the proven X/style owners and moves the category row to y=110.

The Dictionary detail path is independently proven as mode 1/category/term-index through the generic three-level resolver. The complete owned PS4 package was extracted read-only and yielded `English.bytes` SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`. All 208 selectable PS2 definition leaves enumerate safely; all 2,073 nonblank Japanese source rows have exactly one official English match and zero ambiguous/missing matches. `tools/generate_hant_dictionary_definitions.py` generates 208 records with per-page source fingerprints and deterministic official English reflow. The final corpus contains 4,177 display rows at <=21 cells each. No shared detail-font mutation is introduced: `0x190A40` remains pristine, preserving the r15 H.A.N.T Functions fix.

Measured r16 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r16.iso`, SHA-256 `7669e50ddd81778e48e15c1f85f8ac4ff56a7d9e4e6c330c58ab9ae3b7bd8b9b`; pre-ROFS ELF `f8c90885dfd9050570fd5b70db6fbf5b890915e6469128996ab89cfa7ac86106`; post-ROFS ELF `bb4bcb3640616cb33de351b3735cfacb25376e7e4e56601113956e8dc85df752`; final ELF size 8,563,534 bytes; **150/150** final-image checks; **217** tests in both suites (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip). `/private/tmp/kowloon-recharge-startup-en-v11-r16-repeat.iso` is byte-for-byte identical. Runtime acceptance remains Pablo's gate.


## Startup v11-r17 Dictionary/Enemy runtime-polish trace

Pablo's r16 runtime pass narrows the remaining scope to Dictionary and Enemy. Cairo, H.A.N.T, Heracleion and Rosetta Society prove the 208-page official Dictionary corpus is live, but their body rows expose Japanese-layout blank separators inside English prose and their selected title/icon chrome collides with the longer `【Dictionary】` label. Dictionary root tabs are translated but remain visually off. Enemy's lower category row no longer collides vertically with L1/R1, but the three English labels are shifted right. Everything else is accepted/frozen.

Disassembly isolates each owner. Dictionary tabs use fixed L1/R1 anchors around x=195/x=407; ten 12px glyphs on the accepted 14px cadence occupy 138px, so x=232 centers the strip with equal 37px gutters. Selected detail title/icon coordinates are not metadata leaves: the generic renderer reads a per-mode integer table at VA `0x00688C00` (file `0x588C80`) in exactly two X paths. Mode 1 currently contains `6`, yielding roughly icon x=179/title x=197; changing only file `0x588C84` to `8` moves both +32px and leaves the generic constructor plus runtime-critical `0x190A40` untouched. Sampled Dictionary metadata leaves are immediate sentinels, confirming no page-specific icon metadata needs relocation.

The r16 definition generator preserved every Japanese blank row as a paragraph boundary. Runtime shows that assumption is wrong for remaster English: it can split phrases such as `world heritage` / `city`. r17 therefore wraps the first nonblank official fragment as the title, emits one separator, joins every remaining official fragment into one body paragraph, then deterministically wraps at <=21 cells. All 208 source fingerprints and all 2,073 exact official row matches remain unchanged; output falls from 4,177 to **3,827** display rows.

Enemy disassembly shows the three patched immediates are not final X positions: the renderer adds a fixed 21px afterward. r16 bases 209/289/369 therefore rendered at 230/310/390. r17 uses bases 189/269/349, producing visible starts 210/290/370 and a centered 210..430 block while preserving the accepted y=110/style-1 owners.

Measured r17 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r17.iso`, SHA-256 `728f9eae1d7dd2f69009732ff8c880585db1c6cde41d120358e04362428276dc`; pre-ROFS ELF `68ab06d3b2b51dbcdc8853944c04eadd0c165009afed488dfe158a167e0ca6f2`; post-ROFS ELF `ee24bb03984c7be760f398f01128faa65c02925552283c0ac9a6bc48dfd125a0`; final ELF size 8,562,126 bytes; **150/150** final-image checks; **218** tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip). The repeat ISO is byte-for-byte identical.


## Startup v11-r18 correction after r17 runtime

Pablo's r17 screenshots prove the official Dictionary body reflow is live, but disprove both r17 chrome-clearance calculations. The top A/K/S/T/N/H/M/Y/R/W strip still begins behind `【Dictionary】`, and selected titles such as `H.A.N.T` still occupy the same chrome region. Mail remains fully translated but its empty message is visibly off-center; Dictionary `No data.` is likewise off-center. No new runtime defect was reported for the r17 Enemy row, so r18 leaves Enemy unchanged.

The missing constraint is the translated chrome itself. The live H.A.N.T chrome renderer starts the current page label at x=75 in style 0. `【Dictionary】` is twelve 16px glyphs and therefore ends at x=267. The Dictionary index renderer remains style 1 with 12px glyphs and a proven 14px cadence. Starting the ten tabs at x=268 occupies through x=406 (`268 + 9*14 + 12`), clearing the English chrome by one pixel and ending one pixel before the fixed R1 anchor near x=407. r17's x=232 centered only in the L1/R1 span and therefore necessarily overlapped the longer English chrome.

The generic selected-detail renderer uses the mode table at VA `0x00688C00` / file `0x588C80` in exactly two X paths. Mode 1 file `0x588C84` originally contains 6, matching six 16px glyphs in Japanese `【用語辞典】`. English `【Dictionary】` has twelve glyphs, so the bounded Dictionary-only correction is 6→12, not r17's 6→8. This yields approximately icon x=275/title x=293 and leaves the generic constructor and runtime-critical `0x190A40` pristine.

The Mail empty alias (`0x695BD8` → source `0x589960`) and Dictionary empty alias (`0x695968` → source `0x5878F0`) are set on shared row objects whose X constructors also serve ordinary non-empty content. r18 therefore does not move those shared constructors. It removes Mail's guessed two-cell prefix entirely and reduces Dictionary's guessed ten-cell prefix to five style-1 cells, limiting the adjustment to the observed empty states. Exact visual centering remains a runtime gate rather than a static claim.

Measured r18 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r18.iso`, SHA-256 `136a528030ab5ce611efd67fd06cf637f9015e1ba3473f760f9a6e72d7754c9a`; pre-ROFS ELF `64c220490e64da7e6d50d8d76ebd0f9e60cc94c42cbc6414605ba258bd71fad1`; post-ROFS ELF `a61b72b35d95112f68e79f1d1f1f1c36a77a1ab454ff714514694e540799f74a`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **218** tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip). The repeat ISO is byte-for-byte identical. Runtime acceptance is pending.


## Startup v11-r19 root-navigation and Mail centering trace

Pablo's r18 runtime pass accepts Cairo, H.A.N.T and Heracleion selected Dictionary pages, proving the r18 mode-1 offset `0x588C84 = 12` and r17 definition-body reflow; both are frozen. The remaining observed defects are `No mail received.` centering plus Dictionary and Enemy root top-row composition.

Disassembly resolves Mail first. The ten Mail rows are constructed at a shared x=143 owner (file `0x193564`) before the empty-state branch assigns `No mail received.` specifically to row 4. There is no independent empty-row X immediate. Style-0 English is 17 glyphs × 16px = 272px, so x=(512-272)/2=120 is the exact viewport-centered origin. r19 patches that constructor 143→120 rather than reintroducing string padding.

Dictionary root has independent L1/R1 objects (files `0x18E1A4` and `0x18E1EC`) plus the ten-tab cadence/origin owners (`0x18E398`/`0x18E3AC`). r18 moved only the tabs, but the 192px English `【Dictionary】` already extends through x=267 while pristine L1 begins at x=195. r19 therefore composes the complete row: L1=274, tabs begin x=302 at 12px cadence and span through x=422, R1=428. Selected Dictionary page ownership is untouched.

Enemy root has the same structural error. r17 moved category labels to y=110 while L1/R1 remained on the y≈91 header, which r18 runtime still reports as visually wrong. Disassembly proves L1 x=260 at file `0x195BCC`, R1 x=407 at `0x195C14`, category bases at `0x195CB4/0x195CD0/0x195CEC`, and category y at `0x195D18`. r19 restores the pristine y=93 row and composes L1=194, category visible starts 226/292/358 (bases 205/271/337 plus the renderer's fixed +21), and R1=428.

Measured r19 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r19.iso`, SHA-256 `4dbce7f49d537e6cc6aa156ff6d4723596de31b3a8657caa83a4b0a40db81928`; pre-ROFS ELF `c8795405f9746db2ba260c4fe644ee45218d200232112496f4ad6f1f58ba50b3`; post-ROFS ELF `d34d53d62b6236d1c1b87577704bbd2eb8d84945564216750df74347e82a7cef`; **150/150** final-image checks; **218** tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip); repeat build byte-for-byte identical. Runtime acceptance is pending.


## Startup v11-r20 Dictionary/Enemy selection-box trace

Pablo's r19 runtime pass accepts all other reviewed work, including Mail centering and Dictionary detail pages. The remaining red-box mismatch is not text geometry. Dictionary's animated selector updates object `0x14` from current category `c8` with pristine `x = 223 + 18*i`, while the pristine tab text is `225 + 18*i`. r19 moved text to `302 + 12*i` but not this animation owner. r20 therefore preserves the original two-pixel inset with selector `300 + 12*i` (file `0x18DFD8` base and `0x18F7B4` cadence).

Enemy has the same independent owner. Its selected category at struct `0x130` recreates the red object using pristine `x = 288 + 40*i`; Japanese category text begins at `292/332/372`, proving a four-pixel inset. r19 English text is frozen at `226/292/358`, so r20 changes only the selector to `222 + 66*i` (file `0x195F30` base and `0x195F28` cadence). r19's Enemy R1 x=428 is runtime-clipped, so r20 restores the independently owned R1 constructor to pristine x=407.

Measured r20 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r20.iso`, SHA-256 `374a8813fcf10d148c35b9e0e47be6d1d943ebf447752ed461f4a0fb17884ebd`; pre-ROFS ELF `30333e4d488714d2639b67c07da4ea76a4afd4b70e92ecc02f446421dd6850f9`; post-ROFS ELF `e4aa7717fe11111a7a82c07595a3d6e5088c2fc3b93dd4af2cb23610666bca83`; **150/150** final-image checks; **220** tests in both suites; repeat build byte-for-byte identical. Runtime acceptance remains Pablo's gate.


## Startup v11-r21 selector-resource sizing trace

Pablo's r20 screenshots promote the selector X formulas themselves: both red boxes now track the selected text. The remaining mismatch is intrinsic sprite geometry. The generic sprite constructor at VA `0x107D60` receives group 20 for both controls. Group 20 resolves through executable resource-table entry file `0x385310` to VA `0x00482E50`. Dictionary index `0x21` has the unique table record at file `0x382FD8`, resolving to metadata VA `0x00464B30` / file `0x364BB0`, count 1; its rendered width is the second metadata word at file `0x364BB4`, pristine `24.0`. Enemy index `0x41` likewise resolves through file `0x3830D8` to metadata VA `0x00465730` / file `0x3657B0`, count 1; width file `0x3657B4` is pristine `40.0`.

That ownership exactly explains both runtime symptoms. Dictionary tabs are style 1 at 12px cadence, so a 24px red frame spans two tab cells even when its X coordinate is correct. r21 changes only width 24→14px and preserves the complete UV rectangle byte-for-byte; the same red-frame texture is scaled rather than sampling neighboring atlas pixels. Enemy's five-letter names require 60px in the accepted 12px style, so the 40px frame cannot contain them. r21 keeps style 1, changes the frame width 40→64px with identical UVs, packs text starts to 220/282/344, and tracks them with the original four-pixel leading inset at 216/278/340. `Human` then ends at x=404 before the runtime-good R1 x=407.

Measured r21 candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r21.iso`, SHA-256 `08a9781ecfec5096f3d50769fabb686d7d8fa2cc82dcdca003e687dd05f9aaa7`; pre-ROFS ELF `457e2c149493f01a7ffcea7cc896af9b4296a8e587f17cb3e67edbb1ad1bb3cd`; post-ROFS ELF `b2a70936d57c6750f1f54ad19d1f398a11e6c0f2444bf3edb30cfd6e99c81616`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **222** tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip); `/private/tmp/kowloon-recharge-startup-en-v11-r21-repeat.iso` is byte-for-byte identical. Runtime acceptance remains Pablo's gate.


## Startup v11-r22 selector padding trace

r21 runtime proves selector ownership/positioning correct but shows asymmetric padding: Dictionary uses 12px glyphs inside a 14px box at x=text-2, leaving 2px left/0px right; Enemy uses 60px labels inside a 64px box at x=text-4, leaving 4px left/0px right. r22 fixes only this symmetry. Dictionary width becomes 16px, preserving x=300+12*i and UVs. Enemy width stays 64px while selector base moves 216→218, preserving cadence 62, text 220/282/344 and R1 x=407. Result is 2px padding on both sides in both families.

Unlock behavior: these selector fixes apply automatically to every item using the same family renderer/resource. Dictionary's ten root categories and mode-1 detail path are shared, and all 208 definition leaves are already generated. Enemy's Small/Large/Human root selector is shared. Separate H.A.N.T/help body tables remain independent and require their own promotion if still unresolved.

Measured r22: ISO `1b3a9c916ec8436af94f702138efbdde3028158c4af256ba517293a2f3f2f009`, pre-ROFS ELF `60122115b3109f0acfc0c4f895a6fa79eb18fda7a3ff7d645310c050a7cab75d`, post-ROFS ELF `f1f6c68345e806296702fdd2f290b7cfbfb602dbe00992cd62819fe2954ec8ea`, final ELF size 8,562,114 bytes, **150/150** final-image checks, **223** tests in each suite, repeat ISO byte-identical.


## Startup v11-r23 final H.A.N.T. header-clearance trace

Pablo's r22 runtime screenshots leave only two header-edge defects. Dictionary repeats the already-proven Enemy clipping class: its independently owned R1 constructor is still x=428, so r23 moves only file `0x18E1EC` to x=424 while freezing tabs, selector base/cadence/width, detail offset `0x588C84 = 12`, and pristine `0x190A40`. Enemy's first selector is already correct at x=218 with width 64, but L1 remains x=194; the shared navigation footprint reaches into the selector. r23 moves only file `0x195BCC` to x=190, leaving category text 220/282/344, selector `218+62*i`, and R1 x=407 unchanged.

Regression coverage is strengthened at the same boundary: `tests/test_startup_acceptance.py` now tampers every offset in `HANT_RUNTIME_LAYOUT_PATCHES` and requires the `hant_runtime_layout` final-image gate to fail, so all completed Config/Dictionary/Enemy layout owners remain fail-closed as the project continues.

Measured r23: ISO `4465f4322fc252d1fa0cf734fc4c63697c38adbda155a90eadcaca37698a55c5`, pre-ROFS ELF `564c4268faf7f7224bc5a4dc1d67c758a2af003f2c5487a4056af8d537a2041f`, post-ROFS ELF `4b59521acbfc96b68a6a934a7eb2442b8e426288714065f96f1980aeff3516f8`, final ELF size 8,562,114 bytes, **150/150** final-image checks, **224** tests in each suite, repeat ISO byte-identical.


## Startup v11-r24 Dictionary right-navigation clearance

Pablo's r23 runtime pass promotes Enemy's complete reviewed header geometry: L1 x=190, labels 220/282/344, selector x=218+62*i at 64px, R1 x=407, y=93/style 1. r24 freezes those exact values in a dedicated regression test.

Dictionary shows the same monotonic right-edge response as the previous round: R1 x=428 clipped more; x=424 clips less while all tabs/selector/detail paths remain correct. r24 therefore repeats the smallest proven correction and changes only file `0x18E1EC` from runtime x=424 (`0x240201A8`) to x=420 (`0x240201A4`). No other Dictionary or H.A.N.T. owner changes.

Measured r24: ISO `46112aaaefb80a317dec4bed36e526d3e9f05f780dd435b4ecb0516c85e304d0`; pre/post-ROFS ELF `2242f5472f9ab228c51da4f776eb011e47b2facbfec02baf64159f3be71be58f` / `930770fdad8ac71d1291e250400e467c0258cc57a1176f1bc330aa09e8de88e5`; **150/150** final-image checks; both suites execute **225 tests**; repeat ISO is byte-identical.


## Startup v11-r25 Dictionary/Help final-layout trace

Pablo's r24 runtime screenshots preserve Enemy as accepted but expose two remaining presentation classes. Dictionary R1 still clips at x=420; because the tabs and 16px selector are otherwise accepted, r25 avoids another isolated R1 nudge and moves the whole root-navigation cluster left four pixels: L1 x=274→270, tab base x=302→298 at 12px cadence, selector base x=300→296 at the same cadence/16px width, and R1 x=420→416. Detail-mode offset `0x588C84 = 12`, pristine `0x190A40`, the 208 generated definition leaves and selector UVs remain unchanged.

Help tracing identifies separate owners rather than reusing Dictionary/Enemy geometry. Topic text constructor file `0x18C674` and category text constructor `0x18C7F8` are still style 0; r25 changes both to existing style 1. The shared topic selector is group-20 index `0x22`, table file `0x382FE0` → metadata file `0x364BE0`, count 1, with pristine width 168px at `0x364BE4`; the longest translated topic is `Emotion Input Controls` at 22 style-1 cells = 264px, so r25 widens only that rendered width to 268px for 2px padding on both sides and leaves UV bytes unchanged. The three category tabs instead use group-20 index `0x32`, table file `0x383060` → metadata file `0x364EE0`, width 72px. That width stays pristine; only the category composition moves eight pixels left, yielding selector x=192/261/330 and text x=202/263/340, so the final box ends at x=402 before R1 x=403. Enemy's accepted r23 geometry is explicitly regression-frozen and receives no r25 mutations.

Measured r25: ISO `8cd3e369c08f8c29609c54236e73bfb06bf62b1c9aaaa9b0529fd08a17aec6c4`; pre/post-ROFS ELF `4100ea75fd1d82819521279fbf8edfc8038f6ec0dc852e68309896db6f47ed1b` / `d0dfaa4390d6aaba4162b6a5115dfc4fb0b9e40d533737911d4c29557c6c86d5`; **150/150** final-image checks; **226** dependency-free tests (10 skips); **226** Pillow-enabled tests (1 skip); repeat ISO is byte-identical.


## Startup v11-r26 final Dictionary/Help shoulder-clearance trace

Pablo's r25 runtime screenshot narrows the remaining defects to two geometry edges. Dictionary is otherwise accepted but the complete header is still slightly too far right; because r25's rigid four-pixel shift preserved all internal alignment, r26 repeats that exact operation once: L1 270→266, tabs 298→294 + 12*i, selector 296→292 + 12*i at 16px, R1 416→412.

Help exposes the opposite failure mode. r25 moved the 72px category-selector family from x=200 to x=192 so `Other` would end at x=402 before R1, but that also moved `ADV`'s left edge into L1. The selector resource is shared, so r26 restores base x=200 and reduces width 72→64px: positions 200/269/338 still end at 264/333/402. The 12px labels are aligned at selector+2 (202/271/340); only `Ruins` needs to return to its pristine X base for that alignment. This fixes both left and right shoulders without touching selector cadence, R1, the 268px topic selector, Help bodies, or Enemy.

Measured r26: ISO `189434d74b98fe2b1cacb4e1a2edfad9ac6943e12b6e8b655c4a4c4884fd57b0`; pre/post-ROFS ELF `fc001382a330a43313098adf3f70dfeec4fc1d77f2e93284de2d72cd39dcf940` / `572ff87377d3c2692309da36689b38c107988eaf8442fb510f9b034d3678b7c2`; **150/150** final-image checks; both suites execute **227 tests**; repeat ISO is byte-identical.


## Startup v11-r27 final Help category-owner trace

Pablo's r26 runtime screenshot resolves the remaining Help defect without changing selector geometry. The prior static attribution was backwards: the r26 mutation at `0x18C768` visibly moved `Ruins`, proving that owner belongs to `Ruins`; `0x18C778` is therefore the `ADV` X owner. r27 restores `0x18C768` to `0x3C02433D` and changes only `0x18C778` from `0x3C02437A` to `0x3C024372` (-8px). Selector base x=200, selector width 64px, `Other`, topic selector geometry and Help bodies remain unchanged.

The same runtime review promotes Enemy and Dictionary from candidates to accepted/frozen geometry. A dedicated r27 regression pins the complete accepted Dictionary header cluster and the Enemy shoulders/category/selector geometry so later Help work cannot move either family.


## Startup v11-r28 Help selector-width ownership

The r27 screenshots prove label placement is no longer the defect: all three category strings are accepted. Static tracing of the remaining red-box mismatch shows one shared group-20/index-0x32 metadata record (`0x364EE4`, 64px), so changing that width necessarily changes all categories together. The Help update routine at VA `0x28D924` computes selector X from the selected category and writes the sprite at `state+0x14`; generic sprite initialization stores X scale at object `+0x60`. Therefore r28 leaves the shared 64px resource and all label owners untouched, and supplies per-selected-category `(X, X-scale)` values instead. The chosen centered geometry is ADV x=204/scale=.75 (48px), Ruins x=257/scale=1.125 (72px), Other x=338/scale=1 (unchanged 64px). Both the helper cave and table cave are pristine inter-function zero padding and are included in fail-closed final-image layout checks.


## Startup v11-r29 dungeon HUD / SELECT text trace

Pablo's post-r28 runtime review closes the current H.A.N.T. polish scope: Help category alignment/boxes, Enemy and Dictionary are accepted and must remain frozen. A new complete-build regression asserts every `HANT_RUNTIME_LAYOUT_PATCHES` replacement after r29 composition so later non-H.A.N.T. work cannot silently move accepted H.A.N.T. geometry.

The SELECT-menu garbage is not a bad English mapping. The existing command ownership table is correct, but the previous implementation wrote ASCII into compact Japanese string slots. Runtime makes the encoding mismatch observable: `Items` becomes `ISdlR` and `Noise` becomes `NnhRd`, while uppercase `H.A.N.T` remains readable. Static tracing at VAs `0x150C68`/`0x150FEC` confirms the selected command id indexes the 21-entry pointer table at file `0x3BC8B0` and hands that pointer to the command text constructor. r29 therefore preserves all Japanese compact sources and redirects the 18 proven aliases to PS2 two-byte English in the shared PT_LOAD. `メディア` has no unique exact owned-remaster mapping and remains pristine.

The exploration-side moving HUD labels are a separate direct-code owner. `H_CmdIconDraw` materializes `調べる`, `アイテム`, and `ジャンプ` through file instruction pairs `0x4B654/0x4B658`, `0x4B680/0x4B684`, and `0x4B6AC/0x4B6B0`. Owned CUSA27034 `English.bytes` provides exact key matches `Examine`, `Items`, and `Jump`. r29 redirects only those LUI/ADDIU pairs to relocated wide text and verifies both code words plus source bytes fail-closed.

The battle/L1 path is data-driven instead. VA `0x134AB0` indexes a 500-pointer item-name table whose file base is `0x3912B4`; the returned pointer is passed directly into the HUD text constructor. Inventorying all 500 slots yields 446 nonblank CP932 names, 446 distinct source strings/offsets, and 446 unique exact Japanese-key matches in the owned remaster, with no ambiguity or unmatched promoted row. The generated manifest records item id, PS2 source offset, Japanese source, official English, and remaster record offset. r29 redirects exactly those 446 pointer words; blank/unproven slots are left unchanged.


Measured r29: ISO `1692b234b810bf966b94d0d3959abab07ad0c611bca469a5e022727eaac3de0e`; pre/post-ROFS ELF `8caddb81607bd1afe7d30344d2b4bc0e87e979e7df9bd8714bd2e18d27f41062` / `923bc218585f0b9d1ee1edb12ea73d5c04ca6447c653b6aff3b2b43fd30e754f`; final ELF size 8,573,437 bytes; **151/151** final-image checks; **234** dependency-free tests (10 skips); **234** Pillow-enabled tests (1 skip); repeat ISO is byte-for-byte identical. Runtime proof remains limited to the newly promoted SELECT/dungeon-HUD paths.

## Startup v11-r30 companion HUD trace

Pablo's r29 runtime pass accepts both dungeon action-menu sections and the SELECT/start menu as complete; those owners are frozen. The remaining Japanese companion HUD is not part of `H_CmdIconDraw`. `H_TalkBuddyTask`/`H_VoiceDraw` consume the `h_buddy.c` event table at file `0x3D3320`: 601 event records × 0x80 bytes, eight 0x10-byte slots, two optional text pointers per slot. Static inventory finds 1,784 live non-empty aliases referencing 1,650 unique CP932 source strings. All 1,650 sources resolve uniquely by Japanese key in owned CUSA27034 `English.bytes`; there are no unmatched promoted comment rows. The first pair, for example, maps `千年以上の昔、地震で水没した` / `伝説の古代都市ヘラクレイオン。` to `Heracleion flooded after an` / `earthquake 1,000 years ago.`.

The always-visible companion action caption comes from the 31-pointer table at `0x3F8D20`. 26 non-placeholder rows reuse exact PS4 strings; the screenshot-visible `石を投げる` maps to `Throw a Rock`. Four Re:charge-only labels have no exact PS4 key and are kept in a separately provenance-tagged semantic mapping. r30 redirects only these proven pointer owners into the existing wide-text translation segment, preserving all original Japanese source bytes and r29/H.A.N.T. geometry.


## Startup v11-r37 companion slot/action-id trace

Pablo's r36 runtime screenshot accepts the one-line `Throw a Rock` bubble visually. His follow-up question about the second companion slot exposed an ownership distinction that r36 had modeled incorrectly. At file `0x66674`, the renderer loads `lh v0,0x2d0(s0)`, shifts it left by three, and indexes VA `0x4F8E00` (file `0x3F8E80`). That table contains exactly two float pairs: `(172.0,407.0)` and `(230.0,407.0)`. Therefore HUD `+0x2D0` is the selected companion slot, not a 31-value action id.

The real action id is fetched later at file `0x66830..0x66840`: `ori a0,zero,0x8000`; `jal 0x0012FEE0`; `nop`; `andi v0,v0,0xffff`; `xori v0,v0,0x8000`. The result is then used to index the 31-pointer action-caption table at file `0x3F8D20`. r37 preserves the complete slot-position sequence and two-entry table byte-for-byte, and changes only the generic layout hook so it calls the same action-id getter before selecting the per-action layout row. Final-image acceptance now fail-closes both owner families independently.

## Re:charge companion free-talk / AFK owner (r43)

The passive free-talk path is **not** the 601-event `h_buddy.c` table used by r30. Pablo's runtime screenshot supplied the anchor: Salah's visible `む？迷ったかの？` is source file `0x3D20D0` (VA `0x004D2050`) and is referenced by record pointer `0x3F5028`. The enclosing owner is a fixed record pool from file `0x3E5FA0` through `0x3F8BA0` (exclusive), 600 records at 0x80-byte stride. Records are grouped exactly 20 per companion id for ids 1..30. Header `+0` is enabled (`1`), `+4` is companion id, `+8` is line-1 VA, `+0xC` is line-2 VA, and `0x00794150` denotes an empty line. There are 999 live fields and 952 unique source pointers.

This ownership was established from a real runtime string and fixed-stride data structure, not by scanning arbitrary aligned values. Do **not** resurrect the r41 whole-ELF value scan: it produced false positives in unrelated packed/ASCII data and broke the game. Do **not** relocate the shared group-2 resource table as r40 did. r43 patches only the structurally owned free-talk pointer fields and appends their English payload after all previously accepted translated entries.

## r44 AFK-visible state / L1 suppression trace

The same `H_TalkBuddyTask` that owns companion talk exposes a safe visibility discriminator. At file `0x66368`, the task compares `lh 0x04(s0)` with `0x259`. The current record index therefore distinguishes the 601 original `h_buddy` records (`<0x259`) from the Re:charge free-talk continuation (`>=0x259`). The native talk lifecycle stores its active render objects in `s0+0x20`, `+0x24`, `+0x28`, and `+0x2C`; these handles are created for the current record's speech/bubble presentation and cleared/destroyed when that presentation finishes.

The persistent L1 action renderer already has an ideal suppression owner at file `0x666BC`: `lw v0,0x2c8(s0)` followed by `beq v0,zero,0x00166814`, which skips the complete bubble/text construction path. r44 keeps that target and inserts a predicate only for the guard. The predicate first preserves the original `+0x2C8` result; for a Re:charge free-talk record it ORs the four speech handles and returns zero while any is live. No timer threshold or resource ownership is inferred. This avoids both rejected approaches: r40's shared resource relocation and r41's arbitrary aligned-word scan.

## r45 AFK composition / speaker identity trace

Pablo's r44 screenshots distinguish two colors: a green companion-shaped layer and a blue-tinted dialogue panel. Tracing the native free-talk selector shows that the AFK path itself owns both. The selector at file `0x67A80..0x67C68` receives slot 0/1, reads the companion id for that slot, computes `(companion_id-1)*20 + 0x259`, stores the selected companion id at `H_TalkBuddyTask+0x338`, then writes the chosen record index to task `+0x04` and state 9 to task `+0x02`. The AFK-specific text constructor calls at `0x6627C` and `0x6634C` load `lh a3,0x338(s0)`, so speaker identity is preserved all the way into presentation.

The task enters state 11 immediately after the AFK constructors complete (`0x66360..0x66364`). It subsequently transitions through the teardown path, sets state 13 around `0x664DC..0x664E0`, destroys/clears the presentation objects, and returns to state 8 around `0x6656C..0x66570`. Consequently the precise visibility window for suppressing the independent persistent action callout is `record>=0x259 && 11<=state<=13`; render-handle liveness is not needed.

AFK's static composition rows live immediately before the companion slot-position table. Slot 0 green: file `0x3F8E1C`, `(2,0x68,249,172,381)`. Slot 1 green: `0x3F8E30`, `(2,0x69,249,230,381)`. Slot 0 blue: `0x3F8E44`, `(2,0x6A,246,172,381)`. Slot 1 blue: `0x3F8E58`, `(2,0x6A,246,172,381)`. Resource `0x6A` is backed by group-2 table record `0x380E40`, metadata VA `0x00450B20`, count 3, with 0x30-byte frames at file `0x350BA0/0x350BD0/0x350C00`. Their pristine geometry is 288×56, pivot X=67, pivot Y=74/75/76.

r38's accepted action work compacted shared `0x68/0x69` bodies to 224px while preserving their distinct pivots/tails. Because AFK reuses those resources, its green body became compact while blue `0x6A` remained 288px, producing the mismatched stack visible in r44 screenshots. r45 corrects the paired AFK-only blue geometry to 224×56 / pivot X=52 / pivot Y=45/46/47. Slot 2 blue X becomes 185, exactly 13px right of slot 1, matching the compact body displacement; the green tails remain 58px apart and therefore visually identify the speaking slot.

Do not infer `0x6A` ownership from arbitrary immediate constants: raw immediate `0x6A` occurs widely in unrelated code. The meaningful ownership proof is structural. The exact aligned byte pair `(u32 group=2,u32 resource=0x6A)` occurs only at `0x3F8E44` and `0x3F8E58` in the pristine ELF, and no adjacent hard-coded `li a0,2` / `li a1,0x6A` resource-call signature was found. r45 fail-closes on these two placement records plus the metadata table/frames.

## r46 correction: native `0x6A` must remain untouched

Pablo's r45 runtime screenshot falsifies the r45 geometry hypothesis. Compacting the three `0x6A` metadata frames from 288px to 224px and shifting the second placement did **not** produce a smaller blue AFK panel; the blue panel disappeared. Therefore the decoded width/pivot floats are not sufficient evidence that this resource can be independently reshaped. The ownership trace remains valid, but the safe conclusion is now the opposite: native `0x6A` geometry and placements are protected bytes.

r46 keeps the structural ownership checks because they are still valuable: group-2 record `0x380E40` resolves to metadata VA `0x00450B20`, count 3; metadata frames begin at `0x350BA0`, `0x350BD0`, `0x350C00`; exact aligned `(u32 group=2,u32 resource=0x6A)` placement owners are `0x3F8E44` and `0x3F8E58`. But the build performs no write to any of those owners. Final-image acceptance verifies their native values rather than a translated target.

The native-state trace from r45 remains accepted for the next runtime test: free-talk selection writes a record index `>=0x259`, panel construction transitions `H_TalkBuddyTask` into state 11, teardown proceeds through states 12/13, and the task returns to state 8. The relocated L1 visibility predicate therefore remains `record>=0x259 && 11<=state<=13`. r46 proves this can be isolated from `0x6A`: compared with r44, every native `0x6A` byte is identical and only the predicate body differs.

This is now the preferred debugging rule for this surface: **do not reshape or relocate `0x6A` based only on decoded metadata**. If the native blue panel still needs later repositioning, first trace the runtime constructor/transforms that consume `0x6A` and observe a slot-specific coordinate owner; do not mutate its resource metadata speculatively.

## r47 shared-resource geometry and AFK text-fit trace

The original Re:charge composition resolves the green/blue geometry ambiguity. Green resource `0x68` is 288×80 with pivot `(67,77)` and green `0x69` is 288×80 with pivot `(125,77)`. Blue `0x6A` is 288×56 with pivot X=67. AFK placements are slot-0 green `(x172,pivot67)`, slot-1 green `(x230,pivot125)`, and blue `(x172,pivot67)` for both slots. All effective left edges are X=105. Therefore the blue panel already has the correct native body width; the green resource's extra 24px height is part of the outer speech/tail composition. The r38 static 224px compaction of shared `0x68/0x69`, not native `0x6A`, is what caused the AFK mismatch.

The safe architecture is per-consumer runtime geometry. Static `0x68/0x69` remain pristine. Normal L1 actions apply compact geometry just before their resource constructor. Re:charge AFK restores the selected slot to native geometry before its own resource construction. The AFK hook is inserted at file `0x66050`, where the original owner begins `lh v0,4(s0); sll v1,v0,7`; the `sll` is retained as the JAL delay slot and the helper reproduces both result registers on return. Native AFK slot selection is read from `s0+0x2F8` and validated to 0/1 before any metadata write.

AFK text metrics are also directly recoverable. Both specialized free-talk callsites set `f16=1.0` immediately before calling VA `0x001950A0`; lower constructor VA `0x00188AD0` stores `f16/f17/f18` consecutively at object `+0x28/+0x2C/+0x30`, while `f12..f15` feed position/transform fields. In the talk-task path only f16 is explicitly reset at those AFK callsites, which makes it the caller-controlled horizontal transform used by r47. Ordinary h_buddy text retains its original 1.0 setup.

The AFK text constructor uses style-0, whose renderer advance is 16px. Native AFK text X=117 and native body left X=105 establish a 12px left inset. Reserving the same 12px on the right gives 264px safe text width = 16.5 unscaled style-0 cells. r47 generates one horizontal scale per AFK record from the longest of its two translated fields: `min(1,16.5/longest_chars)`. Both row objects use the same value. This avoids changing translation wording, adding speculative line-break semantics, or depending on one companion/slot. The table covers all 600 records and acceptance verifies all 999 live fields against the bound.

Current scale distribution: 81 records remain at 1.0 and 519 scale below 1.0; minimum is 0.4342105263 for 38-character rows. This is intentionally horizontal-only: row Y positions and the untouched f17/f18 transform components remain native. If runtime readability of the longest lines is later judged too compressed, the next safe investigation is the AFK text object's actual newline/wrap support; do not mutate `0x6A` or shared geometry again to solve text length.

Compatibility rule: r47 extras are appended after the r46 visibility hook. The 999 AFK pointer targets and visibility-hook VA/content are unchanged r46→r47. The existing action hook keeps its VA and size; only its return tail changes into a jump to the appended compact-geometry extension. This preserves all historical translated addresses while separating AFK and L1 behavior at runtime.


## r48 correction: AFK caller f16 is alpha; object +0x48 is X scale

Pablo's r47 screenshot is decisive runtime evidence: the bubble geometry is corrected, but the AFK text disappears. Re-disassembly of the constructor chain explains why. At both specialized free-talk callsites, caller `f16` is loaded with 1.0 before `jal 0x001950A0`. Inside that constructor, the value is forwarded to the generic object constructor `0x00188AD0` as the fourth normalized color component. The generic constructor clamps the four color values to [0,1] and stores them as RGBA state. Therefore the r47 table values in f16 were changing alpha, not text width.

The real transform fields are object `+0x48/+0x4C`. The text renderer loads `+0x48` into `f29`; horizontal glyph-coordinate math multiplies by that value. It separately loads `+0x4C` into `f28`, which is used on the vertical path. This makes `+0x48` the correct, directly observed horizontal scale owner.

r48 keeps `0x6625C=0x3C023F80; 0x66260=0x44828000` and `0x6632C=0x3C023F80; 0x66330=0x44828000`, restoring full alpha for both specialized AFK rows. The post-constructor stores are the safe hook sites. Line 1 replaces `0x66284: sw v0,0x28(s0)` with JAL and moves that store into `0x66288` as the delay slot; the helper restores the displaced `lh v0,0x0A(s0)`. Line 2 does the same at `0x66354/0x66358`, restoring `v0=0x78` before native `sh v0,8(s0)`.

The existing 64-byte scale-hook allocation is sufficient and remains at VA `0x00949824` / file `0x849A74`. It preserves the returned text object in t3, derives the zero-based AFK record index, loads the existing r47 table word, writes it to `0x48(t3)`, and distinguishes the two continuation contracts from RA. This introduces no nested calls and touches only caller-saved registers.

Compatibility proof: r47→r48 changes no segment sizes and no relocated VAs. Scale table VA `0x00948EC4` is identical and its complete 2,400 bytes are identical. All 999 AFK pointer owners and all r47 geometry/resource/runtime helpers except the 64-byte scale-hook body are byte-identical. Do not reintroduce pre-constructor f16 scaling; f16 is now a protected alpha owner for this path.


## r49 trace: native newline + vertical AFK ownership

r48 runtime disproves horizontal scaling as the final solution: text is visible, but long English can still extend beyond the 288px bubble. The correct generic primitive is already in the game's text converter. At VA `0x00195A84` the converter compares the raw source byte to `0x0A`; on match, `0x00195A90` materializes `0xFF0E` and `0x00195A94` stores it as the internal command. This proves literal 0x0A is native multiline input for the same constructor used by AFK free-talk.

The AFK style-0 horizontal advance is 16px. Native text X=117 and body-left X=105 leave 12px on the left; keeping a symmetric safety margin gives 264px. r49 chooses 16 cells = 256px, leaving 8px additional horizontal slack. Wrapping is generic word wrapping plus hard splitting for a token >16 cells, so no source word can defeat the width bound.

Native line-1/line-2 Y coordinates are 313/331, proving 18px row spacing. The generic text object stores X/Y at +0x14/+0x18 and scale at +0x48/+0x4C. r49 leaves X and vertical scale native, forces horizontal scale +0x48 back to 1.0, and changes only object +0x18 Y after construction.

The speech resources can be extended upward without moving their lower anchors by increasing height and pivot-Y by the same delta. For green resources 0x68/0x69, native (height,pivot-Y)=(80,77), so height-pivot=3 remains constant. For blue 0x6A frames the native pairs are (56,74/75/76); each frame's height-pivot difference remains constant when both values receive the same delta. Width, pivot-X and placement X are untouched. Slot selection still comes from s0+0x2F8 and therefore the existing 67/125 green X pivots continue to identify the speaking companion.

The r49 geometry hook at the AFK pre-construction owner 0x66050 reads a 32-byte record from a 600-record table and writes only runtime height/pivot-Y plus the already-proven native width/X-pivot values for the selected green slot. It updates all three blue animation frames immediately before the AFK resource construction; static 0x6A bytes remain pristine. This differs materially from the rejected r45 experiment, which statically reshaped 0x6A including width/X geometry.

The current 600-record corpus produces 1..6 total rows. Maximum delta is 72px, but the algorithm has no row-count constant. Its real upper bound is the game's own 0x1950A0 source-buffer guard: converted source length must remain below 0x1FE bytes. The encoder therefore fail-closes at 0x1FD source bytes rather than pretending to support infinite text.

Compatibility trace: current English contains no token >16 cells, so every inserted line break replaces an existing space. Padding after the first NUL preserves every r48 relocation allocation size, which in turn preserves all 999 AFK pointer values and every older payload VA. The only newly appended runtime area is 19,496 bytes at the end of the prior translation payload: layout table VA `0x0094991C`, geometry-hook VA `0x0094E41C`, text-hook VA `0x0094E4D4`.


## r50 runtime geometry correction: embedded AFK rows and blue consumer ownership

The r49 runtime screenshots provide three independent observations that supersede the remaining r49 assumptions:

1. Native raw-newline wrapping is valid: the first screenshot shows r49 breaking long English into multiple visual rows rather than overflowing horizontally.
2. The **18px** difference between the original first/second AFK text-object baselines (313/331) is *not* a safe proxy for the visual advance of multiple rows rendered inside one object. In r49, later newline rows can descend below the blue/green body even when the first row is enclosed.
3. Green and blue speech resources are not safely modeled as one global geometry. In the accepted L1 action screenshot the green action bubble is already in the desired upper band, while blue `0x6A` remains behind at its lower AFK presentation.

r50 therefore treats placement and geometry as properties of the active **consumer**. AFK uses fixed 288px width and a runtime-calibrated 32px visual-row budget; L1 uses the already accepted 224px action geometry. Resource `0x6A` follows the same consumer switch rather than remaining permanently native-AFK-sized.

The static AFK placement table exposes the lower anchor directly: green slot records `0x3F8E1C/0x3F8E30` and blue slot records `0x3F8E44/0x3F8E58` are all Y=381 in pristine Re:charge. r50 moves all four to Y=346, matching the safe vertical band already demonstrated by the L1 callout. Slot-1 blue X also changes 172->230; runtime AFK blue pivot-X follows 67/125, so effective body-left remains aligned with the corresponding green slot. Static metadata bytes themselves remain pristine.

The record layout table remains 32 bytes per AFK record at the same translated VA. Its r50 values use:
- `line_step = 32`
- base green `height=80, pivotY=77`
- base blue `height=56, pivotY=74/75/76`
- base text baselines `278 / 310`
- `delta = 32 * max(0,total_rows-2)`

The AFK helper restores both layers together before construction. Green uses slot-selected metadata `0x00450AC4 + slot*0x30`; blue uses all three frames beginning at `0x00450B24`. Both receive native width 288, record-specific height/pivot-Y, and slot-specific pivot-X 67/125. Thus AFK remains slot-aware even though `0x6A` itself is a shared resource id.

The L1 extension does the inverse immediately before normal action construction. Green receives width 224 and pivot-X 52/97; blue frames receive the same width 224, the current action's calculated height/pivot-Y and the same slot pivot-X. This is necessary because the r49 screenshot proves leaving `0x6A` untouched causes its tinted body to remain in the wrong size/location while green moves correctly.

Compatibility result: r50 appends only 348 bytes and moves no prior translated VA. All 999 AFK structural pointers and all 999 relocated AFK C-string payloads are byte-identical to r49. The r49 text hook and native-newline payloads are also unchanged; r50 is geometry-only with respect to translated dialogue content. The classified r49->r50 common-prefix audit reports zero unexplained bytes.

## r51 runtime rejection; r52 AFK constructor stack ownership

Pablo's r51 PCSX2 screenshots show a permanent blue-tinted rectangle before and after the intended callout, with dynamic sizing and missing AFK English text. This is a confirmed runtime regression; r51's static tests were not sufficient. The independently-created L1 group-2/0x6A object was kept at task+0x2F4 and destroyed at task teardown, with no proof it shared the native green bubble's animation/visibility state. r52 restores the entire r50 L1 create/destroy path. The missing compact L1 tint remains open pending proof of the actual visibility owner.

The AFK caller computes Y in COP1 f13 and spills it with swc1 f13,0x1A4(sp) at file offsets 0x661FC and 0x662D0. r51's pre-constructor hook changed f13 but left the caller's native stack argument unchanged. r52 replaces it with an append-only 84-byte hook, called at 0x66250/0x66320, reading the unchanged per-record r50 Y from the 600-record 32-byte layout table. The same new value goes to f13 and sp+0x1A4; native f14 and f15 setup are preserved. This is a testable hypothesis, not a runtime-certified repair.

Freeze all r50 AFK green/blue geometry, action geometry, 999 AFK structural pointers, translated text bytes, wrapping and accepted unrelated UI. Do not launch PCSX2 automatically.

## r53 text registers, L1 alpha ownership and AFK containment

r52 runtime screenshots: L1 blue below the green callout, AFK text absent, and AFK blue overhangs some bubble sizes. Root cause of missing text: the specialized AFK constructor VA 0x1950A0 preserves caller t0/t1/t2/t3 as extra arguments (including sd t1,0x408(sp)); r51/r52 indexed the Y table with t0..t2, clobbering the original text pointer. r53 keeps the same 84-byte f13+sp+0x1A4 Y owner but uses t4/t5/t6 exclusively, preserving t0..t3. No AFK strings, pointer words, wrapping, height delta or native f14/f15 changed.

L1 blue in r51 was created at task+0x2F4 with no connection to native sprite alpha. Native green animation owns four vertex alpha values through file 0x65A88 (show), 0x65B40 (hide), 0x65C5C (fade hide). r53 creates a resource0x6A sibling at green X/Y, depth242.5, starts its four alpha bytes at zero, then replicates each native green alpha transition to blue using a 32-byte show and 32-byte hide helper. The original green sb executes in the helper, the original following lw a0,2DC(s0) remains the JAL delay slot, and a0/a1/v0/v1 remain unmodified. Both task+0x2F4 cleanup paths 0x66668 and 0x66DD4 use the sprite destructor.

For AFK, r53 sets the blue width to 282 instead of 288 at the AFK-only runtime consumer and places blue at X=175/233, versus green at X=172/230. Native blue pivotX 67/125 then yields a symmetric 3px inset within the 288px green body for both slots. The accepted green border/tail geometry and vertical-growth model remain unchanged. Runtime acceptance remains Pablo's PCSX2 screenshots, not static tests; do not launch PCSX2 automatically.

## r54: two independent blue sprites and multiline second-text baseline (r53 runtime)

Pablo's three r53 screenshots show (a) short AFK English appears and fits, (b) long AFK "Ruins and people both / grow richer with age" displays the second text object too low, ending with "age." below the green outline, and (c) L1 shows TWO tinted rectangles: the original AFK group-2/resource-0x6A panel at its old lower position and the newly-created r53 L1 blue panel at an upper position. Neither can be accepted just because static 155/155 checks passed.

The exact lower L1 impostor has a native owner: H_TalkBuddyTask at VA 0x165EC4 stores its pre-existing AFK resource0x6A at task+0x5C. r53 separately creates one at task+0x2F4. Reusing a shared metadata id does not remove a live old resource. r54 preserves the one explicitly-created and lifecycle-synchronized L1 +0x2F4 object, but suppresses all four alpha vertices of the native +0x5C AFK sprite at L1 construction and on every green show/hide vertex transition; on normal AFK transition the native task destroys/re-creates task+0x5C. Never destroy the old AFK handle merely to hide it, because the native task owns its lifetime.

r53 assumed passing the same stack XY was sufficient to place new blue with green. The sprite constructor at VA 0x107F88/0x107F90 actually stores the constructed instance's X/Y at object+0x3C/+0x40. r54 copies those LIVE fields from already-created L1 green sprite at task+0x2D8 into the new L1 blue sprite at task+0x2F4 after construction, making green's real transform authoritative, with safe NULL guards and unchanged native depth/alpha transition owners. This addresses the misaligned "upper" blue rectangle without another guessed screen-space Y constant.

r53 text layout record 487 is exactly line1=('Ruins and people','both'), line2=('grow richer with','age.'), green height144, blue height120, text1_y214 and text2_y278. The original game renders 0x0A embedded rows closer than the 32-game-unit conservative green bubble budget. R53's line2 baseline is therefore too low. r54 keeps the accepted 32-unit bubble growth/green/blue dimensions and moves only the second text object's Y 18 units UP for every additional visual row in that second object (record487 text2_y=260), leaving single-row AFK and all AFK pointer/text payloads unchanged. The offset is justified by the observed screenshot line spacing and is NOT a claim of PCSX2 runtime confirmation.

Manual runtime gate: see only ONE tinted panel INSIDE the L1 green bubble, never the old lower one or the formerly too-high one; short AFK stays intact; long AFK "age." and blue tint remain inside the green frame; test both slots and bubble disappearance. No PCSX2 auto launch. Freeze 3+3 name entry and unrelated screens.

## r55: single native L1 blue object, never allocate a duplicate

Pablo's r54 PCSX2 screenshots definitively reject three iterations of an extra L1 blue object (r53/r54). The top and lower blue panels remain visible simultaneously despite copying sprite positions and attempting to suppress native alpha. The robust response is to remove the independent allocation instead of adding another guessed position/alpha offset. Native group-2/resource0x6A already exists as task+0x5C, created through the original VA0x165EC4/0x16612C. L1 green speech bubble resource0x68/69 (selected by our r38 hook) is stored at task+0x2D8. r55 uses one 156-byte existing L1 hook at file0x66740 exclusively to reposition the native task+0x5C blue object's real X/Y fields (+0x3C/+0x40) from the already-constructed native green object's same fields, and set native blue sprite Z to 242.5 (green243, text242). NULL guards preserve owner and default next resource initialization. The helper executes ZERO resource-constructor JALs and never writes task+0x2F4. The existing 48-byte action visibility helpers mirror the original green vertex-alpha writes to task+0x5C; the pristine task+0x2F4 native destructor is restored at file0x66668 and0x66DD4, because there is no extra injected sprite to destroy. The native task retains ownership of the AFK blue sprite and can recreate it on AFK reentry.

For AFK, text is confirmed visually correct for short and long records in r54; do not touch r53's live-register fix or r54's second-object baseline. A small downward blue-panel leak still appears for SOME larger bubbles. r55 applies a bottom-only 3-unit trim to the record-dependent BLUE height (layout record+8) strictly when total visual rows > 2. Blue pivot-Y and green height/pivot, shared resource placement, horizontal 3px inset, AFK text positions and translated bytes are frozen. This preserves two-row cases as exact control samples, minimizes potential top-edge drift, and should allow 3px more lower-edge clearance. The trim is a candidate supported by screen inspection, not a runtime-verified resolution.

## r56 candidate — native live-sprite pool owner, AFK gap/bottom adjustment

Pablo's r55 PCSX2 screenshots prove AFK English is visible and short bubbles are accepted. L1 still has no blue fill inside green, with an old blue window visible below; r55's task+0x5C object pointer was not authoritative for the lower sprite. Long AFK screenshots (notably record487, "Ruins and people / both / grow richer with / age.") show a larger-than-usual gap between the TWO native text objects and a small lower blue overhang. The embedded line breaks inside one text object use the game's 32-unit renderer step; do not globally modify that renderer or font.

Tracing native sprite allocation at VA0x107D60 and pool manager VA0x107E00..0x108050 proves live sprites are stored in a 512-record pool at VA0x007A5060 with stride0x94, active byte+0x93, group halfword+0x82, resource halfword+0x84, constructed X/Y floats+0x3C/+0x40, Z float+0x68, vertex alphas+0x23,+0x27,+0x2B,+0x2F. r56 uses those NATIVE allocation records to locate group2/resource0x6A, rather than the task-local +0x5C pointer. The existing 156-byte action helper at file0x66740 searches the pool without allocating or destroying a new sprite, copies the ACTUAL green speech sprite's constructed X/Y from task+0x2D8 into the located blue sprite, sets depth242.5, and caches that exact located pointer in a reserved four-byte RWX word at the end of the existing helper (VA helper+0x98). Both existing 48-byte native green show/hide callbacks use that cached instance to mirror four-vertex alpha. The caller's displaced f12 for next resource remains untouched. If no live group2/resource0x6A is present, the pointer remains null; no speculative allocation or unrelated UI mutation occurs. Native AFK lifecycle retains ownership and disposal.

For AFK, the long-multiline blue-height bottom-only trim increases conservatively from 3 to 6 game units. First text object's Y, all accepted green geometry, blue X/width and pivot, texture data, all translated words and native slot anchors remain unchanged. For AFK records whose first text object spans multiple lines and the second object is present, move ONLY the second object's Y 9 units upward, eliminating the observed extra separation between native text objects; record487 text2_y moves 260->251 while short record480 and 'Easy, easy!' record485 are unchanged. The native within-one-object newline step remains the original 32, because changing this global renderer would risk unrelated accepted screens.

This remains a STATIC-CHECKED r56 candidate, NOT a runtime-proven rendering fix. Manual PCSX2 confirmation is mandatory: one blue panel INSIDE L1 green with no lower panel, disappearance with L1, long AFK line spacing/bottom fit and unchanged short AFK in both companion slots. Never auto-launch PCSX2.

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
