# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Committed accepted baseline

`translations/accepted.json` stores stable IDs, source/output hashes and provenance rather than copyrighted script content. It currently records the historical accepted DG00 MTX, constrained DG00 KSF, and the previously accepted early-UI ELF checkpoint.

v5, v6 and v7 were runtime-tested and failed the full startup acceptance scope. A later emulator log proved the next supervised session had actually booted v8; that run exposed the allocator-protected-but-still-stuck reading flow and the missing memory-card aliases. v10 advanced through the startup/name flow into the first old-man scene and established the presentation baseline. Original v11 was then runtime-tested and also failed presentation acceptance despite 130/130 static checks: DG dialogue remained vertical, H.A.N.T. clipped at its live presentation width, the English pre-title memory-card line clipped, and Japanese H.A.N.T. chrome remained. v11-r3 later booted but its corrected target screens were not re-observed. **v11-r5 is the current deterministic candidate**; it has not been launched in PCSX2. The structural 3+3 name behavior remains unresolved; the screenshot-confirmed memory-card clipping is now explicitly targeted by r5 rather than left out of scope.

## Gate semantics

- additions are allowed;
- mutation/removal of an accepted stable ID fails until intentionally reviewed;
- source-preimage/hash drift fails;
- serial drift from `SLPM-66511` fails;
- save-directory drift from `BISLPM-66511Save` fails;
- duplicate stable IDs fail.

Core implementation: `tools/regression.py`; CLI: `tools/check_regression.py`.

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
```

## Finished-image gate

The generic builder validates the completed nested image, not only intermediate files. For the startup candidate it verifies:

- outer ISO declared volume and total byte size remain unchanged;
- CVM header, outer `DATA.CVM` record and embedded PVD agree;
- every overlay payload in the finished ISO hashes to its generated overlay input;
- the 17 shifted outer-tail files remain byte-identical;
- `SLPM_665.11` may grow/relocate only through the tested builder path and retains `SLPM-66511` + `BISLPM-66511Save`;
- every one of the **1,145** overlay assets has a unique executable ROFS record that re-resolves to its final size/extent;
- startup graphics retain the exact pristine file size, differ from pristine content, and hash exactly to their local generated overlay;
- `tools/startup_acceptance.py` independently reopens the final ISO and checks title/name wide-pointer paths, Latin keyboard, the state-9 skip-reading instruction invariant, the license-completion X owner, ADV horizontal renderer/orientation instructions, active translation PT_LOAD, H.A.N.T. translated rows/controller metadata + page-local 12px style + seven chrome-label relocations + unresolved-source preservation, semantic command-menu fixed labels, long-label relocations and unresolved-pristine owners, memory-card table + boot-handler aliases, 32 startup graphics + ROFS records, DG00 English/removal assertions and DG00 KSF choices;
- the standalone ELF mutation guard compares the pristine executable to `build_early_ui_elf` byte-for-byte before the appended segment and rejects every mutation outside explicitly declared title/name/menu/ADV/H.A.N.T./memory-card/pointer/ELF-metadata regions.

Historical v6 (**96/96**) and v7 (**98/98**) final-image acceptance both preceded runtime failures; static acceptance is therefore necessary but not sufficient. v8 final-image acceptance is **120/120** (`local/startup-acceptance-v8.json`). v9 is **121/121** (`local/startup-acceptance-v9.json`) and adds a named GP088_12 packed-title chunk check. v10 is **123/123** (`local/startup-acceptance-v10.json`) and additionally verifies both memory-card boot aliases and the state-9 skip-reading instruction invariant; a second pristine v10 build is byte-for-byte identical. The later v10 runtime test promotes only the explicitly observed startup/name progression, quote rotation, correct title text, and English first-dialogue content. It does not convert unobserved static invariants into runtime proof, and it records the title/H.A.N.T./menu/vertical-dialogue defects as the v11 regression baseline.

v11 established separately named renderer gates but runtime later disproved two assumptions, reinforcing that static acceptance is only a prerequisite. v11-r4 extends that contract with fail-closed `hant_tutorial_font_style`, `hant_chrome_labels`, the upstream DG all-canvas orientation word, and the license-completion X owner. The measured r4 candidate passes **132/132** final-image checks, hashes to `3566b2395165cf4ba4b34ebed874ba405f17c0d452753786cfc116ed80c494bb`, and `/private/tmp/kowloon-recharge-startup-en-v11-r4-repeat.iso` is byte-for-byte identical. Its final post-ROFS ELF hash is `54690aed73a68d19e8b1fcd787e346086fbd3bb30dd9dea9b39b99acf93d3d9f`; the pre-ROFS ELF hash is `4501cee41d3941d40c687f9806b51aa0196f6c206132fd6614f3bbe8ee461a43`. Both full suites execute **182 tests** (8 dependency-free skips, 1 Pillow-enabled owned-corpus skip). PCSX2 has not been launched for r4, so none of the four r4 fixes is promoted to runtime-proven.

v11-r5 adds named gates for the separate speaker-name orientation, page-local H.A.N.T. 18px row stride, the promoted 15-entry Help-topic owner table, and the additional `B_GP020.BIN` graphics/ROFS pair. The generated GP020 atlas is itself fail-closed by per-region source hashes and preserves every pixel outside its nine caption rectangles. The measured r5 candidate passes **137/137** final-image checks, hashes to `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`, and the repeat ISO is byte-for-byte identical. Its pre-ROFS ELF is `6e385c38fd012d8d11a5e3f0f20220412506ed6aa43b75b8bd712035365a28fa`; post-ROFS ELF is `c3b228c946df9bae9d8aec81058a04801de1483191c28d5077087e1d9c2d3eee`. Both suites execute **191 tests** (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). No r5 runtime claim is made.

## Save compatibility smoke test

Before runtime testing, back up the PCSX2 memory card. After the first successful in-game create/load test, keep a golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are disposable across builds.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that candidate are stated.
