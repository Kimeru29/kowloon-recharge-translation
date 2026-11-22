# r67.15l native coverage

`tools.r67_15l_native_coverage.verify(elf: bytes) -> dict` is the static native
coverage gate for the r67.15l release builder. It accepts only the approved
r67.15k ELF (`fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d`)
and fails closed on any executable drift or missing native anchor:

```python
from tools.r67_15l_native_coverage import verify

native_proof = verify(installed_elf)
```

The checked evidence snapshot is
[`translations/r67_15l_native_coverage.json`](../translations/r67_15l_native_coverage.json).
Regenerate it from the approved local ELF with
`python -m tools.r67_15l_native_coverage --output translations/r67_15l_native_coverage.json`.

## What is covered

- The constructor/callback/destructor and private-data anchors for the shared
  Kanjo input owner, the Kanjo sub-owner, and the ADV emotion task.
- A direct-call census over executable ELF load segments for the three
  constructors, wheel mapper, and outcome path. Callback pointer words are
  listed separately; they are not misreported as direct calls.
- The eight default selection slot values, bounded phase-two mapper JAL, and
  the native sprite initialization ID sequence. Position-to-selection IDs
  are reported in native order `[8, 1, 2, 3, 7, 5, 6, 4]`; command modes
  `1..8` are separately shown as `0x100..0x800`.
- Native result branches `0x100..0x800` are checked at their command stores
  (`+0x9e`), sprite-ID arguments, and calls to `0x107d60`. The IDs map through
  group 1 descriptors 88–95 to texture 8's 41-frame glow resources and their
  first-frame UV cells. The resulting ordinary/default label order is
  `JOY, LOVE, SOMBER, GRIEF, COLD, ANGER, AMITY, HOT`. The corresponding default
  event-slot values are `[8, 1, 2, 3, 7, 5, 6, 4]`. The matching wheel
  positions are pinned from native coordinate setup instructions:
  `1=(257,311), 2=(257,281), 3=(227,341), 4=(197,341), 5=(257,371),
  6=(257,401), 7=(287,341), 8=(317,341)`.
- The eight event-result branches load private slot offsets `+0x0a..+0x11`,
  store the selected byte at `+0x327e`, and feed the shared outcome routine.
  Mode zero initializes the default event-slot values. A nonzero scenario mode
  branches around those writes, so the default label-to-slot crosswalk does not
  apply to forced modes that retain caller-provided slots.
- Wheel initialization reads scenario mode at private `+0xf6`. Mode zero uses
  the ordinary initialization resources 31–34 for indices 12–15. Forced modes
  1–8 calculate resource IDs with
  `0x6d + 4 * (mode - 1) + (init_index - 12)`, covering paired-plaque IDs
  109–140. Completion glow resources use `mode + 0x57`, covering IDs 88–95.
  Input comparisons are pinned as masks `0x1000`, `0x8000`, `0x4000`, and
  `0x2000`; the report does not assign direction names. Strength reads private
  `+0x96` and checks `< 5`.
- The frame labels for IDs 53–60 and the Japanese native command strings are
  separately catalogued. The selector-to-glow crosswalk uses the explicit
  result branch and descriptor path, not a guessed text-string join.
- The mapper's nine raw words at `0x77c260`, pinned against the exact target
  sequence `0x154940, 0x1548c0, ... 0x154930` and a table SHA-256. Its mode
  zero and out-of-range modes use the fallback halfword at private `+0x9e`.
- The upstream state handler at `0x25a480`: its six state-table targets,
  state-zero task creation call `0x25a58c → 0x258700`, task registration
  (`adv emotion task`, callback `0x258040`, destructor `0x2586d0`), and the
  task pointer/active stores at GP `-0x1d68` (`+4`, `+8`). There are no direct
  JAL callers to `0x25a480` in executable PT_LOADs. Its script/opcode entry
  remains unresolved.
- The separate scenario constructor at `0x25a940`: all 15 direct JAL callers,
  the `y_AdvMain.c` source-name anchor, and both scenario registrations through
  `0x1a1190`. The callback LUI/ADDIU pairs are decoded and checked as
  instructions, including their signed low immediates: `adv scenario proc`
  resolves to `0x25a340`, and `adv scenario draw` resolves to `0x25a480`, the
  state handler itself. Signed `ADDIU` low-immediate semantics are required to
  resolve the split pointers correctly. The constructor registration and
  handler-to-task path are byte-pinned, but no complete event/script trace
  closes every runtime route.
- The task callback's eight command branches and native format strings are
  reported without equating Japanese text to art labels.
- Group 1 resource descriptors: all 146 records and all 820 frames, including
  each raw descriptor SHA-256, texture index, dimensions, pivot, UV rectangle,
  angle, and scale fields.
- The four dynamic wheel descriptors (IDs 31–34), their texture indices and
  pixel crops, plus the single-label resource IDs 53–60.
- The native group lookup instructions and the chain from the group index
  table through group 1's `BLBRD/B_GP001.BIN` filename pointer to all eleven
  `BLBRD/GRP001/GP001_00..10` resource names and their pointer array.
- The approved k ISO source range for `B_GP001.BIN`: absolute offset
  `0x2ed7a800`, length 603,520 bytes, SHA-256
  `895f3d1864a653b3eb76a06eae8b8ea65b9f31cfe156fe922eb72d9eeb967942`.
  A regression reads and hashes that bounded range, independently of the
  ELF-only `verify` API. The ISO identity is the approved k lock
  `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`.

The resource path/name/table locks connect native group loading to the actual
container name consumed by the release patch. The release builder should retain
the exact `verify(elf)` result alongside its independent container preimage,
replacement-byte, and whole-disc audit results. The 116 matching `B_GP*.BIN`
files in disc inventory are an inventory count; they do not prove those files
are all distinct wheel routes or contain equivalent wheel resources.

## Coverage boundary

`execute_selection_mapper(elf)` is an optional function-level Unicorn harness
for the ordinary MIPS routine at `0x154880`. It executes completed modes 0–8,
out-of-range modes 9 and -1, and unfinished states `0x12` and `0x14`; it checks
return values and that unfinished calls leave the output halfword untouched.
The fallback test seeds private `+0x9e` with `0x3456`. This bounded run checks
the actual selector code/table only. The native not-ready return contains one
MIPS III `DADDU v0,zero,zero` at `0x154954`; because Unicorn's MIPS32 core
rejects that instruction, a code hook emulates only its exact zero-result
semantics and advances to the native return instruction. The ELF bytes remain
untouched. The run does not execute wheel initialization, graphics, task
scheduling, event delivery, or gameplay.

This is static executable and resource-binding coverage. The JAL scan is limited
to executable PT_LOAD segments, and it cannot close indirect callback or actor
registration, dynamic event dispatch, or every reachable gameplay route. The
scenario constructor call census and both split-immediate callback registrations
are now pinned, while the incoming script/opcode route to `0x25a480` remains
unresolved. The eight-slot order and phase-two call are pinned as data and
instructions. This does not validate a patched art payload, GPU output,
complete game runtime, or gameplay acceptance. The texture patch and its
source/art pixel tests remain owned by the art agent. No PCSX2 state, settings,
memory cards, or savestates were changed; Unicorn is used only for the bounded
native function check above.
