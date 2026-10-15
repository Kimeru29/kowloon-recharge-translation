# r67.15f Item Panel Layout — Diagnostic Release Handoff

**Status: DIAGNOSTIC_VALIDATED_AWAITING_GAMEPLAY_APPROVAL.** The diagnostic ISO, complete-disc audit, finished-image checks and full regression suite pass. The final suite ran 550 tests: 536 passed, 14 fixture-dependent skips, zero failures/errors. Publication is tracked below; no merge or gameplay approval is implied.

**Goal:** correct the Compound/Can't backing, compact complete Items-card names, and translate the proven Items stat tiles without changing numbers, global renderers, or accepted unrelated behavior.

**Architecture:** append-only ELF helpers at two presentation-owner hooks, plus an independently pinned, palette-preserving GP004_14 pixel patch. Existing historical fixtures and tests remain immutable.

**Tech stack:** Python patch/audit tooling, PS2 EE/MIPS instructions, native CP932 glyph streams, indexed TMX graphics. Use Python 3.14 for the complete historical-fixture suite: the default Python 3.13 environment cannot read its Zstandard-compressed ZIP savestate fixtures.

**Spec:** the explicit user bug reports and constraints, with `R67_15D_GOLD_CHAINS_ITEM_UI.md` and `R67_15E_COMPOUND_BUBBLE.md` as historical context. Current user acceptance of 15d supersedes its older diagnostic status language.

## Baseline and evidence boundaries

| Artifact | Pinned identity |
|---|---|
| Tracked diagnosis base | `28536d54e8ef4839ae4b2fbdea52596001a4108b` |
| Worktree | `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67` |
| Integration branch | `fix/67.15f-item-panel-layout` |
| Parent 15e ISO SHA-256 | `442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014` |
| `local/r67-15e-compound-bubble.elf` SHA-256 | `d1dc87b0762465f4aa653e05e07af73cc593d4e716ee2575790edc617a54972e` |
| ELF size | 8,801,220 bytes |
| `local/r67-15d-group4-clean.BIN` SHA-256 | `23dfe4cf48ec3c3ecd2f583fdc2a1fea336442b369cba02264dd9f2f8e7650da` |
| Output name | `67.15f-item-panel-layout.iso` |

The six original comparison attachments are unavailable. Read-only observation of the already-running PCSX2 Items screen confirmed oversized/spaced card titles, Hydrochloric Acid overflowing, and Japanese ammo unit 発 beside otherwise acceptable `50/50`. It did not validate the action bubble or an implemented fix. No emulator input, settings, session, card, or savestate changes were made by this diagnosis.

All instruction findings below concern the pinned native ELF, not inferred source-language implementations. No full native game execution or visual approval is claimed from static analysis or arithmetic tests.

## Global constraints

- No name shortening, catalog-pointer changes, global font/renderer modification, or numerical-stat changes.
- Preserve accepted 15d behavior except these explicit presentation corrections. Keep historical tests and immutable historical fixtures intact.
- Preserve recipe titles, trade-name helper, acquisition/Lion behavior, history/save/AFK owners, footer DETAILS/COMPOUND/SWAP, and all unrelated graphics.
- Native and art patches fail closed on exact preimage identity; new ELF helpers are appended rather than overwriting old helpers.
- Report static verification, isolated native execution, contact-sheet inspection, ISO audit, and game screenshots separately.

## 1. Compound backing: owner, pivot, and lifetime

Action callback VA `0x114A20` gets private owner `s0` through object `+0x3C`. Owner `+0` is the backing sprite; `+8` is text; `+0x0C/+0x10` are origin; `+0x18` action ID; `+0x1C` state.

Creation calls `0x107D60` for group4/type `0x5E` or `0x5F` at `0x114AC8` / `0x114AA0`. Records VA `0x455440/0x455470` have widths96/144, height32, pivotX **-29**, pivotY-3, texture13. Sprite fields: X `+0x3C`, Y `+0x40`, X scale `+0x60`, Y scale `+0x64`; X is not `+0x50`.

Instruction proof:

- `0x107F8C: E640003C` writes constructor X; `0x107F90` writes Y.
- `0x107FBC: AE420060` initializes X scale1; `0x107FC0` initializes Y scale1 independently.
- `0x1072B4..C0` loads scale and resource pivot, multiplies, and negates to form local left.
- `0x1072DC..F4` forms `scale*(width-pivot)-1` for local right.
- `0x1076A8: C622003C` loads sprite X; `0x1076E4` adds it to each vertex.

```text
left  = X - scale*pivotX
right = X + scale*(width-pivotX) - 1

15d: X=P, scale=1 -> left=P+29
15e: X=P, scale=2 -> left=P+58  (29-pixel regression)

inverse correction: Xnew = Xold + pivotX*(scaleNew-scaleOld)
Compound: Xnew=P-29, scaleNew=2 -> left=P+29, right=P+220 (type5E)
```

