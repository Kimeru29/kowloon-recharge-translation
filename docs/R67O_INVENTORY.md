# r67.15o installed ADV inventory

The verified candidate has ISO SHA-256 `049b68c70c74f99b195975000c90e064b5106cbe18cf0dc89f87b44526081b13` and installed ELF SHA-256 `fd4760a3c96260ef0fde8cf113a9cc49d46fe732a7f7b0087357f612f1182787`. Its inventory summary has SHA-256 `1d736560fb90ae695a716b6941f2a487ac45144c42dbab1c42807acff6f97c1d`.

The inventory reads the pinned r67.15n disc and its six JSON files, rechecks all serialized installed locations and fingerprints, and compares original PS2 and PS4 sources. It replays both exact MTX producers, then the fixed speaker-label pass, and reads the final resource payloads through the candidate's DATA.CVM directory. It checks retained English through each pointer-region relocation, verifying alias topology, untouched runs, and native terminal padding.

The candidate ELF is verified against the composed choice and speaker executable, with the installed ADV ROFS size and extent changes applied. The choice table is read from its actual ELF load address. Every staged choice must match its native file, record, ordinal, flags, 30-byte original and installed preimages, and official DC glyph bytes. The inventory also records bounded name controls when present.

| Census | Count |
| --- | ---: |
| Physical ADV files | 3,032 |
| Original official DC array identities | 101,487 |
| Verified installed ranges | 99,284 |
| MTX DC entries with verified installed English | 98,201 |
| KSF DC entries with guarded ELF English | 1,079 |
| Official blank stock no-ops | 4 |
| MTX DC entries with unresolved correspondence | 2,197 |
| KSF DC entries with unresolved correspondence | 6 |
| Physical native choice slots | 1,136 |
| Fixed speaker-label pairs verified against official sources | 214 |
| Newly localized fixed speaker-label occurrences | 7,402 across 478 MTX files |
| Fixed speaker-label pairs used by those occurrences | 31 |

The 98,201 verified MTX entries include nine inherited entries with reviewed source-specific correspondence, 51 newly imported bundle entries, and 148 new alternate-owner entries. For the 148 entries, the original numbered MS01_03 DC array indices and keys remain the logical identity, while `installed_asset` points to `KWLNSCR.MTX`. The candidate keeps both numbered control scripts' original bytes. The speaker census measures occurrences on the candidate. Its source DC references establish fixed name usage without establishing scene-level correspondence for other entries, including FD00 templates.

All 1,136 choice slots retain the same physical resource bytes as r67.15n. The guarded English table owns 1,079 labels across 441 records and 163 files. The four blank no-ops and 53 slots without a verified English owner follow stock behavior. The six unresolved official choice entries belong to the PS4 numbered MS01_03 map. The matching numbered PS2 records have no active choices, and root-context correspondence remains unproven. Previously capacity-blocked labels are covered by the guarded table. The retained Japanese in those KSF fields remains eligible for stock fallback if the guarded path is unavailable.

## Inventory files

| File | Contents |
| --- | --- |
| `files.json` | Each PS2 asset's source, candidate and map hashes, ISO coordinates, and installed evidence |
| `entries.json` | One row per original `(file, official_array_index)`, retaining repeated keys and identifying the physical owner and exact final range where verified |
| `japanese.json` | CP932-aligned body text candidates and physical Japanese choice bytes, including explicit guarded-English fallthrough rows |
| `ksf-labels.json` | Every active native slot, physical before/after hashes, terminators and operative static owner |
| `speakers.json` | Source-proof label identities, installed translated occurrences, and unresolved roles |
| `ps4-payload-index.json` | Same-kind source hash index inherited from the reverified baseline |
| `summary.json` | Counts, producer and source fingerprints, candidate ISO and ELF SHA-256 values, and scanner limits |

The installed scan found 18,254 unresolved MTX lexical candidates and 157 Japanese KSF labels. Of those labels, 104 retain physical Japanese behind verified guarded English, including 11 original safety fallbacks. The other 53 have unresolved correspondence. The 18,411 findings measure physical text candidates and stock labels.

The scanner excludes MTX pointer headers and packed KSF data. A CP932 candidate can be a name, dialogue, or another text operand. A physical Japanese choice can coexist with a verified guarded English label. Missing same-path assets leave correspondence unresolved. The inventory establishes static installed evidence. PCSX2 rendering, actual fallback, and in-game route reachability remain subject to gameplay testing.

## Reproduce

Run from the repository root with a fresh output directory.

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools PYTHONDONTWRITEBYTECODE=1 \
  local/r67m-integration/venv314/bin/python -m tools.r67o_inventory \
  --baseline-iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --candidate-iso local/r67o-release/67.15o-cumulative-official-diagnostic.iso \
  --baseline-inventory local/r67n-inventory-final \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --bundle-report local/r67o-bundles/report.json \
  --kwlnscr-report local/r67o-kwlnscr/report.json \
  --speaker-report local/r67o-speakers/report.json \
  --reviewed-report local/r67o-reviewed/report.json \
  --choices-report local/r67o-choices/report.json \
  --output-dir local/r67o-inventory-final
```

The bundle replay also reads `r67n-partial/report.json`. The choice verifier uses `r67o-research/ksf-design-evidence.json`, `r67o-choice-correspondence/report.json`, and the pristine PS2 ELF. Pass `--bundle-partial-report`, `--choice-research`, `--choice-supplement`, or `--pristine-elf` when those files are stored elsewhere.

The repeat command reproduced all seven JSON files byte for byte. A separate read of the saved inventory verified every serialized ADV file hash, installed DC range, Japanese candidate range, physical KSF slot, and translated speaker range against the completed ISO. All seven focused inventory tests passed.
