# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Committed accepted baseline

`translations/accepted.json` stores stable IDs, source/output hashes and provenance rather than copyrighted script content. It currently records the historical accepted DG00 MTX, constrained DG00 KSF, and the previously accepted early-UI ELF checkpoint.

The current startup-v5 ELF has additional unreviewed-at-runtime startup patches and therefore **must not replace the committed accepted hash until the v5 runtime test passes**. Local candidate verification is additive evidence, not automatic promotion.

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

The generic builder validates the completed nested image, not only intermediate files. For startup v5 it verifies:

- outer ISO declared volume and total byte size remain unchanged;
- CVM header, outer `DATA.CVM` record and embedded PVD agree;
- every overlay payload in the finished ISO hashes to its generated overlay input;
- the 17 shifted outer-tail files remain byte-identical;
- `SLPM_665.11` stays fixed-size and retains `SLPM-66511` + `BISLPM-66511Save`;
- every one of the **1,143** overlay assets has a unique executable ROFS record that re-resolves to its final size/extent;
- startup graphics retain the exact pristine file size, differ from pristine content, and hash exactly to their local generated overlay;
- title pointers/arena, all declared startup string slots, the Latin keyboard, DG00 dialogue and DG00 interaction choices are independently asserted by `local/startup-acceptance-v5.json`.

Current v5 static acceptance: **114/114 checks passed**.

## Save compatibility smoke test

Before runtime testing, back up the PCSX2 memory card. After the first successful in-game create/load test, keep a golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are disposable across builds.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that candidate are stated.