Redirect existing VA `0x114AD8` / FO `0x14B58`, currently `0x0825924F` (`j 0x96493C`), to a newly appended helper. Keep its NOP delay slot and old15e helper intact. Only action3/Compound and action1/Can't with a non-null backing receive the scoped corrections. Resume `0x114B00`, preserving `a1=0` for the native alpha loop and other live state.

Position lifetime is proven: action state1 (`0x114BB4..0x114D48`) changes fade alpha and an auxiliary display, not backing X/Y. Its four registrations initialize owner coordinates once at `0x11C040/44`, `0x11C178/17C`, `0x1251B0/1B4`, `0x125304/308`. The shared renderer's X/Y overwrite at `0x107000/04` is only the 3D projection branch, guarded by byte `sprite+0x92 == 1` at `0x106F08..10`. This 2D constructor clears that byte at `0x108020`; it takes the branch to `0x10708C`. No second lifetime hook is required.

## 2. Can't: complete parser input, insufficient backing

Actual string VA `0x964968`: `8262 8281 828e 8166 8294 00`, decoded `Ｃａｎ’ｔ`. Font0 map VA `0x77CC00` resolves all five characters to `[100,124,137,26,143]`. The final t is present and mapped, not a fallback.

Parser `0x1952F0` advances input/output two bytes and increments count at `0x19544C..458`, then appends `0xFF0F`. Constructor `0x189E40` checks fewer than256 glyphs at `0x189F80`; its stored string capacity is510 bytes (`0x189FBC`, `0x189FD8`). There is no four-glyph limit here.

Action text starts `(P+51,Y+6)`; font0 descriptor VA `0x5D77D0` gives width16/height18, with spacing0 and scale1. Native quad right at `0x18DCA0..B8` is `cursor+16*scale-1`. Thus Can't's last quad ends `P+130`; type5E backing ends `P+124`, six pixels too short. This proves undercoverage, not the exact runtime clipping/scissor mechanism in the unavailable screenshot.

Action1 correction: X scale1.25 and X `P-7.25`. Left stays `P+29`, right becomes `P+148` on type5E. Retain full string, parser, font, text position, and Y geometry. Apply the same pivot equation to type5F, with its own native width.

## 3. Regular and equipped Items-card names

The two screen modes have separate title instances but converge on one title constructor, not two guessed sites:

- `H_ItemPnlDraw2` callback `0x117250` calls initializer `0x10D7D0` at `0x117298`.
- Private `+0x134` mode0 selects group4/type`0x3D`; modes1-5 select type`0xA7` and equipment badges from GP004_11.
- Items screen assigns equipped modes at `0x117A58..78`, then creates the card at `0x117A88`.
- Name lookup is `0x134AB0` at `0x10DA80`.
- Title JAL **`0x10DAC4` / FO `0xDB44`**, original word **`0x0C062790`**, invokes `0x189E40`; result is stored in private **`+0x130`** at `0x10DACC`.

Preserve title origin `(panelX+36,panelY+3)`. Ordinary backing width240/pivotX0 ends `panelX+239`; equipped width240/pivotX2 ends `panelX+237`. A196-pixel title budget retains at least6 pixels on the tighter card. This changes only the shared card-title presentation owner, not every font0 user; the same card class is reused in additional item-panel contexts.

Engineering metrics, subject to visual acceptance: X scale cap0.625, Y scale0.75, added letter spacing0. Normal glyph cells become10 pixels wide and13.5 high before long-name fitting. These are not claimed to be exact official PS4 font metrics.

### Spaces are a separate native consumer

Fullwidth CP932 space becomes control`0xFF0B`. It advances **unscaled16**, through `0x18CCD4/D8` and `0x18E114/118`. A naive `glyphCount*16*scale` oracle is therefore wrong.

For this title instance only, replace generated `0xFF0B` space nodes with native `0xFF0A` halfwidth-space controls, advancing8 at `0x18E0C4..DC`. Keep the stored CP932 name and all catalog bytes unchanged. Read private data via returned text handle`+0x3C`; linked stream starts private`+4`, next pointer node`+0x120`. Count ordinary glyphs G and spaces S, preserving all other node data.

```text
scaleX = min(0.625, (196 - 8*S)/(16*G))  for G>0
scaleY = 0.75
ordinary advance = 16*scaleX; space advance = 8
```

Call native scaling setter **`0x18B120`**, which writes private`+0x48/+0x4C` then calls **`0x18CB50` to rebuild geometry**. Merely writing scale after construction is insufficient. Wrapper preserves constructor inputs/ABI, returned handle in v0, null behavior, and caller state. Bound traversal; validate the plain-name token assumptions against the446 valid name records exercised by the implementer. Empty/all-space/unsupported control streams must not divide by zero or corrupt nodes.

Actual samples: Hydrochloric Acid17 cells, Nitric Acid11, 9mm Luger9; longest catalog name has27 cells. Test the actual parsed streams, including their spaces.

