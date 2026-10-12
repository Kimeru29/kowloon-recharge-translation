# r67.14w — Opening-bubble native shared-geometry restoration (DIAGNOSTIC)

**Status:** build and static checks complete; gameplay screenshots required. This
diagnostic is NOT visually approved and cannot be merged yet.

## User's new evidence

Pablo's r67.14v screenshot shows both opening event-comment lines:
`Make sure you're always ready to` and
`switch into battle mode anytime.`, floating ABOVE their otherwise empty
green bubble. He confirmed `Eerie place.` and other dialogue in the Chamber
still appear properly centered and enclosed. We must not modify their
geometry, font, content, timers or two-bubble progression.

Previously approved r67.14t features still frozen:
- Lion Statue pickup name entirely inside card (horizontal scale 0.72).
- Stone tablet after Chamber enclosed and centered.
- All 58 registered tablet records / 160 live inscription rows ≤21 glyph cells.
- Previously approved q automatic/AFK text objects, event timer, H.A.N.T.
  history and two-row script structure, except precisely the opening bubble
  reconstruction owner described below.

## Investigated source of r67.14v regression

The earlier r67.14u/v hypothesis incorrectly interpreted a
**companion-slot X offset** as a bubble Y offset. The exact native EE placement
record is `(2, sprite 0x68/0x69, 249.0, X, Y)`, where:
- slot 0: **X=172, Y=346**
- slot 1: **X=230, Y=346**.

This is explicitly consistent with the project's older, documented and
runtime-accepted `COMPANION_SLOT_POSITIONS=((172,407),(230,407))`, native
resources `0x68/0x69`, and horizontal 58-unit companion-slot separation.

There was NO justified 58-unit *vertical* text adjustment. It explains
why r67.14v's upper text y=222/242 appears far ABOVE its bubble. It
must never be promoted as a generic dialogue Y fix. r67.14w starts from
**r67.14t** again, NOT r67.14v, and keeps the original approved event text
Y=**280/300** with its 20-unit two-row spacing.

The original green resource has native dimensions 288×80 with pivotY 77.
When constructed with native anchorY=346, its top is 269. The accepted
opening text Y=280/300 thus has green-top insets **11/31 native units**
independent of companion slot. These are the original, screenshot-proven
coordinates. No changed event-wrapper or font word is needed.

**Separate runtime-state risk established by native disassembly:** group-2
green sprites 0x68/0x69 and blue backing 0x6A are shared and intentionally
MUTATED by normal L1 actions (compact 224×48, pivot 45) and AFK/free-talk
(dynamic multiline geometry). AFK has its own restoration hooks, but the
original event H_TalkBuddyTask path reconstructs the sprites at
`0x166070–0x166134` without resetting mutated sprite metadata. This
is a concrete plausible path to a resized/incorrectly aligned normal
event bubble even while the English text Y remains correct. We cannot yet
claim its presence in the screenshot's runtime memory; gameplay confirmation
is the outstanding empirical step.

## Narrow correction

Replace exactly ONE native main-ELF instruction at EE **`0x16606C`**
(original `sw zero,0x5C(s0)`) with `jal` to a private, append-only
204-byte EE MIPS helper. The next untouched native
`lh v1,0x2F8(s0)` is deliberately preserved as the JAL delay slot, so
the original slot calculation at `0x166074` receives exactly the same v1.

The helper always performs the original
`sw zero,0x5C(s0)` before any new logic. It only accesses shared
sprite metadata if:
- current native H_TalkBuddyTask record id **2** (`s0+4`);
- current row/subindex **1** (`s0+0xA`) — the exact opening two-line record;
- native companion slot (`s0+0x2F8`) is valid, **0 or 1**.

The two frozen source pointers for this exact row are
`0x963F00/0x963F8C` at `0x3D3438/0x3D343C`; the prior accepted
`Eerie place.` is row **0**, pointer `0x9630BA` at `0x3D3428`.

For ONLY record 2/subrow 1, BEFORE native sprite creation, restore:
- selected green 0x68/0x69: width=288, height=80, pivotX=67/125,
  pivotY=77;
