# r67.15o cumulative official diagnostic

The cumulative diagnostic starts from the immutable r67.15n ISO with SHA-256 `c3aa8a847f9ed505ca62d11dfa22cfd6e28a9c8f3d63900928f41824e00ea1f0`. It adds 51 official DC entries from [exact bundles](R67O_EXACT_BUNDLES.md), 148 from [KWLNSCR](R67O_KWLNSCR.md), 7,402 [speaker headers](R67O_SPEAKERS.md) and 1,079 [guarded choice labels](R67O_CHOICES.md). The choice renderer uses an executable table. All KSF payloads remain byte-identical.

| Artifact in `local/r67o-release` | SHA-256 |
| --- | --- |
| `67.15o-cumulative-official-diagnostic.iso` | `049b68c70c74f99b195975000c90e064b5106cbe18cf0dc89f87b44526081b13` |
| `67.15o-cumulative-official-diagnostic.elf` | `fd4760a3c96260ef0fde8cf113a9cc49d46fe732a7f7b0087357f612f1182787` |
| `release-report.json` | `86dcbbd0eee797f8183ebe53e900b0e276b8e73464ff129b5d524f0f2775539e` |

## Static audit

The release checks the baseline ISO and producer report fingerprints. It rehashes all 1,516 staged speaker inputs against either installed n bytes or the exact earlier producer bytes. For the three overlapping files, the speaker report must name the precise bundle or KWLNSCR preimage. The composed disc installs the final 478 MTXs and rewrites their corresponding ROFS metadata.

The independent disc audit compared all 2,095,382,528 bytes. It accounted for 7,285,685 changed bytes with zero unexplained bytes. Thirteen new payloads relocate into 53 appended DATA.CVM sectors. The shifted outer ELF extends at the end of the allocated outer files. A separate ROFS audit checked all 10,656 records with zero mismatches. [ELF growth rules](R67O_TAIL_ELF.md)

The executable changes ten pinned calls, the translation segment file-size word and the audited ROFS metadata. The two native producers contribute 182,360 appended bytes within the existing reserve. The installed image passed the 52 protected source fingerprints, historical k report, wheel and Group 4 artwork, native q/t locks, four history regions and 15 save descriptors. Startup passed 154 of 155 raw checks and 155 of 155 scoped checks with the existing bounded wording exception for `memory_card_8`.

A fresh build in `local/r67o-release-repeat` produced a byte-identical ISO and ELF. Both copies have the fingerprints above. The release reports differ only in their output paths.

Gameplay and save compatibility await the user's playthrough.

## Reproduce from verified producers

Run from the repository root after regenerating the producers and their staged speaker inputs. Set `STARTUP_GRAPHICS` to the accepted startup graphics directory from the r67.15n reproduction. Supply a fresh output directory for every run. The output ISO receives its final filename after the audits pass.

```sh
PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m tools.r67o_release \
  --source local/r67n-release/67.15n-official-script-diagnostic.iso \
  --bundles local/r67o-bundles \
  --kwlnscr local/r67o-kwlnscr \
  --speakers local/r67o-speakers \
  --choices local/r67o-choices \
  --staged-inputs local/r67o-speaker-inputs \
  --graphics "$STARTUP_GRAPHICS" \
  --output-dir local/r67o-release-reproduction

PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m unittest \
  tests.test_r67o_release tests.test_r67o_iso tests.test_r67o_tail_elf
```