### Catalog coverage correction

The earlier diagnosis called the preserved500-word region "500 catalog names"; that was incorrect. Source-only reinspection of the pinned15e ELF confirms that `0x134AD0` compares the input ID with500 to choose a lookup branch, not to declare a500-record table. The primary base is VA`0x491234` / FO`0x3912B4`. Record445 points to VA`0x92CF9C` (`Ochimizu`); entry446 is null, and entry447 is`0x93834383`, adjacent data rather than a valid mapped name pointer. Inputs>=500 use the separate indexed base at VA`0x4913A0`; sentinel0xFFFF has its own lookup at VA`0x491230`.

Therefore distinguish **446 valid primary name records exercised** from **the500-word region preserved byte-for-byte**. A preservation lock over adjacent data is useful but is not additional name coverage. This does not claim exhaustive alternate-ID/sentinel execution. Targeted native verification covered those446 valid records in12 passing tests with498 subtests; see the validation ledger for run qualifications.

Excluded sites: `0x29DC44` is actually `m_trade.c`, despite the older15a module description; do not repurpose that accepted helper as an equipped-card fix. `0x115458/54C/5BC` belong to synthesis recipes; `0x14B57C` is `H_CmdIconDrawSub`, not this title. Preserve acquisition/Lion sites `0x2A2A6C/0x2A6060`.

## 4. GP14 art: actual owner versus imported GP05

15a imported official GP004_05 already. That does not translate these native labels: their sprite records still sample **GP004_14**. Inspect the installed pinned container, not only old `local/r67-15a-analysis/GP004_05.png`.

GP14 is128x128, PSMT4, linear packed nibbles. Pixel base is **`0x88980`**; palette is **`[0x88940,0x88980)`**, preserved byte-for-byte. Pixel x-even uses low nibble, x-odd high nibble. No spatial pixel swizzle is required; the existing TMX 8-bit CLUT swizzle is irrelevant here.

GP14 complete chunk SHA: `d344ae4cd1d7616b018014656cda58c620e94be722635d754b29f7d2714f97f6`.
Palette SHA: `d3ebd91a23673e0304fa91fc0461fc648d0ab3f4cb011749560dde4e89c60682`.

### Eight labels copied from official word artwork

Source `local/r67-15a-analysis/ps4-GP004_05_en.png`,576x1152; file SHA `3d35b93c25f6c611411e4fa75f62c45977a78caa124a05a5985e66b0ac6d3e6b`; decoded RGBA SHA `07ccdd23ee525bdd2f2b6efb009b00be33d64fabe252e8b5c4902eec7eb5062d`.

All rectangles below are half-open `(left,top,right,bottom)`.

| Label | Source window | GP14 destination | Sprite |
|---|---|---|---|
| Shots | (190,310,241,335) | (0,0,24,16) | 0x17 |
| ATK | (245,310,311,335) | (88,16,128,32) | 0x18 |
| Range | (321,310,383,340) | (64,0,104,16) | 0x19 |
| AP | (197,344,231,372) | (56,16,88,32) | 0x1A |
| Durability | (233,344,319,375) | (0,16,56,32) | 0x1B |
| Absorption | (321,344,409,375) | (0,32,40,48) | 0x1C |
| Recovery | (197,381,284,409) | (40,32,80,48) | 0x1D |
| Increase | (291,381,375,408) | (24,0,64,16) | 0x1E |

Extract near-white foreground with min(R,G,B)>=128 and max-min<=32; coverage=`round(min(R,G,B)*A/255)`, else0. Tight-crop mask, fit uniformly in `(tileWidth-2)x14`, center with transparent padding, LANCZOS resample, then map coverage to nearest existing palette alpha with lowest-index tie break. No source brown background/RGB is copied. Pin the source-mask hashes below in the art report/tests. The resulting first-eight-label contact sheet is legible; this is offline art inspection, not gameplay approval.

SHA-256 of each row-major, one-byte extraction mask before tight cropping or resampling:

```text
Shots      a4dadbf71138071434cf10d02e7fb87c5ee6826e9c6b208331038595388e2ecd
ATK        a5a2a6ea7350063ba1d2c35cc07bf357e4469d2164ac6b77994f62cd4fb2d072
Range      69a8527ea0be1d1cf2c5373a7d8df3055e6124299518d67617a142d3939ca640
AP         bd78cc05b3775b0771bb96f5f25a67609ca9c6ab46b748fc5542276b59820044
Durability a2a1883ac089f73106c3b4bb807b04a1712a7150406b2781cfb0498fd04308c1
Absorption beb13aec7525fdc4846928a36965a848daf9b0c8e67e5d9f4f2262319023eb17
Recovery   fd9d15eabbb3cfe2c1438940f44eefc475b4c6aaa8ba1f64dc82ed5b2323a3c2
Increase   ca5d2ba66a83a883bd0c4118c2c7c1d73d1992046afa140fabe751554d9e5605
```

