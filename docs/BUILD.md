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

Current v11-r20 result: 220 tests; the dependency-free run passes with 10 expected skips, and the optional-Pillow run passes with 1 owned-corpus skip.

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

v11-r5 was the correction pass after Pablo's r4 screenshot review. It added the then-assumed separate speaker-name orientation, the H.A.N.T. 18px row stride and 15-entry Help topic table, the two-line memory-card boot message, and the baked GP020 caption atlas. Pablo later runtime-tested r5; its results now serve as the preservation/failure baseline for r6. GP020 wording/art is semantic because the current owned PS4 extraction does not expose a localized GP020 bundle.

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

r5 was subsequently runtime-tested manually by Pablo. Preserve its runtime-good GP020 top-level tile artwork and 12px/18px H.A.N.T. tutorial presentation; see `docs/LOCALIZATION_STATUS.md` for the failures that motivated r6.

## Build startup v11-r6 candidate

v11-r6 keeps the r5 graphics/corpus overlays and stone-tablet line split. It changes only evidence-backed executable owners: the true bracket-derived inline speaker text mode, the title label anchors while restoring pristine packed-title scaling, all three Help category/topic owner tables, and the nine-entry Config label table.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r6.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r6.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r6.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r6.json
```

Measured v11-r6 static/deterministic result:

- pristine ISO SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`;
- translated ELF SHA-256 before ISO ROFS rewrite: `06b76b01e9ef1364f5c67473edaf1b68b367512ba0af7dd1ad533f726b64ecfa`;
- final post-ROFS ELF SHA-256: `0fe52d198679c9c2eb4784cab12a554f4569488af018fd9778c3b72ca031b0eb`;
- translated/final ELF size: 8,405,736 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `dbd25ff8ada4724d6c280a32199dd3ef7fc49442923d904db56359ed02ef32a4`;
- 1,145 overlays; 892 in place / 253 relocated; 1,145 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **139/139**;
- dependency-free suite: **198 tests OK** (8 expected skips);
- Pillow-enabled suite: **198 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r6-repeat.iso` has the same SHA-256 and is byte-for-byte identical by `cmp`.

Do not launch r6 automatically. Pablo is the runtime tester; the exact r6 visual gate is in `docs/LOCALIZATION_STATUS.md`.

## Build startup v11-r7 candidate

v11-r7 is the runtime-driven follow-up to Pablo's r6 screenshots. It preserves r6's translated corpus, Help/Config ownership work and title-anchor recentering, then changes only traced presentation owners: the generic speaker orientation and header geometry, DG body fragment stride, name/license prompt X geometry, tablet line padding, the page-local H.A.N.T. row stride, and one compact Help category label. It deliberately does **not** guess at the remaining title black-backing atlas subregion.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r7.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r7.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r7.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r7.json
```

Measured v11-r7 static/deterministic result:

- pristine ISO SHA-256: `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`;
- translated ELF SHA-256 before ISO ROFS rewrite: `318f666a1c7cb990ec2cec91be32513c9abd8ddb16f5da4ffe186cb3976cdf7e`;
- final post-ROFS ELF SHA-256: `e520a919dd7e2a69c148f4cbe317b8f3ef2d729faa6f36e529a6b536b929b4bc`;
- translated/final ELF size: 8,405,744 bytes; outer extent relocated from 288 to 1,013,782;
- ISO SHA-256: `2b64165f820ec208ff9d721b9fbf30d8ee17bb78b9556e7ebe540c83b27221b4`;
- 1,145 overlays; 892 in place / 253 relocated; 1,145 ROFS records patched/re-resolved;
- +900 embedded sectors; 17 shifted outer files; whole ISO remains 2,095,382,528 bytes;
- final-image startup verifier: **140/140**;
- dependency-free suite: **199 tests OK** (8 expected skips);
- Pillow-enabled suite: **199 tests OK** (1 owned-corpus skip);
- deterministic rebuild: `/private/tmp/kowloon-recharge-startup-en-v11-r7-repeat.iso` has the same SHA-256 and is byte-for-byte identical by `cmp`.

Do not launch r7 automatically. Pablo is the runtime tester; the exact r7 visual gate is in `docs/LOCALIZATION_STATUS.md`.

## Build startup v11-r8 candidate

r8 is a presentation-only follow-up to Pablo's runtime-tested r7. It changes only three proven owners: ADV vertical dialogue geometry, boot-tablet line padding, and the `GP088_08` lower title-label backing. Name/license centering, H.A.N.T., title text anchors, `GP088_03`, and packed `GP088_12` are preservation constraints.

For the title overlay, r8 applies the fail-closed `GP088_08` backing transformation to the verified r7 localized `B_GP088.BIN`; this changes only that TMX chunk and preserves the r7 title art path.

Measured r8 result:
- ISO SHA-256: `c2905f8bf1ebe20defb5479591c0dbf86b2e9bfbf9c6062db37ccf6f8ba6593f`;
- pre-ROFS ELF: `62d68ec47255d37eb372f75d074815159b352367096e488247d699ed54043200`;
- post-ROFS ELF: `d19d03a728aba3fff0102b076cc53d045e3329de7b421b4ef4c8ec54a5eb5712`;
- 140/140 final-image checks;
- 201 tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip);
- repeat ISO byte-for-byte identical.

Do not launch PCSX2 automatically. Pablo is the runtime tester.

## Build startup v11-r9 candidate

r9 is the runtime-polish follow-up to r8. Preserve the r8 tablet and speaker/name geometry. Regenerate the GP088 overlay with the current `port_title_startup_graphics` transform (300px lower backing), rebuild the early-UI ELF, then build from the pristine PS2 ISO exactly as previous candidates.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r9.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r9.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r9.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r9.json
```

Measured r9 result:
- ISO SHA-256: `0abe223df878c181da784247fe112553abe030a4f7db240f972285b5aa7696d0`;
- pre-ROFS ELF: `06e364c79be9db69a6b0490d0a2368725ea29d29753aa68e5cd5370a812bf2ca`;
- post-ROFS ELF: `61520a390a50de641096514fe219062f7059a382b3e1a6b9cc231ba4069c3ee6`;
- 1,145 overlays; 892 in place / 253 relocated;
- 140/140 final-image checks;
- 201 tests in both suites (10 dependency-free skips / 1 Pillow-owned-corpus skip);
- repeat ISO byte-for-byte identical.

Do not launch PCSX2 automatically. The r9 runtime gate is documented in `docs/LOCALIZATION_STATUS.md`.

## Build startup v11-r10 candidate

r10 preserves the r9 startup-graphics overlay and changes executable-owned presentation only: calculated 160px title backing primitives, English Yes-focus child ownership, and the corrected dialogue body base/row-stride formula. Build from the pristine PS2 ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r10.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r10.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r10.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r10.json
```

Measured r10 result:
- ISO SHA-256: `a4f629fb22b2b095fe374eab384d86365ff881038fc37d4fa1e590297d5f928d`;
- pre-ROFS ELF: `711ddca9d7813efaf34fc9788407fd0245a198b3ac8d08e925b851051c7b30c5`;
- post-ROFS ELF: `76f335855ce03615f216cff575dfa63ff978b46660b7380d5954825499425a10`;
- 1,145 overlays; 892 in place / 253 relocated;
- 141/141 final-image checks;
- 205 dependency-free tests (10 expected skips);
- 205 Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO byte-for-byte identical.

r10 was later runtime-tested; its accepted confirmation-focus fix and two disproven owner hypotheses are recorded in `docs/LOCALIZATION_STATUS.md`.

## Build startup v11-r11 candidate

r11 preserves every r10-accepted surface and replaces only the two runtime-disproven presentation owners: title backing resource metadata/positions and the primary ADV body-canvas geometry. Build from the pristine PS2 ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r11.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r11.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r11.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r11.json
```

Measured r11 result:
- ISO SHA-256: `c99f43b6f4047f63d3b0f4fd228fb893556933d3c1a65cb46e112ba6395325de`;
- pre-ROFS ELF: `2776fe5598074dea7f72faf941130e4fe623d9bc11c79bd6a3bc862df95d6646`;
- post-ROFS ELF: `5db2a259210ccb0ad8ca68047b5102c9b52301ba4d99c18af75fa7e7b130382c`;
- 1,145 overlays; 892 in place / 253 relocated;
- 141/141 final-image checks;
- 205 dependency-free tests (10 expected skips);
- 205 Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO byte-for-byte identical.

r11 was later manually runtime-tested by Pablo. Its title/backing and ADV corrections are accepted, along with preservation of the tablet, quotations, and visible profile/name surfaces. That pass also proves the H.A.N.T. Help topic-label tables do not own the selected topic body pages; see `docs/LOCALIZATION_STATUS.md`.

## Build startup v11-r12 candidate

r12 preserves every accepted r11 presentation surface and expands only one separately proven H.A.N.T. selected Help body: `HELP → OTHERS → About the Shop` `(mode=4, category=2, topic=5)`. Build only from the pristine PS2 ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r12.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r12.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r12.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r12.json
```

