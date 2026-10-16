# r67.15g — continuation handoff

Status: partial diagnostic built, full-disc audit passed and final regression suite passed on 2026-10-16. The requested scope is **not complete**. This document must not be read as gameplay approval or permission to merge.

## Scope and baseline

Continue translation through the first dungeon's military ambush, inclusive. Catalogue-wide SELECT Details translation is an explicit additional requirement. Correct the western Stone Tablet's ornament/alignment and four H.A.N.T. Help layouts: Item Synthesis, Save & Load, Wire Gun Controls and Jumping. Do not introduce new hospital/school translation work; retain any previously installed English there.

Worktree: `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.

Branch: `feat/67.15g-prologue-details-help`, based on approved `00121314506b4abdf00fb71bdca8276a72536194` on `fix/67.15f-item-panel-layout`. PR #50 for that baseline has already merged; the baseline branch remains available for the requested stacked draft. No merge of this branch is authorized.

Publication: [draft PR #51](https://github.com/Kimeru29/kowloon-recharge-translation/pull/51), targeting `fix/67.15f-item-panel-layout`. Implementation and tested source checkpoint: `3741dfc` (`Add audited r67.15g partial translation diagnostic`). This publication note is a subsequent documentation-only change. The branch was pushed; the worktree and all prior releases are retained. Do not merge on the strength of static audits.

| Immutable input | SHA-256 |
| --- | --- |
| `local/r67-candidates/67.15f-item-panel-layout.iso` | `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0` |
| `local/r67-15f-item-panel-layout.elf` | `418864fdb8700f100218a1dcb06aa90d71ce45b8ca5b98aaa9a8d46171378da1` |
| Official `English.bytes` | `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b` |

## Implemented components and native owners

Detailed native evidence, source fingerprints, algorithms, permitted byte ranges and regression tests live in the linked component notes. Read these before editing their owners.

| Component | Implementation / evidence | Boundary |
| --- | --- | --- |
| Stone Tablet | `tools/r67_15g_tablet_layout.py`; [tablet note](R67_15G_TABLET_LAYOUT.md) | Only western inscription row pointers `0x590FB8..0x590FC4`. Preserve historical accepted compact wording; remove ornament glyphs and balance rows. |
| Four Help pages | `tools/r67_15g_help_layout.py`; [Help note](R67_15G_HELP_LAYOUT.md) | Separate page text/icon descriptors; retain PS2 controls, complete official word sequences and native scrolling. Model full sprite rectangles, not one-cell placeholders. |
| Native prologue text | `tools/r67_15g_prologue.py`; [prologue note](R67_15G_PROLOGUE.md) | Altar room pointer `0x5CD794`, Anubis battle-name pointer `0x594E78`; Anubis Enemy record at `0x5C2410` has 17 official fields, with eight-slot bounded reflow and dynamic fields preserved. |
| Item SELECT Details | `tools/r67_15g_item_details.py`; [Details note](R67_15G_ITEM_DETAILS.md) | Getter EE `0x134B80`; paragraph constructor call EE `0x11518C`; instance-local metrics, no item-name/stat/global font change. |
| Installed scenario evidence | `tools/r67_15g_route_audit.py`; [route note](R67_15G_ROUTE_EVIDENCE.md) | Rebuild exact MTX and KSF imports independently from pristine PS2 plus official PS4 originals/maps and approved fixed-slot exceptions. |
| ISO assembly / ownership | `tools/r67_15g_iso_release.py`; [release contract](R67_15G_RELEASE.md) | Ordered composition, deterministic replay, exact source locks, full-disc changed-byte proof and static save/history checks. |

## Source constraint — do not hide or bypass

The native catalogue contains 431 valid Details records. Official mappings provide 391 nonempty complete descriptions plus four empty/no-prose records. Alternate IDs **500–535** remain unresolved: five have some exact official rows, while 31 have none. All 106 unmatched Japanese rows remain Japanese. The five mixed records are 500, 501, 504, 515 and 534.

Searching 6,975 recovered PS4 asset files did not establish official English for the remaining rows. Do not assume a fuzzy Japanese substring proves a translation, translate from Chinese, invent English, or silently drop these records from the denominator. A complete translation requires an authoritative English correspondence for those rows or a new explicit instruction allowing another source. The user's instruction to proceed without further routine approval does not authorize guessed wording.

The default build requires complete Details coverage. Any explicitly requested partial diagnostic must remain visibly incomplete in its manifest and handoff. It must pass all the same binary safety and preservation checks; the partial designation is not an audit exception.

The Anubis Enemy page no longer has an implementation hold: its renderer stages text into 64-byte row buffers, so merely shrinking the font would not prevent truncation. The exact official word stream for source indices 10–17 wraps into eight rows at 28 cells, retaining the final Treasure heading before the dynamic treasure field. This preserves dynamic indices 5, 7 and 18, all blank/EOF sentinels, and all renderer code. The 336-pixel span is a conservative existing H.A.N.T. bound, not a new runtime measurement of this page; screenshot fit and route reachability remain unverified.

The Weak Spot branch at EE `0x29044C` calls `0x2AAC80`; its known-weakness path resolves the selected Enemy record and reads field `+0x1C` at `0x2AAD78`. Thus the translated record field at index 7 also feeds the dynamic branch, rather than requiring a separate guessed literal replacement. Discovery-state behavior remains native.

## Sources and reproducibility

- Native official corpus: `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`.
- Complete recovered ADV data/maps: `/tmp/kowloon-15f-extractor.JtU7E1/pkg-extract-fixed-read/uroot/Media/StreamingAssets/data/ADV`.
- Original PS2 ISO: `/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`.
- Original executable: `../startup-flow-v10/fixtures/elf/SLPM_665.11`.
- Owned source package: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`; preserve it unchanged.
- Supplied screenshots: copied without overwriting into ignored `local/r67-15g-evidence/`, files 01–11. Images 4 and 5 are identical Save & Load evidence; there is no direct Wire Gun defect capture. Reference controller icons are not authoritative PS2 button mappings.