### Eight additional locally rasterized attribute tiles

Official terms come from `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`, SHA **`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`**. These are not copied official baked word crops. Preserve full spellings; invent no abbreviations.

| Native | English | GP14 destination | Sprite | Corpus row |
|---|---|---|---|---|
| 身体 | Strength | (40,80,72,96) | 0x51 | 0x29F76 |
| 知性 | Mind | (80,32,112,48) | 0x52 | 0x29F94 |
| 生命 | Vitality | (40,64,80,80) | 0x53 | 0x29FAE |
| 精神 | Spirit | (0,64,40,80) | 0x54 | 0x29FCC |
| 洞察 | Insight | (40,48,80,64) | 0x55 | 0x29FE8 |
| 直感 | Instinct | (0,48,40,64) | 0x56 | 0x2A005 |
| 敏捷 | Agility | (0,80,40,96) | 0x57 | 0x2A023 |
| 直・精 | Instinct / Spirit, two lines | (0,98,40,114) | 0xB5 | separate terms above |

The combined treatment is an explicitly authorized localization: compose the two full source-proven components on separate lines. **Do not claim an exact official PS4 combined phrase or abbreviation.** The release report identifies the local rasterizer artwork as pinned Arial, not copied official word art. Retain the font identity, sizes, fit algorithm and resulting masks in implementation evidence. Preserve all palette, numeric owners, sprite geometry and UV data. All full terms are readable in the inspected final contact sheet, including Strength and the two-line Instinct/Spirit; this is offline approval only.

**Reproducible rasterization requires explicit `ImageFont.Layout.BASIC` in every production and test-oracle font load.** Matching Pillow12.3.0 and FreeType2.14.3 versions alone is insufficient: the Python3.13 wheel defaulted to BASIC, while the Python3.14 wheel included RAQM and defaulted to different shaping, changing attribute pixels. This was a real reproducibility defect, not an acceptable environment-dependent output variation.

The corrected font loads and full-output SHA-256 regression pin preserve the original candidate's complete GP004 container hash **`9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a`**. All16 art/release tests pass without skips under both Python3.13 and Python3.14, including the finished-ISO audit. The existing ISO remains byte-identical at **`e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0`**; no replacement ISO is needed for this tooling correction. These targeted results do not substitute for the final full-suite run.

Consumer proof: Items category6 dispatch `0x10DB78 -> 0x1114A0`; item-specific data`+0x32` selects `0x51+selector` for0-6 at `0x111500..14`, or `0xB5` for selector0x14 at `0x11151C..30`. Group4/type from s2 is created at `0x111574` and stored in card private`+0x160`. These tiles are in scope, not unrelated status art.

Exact combined lookup: group table VA`0x485240`; group4 pointer VA`0x485250` / FO`0x3852D0` contains`0x4811A0`. Type0xB5 entry VA`0x481748` / FO`0x3817C8` contains `(0x457F00,1)`. Record VA`0x457F00` / FO`0x357F80`, interpreted `<HH11f>`, has flags0, texture14, width40,height16,pivots0,UV`(0,0.765625,0.3125,0.890625)`. This yields `(0,98,40,114)`. The exact15e source-chain regression passes. The earlier texture6/120x40 observation came from an inapplicable lookup; no alternative atlas mutation is required or authorized.

### Recovery of temporary official-source fixtures

Temporary PS4 corpus/BLBRD assets were recovered after becoming unavailable. This is environment/fixture recovery, not a historical-module change:

- Source: the user's owned PS4 package, verified SHA-256 **`054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314`**.
- Extractor: `maxton/LibOrbisPkg`, pinned commit `643477263b2644e0803e0f58b8726ea4e3f3b7d4`, cloned into scratch directory `/tmp/kowloon-15f-extractor.JtU7E1` and retargeted there to .NET10.
- The default-key attempt failed; the standard zero-passcode path worked for this owned package.
- Scratch `PFSCReader` initially assumed one `DeflateStream.Read` filled the requested buffer. Under the newer runtime, a short read caused corrupted extraction. The scratch reader was corrected to loop until the exact requested length was read, rather than accepting a partial buffer.
- The freshly extracted corpus parses **11,711 records** and matches the original complete SHA-256 **`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`** exactly.
- Recovery restores absent corpus/BLBRD fixtures without overwriting existing files. Historical project modules and tests remain unchanged; corpus identity does not substitute for individual BLBRD identity checks.
- The art module's missing-corpus fallback was removed. Official-source absence or identity mismatch fails closed, with negative regression coverage. A fallback, skipped provenance check or locally substituted term list is not verified official-source evidence.

The extractor fix is confined to scratch tooling; it is not an additional project patch or a reason to relax any source hash. Fresh integrated historical tests are still required after fixture recovery.

## Patch interfaces and exact audit contracts

