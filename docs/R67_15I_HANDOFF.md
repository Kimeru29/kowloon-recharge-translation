# r67.15i — HANT body text and complete-catalogue Details layout

## Scope and current acceptance

The user reports that 15h fixed the Aqua Regia doorway transition, but SELECT
Details still overflow and all HANT bodies are missing. This release corrects
those two regressions while retaining the 19-slot pool safety change. It does
not replace official wording, alter other item-screen owners or bypass loading.

The latest request explicitly authorizes integration into **main**. That
supersedes the no-merge instructions in the historical 15g/15h handoffs; those
documents remain unchanged as records of their original acceptance boundaries.
Main integration is not new visual/gameplay approval. No emulator session,
configuration, card, save or savestate was changed for this work.

Worktree: `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.
Branch: `fix/67.15i-hant-text-item-details`.
Base: `c4918364a9d0ee016c3c8a0c1f08dbdf71cfa9c2` (15h).
The integration PR targets main and includes the pending 15g and 15h commits,
not just the final correction. Publication:
[PR #53](https://github.com/Kimeru29/kowloon-recharge-translation/pull/53),
target **main**. Implementation/build checkpoint: `3766343`. This publication
note is a subsequent documentation-only commit. The user authorized merging;
consult the PR and remote main for its live integration state. The worktree and
all release artifacts are retained after integration.

## Root causes and narrow corrections

### HANT viewport, shared by all body pages

The viewport owner is native `0x28FD60`. The 15h count guard replaced the row
and slot initialization at `0x28FDD4`/`0x28FDD8`, and the branch to the loop
precondition at `0x28FDDC`. Actual caller values in `s4`/`s5` therefore reached
the loop. The old harness initialized these registers to zero and missed the
regression. Nonzero incoming values now reproduce the missing-body behavior.

There was also a real setter ABI regression: moving the X setter call from
`0x28FEA0` to `0x28FEA4` put the handle reload at `0x28FEA8` into its delay slot.
Native setter `0x18AAB0` changes `a0` from a handle to its private object at
`0x18AAB8`. The subsequent Y setter then received that private object instead
of a handle. The previous setter stub did not model this side effect.

`tools/r67_15i_hant_text.py` installs two appended trampolines:

- Entry: reset `s5` in the hook delay slot and `s4` in the trampoline, validate
  unsigned row count below 81, and rejoin the original precondition `0x28FED0`.
  Zero rows skip safely; malformed counts return through `0x28FEE0`.
- Slot selection: perform the displaced pool-pointer calculation; null slots
  skip to `0x28FEC8`, valid slots rejoin `0x28FE9C`. Restore the X setter call at
  `0x28FEA0` and its NOP delay slot. The original reload at `0x28FEA8` again runs
  after X and before Y.

Only six preimage-checked native words change. The relocated handle pool at
private `+0x1A94`, capacity **19**, allocation **0x1AE0**, reset/fade coverage,
scroll predicates and icon placement stay intact. This is shared viewport
repair, not a Help-only string patch.

### SELECT Details, every valid catalogue record

The native converter emits end marker `FF0F` at `0x195464`/`0x195468`. Node
construction at `0x192684..0x19268C` stores controls as signed full words, e.g.
`0xFFFFFF0F`. Ordinary node words are glyph-resource pointers, not character
codes. Nodes occupy `0x130` bytes and their next pointer is at `+0x120`.

The previous helper rejected the native terminator, returning before space
normalization and line spacing. It also classified glyph pointers by their low
16 bits: a valid pointer ending in `FF00` could look like an unsupported control.
Synthetic nodes without the native terminator had concealed these failures.

`tools/r67_15i_item_details.py` redirects only the Details constructor hook
(`0x11518C`, file offset `0x1520C`) to an appended corrected copy of the helper.
Its classifier uses the complete word, recognizes the signed terminator, and
does not count it as a glyph. Unsupported controls still fail closed. The
existing instance-only space normalization converts `FFFFFF0B` to `FFFFFF0A`;
scale stays **0.5**, glyph/normalized-space advance **8px**, added line spacing
**-9**, native line pitch **9px**. Shared renderers, source strings, sparse
translation pointers, recipe hooks and accepted item cards/bubbles are unchanged.

The build enumerates **431 valid descriptions**, using sparse table `0x974EA8`
and original-description fallback. All fit without shortening: at most **27
characters / 216px** per row within 220px, and **six rows / 54px** within 60px.
The gate rejects unknown inline controls, catalogue drift and excessive nodes.
All 431 descriptions run through the corrected machine-code helper in tests.

## Verification model and limits

The new tests reproduce both old regressions, then exercise the corrected paths:

- HANT: nonzero/pointer-like incoming saved registers; native X and Y setters;
  zero/malformed counts; all tested scrolling positions in 5px steps; counts
  1, 16, 17, 19, 34, 55, 70 and 80; null slots; state canaries; saved-register
  preservation. Entry mode values 0–7 are exercised.
- Details: actual converter termination and signed-control packing; realistic
  32-bit node metadata and stride; pointer ending in `FF00`; all 431 records;
  unchanged text, unrelated hooks and invalid-control fail-closed behavior.
- Composition: pinned input hashes, deterministic component replay, exact
  permitted byte owners, runtime-status reporting separate from user feedback.

These are bounded instruction tests, not a full emulator run. New harnesses
lower EE SQ/LQ to 64-bit SD/LD and do not prove upper 128-bit lanes. Geometry
builders and upstream constructor/external effects are stubbed where specified
in each harness. Native setters and the relevant parser instructions execute.
No GPU screenshot or cold-boot visual acceptance is inferred from these tests.
An independent reviewer was unavailable because delegated runs hit the account
usage limit; no independent-review result is claimed.

## Release inputs, artifacts and checks

| Pinned input | SHA-256 |
| --- | --- |
| 15h ISO | `3c4a2a57079070fed5c205aa338e45d88371164dc4ccc0db36fc402f88c5ace8` |
| 15h ELF | `de5b2e49ffc0a458a053becd50ac6fcf511a194319038a79236e19187ade4816` |
| Approved 15f ISO | `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0` |
| Official PS4 English.bytes | `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b` |

The new builder independently reconstructs 15g and 15h, composes the correction
twice, verifies the installed input ELF, clones approved 15f, installs the
finished executable and audits every finished-disc byte. Both-endian directory
sizes are updated; no old artifact is overwritten. Independent ROFS validation
compares all 10,656 lookup records to pristine. Approved 15f/art, q/t, history,
native save identity and scoped startup remain release gates.

Outputs:

- `local/r67-candidates/67.15i-hant-text-item-details.iso`
- `local/r67-15i-hant-text-item-details.elf`
- `local/r67-15i-hant-text-item-details.json`
- `local/r67-15i-whole-iso-audit.json`

Fresh full suite: **679 tests, 14 expected skips, zero failures** in 162.220s.
All **15 new tests** also passed together in 18.625s. The build and independent
post-rename hashes passed:

| Finished artifact | SHA-256 |
| --- | --- |
| 15i ISO | `ab31dd12eae33beace62b00f7fb7765c203959b210747071668a61c87eb3dafc` |
| 15i ELF | `ffd1fb3f912268d589c19b607eeed68899ac0c31151c731aac59afeb913c8096` |

The complete **2,095,382,528-byte** disc audit found **68,164 changed bytes**
against approved 15f (including inherited 15g/15h), **zero unexplained**.
DATA.CVM, all art and ADV resources are byte-identical. Independent ROFS audit:
**10,656 records, zero mismatches or unmatched records**.

Startup is **155/155 scoped, 154/155 raw**, using only the documented unchanged
`memory_card_8` exception. History **4/4**, save descriptors **15/15**, namespace
`BISLPM-66511Save`, serial `SLPM-66511`, q/t and latest 15f preservation all pass.
The inherited q/t in-memory reconstructions remain explicit; historical locks
were not rewritten. Latest preservation includes 500 item-name pointer slots,
446 catalogue names, two accepted hooks and four protected art chunks.

Final appended owners: Details helper **0x976200** (908 bytes), HANT entry
**0x97658C**, HANT slot selection **0x9765B8** (80 bytes together).
The user's three regression screenshots are preserved in ignored
`local/r67-15i-evidence/`; copyrighted binaries and private screenshots are not
committed.

The builder refuses existing output paths; do not delete old outputs just to
rerun it. Its pre-rename startup path ends in `.incomplete`; the final renamed
artifact was independently hashed and matches the report.

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m unittest discover -s tests -q

uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m tools.r67_15i_iso_release
```

