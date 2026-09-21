# Whole-game build implementation plan

## Milestone A — generic build layer

- [x] Add TDD coverage for overlay discovery/precedence and relocation planning.
- [x] Implement deterministic overlay manifest/provenance assembly.
- [x] Add accepted DG00 KSF override generation from committed metadata.
- [x] Implement generic nested ISO/CVM overlay builder with in-place and append-relocate modes.
- [x] Add local proprietary integration validation against the pristine PS2 ISO.
- [x] Verify the output remains fixed-size using existing outer ISO slack.

## Milestone B — structural MTX transfer

- [x] Add red tests for exact monotonic byte-block address mapping.
- [x] Implement structural address mapper and full-file fail-closed MTX importer.
- [x] Validate `DG/DG13_02.MTX` maps 577/577 official entries.
- [x] Survey all changed English-mapped MTX files and emit only 100%-proven files.
- [x] Write `local/structural-mtx` + `local/structural-import-report.json`.

## Milestone C — regression-preserving candidate

- [x] Assemble exact MTX + exact KSF + structural MTX + accepted overrides.
- [x] Regenerate early UI ELF directly from pristine `SLPM_665.11`.
- [x] Build a whole-game ISO from the pristine source.
- [x] Validate translated files from the finished ISO, outer tail integrity, save/serial identity, and historical accepted early slice.
- [x] Emit build manifest/report with counts/hashes.

## Milestone D — unresolved-format research

- [x] Probe FD00 template alignment and quantify safe matches (1/26 structural-compatible); leave the unresolved 25 fail-closed.
- [x] Research KSF overflow/reference structure; safe relocation remains unproven, so 48 overflows stay fail-closed.
- [x] Locate/inventory localized Unity AssetBundles; extraction path is proven, PS2 TMX encode/repack remains the blocker.

## Milestone E — repository publication and runtime gate

- [x] Run full test suite and clean-clone suite (82/82 local; 59 clean-copy with 7 expected proprietary-fixture skips).
- [x] Audit commit candidate for copyrighted/generated binaries; ignored game data remains outside Git.
- [x] Update `docs/HANDOFF.md`, `docs/DISCOVERY.md`, `docs/BUILD.md` and regression docs with actual results.
- [ ] Commit and push tooling/docs/tests to private GitHub.
- [ ] State the exact expected visual result of the generated test candidate and wait for Pablo's explicit approval before launching PCSX2.