Measured r12 result:
- ISO SHA-256: `ef65129b13b9b49a705a03bc8d83d434a16c76915d5024da597ba1f559f96916`;
- pre-ROFS ELF: `3faa98a1585bc0d55ffb41a5dfbc6cbf8ae3cb0c03742dc7214fcd5f5e21407a`;
- post-ROFS ELF: `3844b03e7fc5bc0d9464a3e9d9d256b0c7b6783c1aa90ff09afd32d83e3cf8f0`;
- translated/final ELF size: 8,405,990 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- 142/142 final-image checks, including the new separate `hant_help_bodies` gate;
- 208 dependency-free tests (10 expected skips);
- 208 Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r12-repeat.iso` is byte-for-byte identical and has the same SHA-256.

The promoted page has a seven-row source table and an empty metadata list, so r12 does not alter controller/icon geometry. Its Japanese source table and metadata remain byte-identical and only the proven text descriptor is redirected to the shared translation PT_LOAD. The wording is explicitly `semantic` because the owned extraction still lacks `English.bytes`. `Command Thumbnails` and other unpromoted Help bodies intentionally remain Japanese.

Do not launch PCSX2 automatically. The exact r12 visual gate is documented in `docs/LOCALIZATION_STATUS.md` and `docs/HANDOFF.md`.

## Build startup v11-r13 candidate

r13 preserves every runtime-accepted pre-H.A.N.T. surface and the H.A.N.T. main/chrome/navigation presentation from r12, then expands only the H.A.N.T. content owners proven Japanese by the r12 screenshots. Build only from the pristine PS2 ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r13.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r13.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r13.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r13.json
```

Measured r13 result:
- ISO SHA-256: `53bf85f051ff3f3c8714e41be134dbd5fa9fcd0fd4ba2e3bd58091bf2acc1648`;
- pre-ROFS ELF: `a0b9b3fcb83c6579d5d2f93ab74749636d62fd0cb7aae7f8b0bd5a365d15b2bf`;
- post-ROFS ELF: `062d0380ba7f8ee094ac4230799ffee5a4f1029b7230734bca2caafd9d4b6b6f`;
- final ELF size: 8,414,614 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- **146/146** final-image checks;
- **212** dependency-free tests (10 expected skips);
- **212** Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r13-repeat.iso` is byte-for-byte identical and has the same SHA-256.

r13 translates the three runtime-observed Japanese Help bodies while keeping all source metadata/icon records intact, plus Mail empty state, Config values/ringtones, Enemy category tabs, Dictionary index tabs and 208 selectable Dictionary terms. The wording is semantic because `English.bytes` remains unavailable. Dictionary definition pages are intentionally outside this build's acceptance claim.

Do not launch PCSX2 automatically. The exact r13 visual gate is documented in `docs/LOCALIZATION_STATUS.md` and `docs/HANDOFF.md`.


## Build startup v11-r14 candidate

r14 is the runtime-layout and selected-Dictionary-definition follow-up to r13. Build only from the pristine PS2 ISO.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r14.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r14.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r14.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r14.json
```

Measured r14 result:
- ISO SHA-256: `2d543df1367dea4b9b9b31d77cf246d959f2e5c0b23a8726e6b001be611ce795`;
- pre-ROFS ELF: `29be2791d014be9730d5d8107d8d3c4990132bf3fd6d25c227fc6a97b768c08a`;
- post-ROFS ELF: `36ac6bfa4e0b995bc94163e728eaa5787110d17f250777c52ccf602830676041`;
- final ELF size: 8,416,234 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- **150/150** final-image checks;
- **214** dependency-free tests (10 expected skips);
- **214** Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r14-repeat.iso` is byte-for-byte identical and has the same SHA-256.

r14 preserves all accepted pre-H.A.N.T. behavior and r13 text ownership while correcting the runtime-observed H.A.N.T. presentation: translated Help icon metadata follows English geometry, Config/Dictionary/Enemy render with proven English style/spacing, Mail chrome/empty-state positioning is corrected, and the two observed Dictionary definition leaves are translated fail-closed.

Do not launch PCSX2 automatically. The exact r14 visual gate is documented in `docs/LOCALIZATION_STATUS.md` and `docs/HANDOFF.md`.


## Build startup v11-r15 H.A.N.T Functions recovery candidate

r15 is built from the same pristine PS2 ISO and overlay set as r14. It restores the runtime-disproven H.A.N.T singleton constructor at `0x190A40` to pristine and reserves a two-cell gutter around the Exploration warning icon.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r15.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r15.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r15.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r15.json
```

Measured r15 result:
- ISO SHA-256: `e4cf331c90470e99c2c0db1728673a7ddcdab358182f8d1ba7927b6dbbf387f6`;
- pre-ROFS ELF: `dcdd2f0c4a22bb74f280ec285fc43a061dd475c07ce10a00e31498849a274f86`;
- post-ROFS ELF: `306cfa21e720328c269c505995c5041b0d4b77496329ecbf22bdf14b5eef1a68`;
- final ELF size: 8,416,238 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- **150/150** final-image checks;
- **215** dependency-free tests (10 expected skips);
- **215** Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r15-repeat.iso` is byte-for-byte identical and has the same SHA-256.

Do not launch PCSX2 automatically. r15's first runtime gate is H.A.N.T Functions body/exit-state recovery plus the Exploration warning-icon gutter; Moving in Ruins and all pre-H.A.N.T. accepted presentation remain frozen.


## Build startup v11-r16 H.A.N.T. completion/presentation candidate

r16 is built from the same pristine PS2 ISO and overlay set as r15. It preserves the r15-good H.A.N.T Functions/ADV/Moving/Config paths, refines the remaining Mail/Dictionary/Enemy/Exploration layout owners, and adds generated official English tables for all 208 selectable Dictionary definitions from the recovered owned-remaster `English.bytes`.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r16.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r16.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r16.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r16.json
```

Measured r16 result:
- ISO SHA-256: `7669e50ddd81778e48e15c1f85f8ac4ff56a7d9e4e6c330c58ab9ae3b7bd8b9b`;
- pre-ROFS ELF: `f8c90885dfd9050570fd5b70db6fbf5b890915e6469128996ab89cfa7ac86106`;
- post-ROFS ELF: `bb4bcb3640616cb33de351b3735cfacb25376e7e4e56601113956e8dc85df752`;
- final ELF size: 8,563,534 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- **150/150** final-image checks;
- **217** dependency-free tests (10 expected skips);
- **217** Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r16-repeat.iso` is byte-for-byte identical and has the same SHA-256.

Do not launch PCSX2 automatically. r16's manual gate is the remaining r15 review: Exploration warning-icon spacing, Mail alignment/centering, Dictionary tabs/empty state plus representative opened definitions, and Enemy category/L1-R1 separation. Reconfirm Moving in Ruins, H.A.N.T Functions, ADV Controls and Config remain unchanged.


## Build startup v11-r17 Dictionary/Enemy presentation candidate

r17 uses the same pristine PS2 ISO and overlay set as r16. It changes only Dictionary tab/detail geometry, deterministic definition reflow, and Enemy category X geometry.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r17.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r17.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r17.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r17.json
```

Measured r17 result:
- ISO SHA-256: `728f9eae1d7dd2f69009732ff8c880585db1c6cde41d120358e04362428276dc`;
- pre-ROFS ELF: `68ab06d3b2b51dbcdc8853944c04eadd0c165009afed488dfe158a167e0ca6f2`;
- post-ROFS ELF: `ee24bb03984c7be760f398f01128faa65c02925552283c0ac9a6bc48dfd125a0`;
- final ELF size: 8,562,126 bytes;
- **150/150** final-image checks;
- **218** dependency-free tests (10 expected skips);
- **218** Pillow-enabled tests (1 owned-corpus skip);
- repeat ISO is byte-for-byte identical.

