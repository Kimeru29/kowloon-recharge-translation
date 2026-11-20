# Official MS01_03 text in the PS2 KWLNSCR program

The r67.15o cross-file overlay transfers **148 official English entries in 146 groups** from `ADV/MS/EN/MS01_03DC.json` to `ADV/KWLNSCR.MTX` over the immutable r67.15n baseline. The official key identity remains the numbered PS4 DC path plus its original array index and key. The destination offset is recorded separately.

The PS2 numbered `MS01_03.MTX` and `MS00_01.MTX` are small control programs with no CP932 display text after their pointer tables. The loader uses a separate path for the PS2 root program in Mode 6. It selects the `KWLNSCR` prefix at `0x7948b0` and uses the `adv/%s.MTX` and `adv/%s.KSF` templates. Both numbered PS2 programs retain their original payloads.

## Correspondence

Each half-open span below includes Japanese display text and native scene controls. The importer verifies the entire block on CP932 boundaries and searches every physical MTX for exact occurrences.

| PS4 MS/MS01_03.MTX | PS2 KWLNSCR.MTX | Bytes |
| --- | --- | ---: |
| `[1854, 2919)` | `[387, 1452)` | 1,065 |
| `[2919, 4186)` | `[1505, 2772)` | 1,267 |
| `[4188, 5172)` | `[2772, 3756)` | 984 |

Each block occurs once across 1,516 PS2 MTXs and twice across 1,067 PS4 MTXs. The PS4 occurrences are the numbered script and the PS4 root script. The latter matches PS2 `KWLNSCR.MTX` byte for byte. Each transferred group fits inside a single pointer region on both sides and retains matching left controls and the right delimiter. Official `(px)`, `(pm1)`, and `(pn1)` use the original native control tokens. Each group conserves the name tokens it owns, including the two-line group that reorders its first-name and family-name tokens.

| Classification | Official entries |
| --- | ---: |
| Transferred with exact block and control evidence | 148 |
| Held because the title's full left-control context differs (key 1875) | 1 |
| Held because an official name moves into a blocked phonetic group (key 3649) | 1 |
| Held because phonetic macros and native one-glyph controls differ (keys 3670 and 3760) | 2 |
| No bounded alternate owner | 74 |
| Total | 226 |

The fingerprint manifest records the complete release input hashes, three blocks, four holds, expected entry dispositions and a digest over every approved group and encoded line. It also fingerprints the full inventories of physical MTX files. [Correspondence manifest](../translations/r67o_kwlnscr_correspondence.json)

## Native pointer and KSF verification

The 17 KSF records select chapter ordinals. The code at `0x22c598` reads the current ordinal with the KSF record walker at `0x22d0b0`. The link fields feed the next ordinal. At `0x22c77c`, value 999 ends the scenario. For another chapter the engine selects an MTX pointer slot through `0x215820`, then computes `MTX_base + 4 * u16[ordinal]`. The importer verifies those instructions and loader anchors in both pristine and installed executables, and checks every KSF header and conditional link target against the live pointer slots.

The emitted MTX keeps all 18 original pointer slots, including the null slot. A byte audit replays every approved span, examines all intervening bytes and confirms 23 alignment NULs after existing `_` terminators. The four mapped holds are also checked at their relocated output offsets. The KSF is byte-identical to the pristine and installed input, with SHA-256 `3bc7536ae977375f949cde5376401e348a680e94915a409d54a3c034e7fd3177`. The overlay contains one MTX and has no native code delta. Mode 6 activation and presentation remain unverified in PCSX2.

## Reproduction

The tool uses the original source extraction layout. It reads the pristine `SLPM_665.11` alongside the PS2 `assets` directory and reads `Modules/Il2CppUserAssemblies.prx` under the PS4 extraction's `Media` directory. It requires a fresh output directory.

```sh
PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m tools.r67o_kwlnscr \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --baseline-iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --output-dir local/r67o-kwlnscr-reproduction

PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m unittest \
  tests.test_r67o_kwlnscr tests.test_r67n_partial tests.test_r67n_ksf \
  tests.test_mtx tests.test_mtx_compile tests.test_localization
```

| Output under `local/r67o-kwlnscr/` | SHA-256 |
| --- | --- |
| `overlay/KWLNSCR.MTX` (6,176 bytes) | `bdc710ef77e6351fc452c3dcc88872f582143f8c770737a632e27256d49392cc` |
| `report.json` | `4f7c0671e09ea26f916d6d3bb675021f2a202f7fd5a52b33e342fe76e1afa4ab` |

`report.json` lists all 226 DC indices in official array order. Each record includes the source and target asset fingerprints, PS4 group, PS2 original and installed ranges, relocated output where a target is proven, pointer slots and disposition. Synthetic DC keys share the source group range and have separate English line ranges.
