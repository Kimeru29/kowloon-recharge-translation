# r67.15k — live-metric description wrapping

## Handoff status

The corrected r67.15k diagnostic is built and its complete disc audit passes.
Gameplay evidence is still pending. An earlier unpublished k build used
unsupported processor comparisons; its ISO, ELF and reports are retained in
`local/r67-15k-rejected-generic-cop1/` for diagnosis, not distribution.

| Release evidence | Value |
|---|---|
| Corrected ISO SHA-256 | `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53` |
| Corrected ELF SHA-256 | `fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d` |
| Native/layout focused checks | 25 tests passed; release composition and artifact locks also pass. |
| Full suite | 755 tests run: 742 passed, 13 skipped, zero failures or errors (232.614 seconds). |
| Complete disc audit | 2,095,382,528 bytes compared with pinned f; 91,135 changed bytes, zero unexplained. This is the cumulative f-to-k delta, not the j-to-k delta. |
| Startup | Raw 154/155; scoped 155/155 with only the established `memory_card_8` exception. |
| Protected history / saves | 4/4 regions; 15/15 descriptors, namespace `BISLPM-66511Save`, serial `SLPM-66511`. Static preservation, not runtime compatibility proof. |
| Resources / accepted locks | 10,656 ROFS records; DATA.CVM, artwork and ADV unchanged; q/t and accepted f locks pass with their documented reconstruction scope. |
| Pull request / integration reference | **PENDING — do not infer from the current branch** |
| Cold-boot visual approval | **PENDING — no runtime approval claimed** |

The worktree is `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`,
on `fix/67.15k-description-word-wrap`. The only requested change in this
release is the two description-family layout paths; preserve all unrelated work.

Diagnostic: `local/r67-candidates/67.15k-description-word-wrap.iso`.
Executable/report: `local/r67-15k-description-word-wrap.elf` and
`local/r67-15k-description-word-wrap.json`.
Full audit: `local/r67-15k-whole-iso-audit.json`.
The j predecessor remains unchanged with ISO hash
`26ced321471b4415c2a855079c778502ed7c043d2e9467c8c1edc1833b58a079`
and ELF hash `6ebb80d3346f4f5ab68bc49197419658603b14686e4a8b549b451c1c8d7e76d8`.

## Scope and presentation contract

The change is generic live-metric word wrapping for Item SELECT Details and
dungeon inspection descriptions. It keeps the full source text and wraps
whole words using the active font's glyph dimensions, scale, tracking, spacing,
and line pitch. Inspection is treated as one grouped layout across its four
native text handles, so wrapped rows do not collide at their former fixed Y
positions.

Wrapping happens at the requested live metrics first. Only if the reflowed
paragraph exceeds the available vertical space may the presentation use the
largest uniform fit factor that accommodates all rows. That factor is a
rare vertical-overcapacity safeguard, not the normal layout strategy. It must
preserve every character and must not change the stored requested font scale,
clip text, or accumulate across repeated draws.

Official source text remains unchanged. Do not edit catalogue wording, remove
visible characters, or turn layout coverage into a claim of complete game
translation. Preserve untranslated fallbacks and all numeric columns, recipes,
titles, action labels, HANT behavior, doorway loading, saves, and previously
accepted UI. No PCSX2 settings, session, memory card, or save changes are
authorized by this handoff.

## Native owners and implementation

| Owner | Native entry / call | Layout ownership |
|---|---|---|
| Item Details | Constructor VA `0x11518C`, file offset `0x1520C`; official selector `0x975A78`; native constructor `0x189E40` | Final-draw callback is attached to the Details text object. Content bounds are 198 by 60 pixels. |
| Inspection body | Font construction call `0x29ACBC`; reveal construction call `0x29BADC`; body line pitch 18 pixels | One callback resolves all four handles at owner offsets `0x38`, `0x3C`, `0x40`, and `0x44`, then reflows the complete group independent of draw order. |

Installed kernel: `0x97B290`; Details draw callback: `0x97D850`; inspection draw
callback: `0x97DAD0`; copied font allocator: `0x97DDC0`; Details constructor:
`0x97E080`; inspection constructor: `0x97E0C0`. The wrappers tail-call native
draw `0x188420` with entry state restored. They save GPRs, FPRs, frame pointer
and FCR31 around the 64-byte-stack freestanding kernel.

Only three existing call words and the translation segment file-size field
change relative to j (10 existing bytes differ); 11,900 bytes are appended.
Inspection copies native allocator `0x188AD0..0x188D88`, increasing only its
private block from `0x254` to `0x258` and changing its draw callback. The extra
word at `private+0x254` belongs to the live inspection owner. The original
destructor `0x188A90` is retained. No shared renderer or global pointer cache
is modified. Body reveal construction returns to native `0x29A520`; accepted
j title, reading and action paths remain unchanged.

Inspection uses sprites `0x91`, `0x92`, and `0x93` as the panel backing. They
share anchor `(256,256)`, or Y `-32` for the high-positioned panel. The body
starts at anchor Y + 92; its 90-pixel content height allows five 18-pixel rows.
The backing's lower sprite height is not the full content-height limit.

The layout policy is implemented by `tools/r67_15k_word_wrap.py` and the
freestanding kernel `tools/native/r67_description_wrap.c`; native owner hooks
and allocation are in `tools/r67_15k_description_layout.py`. Existing source
text remains owned by the official corpus and native PS2 data. For translation
provenance, use the recovered PS4 English corpus at
`/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`
and the established matching rules; do not author or infer replacement
wording as part of k. The prior j handoff records the corpus SHA-256 as
`b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`.

