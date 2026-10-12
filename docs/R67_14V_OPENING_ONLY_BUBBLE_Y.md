# r67.14v — Opening-only upper speech-bubble layout (diagnostic)

## Newly supplied approved screenshot evidence

Pablo explicitly clarified the approved reference: the opening companion
message displayed TWO English rows fully centered/enclosed in one green bubble,
then **`Eerie place.`** displayed separately inside its own well-centered
bubble. The r67.14t screenshot showed only the top English line near the lower
border, with the second row falling below the green frame. The previously
accepted q bubble MUST NOT be flattened into a one-line design.

User approval also now locks:
- Lion Statue pickup label completely enclosed at scale **0.72**;
- post-Chamber Stone tablet fully enclosed and centered;
- original 58/58 native tablet records, 160/160 populated rows bounded to 21
  full-width glyph cells.

All such accepted owners have their own frozen manifest and 8 mutation tests:
`translations/r67_14t_approved_ui_lock.json`,
`tools/r67_14t_approved_ui_lock.py`,
`tests/test_r67_14t_approved_ui_lock.py`.

## Native cause — exact runtime bubble placement variant

The original `H_TalkBuddyTask` reads **`task+0x2F8`** as an active
**0-or-1 bubble layout selector**, at EE `0x166014/0x166030`. Both
unchanged sprite resources are assembled at EE `0x166070..0x166134` from
the fixed native sprite table:

| Native sprite | Selector 0 Y | Selector 1 Y |
|---|---:|---:|
| Green frame, IDs 0x68 and 0x69 | 172 | 230 |
| Blue backing, IDs 0x6A and 0x6B | 175 | 233 |

The two q English event-text wrapper calls at EE `0x963D78` and
`0x963E54` used **fixed** Y=280/300, regardless of bubble variant.
Thus the lower placement had approved text/frame insets 50/70, but the
upper placement potentially yielded insets 108/128 and clipped its second
row in the user screenshot. Both q and t indeed contained identical
preexisting event instructions; the difference was the runtime-selected
background position, not a data difference.

### Versioned implementation

r67.14u was a first generic diagnostic for all companion event strings, but
Pablo's newly supplied screenshot showed `Eerie place.` already correctly
enclosed. Applying a global variant correction to `Eerie place.` could
regress that approved screen. **r67.14u is superseded by r67.14v and should
not be offered as the recommended next playtest.** Both versioned ISOs are
retained intact.

**r67.14v applies the 58-unit upper-bubble adjustment ONLY when the original
native event text pointer is one of the two approved opening lines**:

- Opening first pointer `0x963F00`: selector 0 -> Y=222, selector 1 -> Y=280.
- Opening second pointer `0x963F8C`: selector 0 -> Y=242, selector 1 -> Y=300.
- `Eerie place.` pointer `0x9630BA`, all other event comments, and all
  AFK/free-talk (which use the separate original native code): untouched Y,
  unchanged text, unchanged two-line state, no green/blue sprite alterations.

The helpers read `task+0x2F8` and inspect the original `$t1` text source.
No changes to game story serialization, flags, inventory, background images,
event timer, history, H.A.N.T., glyph width, line count or item logic.

The **only two prior original ELF code words** intentionally changed from
r67.14t are at `0x963D78` and `0x963E54`. They now JAL into separate
**80-byte** append-only EE-MIPS helpers. Each helper preserves the matched
opening text's relative inset and 20-unit vertical row spacing.

- Tool `tools/r67_14v_opening_only_bubble_y.py`
- ELF `local/r67-14v-opening-dialogue-relative.elf`,
  SHA-256 `27a4084960018949be5ed91a13f2fdc79f61fb5e01de33e3d54646729d5822d3`.
- Finished ISO `local/r67-candidates/67.14v-opening-only-bubble-fit.iso`,
  SHA-256 `042c41a3d58209d537ad6fd6264e9e96c87dd902f0bcc6bf62f1a05d82e95205`.
- Installed ELF SHA-256
  `1ad069db3c26afe5b4bf17648526a391cc85a0b1037ef7c606ab53eda2154741`.
- ISO builder `tools/r67_14v_iso_patch.py`
- Finished 2GB whole-ISO auditor `tools/r67_14v_iso_byte_audit.py`
- Focused regression `tests/test_r67_14v_opening_only_bubble_y.py`.

## Immutable q lock — mandatory exception transparency

The original approved q manifest
`translations/r67_14q_approved_lock.json` was **never rewritten**.
The unmodified strict q-lock ***intentionally rejects*** r67.14v because
these two old hard-coded event Y instruction words are the actual defect
being corrected. The user's new explicit request authorizes precisely these
two words' diagnostic deviation. Do not claim the strict q lock passes
candidate v; it does not.

To preserve every other former approval, the separate validator
`tools/r67_14v_scoped_approval_lock.py` proves (against either SHA-pinned
previous staged or installed t reference) that ALL earlier data/code bytes,
except two specific JAL words and the ELF length, remain unchanged.
It disassembles/checks the exact new variant-aware helper bytes, and restores
the two old words **IN MEMORY ONLY** before requiring both ORIGINAL strict q
and t static locks to pass. The approved Lion item-name callsites, scale
helper and the three frozen tablet records/text hashes are unchanged.
No q manifest has been regenerated and no previous ISO has been overwritten.

The new 2GB ISO audit of t->v classifies EVERY modified byte:
- 4 bytes at the first private event Y-load JAL;
- 4 bytes at the second private event Y-load JAL;
- 86 nonzero bytes in 163 appended alignment/helper bytes;
- 1 changed ELF PT_LOAD byte;
- 4 ISO9660 executable length bytes;
- **zero unexpected ISO bytes**, **zero DATA.CVM changes**.

The original r67.14q approval remains the reference. Do not adopt v's newly
modified Y-logic into the permanent q approval until Pablo visually confirms
the two-line scene in-game.

## Validation

- Startup acceptance **155/155** on finished ISO v.
- Protected history **4/4 ELF and 4/4 ISO**.
- 8 opening-specific v tests, alongside 8 immutable r67.14t UI-lock tests
  and previously installed translation regression suite.
- Full suite: **416 tests, 18 expected skips, all passing**;
  `local/r67-14v-full-regression.log`.
- Whole-ISO audit: `local/r67-14v-whole-iso-audit.json`.
- Build manifest: `local/r67-14v-build.json`.
- Staged report: `local/r67-14v-opening-dialogue-report.json`.
- Finished ISO report: `local/r67-14v-iso-report.json`.
- Startup report: `local/r67-14v-startup.json`.

## Gameplay and promotion gates

Pablo should cold-boot **r67.14v** and show the opening **two-line bubble**,
then the separate `Eerie place.` bubble. Both must remain centered and
enclosed like the user-provided screenshots. Do not inject previous-CRC
savestates. The Lion Statue and Anubis Stone tablet remain locked; check
their already accepted visual layout as well when practical.

No in-game runtime proof exists yet for v, and ordinary PS2 memory-card
cross-release migration remains unverified. The approved q, diagnostics
r/s/t/u, and new v remain separate. No PCSX2 settings, original cards,
savestates or active sessions have been modified.

**Do not commit, push, create or merge a PR without Pablo's explicit final
visual release approval.**