- all three animated blue 0x6A metadata frames: width=288,
  height=56, pivotX=67, pivotY=74/75/76.

All metadata restored to original approved PS2 values. The executable's
static resource tables are UNCHANGED; writes occur only in this target
runtime path, as the original game and existing AFK/L1 hooks already do.
No AFK, item, tablet, story, timer, original text Y or generic renderer
code is patched. Runtime actions/AFK retain their own previously
approved geometry-setting hooks.

The helper intentionally uses only v0/a0/a1/a2, which are overwritten by
the native constructor continuation; it preserves v1, s0, t0/t1, ra and
all floating-point registers.

## Code, artifacts and validation

- Implementation:
  `tools/r67_14w_restore_opening_bubble_shape.py`
- Native instruction-level regression + metadata mutation tests:
  `tests/test_r67_14w_opening_bubble_geometry.py`.
  A small self-contained MIPS interpreter EXECUTES the actual helper
  machine code with simulated event record, subrow, slot and original
  resource fields; verifies both green slots and all three blue frames;
  verifies Eerie row0, other rows/records, AFK and invalid slots do not
  modify any sprite shape. Tests also enforce the native JAL, delay-slot
  preservation, old text Y identity and prior Lion/tablet approvals.
- Immutable q/t scoped validator:
  `tools/r67_14w_scoped_approval_lock.py`. The original q manifest is
  UNCHANGED, and its strict direct check correctly rejects the one new
  original event-region word. The scoped validator verifies exact t/q
  SHA-pinned preimages, restricts the exception to ONE code word, then
  reconstructs that old word **in memory only**, and reruns all four
  original strict q regions AND all previously visually approved t UI
  locks. No q approval is silently rebased or discarded.
- ISO build tool: `tools/r67_14w_iso_patch.py`
- Whole 2,095,382,528-byte finished ISO audit:
  `tools/r67_14w_iso_byte_audit.py`
- Staged candidate ELF:
  `local/r67-14w-opening-bubble-restored.elf`
  SHA-256 `5aed2875a664766ce58915a942bb5cc0007bd1797ed0b9004b44a95e4127c128`.
- **Finished diagnostic ISO**:
  `local/r67-candidates/67.14w-opening-bubble-geometry.iso`
  SHA-256 **`1eb0da0cbc6306403c565ee7566fa151a3abfa05f0361fd6e1e6436ff32c9724`**.
- Installed ELF SHA-256:
  `9d7b24576eaec78e67b2e1f81417ba83429c7cefa9ae8e9e3dc1bdde98be6f84`.
- ELF report: `local/r67-14w-opening-bubble-report.json`
- ISO build report: `local/r67-14w-build.json`
- Whole-disc audit: `local/r67-14w-whole-iso-audit-final.json`
- Acceptance: `local/r67-14w-startup.json`
- Regression: `local/r67-14w-full-regression.log`

Confirmed by static tests:
- **426 tests successful**, 18 expected skips (full suite).
- Native MIPS geometry test: **10/10** including other-event nonmutation.
- **155/155 finished-ISO startup acceptance**.
- Protected history: **4/4** on ELF and ISO.
- q/t scoped owner locks: PASS (one declared original instruction exception).
- Whole finished ISO comparison against SHA-pinned approved r67.14t:
  zero unclassified modified bytes; only one new event-hook JAL, appended
  private helper bytes, ELF size and ISO9660 file-size metadata.
- Game identity remains `SLPM-66511`; ordinary save namespace remains
  `BISLPM-66511Save`. No save/load/serialization changed.

**Explicit limitation:** neither interpreter-based metadata tests nor
startup static acceptance are actual PCSX2 screenshots. r67.14w's
on-screen bubble placement must be checked in cold-boot gameplay and must
match BOTH user-approved opening lines and the separately correct
`Eerie place.`. Do not mark runtime fixed until that proof arrives.

## Release safety

All prior approved and diagnostic ISOs remain in
`local/r67-candidates/`; no original cards, PCSX2 settings, savestates
or active emulator sessions touched. Cross-release portable memory-card
runtime validation remains not established. Branch/worktree unchanged,
**no commit, push, PR or merge before Pablo's explicit visual approval**.