Native module: `tools/r67_15f_item_panel_layout.py`; `apply(old: bytes) -> tuple[bytes, dict]`.

The exported mapping contains only existing native owner-hook ranges. The release builder separately owns/permits translation-segment size metadata and rejects that metadata range inside this export:

```python
PERMITTED_EXISTING_RANGES = {
    "action_backing_creation_hook": ((0x14B58, 0x14B5C),),
    "item_card_title_constructor": ((0xDB44, 0xDB48),),
}
```

The complete allowed existing-byte delta is the union of these two hook ranges and builder-owned metadata **`[0x64,0x68)`**. Do not include a `translation_segment_filesz` entry in `PERMITTED_EXISTING_RANGES`. This is a contract distinction, not permission for additional native edits.

All ranges are half-open file offsets. Original VA-to-FO bias is`0xFFF80`; appended translation segment FO`0x803150`, VA`0x902F00`, capacity`0x100000`. Align new helpers, preserve every prior byte outside the complete allowed delta, account for segment size through the builder's separate metadata contract, and report helper VAs/preimages/deltas. Existing string pointer for Can't and old helper bodies stay intact.

Art module: `tools/r67_15f_item_panel_art.py`; `apply(old: bytes) -> tuple[bytes, dict]`; `TARGET_TMX = 'GRP004/GP004_14.TMX'`. Export `PERMITTED_ART_RANGES` with named absolute container-byte ranges for the16 tiles. For each destination rectangle:

```python
tuple((0x88980 + 64*y + left//2,
       0x88980 + 64*y + right//2)
      for y in range(top, bottom))
```

All boundaries are even; no neighboring nibble is shared. Preserve every byte outside these ranges, every outside-tile decoded pixel, palette, punctuation including sprite0x1F/0x58, all other TMXs, and container metadata. No global atlas import.

The release builder `tools/r67_15f_iso_release.py`, covered by `tests/test_r67_15f_iso_release.py`, integrates independent ELF/art outputs into the exact15e source and audits the entire disc.

### Built diagnostic artifact and report evidence

Evidence: `local/r67-15f-release.json`, `local/r67-15f-whole-iso-audit.json`, `local/r67-15f-startup-raw.json`, `local/r67-15f-startup.json`, `local/r67-15f-history.json`, and `local/r67-15f-save-static.json`. Results below reflect the inspected reports, not an independent rerun or implementation review.

| Built artifact/property | Recorded result |
|---|---|
| ISO | `local/r67-candidates/67.15f-item-panel-layout.iso` |
| ISO SHA-256 | `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0` |
| ELF | `local/r67-15f-item-panel-layout.elf` |
| ELF size / SHA-256 | 8,801,784 bytes / `418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1` |
| Appended backing helper | VA`0x964974`,180 bytes; hook word`0x0825925D`, resume`0x114B00` |
| Appended title helper | VA`0x964A28`,384 bytes; title hook word`0x0C25928A` |
| ELF growth | 564 bytes total; whole-disc comparison finds334 differing nonzero appended bytes |
| Actual changed existing ELF offsets | `0x64`, `0x65`, `0xDB44`, `0xDB45`, `0xDB46`, `0x14B58` |
| Audit status | `PASS_EXACT_15E_BASELINE_ZERO_UNEXPLAINED` |
| Complete disc compared | 2,095,382,528 bytes |
| Changed / unexplained bytes | 3,545 / **0** |
| Other art | All non-GP004_14 assets unchanged, explicitly including GP004_18 and GP004_19 |
| Other native owners | Unchanged per whole-disc audit and prior approval locks |

Changed-byte accounting, not sizes of permitted ranges:

```text
3,201 GP14 pixel bytes
  334 appended nonzero payload bytes
    1 action-hook byte
    3 title-hook bytes
    2 ELF segment-length bytes
    4 ISO9660 executable-size bytes (both endian copies)
-----
3,545 changed bytes; 0 unexplained
```

Exported owner ranges exclude `[0x64,0x68)`, while the native module's internal complete-delta guard retains its metadata allowance. This interface has a dedicated regression test. The initial native targeted run predates that interface correction; its counts are not a post-correction full-suite result.

Finished-image static gates:

