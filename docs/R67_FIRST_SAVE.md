# r67 release contract: English from New Game through the first Soul Well save

**Status: IN PROGRESS — NO r67 RELEASE OR GAMEPLAY APPROVAL.** Approved base is
`v11-r66`, SHA256 `1e818e50283ea1f8d9480293aecc5cd8dcc95b32fe128b430d7445ef1718d5e5`.
The unrelated post-save `MS04_00` candidate in draft PR #34 is **not**
included in this release. Do not merge or label this P0 candidate "r67".
All user-accepted AFK/L1 binary goldens stay frozen.

## Acceptance definition

The user plays from *New Game*, through original Heracleion Shrine prologue
(Salah, the H.A.N.T. tutorial, Chamber of Lions, first Umara fight, Door of
Anubis, Snake Staff) and reaches the first **Soul Well**. Every accessible
dialogue, location label, combat/puzzle/interaction prompt, command,
Save/Load screen, and optional pre-save content must be English and visually
correct. A complete static owner inventory precedes that playthrough; any
missed Japanese found by Pablo is corrected before completion.

**After** the English end-to-end walkthrough is accepted, Pablo creates the
first ordinary PS2 in-game save on a disposable PCSX2 memory card, cold-boots
to load it, and keeps a pristine, checksummed baseline. Future releases use
that actual card, *not a savestate*. Do not operate PCSX2 without explicit
approval. Preserve game serial `SLPM-66511` and save dir
`BISLPM-66511Save` throughout.

## Completed implementation: append-only P0 executable-localized text

`translations/first_save_pointer_owners.json` pins **29** independently
proven PS2 executable source records, **148** literal pointer aliases,
unique Japanese-key correspondences in the official English PS4
`English.bytes`, the original r66 executable SHA256, source SHA256 per
record, official original record offsets, and official English wording.

Families covered so far:

- Chamber of Lions, Door of Anubis and 13-alias Soul Well room names.
- Lion inscription (2 rows), Anubis alignment inscription (3 rows),
  Anubis crouch/west inscription (3 rows).
- Umara, Treasure Vase, Snake Staff, Heaven Door, Earth Door, Door to Yomi.
- Lion Statue examination name and description, Anubis statue name and
  multiple descriptions, Isis inscription name and descriptions, Snake Staff
  inspection messages and shared fixed-base/cannot-interact inspection
  messages.

`tools/first_save_r67.py` verifies that **every source, every literal
pointer alias, and every PS4 correspondence** still matches its approved
fingerprint, then appends 1,437 bytes into the existing translation PT_LOAD's
reserved 1 MiB range. The only original ELF bytes changed are the PT_LOAD
`p_filesz` and the explicitly approved 148 pointers. It does **not**
rebuild/move existing r66 translated content, AFK/L1 handlers, scenario
IDs/flags, item IDs, save/load code or original strings.

`tools/first_save_iso_delta.py` compares complete 2 GB old/new images
read-only, classifies *every changed byte*, and aborts on any unexplained
change. Last proven result:

- 444 pointer bytes (148 four-byte words, only three byte values change each);
- 1,380 non-identical bytes within the **1,437 appended** English bytes;
- 2 ELF `p_filesz` bytes;
- 4 outer ISO9660 file-size bytes;
- **0 unclassified changes** anywhere in the image.

The output is a **P0 partial candidate**:
`/private/tmp/kowloon-recharge-startup-en-v11-r67-first-save-p0-expanded.iso`
SHA256 `57897c2ff1c4d84161bbb988318a00df5a75e2f20bc55c5fe82b6db612f487fb`.
Finished-image acceptance: **155/155**. This is not a playable
English-complete release until the remaining work below is finished.
No PCSX2 launch occurred.

### Regeneration from owned/extracted sources

In `.worktrees/first-save-r67`, with r66's ignored outputs in sibling
`../startup-flow-v10`:

