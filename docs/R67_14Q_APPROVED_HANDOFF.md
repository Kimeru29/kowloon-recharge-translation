# r67.14q — VISUALLY ACCEPTED Chamber event dialogues (2026-10-11)

## Acceptance

Pablo explicitly accepted the r67.14q **automatic companion-event dialogue** work after cold-boot visual review: the opening's entire first and second rows are enclosed within the original bubble, including final **“anytime.”**; the short **“Eerie place.”**, other old-man/door and trap dialogues are properly positioned. The approved output is:

- First opening row: `Make sure you're always ready to`
- Second opening row: `switch into battle mode anytime.`
- Event pen X advance `0.40`, font glyph actual width `0.40`; native approved glyph Y positions, text source argument restoration and two-row rendering unchanged.
- All normal automatic companion-event comments use a stable **240-frame (~4-second at 60 FPS)** hold. This is **not** the AFK/free-talk timer.
- All 30 companions' **AFK/free-talk** layout, native wrap, visual geometry and original 156/240-frame timing overrides are separately accepted. They are **permanently locked** and are not an editable target.
- Green dialogue bubble, blue backing/background, native history layout, H.A.N.T., action HUD, combat Help/Basic Attack and all previously visually accepted content are unchanged.

**This is a scoped visual approval, not a claim that the entire game is finished.** The native story text is no longer a work item; do not revisit font scaling, spacing, renderer placement, timers, bubble geometry, or script segmentation to fix unrelated Lion Statue UI.

Source snapshot:
- Branch: `fix/67.06-renderer-corrections`; user-approved baseline commit `86e5319760b5ca1cabe69fde806e4811dd1c0fe8` (r67.14q).
- Unmerged PR: https://github.com/Kimeru29/kowloon-recharge-translation/pull/42 (leave open).
- Worktree: `~/repos/kowloon-recharge-translation/.worktrees/first-save-r67`.
- Staged ELF (ignored): `local/r67-14q-opening-final-line-fit.elf`, SHA-256 `c3babe784c07f83312273ac789040b74ea46d492eea48eee0f1ae17ce5c781ba`.
- Finished ISO (ignored): `local/r67-candidates/67.14q-opening-final-line-fit.iso`, SHA-256 `3c07d63b0be346bc8493de581c28772272a2c6dd56a1704d528e0c95c7d44e96`.
- Build report `local/r67-14q-build.json`; ISO audit `local/r67-14q-whole-disc-audit.json`; 366 tests, 18 expected skips; 155/155 startup checks; 4/4 history region locks. Prior near-final r67.14p also retained as rollback.

## Added approval locks (independent of the next item UI)

The committed `translations/r67_14q_approved_lock.json` stores specific immutable **native code spans** (event state machine, AFK constructor, ordinary glyph renderer, private event helper), **16 exact critical native words**, and the **two exact approved visible English line bytes** plus event/door/Eerie header/pointer sentinels. Its baseline SHA-256s are *provenance*, NOT an attempt to force all future item-UI candidates to have an identical global ISO hash.

Reusable tool: `tools/r67_14q_approved_lock.py`.

Run on any **new staged candidate ELF**:

```sh
python3 -m tools.r67_14q_approved_lock --elf local/<new-candidate>.elf
```

Run on any **new finished candidate ISO**, using its own build report for the right ELF extent:

```sh
python3 -m tools.r67_14q_approved_lock --iso local/r67-candidates/<new-candidate>.iso --build-report local/<new-candidate>-build.json
```

Tests: `tests/test_r67_14q_approved_lock.py`. Positive checks cover the approved staged ELF and independently relocated finished ISO; negative mutations prove all four critical spans and the exact event native timer, pointer, header and visible text are protected. A mutation in the *distinct* `M_ObjGetDraw` UI owner must not fail the event/AFK lock. To change any locked owner, **do not regenerate the JSON manifest or bypass the check**; obtain an explicit new user-approved exception first and update the acceptance evidence.

Approval-lock validation on 2026-10-11: **373 tests passed, 18 expected skips; seven new lock-focused tests; both baseline staged ELF and embedded ISO owner locks passed; startup acceptance 155/155; history locks 4/4 each on ELF and ISO**. Full evidence: ignored `local/r67-14q-approved-lock-full-validation.log`.\n\nAlso run full `python3 -m unittest discover -s tests -q`, startup acceptance `155/155`, history lock against **new** ELF/ISO, whole finished ISO difference audit, and actual gameplay screenshots of both repaired Lion Statue UI cases. Tests alone cannot prove UI geometry.

## NEXT TASK — TWO Lion Statue UI overflow cases, do NOT fix in this locking step

Pablo supplied two screenshots at end of this chat:

1. **Lion Statue acquisition / new-item popup** after breaking a vase in Chamber of Lions: **“Lion Statue”**, the official English name, extends past its yellow/green-backed rectangular item pickup overlay (the word “Statue” partly exceeds the right side). Screenshot `image(20261011-214041).png`. The lion item description “Stone carving.” is visible below. The underlying official item catalog label for item ID **413** is correct and MUST remain `Lion Statue`. Earlier attempt to shorten shared catalog broke translation acceptance. Inspect the **pickup popup's own text placement/font scale/border width**, not general event/AFK dialogue.
2. **Stone pedestal/stone pillar interaction**: when the `PUSH` option is presented to push the Lion Statue into the stone pillar, “Lion Statue” next to `PUSH` is **clipped/truncated on the right**, overlapping the side-HUD area. Screenshot `image(20261011-214102).png`. Do not assume this uses the acquisition-popup owner. The previously accepted **Stone Pedestal Push / Use Item** action is frozen; locate the **item-name text position / target selection renderer** responsible for the clipping. Also do not conflate this with the distinct L1/R1 “Change target” owner described in older docs.

Technical breadcrumbs from prior reverse engineering:
- `docs/R67_06_RENDERER_PROGRESS.md`: item-acquisition `M_ObjGetDraw` registration at **VA 0x2A2344**, draw controller **0x2A23E0**, related `M_EvItemDraw` routes. Item text/sprite owners reach native `0x18AD30`. Separate popup-specific layout/scale/border owner must be isolated before patching.
- `tools/dungeon_item_names_data.py`, item ID **413**, source name `獅子の像`, exact English catalog name `Lion Statue`; earlier item pointer at ELF offset **0x391928**. Never replace catalog name globally.
- `docs/R67_07_FEEDBACK.md` and `docs/R67_04_PLAYTEST.md`: distinct L1/R1 `Change target` literal in fixed 32-byte slot **0x596CD0** with native call at VA **0x2A6AF8**. Previously moving guessed icon origins did not fix it. Do not repeat rejected experiments or assume this is the same as the stone pillar `PUSH Lion Statue` text.
- `tools/r67_06_layout.py` and `tests/test_r67_06_layout.py` protect the accepted Stone Pedestal Use/Push target; preserve its string and presentation except for separately proven item-caption coordinates.
- Previous accepted physical **Lion Statue inspection** is distinct from item pickup and must not regress.

New chat should **first inspect repository and provenance**, locate exactly which native owner produces each screenshot, inspect user-approved states read-only (never overwrite/restore without permission), design minimal per-owner fix, produce r67.14r or next available separate diagnostic, run all locks and static gates, cold-boot test with Pablo, and keep PR #42 unmerged until visual approval. Preserve the currently running PCSX2 process, global settings, all original savestates and unrelated applications.

See `docs/R67_16_CHAMBER_STORY_COMMENT_REPLACEMENT.md` for detailed history, r67.14n rejected header change, r67.14o safe reflow, r67.14p timing/advance and r67.14q final single-line semantic rewording.