## Remaining translation and runtime boundaries

Whole-catalogue layout does **not** mean whole-catalogue English completion.
Inherited coverage remains 391 nonempty official descriptions, four empty
records and **36 unresolved records (IDs 500–535, 106 unmatched Japanese rows)**.
Those fallbacks also receive the layout fix, but their wording is unchanged.
Do not author replacements while claiming they came from the official corpus.
Military-attack route coverage is inherited evidence, not a new playthrough.

## Next screenshot checklist

The user operates PCSX2; this list does not authorize session/card/settings edits.

1. Cold boot the **15i ISO**, load the normal Soul Well save, and avoid an old
   executable-bearing savestate. Record the exact ISO hash with the test.
2. SELECT Details: capture the reported shotgun and high-carbon-steel blade,
   compressed gas grenade, Aqua Regia and a long six-row entry. Final words must
   remain inside the border and above recipes. Reopen and switch items.
3. Open several HANT categories, not only Help: capture full text bodies, scroll
   to bottom and back, switch categories and reopen. Include Item Synthesis,
   Save & Load, Wire Gun Controls and Jumping, plus non-Help body pages.
4. Repeat four or five HANT pages in one run, then use Aqua Regia and enter the
   doorway. Capture the fully loaded next area. The prior 15h success is user
   confirmed; this sequence checks that the repair preserves it.
5. Check recipe ingredient/result names and numbers, right-card names, both
   Compound/Can't bubbles, Gold Chains and tablet text against accepted behavior.
6. If anything fails, retain the exact ISO hash, screenshot and same-run log.
   Do not change emulator settings or overwrite the original save as a workaround.

## Return prompt

Continue Kowloon from `docs/R67_15I_HANDOFF.md` in the existing first-save-r67
worktree. Verify main/PR status and the 15i ISO hash. The HANT regression was
missing viewport-counter initialization plus X-setter handle reload ordering;
Details rejected native signed end nodes and misclassified glyph pointers.
The repair preserves 19-slot HANT safety and all official text. Review new user
screenshots across HANT categories and Details, and repeat the post-HANT doorway
route. Do not confuse whole-catalogue layout or main integration with gameplay
approval or resolution of the 36 unmatched official-source records. Preserve
all prior releases, accepted locks and original saves.