```sh
python3 -m tools.first_save_r67 \
  ../startup-flow-v10/artifacts/SLPM_665.11.en-early \
  --approved-manifest translations/first_save_pointer_owners.json \
  --official-english-bytes /private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes \
  --output local/first-save-r67-expanded.elf \
  --report local/first-save-r67-expanded-elf-report.json

python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r67-first-save-p0-expanded.iso \
  --overlay exact-mtx ../startup-flow-v10/local/exact-mtx \
  --overlay exact-ksf ../startup-flow-v10/local/exact-ksf \
  --overlay structural-mtx ../startup-flow-v10/local/structural-mtx \
  --overlay accepted ../startup-flow-v10/local/accepted-overrides \
  --overlay startup-graphics ../startup-flow-v10/local/startup-graphics \
  --elf local/first-save-r67-expanded.elf \
  --report local/first-save-r67-expanded-build.json

python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r67-first-save-p0-expanded.iso \
  --startup-graphics-root ../startup-flow-v10/local/startup-graphics \
  --report local/first-save-r67-expanded-acceptance.json

python3 -m tools.first_save_iso_delta \
  /private/tmp/kowloon-recharge-startup-en-v11-r66.iso \
  /private/tmp/kowloon-recharge-startup-en-v11-r67-first-save-p0-expanded.iso \
  --elf-report local/first-save-r67-expanded-elf-report.json \
  --report local/first-save-r67-expanded-iso-delta.json
```

The tool refuses to overwrite its ELF, JSON report, or existing acceptance
outputs. Use unique temporary output paths for repeats.

## Still required before first-player release candidate

1. **Optional H.A.N.T. Help bodies:** all 55 topic labels exist, but only
   four individually promoted bodies plus the distinct H.A.N.T. startup
   tutorial are translated. The complete 55-topic static inventory finds
   **50 unpromoted Help pages**, including 15 ADV topics that all share
   the same Japanese one-line placeholder (official PS4 English:
   `Saitama, Saitama!`). Those pages are *not empty*. The 55 pages have
   759 original nonblank rows, 737 with uniquely resolved official PS4
   English. A matching string is not proof of safe page rendering. Prioritize
   Jumping, Wire Gun Controls, Opening Doors, Operating Switches, Moving
   Objects, Basic Attack, Turn-Based Combat, and Save & Load.
   Existing source tables and icon metadata are independent; direct
   English-text-only replacement can clip or overlap icons.
   Implement each generic source/row/metadata class with exact source
   fingerprints, PS4 correspondence (where exact), row widths, and icon
   coordinates. Preserve previously accepted H.A.N.T. layout.
2. **Puzzles/interaction inventory:** verify **all** interactions reachable
   before the first Soul Well, including optional inscriptions, item tooltip
   descriptions and battle status. The existing 29 owners are a bounded
   first-pass set, not a whole-game source inventory.
3. **Graphics and combat overlays:** audit early-screen texture-baked Japanese
   and controls/abilities. Do not infer successful coverage from an English
   executable lexical scan alone.
4. **Layout proof:** Long official English inscription rows and room labels
   were source-proven and encoded, but have **not** been observed on the
   actual PS2 renderer. Do not claim no clipping or correct puzzle layout.
5. **Finish implementation + review gate:** build reproducible full r67
   candidate, rerun full tests/155 acceptance, strict binary-diff
   classification, then obtain Pablo's in-game report. Fix missed Japanese
   before marking the milestone accepted; only then create the first
   persistent save and preserve its own checksum.

Earlier full discovery: `docs/FIRST_SAVE_TRANSLATION_GATE.md`.

## r67 follow-up: all 50 remaining H.A.N.T. Help bodies translated (static, unreviewed)

`tools/first_save_help.py` is an append-only second executable pass over the
already-validated 29-owner P0 ELF. It uses the same owned PS4 `English.bytes`
to resolve **50 previously untranslated Help pages**, while preserving all five
previously accepted pages (including the separate startup tutorial).
The auditable file `translations/r67_help_owners.json` stores **no proprietary
English body corpus**, only page/row source SHA256 fingerprints, mode/topic IDs,
original descriptor offsets, and icon metadata SHA256 fingerprints.

For all 50 pages, the localized table retains its **original row count and
original EOF sentinel**. Output lines are at most **28 two-byte PS2 font
cells**. The generator uses the already approved 12px glyph/16px row-advance
transform and reserves five glyph cells for every visible controller icon
before writing English glyphs; icons retain their original page-row association
and their type/variant. The 14 unmatched controller-instruction occurrences
are translated semantically by explicit original-offset mappings; the
"Entering Battle" page requires four repetitions of two compact semantic
sentences to fit its controller-heavy layout. No source rows are dropped or
truncated by the packing algorithm. The original 15 ADV placeholder pages
carry the official English "Saitama, Saitama!" and keep their original
independent page descriptors.

