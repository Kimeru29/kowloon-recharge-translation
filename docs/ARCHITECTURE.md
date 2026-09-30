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

r13 also formalizes independent H.A.N.T. content-owner classes revealed by runtime. Config's 20 ringtone aliases are proven by the two code materializations of table VA `0x00687160`; Dictionary's ten index aliases are proven by renderer materialization of table VA `0x00687840`; Enemy's three category aliases are proven by materialization of table VA `0x00689978`. The empty-Mail message has one direct pointer alias. Dictionary term lists contain 208 real selectable pointers plus placeholder slots; r13 redirects only the real entries, with source identity pinned by NUL-terminated string SHA-256 and exact pointer preimages. Definition pages opened after selecting a Dictionary term are a separate descriptor/table class and remain outside r13. r14 promotes only the two definition leaves actually observed at runtime (`King Akhenaten` and `Heracleion`), preserving their source tables and redirecting only the proven leaf descriptors to EOF-terminated English tables. r14's additional font-owner inference was wrong: `0x190968` is the established mode-4 H.A.N.T. row constructor, while `0x190A40` is a different singleton constructor in the same function. r14 runtime shows that changing `0x190A40` blanks/traps `H.A.N.T Functions`; r15 restores and fail-closes it pristine. Dictionary definition font-style ownership is therefore unresolved independently of the two proven text-table leaves.

## ADV/DG dialogue layout

ADV dialogue is a renderer-specific layout class. The record fields at `+0x463` (line) and `+0x465` (byte position) have two proven consumers, but only one owns glyph placement. The ordinary script-text path reaches constructor VA `0x24F660`, whose coordinate code around VA `0x24F9E0` computes `114 - 39 * line` and `20 + 26 * (byte_position / 2)` before passing the results as integer coordinate arguments. Callback VA `0x24E920` consumes the same fields only to gate glyph reveal/progress and must remain pristine.

The v11 English transform therefore does not alter the source fields, FPU constants, glyph renderer, or reveal callback. It swaps only the completed coordinate argument registers immediately before the coordinate helper: the byte-position formula becomes X and the line formula becomes Y. Runtime v11 then proved that coordinate ownership alone was insufficient: the DG object constructs four font canvases and propagates one wrapper orientation argument to all of them. v11-r4 therefore adds one upstream mutation at file `0x14E96C` / VA `0x24E8EC`, changing the unique wrapper callsite argument from `a2=1` to `a2=0`; every DG body canvas receives horizontal advance from the same owner. `ADV_DG_LAYOUT_PATCHES` remains the fail-closed body-layout table.

r5 added a second orientation patch at file `0x151608` / VA `0x251588`, but r5 runtime showed the visible inline speaker still rendered incorrectly. r6 traces the actual bracket-derived speaker separately: the script dispatcher recognizes CP932 `【`, the parser stores the resolved name at global `+0x198`, and the live renderer at file `0x15007C` passes that exact buffer to the generic text constructor. Its text-mode argument at file `0x15006C` is pristine mode 2; generic constructor tracing proves mode 1 follows the horizontal mesh branch used by ordinary dialogue. `ADV_SPEAKER_LAYOUT_PATCHES` now changes `0x15006C` from mode 2 to mode 1 while preserving the older `0x151608` mutation as a distinct record-label owner until runtime proves it can be removed. All owner words are independently fail-closed. This preserves the signed two-byte-glyph `/2` normalization exactly once and leaves the reveal/progress callback untouched.

## Current candidate verification contract

v11-r15 composes all executable relocations through the same single translation PT_LOAD and preserves every accepted pre-H.A.N.T. owner plus r14's proven H.A.N.T. geometry/content changes, while reverting the runtime-disproven `0x190A40` mutation and adding the Exploration warning gutter. The measured candidate uses 1,145 overlays (892 in place, 253 relocated), patches 1,145 executable ROFS records, and produces an 8,416,238-byte final ELF with SHA-256 `306cfa21e720328c269c505995c5041b0d4b77496329ecbf22bdf14b5eef1a68`. The pre-ROFS translated ELF hashes to `dcdd2f0c4a22bb74f280ec285fc43a061dd475c07ce10a00e31498849a274f86`. The finished 2,095,382,528-byte ISO hashes to `e4cf331c90470e99c2c0db1728673a7ddcdab358182f8d1ba7927b6dbbf387f6`; the independent repeat build is byte-for-byte identical. Final-image acceptance is **150/150**; both suites execute **215 tests** (10 dependency-free skips, 1 Pillow-enabled owned-corpus skip). These are static/deterministic guarantees; r15 runtime acceptance remains Pablo's gate.

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

The executable uses `BISLPM-66511Save`. Ordinary memory-card saves are the cross-build compatibility target. Savestates are considered build-specific. The serial `SLPM-66511` and save namespace are build invariants.
