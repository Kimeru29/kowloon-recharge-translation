# r67.14u — Variant-relative companion dialogue geometry (diagnostic)

## User-reported defect and approved reference

Pablo provided two screenshots of the **previous visually correct dialogue**:

- The opening automatic companion comment displays **two lines, enclosed and vertically centered** within the unchanged green/blue speech bubble:
  1. `Make sure you're always ready to`
  2. `switch into battle mode anytime.`
- A later **separate** bubble displays `Eerie place.`, properly enclosed/centered.

In r67.14t, the first line appeared too low in the upper-position bubble;
the second line overlapped its bottom green border. Previous tools had
correctly asserted that event text strings, renderer, and green/blue art were
byte-identical to q, but that did NOT prove a runtime alignment invariant.

**User-approved, frozen features:** The Lion Statue pickup is fully enclosed,
the Stone Pillar/PUSH label remains, and the post-Chamber stone-tablet text
is fully enclosed and centered. Do not regress those visually accepted UIs.

## Root cause traced to original native owner

Native EE `H_TalkBuddyTask` selects a speech-background placement variant
with **`lh ...,0x2F8(s0)`** at VA `0x166014/0x166030`. The value is
0 or 1. The original sprite owners at `0x166070–0x166134`
index their immutable geometry table at EE `0x4F8D9C` and companion
backing at `0x4F8DC4` by 20 bytes per variant:

- Frame variant 0: `(kind=2, sprite=0x68, x=249, y=172, width=346)`.
- Frame variant 1: `(kind=2, sprite=0x69, x=249, y=230, width=346)`.
- Background variant 0: `(kind=2, sprite=0x6A, x=246, y=175, width=346)`.
- Background variant 1: `(kind=2, sprite=0x6B, x=246, y=233, width=346)`.

The separate r67.14q event-text wrappers `0x963D20` and `0x963DFC`
had **fixed absolute text Y values of 280/300**. These retain the approved
relative insets **50/70** when the frame uses Y=230, but produce
**108/128** for the frame using Y=172. This is why the top-placement
variant can show its text low or outside its frame even though the q-lock
source instructions remain exactly the same.

### Smallest scoped dynamic correction

On the exact SHA-verified r67.14t staged ELF, change only the two Y-load
instructions at **`0x963D78` and `0x963E54`** from `lui t0,<constant>`
to a JAL into two dedicated, private, 40-byte MIPS helpers appended inside
the existing PT_LOAD reservation.

Each helper reads the **native task's actual `s0+0x2F8` selection**.
It leaves the approved lower-bubble Y=280/300 intact and uses Y=222/242
for the upper bubble. **Both variants now have the identical 50/70 inset
from their frame Y**; both line spacings stay exactly 20. No global
glyph renderer, AFK/free-talk, timer, font-width, animation, sprite origin,
script header/translation, story flags, save routines, line indices, or
textual source pointers are modified. The original MIPS `mtc1 t0,f13`
instructions remain as call delay slots; the helper explicitly overwrites
f13 with the corrected Y before returning to the rest of the existing
wrapper. The previously accepted original lower variant is exact.

- Exact-source script:
  `tools/r67_14u_companion_bubble_relative_y.py`
- Two exact native MIPS helper VAs:
  `0x96412C` and `0x964154`.
- Staged ELF: `local/r67-14u-bubble-relative-dialogue.elf`,
  SHA-256 `0260c0f60d5256068b78fb496237750af7089cf4ca1710cae6d3204ab49b21ab`.
- Finished ISO: `local/r67-candidates/67.14u-bubble-relative-dialogue.iso`,
  SHA-256 `49550ffd6728968d9a93b5df02e5ab39d2587c7b2f4843091acfa816c118c00e`.
- Installed ELF SHA-256:
  `0e4d808379b56ad1251d7e7f5c3e1586053023a97c942079632a43d648595d45`.
- ISO generator `tools/r67_14u_iso_patch.py`.
- Whole-disc auditor `tools/r67_14u_iso_byte_audit.py`.
- Focused geometry tests `tests/test_r67_14u_bubble_relative_y.py`.
- Dedicated approved Lion/Anubis UI lock and mutation tests unchanged:
  `tools/r67_14t_approved_ui_lock.py`,
  `tests/test_r67_14t_approved_ui_lock.py`,
  `translations/r67_14t_approved_ui_lock.json`.

## Mandatory transparency about old r67.14q approval lock

The original immutable r67.14q manifest
`translations/r67_14q_approved_lock.json` has **not** been edited or
regenerated. The strict unmodified `r67_14q_approved_lock` *intentionally*
rejects r67.14u because the requested bubble fix must replace the two
old hard-coded Y loads in the private approved companion helper.

**DO NOT claim that r67.14u passes the unchanged q lock**.

Instead the additional scoped-preservation validator
`tools/r67_14u_scoped_approval_lock.py` enforces that ONLY those TWO
pre-declared callsites changed within the original native executable.
All other bytes of r67.14t, including every accepted Lion & tablet owner,
AFK, dialogue pointers, and the rest of the q protected regions, are exact.
The validator restores those two old instruction words IN MEMORY ONLY and
runs both original independent q and t immutable locks against that
reconstructed image. It SHA-verifies BOTH original staged/installed t
references and rejects any unknown changes or helper mutations. This
provides an explicit, auditable one-feature exception without changing a
single earlier approval baseline or merely exempting an entire region.

**Do not adopt this new q-lock exception as a visually approved reference
until user screenshots confirm r67.14u works.**

## Static release validation

- Approved r67.14t source is SHA pinned.
- 155/155 startup acceptance on finished r67.14u ISO.
- 4/4 protected history regions on staged ELF and finished ISO.
- Native Lion + 58 Stone tablet class preserved through strict t manifest
  and exact helper/content hashes, using the one-word-in-memory exception.
- Whole 2,095,382,528-byte finished r67.14t→u ISO audit has **ZERO
  unclassified bytes**. It observes only:
  - 4+4 modified bytes at the exact private event Y-load callsites.
  - 44 nonzero bytes in the 83-byte aligned appended helper region.
  - 1 ELF PT_LOAD file-size byte.
  - 2 ISO9660 bidirectional ELF-file-size bytes.
  - Nothing in DATA.CVM, prior translation strings, earlier native owner
    code, original memory-card data or savestates.
- Focused and complete regression logs:
  `local/r67-14u-full-regression-final.log`.
- Build, scoped protection, startup and byte audit reports:
  `local/r67-14u-bubble-relative-dialogue.json`,
  `local/r67-14u-build.json`,
  `local/r67-14u-iso-build-report.json`,
  `local/r67-14u-startup.json`,
  `local/r67-14u-whole-iso-audit.json`.

## Outstanding **in-game** approval

Cold-boot r67.14u (not a previous-version savestate). Capture the
**upper-position two-line opening bubble** and the separate **Eerie place.**
bubble. Compare alignment/enclosure against Pablo's two provided reference
screenshots. Verify the lower variant when it appears, the already accepted
Lion Statue pickup & PUSH label, and the Stone tablet after the Chamber.
Runtime cross-release save checkpoint migration remains unverified.

Keep original ISO q/r/s/t and this separate u candidate. No commit, push,
PR or merge until Pablo approves gameplay. Do not modify PCSX2 settings,
active sessions, original cards or savestates.
