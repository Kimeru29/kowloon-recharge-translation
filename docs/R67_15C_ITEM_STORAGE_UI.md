# r67.15c — chest / Items / synthesis / golden-lock UI diagnostic

**Status:** DIAGNOSTIC — awaiting native PCSX2 gameplay screenshots. Not a
user-approved release; do not merge or promote this new item UI candidate
until the game-level labels and interactions have been checked.

## Approved parent and boundary

The user confirmed that **r67.14z works** in the Storeroom; treat the
Storeroom name and golden-lock inscription as visually accepted. The source
is the untouched diagnostic
`local/r67-candidates/67.14z-storeroom-inscription.iso`, SHA-256
`18b390bcb230a9a69ccff284eeea39a0d00dfc6502b2526ee9895f5f38c423a6`.
The pre-existing q/t/y/z visual approvals, Lion Statue special 0.72 x-scale,
golden-lock tablet geometry, AFK/dialogue/story/rendering, and the original
save namespace are protected. Only three proven item-name text-setter JALs,
three newly identified synthesis text owners, and specific GP004 textures
are intentionally different; two older approved Lion callsites are verified
by restoring their exact predecessor JALs *in memory only* before running
the unchanged r67.14t acceptance manifest. Do not regenerate or weaken it.

## Reported issues and corrections

| # | Report | Implementation and official evidence |
| - | - | - |
| 1 | Japanese-looking emblem on chest | Kept original decorative/icon geometry. No evidence it is an interactive untranslated label. Its visual status is still subject to gameplay review. |
| 2 | Japanese room vs item storage | Imported official **Store in room**, **Store in assault vest**, and storage-choice art from PS4 EN `GP004_03`, `GP004_15`, `GP004_16`, and `GP004_18`. |
| 3 | **Hydrochloric Acid** clips | Preserved the exact official 17-cell item name; native item-list name setter at VA `0x29DC44` now scales x by `min(1,15/glyphs)`. 17 cells receive 15/17; other already-fitting names keep 1.0. |
| 4 | Japanese acquired-item heading | Imported native group4 `GP004_17` official **Items Obtained** atlas. |
| 5 | Items bottom bar labels overlap | Native GP004_19 has PS2-only baked Japanese captions, while PS4 GP004_19 EN contains no usable captions. Repainted five independent non-overlapping sprite rectangles: **Details** (official PS4 GP004_05 EN), **Compound** and **Swap** (exact PS4 English.bytes), **Discard**, **Recycle** (same PS4 English UI). Asserted per-cell width, borders and unchanged surrounding pixels. |
| 6 | Synthesis Square action/prompt Japanese | Imported official PS4 `GP004_05` item detail artwork; additionally translated **three live native synthesis text owners**: the two formatted “Compounded” notifications and “Stored in” label. Official English.bytes offsets: `0x458c9`, `0xd13c5`, `0xd13ee`. Preserved ASCII `%s` placeholders within CP932/JIS display text (PS4 uses positional `{0}`/`{1}`). Updated only pointer word `0x3861D0` and native `LUI/ADDIU` pairs `0xD660/0xD664`, `0xD718/0xD71C`; original Japanese text remains immutable provenance. |
| 7 | **Aqua Regia** clips on golden-lock item selection | Preserved exact official 10-cell name; native narrow name-renderer paths at VAs `0x2A2A6C` and `0x2A6060` now apply `min(1,8/glyphs)`, with the prior Lion Statue `0.72` override intact. Aqua Regia becomes 0.80. |

The PS4 English art for **“Choose storage location”** did *not* fit
the PS2's native first 128-pixel GP004_18 tile and overlapped **Vest**.
For r67.15b, the first caption alone was repainted as **“Choose storage”**
(semantically faithful but intentionally shorter than the remaster), using
the source parchment/background and native 128-pixel texture-cell boundary.
Adjacent **Vest** and **Room** sprites are unchanged, and the bounded image
was inspected offline. Offline atlas inspection is not proof of in-game fit.

## Candidate chain — do not overwrite prior builds