Do not launch PCSX2 automatically. Runtime checklist: Dictionary root tabs centered between L1/R1; Cairo/H.A.N.T/Heracleion/Rosetta Society title+icon clear of `【Dictionary】`; no body-internal blank-row sentence splits; Enemy `Small / Large / Human` centered/regularly spaced. Everything else should remain unchanged.


## Build startup v11-r18 Dictionary/Mail geometry follow-up

r18 responds only to Pablo's r17 screenshots. It preserves r17's official 208-page definition reflow and Enemy geometry. Mail's empty message drops the previous guessed two-space prefix; Dictionary `No data.` uses five leading style-1 cells instead of ten; the Dictionary index origin moves to x=268 while retaining the 14px cadence; and the Dictionary-only detail offset at file `0x588C84` changes 6→12 so selected title/icon content clears the full English `【Dictionary】` chrome.

```bash
python3 -m tools.build_early_ui_elf
python3 -m tools.build_translation_iso \
  '/private/tmp/khc-ps2/Kowloon Youma Gakuenki re-charge (Japan).iso' \
  /private/tmp/kowloon-recharge-startup-en-v11-r18.iso \
  --overlay exact-mtx local/exact-mtx \
  --overlay exact-ksf local/exact-ksf \
  --overlay structural-mtx local/structural-mtx \
  --overlay accepted local/accepted-overrides \
  --overlay startup-graphics local/startup-graphics \
  --elf artifacts/SLPM_665.11.en-early \
  --report local/startup-build-v11-r18.json
python3 -m tools.startup_acceptance \
  /private/tmp/kowloon-recharge-startup-en-v11-r18.iso \
  --startup-graphics-root local/startup-graphics \
  --report local/startup-acceptance-v11-r18.json
```

Measured r18 result:
- ISO SHA-256: `136a528030ab5ce611efd67fd06cf637f9015e1ba3473f760f9a6e72d7754c9a`;
- pre-ROFS ELF: `64c220490e64da7e6d50d8d76ebd0f9e60cc94c42cbc6414605ba258bd71fad1`;
- post-ROFS ELF: `a61b72b35d95112f68e79f1d1f1f1c36a77a1ab454ff714514694e540799f74a`;
- final ELF size: 8,562,114 bytes;
- 1,145 overlays; 892 in place / 253 relocated;
- **150/150** final-image checks;
- **218** dependency-free tests (10 expected skips);
- **218** Pillow-enabled tests (1 owned-corpus skip);
- `/private/tmp/kowloon-recharge-startup-en-v11-r18-repeat.iso` is byte-for-byte identical.

Do not launch PCSX2 automatically. r18's visual gate is Mail empty-state centering; Dictionary empty-state centering across several index pages; Dictionary A/K/S/T/N/H/M/Y/R/W clearing `【Dictionary】` and R1; and selected titles/icons such as H.A.N.T/Cairo/Heracleion/Rosetta Society clearing `【Dictionary】`. The r17 definition body reflow, Enemy row, and every previously accepted surface are preservation checks.


## Build startup v11-r19 Mail/Dictionary/Enemy root-layout candidate

r19 uses the same pristine source and overlays. It freezes all r18 Dictionary detail work and changes only Mail shared-row X plus Dictionary/Enemy root-nav geometry.

Measured result: ISO `4dbce7f49d537e6cc6aa156ff6d4723596de31b3a8657caa83a4b0a40db81928`; pre-ROFS ELF `c8795405f9746db2ba260c4fe644ee45218d200232112496f4ad6f1f58ba50b3`; post-ROFS ELF `d34d53d62b6236d1c1b87577704bbd2eb8d84945564216750df74347e82a7cef`; **150/150** final-image checks; **218** dependency-free tests (10 skips); **218** Pillow-enabled tests (1 skip); repeat ISO byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r19.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r20 Dictionary/Enemy selector-alignment candidate

r20 uses the same pristine source and overlays. It freezes every r19-accepted surface and changes only the independently animated Dictionary/Enemy selector geometry plus the clipped Enemy R1 anchor.

Measured result: ISO `374a8813fcf10d148c35b9e0e47be6d1d943ebf447752ed461f4a0fb17884ebd`; pre-ROFS ELF `30333e4d488714d2639b67c07da4ea76a4afd4b70e92ecc02f446421dd6850f9`; post-ROFS ELF `e4aa7717fe11111a7a82c07595a3d6e5088c2fc3b93dd4af2cb23610666bca83`; **150/150** final-image checks; **220** dependency-free tests (10 skips); **220** Pillow-enabled tests (1 skip); repeat ISO byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r20.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r21 Dictionary/Enemy selector-sizing candidate

r21 uses the same pristine source and overlay set as r20. It freezes all r20-accepted surfaces, changes Dictionary selector intrinsic width 24→14px with identical UVs, and changes Enemy selector width 40→64px while compacting the accepted 12px category row left enough to clear R1.

Measured result: ISO `08a9781ecfec5096f3d50769fabb686d7d8fa2cc82dcdca003e687dd05f9aaa7`; pre-ROFS ELF `457e2c149493f01a7ffcea7cc896af9b4296a8e587f17cb3e67edbb1ad1bb3cd`; post-ROFS ELF `b2a70936d57c6750f1f54ad19d1f398a11e6c0f2444bf3edb30cfd6e99c81616`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **222** dependency-free tests (10 skips); **222** Pillow-enabled tests (1 skip); repeat ISO `/private/tmp/kowloon-recharge-startup-en-v11-r21-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r21.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r22 selector-padding candidate

r22 uses the same pristine source/overlay pipeline. Only Dictionary selector width (14→16px) and Enemy selector base (216→218) differ from r21.

Measured result: ISO `1b3a9c916ec8436af94f702138efbdde3028158c4af256ba517293a2f3f2f009`; pre-ROFS ELF `60122115b3109f0acfc0c4f895a6fa79eb18fda7a3ff7d645310c050a7cab75d`; post-ROFS ELF `f1f6c68345e806296702fdd2f290b7cfbfb602dbe00992cd62819fe2954ec8ea`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **223** dependency-free tests (10 skips); **223** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r22-repeat.iso` is byte-for-byte identical.


## Build startup v11-r23 final H.A.N.T. header-clearance candidate

r23 is a bounded follow-up to Pablo's r22 runtime screenshots. It preserves all r22 selector/text geometry and changes only two navigation-control owners: Dictionary R1 moves x=428→424, and Enemy L1 moves x=194→190. The H.A.N.T. final-image regression test now fail-closes every owner in `HANT_RUNTIME_LAYOUT_PATCHES`, not a representative subset.

Measured result: ISO `4465f4322fc252d1fa0cf734fc4c63697c38adbda155a90eadcaca37698a55c5`; pre-ROFS ELF `564c4268faf7f7224bc5a4dc1d67c758a2af003f2c5487a4056af8d537a2041f`; post-ROFS ELF `4b59521acbfc96b68a6a934a7eb2442b8e426288714065f96f1980aeff3516f8`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **224** dependency-free tests (10 skips); **224** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r23-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r23.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r24 Dictionary R1 final-clearance candidate

r24 follows Pablo's r23 runtime review. Enemy is promoted to runtime-proven/frozen at its r23 geometry. Dictionary improved but still clips R1 slightly, so r24 changes only the Dictionary R1 owner from x=424 to x=420. Tabs, selector, Dictionary detail layout, Enemy, and all other accepted H.A.N.T. owners remain unchanged.

Measured result: ISO `46112aaaefb80a317dec4bed36e526d3e9f05f780dd435b4ecb0516c85e304d0`; pre-ROFS ELF `2242f5472f9ab228c51da4f776eb011e47b2facbfec02baf64159f3be71be58f`; post-ROFS ELF `930770fdad8ac71d1291e250400e467c0258cc57a1176f1bc330aa09e8de88e5`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **225** dependency-free tests (10 skips); **225** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r24-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r24.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r25 H.A.N.T. final layout candidate

r25 follows Pablo's r24 runtime review. Enemy is accepted and remains completely frozen. Dictionary moves its complete L1→R1 cluster four pixels left as one unit: L1 274→270, tabs 302→298 at unchanged 12px cadence, selector 300→296 at unchanged 16px width, and R1 420→416. Help switches its topic/category label constructors from style 0 to the already-proven 12px style 1; its `ADV / Ruins / Other` category composition shifts eight pixels left while keeping the 72px category selector, and the shared group-20 topic selector widens 168→268px with UVs byte-identical.

