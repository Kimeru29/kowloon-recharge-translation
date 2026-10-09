# Architecture

## Principle

Every output is derived from pristine user-owned sources plus deterministic tooling/metadata. Never use a previously patched ISO as build input. Automatic localization is fail-closed: uncertainty produces a report/rejection, not a guessed translation.

## Layers

1. **Source identity** — hashes and game IDs prove the PS2/PS4 inputs.
2. **Corpus inventory** — PS2/PS4 ADV relationships and English-map availability are classified independently.
3. **Format parsers/compilers** — MTX, KSF, TMX, ELF/ROFS, CVM and ISO9660 logic are isolated and structurally validated.
4. **Localization importers** — exact, structural and explicit-reviewed imports emit only proven outputs.
5. **Startup/UI backport** — executable-resident UI and localized PS4 graphics are ported through renderer-specific encodings and PS2 indexed textures.
6. **Regression/identity gate** — accepted translations, serial and save namespace cannot silently drift.
7. **Build/repack** — overlays are applied to the nested CVM ISO, executable ROFS metadata is updated atomically, and the finished image is re-read and verified.

## MTX

The first little-endian u16 is the pointer-header size in 4-byte units. Pointer targets are quarter-offsets and rebuilt regions stay 4-byte aligned. Because MTX also uses ordinary ASCII as a command language, localized dialogue uses the PS2 two-byte CP932/full-width glyph path rather than injecting ambiguous ASCII opcode bytes.

## KSF

PS4 KSF DC maps identify official strings, but English can exceed PS2 inline field capacity. The current importer accepts only proven fixed fields whose English fits. Overflow fields stay Japanese unless there is a reviewed constrained override. A relocatable general KSF compiler is still unproven.

## Executable UI

Renderer encoding is not assumed globally. The title renderer was runtime-proven to consume two-byte glyph units. The exact official labels are now stored in a verified 40-byte title arena: `New Game` remains at the first source slot and `Load Game` is moved within the arena with its pointer updated. Name-entry keyboard cells also remain two-byte glyphs and preserve the original 20-key logical geometry.

Name/profile startup prompts are a separate two-byte-glyph class. Six official English prompts fit a verified module-local arena; the two reading prompts overflow that arena and remain relocatable through the shared executable translation PT_LOAD for provenance/testing. Protagonist/default names are redirected to wide strings. Static tracing shows the PS2 name editor has two structural 3-glyph permanent-name buffers; this remains an unresolved renderer/input-structure issue rather than a limit-only patch.

v10 also introduces a distinct executable-control-flow localization class. The PS2 reading editor is a kana-specific second pass that the official English data does not need. Rather than shortening its clipped prompt or weakening its Japanese validator, the English build changes the state-9 transition flag from 0 to the game's existing flag-1 post-reading path. The patch validates the state-9 flag/call and matching state-11 flag/call as exact instruction preimages before changing one word. Default/runtime reading buffers stay blank, matching the remaster's deleted reading values.

The translation PT_LOAD owns a 1 MiB VA window starting at `0x00902F00`. Reserving that window requires moving not only startup/ELF heap metadata but also libkernel's live `sbrk` break word at file offset `0x650014`; v7 runtime proved that omitting this third owner lets the allocator corrupt relocated strings. v8 treats all three as one fail-closed allocator invariant. v11 centralizes allocation in `tools/executable_text.py`: one deterministic input-order payload, 2-byte entry alignment, one PT_LOAD installation, unique key/pointer ownership, and a target-VA map. The same segment now stores the two overflow name-reading prompts, H.A.N.T. tutorial rows/table/metadata, the seven pointer-owned H.A.N.T. chrome labels, r6's three Help category labels + 55 Help topic labels + nine Config labels, r13's separately owned selected Help-body rows/tables plus runtime-observed Mail/Config/Enemy/Dictionary content aliases, r14's relocated Help icon metadata, Mail count label, and two runtime-observed Dictionary definition leaves, the proven memory-card subset, and the two ownership-proven long command labels `Return above ground` and `Report card`. Executable message ownership includes both canonical pointer tables and any statically proven aliases; unproven labels such as `メディア` remain outside the allocator. H.A.N.T. chrome/help/config/body mappings are marked semantic rather than official when the owned remaster extraction does not expose their localized TextAsset.

