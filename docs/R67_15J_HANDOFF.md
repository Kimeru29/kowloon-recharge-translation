# r67.15j — bounded item text and Help layout

## Release and acceptance

This diagnostic addresses the remaining Details and recipe overflow, Help
icon/paragraph association, Japanese Place/Take actions, and overwide dungeon
inspection text. The user confirmed that the doorway transition and HANT body
visibility work in the preceding build. Those fixes are retained.

Worktree: `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.
Branch: `fix/67.15j-generic-text-bounds`.
Base: `a7a029c9ce51b3691ff37fbfbf051d7a6f0bc1db` (main, r67.15i).
The user explicitly authorized integration into main. That is not visual
approval of this diagnostic. No PCSX2 configuration, session, memory card,
save, or savestate was changed. Every prior release remains in place.

Artifact: `local/r67-candidates/67.15j-generic-text-bounds.iso`.

| Artifact | SHA-256 |
|---|---|
| r67.15j ISO | `26ced321471b4415c2a855079c778502ed7c043d2e9467c8c1edc1833b58a079` |
| r67.15j ELF | `6ebb80d3346f4f5ab68bc49197419658603b14686e4a8b549b451c1c8d7e76d8` |
| Input r67.15i ISO | `ab31dd12eae33beace62b00f7fb7765c203959b210747071668a61c87eb3dafc` |
| Input r67.15i ELF | `ffd1fb3f912268d589c19b607eeed68899ac0c31151c731aac59afeb913c8096` |
| Official English corpus | `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b` |

The local JSON reports are `local/r67-15j-generic-text-bounds.json` and
`local/r67-15j-whole-iso-audit.json`. Proprietary assets and extracted prose
remain local; source code records their identities and native owners.

## Root causes and native owners

### Item Details and recipe names

The previous Details budget treated 220px as available inside the decorative
256px frame. It allowed text into its right-hand border. Additionally, native
space advances do not scale with glyphs: the original builder at
`0x18CB50..0x18E1F0` advances full spaces by 16px and half spaces by 8px,
regardless of horizontal glyph scale. Newline pitch is independent too.

Details starts at `(26,16)` in group 4/type 0x0B. The new 198px width ends at
224, a conservative inset selected from the original decorative texture. This
is not a claimed native clipping boundary. The vertical budget remains 60px.
For each row the helper counts glyphs and spaces separately, then selects the
minimum scale satisfying `glyphs * 16 * scale + spaces * 8 <= width`.
Space normalization occurs only after the entire bounded node list validates.
All 431 installed description records, including original-language fallbacks,
are exercised against the original native quad builder.

The three recipe constructors still used the older helper, which rejected the
signed native terminator `0xFFFFFF0F` and returned without scaling. These now
share the corrected bounded classifier. Their width is 114px: text X=39,
numeric column X=177, less the 16px icon and 8px clearance. All 446 official
item names are tested; ingredient, success-result and failure-result call sites
are covered. Numeric fields, source strings and the accepted item-card path
are unchanged.

| Owner | File offset | Native role |
|---|---:|---|
| Details | `0x1520C` | Constructor at VA `0x11518C` |
| Recipe ingredient | `0x154D8` | Independent left-panel caption |
| Recipe success | `0x155CC` | Independent result caption |
| Recipe failure | `0x1563C` | Independent failure-result caption |
| Item action caption | `0x14C18` | Constructor at VA `0x114B98` |

The action caption budget is 66px inside native type 0x5E. IDs 1 and 3 bypass
this new fitter, preserving the accepted Can't and Compound bubbles exactly.
The source-grounded table and remaining translation limit are documented in
R67_15J_ACTIONS.md. Place, Take and the other proven labels retain full official
wording rather than abbreviations.

### HANT Help

The earlier layout used group-2 dimensions for icons actually in groups 0 and
38, and merged source rows independently of their icon ownership. This broke
the Item Screen category labels and left excessive gaps in Synthesis.

The new layout defines semantic units over original source rows and native
metadata indices. Each unit owns both the official paragraph and its icons.
Every animation frame is measured from its real table under `0x485240`, using
signed pivots. Text is wrapped around the combined frame envelope, including
multiple icons on one instruction. The actual 12px font descriptor is
`0x5D7800`, row pitch 16, text origin `(85,131)`, width at most 28 cells.

| Page | Text descriptor FO | Metadata descriptor FO | Rows |
|---|---:|---:|---:|
| Item Screen | `0x5CBAC8` | `0x5CBA78` | 57 |
| Item Synthesis | `0x5CBADC` | `0x5CBA8C` | 23 |
| Save & Load | `0x5CBAE8` | `0x5CBA98` | 16 |
| Wire Gun | `0x5C8A90` | `0x5C8A40` | 31 |
| Jumping | `0x5C8A8C` | `0x5C8A3C` | 41 |

Exact official rows are joined/reflowed without dropping words. Existing
PS2-specific directional-control wording is explicitly tagged, not presented
as an exact PS4 row. Official deletion markers and existing separator rules
are retained. No HANT renderer, allocator, row setter or pool instruction changes.
Tests sweep five-pixel scroll positions through the unchanged native extent,
execute the current viewport and actual X/Y setters, reach every row and stay
within the 19-handle pool. The native extent can scroll past the final Help
row; this pre-existing behavior is not changed or claimed as new pagination.

### Dungeon inspection

The object registry is reached through GP `0x79B1F0`, slot `GP-0x5480`
(`0x795D70`). Two pinned native arrays at `0x690500` and `0x694560` contain
400 and 200 six-pointer records. This is a complete native-table inventory,
not a heuristic scan. All 600 records' title, four description fields and
reading field are enumerated and checked against their actual font metrics.

| Role | M_ObjDtl call | Budget and placement |
|---|---:|---|
| Title reveal | `0x29B4A4` | 336px, centered at X=256, font 16x18 |
| Body reveal | `0x29BADC` | 336px, original X=88, font 16x18 |
| Action reveal | `0x29B2C8` | 164px, original left edge, font 16x18 |
| Reading update | `0x29B5E4` | 336px, centered at X=256, font 12x12 |

Group 2/type 0x93 has final frame width 360 and pivot X=180: left=76,
right=436. The body budget reserves 12px on each side. The action frame is
type 0x9D, width 232, pivot X=-52; its caption starts at owner X+112 and
reserves an 8px right inset. Short accepted text keeps its original spacing
and origin; scale is reset to 1 when a handle is reused for a short string.

The reveal callback `0x299F30..0x29A440` and constructor
`0x29A520..0x29A710` have other callers. They remain byte-identical. Private
copies retain their native state machine, allocation and teardown. Only each
copy's switch-table address, text-update call and callback registration change.
Only the three registered M_ObjDtl call sites select those copies. The fitter
updates that animation instance's origin and mean reveal advance for long
text; it does not patch shared font state or change native animation timing.
The reading uses its separate direct update hook.

The duplicated Isis readings at FO `0x58A1C4` and `0x592A84` map uniquely to
official deletion marker `@D`, corpus record 400151. Only those duplicate
reading pointers are redirected to the native empty sentinel `0x795B9C`.

## Verification and limits

- Final full suite: **725 tests run, 14 skipped, zero failures** in 201.820s.
  The initial new scroll test used the h-era harness and failed because it
  did not map i's appended viewport helper. It now uses the i harness with
  actual setters; the final full run includes all scroll and artifact locks.
- Independent deterministic replay reconstructs g, h and i from approved f,
  verifies the exact i executable, then composes all five j components twice.
- The whole finished disc audit compares **2,095,382,528 bytes** against f:
  **83,211 modified bytes, zero unexplained**. DATA.CVM, art and ADV resources
  are byte-identical to the approved f baseline.
- Finished resource lookup: **10,656 records**, 969 previously relocated or
  resized records, zero mismatches and zero unmatched records.
- Startup: raw **154/155**, scoped **155/155** using the documented
  `memory_card_8` exception. This is not a new waiver.
- q/t locks, accepted f names/art/bubbles, protected history **4/4**, and save
  descriptors **15/15** pass. Save namespace stays `BISLPM-66511Save`.
- `tests/test_r67_15j_release_lock.py` pins this executable and finished ISO.
  The diagnostic hash is a reproducibility lock, not visual approval.

Native tests execute the full original glyph-quad builder and the new fitters.
Inspection tests also execute copied callback dispatch through phase 2 into
phase 3. External text parsing/allocation services are intercepted; tests
provide realistic parsed nodes. EE SQ/LQ are lowered to SD/LD only in the
harness, so upper 128-bit register lanes are not independently emulated.
Selected EE accumulator operations are modeled explicitly. GPU drawing,
transient reveal glows/cursor appearance, timing across a complete gameplay
session, and cross-release save compatibility remain unverified. Native
instruction tests and static budgets must not be called cold-boot screenshots.

The independent review attempt did not complete because the review service was
unavailable. No independent-review approval is claimed. Publication references
are recorded below after the implementation commit is pushed.

Translation completeness remains separate from layout coverage: 36 existing
Details records retain original-language fallback, and dungeon action `入る`
at FO `0x594FBC` has no verified exact official corpus match. Their geometry is
covered; this release does not claim that every string in the game is English.

## Reproduction

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m unittest discover -s tests -q

uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m tools.r67_15j_iso_release
```