- Raw startup: **154/155**. Sole failed check is `memory_card_8`, with legacy diagnostic "memory-card entry 8 does not resolve to official English".
- Scoped startup: **155/155**, with exactly one explicit legacy wording exception for the reproducible bounded15y saving message: blank line, `Saving...`, `Do not remove/insert`, `memory card (PS2) or`, `turn off the power.` Its maximum width is20 cells over5 rows. This is not a silent test weakening; `q_t_lock_exceptions` is empty.
- History: **4/4** regions — `adv_history_layout_and_row_spacing`, `adv_history_font_creator`, `history_horizontal_constructor_clone`, `history_chronological_ring_helper`.
- Q lock: `PASS_R67_14Q_VISUALLY_APPROVED_OWNERS`; T lock: `PASS_VISUALLY_ACCEPTED_LION_AND_STONE_TABLET_STATIC_OWNERS`; inspection/save result: `PASS` in the release manifest. These preserve earlier accepted owners, not new15f visual acceptance.
- Save identity:15 native descriptors, SHA **`27e5830aedec88451070b350897733f043dd11fef38fdab27a1dc9dd5cd5294f`**, namespace **`BISLPM-66511Save`**, serial **`SLPM-66511`**. Original cards/savestates remain unmodified. Golden checkpoint unavailable; cross-release runtime test not performed; status `STATIC_ONLY_NO_GOLDEN_CHECKPOINT`.
- Reports explicitly retain `gameplay_approved=false`, `runtime_verified=false` where applicable, and `runtime_save_compatibility_verified=false`. Static startup validation is not a cold-boot screenshot or a demonstrated save/load test.

## Consumer-space regression coverage

Completed evidence gates:

- [x] Isolated native execution covers the title constructor, instance scaling setter and glyph consumer, including446 valid primary name records.
- [x] Isolated native bubble geometry/fade execution validates the scoped correction; this is not full-game screenshot evidence.
- [x] The exact15e B5 pointer-chain regression resolves the combined GP14 consumer.
- [x] Offline inspection confirms all16 full English labels are readable in the contact sheet.
- [x] The finished-image whole-disc audit accounts for every changed byte; startup, history, Q/T and static save-identity gates pass as qualified above.
- [ ] The Python3.14 full-suite rerun must establish the final integrated result.
- [ ] Gameplay screenshots and runtime save compatibility remain unverified.

Acceptance contracts retained for the regression suite (not additional execution-count claims):

- Bubble tests reproduce15e +29 left drift using actual resource records and native vertex arithmetic; corrected left equals15d for positive/negative origins and both widths. Right grows by `width*(newScale-1)`; Y/pivot/UV unchanged.
- Execute/helper-test all16 action IDs with null/non-null sprites, correct continuation/registers, repeated state1 fades, and 2D versus3D lifecycle branch conditions. Do not substitute stored-scale assertions for vertex bounds.
- Can't tests use actual encoded bytes, five native mapping entries, parser terminator/count, and all five quad extents. Preserve text bytes; reproduce original six-pixel backing undercoverage.
- Card tests cover mode0 and equipped modes1-5, actual constructor return/instance setter relayout, ordinary glyphs and both space controls, the446 valid full-name records, empty/null inputs and bounded malformed streams. Evaluate generated quads/advances within196 pixels. Separately byte-lock the500-word region; do not count adjacent data as valid names.
- Assert strings/catalog pointers, numeric child handles/formatters, badge/backing data, trade/recipe/acquisition/Lion/history/save owners and global renderer/font descriptors unchanged.
- Art tests decode actual output and sample native resource UVs; independently compare masks, palette, outside-tile pixels and absolute byte-range deltas. Pin copied-source masks and local-rasterizer provenance separately. Cover all16 consumers including Shots and the exact combined lookup.
- Run historical tests unchanged against historical fixtures, targeted new suites, deterministic repeat builds, and the full source15e-to-output disc audit. Record actual commands/counts/skips without turning a skip into a pass.
- Eventual explicitly authorized game screenshots must show complete names, both actions, quantities, and attributes. No emulator controls are implicitly authorized by this handoff.

## Exact screenshot acceptance checklist

These are future acceptance requirements, not authorization to manipulate the running session. Obtain them from user operation or a subsequently authorized test session. Associate each screenshot with the audited candidate ISO SHA, screen/state, and item/action. Record unavailable cases as pending rather than inferring them from a nearby screen. Do not overwrite any existing card/savestate or change emulator settings to obtain evidence.

| Capture | Required visible evidence |
|---|---|
| Compound action, type5E | Entire word including `Co` lies inside white backing; original left anchor is preserved; only right extent grows; original text origin and vertical placement remain intact. Compare with a matching original/15d reference if available, otherwise do not claim measured runtime anchor equality. |
| Compound action, type5F | Same acceptance for the alternate wider backing; do not infer this branch from type5E. |
| Same-item Can't | All five glyphs including final t are visible inside the backing; apostrophe retained; no substitution, shortening, or shifted text. Capture alternate backing mode too if reachable. |
| Bubble stable/fade frames | Early visible and settled frames show no later position snap, repeated compensation, or left drift. Static lifetime proof alone is not a screenshot of this behavior. |
| Regular Items cards | Hydrochloric Acid, Nitric Acid and9mm Luger shown completely at compact spacing, within the right border. Preserve card origin, icons and DETAILS/COMPOUND/SWAP footer. Include at least one ordinary non-weapon card. |
| Equipped Items cards | Actual equipped weapon names on the equipped-card backing, including a long available name; no shortening, clipping or badge overlap. Cover the available equipment slot variants; mark unobserved modes pending. |
| Long-name case | A long available catalog name, preferably the27-cell case if accessible without changing user data, remains complete and legible. The446-name isolated test coverage is separate evidence, not proof of446 live screenshots. |
| Ammo count | `50/50` or the current known count is unchanged, with `Shots` visible instead of 発; native count and unit positions remain intact. Do not create or consume ammo merely to match50/50. |
| Core stats | Applicable cards expose ATK, Range, AP, Durability, Absorption, Recovery and Increase; numeric values, signs, units and alignment remain unchanged for the same item/state. Use multiple cards as necessary. |
| Attributes | Applicable cards expose Strength, Mind, Vitality, Spirit, Insight, Instinct and Agility in full. Include the combined native selector0x14 case showing full Instinct/Spirit on separate lines if accessible. No guessed abbreviations. |
| Preservation spot checks | Existing user-reachable acquisition/Lion, trade, recipe and other accepted presentation remains unchanged; do not initiate new gameplay solely to manufacture these captures without authorization. |