## H.A.N.T. executable layout

H.A.N.T. is a renderer-specific executable text class rather than a generic wide-string replacement. The row staging buffer is still the hard storage ceiling at 64 encoded bytes, or 32 PS2-English glyph cells. Runtime v11 evidence is stricter for presentation: style 0 uses 16-pixel glyph advance and exposed only about 21 safe English cells, roughly 336 pixels, before right-side clipping. v11-r4 keeps that runtime-proven pixel span but changes only the mode-4 tutorial row constructor at file `0x190968` from existing font style 0 to existing style 1, whose record is 12×12. That yields a conservative 28-cell visual budget (`336 / 12`) without injecting a new scale path or modifying global font data. r5 tightens only this page's row stride from 21 to 18 pixels; Pablo's r5 runtime test confirms the resulting 14-row presentation has good spacing. Controller-icon holes remain protected five-cell spans and may not be split. r6 preserves this runtime-good tutorial geometry unchanged.

The tutorial owner is selected through a mode/page/subpage descriptor, not by direct code references to the 17-entry source table. Tuple `(4,2,0)` has two independently resolved leaves: the text table and a three-record-plus-sentinel controller metadata list. Translation keeps both pristine sources byte-identical, writes a new 14-row-plus-EOF text table and relocated controller metadata into the translation PT_LOAD, and redirects only those two proven leaf descriptors. The 28-cell reflow omits redundant presentation-only heading/separator rows and places the three controller holes on rows 6, 9, and 12; metadata moves with the holes while preserving each icon's original offset from its Japanese placeholder.

Separately, the seven live chrome labels are owned by the pointer table at file `0x586D20`. r6 adds three independently proven **label/presentation** owner classes: Help category tabs at `0x587288`, three sibling Help topic-label tables at `0x587430`, `0x587690`, `0x587840` (55 labels total), and the nine-entry Config label table at `0x586EF0`. Pablo's r11 runtime pass proves those 55 topic-label aliases do not own the text shown after selecting a topic.

Selected Help bodies use a separate `(mode=4, category, topic)` tree. Text resolver VA `0x2A9FE0` indexes root VA `0x006CBAC0`; metadata resolver VA `0x2A9FA0` indexes root VA `0x006CBAA0`. `tools.hant_inventory.inventory_hant_help_bodies` follows only the proven Help cardinalities (20 ADV + 20 Ruins + 15 Other) and fail-closes unless all 55 text leaves reach EOF and all metadata leaves reach a negative sentinel. `(4,2,0)` resolves back to the translated tutorial table, explaining why `H.A.N.T Functions` was already English at runtime. r12 promoted `(4,2,5)` / `About the Shop`; r13 additionally promotes `(4,0,0)` / `ADV Controls`, `(4,1,0)` / `Exploration Controls`, and `(4,1,1)` / `Moving in Ruins`. Each new body keeps the exact pristine row cardinality and exact metadata record list; only its text-table descriptor moves to a word-aligned English table in the translation PT_LOAD. Because `English.bytes` is absent, this wording is tagged `semantic`, not `official`.

r13 also formalizes independent H.A.N.T. content-owner classes revealed by runtime. Config's 20 ringtone aliases are proven by the two code materializations of table VA `0x00687160`; Dictionary's ten index aliases are proven by renderer materialization of table VA `0x00687840`; Enemy's three category aliases are proven by materialization of table VA `0x00689978`. The empty-Mail message has one direct pointer alias. Dictionary term lists contain 208 real selectable pointers plus placeholder slots; r13 redirects only the real entries, with source identity pinned by NUL-terminated string SHA-256 and exact pointer preimages. Definition pages opened after selecting a Dictionary term are a separate mode-1 descriptor/table class. r14 promoted two observed leaves but incorrectly mutated `0x190A40`; r14 runtime proves that word is a mode-4 singleton whose mutation blanks/traps `H.A.N.T Functions`, so r15 restores and permanently pins it pristine. r16 then enumerates all 208 mode-1 definition leaves without changing that shared singleton. The recovered owned-remaster `English.bytes` uniquely matches all 2,073 nonblank source rows. Generated definition data stores descriptor/table ownership, pristine row count, a SHA-256 source fingerprint, and official English reflowed to a conservative 21-cell body width. r17 treats Japanese blank rows as layout rather than semantic English paragraph boundaries: exactly one title/body separator is retained and the remaining official fragments are reflowed continuously. Thus all 208 source tables remain immutable provenance while only their proven descriptors point at new EOF-terminated English tables in the translation PT_LOAD.