Build only from the pristine PS2 ISO with the same overlay pipeline as r24. Measured result: ISO `8cd3e369c08f8c29609c54236e73bfb06bf62b1c9aaaa9b0529fd08a17aec6c4`; pre-ROFS ELF `4100ea75fd1d82819521279fbf8edfc8038f6ec0dc852e68309896db6f47ed1b`; post-ROFS ELF `d0dfaa4390d6aaba4162b6a5115dfc4fb0b9e40d533737911d4c29557c6c86d5`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **226** dependency-free tests (10 skips); **226** Pillow-enabled tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r25-repeat.iso` is byte-for-byte identical to `/private/tmp/kowloon-recharge-startup-en-v11-r25.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r26 final H.A.N.T. shoulder-clearance candidate

r26 is a bounded follow-up to Pablo's r25 runtime screenshot. Dictionary moves the complete accepted L1→R1 cluster another four pixels left. Help keeps the r25 12px text and 268px topic selector, but fixes the category selector's L1 overlap by restoring selector base x=200, shrinking its shared width 72→64px while preserving right edge x=402, and aligning category labels at x=202/271/340. Enemy and all accepted detail/content owners remain frozen.

Measured result: ISO `189434d74b98fe2b1cacb4e1a2edfad9ac6943e12b6e8b655c4a4c4884fd57b0`; pre-ROFS ELF `fc001382a330a43313098adf3f70dfeec4fc1d77f2e93284de2d72cd39dcf940`; post-ROFS ELF `572ff87377d3c2692309da36689b38c107988eaf8442fb510f9b034d3678b7c2`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **227** dependency-free tests (10 skips); **227** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r26-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r26.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r27 final Help owner-correction candidate

r27 changes only the Help category X owner proven wrong by runtime: `Ruins` is restored at `0x18C768`, and `ADV` receives the intended -8px nudge at `0x18C778`. The accepted Help selector base/width, `Other`, Dictionary and Enemy geometry remain frozen.

Measured result: ISO `5210dde53302c6340cc27550f0f170a31ca317907759dbc29a92839c4781fb9e`; pre-ROFS ELF `9a925cb3c5b930ecaea0669f85399c1ef1c3514edf8e18e656e21df81773a1ff`; post-ROFS ELF `a31135de31bba5baa367925b743d48ddb6ab8a9a2d169da176440a4b3777fc27`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **228** dependency-free tests (10 skips); **228** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r27-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r27.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r28 Help selector-box candidate

r28 freezes all r27 Help category text geometry and changes only the selected red box. ADV uses a centered 48px box, Ruins a centered 72px box, and Other keeps its centered 64px box. Enemy, Dictionary, topic selectors and Help bodies are unchanged.

Measured result: ISO `e7517dfafd98766733324d3b8f62dcccf29b69928e8242cf469114830e197a83`; pre-ROFS ELF `25bad09a73def9900addcb96bdfea01a564d3147b0544d425ac7edef11901eef`; post-ROFS ELF `44ab4e4a20e11ce2162fe1e262dfa1d59e6106ab2fa89dedfa3aeafe856a2547`; final ELF size 8,562,114 bytes; **150/150** final-image checks; **229** dependency-free tests (10 skips); **229** Pillow tests (1 skip); `/private/tmp/kowloon-recharge-startup-en-v11-r28-repeat.iso` is byte-for-byte identical. Candidate path: `/private/tmp/kowloon-recharge-startup-en-v11-r28.iso`. Do not launch PCSX2 automatically.


## v11-r30 companion HUD build

Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r30.iso`

- SHA-256: `7bed876be95e19fd7c2fe1ade882eaf9fb0518db1165510861fa69d89db63c5f`
- pre-ROFS translated ELF SHA-256: `3da35c9939524c8e89c5df5b618c9556e721ec86051d9010dba9df0e303378ec`
- post-ROFS ELF SHA-256: `a85d899f3fd6d6ca8ce88a4c8f3b71eb02aa960577367c456ab4fbb865049d17`
- final ELF size: 8,642,989 bytes
- final-image acceptance: **153/153**
- dependency-free suite: **239 tests OK** (10 expected skips)
- Pillow-enabled suite: **239 tests OK** (1 owned-corpus skip)
- 1,145 overlays; 892 in place / 253 relocated; 1,145 executable ROFS records patched
- repeat build `/private/tmp/kowloon-recharge-startup-en-v11-r30-repeat.iso` is byte-for-byte identical.

Build uses the same pristine ISO/overlay set as r29. `tools.generate_companion_hud_data` derives the committed companion ownership manifest from pristine `SLPM_665.11` plus owned CUSA27034 `English.bytes`; normal builds do not require the PS4 extraction because the generated exact mappings and source hashes are committed.


## v11-r31 companion HUD presentation candidate

r31 is a bounded presentation-only follow-up to Pablo's r30 runtime screenshot. It leaves all r30 companion translations and the proven 160x32 group-2 backing resource unchanged, switches the persistent companion action caption from style 0 (16px) to the existing style 1 (12px), repositions the observed `Throw a Rock` text to 8px horizontal padding inside that backing, and moves the backing/text pair one 32px strip-height upward so it no longer covers the dungeon action palette. The four executable geometry/style owners and the backing dimensions are fail-closed in unit and final-image acceptance tests.

Current candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r31.iso`, SHA-256 `85bbe609fbe6ee875015a3c02ba685ca0d21f40d4b65ab164e2f0d82ba850833`; pre/post-ROFS ELF `249f074d753dcedb438725847ebadd6985145fdf3dbe0d8869394982c5fe7d4e` / `ef66c365be8c7c4ed28c7b2e98893572e6fe9566e785af5b5b83e39b6fe731d1`; final ELF size 8,642,989 bytes; final-image acceptance **154/154**; both suites execute **242 tests** (10 dependency-free skips / 1 Pillow skip); `/private/tmp/kowloon-recharge-startup-en-v11-r31-repeat.iso` is byte-for-byte identical. Do not launch PCSX2 automatically.


## Build startup v11-r32 companion bubble horizontal alignment

r32 is a bounded presentation-only follow-up to Pablo's r31 runtime screenshot. The official PS4/remaster companion payload remains frozen (`石を投げる` -> `Throw a Rock` is `official_exact`, not a new translation). The accepted r31 12px font, text X/Y, backing Y, 160x32 bubble resource, spike, and action-menu geometry remain unchanged. Only the bubble backing X owner moves 8px left (`+12 -> +4`) so the visible body/spike begins before the first caption glyph and more closely matches the PS4 HUD composition.

Measured result: ISO `acbc138a1c89ab0d81979e2d531dd5706c369df2cf49ef070311014ed833cb56`; pre-ROFS translated ELF `a0415bbcfeb3f20acc61ac0bf8431a690d2fbdd65bc5e82093ceb6afa7aaed96`; post-ROFS ELF `8a2721d16ad2c9602678472acadc4e397c342ea885e9be6fbaecfe4059a18159`; final-image acceptance **154/154**; dependency-free suite **242 tests** (10 expected skips); Pillow-enabled suite **242 tests** (1 owned-corpus skip); repeat ISO is byte-for-byte identical. Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r32.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r33 PS4-style companion speech bubble

r33 is a bounded presentation-only follow-up to Pablo's r32 runtime screenshot. The companion translations remain frozen and PS4/remaster-first; `石を投げる` -> `Throw a Rock` is still the committed `official_exact` remaster string. The defect was the backing resource itself: group-2 index `0x18` is intrinsically a 160x32 strip with a left-facing tail. r33 switches only that call site to the game's existing group-2 index `0xC5`, a 288x80 horizontal bubble with a downward tail. Atlas inspection confirms the record pivot `(67,77)` lands on the tail tip (bottom opaque pixels y=77, x=64..68), so the accepted r32 tail-tip anchor `(+4,-61)` is preserved. The 12px font is unchanged; text moves to `(-47,-131)`, preserving a 16px left / 7px top inset inside the wider bubble and substantially increasing English text room. Final-image acceptance now fail-closes the 0xC5 width, height and pivot as well as every executable layout owner.

Measured result: ISO `c9e31bccfe87c8fe9356107be9e572c6764dd9ed303268bf04f70058f1f13d19`; pre-ROFS translated ELF `75c1bba7ef9331cc60919715e620acba4605ea44d88969cabf96ee7d9b8e1a6a`; post-ROFS ELF `0345ed3f1ffece03384db78347b3369f62cfb0d817ce92e3e74bdeeb779fca5e`; final ELF size 8,642,989 bytes; final-image acceptance **154/154**; dependency-free suite **242 tests** (10 expected skips); Pillow-enabled suite **242 tests** (1 owned-corpus skip); `/private/tmp/kowloon-recharge-startup-en-v11-r33-repeat.iso` is byte-for-byte identical. Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r33.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r34 companion bubble resource correction

