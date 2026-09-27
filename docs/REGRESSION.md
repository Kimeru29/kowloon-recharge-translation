# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Committed accepted baseline

`translations/accepted.json` stores stable IDs, source/output hashes and provenance rather than copyrighted script content. It currently records the historical accepted DG00 MTX, constrained DG00 KSF, and the previously accepted early-UI ELF checkpoint.

v5, v6 and v7 were runtime-tested and failed the full startup acceptance scope. A later emulator log proved the next supervised session had actually booted v8; that run exposed the allocator-protected-but-still-stuck reading flow and the missing memory-card aliases. v10 advanced through the startup/name flow into the first old-man scene and established the presentation baseline. Original v11 was then runtime-tested and also failed presentation acceptance despite 130/130 static checks: DG dialogue remained vertical, H.A.N.T. clipped at its live presentation width, the English pre-title memory-card line clipped, and Japanese H.A.N.T. chrome remained. v11-r3 later booted but its corrected target screens were not re-observed. Pablo manually tested v11-r5 and later v11-r6. r6 materially improved the title labels and translated the deeper H.A.N.T. submenus, but dialogue still failed the PS4-style block target, name/license prompts needed centering, the tablet needed more padding/centering, H.A.N.T. rows remained too loose and the title black backing remained incomplete. **v11-r7 is the current deterministic candidate** and has not been launched for runtime testing. The structural 3+3 name behavior remains unresolved.

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
- `tools/startup_acceptance.py` independently reopens the final ISO and checks title/name wide-pointer paths, Latin keyboard, the state-9 skip-reading instruction invariant, all six centered M_Name/license prompt X owners, ADV horizontal renderer/orientation + inline-speaker header/body-stride instructions, active translation PT_LOAD, H.A.N.T. translated rows/controller metadata + page-local 12px/16px layout + seven chrome labels + three Help categories + all 55 Help-topic labels + nine Config labels + unresolved-source preservation, semantic command-menu fixed labels, long-label relocations and unresolved-pristine owners, memory-card table + boot-handler aliases, 32 startup graphics + ROFS records, DG00 English/removal assertions and DG00 KSF choices;
- the standalone ELF mutation guard compares the pristine executable to `build_early_ui_elf` byte-for-byte before the appended segment and rejects every mutation outside explicitly declared title/name/menu/ADV/H.A.N.T./memory-card/pointer/ELF-metadata regions.

Historical v6 (**96/96**) and v7 (**98/98**) final-image acceptance both preceded runtime failures; static acceptance is therefore necessary but not sufficient. v8 final-image acceptance is **120/120** (`local/startup-acceptance-v8.json`). v9 is **121/121** (`local/startup-acceptance-v9.json`) and adds a named GP088_12 packed-title chunk check. v10 is **123/123** (`local/startup-acceptance-v10.json`) and additionally verifies both memory-card boot aliases and the state-9 skip-reading instruction invariant; a second pristine v10 build is byte-for-byte identical. The later v10 runtime test promotes only the explicitly observed startup/name progression, quote rotation, correct title text, and English first-dialogue content. It does not convert unobserved static invariants into runtime proof, and it records the title/H.A.N.T./menu/vertical-dialogue defects as the v11 regression baseline.

v11 established separately named renderer gates but runtime later disproved two assumptions, reinforcing that static acceptance is only a prerequisite. v11-r4 extends that contract with fail-closed `hant_tutorial_font_style`, `hant_chrome_labels`, the upstream DG all-canvas orientation word, and the license-completion X owner. The measured r4 candidate passes **132/132** final-image checks, hashes to `3566b2395165cf4ba4b34ebed874ba405f17c0d452753786cfc116ed80c494bb`, and `/private/tmp/kowloon-recharge-startup-en-v11-r4-repeat.iso` is byte-for-byte identical. Its final post-ROFS ELF hash is `54690aed73a68d19e8b1fcd787e346086fbd3bb30dd9dea9b39b99acf93d3d9f`; the pre-ROFS ELF hash is `4501cee41d3941d40c687f9806b51aa0196f6c206132fd6614f3bbe8ee461a43`. Both full suites execute **182 tests** (8 dependency-free skips, 1 Pillow-enabled owned-corpus skip). PCSX2 has not been launched for r4, so none of the four r4 fixes is promoted to runtime-proven.

