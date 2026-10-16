# r67.15g — tutorial through the military attack

Status: verified partial diagnostic checkpoint; no new gameplay approval. See `R67_15G_HANDOFF.md` for current artifacts and remaining source gaps.

## Approved scope and constraints

User approved the bounded design in this conversation and explicitly requested continuous execution without further design approvals. Translate reachable content through the military attack, inclusive, plus ALL item-menu SELECT Details descriptions. Correct stone-tablet quotation/alignment and H.A.N.T. Item Synthesis, Save & Load, Wire Gun Controls and Jumping layouts. Use the owned official English corpus; reference screenshots guide layout, not controller mappings. Screenshot 5 duplicates Save & Load and is not evidence of Wire Gun's exact defect.

Reuse `.worktrees/first-save-r67`; base commit `0012131`, approved r67.15f ISO SHA-256 `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0`. Preserve original sources, previous releases, accepted UI, game logic, identifiers, saves and emulator state. No emulator input or launch is authorized. New runtime acceptance requires user screenshots. Do not merge.

Official corpus: `/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`, SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`. Load proprietary prose at build time; do not commit extracted corpora/assets.

## Work allocation and integration contract

| Task | Write ownership | Completion evidence |
| --- | --- | --- |
| All item Details | New `tools/r67_15g_item_details.py`, matching tests and component note | catalogue coverage, exact corpus provenance, native consumer/width proof, targeted tests |
| Four Help pages | New `tools/r67_15g_help_layout.py`, matching tests and component note | full glyph/icon rectangles, scrolling and content preservation, targeted tests |
| Tablet formatting | New `tools/r67_15g_tablet_layout.py`, matching tests and component note | marker glyph diagnosis, aligned bounded rows, narrowly scoped old-lock exceptions |
| Route and integration | Controller; release tooling, route evidence, final handoff | endpoint mapping, finished-image coverage, complete ISO audit and full suite |

Components expose `apply(source: bytes, ...) -> (bytes, report)` and named `PERMITTED_EXISTING_RANGES` for original ELF changes. They accept a sequentially extended ELF while independently pinning their owned source ranges against the approved 15f image; never accept unexpected drift in their own owners. Appended payload belongs to the component; ELF segment-length metadata is audited separately. Report exact original ranges, appended extent, mapping failures and unresolved runtime assumptions. Do not rewrite historical patchers, manifests or tests. Do not build final ISO or commit from worker tasks.

## Execution decisions

- Independent workers use disjoint new files in this shared worktree; controller integrates sequential ELF transformations. User-directed Luna implementation/targeted verification supersedes the skill's default independent review cycle.
- Existing screenshot approval locks remain immutable. Only the explicitly requested tablet presentation may require a new scoped comparison; preserve and explain every historical lock exception.
- Unknown official correspondence is a reported gap, never guessed English or silently counted as translated.
- Full item Details coverage is catalogue-wide; route scope otherwise ends at the military attack, not subsequent hospital/school scenes.

## Progress

- Baseline: clean worktree; branch `feat/67.15g-prologue-details-help` created from `0012131`.
- Baseline suite: 560 tests, 14 skips, zero failures/errors in 123.319s (Python 3.14, Pillow, NumPy, Unicorn, Capstone, OpenCV, UnityPy). Initial attempt omitted Capstone and had one import error; no test or fixture was changed to obtain the passing rerun.
- Component work: Luna workers assigned Details, four Help pages, tablets, and remaining prologue native text in disjoint new modules/tests/notes. Parent owns script/finished-disc coverage and integration.
- Integrated ISO, audit, publication and final handoff: pending.

## Diagnosis and evidence checkpoints

- Installed 15f script verification regenerated `DG00_00.MTX` (195 official map entries), `DG00_01.MTX` (34), and `MS00_02.MTX` (593) from pristine PS2 bytes plus exact owned PS4 sources/maps. All three equal the finished ISO payloads. `DG00_02.MTX` is unchanged 32-byte control-only data. The 593-entry file includes the military ambush AND later hospital scenes; its count is not an ambush dialogue-line count or route-completeness percentage.
- All ten official `MS00_02.KSF` choice fields match the exact importer. `DG00_00.KSF` retains its three exact translations and two historically approved fixed-slot compactions; no new scenario-byte edits are required for these files.
- Details screenshot witness: Japanese 9mm Luger paragraph starts at file `0x39A600`, pointed to by `0x39C4AC` for item ID 334. Getter EE `0x134B80` selects base VA `0x49BEF4` for IDs below 500 and alternate base VA `0x49CB00` for higher IDs; `0xFFFF` has a separate sentinel path. These are not item-name pointers. Its caller at EE `0x115148` passes the result to text constructor `0x189E40` at `0x11518C`, storing the result at instance `+0x190`. Paragraph origin is panel X+26, Y+16; background is group4/resource0xB. Worker resumed with these traced owners instead of guessing from the name renderer.
- Original screenshots copied without overwriting to ignored `local/r67-15g-evidence/01-…11-….png`. Images 4 and 5 are byte-identical (SHA-256 `03acf30662e93dbf0ffbaa5be44fa9cf23d07276ed86c4ba709444a97d4bc8ca`). No direct Wire Gun screenshot was supplied. Reference button legends are not PS2 mappings.
- Tablet targeted suite: six tests passed. Four Help pages: eleven targeted tests passed. Two initial prologue native labels: six tests passed; optional enemy-page and remaining route investigation continues. These component runs do not constitute final integrated or runtime acceptance.
- Official Details mapping now covers 391 nonempty complete descriptions and four empty records. Thirty-six alternate records retain 106 Japanese rows: the recovered PS4 asset search did not establish their official English correspondence. Five of those records have some exact official rows. This is a source constraint, not permission to author substitute English.
- The read-only finished-image route audit passed against the approved 15f ISO: exact script regeneration and no unresolved choice mappings. This does not establish closed-world route coverage or runtime captures.
- Publication policy: the default full-coverage build gate remains closed. A separately explicit partial-diagnostic path may package tested improvements while recording `scope_complete: false`; it must retain every safety, provenance, preservation and full-disc audit gate. No partial diagnostic may be described as the finished tutorial/all-item translation.
- GitHub PR #50 for 15f is already merged. Its remote branch remains at `0012131`; the requested stacked draft will still target that exact approved baseline branch. No merge of 15g is authorized.
- Fresh SHA-256 verification preserved 15d (`5d5850b660e92d9fd0dcb11456519d99b060cbaae131ebf48f6d0f80262a446d`), 15e (`442bc5bde6e8382aeacb8a03fbac34b04e3150bf96e8d209507006cd5d8f0014`) and 15f (baseline above). No previous release was overwritten.
- First integrated suite: 610 tests, 14 expected skips, no failures/errors, 303.366 seconds. Additional source-search, partial-publication and optional Enemy-page work followed; this run is not the final verification of those later changes.
- In-memory composition passed approved-15f native hooks, all 500 item-name pointer slots, 446 named entries, four protected art chunks, q/t checks, history 4/4 and static save identity 15/15. Final artifact checks must still run on the finished candidate.
- Anubis Enemy page completed as a data-only change after tracing the mode-2 consumer at EE `0x290304`, row staging at `0x290608`, and its 64-byte copy at `0x290698`. Official fields 10–17 pack into the same eight rows at 28 cells, preserving dynamic indices 5/7/18. Seven focused prologue tests pass. Runtime fit and optional reachability are not claimed.
- All component edits frozen for final full-suite and explicit partial-diagnostic build. Default full-coverage build remains blocked by the 36 unresolved official Details mappings.
- First real partial-build preflight found a release-tool interface error: `index_iso` received a `Path` instead of a mapped byte buffer. It failed before cloning or writing any artifact. A narrow fix and regression test were assigned; final suite/build results must come after that correction, not the earlier in-memory composition.
- Corrected preflight passed 18 focused release tests. Partial diagnostic built successfully: ISO SHA-256 `cb2ef57789d62fc078678285da86e272eaf426740f181d576126be4d1946f267`; complete 2,095,382,528-byte audit found 66,034 changes and zero unexplained. Scoped startup 155/155 (raw 154/155, sole documented exception), history 4/4 and saves 15/15 passed.
- Final verification on 2026-10-16: 621 tests, 14 expected skips, no failures/errors in 125.470s. After interrupted terminal sessions were unavailable, no pending test result was assumed: this fresh run completed. Recomposition reproduced the saved ELF and a fresh read-only whole-disc audit again passed. Prior source/code/lock files remain untouched; all repository changes are additive.
- Published implementation commit `3741dfc` on `feat/67.15g-prologue-details-help`; created [draft PR #51](https://github.com/Kimeru29/kowloon-recharge-translation/pull/51) against the approved 15f baseline branch. No merge, emulator operation, original-save mutation or runtime approval occurred. Final publication metadata is documentation-only.
