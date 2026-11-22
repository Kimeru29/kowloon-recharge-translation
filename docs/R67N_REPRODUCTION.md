# Reproduce the r67.15n diagnostic

Use the existing isolated integration worktree and its pinned Python 3.14.7 environment. Recover owned sources into a fresh directory if temporary paths are absent; never overwrite existing sources, diagnostic images or emulator state. The baseline must have SHA-256 `3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f`. The pristine source is `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`. All per-file PS2/PS4/DC identities are in the fingerprint manifest. Equivalent source path aliases are sufficient; their contents must match.

The deliverable includes `reproduce-r67n.sh`. From the repository root, supply the two ADV directories, exact m ISO, retained historical structural import report, accepted startup graphics directory, and a new run directory:

```sh
/path/to/reproduce-r67n.sh \
  "$PWD/local/r67n-sources/assets/ADV" \
  "$PWD/local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV" \
  "$PWD/local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso" \
  /Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/startup-flow-v10/local/structural-import-report.json \
  /Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/startup-flow-v10/local/startup-graphics \
  "$PWD/local/r67n-another-reproduction"
```

The script invokes the committed partial, name, KSF safety and KSF event-record generators; rejects overlay collisions or output fingerprints differing from the release manifest; runs the existing cumulative builder and independent full-disc audit; and requires the original n ISO hash. Source data and historical reports remain read-only. Generated report output-path metadata may differ between directories; game payloads must remain identical. The script is also installed as `tools/reproduce_r67n.sh` in this branch.

To inspect the finished ISO independently:

```sh
python -m tools.r67n_inventory \
  --iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --output local/r67n-new-inventory \
  --partial-report local/r67n-partial/report.json \
  --names-report local/r67n-names-final/report.json \
  --ksf-report local/r67n-ksf/report.json \
  --structural-ksf-report local/r67n-ksf-structural/report.json \
  --structural-report local/r67m-integration/structural-report-v2.json \
  --structural-report /Users/juan.pena/repos/kowloon-recharge-translation/.worktrees/startup-flow-v10/local/structural-import-report.json
```

Require the final installed candidate in the established suite:

```sh
DEVELOPER_DIR=/Library/Developer/CommandLineTools \
PYTHONDONTWRITEBYTECODE=1 R67N_REQUIRED=1 \
R67_HISTORY_LOCK_ELF="$PWD/local/r67n-release/67.15n-official-script-diagnostic.elf" \
R67_HISTORY_LOCK_ISO="$PWD/local/r67n-release/67.15n-official-script-diagnostic.iso" \
local/r67m-integration/venv314/bin/python -m unittest discover -s tests -v
```

The source/report archive includes the exact full producer reports, native research hashes and readers, output inventory, validation logs and preservation fingerprints. It excludes game binaries and the proprietary script corpus. Those remain locally owned inputs. Static success is not gameplay acceptance; use the runtime checklist in `R67N_HANDOFF.md`.