r17 runtime proves its remaining Dictionary geometry assumptions were still too narrow: the live style-0 `【Dictionary】` chrome begins at x=75 and spans twelve 16px glyph cells through x=267. r18 therefore keeps the accepted 14px/style-1 tab cadence but moves the ten-tab origin to x=268, ending the final glyph at x=406 immediately before the fixed R1 anchor near x=407. The same width proof corrects mode-1 detail offset file `0x588C84`: Japanese `【用語辞典】` is six 16px glyphs while English `【Dictionary】` is twelve, so the Dictionary-only offset changes 6→12 rather than r17's insufficient 6→8. Mail and Dictionary empty-state strings remain pointer-owned content on shared row geometry; r18 removes the r16 Mail leading-space guess and reduces Dictionary empty padding from ten to five cells rather than moving row constructors shared with non-empty content.

## ADV/DG dialogue layout

ADV dialogue is a renderer-specific layout class. The record fields at `+0x463` (line) and `+0x465` (byte position) have two proven consumers, but only one owns glyph placement. The ordinary script-text path reaches constructor VA `0x24F660`, whose coordinate code around VA `0x24F9E0` computes `114 - 39 * line` and `20 + 26 * (byte_position / 2)` before passing the results as integer coordinate arguments. Callback VA `0x24E920` consumes the same fields only to gate glyph reveal/progress and must remain pristine.

The v11 English transform therefore does not alter the source fields, FPU constants, glyph renderer, or reveal callback. It swaps only the completed coordinate argument registers immediately before the coordinate helper: the byte-position formula becomes X and the line formula becomes Y. Runtime v11 then proved that coordinate ownership alone was insufficient: the DG object constructs four font canvases and propagates one wrapper orientation argument to all of them. v11-r4 therefore adds one upstream mutation at file `0x14E96C` / VA `0x24E8EC`, changing the unique wrapper callsite argument from `a2=1` to `a2=0`; every DG body canvas receives horizontal advance from the same owner. `ADV_DG_LAYOUT_PATCHES` remains the fail-closed body-layout table.

r5 added a second orientation patch at file `0x151608` / VA `0x251588`, but r5 runtime showed the visible inline speaker still rendered incorrectly. r6 traces the actual bracket-derived speaker separately: the script dispatcher recognizes CP932 `【`, the parser stores the resolved name at global `+0x198`, and the live renderer at file `0x15007C` passes that exact buffer to the generic text constructor. Its text-mode argument at file `0x15006C` is pristine mode 2; generic constructor tracing proves mode 1 follows the horizontal mesh branch used by ordinary dialogue. `ADV_SPEAKER_LAYOUT_PATCHES` now changes `0x15006C` from mode 2 to mode 1 while preserving the older `0x151608` mutation as a distinct record-label owner until runtime proves it can be removed. All owner words are independently fail-closed. This preserves the signed two-byte-glyph `/2` normalization exactly once and leaves the reveal/progress callback untouched.

## Current candidate verification contract

v11-r19 freezes the r18 runtime-accepted Dictionary selected-page layout and changes only root presentation owners: shared Mail-row X 143→120; Dictionary L1/tab cadence+origin/R1; and Enemy L1/category bases/R1 with category Y restored to pristine 93. The candidate hashes are pre-ROFS `c8795405f9746db2ba260c4fe644ee45218d200232112496f4ad6f1f58ba50b3`, post-ROFS `d34d53d62b6236d1c1b87577704bbd2eb8d84945564216750df74347e82a7cef`, ISO `4dbce7f49d537e6cc6aa156ff6d4723596de31b3a8657caa83a4b0a40db81928`; final-image acceptance is **150/150**, both suites execute **218 tests**, and the independent repeat ISO is byte-for-byte identical.