r34 fixes the runtime-disproven r33 resource selector without changing the accepted translation, 12px font, caption placement, tail-tip anchor, or action-menu geometry. r33 correctly identified the 288x80 down-tail bubble metadata at file `0x350B40` / VA `0x450AC0`, but incorrectly assumed it was group-2 index `0xC5`. Direct tracing of the group-2 resource table (`0x380AF0`) proves that metadata belongs to index `0x68` via record `0x380E30`; index `0xC5` instead resolves to unrelated metadata at file `0x353CF0`. r34 changes only the call-site resource selector from `0xC5` to `0x68` and now fail-closes the resource-table mapping itself so this class of mismatch cannot pass static acceptance again.

Measured result: ISO `ba4cc8e6949aa2331c9f043256b0418d6383c454f72762e1a87255662c61155a`; pre-ROFS translated ELF `6e5091fba3c2940fd76ced4757d46c9d038509703460bd0aaacfdbf80c6cc232`; post-ROFS ELF `06427d9d35390eca95d3a749b01023975cd1d141e7f8515dde971aebf514fe8b`; final ELF size 8,642,989 bytes; final-image acceptance **154/154**; dependency-free suite **242 tests** (10 expected skips); Pillow-enabled suite **242 tests** (1 owned-corpus skip); `/private/tmp/kowloon-recharge-startup-en-v11-r34-repeat.iso` is byte-for-byte identical. Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r34.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r35 compact one-line companion bubble

Pablo's r34 runtime screenshot proves the horizontal down-tail bubble is now the correct live resource, but its pristine 288x80 presentation is oversized for the persistent one-line action-caption path. The three lower HUD boxes span about 230 logical pixels in the same screenshot, so r35 keeps proven group-2 index `0x68` and its tail-tip anchor while changing only its rendered metadata to **224x48** with pivot **(52,45)**. The width is deliberately slightly less than the lower HUD group, creating extra clearance from the right-side action menu; 48px is the bounded one-line height for the existing 12px caption. Text moves to anchor offsets X=-36/Y=-99, preserving 12px left and 7px top inset after the resize. All persistent action labels remain single-line in the owned table; r35 does not invent an unproven multiline text renderer, and the separate transient companion-comment path remains untouched.

Measured result: ISO `2acae913416507008e0b6ec7e881b98c04f257f6ceef01f51534b8c74eb7bf04`; pre-ROFS translated ELF `129bf17c53fa92ae7c072db1ff7c92e8a2b415d721595d05676efe36a4e72199`; post-ROFS ELF `3ce090549ae6113210fd246ffadde1a80ff0d7dffddf9ca243818ee5e6cda063`; final-image acceptance **154/154**; dependency-free suite **242 tests** (10 expected skips); Pillow-enabled suite **242 tests** (1 owned-corpus skip); `/private/tmp/kowloon-recharge-startup-en-v11-r35-repeat.iso` is byte-for-byte identical. Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r35.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r36 generic companion-action bubble

r36 replaces the r35 fixed one-line companion-action presentation with one generic runtime path for every owned companion action. Official PS4/remaster wording remains the source of truth; no action-specific visual exceptions were introduced. Each English action label is deterministically word-wrapped at **17 12px cells per row** and encoded with the game's existing literal `0x0A` multiline control. Bubble width remains capped at the runtime-accepted **224px** so it stays slightly narrower than the three lower HUD boxes and clear of the right action palette. Height is generated solely from line count: **48px** for one line, **64px** for two, **80px** for three, with a 16px increment per additional row and a fail-closed four-line safety ceiling. The current corpus needs at most three rows. `Throw a Rock` therefore preserves the exact accepted r35 224x48 geometry, while `Smoking an Aroma Stick` becomes two rows and `Secret Technique: Reverse Waterfall Blade` becomes three automatically.

The implementation installs a generated 31-entry layout table plus a 96-byte MIPS selector in the shared translation PT_LOAD. At runtime the selector reads the current action id from the existing HUD object, bounds-checks it, applies that action's height/pivot-Y/text-Y values, selects the proven group-2 `0x68` down-tail bubble, and leaves the accepted X anchor/font/resource semantics untouched. The full early-UI build marks the translation PT_LOAD executable (flags 7) only because this verified hook lives there; standalone text/H.A.N.T. installers retain their previous non-executable default. Regression and final-image acceptance validate the hook, generated table, runtime owners, executable segment, wrapped payloads, metadata owners, and all previously frozen UI surfaces.

Measured result: ISO `4f61745be89ada402af35368169e2e6a5097367713f847a54fd1df78e963b9e9`; pre-ROFS translated ELF `f67c67eec2d3bd5e64811ad30375af8722579fa31d54832d727aefbd8309d4c8`; post-ROFS ELF `2fbf9d214437c588aad08f88f799587f2e06c4511942d4c483449d696710abf5`; final-image acceptance **154/154**; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip); `/private/tmp/kowloon-recharge-startup-en-v11-r36-repeat.iso` is byte-for-byte identical to the candidate. Candidate: `/private/tmp/kowloon-recharge-startup-en-v11-r36.iso`. Do not launch PCSX2 automatically.


## Build startup v11-r37 companion slot/action-id correction

r37 is a bounded correctness follow-up to Pablo's runtime-accepted r36 one-line bubble. Tracing the second-companion question proves HUD `+0x2D0` is the 0/1 companion-slot selector, not the action id: pristine code indexes the two position pairs at file `0x3F8E80` / VA `0x4F8E00`, `(172,407)` and `(230,407)`. r37 keeps that complete positioning path byte-identical. The actual action id is fetched by the original renderer through VA `0x0012FEE0` with key `0x8000`, then `ANDI 0xffff` / `XORI 0x8000`; the new 132-byte hook reuses that exact contract before indexing the generated 31-entry layout table. The accepted r36 text/resource/width/wrapping policy is unchanged.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r37.iso`; ISO SHA-256 `69ece655ce0700a88ace5444334f0570a69568fdd1de140ef1e5efdff19a0c9b`; pre-ROFS translated ELF `ef7f6cd3100560ded37e4ad0aedb1919f0b09bf48a76a77339a7a6b212b04604`; post-ROFS ELF `0eb2cd74ad0341685e5c942ad0e37ab875eaf0165855cfb84c35e1391d74a959`; final ELF size 8,643,496 bytes; **154/154** final-image checks; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r37-repeat.iso` is byte-for-byte identical and has the same SHA-256. Do not launch PCSX2 automatically; slot-2 and multiline runtime proof remains gated by story progression.


## Build startup v11-r38 slot-aware companion speech bubble

r38 keeps the runtime-accepted slot-1 presentation while making the persistent companion action bubble safe for companion slot 2. The pristine group-2 table proves sibling resources `0x68` and `0x69` share the same 288x80 bubble family while their X pivots differ by 58px, exactly matching the two pristine companion anchors `(172,407)` and `(230,407)`. Both resources are scaled to the same 224px safe body width. Slot 1 remains `0x68`, 224x48, pivot `(52,45)`; slot 2 uses `0x69`, 224x48, pivot `(97,45)`. This makes the slot-2 body and text move only about 13px right while the speech tail tracks the full 58px companion-anchor delta, avoiding the right-side action palette.

The runtime selector is now 188 bytes. Action id still comes independently from the game's existing getter at VA `0x0012FEE0` with key `0x8000`; HUD `+0x2D0` is read separately as the bounded 0/1 companion slot. Per-action height/pivot-Y/text-Y remains generated from the r36 wrapping policy, while slot chooses resource `0x68/0x69` and text-X `-36/-81`. Both sibling resource-table records and all eight sprite-geometry words are fail-closed, and the global pristine-region regression explicitly owns the slot-2 geometry without broadening any unrelated mutable range.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r38.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; pre-ROFS translated ELF `06a27d655951d86c55ae3c8b218450ac474074cbbf1f066f38e11c60114c22d7`; post-ROFS ELF `6b60a13db20c5de99e03258ae70d3a5f4a4d2e442ffba934dc7aef04021f3303`; final ELF size 8,643,556 bytes; ISO SHA-256 `e7d4c62df8157f00d8748b8e3bc93624705dacb19f8ae108d04683551c706a59`; **154/154** final-image checks; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r38-repeat.iso` is byte-for-byte identical and has the same SHA-256. Do not launch PCSX2 automatically. Runtime proof should confirm slot 1 is visually unchanged and slot 2 keeps the body in the central safe region while its tail points at the second companion.


