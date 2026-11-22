#!/bin/zsh
set -eu
# Run from the repository root. Arguments are owned sources and a fresh destination.
# PYTHON defaults to the existing pinned environment; it may name another equivalent 3.14.7 runner.
if [ "$#" -ne 6 ]; then
  echo 'usage: reproduce-r67n.sh PS2_ADV PS4_ADV BASELINE_M_ISO HISTORICAL_STRUCTURAL_REPORT STARTUP_GRAPHICS FRESH_RUN_DIR' >&2
  exit 2
fi
r67n_python="${PYTHON:-$PWD/local/r67m-integration/venv314/bin/python}"
r67n_ps2="$1"
r67n_ps4="$2"
r67n_baseline="$3"
r67n_historical="$4"
r67n_graphics="$5"
r67n_run="$6"
export DEVELOPER_DIR=/Library/Developer/CommandLineTools
export PYTHONDONTWRITEBYTECODE=1
test ! -e "$r67n_run"
mkdir -p "$r67n_run"
"$r67n_python" -m tools.r67n_partial_corpus --ps2-adv "$r67n_ps2" --ps4-adv "$r67n_ps4" --output-dir "$r67n_run/partial"
"$r67n_python" -m tools.r67n_names --ps2-adv "$r67n_ps2" --ps4-adv "$r67n_ps4" --baseline-iso "$r67n_baseline" --historical-report "$r67n_historical" --output-dir "$r67n_run/names"
"$r67n_python" -m tools.r67n_ksf --ps2-adv "$r67n_ps2" --ps4-adv "$r67n_ps4" --installed-iso "$r67n_baseline" --output "$r67n_run/ksf"
"$r67n_python" -m tools.r67n_ksf_structural --ps2-adv "$r67n_ps2" --ps4-adv "$r67n_ps4" --installed-iso "$r67n_baseline" --output "$r67n_run/ksf-records"
"$r67n_python" - "$r67n_run" <<'PY'
import hashlib,json,sys
from pathlib import Path
run=Path(sys.argv[1]);manifest=json.loads(Path('translations/r67n_script_transfer.json').read_text());expected={r['path']:r['output_sha256'] for r in manifest['assets']};seen=set()
for stage in ('partial','names','ksf','ksf-records'):
    for source in sorted((run/stage/'overlay').rglob('*')):
        if not source.is_file():continue
        rel=source.relative_to(run/stage/'overlay').as_posix().removeprefix('ADV/')
        if rel in seen:raise ValueError('Overlay collision: '+rel)
        raw=source.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected.get(rel):raise ValueError('Unproven output: '+rel)
        seen.add(rel);target=run/'overlay'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
if seen!=set(expected):raise ValueError('Overlay inventory drift')
PY
"$r67n_python" -m tools.r67n_release --source "$r67n_baseline" --output-dir "$r67n_run/release" --overlay-root "$r67n_run/overlay" --manifest translations/r67n_script_transfer.json --ps2-adv "$r67n_ps2" --ps4-adv "$r67n_ps4" --graphics "$r67n_graphics"
"$r67n_python" - "$r67n_run/release/release-report.json" <<'PY'
import json,sys
from pathlib import Path
report=json.loads(Path(sys.argv[1]).read_text());expected=json.loads(Path('translations/r67n_release_lock.json').read_text())['candidate_iso_sha256']
if report['candidate_iso_sha256']!=expected:raise ValueError('Reproduced ISO identity differs')
print('Verified deterministic r67.15n ISO:',expected)
PY
