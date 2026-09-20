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