## Processor-compatibility correction

The corrected compiler must preserve EE COP1 S-format comparison functions
`fn34` and `fn36`, and lower generic LLVM `fn35` to EE `fn34`, and generic
`fn37` to EE `fn36`. The first k image was produced with generic `fn3C`/`fn3E`
comparison encodings and is invalid for the EE. Keep it quarantined. Retain a
raw instruction audit and allowlist that verifies the corrected emitted kernel
against EE COP1 dispatch before accepting a build. The regression failed on
141 unsupported comparisons in the rejected payload and passes on the corrected
payload. Mutation tests reject 0x3C/0x3E, unsupported unordered predicates,
double-format operations, and unsupported word/branch forms. The release-lock
test audits the actual installed kernel as well as locking the complete ELF.

Build dependencies are pinned: Apple clang `21.0.0`
(`clang-2100.1.1.101`), `llvmlite 0.50.0`, and LLVM `22.1.0`. The backend
uses the MIPS II subset supported by the EE; the MIPS III/o32 selection failed
instruction selection. Only paired HI16/LO16 and local J26 relocations are
accepted. The kernel stack frame is 64 bytes. Preserve explicit finite-input
comparison semantics and instruction validation during the correction.

Other kernel safety limits remain: unknown controls, malformed pointers, or
more than 1024 nodes must reject before geometry writes. These checks do not
prove that every possible future control type can be wrapped. Full 128-bit EE
GPR behavior is not emulated in the native harness.

## Runtime evidence and limits

The j screenshots have not been reproduced conclusively. The user likely
booted from an in-game memory-card save; the exact j ISO used was not confirmed.
There has been no live PCSX2 test for k. Native execution and static layout
checks are not visual approval. The native inspection test now runs the actual
Isis record `0x592A70`, converter, node builder, glyph builder, opacity update
and final draw submission across all four handles. Forward, reversed and mixed
draw orders, repeated draws and 1.25x font metrics retain all submitted glyphs
inside `(88,348)..(424,438)` without overlapping paragraphs. Bypassing the new
callback reproduces over-wide submitted geometry. It is still not a complete
test of the reveal state machine, cursor animation, owner teardown, task
scheduler or real PCSX2 rendering.

All 431 Details catalogue records (including 36 untranslated fallbacks) and
600 inspection records are checked against the layout contract at multiple
sizes. Four actual item records also pass native conversion, opacity rebuild
and draw-submission tests. These are not 1,031 independently gameplay-tested
screens, and the game is not fully translated. The diagnostic is ready for a
user visual check; that remains separate from source integration and automated
verification.

The 13 suite skips are existing unavailable-fixture checks: five CVM/MTX/KSF
fixture modules, one historical graphics-port fixture, six old finished-ISO
checks (q, t, u, z, a, and r67.12 history), and one DG13 structural corpus case.
The corrected k installed-ISO lock, all k tests and current q/t/history/save
checks ran; these were not skipped. Full log: `local/r67-15k-final-suite.log`.

## Reproduction and fixture recovery

The build refuses to overwrite any existing artifact. Use the pinned toolchain
and the existing local prerequisites, then run:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  --with llvmlite==0.50.0 --with pyelftools \
  python -m unittest discover -s tests -v
```

The corresponding build entry is `python -m tools.r67_15k_iso_release` with
the same dependencies. `tests/test_r67_15k_release_lock.py` verifies exact
composition, final ISO identity, installed executable, processor encodings and
reported acceptance gates without rebuilding or overwriting the ISO.

Temporary owned PS4 assets and some historical ISO fixtures were absent during
verification. The owned package at `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
was verified as SHA-256
`054ceec8ef413f66c5c6057eadd8862dd7bf48eec1d3cfb183fdcdf97b700314` and
extracted with LibOrbisPkg revision `643477263b2644e0803e0f58b8726ea4e3f3b7d4`
plus the documented exact-read fix in an ignored recovery directory. The
English corpus matches the original hash above. Missing b/c/d/e/f ISOs were
reconstructed from retained pinned executables/art and accepted only when
their complete original SHA-256 hashes matched. Existing artifacts were never
overwritten. Original memory cards and savestates were not modified.

## Next screenshot checklist

After the corrected k ISO is built, audited, and identified by its final hash,
cold-boot that confirmed ISO from a memory-card save without changing the
user's emulator configuration, active session, card, or save contents. Capture:

1. Item SELECT Details for ammunition, grenade, shotgun, knife, and the longest
   available description. Include the whole panel and verify every rightmost
   glyph and final wrapped row remains visible.
2. Isis inspection with every description line visible; capture during reveal
   and settled, then close and reopen it to check stable grouped placement.
3. HANT body visibility and scrolling as a regression check.
4. The previously accepted doorway transition and continuation past the
   doorway. Confirm the next area loads and accepted UI remains unchanged.

Record the exact confirmed ISO identity, tested memory-card-save context,
screenshots, and observations before making any visual acceptance claim.

## Return prompt

Continue Kowloon in `.worktrees/first-save-r67`. Read `docs/R67_15K_HANDOFF.md`
and `docs/LOCALIZATION_STATUS.md`, then inspect Git status and the integration
reference. Test the hash-locked `67.15k-description-word-wrap.iso` against the
new screenshots. Keep generic live-metric wrapping for Details and grouped
inspection bodies; preserve official wording and accepted other screens.
Do not alter PCSX2 settings, sessions or saves, or claim visual approval without
fresh runtime evidence. The j screenshot discrepancy remains unproven.