**Current provisional Help-inclusive ISO**:
`/private/tmp/kowloon-r67-first-save-help-icons.iso`;
SHA256 **`45dfa8ee15dc509e7c27d3d714cc9e88d91d9d3f8c701ff0804c4df78cb262b1`**.
Two pristine builds are SHA-identical. **155/155** finished-ISO acceptance
checks pass. Full suites: **259 tests** each (15 expected skips without Pillow;
six expected skips with Pillow). New `tests/test_first_save_help.py`
replays all 50 pages from the owned PS2/PS4 sources and checks the original
row count/EOF, text width, icon-cell exclusions, controller metadata and
SHA256-golden complete ELF.

Compared with unchanged r66 across the entire ~2GB image:
**148** original name/inscription/description pointers and **99** Help
descriptor owners explain all changes, as do the appended English payload,
ELF translation segment-size metadata and ISO9660 file-size records.
`tools/first_save_iso_delta.py` returns **zero unclassified bytes**.

**This is not a runtime-proven English-complete release**. First-dungeon
optional graphics, item/interaction names and inspection prompts and
combat/menu overlays are still under audit; long room/puzzle strings and new
Help page layout have not yet been visually inspected in PCSX2. Do not label
the ISO approved or request a save until those static audits and Pablo's
subsequent playthrough have occurred.

### Rebuild the 50-page r67 Help pass

Start from the **unchanged original PS2 ELF** and the already-produced P0 ELF
(`local/first-save-r67-expanded.elf`). This second pass does not rebuild or
move any earlier AFK/L1 code:

```sh
python3 -m tools.first_save_help \
  ../startup-flow-v10/fixtures/elf/SLPM_665.11 \
  local/first-save-r67-expanded.elf \
  --official-english-bytes /private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes \
  --manifest translations/r67_help_owners.json \
  --output local/r67-help-icon-safe.elf \
  --report local/r67-help-icon-safe-report.json

python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-r67-first-save-help-icons.iso \
  --overlay exact-mtx ../startup-flow-v10/local/exact-mtx \
  --overlay exact-ksf ../startup-flow-v10/local/exact-ksf \
  --overlay structural-mtx ../startup-flow-v10/local/structural-mtx \
  --overlay accepted ../startup-flow-v10/local/accepted-overrides \
  --overlay startup-graphics ../startup-flow-v10/local/startup-graphics \
  --elf local/r67-help-icon-safe.elf \
  --report local/r67-help-icons-build.json

python3 -m tools.first_save_iso_delta \
  /private/tmp/kowloon-recharge-startup-en-v11-r66.iso \
  /private/tmp/kowloon-r67-first-save-help-icons.iso \
  --elf-report local/first-save-r67-expanded-elf-report.json \
  --help-report local/r67-help-icon-safe-report.json \
  --help-manifest translations/r67_help_owners.json \
  --report local/r67-help-icons-delta.json
```

Use fresh output destinations if the paths already exist; the build is
content-deterministic and SHA-fingerprinted. Never overwrite r66 or the
pristine corpora. Layout and icons are **statically verified**; graphical
acceptance still requires Pablo's own screenshots.

## Integrated static candidate for first-save player review (2026-10-09)

**Current state: static candidate built and checked; no PCSX2 launch or save; PR #36 remains a draft.** The older "Still required" section above describes the gaps found *before* the subsequent Help, inspection and graphics implementation.

**Coverage:** the previously frozen 29 executable source owners/148 aliases now coexist with 50 added English H.A.N.T. Help bodies/99 body+metadata descriptors and nine extra first-dungeon interaction owners/78 aliases. All **55 Help topics** have English text pointers (the four previously accepted bodies and the separate starter tutorial remain frozen). The English Help generator respects the original row count, EOF markers, 28-cell width, controller-icon metadata and existing 12px/16px renderer. Official PS4 text is matched through hashed Japanese source text; missing standalone controller keys and the repeated Entering Battle command use explicit semantic exceptions.