Temporary extraction directories may disappear. Verify actual source files and their hashes; do not infer source availability from a directory's existence. Do not commit proprietary assets, corpora, ISOs or saves.

Full regression command:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m unittest discover -s tests -q
```

## Acceptance limits and next screenshots

### Built partial diagnostic

| Artifact / gate | Result |
| --- | --- |
| ISO | `local/r67-candidates/67.15g-partial-diagnostic.iso` |
| ISO SHA-256 | `cb2ef57789d62fc078678285da86e272eaf426740f181d576126be4d1946f267` |
| ELF | `local/r67-15g-partial-diagnostic.elf`, 8,871,244 bytes |
| ELF SHA-256 | `74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee` |
| Manifest | `local/r67-15g-partial-diagnostic.json`; `PARTIAL_DIAGNOSTIC_NOT_GAMEPLAY_APPROVED`, `scope_complete=false` |
| Entire disc audit | 2,095,382,528 bytes compared; 66,034 changed; **zero unexplained** |
| Art / scenario data | Entire `DATA.CVM` byte-identical to approved 15f |
| Startup | Raw 154/155; scoped 155/155 with the sole preserved `memory_card_8` legacy-wording exception |
| Protected history | 4/4 regions |
| Static saves | 15 descriptors unchanged; serial `SLPM-66511`, namespace `BISLPM-66511Save` |
| Approved 15f owners | Two hooks, 500 name-pointer slots, 446 named entries and four protected art chunks unchanged |
| q/t locks | Pass with exact in-memory historical Lion-callsite restoration and the three explicitly authorized tablet-pointer exceptions; old manifests unchanged |
| Finished-image route audit | Exact script/choice provenance passed; no unresolved checked choice mappings |
| Final full suite | 621 tests, 14 expected skips, zero failures/errors, 125.470 seconds |

Local report family: `local/r67-15g-partial-diagnostic-{whole-iso-audit,startup-raw,startup,history,save-static}.json`. The full release manifest contains component provenance, per-owner deltas, append extents, native addresses and the exact unresolved Details rows. No proprietary generated report or image is committed.

Reproduction is explicit: call `tools.r67_15g_iso_release.build(route_evidence=tools.r67_15g_route_audit.audit(SOURCE_ISO), allow_partial_diagnostic=True)`. Existing output paths are protected against overwrite. Do not rerun this command over existing artifacts or remove them merely to obtain a fresh run; use the read-only audit functions. The default full-coverage build remains rejected.

The first build attempt failed before any output because the ISO indexer received a path rather than a mapped buffer. The corrected preflight retains a live read-only mapping for indexing and growth validation; its regression exercises the real approved source ISO. The successful artifact above was built after that correction.

On resumption, the earlier terminal sessions were unavailable. Their pending test runs were not assumed successful: the full suite was rerun to completion. Fresh source composition exactly reproduced the saved ELF, both artifact hashes matched, and the read-only complete-disc audit again passed with 66,034 explained changes. This verification-before-completion workflow keeps the tested checkpoint separate from gameplay approval.

No emulator was launched or controlled for this work. Settings, cards and savestates must remain untouched. Static native geometry, binary emulation and matching official text do not establish visual acceptance. Use the exact checklist in [automation evidence](R67_15G_AUTOMATION_EVIDENCE.md#screenshot-acceptance-checklist-for-this-milestone): western tablet; SELECT Details including 9mm Luger and long descriptions; all scroll positions on all four Help pages; storeroom/Gold Chains/Altar/boss/exit/military attack; optional Enemy pages; accepted Compound/Can't/name/stat screens unchanged. A later save/reload test requires separately authorized disposable-card handling.

The route script audit verifies specific files, not every reachable state or optional screen. `MS00_02.MTX` contains later hospital material as well as the attack: its 593 map entries are not an attack-only coverage count. PS2 `MS00_01.MTX` is control-only and structurally different from PS4; preserve PS2 control flow.

## Return prompt

> Continue Kowloon in the existing first-save-r67 worktree on feat/67.15g-prologue-details-help. Read docs/R67_15G_HANDOFF.md, the release report and component notes first; verify live branch/status/artifact hashes. Preserve accepted 15f/q/t/history/save owners and the explicitly scoped tablet exception. Do not call 15g complete: IDs500–535 lack complete official English Details source, and runtime/optional-route evidence remains separate. Use the supplied official PS4 corpus only; never invent missing wording. Keep partial diagnostic and gameplay approval distinct. Reuse completed work, do not restart, touch PCSX2, overwrite releases/saves or merge without explicit gameplay approval.