Retain full-screen context with any close crop. Assess at native logical scale as well as the displayed screenshot scale; a magnified contact sheet does not establish in-game legibility. Missing original PS4 comparison images prevent an exact visual-match claim.

## Essential remaining uncertainties

- Native byte/parser/layout evidence proves Can't undercoverage, but the unavailable original action screenshot prevents distinguishing background contrast, actual clipping and other runtime visibility effects. Final-t screenshot acceptance remains mandatory.
- Title metrics are a bounded engineering fit, not measured PS4 typography. Generated spaces and glyphs must both be consumed in tests; instance scale alone is not proof of compact advances.
- `H_ItemPnlDraw2` is a shared item-card presentation class. Its title-instance correction is deliberately not a global renderer change, but other screens reusing that same class can inherit its title metrics; preservation checks must not claim otherwise.
- Attribute rasterization and the combined two-line treatment are local artwork using official component terms. Only the first eight labels are copied official word artwork.
- The diagnostic ISO identity, whole-disc audit and full regression suite are established by the reports above. In-game visual acceptance and cross-release save/load behavior remain unverified. No further native-owner investigation is required unless a new defect exposes a concrete contradiction.

## Validation ledger

| Gate | Current evidence |
|---|---|
| Native diagnosis | Owners, pivot inverse, lifetime, parser, card paths and space-consumer behavior traced in pinned ELF |
| Art provenance | Eight copied official word crops; seven official corpus terms; one explicitly composed two-line label |
| Art/release targeted tests | 16/16 pass in both Python 3.13 and 3.14, including the finished-ISO audit; no skips |
| Final16-label contact sheet | All full terms readable offline, including Strength and two-line Instinct/Spirit; not gameplay proof |
| Native targeted tests | 12 tests with 498 passing subtests, exercising 446 valid name records; all native tests also pass in the final full suite |
| Metadata-export contract | Export excludes metadata, internal complete-delta guard preserved; dedicated regression added |
| Isolated native execution | Constructor/setter/glyph consumer and bubble geometry/fade paths executed; not full-game runtime visual approval |
| Official-source recovery | 11,711 corpus records; exact original corpus SHA; non-overwriting fixture recovery |
| Art fail-closed provenance | Missing-corpus fallback removed; negative fail-closed regression coverage |
| Combined attribute owner | Exact15e B5 pointer-chain regression passes |
| Extended16-tile art tests | Source rows, native UV consumers, palette/outside-tile preservation, explicit BASIC layout and exact output hash pass |
| Diagnostic ISO identity/full audit | Reports inspected: SHA`e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0`; 2,095,382,528 bytes compared,3,545 changed,0 unexplained |
| Finished-image startup | Reports inspected: raw154/155; scoped155/155, only explicit `memory_card_8` exception |
| Finished-image history/save | Reports inspected:4/4 history regions;15 save descriptors exact; Q/T pass; runtime save compatibility unverified |
| Fresh full suite | **550 tests run, 536 passed, 14 skipped, zero failures/errors**, 131.781s, Python 3.14; `local/r67-15f-full-suite-final.log` |
| Commit/PR/release publication | Implementation commit `f9692361e4af30a475f54ed1ea351cbb3f055b03`; pushed [draft PR #50](https://github.com/Kimeru29/kowloon-recharge-translation/pull/50), stacked on PR #49; not merged |
| Runtime visual approval | Pending; no-input constraint remains |

Historical attempts: an earlier focused historical run recorded38 passes,1 skip and7 environment errors from absent corpus/UnityPy. The first full-suite attempt ran550 tests in111.852s, with9 errors and14 skips; all9 errors were reads of immutable Zstandard-compressed ZIP `.p2s` fixtures under the default Python3.13 environment. Its log is preserved as `local/r67-15f-full-suite.log`. The same runtime limitation is documented for14y. The rerun uses the already-installed **`/opt/homebrew/bin/python3.14`**, with no fixture or test changes. Neither failed attempt is a green suite result.

The first Python3.14 rerun ran550 tests in122.701s, with1 error and14 skips (`local/r67-15f-full-suite-python314.log`). Unlike the earlier ZIP-reader failures, its error exposed the genuine BASIC-versus-RAQM rasterization reproducibility defect described above. After the explicit-layout fix and cross-interpreter targeted verification, the fresh full suite passed in **`local/r67-15f-full-suite-final.log`**: 550 tests run, 536 passed, 14 skipped, zero failures/errors, 131.781 seconds.

The 14 skips are existing optional historical ISO/build-report, pristine extraction, copyrighted fixture and legacy corpus-path checks. None is a new r67.15f test. Historical q/t/history ISO-fixture skips do not replace the separately successful checks against the finished r67.15f executable. The full skip list remains in the final log. Static validation and readable contact sheets do not establish complete in-game translation or visual approval.

Reproduce the full suite from this worktree:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with unicorn --with capstone --with numpy \
  --with opencv-python-headless --with UnityPy \
  python -m unittest discover -s tests -v
```

The builder `python -m tools.r67_15f_iso_release` refuses to overwrite any existing diagnostic artifact. To recheck the existing image, call `tools.r67_15f_iso_release.audit()` or run its finished-disc regression; do not delete or replace the ISO merely to repeat the build. Explicit BASIC layout and the exact GP004 output hash guard against environment-dependent rasterization drift.

## Preserved releases and publication

The earlier 15b/15c/15d images were restored only to absent paths from preserved, pinned assets. Their complete SHA-256 values, and the unchanged 15e source, were verified:

| Release | SHA-256 |
|---|---|
| 15b | `8c63c86d64de7cb770bab350a8728fe76db5e6825693b3614d9c559e408f7704` |
| 15c | `d140cca2ce4c9603d5f89a4b0413c4dc5ddce0e1385301e9a11f376fa17368aa` |
| Accepted 15d | `5d5850b660e92d9fd0dcb11456519d99b060cbaae131ebf48f6d0f80262a446d` |
| Parent 15e | `442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014` |

Branch: `fix/67.15f-item-panel-layout`. Stacked base: `fix/67.15e-compound-bubble`, parent [draft PR #49](https://github.com/Kimeru29/kowloon-recharge-translation/pull/49). Implementation commit: **`f9692361e4af30a475f54ed1ea351cbb3f055b03`**. Published [draft PR #50 — Fit compound bubbles and compact item cards](https://github.com/Kimeru29/kowloon-recharge-translation/pull/50). This publication-metadata update is documentation-only; the implementation and audited ISO are unchanged. The original worktree is retained. No merge is authorized before explicit user approval of new gameplay screenshots.

## Return prompt for the next handoff

```text
Continue Kowloon r67.15f from docs/R67_15F_ITEM_PANEL_LAYOUT.md in
/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67.
Branch: fix/67.15f-item-panel-layout. Draft stacked PR #50:
https://github.com/Kimeru29/kowloon-recharge-translation/pull/50
Implementation commit:f9692361e4af30a475f54ed1ea351cbb3f055b03.
Continue the diagnostic release handoff;
do not restart completed diagnosis or review implementation absent a reported
bug. Preserve unrelated work, historical tests and immutable fixtures.

Built diagnostic: local/r67-candidates/67.15f-item-panel-layout.iso
SHA256: e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0
Parent15e SHA256:
442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014
ELF SHA256:
418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1

Use the document's pinned owner, art-source and audit contracts. Whole audit:
2,095,382,528 bytes,3,545 changed,0 unexplained. Startup raw154/155 and scoped
155/155 differ only by the explicit memory_card_8 exception; history4/4,
15 save descriptors exact, Q/T locks pass. Keep446 exercised valid names
distinct from500 byte-locked words, and copied artwork distinct from local
rasterization. Metadata0x64..68 is builder-owned, not in the native export.

Use /opt/homebrew/bin/python3.14 for historical Zstd ZIP fixtures. All font
loads require explicit ImageFont.Layout.BASIC; preserve the full GP004 hash
9e6450469c6d7628c1d9e7af0f7ac96278c97bc79c380c2c6a6543d65317786a.
The BASIC fix preserves the existing ISO. Cross-interpreter art/release tests
pass16/16 with no skips. Final full suite:550 tests,536 passed,14 fixture
skips,0 failures/errors; local/r67-15f-full-suite-final.log. Preserve earlier
failed logs as provenance. Use the publication section for the draft PR.

Continue from the user's new screenshots or next explicitly requested task.
No emulator input, settings, session, card or savestate changes are authorized.
Runtime visuals and save compatibility remain unapproved. Use the exact
screenshot checklist for user-supplied captures or a separately authorized
test session. Missing PS4 comparisons prevent an exact visual-match claim.
```
