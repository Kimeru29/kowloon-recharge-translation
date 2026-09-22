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

The prompt table at `0x586AD0` points into `m_name.c` text around `0x5869C0`. v6 packs visible official English prompts as two-byte CP932 into the verified `0x5869C0..0x586AD0` arena and repoints that table. Default/runtime protagonist name pointers are similarly redirected to wide `Habaki`, `Kuro`, `Hiyuu`, `Tatsuma`; reading strings point to a blank wide string. The original runtime name records are preserved.

## ADV horizontal-renderer transform

Reverse engineering connected the script record writer and renderer:

- record `+0x463` stores line index;
- record `+0x465` stores byte position within the line;
- pristine renderer consumes `+0x463` as X and `+0x465 / 2` as Y, yielding vertical Japanese columns;
- v6 changes four exact MIPS instructions so X uses `+0x465 / 2` and Y uses `+0x463`.

`tools/adv_layout.py` asserts the pristine instruction preimage before patching. This is a global ADV renderer-class rule, not a DG00 string exception.

## Executable translation segment / H.A.N.T. tutorial

The H.A.N.T. startup tutorial pointer table is at `0x5C8C70`. The pristine ELF's second PT_LOAD is zero-sized at virtual address `0x00902F00`; v6 activates it as a reusable translated-text segment. It appends the English payload, reserves a 1 MiB VA window, moves the heap start from `0x00902F00` to `0x00A02F00`, and repoints tutorial entries to wide official English. Exact program-header and heap-instruction preimages are enforced.

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

**v6 has not been launched. Exact visible expectations + Pablo approval remain mandatory.**