v11-r5 adds named gates for the separate record-label orientation, page-local H.A.N.T. 18px row stride, the promoted 15-entry Help-topic owner table, and the additional `B_GP020.BIN` graphics/ROFS pair. The generated GP020 atlas is itself fail-closed by per-region source hashes and preserves every pixel outside its nine caption rectangles. The measured r5 candidate passes **137/137** final-image checks, hashes to `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`, and the repeat ISO is byte-for-byte identical. Its pre-ROFS ELF is `6e385c38fd012d8d11a5e3f0f20220412506ed6aa43b75b8bd712035365a28fa`; post-ROFS ELF is `c3b228c946df9bae9d8aec81058a04801de1483191c28d5077087e1d9c2d3eee`. Both suites execute **191 tests** (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). Pablo's r5 runtime test promotes only the GP020 top-level tiles and the 12px/18px tutorial presentation; the title, inline speaker, and deeper H.A.N.T. surfaces remained failures.

v11-r6 replaces those disproven assumptions with separately named gates: `adv_speaker_horizontal_layout` now includes the bracket-derived live speaker text mode at file `0x15006C`; `title_english_label_geometry` pins the recentered label anchors while requiring the packed GP088_12 art scale to remain pristine; H.A.N.T. acceptance now covers the three Help category labels, all 55 labels in the three sibling Help topic tables, and the nine-entry Config table. The measured r6 candidate passes **139/139** final-image checks, hashes to `dbd25ff8ada4724d6c280a32199dd3ef7fc49442923d904db56359ed02ef32a4`, and `/private/tmp/kowloon-recharge-startup-en-v11-r6-repeat.iso` is byte-for-byte identical. Its pre-ROFS ELF is `06b76b01e9ef1364f5c67473edaf1b68b367512ba0af7dd1ad533f726b64ecfa`; post-ROFS ELF is `0fe52d198679c9c2eb4784cab12a554f4569488af018fd9778c3b72ca031b0eb`. Both suites execute **198 tests** (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). These remain static/deterministic guarantees until Pablo manually accepts the r6 target screens.


v11-r7 replaces the runtime-disproven r6 speaker mode hypothesis with the actual generic-font orientation owner: the `0x190A50` constructor's orientation argument now depends on saved mode, only the bracket speaker uses horizontal mode 0, and its fixed header origin is X=20/Y=80. The transposed DG body additionally changes only its live Japanese 26px column multiplier to the exact 12px style-1 glyph advance. `name_prompt_centered_layout` fail-closes six M_Name/license X owners; the tablet payload adds measured padding/centering; H.A.N.T. retains the 12px font but changes the page-local row stride to 16px with recalculated controller metadata, and its long `Exploration` tab becomes `Ruins`. The r6 title anchors and packed-title scale remain unchanged because the remaining black backing is inside a multi-region atlas whose live sampled subregion is not yet proven. The measured r7 candidate passes **140/140** final-image checks, hashes to `2b64165f820ec208ff9d721b9fbf30d8ee17bb78b9556e7ebe540c83b27221b4`, and `/private/tmp/kowloon-recharge-startup-en-v11-r7-repeat.iso` is byte-for-byte identical. Its pre-ROFS ELF is `318f666a1c7cb990ec2cec91be32513c9abd8ddb16f5da4ffe186cb3976cdf7e`; post-ROFS ELF is `e520a919dd7e2a69c148f4cbe317b8f3ef2d729faa6f36e529a6b536b929b4bc`. Both suites execute **199 tests** (8 dependency-free skips / 1 Pillow-enabled owned-corpus skip). These remain static/deterministic guarantees until Pablo manually accepts the r7 target screens.

## Save compatibility smoke test

Before runtime testing, back up the PCSX2 memory card. After the first successful in-game create/load test, keep a golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are disposable across builds.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that candidate are stated.