An offline JP/EN texture audit covered all 31 official localized remaster bundle pairs. The integrated overlay includes **85 official English TMX entries across 18 PS2 containers**: HUD, combat, menu, item/stat, optional H.A.N.T. panels, enemy/profile cards, first-save labels and secondary New Game/Load Game artwork. Entries are pinned by source and output hashes and the importer preserves every neighboring TMX chunk. The single previously translated native H.A.N.T. graphics resource, GP020_03, is preserved *from accepted r66* while GP020_02 is localized in the same container. No pristine source or accepted r66 asset was modified.

**The ISO on the Mac:** /private/tmp/kowloon-r67-first-save-complete-static.iso

**SHA-256:** e3cfa94fe2a23ba203387c7141072ccbf117db4f4bb60da49b1101d9a89f4a04

**ISO size:** 2,095,382,528 bytes. Two independently generated ISO builds have the same hash. All **155/155** startup acceptance checks pass with the r67-specific graphics acceptance reference, and the complete ISO delta audit classifies **every changed byte**: exactly 148 earlier text pointers, 99 Help descriptors, 78 additional interaction pointers, 85 owned graphics entries, appended English payload and ELF/ISO9660 size fields. **Zero unclassified modifications.** The save namespace BISLPM-66511Save is byte-identical to r66 at all 15 offsets; the serial SLPM-66511 is unchanged. AFK/L1 and old-man renderer accepted static golden checks remain active.

Static evidence is generated under local/r67-complete-static-build.json, local/r67-complete-static-acceptance-v2.json, local/r67-complete-static-delta.json, local/r67-help-icon-safe-report.json, local/r67-early-interactions-report.json, local/r67-english-graphics-85-report.json, and local/r67-graphics-pixel-audit.json. The audited source-owner manifests (not copyrighted byte arrays) are committed under translations/. The reproducible scripts are tools/first_save_r67.py, tools/first_save_help.py, tools/first_save_interactions.py, tools/first_save_graphics_port.py and tools/first_save_iso_delta.py.

### Rebuild the finished ISO

After regenerating P0, Help and interaction ELFs using the documented commands above, run the graphics importer on the owned original and accepted r66 sources:

    uv run --with UnityPy python -m tools.first_save_graphics_port \
      --pristine-iso '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
      --approved-r66-iso /private/tmp/kowloon-recharge-startup-en-v11-r66.iso \
      --ps4-bundles /private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/BLBRD \
      --manifest translations/r67_graphics_owners.json \
      --overlay-root local/r67-english-graphics-85 \
      --report local/r67-english-graphics-85-report.json

    python3 -m tools.build_translation_iso \
      '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
      /private/tmp/kowloon-r67-first-save-complete-static.iso \
      --overlay exact-mtx ../startup-flow-v10/local/exact-mtx \
      --overlay exact-ksf ../startup-flow-v10/local/exact-ksf \
      --overlay structural-mtx ../startup-flow-v10/local/structural-mtx \
      --overlay accepted ../startup-flow-v10/local/accepted-overrides \
      --overlay startup-graphics ../startup-flow-v10/local/startup-graphics \
      --overlay r67-graphics local/r67-english-graphics-85 \
      --elf local/r67-early-interactions.elf \
      --report local/r67-complete-static-build.json

For finished-image acceptance, create an ignored reference tree at local/r67-acceptance-graphics/BLBRD containing symlinks to accepted r66 B_GP019.BIN, B_GP088.BIN and INIT_MES, but point B_GP020.BIN to the new r67 overlay. This allows the original 155 checks to account for the *intentional* GP020_02 localization; a separate test enforces byte-for-byte r66 GP020_03 and all other unowned sprite data. The full ISO delta gate additionally enforces per-entry SHA256.

### What static analysis cannot prove

This is a candidate **for the user's first playthrough**, not runtime acceptance. No claim is made that in-game text is not clipped or that all game-state-dependent optional screens have been visited. Twelve localized PS4 bundle families remain outside this bounded graphics import because their first-save relevance or PS2 atlas ownership was not established; some contain later-game school, dorm, museum, guild or ending artwork. This is not evidence that their content is reachable before the first save.

**Player verification required:** New Game, Salah, full first dungeon, combat, all optional H.A.N.T. Help and item/inspection screens, Soul Well Save/Load. Report untranslated fragments and visual bugs. Fix those *before* the user makes the first permanent save and hashes the resulting memory card. Do not launch PCSX2 or create a save autonomously.
