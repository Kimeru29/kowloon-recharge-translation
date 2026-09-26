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

Current v11-r5 result: 191 tests; the dependency-free run passes with 8 expected skips, and the optional-Pillow run passes with 1 owned-corpus skip.

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

## Build startup v8 candidate

v8 is the successor to the runtime-tested v7 build. It fixes the translation-PT_LOAD/runtime-heap collision, relocates the proven memory-card executable-text subset to official English, and adds the direct same-layout `B_GP088/GP088_03` English texture. The structural 3+3 name buffers and PS2-specific `GP088_12/13` packed title atlas remain unchanged.

Before the ISO build, regenerate the direct GP088 overlay from the owned PS4 localized PNG extraction:

```bash
uv run --with pillow python - <<'PY'
from pathlib import Path
import mmap
from tools.iso9660_patch import index_iso, find_record, SECTOR_SIZE
from tools.startup_graphics import port_title_startup_graphics

payload = Path('/private/tmp/kowloon-recharge-inspect/DATA_payload.iso')
target = Path('local/startup-graphics/BLBRD/B_GP088.BIN')
pngs = Path('/private/tmp/khc-ps4-en-textures/b_gp088_en')
with payload.open('rb') as handle:
    image = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
    try:
        _, records = index_iso(image)
        record = find_record(records, 'BLBRD/B_GP088.BIN')
        raw = bytes(image[record.extent * SECTOR_SIZE:record.extent * SECTOR_SIZE + record.size])
        localized = port_title_startup_graphics(raw, pngs)
    finally:
        image.close()
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(localized)
PY
```

Build and verify only from the pristine ISO:

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v8.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v8.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v8.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v8.json
```

Current v8 static result:

- ISO SHA-256: `7431f7f44eb9ed14927f2181491b02217efe8675c64c4c07789d13ad934aa550`;
- 1,144 overlay files; 891 in place / 253 relocated;
- translated ELF size: 8,403,943 bytes;
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`;
- the translated executable outgrew its original outer allocation and was relocated by the tested builder from extent 288 to 1,013,782;
- 1,144 executable ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files;
- whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **120/120**;
- dependency-free suite: **126 tests OK** (6 expected skips);
- Pillow-enabled suite: **126 tests OK** (1 owned-corpus skip).

Do not launch v8 automatically. Follow the exact runtime checklist in `docs/LOCALIZATION_STATUS.md` and wait for Pablo's explicit approval before launching PCSX2.


## Build startup v9 candidate

v9 superseded v8 as the static candidate by adding a proven structural GP088_12 atlas repack. A later emulator log showed the supervised runtime session had in fact booted v8, so v8/v9 executable findings are tracked separately from the v9-only atlas change. Regenerate `local/startup-graphics/BLBRD/B_GP088.BIN` with the same `port_title_startup_graphics` command above; the function now validates the pristine GP088_03→GP088_12 alpha layout and rebuilds GP088_12 from official-English GP088_03 regions.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v9.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v9.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v9.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v9.json
```

Current v9 static result:

- ISO SHA-256: `6770862cbde8edf301afdef7778d440c0d2eab99806d732724afc6ef5a279d76`;
- final post-ROFS ELF SHA-256: `5c1cee88e6cb9c2aaf4710a928ce24fb013beb3a56f3fd98b94654ef1f507fdd`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 ROFS records patched;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **121/121**;
- dependency-free suite: **130 tests OK** (8 expected skips);
- Pillow-enabled suite: **130 tests OK** (1 owned-corpus skip).

Do not launch v9 automatically. Follow the exact runtime checklist in `docs/LOCALIZATION_STATUS.md` and wait for Pablo's explicit approval before launching PCSX2.


## Build startup v10 candidate

v10 keeps the v9 graphics/corpus overlay set and changes only executable runtime routing: memory-card entry 1 now moves its two boot-handler aliases with the canonical pointer, and the English name flow reuses the existing post-reading transition instead of entering the PS2 kana-reading editor. Both patches validate exact pristine preimages.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v10.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v10.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v10.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v10.json
```

Current v10 static result:

- pristine ISO SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`;
- translated ELF SHA-256 before ISO ROFS rewrite: `ef1db436e6ef9c5b314cdb1c580b75c94cb2981025dc9788287810cd09c5a6ea`;
- final post-ROFS ELF SHA-256: `e276442dc435034c59d471f6aad4b1eab7c0a4679f68717d4a3a5a3808b345a0`;
- translated/final ELF size: 8,403,943 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `24d425433af97b1617e820cac05aa2a4d9389aa9fa19c1767a57eb763812da8e`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **123/123**;
- dependency-free suite: **134 tests OK** (8 expected skips);
- Pillow-enabled suite: **134 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v10-repeat.iso` has the same SHA-256 and `cmp` reports byte-for-byte identity.

