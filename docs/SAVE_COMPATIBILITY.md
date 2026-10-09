# Cross-release PS2 memory-card save compatibility

The approved runtime baseline is **v11-r66** (serial SLPM-66511; save namespace
BISLPM-66511Save). Normal PS2 memory-card saves must load in future releases.
PCSX2 savestates are **not** compatible test artifacts.

## One-time baseline preparation (offline)

1. **Close PCSX2 yourself**, and ensure its memory cards are quiescent. The
   assistant must not launch or control PCSX2 without Pablo's approval.
2. Identify a **formatted** memory-card image containing an actual Kowloon
   in-game save. The script checks the PS2 header only; it does **not**
   validate filesystem integrity, save presence or progression. A recently
   used card is not automatically a golden save.
3. From the repository, create a snapshot in a NEW directory:

       python3 -m tools.save_compatibility snapshot \
         --source "$HOME/Library/Application Support/PCSX2/memcards/Mcd001.ps2" \
         --destination local/save-compat/r66-UNIQUE-CHECKPOINT
       python3 -m tools.save_compatibility verify \
         --destination local/save-compat/r66-UNIQUE-CHECKPOINT --preflight

   An existing destination is never overwritten. Snapshots go under
   ignored local/; **never commit/share memory-card images**. The reference
   card is read-only; r66.ps2 and candidate.ps2 are separate writable copies.
   SHA-256 and original source metadata are verified on snapshot creation.
   Keep an additional offline backup and checksum of the golden reference.
4. If no actual Kowloon save exists, **first** create one in r66 using an
   expendable working copy of the card, close PCSX2, then snapshot **that
   working copy**. Do not call an empty-card snapshot a save baseline.
   Preserve the original memory-card image throughout.

## Per-candidate runtime gate (requires Pablo's explicit approval)

Before testing a release, verify the golden reference and prepare fresh
disposable copies of it. Existing candidate-written cards must not be reused
for a fresh baseline comparison. On an unused pair, --preflight requires
both clones to match the baseline hash.

1. Cold boot the approved r66 ISO with the **r66 clone** installed in PCSX2,
   not the original card. Do **not** load a savestate. Load the known save.
   Record protagonist, chapter/scenario, location, party, inventory, quest
   flags, and available progression/action.
2. Exit PCSX2. Cold boot the candidate ISO with the **candidate clone**
   of the **same golden reference**. Compare recorded state and perform
   a meaningful story transition, then save normally.
3. Close and cold-restart the candidate and reload its newly written save.
   Confirm persistence, story progression, inventory and flags. Load in r66
   too **only when backwards compatibility is promised**, on a further
   disposable copy.
4. After testing, run:

       python3 -m tools.save_compatibility verify \
         --destination local/save-compat/r66-UNIQUE-CHECKPOINT

   This confirms immutable golden-reference integrity, not gameplay
   success. Differences in writable clones after runtime are expected.
5. Record both ISO SHA-256 values, golden-save SHA-256, scene/screenshot
   evidence, test date, observed state and Pablo's signoff under ignored
   local/save-compat/. Block any release if a save disappears, corrupts,
   loses inventory/flags or fails a progression transition.

Serial, namespace, serialized structures, scenario/item IDs and save/load
routines remain unchanged. The 15 original save-path checks are necessary
but do **not** replace this runtime test.

## Disaster recovery

Never use a runtime-written disposable clone as the golden seed. Prepare
each new release from the unchanged golden reference. Do not overwrite
existing snapshots. If reference integrity or actual save presence is in
doubt, stop, restore from the offline backup and establish a new
independently verified checkpoint.
