# r67 — START-history native parser probe (2026-10-10)

## User feedback on first font-style experiment

- Pablo tested `67.08-history-style1-diagnostic.iso` and reported that rendering **changed**, but history is **still vertical** and original formatting was lost.
- The supplied screenshot shows `[Old man's voice] / Hey; over here.` over the game scene with altered spacing/formatting. It is not a conclusive visual acceptance of the START history screen. Treat the first diagnostic as **rejected**.
- Original history font-style IDs `5/3/4` must stay intact. The previous diagnostic's replacement with `1/1/1` was too broad semantically even though it changed only three physical bytes.

## Distinct second diagnostic — retain font styles, change parsing routine

- Baseline: `local/r67-candidates/67.07-containment.iso`, SHA-256 `d5925fcf14959d041b0af45b38170f03e375eaefd43ccc9d089253a093acadfb`.
- Candidate: `local/r67-candidates/67.08-history-parser-diagnostic.iso`, SHA-256 `3cb35d3806d96927e46c76c58afb08f3872b127258f730e0d852f4b104116279`.
- Exact controlled patch in *installed* ELF: **one MIPS instruction** at file offset `0x90CD0`, VA `0x190C50`: `jal 0x18F6F0` (`0x0C063DBC`) → `jal 0x192400` (`0x0C064900`).
- The underlying caller `0x190A50` performs a switch on font style `0/1` vs `2+`: native `0x192400` parses styles `0/1`, while `0x18F6F0` handles higher styles. Both entrypoints have matching two-argument signatures in the factory and similar internal control-code parsing. The experiment routes all style `2+` to the alternative parser **without changing style ID or glyph resource descriptor**.
- **Important scope caveat:** `0x190C50` is a shared factory dispatch. This affects **all** style `2+` text objects, not just history, and could regress other screens. It is therefore **diagnostic only**, irrespective of the outcome. Any final patch must constrain this behavior to the ADV history objects created via `0x255E10`, without changing normal dialogue or approved H.A.N.T.
- The installed ELF SHA-256 advances from `1db2b2bfe2dc9df4ab54b71775688062d28bb5922436168051621f8925cdc591` to `8b15f9cf06cd32720478d3586d35a23100a3c02d6cc3fdc7c8672caf19c0e03f`. ISO size is unchanged; original save namespace and all other ISO bytes are unchanged.

## Static check and release gate

- Baseline and second diagnostic both run `tools.startup_acceptance` at **153/155**, same graphics fixture issues (`BLBRD/B_GP020.BIN` mismatch and `31/32` graphics). Their equality verifies no **new detected** acceptance failure; it does not constitute runtime correctness. Do not weaken checks or claim the historical `155/155` gate met.
- The original 8BitDo, PCSX2 settings, real savestates and memory cards must not be modified by automated testing. **Do not send global keyboard shortcuts affecting Edge/YouTube.**
- Diagnostic source script is local and untracked: `/tmp/r67-history-parser-diagnostic.py`; diagnostic metadata is stored locally at `local/pcsx2-67.06-isolated/history-parser-diagnostic.txt`.
- No experimental ISO should be merged, tagged as r67 or included in Git.

## Immediate next step — do not start other issues

Have Pablo open `67.08-history-parser-diagnostic.iso` using his existing physical 8BitDo controller and copied slot-2 savestate and send the **START history screen screenshot**, along with a regular dialogue screenshot only if it has regressed. Verify full horizontal words, speaker and body formatting, line wraps, scroll behavior. If the parser route fixes orientation, build a history-only dispatch and regression test it; otherwise revert this one-instruction hypothesis and continue tracing glyph advance in `0x18F6F0`. Keep the H.A.N.T. Basic Attack screen frozen.