## Build startup v11-r40 AFK companion chatter fix

r40 is intentionally **AFK-only**. The reverted 8+8 name-editor experiment is not present: `tools/startup_ui.py` and `tests/test_startup_ui.py` remain byte-identical to r38, and the original PS2 3+3 name behavior is accepted/frozen.

The passive companion chatter issue had two concrete owners. First, r38 compacted shared group-2 speech resources `0x68/0x69`; runtime proved AFK chatter also consumes those same resources. r40 restores their pristine 288x80 metadata and relocates group-2 to a byte-identical table prefix with two private compact active-action clones appended at ids `0xA4/0xA5`. The active L1 path keeps r38's 224px slot-aware geometry and generic action wrapping, while passive/AFK dialogue gets the original bubble presentation back.

Second, the r30 `h_buddy.c` inventory correctly translated 1,650 unique Japanese source lines through 1,784 event-table aliases, but a whole-ELF scan found ten additional direct executable pointers to nine of those same sources. r40 owns those ten aliases as well, producing **1,794 total direct companion-comment pointers**. Every line still uses the exact owned CUSA27034 `English.bytes` translation; no AFK text was authored. A regression test scans the complete ELF and requires the discovered direct-pointer set to equal the modeled owner set exactly.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r40.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; pre-ROFS translated ELF `22e5b157164fbac32bfb905ab7295059c1a271b44fadf03ec34971aab763e498`; post-ROFS ELF `01c9fd338ce37b11a69fa9456717770a27d9de2c2e0a508de46c7fc86e98453f`; final ELF size 8,644,980 bytes; ISO SHA-256 `7693f45672ca510320911faef6108fd27521f8d2e865069b9da632d045643528`; final-image acceptance **154/154**; dependency-free suite **244 tests** (10 expected skips); Pillow-enabled suite **244 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r40-repeat.iso` is byte-for-byte identical and has the same SHA-256. Runtime gate: confirm AFK chatter is English and correctly positioned, while the active L1 bubble remains visually identical to r38. Do not launch PCSX2 automatically.

## Build startup v11-r41 AFK text-only hotfix

r40 is **runtime-rejected**. Pablo reproduced a deterministic break immediately before the first old-man dialogue / first H.A.N.T. interaction: the `Heracleion` transition corrupts and the game stops progressing. Static acceptance had not caught this because r40's group-2 relocation preserved individual table records while changing the table's runtime placement/ownership model. That entire mechanism is removed in r41.

r41 starts from the restored r38 runtime layout and adds only the missing AFK text aliases. The original r38 companion action implementation is restored byte-for-byte: shared group-2 resources remain `0x68/0x69`, the 224px action bubble geometry/hook is unchanged, and there are no relocated resource tables or private `0xA4/0xA5` clones. The original 3+3 name system is also untouched.

Translation ownership remains the proven r30 corpus: 1,650 exact CUSA27034 `English.bytes` companion-comment strings. A whole-ELF scan found ten direct aliases outside the original 1,784 `h_buddy.c` event-table pointers, so r41 repoints those ten words to the already-existing relocated English strings, producing **1,794 total direct pointers**. No translation payload or translation-segment layout changes are introduced.

A fresh r38 reference rebuild was byte-compared against r41 before promotion. Both pre-ROFS ELFs are exactly 8,643,556 bytes, and r41 differs at exactly the ten intended 32-bit pointer owners: `0x3E6728`, `0x3F3BA8`, `0x3F452C`, `0x4104A0`, `0x43C42C`, `0x48897C`, `0x497190`, `0x49B564`, `0x4BE468`, `0x576778`. There are **30 differing bytes total** because each new pointer shares one unchanged high byte with its r38 value; there are no other binary differences.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r41.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r38 reference pre-ROFS ELF `06a27d655951d86c55ae3c8b218450ac474074cbbf1f066f38e11c60114c22d7`; r41 pre-ROFS ELF `9361623fa72cf61500dc3547c83a0b1f8df06ed0cd0d54b44182523535a9b63a`; r41 post-ROFS ELF `3c8faabc1e1870e3b1650ae332f7476e179d9faa7ce1d3ae8548775420ba1cb9`; ISO SHA-256 `fe04b2070efd647dfd657d6dbdc973646f1e69c559e234835fb57c7d2f113f4d`; final-image acceptance **154/154**; dependency-free suite **244 tests** (10 expected skips); Pillow-enabled suite **244 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r41-repeat.iso` is byte-for-byte identical. Runtime gates: first confirm the `Heracleion` -> old-man -> first H.A.N.T. flow is restored, then verify the previously Japanese AFK lines now render in English. AFK bubble positioning is deliberately not changed in r41.

## Build startup v11-r42 safe rollback after r41 false-positive alias corruption

r41 is **runtime-rejected**. The whole-ELF aligned-word scan used to discover ten supposed extra companion-comment aliases was not a valid ownership proof. Inspection of the ten locations shows that several are unrelated packed/binary data; most decisively, file offset `0x576778` is the 32-bit value formed by bytes inside the ASCII token `FOUT_CMD_PNL`, not a text pointer. Repointing those values corrupted unrelated game data and preserved the same pre-H.A.N.T. failure even after r40's resource-table relocation had been removed.

r42 removes **all ten speculative aliases** and restores the executable-producing code exactly to r38. It does not attempt another AFK translation fix. The accepted r38 companion action layout/runtime path, all H.A.N.T./old-man/startup content, and the original 3+3 name system are restored unchanged. The only retained companion-comment ownership is the proven r30 `h_buddy.c` event-table set: 1,650 exact CUSA27034 `English.bytes` strings through 1,784 validated table pointers.

The release gate is binary identity, not structural similarity. Fresh r42 pre-ROFS ELF SHA-256 is `06a27d655951d86c55ae3c8b218450ac474074cbbf1f066f38e11c60114c22d7`, exactly the known-good r38 pre-ROFS hash. Post-ROFS ELF is `6b60a13db20c5de99e03258ae70d3a5f4a4d2e442ffba934dc7aef04021f3303`. The finished r42 ISO SHA-256 is `e7d4c62df8157f00d8748b8e3bc93624705dacb19f8ae108d04683551c706a59`, exactly the known-good r38 ISO hash. Final-image acceptance is **154/154**; dependency-free suite **243 tests** (10 expected skips); Pillow-enabled suite **243 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r42-repeat.iso` is byte-for-byte identical.

Runtime expectation: the `Heracleion Shrine` -> first old-man dialogue -> first H.A.N.T. interaction must behave exactly as r38. The passive AFK Japanese dialogue remains explicitly unresolved and must be traced from its actual runtime consumer rather than inferred by raw-value scanning.

## Build startup v11-r43 Re:charge companion free-talk localization

r43 fixes the Japanese passive/AFK companion chatter by patching the **actual structurally bounded owner**, not by scanning arbitrary ELF words. The free-talk corpus is a fixed 0x80-stride table at file `0x3E5FA0..0x3F8BA0`: 30 companion ids × 20 records = 600 records. Each record owns line 1 at `+0x08` and optional line 2 at `+0x0C`, with `0x00794150` as the pristine empty-string sentinel. The table contains 999 live text fields and 952 unique Japanese source pointers. Pablo's screenshot line `む？迷ったかの？` is Salah id 25, record 01, structurally owned by pointer field `0x3F5028` and source file offset `0x3D20D0`.

The PS4/remaster localization does not contain this Re:charge-only free-talk corpus as a complete source set. Four fields have exact official PS4 matches and use those strings verbatim. The remaining fields are authored English, translated record-by-record with companion context and calibrated against the existing PS4 localization's terminology and voice conventions (for example `Mummy's`, `Gravekeeper`, `Treasure Hunter`, `Rosetta Society`, Higo's childish phonetic speech, military diction, and established character registers). Reused Japanese source pointers are required to use one identical English rendering, and every English field is capped at 38 characters and validated against the PS2 glyph encoder.

