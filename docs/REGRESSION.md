# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Accepted baseline

`translations/accepted.json` is the committed baseline. It deliberately stores stable IDs, asset identities, source SHA-256 values, generated-output SHA-256 values and provenance rather than copying bulk game script text.

The initial baseline covers the three already accepted vertical-slice artifacts:

- translated `ADV/DG/DG00_00.MTX`;
- translated/constrained `ADV/DG/DG00_00.KSF`;
- early translated `SLPM_665.11` UI executable artifact.

## Gate semantics

A comparison reports `added`, `changed` and `removed` stable IDs.

- additions: allowed;
- existing-entry mutation: fail until an intentional baseline update is reviewed;
- removals: fail;
- source-preimage/hash drift: represented as an entry mutation and fails;
- serial drift from `SLPM-66511`: fail;
- save-directory drift from `BISLPM-66511Save`: fail;
- duplicate stable IDs: fail.

The core implementation is `tools/regression.py`; CLI entry point is `tools/check_regression.py`.

Current baseline self-check:

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
```

Expected output contains empty `added`, `changed` and `removed` arrays.

Future multi-file build stages should emit a generated current manifest and compare it to the committed baseline before producing/releasing a test ISO. Accepted new artifacts are promoted into the baseline only after validation.

## Save compatibility smoke test

Before runtime testing, preserve a backup of the PCSX2 memory card. After the first successful in-game create-save/load-save validation, keep one golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are considered build-specific.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that build are stated.

## Whole-game candidate gate

The generic builder now validates the finished ISO, not only intermediate overlay files. For the current candidate it verifies:

- source/output total size relationship and unchanged outer declared volume;
- CVM header, outer `DATA.CVM` record, and embedded PVD sector counts agree;
- all 1,113 translated ADV files in the finished ISO hash exactly to their overlay manifest values;
- 17 shifted outer-tail files remain byte-identical;
- translated `SLPM_665.11` is fixed-size and contains `SLPM-66511` + `BISLPM-66511Save`;
- every overlay asset has exactly one pristine-matching executable ROFS record; final ROFS size/extent must resolve to the same translated payload as ISO9660;
- the early UI artifact is the base executable input; final whole-game ELF hash is expected to differ because ROFS metadata is deterministically patched on top.

The `SLPM_665.11` accepted-baseline hash was intentionally migrated after the failed v1 runtime test: single-byte title ASCII was replaced by two-byte PS2 glyph encoding. This is a reviewed bug-fix mutation, not silent regression.

Current ignored evidence is `local/whole-build-report-v2.json`; v1 reports remain diagnostic history only. A new accepted artifact must still be added through the committed regression manifest rather than relying only on a local report.
