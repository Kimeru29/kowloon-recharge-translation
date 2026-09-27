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

Current deterministic candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r10.iso`, SHA-256 `a4f629fb22b2b095fe374eab384d86365ff881038fc37d4fa1e590297d5f928d`; pre-ROFS ELF `711ddca9d7813efaf34fc9788407fd0245a198b3ac8d08e925b851051c7b30c5`; post-ROFS ELF `76f335855ce03615f216cff575dfa63ff978b46660b7380d5954825499425a10`; size 8,405,750 bytes; **141/141** final-image checks; **205** dependency-free tests. The repeat ISO is byte-for-byte identical. PCSX2 has not been launched for r10.