Safety is intentionally stronger than r40/r41. r43 changes **no** group-2 speech resource table, bubble geometry, action hook, name editor, H.A.N.T. owner, or old-man/story data. Original Japanese AFK bytes remain immutable. The AFK relocation entries are appended after every pre-r43 translated entry, preserving all previously accepted translated VAs. A fresh detached r42 rebuild was compared byte-for-byte against r43: all **999/999** structurally proven AFK pointer words change; outside those owners the only common-prefix change is ELF `p_filesz` at `0x64..0x66`, required to grow the existing translation PT_LOAD. r43 appends 44,257 bytes and changes no other pre-existing runtime/data range.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r43.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r42 reference pre-ROFS ELF `06a27d655951d86c55ae3c8b218450ac474074cbbf1f066f38e11c60114c22d7`; r43 pre-ROFS ELF `517e6249a78f79bfb5c474445627df056487757aef2ae90babeb0965d9e4faef`; post-ROFS ELF `fe34ee64b1ea2a1966604cc5cb9bbca2e50736238ee1bfe589221f54b284f129`; final ELF size 8,687,813 bytes; ISO SHA-256 `6d52f43224744bb24fe22c19f5cf0047b65ccfddc7815e44d909bd3aa3546165`; final-image acceptance **155/155**; dependency-free suite **246 tests** (10 expected skips); Pillow-enabled suite **246 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r43-repeat.iso` is byte-for-byte identical and has the same SHA-256. Runtime gate: verify the known-good `Heracleion Shrine` -> first old-man -> first H.A.N.T. sequence remains intact, then wait for passive companion chatter and confirm the free-talk text is English. AFK bubble geometry is deliberately unchanged from r42/r38.

## Build startup v11-r44 hide persistent L1 callout during AFK free-talk

Pablo runtime-confirmed r43's Re:charge free-talk localization: passive companion dialogue now renders in English. The remaining presentation conflict was simultaneous ownership of two bubbles—the native AFK/free-talk bubble plus the persistent L1 companion-action callout. r44 keeps the AFK renderer and the accepted r38/r43 action presentation completely separate; it does **not** route AFK text through the L1 renderer and does not change either bubble's resources or geometry.

The visibility gate is tied to native `H_TalkBuddyTask` state rather than a timer guess. The task's current record index lives at `s0+0x04`; indices below `0x259` are the original 601 `h_buddy` records and indices `>=0x259` are the Re:charge free-talk continuation. The task's four live speech render handles are `s0+0x20`, `+0x24`, `+0x28`, and `+0x2C`. r44 suppresses the persistent L1 callout only when the current record is in the AFK range **and** at least one of those native render handles is live. This means the L1 callout remains visible during the idle countdown and returns automatically as soon as AFK speech has finished.

The renderer already had a clean whole-callout visibility branch at file `0x666BC..0x666C4`: pristine `lw v0,0x2c8(s0)` followed by `beq v0,zero,0x166814`. r44 appends a 76-byte side-effect-free predicate to the existing translation PT_LOAD. The callsite becomes `jal predicate`, `nop` delay slot, `beq v0,zero,0x166814`; the branch moves one instruction but keeps the same destination. The predicate preserves the original `s0+0x2C8` guard first, then evaluates only the AFK index/render-handle condition. No resource ids, action ids, coordinates, bubble metadata, AFK strings, H.A.N.T., story data, or name owners are modified.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r44.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r44 pre-ROFS ELF `e190a6399ebb6aabdf737b19861a355a6cbf1041df995a01e4e501b1b4508857`; post-ROFS ELF `b1c13ddc0c9ed571a053dc867a9d2b9e2d106f013757a0d8f4275d255ef14b32`; final ELF size 8,687,892 bytes; ISO SHA-256 `ec0f35ff63bacff5f9d7f40ead7f29da59919fb81926489ecdd24bf29788b48c`; final-image acceptance **155/155**; dependency-free suite **247 tests** (10 expected skips); Pillow-enabled suite **247 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r44-repeat.iso` is byte-for-byte identical.

Direct r43→r44 pre-ROFS audit: r43 is 8,687,813 bytes and r44 grows by only 79 bytes (3 alignment bytes + 76-byte predicate). In the complete r43 prefix, only 11 bytes differ: the ELF translation-segment `p_filesz` byte at `0x64` and the intended three-instruction callsite at `0x666BC..0x666C7`. Every r43 AFK translation pointer/payload address remains stable. Runtime gate: trigger AFK free-talk and confirm only its native bubble remains visible; after it closes, the L1 companion-action bubble must return automatically.

## Build startup v11-r45 unify native AFK companion callout

r45 is the runtime-driven presentation correction after Pablo's r44 screenshots. The screenshot clarified an important ownership mistake in the r44 interpretation: the green layer visible behind the AFK text is not sufficient evidence that the independent persistent L1 action callout survived. Native Re:charge free-talk itself constructs a **two-layer callout**: a slot-specific green group-2 resource `0x68`/`0x69`, which carries the companion-tail/speaker cue, plus a blue-tinted group-2 resource `0x6A`, which provides the dialogue panel behind the AFK text.

Static tracing of the free-talk selector at file `0x67A80..0x67C68` proves speaker identity is already native. The selector is called separately for companion slot 0 and slot 1, reads the companion id for that slot, computes `(companion_id - 1) * 20 + 0x259`, stores the selected companion id into `H_TalkBuddyTask+0x338`, stores the selected record index into task `+0x04`, and enters state 9. The AFK-specific text constructors at `0x6627C` / `0x6634C` receive that stored speaker id. After construction the task enters state 11; visible/teardown processing continues through states 12 and 13 before returning to state 8. r45 therefore replaces r44's render-handle inference with the exact native lifecycle predicate: preserve the original `s0+0x2C8` L1 guard, require record index `>=0x259`, then suppress the independent action callout only for task states 11..13.

The geometry mismatch also has a concrete cause. AFK placement records are `0x3F8E1C=(group 2, resource 0x68, z249, x172, y381)`, `0x3F8E30=(2,0x69,249,230,381)`, `0x3F8E44=(2,0x6A,246,172,381)`, and `0x3F8E58=(2,0x6A,246,172,381)`. r38 intentionally compacted shared `0x68/0x69` from their pristine 288px speech-body geometry to the accepted 224px action-body geometry, so AFK's green layer became compact too while its paired blue `0x6A` remained 288px wide. r45 does **not** restore or relocate shared resources. Instead it patches only `0x6A`'s three animation metadata frames at file `0x350BA0/0x350BD0/0x350C00`: `(288,56,67,74/75/76)` becomes `(224,56,52,45/46/47)`. The 1px frame-to-frame Y progression is preserved. Slot 1's blue panel remains x=172; slot 2 changes x=172→185, matching the accepted 13px body shift between compact `0x68` and `0x69` while their green tails continue to target the two companions 58px apart.

Ownership is fail-closed. Group-2 resource `0x6A` resolves through table record file `0x380E40` to metadata VA `0x00450B20`, count 3. A structured scan for the exact `(group=2, resource=0x6A)` pair finds exactly two aligned placement owners in the pristine ELF: `0x3F8E44` and `0x3F8E58`. The AFK layout pass validates that resource record, all three pristine geometry records, both pristine placement records, and the structured-owner inventory before writing. It never modifies `0x68/0x69`, the slot-position table, the 600-record AFK text table, any translated AFK pointer, H.A.N.T., story data, or name-entry code.

