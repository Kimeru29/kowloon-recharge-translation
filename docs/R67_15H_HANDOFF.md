# r67.15h — item overflow and HANT pool diagnostic

## Scope and acceptance boundary

Repair the reported SELECT Details overflow and left-side compounding recipe
names; investigate the indefinite animated area load after using Aqua Regia on
Gold Chains. The user confirmed opening/scrolling at least four or five HANT
Help pages earlier in that run. Preserve official wording, accepted right-card
names and action bubbles, other UI screens, all previous releases and saves.

The HANT handle overrun is reproduced in native-instruction tests and corrected.
Its correspondence to the captured log is strong; its causality for the later
door stall is **not proven**. Neither a static test nor a finished ISO audit is
gameplay approval. Do not merge without the user's new gameplay acceptance.

Worktree: `/Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.
Branch: `fix/67.15h-details-area-transition`.
Base: `c2033b1fa77957ce888649cecb8f8951467a9eb5`,
`feat/67.15g-prologue-details-help` ([draft PR #51](https://github.com/Kimeru29/kowloon-recharge-translation/pull/51)).

Publication: [draft PR #52](https://github.com/Kimeru29/kowloon-recharge-translation/pull/52),
stacked on `feat/67.15g-prologue-details-help`. Implementation and verified build
checkpoint: `905d4b1` (`Fix r67.15h item text bounds and HANT viewport handle pool`).
This publication note is a subsequent documentation-only commit. The branch is
pushed; no merge is authorized or performed.

## Changes and native ownership

| Component | Owners and correction | Evidence |
| --- | --- | --- |
| SELECT Details | Constructor call `0x11518C`; instance-only fullwidth-to-halfwidth space nodes, 0.5 scale, added line spacing -9 for native 9px pitch. Six-row maximum ends before the recipe region. No wording changes. | [Item layout](R67_15H_ITEM_LAYOUT.md) |
| Left recipe names | Calls `0x115458`, `0x11554C`, `0x1155BC`; normalize instance spaces and bound name advance to 114px, conservatively reserving a full icon cell and gap before numeric columns. Preserve constructor handles, colors and numeric formatting. | [Item layout](R67_15H_ITEM_LAYOUT.md) |
| HANT viewport | Draw `0x28FD60`; relocate the 16-handle pool from private `+0x17A0` to `+0x1A94`, capacity 19, owner allocation `0x1AE0`. Coordinate predicate, pitches, icons and scrolling stay native. Real bounds, null-child handling, explicit initialization, reset/fade coverage and allocation-failure return. | [HANT pool](R67_15H_HANT_POOL.md) |
| Loading investigation | Old seventeenth handle aliases state 5; `5+0x3C=0x41` matches logged invalid text-handle accesses. All installed file lookup metadata matches. No forced transition or timeout bypass. | [Investigation](R67_15H_AREA_TRANSITION_INVESTIGATION.md) |
| Integration | Rebuild pinned 15g from approved 15f and official corpus, compose item layout then HANT twice, exact byte owners, finished-disc audit and independent ROFS comparison. | [Release contract](R67_15H_RELEASE.md) |

The text harness explicitly models unsupported EE accumulator instructions and
128-bit register save/load lanes. It is not a full PCSX2 gameplay run. The HANT
harness covers viewport/reset/fade/initialization/failure paths; actual child
task teardown/leak behavior is not runtime-verified.

## Immutable inputs

| Input | SHA-256 |
| --- | --- |
| 15g ISO `67.15g-partial-diagnostic.iso` | `cb2ef57789d62fc078678285da86e272eaf426740f181d576126be4d1946f267` |
| 15g ELF | `74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee` |
| Approved 15f ISO | `e60551bb44fdc27c29b06484a56722d54c0522591c87386741bd6e7d954ff9c0` |
| Official `English.bytes` | `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b` |
| Pristine PS2 ELF extracted during ROFS audit | `6cc4f52dd2b576396003a9455f8222c9b647aa2d7076c08a97c703778d024794` |
| Captured user-run log | `354c5cb9da253a3d6828e9a511e9ecf20526c0934983d93f58cc77c7b67a1848` |

Official corpus path:
`/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes`.
Screenshots and log are preserved under ignored `local/r67-15h-evidence/`;
neither copyrighted binaries nor private run evidence is committed.

## Verification and artifact

Fresh integrated suite: **664 tests, 14 skipped, zero failures** in 142.018
seconds. The baseline had 621 tests and the same 14 skips; all 43 new tests ran.
Component results: 13 item-layout tests, 14 HANT tests, and 16 combined
release/ROFS tests passed.

Built diagnostic: `local/r67-candidates/67.15h-details-transition-diagnostic.iso`.

| Artifact | SHA-256 |
| --- | --- |
| Finished ISO | `3c4a2a57079070fed5c205aa338e45d88371164dc4ccc0db36fc402f88c5ace8` |
| ELF `local/r67-15h-details-transition-diagnostic.elf` | `de5b2e49ffc0a458a053becd50ac6fcf511a194319038a79236e19187ade4816` |

Machine-readable reports are `local/r67-15h-details-transition-diagnostic.json`
and `local/r67-15h-details-transition-whole-iso-audit.json`. The complete disc
comparison covers **2,095,382,528 bytes**, with **67,452 modified bytes and zero
unexplained bytes versus approved 15f** (includes inherited 15g changes).
DATA.CVM and all art/ADV resources are byte-identical to that baseline.
The independent finished-image ROFS audit matched **10,656** file records,
including 969 resized/relocated records since pristine, with zero mismatches.

Startup: **155/155 scoped, 154/155 raw**, with only the documented unchanged
`memory_card_8` bounded-wording exception. Protected history: **4/4**. Native save
descriptors: **15/15**; serial and namespace unchanged. q/t locks passed with
the already-documented in-memory-only reconstruction of the accepted Lion
callsites and 15g western tablet pointers; historical manifests were not edited.
Latest 15f preservation passed: both accepted native hook words, 500 item-name
pointer slots, 446 catalogue entries and four protected art chunks retained.
These checks do not establish runtime save compatibility.

No original ISO, save, card, savestate, emulator configuration or emulator
session was modified. The build audited its `.incomplete` clone before renaming
it; startup report paths therefore retain that temporary name. The final ISO's
hash is identical. Publication status is recorded above.

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 \
  --with pillow --with numpy --with unicorn --with capstone \
  --with opencv-python-headless --with UnityPy \
  python -m unittest discover -s tests -q
```