| Step | Local ISO | SHA-256 | Unique scope |
| - | - | - | - |
| r67.15a | `local/r67-candidates/67.15a-item-storage-ui.iso` | `8eb05f5cfc6cacd4f5dc58e9262b80ac720292e422c7264da3ce16f87cc8a1f0` | Six directly imported official English group4 textures, five-item footer, generic two-class item-name fit. |
| r67.15b | `local/r67-candidates/67.15b-item-storage-compact.iso` | `8c63c86d64de7cb770bab350a8728fe76db5e6825693b3614d9c559e408f7704` | Native storage heading shortened and bounded. |
| **r67.15c** | **`local/r67-candidates/67.15c-synthesis-items-ui.iso`** | **`d140cca2ce4c9603d5f89a4b0413c4dc5ddce0e1385301e9a11f376fa17368aa`** | Three official native synthesis messages; official **Details** instead of the intermediate INFO fallback. |

All candidate ISOs are **2,095,382,528 bytes**. Last-step full-disc
audits are zero-unexplained-byte exact comparisons, covering every byte,
not just the inner executable or atlas:

- z→15a: **336,020** accounted-for changes, **0** unexplained.
- 15a→15b: **2,245** accounted-for changes, **0** unexplained.
- 15b→15c: **408** accounted-for changes, **0** unexplained
  (`local/r67-15c-whole-iso-audit.json`).
- Original ISO artifacts, original PS4 corpus, item catalog pointer table,
  graphics other than the named GP004 TMX regions, original memory cards,
  and gameplay saves are not modified.

## Validation

- Focused test suite: **23/23 PASS** for item-name/texture/synthesis owners,
  preservation, mutation guards and finished-image exact-diff audit.
  See `local/r67-15c-focused-tests.log`.
- Raw startup acceptance: **154/155**. Same known
  `memory_card_8` English text fixture mismatch as previous candidates,
  not introduced by these changes. Scoped check retains original fixture
  invariants and explicitly reconciles only this known baseline condition,
  yielding **155/155 PASS**
  (`local/r67-15c-startup.json`).
- Approved r67.12 START/history single-dialogue geometry remains unchanged.
- Static memory-card descriptor SHA-256
  `27e5830aedec88451070b350897733f043dd11fef38fdab27a1dc9dd5cd5294f`.
  Save serial remains `SLPM-66511` and namespace
  `BISLPM-66511Save`. **Cross-build runtime save compatibility is not
  proven** because there is no reusable golden memory-card checkpoint.
- **Repository-wide test suite: 498 tests in 111.935 seconds, all PASS, 9 skipped**.
  Exit code 0; see `local/r67-15c-full-suite.log` and
  `local/r67-15c-full-suite.exit`. Skips are not reported as passes.
- **Visual and runtime validation have not been performed.** In particular
  the new native synthesis formatting and dynamically scaled item names
  must be reviewed on the actual PS2 UI. Avoid disturbing the user's
  active PCSX2 session or its existing saves.

## Game-level validation for user approval

Load **r67.15c** in the user's normal isolated PCSX2 setup without changing
memory-card/savestate configuration. In the Storeroom, compare the acquired
Hydrochloric Acid popup and storage buttons; enter Items and look at all
five footer actions; press Square to compound and inspect the resulting
prompt; use Aqua Regia on the golden lock; confirm all text stays within
its individual backgrounds and no button overlaps. Also revisit the
accepted Lion Statue UI and both approved Storeroom texts to detect
regressions. A subsequent user screenshot/approval is required before merge.

## Source/implementation

- `tools/r67_15a_item_width.py`: native text-setter helpers, dynamic
  2-byte cell measurement, original Lion exception.
- `tools/r67_15a_items_art.py`: six PS4 art ports and native menu footer.
- `tools/r67_15a_iso_release.py`: z→a full-disc patch and audit.
- `tools/r67_15b_bounded_storage_title.py`: 128-pixel cell-conscious title
  repaint; uses Pillow / NumPy / OpenCV only during local regeneration.
- `tools/r67_15b_iso_release.py`: a→b full-disc patch and audit.
- `tools/r67_15c_synthesis_prompts.py`: official remaster formatted
  synth messages, preimage/placeholder verification, q/t approval locks.
- `tools/r67_15c_details_footer.py`: exact one-cell official Details repaint.
- `tools/r67_15c_iso_release.py`: b→c deterministic full-disc audit.
- `tests/test_r67_15a_item_ui.py`,
  `tests/test_r67_15c_release.py`: focused owners/delta/mutation tests.

The binary ISOs and extracted PS4 artwork remain under ignored `local/`;
do not commit any copyrighted source/game data.
