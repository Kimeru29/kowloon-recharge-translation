# Build and analysis workflow

## Local paths currently used on Pablo's Mac

- PS2 archive: `/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z`
- pristine PS2 ISO: `/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso`
- PS2 ADV: `/private/tmp/khc-ps2-assets/ADV`
- CVM payload ISO: `/private/tmp/kowloon-recharge-inspect/DATA_payload.iso`
- PS4 PKG: `/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg`
- PS4 extracted root: `/private/tmp/khc-ps4-extracted/CUSA27034`
- PS4 ADV: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV`
- PS4 BLBRD bundle root: `/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/BLBRD`

These are local convenience paths, not committed source data.

## Tests

Dependency-free suite:

```bash
python3 -m unittest discover -s tests -v
```

Full graphics suite:

```bash
uv run --with pillow python -m unittest discover -s tests -v
```

Current result after the v7 name-entry regression work: 122 tests; the optional-Pillow run passes all 122.

## Core corpus regeneration

Source identity:

```bash
python3 -m tools.source_manifest \
  --ps2-archive '/Volumes/TerraMas MAC A/Roms/PS2/Kowloon Youma Gakuenki re-charge (Japan).7z' \
  --ps2-iso '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  --ps2-adv '/private/tmp/khc-ps2-assets/ADV' \
  --ps4-pkg '/Volumes/TerraMas MAC A/Roms/PS2/khc.pkg' \
  --ps4-adv '/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV' \
  --output local/source-manifest.json
```

Corpus inventory:

```bash
python3 -m tools.build_corpus_manifest \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output local/corpus-manifest.json
```

Exact MTX:

```bash
rm -rf local/exact-mtx
python3 -m tools.import_exact_mtx \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output-root local/exact-mtx \
  --report local/exact-import-report.json
```

Exact KSF:

```bash
rm -rf local/exact-ksf
python3 -m tools.import_exact_ksf \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --ps4-adv /private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV \
  --output-root local/exact-ksf \
  --report local/ksf-report.json
```

Reviewed DG00 KSF override:

```bash
python3 -m tools.accepted_overrides \
  --manifest translations/DG00_00.vertical-slice.json \
  --ps2-adv /private/tmp/khc-ps2-assets/ADV \
  --exact-ksf-root local/exact-ksf \
  --output-root local/accepted-overrides
```

Regenerate executable UI:

```bash
python3 -m tools.build_early_ui_elf
```

## Rebuild startup graphics

Generated graphics are local-only and ignored by Git.

### 1. Extract official English Texture2D PNGs

Use UnityPy only as an ephemeral dependency:

```bash
uv run --with UnityPy --with pillow python - <<'PY'
from pathlib import Path
import UnityPy

root = Path('/private/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/BLBRD')
for bundle_name, output in (
    ('tr_en', Path('/private/tmp/tr_en_textures')),
    ('b_gp019_en', Path('/private/tmp/gp019_en')),
):
    output.mkdir(parents=True, exist_ok=True)
    env = UnityPy.load(str(root / bundle_name))
    for obj in env.objects:
        if obj.type.name != 'Texture2D':
            continue
        texture = obj.read()
        texture.image.save(output / f'{texture.m_Name}.png')
PY
```

Expected source sets:

- `/private/tmp/tr_en_textures/TR000.png` through `TR028.png` — 29 quote images;
- `/private/tmp/gp019_en/GP019_00.png`, `GP019_01.png` — name-entry graphics.

### 2. Port them into PS2 indexed assets

```bash
rm -rf local/startup-graphics/BLBRD/INIT_MES
uv run --with pillow python - <<'PY'
from pathlib import Path
import mmap
from tools.iso9660_patch import index_iso, find_record, SECTOR_SIZE
from tools.startup_graphics import port_name_entry_graphics, port_quote_graphic

payload = Path('/private/tmp/kowloon-recharge-inspect/DATA_payload.iso')
out = Path('local/startup-graphics')
quotes = Path('/private/tmp/tr_en_textures')
name_pngs = Path('/private/tmp/gp019_en')

