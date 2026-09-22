# Localization status

This file is the authoritative runtime/localization ledger. Update a row only when new static or runtime evidence changes its state. Static verification never upgrades a surface to runtime-proven by itself.

Status meanings:

- **Working / runtime-proven** — observed in PCSX2 and accepted for the tested surface.
- **Translated but buggy** — English exists, but the runtime surface has a proven defect or unresolved transition.
- **Still Japanese / unresolved** — no safe accepted English implementation exists yet.
- **Not runtime-tested** — statically translated/verified but not yet observed successfully in PCSX2.

## Startup / first-play flow

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| 29 random opening quotations (`TR000`-`TR028`) | **Working / runtime-proven** | v6 runtime showed the English quotation artwork correctly; generated files remain same-size indexed PS2 TMX. |
| Title `New Game` / `Load Game` | **Working / runtime-proven** | v6 runtime showed both exact English labels correctly. |
| Name-entry English button graphics (`B_GP019.BIN`) | **Working / runtime-proven** | v6 runtime showed Back/Edit/Finish/Delete/Confirm controls correctly. |
| `Enter last name.` | **Working / runtime-proven** | v6 runtime showed the wide English prompt correctly. |
| Lowercase Latin keyboard | **Working / runtime-proven** | v6 runtime showed and accepted lowercase Latin input. |
| Uppercase Latin keyboard | **Not runtime-tested** | v6 stored uppercase in rows 7-13, but PS2 code only indexes rows 0-6. v7 folds uppercase into the reachable rows; static tests prove `A-Z` are reachable. Runtime proof still required. |
| Name fields / permanent name storage | **Translated but buggy** | PS2 editor is structurally two 3-glyph permanent fields: two 6-byte buffers, six-position cursor, split/layout/delete logic at position 3. v7 intentionally does not patch this until a buffer-safe direct-Latin design is proven. |
| `Enter first name.` | **Not runtime-tested** | Official wide English is present and statically verified; v6 test stopped before a clean acceptance of this state. |
| `Enter reading for last name.` | **Not runtime-tested** | v6 incorrectly blanked this active prompt. v7 relocates the official prompt into the shared translation PT_LOAD; final-ISO verifier checks the exact wide string. |
| `Enter reading for first name.` | **Not runtime-tested** | Same v6 regression/fix as the previous row. |
| Reading-input states | **Translated but buggy** | States are active in the PS2 state machine. v7 restores their labels, but direct English name/readings behavior is not yet runtime-proven. |
| Finish/advance after name-reading input | **Translated but buggy** | v6 appeared to freeze after completing the hidden reading flow. Persistence helpers are simple fixed-size copies; root cause remains unproven. Retest with the restored v7 prompts before deeper state tracing. |
| `Is this fine?` / `Yes / No` | **Not runtime-tested** | Official English is statically present; blocked by the v6 name-entry failure. |
| License-ID messages | **Not runtime-tested** | `Verifying license ID...` and `ID verification complete.` are statically present. |
| `Heracleion Shrine` | **Not runtime-tested** | Statically translated as wide executable text. |
| H.A.N.T. tutorial | **Not runtime-tested** | Official English is relocated into the executable translation PT_LOAD and passes static verification. |
| ADV horizontal dialogue renderer | **Not runtime-tested** | Four-instruction fail-closed renderer transform is present; v5 proved the pre-fix vertical failure. |
| First old-man DG00 English dialogue | **Not runtime-tested** | English MTX data is present and statically accepted; runtime blocked before reaching it. |
| DG00 English choices | **Not runtime-tested** | Reviewed KSF overrides/imports are present; runtime blocked before reaching them. |

## Known executable/UI text not yet solved

| Surface | Status | Evidence / next action |
| --- | --- | --- |
| `Return above ground` | **Still Japanese / unresolved** | Exact official English is known, but the current compact executable slot cannot hold it safely. |
| `Report card` | **Still Japanese / unresolved** | Exact official English is known, but it does not fit the proven fixed slot. |
| `メディア` | **Still Japanese / unresolved** | No exact official dictionary mapping has been proven for this PS2-only label. |

## Corpus-level translation coverage

| Class | Status | Current evidence |
| --- | --- | --- |
| Exact mapped MTX | **Partially translated** | 962 files / 56,642 official English entries imported. 23 exact mapped files / 21,672 entries remain rejected because their localization semantics are indirect/dynamic. |
| Changed/template MTX | **Partially translated** | 7 files / 2,284 entries proven and imported. Consolidated FD00 remains the largest special class; only `FD00_31` is currently proven among the 26-file FD00 family. |
| KSF | **Partially translated** | 868 fitting official entries imported; 48 overflow entries and 4 ambiguous entries remain unresolved. |
| PS2-only text | **Still Japanese / unresolved** | Lexical proxy estimates 419 novel runs / 3,672 Japanese characters beyond reused mapped content. This is an estimator, not a dialogue-line percentage. |
| Broad graphics beyond startup | **Still Japanese / unresolved** | Indexed PS2 graphics porting is proven for the startup asset classes; other layouts still need per-format proof. |

## Candidate history

### v6 — runtime failed in name entry

Static verifier: 96/96. Runtime proved the quotation, title, name-entry graphics, `Enter last name.`, and lowercase keyboard. It then exposed the 3+3 name structure, inaccessible uppercase rows, a blank active reading prompt caused by our suppression, and an apparent freeze after completing that hidden flow.

### v7 — current static candidate

- path: `/private/tmp/kowloon-recharge-startup-en-v7.iso`
- ISO SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`
- translated/final ELF size: 8,402,095 bytes
- final post-ROFS ELF SHA-256: `b4b21905f920f8fb6472c198088d990f631f9d6f0ab02d3e66d05c86c3fb4432`
- overlays: 1,143 total; 890 in place / 253 relocated
- embedded growth: +900 sectors; 17 shifted outer files
- executable ROFS records: 1,143/1,143 patched/re-resolved
- whole ISO size unchanged: 2,095,382,528 bytes
- source/test suite: 122/122 with Pillow
- final-image startup acceptance: **98/98** (`local/startup-acceptance-v7.json`)

v7 changes only the newly proven name-entry fixes: both official reading prompts are restored via the shared translation PT_LOAD, and uppercase Latin keys are folded into the seven keyboard rows the PS2 code can actually reach. The structural 3+3 name limit remains deliberately unresolved.

## Runtime gate for v7

Do not launch PCSX2 automatically. Before launch, state the exact expected visual sequence and wait for Pablo's explicit approval.

The minimum v7 regression scope is:

1. opening quotation and title still look exactly as accepted;
2. `Enter last name.` still renders correctly;
3. both lowercase and uppercase Latin letters are selectable on the visible keyboard;
4. the 3+3 name-field limitation is expected to remain and is not a v7 acceptance failure by itself;
5. after the name input, `Enter reading for last name.` must be visible instead of a blank prompt;
6. the following reading prompt must be `Enter reading for first name.`;
7. complete both reading inputs and determine whether the flow reaches confirmation or still freezes;
8. if it advances, continue capturing every text-bearing screen through the first old-man dialogue; Japanese text, garbage text, or vertical dialogue is a failed checkpoint.