v11-r18 is the bounded follow-up to Pablo's r17 screenshots. It preserves the r17 definition reflow, Enemy geometry, and all previously accepted surfaces; only Mail empty-state padding, Dictionary empty-state padding, Dictionary top-tab origin, and Dictionary mode-1 title/icon offset change. The finished executable is 8,562,114 bytes; pre-ROFS SHA-256 `64c220490e64da7e6d50d8d76ebd0f9e60cc94c42cbc6414605ba258bd71fad1` and post-ROFS SHA-256 `a61b72b35d95112f68e79f1d1f1f1c36a77a1ab454ff714514694e540799f74a`. The finished ISO hashes to `136a528030ab5ce611efd67fd06cf637f9015e1ba3473f760f9a6e72d7754c9a`. Final-image acceptance is **150/150**, both complete suites execute **218 tests** (10 dependency-free skips / 1 Pillow-enabled owned-corpus skip), and the independent r18 rebuild is byte-for-byte identical. These are static/deterministic guarantees only; r18 still requires Pablo's visual acceptance.

## PS2 indexed graphics

`tools/tmx.py` handles both named TMX chunks inside `B_GPxxx.BIN` containers and standalone `TMX0` files. `tools/graphics_port.py` downsizes official PS4 RGBA artwork, quantizes it to the PS2 palette size, preserves 4/8-bit indexed layout and CLUT ordering, and rewrites only palette/pixel payloads. File/container sizes remain fixed.

The first accepted graphics scope is startup-specific:

- `BLBRD/B_GP019.BIN` — name-entry controls;
- `BLBRD/B_GP020.BIN` / `GP020_03` — semantic-English H.A.N.T. caption atlas; only nine SHA-pinned green caption rectangles may change, with icons/chrome/coordinates and the indexed palette preserved;
- `BLBRD/B_GP088.BIN` / `GP088_03` — direct same-layout official English startup/title texture;
- `BLBRD/B_GP088.BIN` / `GP088_12` — structurally repacked title atlas derived from proven GP088_03 regions;
- `BLBRD/INIT_MES/TR000.TMX` through `TR028.TMX` — the 29 opening quotation images.

Structurally changed atlases use the generic fail-closed `tools.graphics_layout` class: declarative source rectangles plus coordinate offsets are validated against the pristine target by alpha-mask Dice overlap before localized regions are repacked. GP088_12 is the first accepted instance: two GP088_03 regions map at `(-223,+14)` and `(-87,+14)`, scoring 0.8758/0.8765 after excluding the known flattened banner band. Unproven atlas layouts remain rejected.

Generated graphics remain local-only; repository code stores no copyrighted artwork. `tools/hant_graphics.py` stores only caption geometry, source-region hashes, a tiny deterministic 5x7 ASCII bitmap, and the semantic labels; it does not embed the source atlas.

## Runtime CVM / ROFS lookup

ISO9660 is not the only runtime source of truth. `SLPM_665.11` contains a ROFS file table: for the proven records, byte size is 14 bytes before the NUL-terminated basename and sector extent is 6 bytes before it. The failed v1 runtime build proved that updating only ISO9660 leaves the game loading stale Japanese sectors.

`tools/build_translation_iso.py` therefore treats embedded ISO metadata and executable ROFS metadata as one atomic update. Every overlay asset must have a unique pristine size+extent match in the ELF; the final record must resolve to the same output size/extent and payload as ISO9660. Missing, duplicate or mismatched records are hard failures.

## Save compatibility

The executable uses `BISLPM-66511Save`. Ordinary memory-card saves are the cross-build compatibility target. Savestates are considered build-specific. The serial `SLPM-66511` and save namespace are build invariants. The accepted r66 gate preserves all 15 original save path references and surrounding descriptors, while future changes must also preserve serialized fields, scenario/flag/item IDs and the save/load code path. A cold-boot, cross-build memory-card load/progress/re-save/re-load smoke test is required before calling a future ISO save-compatible. Static name preservation alone is insufficient proof.


