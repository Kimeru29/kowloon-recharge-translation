# r67.14t user acceptance locks + new automatic-dialogue regression report

## Accepted results — now permanently protected (2026-10-11)

Pablo visually approved both **Lion Statue fully enclosed** at the
acquisition popup, and **the Stone tablet immediately after Chamber of Lions,
properly enclosed and centered** when testing r67.14t.

The latest candidate is retained unchanged:
`local/r67-candidates/67.14t-lion-statue-and-tablets.iso`
SHA-256 `03526a1779822ad1ec15136c26ff8c3b50d6997bb395a601db228b3fc2fe321f`.

A dedicated committed-intent, uncommitted-on-disk immutable manifest is at
`translations/r67_14t_approved_ui_lock.json`; see
`tools/r67_14t_approved_ui_lock.py`. Run it on BOTH staged ELF and finished
ISO (with that ISO's own build report). It fails closed on:

- Lion Statue item ID 413, original shared catalog pointer/name;
- both native UI name-rendering callsites `0x2A2A6C` (pickup) and
  `0x2A6060` (PUSH selection);
- the exact accepted 112-byte private helper including X scale **0.72**
  and unmodified native Y scale;
- approved Chamber tablet record at `0x58A250` and both Anubis tablet
  records at `0x590F30`, `0x590FB0`, including all content field-pointer
  words AND SHA-256 of each referenced string;
- every Stone tablet class member (58) and all populated inscription rows
  (160), enforcing at most 21 full-width CP932 glyphs per row;
- all previously approved r67.14q native event/AFK/glyph/Y geometries and
  exact opening two English strings, via the unchanged q lock.

Focused mutation tests are in `tests/test_r67_14t_approved_ui_lock.py`;
the tests verify changed item-name pointer, either JAL, any scale word,
approved tablet descriptor/row pointer, string bytes, and the q event lock
fail instead of silently passing. For runtime screenshots, static tests
are not sufficient to claim visible geometry.

Local validation results:
- `local/r67-14t-accepted-ui-staged-lock.json`
- `local/r67-14t-accepted-ui-finished-lock.json`
- `local/r67-14t-ui-locks-full-regression.log`

## Newly reported regression — REPRODUCED IN USER SCREENSHOT, UNFIXED

User provided a screenshot of the opening automatic-event speech
`Make sure you're always ready to`, which now sits very low inside the
original green/blue speech bubble. The continuation is occluded/overlapped
at the lower green border. This must not be called working or approved.

The user says the same event geometry was correctly centered in the
previous accepted version. The precise reason for different runtime geometry
is **not yet proven**, despite byte-identical event code:

- PCSX2 last run's `emulog.txt` records an actual r67.14t boot from
  `local/r67-candidates/67.14t-lion-statue-and-tablets.iso`,
  CRC `B2A6289C`, with ELF loading. It contains no state-restore operation.
- r67.14q vs r67.14t native opening event calls and 2 approved string
  pointer words have been compared and are exactly equal.
- The existing `r67_14q_approved_lock` passed on r67.14t staged ELF and
  installed ISO, including native event code, private event helper (728
  bytes), generic glyph renderer, AFK free-talk and both approved lines.
- Complete 2,095,382,528-byte ISO audit `local/r67-14t-whole-iso-audit.json`
  says zero unclassified modifications: ONLY two new Lion UI native JALs,
  six Anubis row-pointer words, the appended Lion helper and compact English
  tablet data, ELF filesize metadata and outer ISO9660 ELF length changed.
  Neither bubble artwork nor dialogue renderer bytes differ from q.
- Both Lion interception callsites consume the original setter return and
  load new registers immediately afterwards. No proved caller use of
  `$v0` (or persistent temp register) after the new helper was observed,
  so assigning this regression to its return value is not supported.
- PCSX2 is closed; no new runtime EE snapshot corresponding to this
  failing screenshot is available. No PCSX2 memory cards, savestates, app
  configuration or running sessions have been modified.

**Implication:** previous static q approval locks were necessary but
insufficient; creating an additional identical q-derived build or blindly
modifying protected event Y positions does not establish a valid fix.
Changes to a visually approved event geometry may not be guessed merely to
force a new build. Investigate the *actual runtime presentation owner*.

### Runtime discriminating experiment (requires Pablo's consent/participation)

The key missing evidence is a screenshot of the SAME automatic opening
speech at the SAME settled display stage after a genuine cold boot of the
still SHA-pinned `r67.14q` ISO and one of `r67.14s`/`r67.14t`.
Do not load an older `*.p2s` savestate after switching executables;
doing so restores old code and invalidates the comparison. Avoid changing
original memory cards or emulator settings. A stable frame (e.g. after
the bubble enters and before it disappears) distinguishes an animation
stage from a persistent geometry regression. If the baseline q also
shows the low text in the same scene, the user-approved previous screenshot
represented a different runtime state/context. If q is centered and t is
not, isolate the indirect state/lifetime effect via the two new Lion
callsites vs six tablet strings using the already-retained r67.14r/s
candidate ISOs or approved read-only emulator instrumentation.

No r67.14u executable was produced. **Do not describe the dialogue as fixed.**
All previously approved renderers remain frozen, and no commit/push/PR/merge
was made. Runtime cross-release memory-card save validation is also pending.