Direct r44→r45 pre-ROFS audit is the release invariant. Both files are exactly 8,687,892 bytes. Only **44 bytes** differ across 20 byte ranges. Every range is contained either in the declared AFK `0x6A` geometry/slot-placement words or in the existing 76-byte visibility-hook body at file `0x8490C8`; there is no translation-segment growth and no callsite change. All 999 r43 AFK translation pointer words are byte-identical r44→r45, and accepted compact `0x68/0x69` metadata is byte-identical. The hook remains 76 bytes at the same VA/file location, so all pre-existing translation payload VAs remain stable.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r45.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r45 pre-ROFS ELF SHA-256 `1e8aa69d63eb1056b0a319f417abaa14627165029e0d0e4470cf35e603b0f000`; post-ROFS ELF SHA-256 `2f3a849ef82eb3a2bd4d266955652fbc07266565ac653b9b3f6a41b5e19d23e3`; final ELF size 8,687,892 bytes; ISO SHA-256 `8828ce028ef6b18ffe0525ada81925ef6ca8ff2b48a7d46141e54c959cb806ab`; final-image acceptance **155/155**; dependency-free suite **249 tests** (10 expected skips); Pillow-enabled suite **249 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r45-repeat.iso` is byte-for-byte identical with the same SHA-256.

Runtime gate for r45: with one companion, AFK free-talk should render as one visually coherent compact callout (green speaker tail + aligned blue dialogue panel), without a second independent action callout. With two companions, trigger free-talk from each slot and confirm the green tail identifies the speaker while the blue body follows the matching 13px slot-body shift. After AFK state leaves 11..13, the persistent L1 action callout must return. Do not launch PCSX2 automatically.

## Build startup v11-r46 restore native AFK blue panel

r45 is **runtime-rejected for AFK presentation**. Pablo's r45 screenshot showed the opposite of the intended composition: the blue-tinted AFK panel disappeared and only the green companion-shaped layer remained behind the English free-talk text. Static metadata checks had passed, so this is a concrete reminder that the `0x6A` resource's width/pivot fields cannot be treated as ordinary independent geometry merely because they decode as floats.

r46 therefore removes every r45 write to group-2 resource `0x6A` and its two placement rows. The AFK layout pass is now validation-only: it still proves table record `0x380E40 -> (VA 0x00450B20, count 3)`, the three native frames at `0x350BA0/0x350BD0/0x350C00`, and the exact two structured `(group=2,resource=0x6A)` owners at `0x3F8E44/0x3F8E58`, but it returns the input bytes unchanged. Native geometry remains `(288,56,67,74/75/76)` and both native placements remain `(2,0x6A,246,172,381)`. These values are now treated as immutable final-image invariants rather than legal patch owners.

r46 deliberately **keeps r45's improved visibility predicate byte-for-byte**. The original action guard at `s0+0x2C8` remains first. The predicate then requires a Re:charge free-talk record (`task+0x04 >= 0x259`) and native `H_TalkBuddyTask` state 11..13 before returning zero to the game's existing whole-L1-callout skip branch. This is the only presentation logic retained from r45; the AFK blue resource itself is restored to the known-visible r44/native state.

The binary relationship is unusually strong. r44, r45 and r46 pre-ROFS ELFs are all exactly 8,687,892 bytes. r45->r46 changes only **10 bytes in 10 one-byte ranges**, each inside one of the ten r45 `0x6A` geometry/slot-placement words, restoring the native values; the 76-byte r45 visibility hook is byte-identical. Conversely, r44->r46 changes only **34 bytes across 10 ranges**, all inside that same relocated 76-byte visibility-hook body at file `0x8490C8`; the complete native `0x6A` metadata/placement regions are byte-identical to r44. In other words, r46 is exactly the intended hybrid: **r44/native blue panel + r45 native-state visibility predicate**.

All r43 free-talk ownership remains frozen: 600 records, 999 live pointer fields, 952 unique Japanese sources and their English payloads are unchanged. Shared `0x68/0x69` action geometry, action-id lookup, H.A.N.T., story/startup data and the intentionally frozen 3+3 name system are unchanged. No group-2 table relocation/private resource mechanism is reintroduced.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r46.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r46 pre-ROFS ELF SHA-256 `3e217f69399acbd66527d83345f1fa8405db7fb5ac8007ce68185b31b2d65b2d`; post-ROFS ELF SHA-256 `f847aca18d1d6741b6f23579951f5cfd39f19c70e538d20bc228a07099ccfa82`; final ELF size 8,687,892 bytes; ISO SHA-256 `f2ee41dbc82bb8499786094de501093ff62e81d6d0c6e8d127ce1caba1536d7a`; final-image acceptance **155/155**; dependency-free suite **249 tests** (10 expected skips); Pillow-enabled suite **249 tests** (1 expected skip). `/private/tmp/kowloon-recharge-startup-en-v11-r46-repeat.iso` is byte-for-byte identical with the same SHA-256.

Runtime gate: confirm the blue-tinted native AFK panel is visible again around the English free-talk text. While `H_TalkBuddyTask` is in free-talk states 11..13, the independent persistent L1 action callout should be absent; after the AFK lifecycle exits those states it should return. Do not infer correctness from green-layer presence alone because native AFK itself also uses `0x68/0x69`. Do not launch PCSX2 automatically.


## Build startup v11-r47 generic AFK bubble/text fit

r47 resolves the underlying shared-resource conflict instead of resizing the native AFK blue panel. Pristine Re:charge AFK is a two-layer composition: slot-specific green resource `0x68/0x69` is 288×80 with pivots `(67,77)/(125,77)`, while blue resource `0x6A` is 288×56 with pivot X=67 and its native three-frame Y progression. The AFK placement rows make all layers share effective left edge X=105: slot-0 green `172-67`, slot-1 green `230-125`, and blue `172-67`. The 24px green-vs-blue height difference is therefore part of the outer bubble/tail composition, not evidence that the blue panel should be stretched. r47 keeps `0x6A` byte-for-byte native.

The actual regression came from r38 statically compacting shared `0x68/0x69` to the 224px L1-action geometry. AFK reuses those same resources, so its green outer bubble was compact while its native 288px blue body was not. r47 separates the two consumers at runtime. Shared `0x68/0x69` metadata is pristine in the finished ELF. Before a normal L1 action callout, the existing 188-byte action selector tail-jumps into a new 72-byte geometry extension which writes width 224 and pivot X 52/97 for the active slot; the existing selector still writes action-specific height/pivot-Y and text position. Before native AFK constructs its callout, file owner `0x66050` calls a new 112-byte helper that restores the selected slot's green resource to native width 288, height 80, pivot Y 77 and pivot X 67/125. The original `sll v1,v0,7` at `0x66054` remains the JAL delay slot and the helper recreates the original v0/v1 result on return.

AFK text fit is calculated for the complete 600-record corpus rather than hard-coded for a sample line. The specialized free-talk text constructor uses style-0 16px glyph advance; native AFK text begins at X=117 while the bubble body begins at X=105, proving a 12px left inset. r47 reserves the same 12px on the right, giving `288-12-12 = 264px` usable width, or 16.5 style-0 cells. A 600-float relocated table stores one horizontal scale per record:
`scale = min(1.0, 264 / (16 * max(len(line1), len(line2))))`.
Both rows of a record use the same scale so typography stays consistent. Only the Re:charge/free-talk callsites at `0x6625C/0x6632C` are redirected to the scale helper; the original h_buddy text path keeps `f16=1.0`. Across the current English corpus, 81 records remain at 1.0, 519 are scaled, the minimum scale is 0.4342105263 for 38-character rows, and every one of the 999 live fields is mathematically bounded to <=264px.

All new relocated payloads are appended strictly after the r46 visibility hook, preserving every prior translated VA. Direct r46→r47 audit proves all 999 AFK translated pointer words are unchanged and the r46 visibility hook is byte-identical. The old r46 translation-segment payload is byte-identical except for the deliberate final words of the existing action hook, which now tail-jump to the new geometry extension. Native blue `0x6A` is unchanged. Shared green `0x68/0x69` is restored to pristine static geometry. The complete common-prefix delta is 41 bytes across 18 ranges, all classified as translation-segment size metadata, the three new AFK runtime callsites, restoration of the eight static green geometry floats, or the action-hook tail. r47 appends 2,648 bytes: the 2,400-byte scale table plus the new helpers/alignment.

Measured result: candidate `/private/tmp/kowloon-recharge-startup-en-v11-r47.iso`; pristine ISO SHA-256 `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`; r47 pre-ROFS ELF SHA-256 `94f055aa0a659be822cfc2f097cd873929e6d89b0022d4fc72b57a3514787039`; post-ROFS ELF SHA-256 `02b713ef36cd3daa641208c029743ea069f254a759277a49755f19d06dcac9d7`; final ELF size 8,690,540 bytes; ISO SHA-256 `c81013599fa3b504670f630c8644f35c0c8bcccf36bc5967a3866183387a73aa`. Focused companion/early-UI/acceptance suite: **38/38**. Complete dependency-free suite: **250 tests** (10 expected skips). Pillow-enabled suite: **250 tests** (1 expected skip). Final-image acceptance: **155/155**. `/private/tmp/kowloon-recharge-startup-en-v11-r47-repeat.iso` is byte-for-byte identical with the same SHA-256.

Runtime gate: with either companion slot speaking, the AFK green outer bubble/tail and native blue inner panel should align as the original 288px composition; the tail must continue to identify the speaking slot. Every translated AFK row should remain inside the green/blue body via the calculated horizontal scale. Normal L1 action callouts must still use the accepted compact 224px presentation, and r45/r46's independent-L1 suppression during free-talk states 11..13 remains unchanged. Do not launch PCSX2 automatically.
