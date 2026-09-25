# Regression policy

The project is cumulative: once a translation is accepted, later builds must not silently remove or mutate it.

## Committed accepted baseline

`translations/accepted.json` stores stable IDs, source/output hashes and provenance rather than copyrighted script content. It currently records the historical accepted DG00 MTX, constrained DG00 KSF, and the previously accepted early-UI ELF checkpoint.

v5, v6 and v7 were runtime-tested and failed the full startup acceptance scope. A later emulator log proved the next supervised session had actually booted v8; that run exposed the allocator-protected-but-still-stuck reading flow and the missing memory-card aliases. v10 is now the latest runtime-tested checkpoint: its startup/name flow advances into the first old-man scene, opening quote rotation works, and first-old-man DG00 content is English. v10 also exposes presentation defects that v11 must preserve as known failures until fixed: `New Game` / `Load Game` overrun the original backing, DG dialogue remains vertical, H.A.N.T. is partial/clipped, and menu labels are mixed awkward/unresolved. The structural 3+3 name behavior remains unchanged and out of scope.

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
- every one of the **1,144** overlay assets has a unique executable ROFS record that re-resolves to its final size/extent;
- startup graphics retain the exact pristine file size, differ from pristine content, and hash exactly to their local generated overlay;
- `tools/startup_acceptance.py` independently reopens the final ISO and checks title/name wide-pointer paths, Latin keyboard, the state-9 skip-reading instruction invariant, ADV horizontal renderer instructions, active translation PT_LOAD, H.A.N.T. relocated pointers/text, memory-card table + boot-handler aliases, 31 startup graphics + ROFS records, DG00 English/removal assertions and DG00 KSF choices.

Historical v6 (**96/96**) and v7 (**98/98**) final-image acceptance both preceded runtime failures; static acceptance is therefore necessary but not sufficient. v8 final-image acceptance is **120/120** (`local/startup-acceptance-v8.json`). v9 is **121/121** (`local/startup-acceptance-v9.json`) and adds a named GP088_12 packed-title chunk check. v10 is **123/123** (`local/startup-acceptance-v10.json`) and additionally verifies both memory-card boot aliases and the state-9 skip-reading instruction invariant; a second pristine v10 build is byte-for-byte identical. The later v10 runtime test promotes only the explicitly observed startup/name progression, quote rotation, correct title text, and English first-dialogue content. It does not convert unobserved static invariants into runtime proof, and it records the title/H.A.N.T./menu/vertical-dialogue defects as the v11 regression baseline.

## Save compatibility smoke test

Before runtime testing, back up the PCSX2 memory card. After the first successful in-game create/load test, keep a golden Kowloon test save and verify later builds can load it. Normal memory-card saves are the compatibility contract; savestates are disposable across builds.

The emulator launch still requires Pablo's explicit approval after the exact visible expectations for that candidate are stated.