### v11-r20 selector ownership

Dictionary and Enemy root selection rectangles are independent animated objects, not properties of their text canvases. Dictionary derives selector X from a stored base plus current-category cadence (`223 + 18*i` pristine), while Enemy recreates its selector from selected category `0x130` (`288 + 40*i` pristine). r20 changes only those formulas to follow the already-accepted English text geometry (`300 + 12*i` and `222 + 66*i`) and restores Enemy's independently owned R1 anchor to x=407. This keeps Mail, Dictionary detail offset `0x588C84 = 12`, `0x190A40`, translated text payloads, and all other r19-accepted owners outside the r20 mutation set.


### v11-r21 selector resource geometry

r20 proves selector position and selector size are independent owners. Both Dictionary and Enemy red frames are group-20 sprite resources constructed through VA `0x107D60`; their resource-table records resolve to one metadata leaf each. Dictionary index `0x21` owns metadata file `0x364BB0` and Enemy index `0x41` owns `0x3657B0`. r21 treats the second metadata word as the bounded rendered-width owner (24→14px and 40→64px respectively) and deliberately leaves each resource's UV rectangle byte-identical. Enemy additionally keeps the runtime-accepted style-1 font and adjusts only category/selector X packing; no global font or atlas mutation is introduced.


### v11-r22 selector-family inheritance

Dictionary group-20 selector index `0x21` and Enemy index `0x41` are family-level resources, not per-item assets. The runtime computes selector position from the selected category index, so width/base changes apply uniformly to every item in that family. Dictionary's mode-1 detail renderer is likewise shared across all enumerated terms; the generated corpus already covers 208 definition leaves, including currently locked ones when they become reachable. This inheritance does not extend across unrelated H.A.N.T families: Help/topic bodies and other menu classes may own separate descriptors, text tables or selectors and remain fail-closed until promoted.


### v11-r25 Help selector-family geometry

r25 extends the group-20 selector ownership model to Help without coupling it to Dictionary or Enemy. The Help topic selector is index `0x22`, resolved uniquely through table file `0x382FE0` to metadata file `0x364BE0`; its second metadata word is the rendered width owner and changes 168→268px while the UV rectangle remains byte-identical. The three Help category tabs use independent selector index `0x32`, resolved through `0x383060` to metadata file `0x364EE0`; its 72px width remains pristine. Topic and category text constructors are also separate owners at files `0x18C674` and `0x18C7F8`, both switched from style 0 to the existing style 1. This family-level ownership means every Help topic row inherits the 268px selector, while Dictionary index `0x21` and Enemy index `0x41` remain isolated and regression-frozen.


### v11-r26 bounded header/selector geometry

r26 keeps the existing family-owned renderers and changes no text ownership. Dictionary remains one rigid header cluster: L1, tab text base, animated selector base and R1 all move four pixels left together while cadence/width stay fixed. Help keeps the shared category-selector resource but corrects both shoulders without a new renderer: selector base returns to x=200 and shared width shrinks 72→64px, preserving the same x=402 right edge; category labels align at x=202/271/340. The 268px Help topic selector, all 55 topic labels, Help bodies, Dictionary details/definitions and the runtime-proven Enemy family remain independent/frozen.


### v11-r27 Help category-owner correction

r27 changes no renderer or resource ownership. Runtime observation identifies the r26 Help category X-owner attribution as reversed: file offset `0x18C768` controls `Ruins`, while `0x18C778` controls `ADV`. The selector remains at x=200 with the accepted 64px shared width; `Ruins` is restored to its pristine owner word and only `ADV` receives the intended -8px X nudge. `Other`, the 268px Help topic selector, Help bodies, and all accepted content remain unchanged. Enemy and Dictionary are now runtime-accepted and explicitly frozen by dedicated geometry regressions.


### v11-r28 per-category Help selector geometry

