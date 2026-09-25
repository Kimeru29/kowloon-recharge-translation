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

A fuller trace also disproved the earlier `(2,0x8E)` backing hypothesis. The label renderer does create one `(2,0x8E)` sprite before its `(2,0x8C)` glyph loop, but state 3 repeatedly updates that object's X coordinate as text reveal advances. It is therefore a moving reveal marker, not the static `New Game` / `Load Game` backing. Task 5 must operate on the paired `(88,12)` / `GP088_12` owner and preserve neighboring title records. Full bounded evidence is recorded in ignored `local/title-layout-v11.json`.

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

The v6-v10 four-word patch targeted the correct constructor but contains a concrete sequencing defect. It changes the first load to `+0x465` and places `sra v1,v1,1` at VA `0x24F9E8`, **after** VA `0x24F9E4` has already copied `v1` into `f0` with `mtc1`. The float X calculation therefore receives the unhalved byte position. This explains why the static `adv_horizontal_layout` check could pass while the v10 DG00 runtime presentation remained wrong. Task 3 must fix the proven constructor sequence and must not mutate the `0x24ED20` progress gate.

`tools/adv_layout.py` fail-closes on the exact consumer and ownership-chain preimages. Detailed local evidence is emitted to ignored `local/adv-renderer-ownership-v11.json`.

## Executable translation segment / H.A.N.T. tutorial

The H.A.N.T. startup tutorial pointer table is at `0x5C8C70`. The pristine ELF's second PT_LOAD is zero-sized at virtual address `0x00902F00`; localization activates it as a reusable translated-text segment and reserves a 1 MiB VA window through `0x00A02F00`.

v7 runtime exposed an allocator invariant that the original implementation missed. The startup heap instruction and ELF heap metadata had been moved to `0x00A02F00`, but libkernel's live `sbrk` break word at file offset `0x650014` still contained `0x00902F00`. The allocator routine at `0x387E60` reads/advances that word, so normal allocations could overwrite the translation PT_LOAD. This explains the v7 reading prompt degrading from the statically correct full string to visible `Enter` and the later freeze. v8 validates and moves all known heap ownership sites to `0x00A02F00`.

The shared segment now carries H.A.N.T., the two overflow name-reading prompts, and the proven subset of executable memory-card UI strings. Exact program-header, heap, source-string and pointer preimages are enforced.

v11 Task 6 adds a bounded ownership inventory before expanding H.A.N.T. translation. The `0x5C8C70` table is exactly 17 slots: text at indices `0,2,3,4,7,8,9,10,12,13,14`, and blank/EOF control slots at `1,5,6,11,15,16`. A main-executable pointer scan also surfaces 10 additional CP932 strings containing the fullwidth `Ｈ．Ａ．Ｎ．Ｔ` token outside that table; they remain ownership candidates rather than being silently treated as tutorial text. Generic occurrences of words such as `情報` are not enough evidence by themselves.

The official remaster `English.bytes` corpus was not present at its expected local extraction path during this inventory pass. Following the fail-closed rule, text entries are therefore recorded as `unresolved` with `official_english: null`; no new English mapping is inferred from memory or from the already-patched runtime strings. The committed `translations/hant_ui.json` contains only the 17 proven tutorial slots, while the broader candidate evidence is kept in ignored `local/hant-inventory-v11.json`. The documented PS2 `方向キー` / remaster `方向ボタン` semantic join is implemented but only activates when a matching official corpus row is supplied.

v11 Task 7 traces the tutorial presentation path far enough to separate storage limits from visible geometry. Resolver VA `0x2A9FE0` reaches the startup tutorial through descriptor tuple `(mode=4,page=2,subpage=0)`; the leaf descriptor word is file `0x5CBAB0`, which points to the pristine table VA `0x006C8BF0`. This matters because the renderer's absolute source-index hooks at rows 5/7/18 belong to mode 2 and do not execute for the mode-4 tutorial. The mode-4 row walk is EOF-sentinel-driven and materializes at most 16 rows. Its parallel metadata owner is a separate 8-byte-record list at VA `0x006C8A20` with its own negative sentinel, so the text table is not required to retain one-for-one row alignment with that auxiliary data.

Each resolved H.A.N.T. row is copied through the bounded helper at VA `0x39FCC0` into a 64-byte staging field. Because the accepted PS2 English encoder emits two bytes per printable glyph, that is a 32-cell storage ceiling, not the visible line width. The actual text rows begin at logical X `85`, use Y `131 + 21*n`, and the generic text object uses style 0 from font-record VA `0x005D77D0`. That record's width/height bytes are `16/18`; the separate `20.0` constructor argument observed at the call site is not the glyph step. With the page's 1.0 horizontal scale, the ordinary-glyph advance is therefore 16 logical pixels in a 512-wide canvas, giving `floor((512-85)/16) = 26` visible cells. `tools/hant_layout.py` records that 26-cell visual limit and wraps only at legal word boundaries while protecting five-cell controller-placeholder spans.

The parallel resolver at VA `0x2A9FA0` proves that tuple `(4,2,0)` also owns a controller metadata list at VA `0x006C8A20`, selected by leaf descriptor file `0x5CBA60`. Its three 8-byte records place the original icons at approximately `(83,320)`, `(127,382)`, and `(82,424)`, aligned with Japanese placeholder gaps on text rows 9, 12, and 14. The accepted English reflow preserves the 16 materialized-row shape and EOF: row 1 stays blank, the decorative underline is omitted rather than shortened, body text expands through row 6, and the controller gaps land on rows 8, 11, and 14 at columns 10, 6, and 10. The relocated metadata records become `(0,5,170,180)`, `(38,1,102,242)`, `(0,0,169,305)`, plus the unchanged negative sentinel, preserving each icon's original sub-cell offset relative to its placeholder.

The v11 patch keeps both the original 17-entry tutorial pointer table and original controller metadata byte-identical as provenance. It places the 16 translated rows, a 17-word text table including the original EOF sentinel, and the relocated controller metadata in the translation PT_LOAD; only text leaf descriptor `0x5CBAB0` and metadata leaf descriptor `0x5CBA60` are redirected. Newly discovered Task-6 H.A.N.T. candidates remain unpromoted without `English.bytes`; the executable main-menu label at file `0x3BC7E8` is an explicit cross-owner exception because it is already translated by the separately proven menu fixed-string patch. Final-image acceptance names the ownership/layout gates `hant_inventory_proven_targets`, `hant_wrapped_layout_payload`, and `hant_unresolved_pristine`.

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

The final-image verifier now checks the live libkernel heap break, all eight name prompts, the proven memory-card English pointers/text, 31 startup graphics including B_GP088, H.A.N.T., ADV layout, ROFS resolution and the DG00 text/choice slice. Runtime proof remains mandatory.


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

The v10 runtime failure does not disprove that ownership: the old four-word patch itself is malformed. Its `/2` normalization at VA `0x24F9E8` executes after `mtc1` at VA `0x24F9E4`, so the float X calculation still receives unhalved byte positions. Task 3 is cleared to patch only the proven `0x24F9E0` layout sequence and leave the progress gate unchanged.
