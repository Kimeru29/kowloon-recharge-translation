# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Committed accepted baseline

`translations/accepted.json` stores stable IDs, source/output hashes and provenance rather than copyrighted script content. It currently records the historical accepted DG00 MTX, constrained DG00 KSF, and the previously accepted early-UI ELF checkpoint.

v5 was runtime-tested and failed the full startup acceptance scope, so it must not be promoted. The current v6 renderer-class/ELF changes are statically verified but **must not replace the committed accepted hash until the v6 runtime test passes**. Local candidate verification is additive evidence, not automatic promotion.

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

The generic builder validates the completed nested image, not only intermediate files. For startup v6 it verifies:

- outer ISO declared volume and total byte size remain unchanged;
- CVM header, outer `DATA.CVM` record and embedded PVD agree;
- every overlay payload in the finished ISO hashes to its generated overlay input;
- the 17 shifted outer-tail files remain byte-identical;
- `SLPM_665.11` may grow/relocate only through the tested builder path and retains `SLPM-66511` + `BISLPM-66511Save`;
- every one of the **1,143** overlay assets has a unique executable ROFS record that re-resolves to its final size/extent;
- startup graphics retain the exact pristine file size, differ from pristine content, and hash exactly to their local generated overlay;
- `tools/startup_acceptance.py` independently reopens the final ISO and checks title/name wide-pointer paths, Latin keyboard, ADV horizontal renderer instructions, active translation PT_LOAD, H.A.N.T. relocated pointers/text, 30 startup graphics + ROFS records, DG00 English/removal assertions and DG00 KSF choices.

Current v6 final-image acceptance: **96/96 checks passed** (`local/startup-acceptance-v6.json`).

## Save compatibility smoke test

Before runtime testing, back up the PCSX2 memory card. After the first successful in-game create/load test, keep a golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are disposable across builds.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that candidate are stated.