r28 keeps the r27 Help labels byte-for-byte fixed. The category highlight cannot be solved with another shared-resource width edit because ADV, Ruins and Other all instantiate group-20/index-0x32. The live Help update path writes selector X through sprite field `+0x3c`; generic sprite construction and the independently proven title path establish `+0x60` as X scale. A 48-byte helper is placed in the existing zero padding at file `0x287388` / VA `0x387308`, with a 24-byte geometry table in zero padding at file `0x290484` / VA `0x390404`. The original category-X FPU sequence calls that helper; it writes only X and X scale for the selected selector. Geometry is ADV `(204,.75)`, Ruins `(257,1.125)`, Other `(338,1.0)`, yielding 48/72/64px boxes centered on the frozen 12px labels.


### v11-r29 dungeon HUD / command-label text ownership

r29 keeps the accepted r28 H.A.N.T. renderer/layout byte-for-byte frozen and extends only the shared executable-text ownership model. Runtime proves the SELECT command renderer is a two-byte PS2 glyph consumer: the previous compact ASCII substitutions render lowercase letters as deterministic garbage (`Items` → `ISdlR`, `Noise` → `NnhRd`) while uppercase `H.A.N.T` happens to survive. All 18 proven command labels are therefore stored as `encode_ps2_english` payloads in the shared translation PT_LOAD and every proven entry in the 21-slot command pointer table is redirected to that payload. The compact Japanese source slots remain immutable provenance; unresolved `メディア` remains untouched.

The dungeon HUD has two additional text ownership classes. `H_CmdIconDraw` directly materializes the exploration-action strings `調べる`, `アイテム`, and `ジャンプ`; r29 models their LUI/ADDIU pairs as `RelocatedCodeReference` owners and retargets only those address materializations to official `Examine`, `Items`, and `Jump`. The battle/L1 selection path calls VA `0x134AB0`, which indexes the 500-entry item-name pointer table at file `0x3912B4` and passes the selected pointer to the HUD text constructor. Exactly 446 nonblank PS2 names have unique exact Japanese-key matches in the owned CUSA27034 `English.bytes`; r29 relocates those 446 pointer owners to official two-byte English and leaves the remaining blank/unproven slots untouched. Source strings and owner preimages are all fail-closed before allocation.


### v11-r30 companion HUD text ownership

r30 leaves every runtime-accepted r29 action/SELECT owner and the frozen H.A.N.T. layout unchanged. Companion chatter is owned separately by `h_buddy.c`: file `0x3D3320` is a 0x259-event table with 0x80-byte event stride, eight 0x10-byte slots per event, and line pointers at slot `+0x08/+0x0C`. Inventorying the live non-empty entries yields 1,650 unique Japanese source strings and 1,784 pointer aliases. Every source has one unique exact CUSA27034 `English.bytes` key, so all comments are relocated into the shared wide-text PT_LOAD while the Japanese source corpus remains byte-identical. Seven official `@D` rows are represented as empty PS2 second lines.

The persistent companion action/skill caption uses a separate 31-pointer table at file `0x3F8D20`. IDs 1..26 have exact PS4 matches, including the observed `石を投げる` -> `Throw a Rock`; ID 0 is a placeholder and remains pristine. Four Re:charge-only actions absent from the PS4 key corpus are explicitly tagged `recharge_semantic` rather than being presented as exact remaster reuse. All source strings and pointer preimages are fail-closed, and startup acceptance independently validates comment and action owner classes.


### v11-r37 companion slot positioning vs action layout

The persistent companion caption has two independent runtime axes. Companion **position** is selected by HUD-object `+0x2D0`, which is a 0/1 slot index. The pristine renderer multiplies that value by eight and indexes the two `(x,y)` pairs at file `0x3F8E80` / VA `0x4F8E00`: slot 1 `(172,407)`, slot 2 `(230,407)`. r37 does not patch this path or table.

Companion **action layout** is selected separately. The original renderer obtains the live action id by calling VA `0x0012FEE0` with key `0x8000`, normalizes the low 16 bits with `ANDI 0xffff` / `XORI 0x8000`, and then indexes the 31-pointer action table at file `0x3F8D20`. r37's 132-byte translation-PT_LOAD hook reuses that exact getter contract to select the generated height/pivot/text-Y row. This corrects r36's latent conflation of slot index and action id while retaining the generic 17-cell wrapping policy and accepted 224px bubble geometry.