## Exact next gameplay checklist

The user operates PCSX2. This checklist does not authorize changing settings,
cards, saves, savestates or the emulator session. Keep the original normal save.

1. Cold boot the published 15h ISO and load the normal Soul Well save; do not
   resume an executable-bearing savestate from 15g.
2. Capture SELECT Details for the compressed gas grenade and Aqua Regia. Check
   complete final words, no right-edge overflow, and no spill into recipes.
   Include a long six-line description if available, and reopen/change items.
3. Capture left recipe ingredient/result rows for Hydrochloric Acid + Nitric
   Acid = Aqua Regia. Names must stay clear of icons and numbers; right-card
   names and Compound/Can't bubbles must remain as accepted.
4. Fully scroll Item Synthesis, Save & Load, Wire Gun Controls and Jumping Help
   pages to the bottom and back, then close/reopen several pages. Check that
   bottom-visible text is present and no stale text remains.
5. In that same run, use Aqua Regia on Gold Chains and enter the doorway.
   Capture the fully loaded destination, not just a changed loading message.
6. If loading still stalls, preserve that run's log and exact ISO hash. Do not
   overwrite the save or silently enable debugging. A separately authorized
   read-only guest-state capture would be the next diagnostic step.

## Translation scope retained

This does not finish the earlier catalogue-wide translation request. The 15g
coverage remains: 431 valid Details records, 391 nonempty official descriptions,
four empty records, and **36 unresolved records (IDs 500–535)** retaining 106
unmatched Japanese source rows. Do not invent English to hide that source gap.
Military-attack route coverage/provenance is inherited, not a newly verified
playthrough. Historical q/t and latest approved locks remain release gates.

## Return prompt

Continue Kowloon from `docs/R67_15H_HANDOFF.md` in the existing
`.worktrees/first-save-r67` worktree. Verify the branch, release hash and draft PR
before edits. Treat 15h as a diagnostic, not gameplay-approved. Review the user's
new Details/recipe/HANT screenshots and whether the Aqua Regia doorway loads
after scrolling four Help pages. If it still stalls, retain the log and diagnose
the actual wait; do not assume the corrected HANT overrun was its cause. Preserve
all approved locks, prior ISOs and saves; no merge or emulator changes without
the required explicit consent. Keep the 36 unresolved official-source records
visible in scope reporting.
