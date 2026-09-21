# Build and analysis workflow

## Local paths currently used on Pablo's Mac

- PS2 archive: `/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z`
- PS2 extracted ADV: `/private/tmp/khc-ps2-assets/ADV`
- PS4 package: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
- PS4 extracted ADV: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV`
- Pristine extracted PS2 ISO: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
- Current historical early test ISO: `/private/tmp/kowloon-recharge-early-en.iso`

These paths are convenience defaults only and are not committed configuration. Use `config/sources.example.json` as the portable reference.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

Local proprietary fixture tests skip cleanly in a clean clone.

## Regenerate source identity

```bash
python3 -m tools.source_manifest \
  --ps2-archive '/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z' \
  --ps2-iso '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  --ps2-adv '/private/tmp/khc-ps2-assets/ADV' \
  --ps4-pkg '/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg' \
  --ps4-adv '/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV' \
  --output local/source-manifest.json
```

## Regenerate corpus inventory

```bash
python3 -m tools.build_corpus_manifest \
  --ps2-adv '/private/tmp/khc-ps2-assets/ADV' \
  --ps4-adv '/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV' \
  --output local/corpus-manifest.json
```

This also writes the lexical-run estimate used to distinguish a large PS2-only file count from the much smaller amount of apparently novel Japanese text.

## Regenerate exact MTX tier

```bash
rm -rf local/exact-mtx
python3 -m tools.import_exact_mtx \
  --ps2-adv '/private/tmp/khc-ps2-assets/ADV' \
  --ps4-adv '/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV' \
  --output-root local/exact-mtx \
  --report local/exact-import-report.json
```

Current verified result: 962 files / 56,642 English entries imported; 23 files / 21,672 entries rejected fail-closed.

## Regenerate conservative exact KSF tier

```bash
rm -rf local/exact-ksf
python3 -m tools.import_exact_ksf \
  --ps2-adv '/private/tmp/khc-ps2-assets/ADV' \
  --ps4-adv '/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV' \
  --output-root local/exact-ksf \
  --report local/ksf-report.json
```

Current verified result: 868 fitting entries, 48 overflows left untouched, 4 ambiguous entries.

## Regression gate

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
```

That self-check proves schema/invariants for the committed baseline. Future build stages should emit a current accepted manifest and compare it against `translations/accepted.json`; additions are allowed, disappearance/mutation of accepted entries fails.

## Existing early vertical slice

The historical scripts generate local ignored artifacts:

- `artifacts/DG00_00.en-fullwidth.MTX`
- `artifacts/DG00_00.en-ascii-probe.KSF`
- `artifacts/SLPM_665.11.en-early`

and can rebuild the early test ISO with `tools/build_vertical_slice_iso.py`. The accepted hashes for those three artifacts are preserved in `translations/accepted.json`.

## Runtime testing

Do not start PCSX2 automatically. Before every new runtime test, describe exactly which title/menu/dialogue elements are expected to be English, which Japanese text is intentionally still present, and any rendering caveat. Wait for Pablo's explicit approval before launch.

## Whole-game deterministic candidate

The current generic builder is `tools/build_translation_iso.py`. Run repository CLIs as modules (`python3 -m tools.<name>`) so repository imports resolve consistently.

Current overlay precedence, low to high:

1. `local/exact-mtx`
2. `local/exact-ksf`
3. `local/structural-mtx`
4. `local/accepted-overrides`

Generate the reviewed DG00 override and ELF, then build:

```bash
python3 -m tools.accepted_overrides \
  --manifest translations/DG00_00.vertical-slice.json \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --exact-ksf-root local/exact-ksf \
  --output-root local/accepted-overrides

python3 -m tools.build_early_ui_elf

python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-whole-en-candidate.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/whole-build-report.json
```

Verified result for the current inputs:

- SHA-256 `8fc57b8b295a414e15ebb5d2d762114e3106282564f38ae30a7f63bc10a06362`
- 1,113 overlay files
- 860 in place / 253 relocated
- +900 embedded sectors
- 17 shifted outer-tail files, payload-identical after shift
- outer ISO size unchanged at 2,095,382,528 bytes

The builder is deliberately fail-closed on missing paths, insufficient outer slack, directory relocation, CVM/PVD disagreement, changed overlay input hashes, translated-output hash mismatch, shifted-tail payload drift, ELF size drift, and serial/save-identity loss.

### Graphics inventory

Graphics are not yet included in the candidate. The packed PS4 English art can be inventoried without making UnityPy a repository dependency:

```bash
uv run --with UnityPy python -m tools.graphics_inventory \
  --dictionary /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/AssetFileDic_en.txt \
  --bundle-root /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/BLBRD \
  --output local/graphics-inventory.json \
  --deep
```

Do not add graphics to a runtime build until the PS2 TMX encoder/container repacker has round-trip tests.
