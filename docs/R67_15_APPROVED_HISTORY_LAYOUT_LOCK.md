# r67 — APPROVED START-history visual layout lock (2026-10-10)

## Approval and exact scope

Pablo visually approved the r67.12 START dialogue-history screenshot with **"perfection, let's lock it for now to prevent further changes."**

**Freeze the current verified presentation:** speaker first on its own horizontal row, dialogue directly below, compact 25 logical-pixel speaker/body spacing and a separate 12-pixel extra gap after spoken dialogue (37 pixels before the next speaker). Retain English left-to-right glyph advance and the r67.11 chronological ring-index mapping.

**The approval covers the screenshot's single visible old-man conversation.** Multiple successive conversations, long text wrapping, pagination/scrolling over 12 visible records, and first-Soul-Well release readiness remain unverified. Do not treat model-based ring-order tests as runtime acceptance of those scenarios. If they require changes later, obtain specific user permission before changing the approved layout.

Other remaining r67 work is **not** approved merely because START history is locked. PR #42 remains unmerged and there is no new release/tag.

## Technical freeze implementation

Checked-in manifest: `translations/r67_history_layout_lock.json`

Checked-in fail-closed verifier: `tools/r67_history_layout_lock.py`

The four immutable owners are pinned by 256-bit hashes:

1. `0x1538C0..0x153E30` (1,392 bytes): ADV history state machine, record selection, order, row spacing and grouping.
2. `0x155E90..0x155F30` (160 bytes): dedicated history font constructor selection.
3. `0x863CA0..0x863EE0` (576 bytes): history-only horizontally advancing constructor clone.
4. `0x863EE0..0x863F10` (48 bytes): chronological circular-history helper.

Both the local r67.12 staged ELF and the installed ELF inside the user-approved ISO match **all four** hashes. The verifier checks individual regions rather than the whole executable, allowing unrelated r67 fixes without silently changing history.

The corresponding regression suite `tests/test_r67_history_layout_lock.py` pins manifest fingerprints independently, checks the active ELF and ISO when they are available, rejects corrupted or overlapping locks and one-byte mutations to every protected owner, and confirms unrelated executable changes remain permissible.

## Mandatory future regression guard

Before sharing **any later r67 ISO**, verify its installed ELF against this lock:

```bash
python3 -m tools.r67_history_layout_lock --iso /path/to/new-r67-candidate.iso
```

For a staged ELF plus ISO:

```bash
python3 -m tools.r67_history_layout_lock \
  --elf /path/to/updated.elf \
  --iso /path/to/updated.iso
```

During full-suite testing, supply `R67_HISTORY_LOCK_ELF` and `R67_HISTORY_LOCK_ISO` to make the suite verify the **new** candidate artifacts, not just the original approved fixture. A regression guard failure means **STOP**: investigate the mismatch instead of updating the manifest or the reference hashes. Only change those hashes following explicit new approval for this exact screen.

To check the approved snapshot:

```bash
python3 -m tools.r67_history_layout_lock \
  --elf local/r67-12-history-compact.elf \
  --iso local/r67-candidates/67.12-history-compact-diagnostic.iso
```

This is a source/byte-level guard, not a substitute for in-game visual inspection. Do not edit original savestates, the real PCSX2 profile, or Edge/YouTube to validate it.

## Previously protected UI

The approved **H.A.N.T. Basic Attack** help screen remains separately frozen by `tools/r67_07_lock.py` and `tests/test_r67_07_lock.py`. The two locks are independent; neither may be weakened or removed for speed.

## Current review state

- Approved display ISO: `local/r67-candidates/67.12-history-compact-diagnostic.iso`.
- ISO SHA-256: `87cfa6f445eba36687e1d5badc621d9efd3157560a3be8da0c5eda4309a54e63`.
- Staged ELF SHA-256: `d531e8545c86322d09527bc2a8c32ee01e3d5fbda67f735a0a92acc2519b2179`.
- Embedded ELF SHA-256: `669b997d767d39c1ca5e29dc6458eaedc71bfe78e2fe74ca7f1dd9312858988c`.
- Previous ISO acceptance: **155/155** startup checks; no ISO bytes were changed by adding this lock.
- Lock verification: **4/4 protected regions PASS** in both the approved staged ELF and installed ISO ELF.
- Full Python regression suite after adding the lock: **304 tests, 17 expected skips, zero failures** (run with `R67_HISTORY_LOCK_ELF` and `R67_HISTORY_LOCK_ISO` set to the approved candidate).
- No generated copyrighted ISO, ROM, BIOS, emulator save, screenshot, or executable is committed to Git.

**Keep this approved history appearance unchanged until Pablo explicitly requests otherwise.**