The builder refuses to overwrite any artifact, including an incomplete image.
Use `prepare()` for repeat executable verification after release; do not delete
prior releases to rerun the builder. The official corpus and pristine PS2
fixture must match their pinned hashes.

## Next screenshot checklist

Cold-boot the j ISO when the user chooses; do not alter their active session.

1. SELECT Details: shotgun, high-carbon blade, gas grenade, 9mm ammunition,
   Aqua Regia, and a long multi-line item. Capture the whole frame, with every
   rightmost glyph and final row visible.
2. Recipe panel: select Nitric Acid and Hydrochloric Acid; capture every
   ingredient/result name alongside unchanged numeric columns. Also show
   Mineral Water/Nitrate and any available failure result.
3. Swap/place an item: capture **Place**. Recheck **Compound** and **Can't**
   without movement of the accepted bubble left edge.
4. HANT Item Screen: category-icon rows, capacity rows, yellow/green legend.
   Synthesis: both item instructions, caution and guide. Scroll from top to
   bottom, then revisit Save & Load, Wire Gun and Jumping. Capture non-Help
   body text as a visibility regression check.
5. Isis: capture one title, complete description and **Take** action, both
   during reveal and settled. Recheck Gold Chains and another short inspection
   string; compare long and short objects consecutively.
6. In one run, visit and scroll at least five HANT pages, then cross the Aqua
   Regia doorway and continue toward the military attack. Confirm the next
   area loads; record any later untranslated or clipped owner separately.

## Return prompt

Continue Kowloon from docs/R67_15J_HANDOFF.md in the existing first-save-r67
worktree. Verify branch/main and the pinned r67.15j ISO before editing. Item
Details and recipes now use per-row glyph/space bounds; Help text and real
sprite envelopes share semantic units; inspection uses private native reveal
copies. Preserve i's doorway/HANT fixes, accepted d/f art and bubbles, all
saves and prior ISOs. User screenshots, not static checks, decide visual
acceptance. Track the 36 Details translation fallbacks and unresolved 入る
separately from the layout coverage. Use the owned official corpus and add a
new version for any subsequent correction.
