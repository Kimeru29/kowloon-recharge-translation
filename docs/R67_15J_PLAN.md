# r67.15j: text bounds and Help layout

Base: `a7a029c9ce51b3691ff37fbfbf051d7a6f0bc1db` (r67.15i).
Worktree: `.worktrees/first-save-r67`; branch: `fix/67.15j-generic-text-bounds`.

## Scope and acceptance

Keep the confirmed doorway-loading and HANT visibility fixes. Fit every Item
Details record, every recipe name, and dungeon inspection text within the
owning panel. Preserve full official strings, numeric columns, accepted item
cards and Compound/Can't bubbles. Restore semantic association between Help
icons and text. Translate remaining action owners using verified corpus rows.

Do not alter emulator settings, running sessions, memory cards or savestates.
Do not overwrite any prior release. Static/native-instruction tests are not
gameplay approval. The user has authorized integration to main after validation.

## Implementation sequence

1. Execute the original native glyph builder in a bounded test harness. Pin
   the actual font descriptor, control-node behavior and quad coordinates.
2. Replace Details/recipe assumptions with per-handle bounded layout. Test all
   431 Details entries and catalogue recipe names, including the photographed
   failures and signed native end markers. Preserve unrelated renderers.
3. Rebuild Help text and icons from shared semantic blocks. Resolve dimensions
   through each sprite's real group/frame table and test attachment, compactness,
   clipping and scroll extent for all affected pages.
4. Apply corpus-backed action pointer changes and fit each actual caption owner.
   Keep unmatched `入る` explicitly unresolved until official evidence is found.
5. Finish tracing M_ObjDtl handles and refresh paths; derive green-panel bounds
   from native assets and add generic per-handle inspection layout tests.
6. Build a separate versioned diagnostic ISO, run the complete test suite,
   startup scoped 155/155, protected history 4/4, all save paths and q/t/latest
   locks, and audit every changed ISO byte. Document hashes and runtime limits.
7. Commit, push, create/attach a PR and integrate to main. Record the exact
   user screenshot checklist; do not describe static checks as visual approval.

## Evidence already collected

- Baseline: 679 tests passed, 14 skipped.
- Native Details frame is group 4/type 0x0B, 256x112; text starts at (26,16).
  The old 220-pixel budget allowed text into the right decorative border.
- Recipe wrappers still reject the native signed 0xFFFFFF0F end node, causing
  the original unscaled layout to survive. Details was corrected separately.
- Help layout used group 2 geometry for actual groups 0 and 38. Item Screen
  paragraph merging also discarded icon/label association; Synthesis allocated
  separate blank blocks for icons belonging to the same instruction.
- The action pointer patch and geometry component are separate, so official
  wording and screen-local fit have independent validation gates.

## Outstanding proof

Native rendering is a geometry oracle, not a GPU or gameplay emulator. Owner
mapping and static geometry are documented in R67_15J_HANDOFF.md. Cold-boot
screenshots and visual acceptance remain outstanding. Integration to main is
authorized separately and must not be described as gameplay approval.