with payload.open('rb') as handle:
    image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
    try:
        _, records = index_iso(image)
        for i in range(29):
            filename = f'TR{i:03d}.TMX'
            rel = f'BLBRD/INIT_MES/{filename}'
            record = find_record(records, rel)
            raw = bytes(image[record.extent * SECTOR_SIZE:record.extent * SECTOR_SIZE + record.size])
            localized = port_quote_graphic(raw, quotes / f'TR{i:03d}.png', name=filename)
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(localized)

        record = find_record(records, 'BLBRD/B_GP019.BIN')
        raw = bytes(image[record.extent * SECTOR_SIZE:record.extent * SECTOR_SIZE + record.size])
        localized = port_name_entry_graphics(raw, name_pngs)
        target = out / 'BLBRD/B_GP019.BIN'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(localized)
    finally:
        image.close()
PY
```

All 30 outputs must keep the pristine file size. Quote fidelity evidence is stored locally in `local/startup-quotes-report.json`; current maximum mean absolute RGBA error is 0.5594/255.

## Build startup v5 candidate

Overlay precedence, low to high:

1. `local/exact-mtx`
2. `local/exact-ksf`
3. `local/structural-mtx`
4. `local/accepted-overrides`
5. `local/startup-graphics`

Build only from the pristine ISO:

```bash
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v5.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v5.json
```

Current static build result:

- SHA-256: `f8d65c029f86ce871f9d9930f76d12b6f6a95c79c4152a0437b19ceef1fd20b5`
- 1,143 overlay files
- 890 in place / 253 relocated
- 1,143 executable ROFS records patched and re-resolved
- +900 embedded sectors
- 17 outer-tail files shifted with byte-identical payloads
- outer ISO size unchanged: 2,095,382,528 bytes
- startup acceptance report: `local/startup-acceptance-v5.json`, 114/114 checks

The builder fails closed on missing/duplicate ROFS records, pristine metadata mismatch, unsupported overlay paths, insufficient outer slack, CVM/PVD disagreement, overlay hash drift, final-payload mismatch, shifted-tail drift, ELF size drift, and serial/save-identity loss.

## Regression baseline

```bash
python3 -m tools.check_regression translations/accepted.json translations/accepted.json
```

Do not promote the current startup ELF/graphics to the committed accepted baseline merely because static checks pass. Promote after the relevant runtime acceptance test succeeds.

## Runtime testing

Do not start PCSX2 automatically. Before each build launch, state exactly what Pablo should see and wait for explicit approval. For v5 the acceptance scope is every text-bearing screen from the opening quotation through the first old-man dialogue; any Japanese text in that interval is a failure to capture and investigate.


## Build startup v6 candidate

v6 keeps the v5 overlay set but rebuilds `artifacts/SLPM_665.11.en-early` with the generalized renderer classes: wide name/profile relocation, ADV horizontal layout, and the executable translation PT_LOAD used by H.A.N.T. long text.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v6.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v6.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v6.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v6.json
```

Current v6 result:

- ISO SHA-256: `beaaa53bbfe3a60cd3af6749d4113cd4d91e81d804b122f80b85c347bded761b`;
- 1,143 overlay files; 890 in place / 253 relocated;
- translated ELF size 8,401,977 bytes; it still fits the original outer sector allocation;
- final post-ROFS ELF SHA-256: `2dacea600e06c4db29311402ae5a1ae0880be23bfab2cfb3e8b0e1a811831922`;
- final-image startup verifier: **96/96**;
- Pillow-enabled tests: **121/121**.

v6 was later runtime-tested after explicit approval and failed during name entry; see `docs/LOCALIZATION_STATUS.md`. Do not reuse it as the current runtime candidate.


## Build startup v7 candidate

v7 is the successor to the runtime-tested v6 build. It restores the two active official reading prompts through the shared executable translation PT_LOAD and folds uppercase Latin characters into the seven keyboard rows that the PS2 `m_name` routine can actually index. It deliberately does **not** change the structural two-3-glyph permanent-name layout.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v7.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v7.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v7.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v7.json
```

Current v7 static result:

- ISO SHA-256: `f43e2e6bf92dd48c09a43093748d2dea112e361e7c3ca33ed540770c1d6d56ed`;
- 1,143 overlay files; 890 in place / 253 relocated;
- translated/final ELF size: 8,402,095 bytes; outer ELF extent remains 288;
- final post-ROFS ELF SHA-256: `b4b21905f920f8fb6472c198088d990f631f9d6f0ab02d3e66d05c86c3fb4432`;
- +900 embedded sectors; 17 shifted outer files;
- whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **98/98**;
- Pillow-enabled tests: **122/122**.

Do not launch v7 automatically. Follow the exact runtime checklist in `docs/LOCALIZATION_STATUS.md` and wait for Pablo's explicit approval before launching PCSX2.