Do not launch v10 automatically. Follow the exact v10 runtime checklist in `docs/LOCALIZATION_STATUS.md` and wait for Pablo's explicit approval before launching PCSX2.


## Build startup v11 candidate

v11 is the renderer/layout pass built on the runtime-tested v10 flow. It keeps the same overlay corpus and fixes the four presentation classes isolated by v10: title backing geometry, the live ADV/DG coordinate owner, H.A.N.T. wrapping/controller metadata, and semantic command-menu ownership. The build remains fail-closed and is produced only from the pristine ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11.json
```

Measured v11 static result:

- translated ELF SHA-256 before ISO ROFS rewrite: `edfca4471122c3f05c35c23a0d8c728ff45cc207b021ea2efca8af02c7003fac`;
- final post-ROFS ELF SHA-256: `9771bd9c031d7bcdb5e716c458d059feac6bdb2e31dd2fca6f4de7ca7f38e088`;
- translated/final ELF size: 8,403,944 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `4150414b817fe54cf90ac28887568a37c6910995d7f8bc46e6887a6c4f6ef516`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **130/130**;
- dependency-free suite: **177 tests OK** (8 expected skips);
- Pillow-enabled suite: **177 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-repeat.iso` has the same SHA-256 and `cmp` reports byte-for-byte identity.

Do not launch v11 automatically. The exact supervised runtime checklist is in `docs/LOCALIZATION_STATUS.md`; PCSX2 remains blocked until Pablo explicitly approves that launch.

## Build startup v11-r4 candidate

v11-r4 is the historical four-defect correction pass after the supervised v11 presentation failure and the unproven r3 experiment. It preserves the accepted title/tablet geometry and does **not** include the r3 memory-card wrapping experiment. The only new runtime-facing owners are the license-completion X origin, the upstream DG all-canvas orientation flag, the mode-4 H.A.N.T. tutorial font/reflow, and the seven pointer-owned H.A.N.T. chrome labels.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r4.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r4.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r4.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r4.json
```

Measured v11-r4 static/deterministic result:

- translated ELF SHA-256 before ISO ROFS rewrite: `4501cee41d3941d40c687f9806b51aa0196f6c206132fd6614f3bbe8ee461a43`;
- final post-ROFS ELF SHA-256: `54690aed73a68d19e8b1fcd787e346086fbd3bb30dd9dea9b39b99acf93d3d9f`;
- translated/final ELF size: 8,404,046 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `3566b2395165cf4ba4b34ebed874ba405f17c0d452753786cfc116ed80c494bb`;
- 1,144 overlays; 891 in place / 253 relocated; 1,144 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **132/132**;
- dependency-free suite: **182 tests OK** (8 expected skips);
- Pillow-enabled suite: **182 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r4-repeat.iso` has the same builder SHA-256 and `cmp` reports byte-for-byte identity.

Do not launch r4 automatically. PCSX2 has not been launched for this candidate. The supervised target-screen checklist is recorded in `docs/LOCALIZATION_STATUS.md`.


## Build startup v11-r5 candidate

v11-r5 is the current correction pass after Pablo's r4 screenshot review. It preserves the accepted title/tablet geometry and adds only the remaining runtime-facing owners: the separate speaker-name orientation, the H.A.N.T. 18px row stride and 15-entry Help topic table, the two-line memory-card boot message, and the baked GP020 caption atlas. GP020 wording/art is semantic because the current owned PS4 extraction does not expose a localized GP020 bundle.

The generated local `BLBRD/B_GP020.BIN` is a same-size transform of pristine `GRP020/GP020_03.TMX`. Its nine caption rectangles are pinned by SHA-256 preimages and only the existing H.A.N.T.-green indexed pixels inside those rectangles may change.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r5.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r5.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r5.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r5.json
```

Measured v11-r5 static/deterministic result:

- translated ELF SHA-256 before ISO ROFS rewrite: `6e385c38fd012d8d11a5e3f0f20220412506ed6aa43b75b8bd712035365a28fa`;
- final post-ROFS ELF SHA-256: `c3b228c946df9bae9d8aec81058a04801de1483191c28d5077087e1d9c2d3eee`;
- translated/final ELF size: 8,404,478 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `2ebee6fb45125fdfd826f15cb0a9eee09a66a861f39058103704a00244deb739`;
- 1,145 overlays; 892 in place / 253 relocated; 1,145 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **137/137**;
- dependency-free suite: **191 tests OK** (8 expected skips);
- Pillow-enabled suite: **191 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r5-repeat.iso` is byte-for-byte identical by `cmp`.

Do not launch r5 automatically. Pablo will perform the runtime checks manually.
