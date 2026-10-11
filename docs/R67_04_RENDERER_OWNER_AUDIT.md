# 67.04 — renderer-owner investigation (NOT a playable release)

Date: 2026-10-09. Starting point: verified clean `fix/67.03-runtime-layout` at `2a09697`; prerelease 67.03 remains the latest playable build, pending Pablo's runtime feedback.

## Proven from pristine and staged executable bytes

- Eleven distinct `jal 0x18BF10` font-canvas constructor callsites exist in the pristine PS2 executable. Their file offsets are now inventoried by `tools/r67_04_owner_audit.py`.
- `0x159D54` (virtual address `0x259CD4`) is **already redirected** to the experimental 72-byte MIPS helper at virtual address `0x962FFC` in the 67.02-history candidate, and that same hook is still present **unchanged** in the staged 67.03 ELF. Therefore the previous patch was not lost during the 67.03 build; repeating it would not produce a new fix. The previous runtime reports still describe vertical history text. Whether this constructor is used by the visible START modal remains unproven.
- Independent constructor callsite `0x151614` is still the native JAL; its upstream orientation word at `0x151608` is the previously approved horizontal `a2=0`. Do **not** patch this merely because it is another two-canvas renderer; its separate role has to be demonstrated.
- Compared with the 67.02-history ELF, the 67.03 executable has zero changed bytes in the tested ADV/DG speaker/body, history caller, other constructor, L1 visibility and AFK table-prefix regions. The changes for 67.03 are limited elsewhere and do not justify altering these approved surfaces.
- The Chamber of Lions old-man story comment (`0x3C1A50`, pointer alias `0x3D3428`) and later door-ready comment (`0x3C1F38`, alias `0x3D3B28`) have distinct string owners. Text identity/pointer ownership does **not** establish the blue background's sprite/resource owner.
- The first-fight transition has been reported to use the short companion AFK record 480 (`Come now, this way.`), which already has approved normal AFK geometry. Its **transition-specific** positioning remains unproven. Do not globally change AFK or L1 text offsets.

## Read-only audit and regression gate

Run from the current worktree:

```sh
python3 -m tools.r67_04_owner_audit \
  --pristine ../startup-flow-v10/fixtures/elf/SLPM_665.11 \
  --before-history local/r67-02-layout.elf \
  --with-history local/r67-02-history.elf \
  --release-6703 local/r67-03.elf \
  --report local/67.04-owner-audit.json
python3 -m unittest discover -s tests -p test_r67_04_owner_audit.py -v
```

The audit fingerprints preserved code spans, confirms the shipped shim, and explicitly returns `release_allowed: false`. It introduces **no executable, gameplay, ISO, graphics, or save-system modifications**. Tests fail closed if a pinned native caller or preserved region drifts.

## Required evidence before changing renderer code

1. For START history, determine which code actually executes while the vertical letters are drawn. The prior history hypothesis points to virtual address `0x259CD4`; the distinct font-canvas constructor is at file offset `0x151614` (VA `0x251594`). Collect execution evidence (manually using PCSX2's debugger when Pablo authorizes gameplay), then trace the actual glyph-direction flag and canvas coordinates. Do not copy the old 72-byte shim to another JAL without evidence.
2. For Chamber of Lions, identify the native sprite pool resource and rectangle geometry associated with the story-comment overlay, separate from the already accepted r66 AFK/L1 layers. Confirm both left text padding and blue rectangle containment from Pablo's gameplay screenshots.
3. For the battle-entry line, distinguish native AFK presentation from transition-specific caller transforms/timing. Preserve the correctly sized blue layer, and move only the proven text owner if necessary.
4. Check user screenshots from 67.03 for all previously changed inspection and H.A.N.T. pages. Static pass counts cannot approve runtime geometry.

**Status:** Work in progress. Do not publish 67.04, call the history or companion issues solved, launch PCSX2 automatically, or merge into main based on this audit alone. Produce a new numeric prerelease only after a concrete renderer correction with static regression checks; Pablo must still accept it visually.
