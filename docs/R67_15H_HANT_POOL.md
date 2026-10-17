# r67.15h H.A.N.T. viewport pool

## Change

The H.A.N.T. viewport can display more rows than its original 16 text handles.
At the native 16-pixel row pitch, five-pixel scrolling admits 19 rows in the
strict `89 < Y < 383` viewport. The old pool ended at the state halfword, so
the seventeenth eligible row read state value 5 as a text handle.

The earlier 15g Help layout model's 16-row viewport assumption is not a native
safety bound. Blank records also consume handles. Its `(rows-16)*16` scroll
model must not be reused as proof of runtime coverage: native scrolling uses
five-pixel updates and a separately derived 21-based extent. The 15h tests use
the traced native bounds, including the terminal clamped step.

This transform moves only the H.A.N.T. pool to owner offset `0x1A94`, expands
the owner allocation to `0x1AE0`, and uses 19 handles. Existing state, mode,
row records, positions, colors, icons, and scroll behavior keep their offsets
and native logic. Reset and fade loops cover the expanded pool. A full pool
skips the current row before reading a handle and advances the row index
without consuming a pool slot. A null child similarly consumes its row slot
but skips all three text setters.

The viewport checks the total row count against the native 80-record storage
limit before reading any row coordinates. Oversized or malformed counts exit
the viewport. Failed owner allocation reaches the original zero-return
epilogue; successful allocation clears the relocated pool before child
creation so partially failed child creation leaves null slots.

## Build and ownership

`tools.r67_15h_hant_pool.build(source)` is import-safe and has no filesystem or
emulator effects. It accepts the UI-transformed ELF as input, appends its small
pool initializer after the UI payload, updates the translation segment file
size, and reports the exact appended extent and modified existing-byte offsets
for the component auditor. Its source instruction preimages and write ranges
are pinned; its row-pitch geometry is pinned to the native 16- and 21-pixel
producers.

## Verification

The targeted Unicorn suite executes the original 17th-visible-row failure and
the patched viewport, including 19 emitted rows and their coordinates, exact
Y-boundary exclusions, null child handling, reset and fade coverage, row-count
boundaries, state/metadata canaries, and 5-pixel sweeps of all four current
Help page sizes at both pinned native pitches through their terminal scroll
bounds. It also executes
the pool initializer and the owner-allocation failure path. The composed UI
then H.A.N.T. output passes the existing exact-delta component auditor.

Run the focused suite with:

```sh
uv run --quiet --python /opt/homebrew/bin/python3.14 --with pillow --with numpy --with unicorn --with capstone --with opencv-python-headless --with UnityPy python -m unittest tests.test_r67_15h_hant_pool -q
```

## Limits

This is static binary and emulator-harness evidence. It does not establish
gameplay behavior, child teardown/leak behavior, or release approval. The
reported later door/loading stall remains unconfirmed as a consequence of this
pool bug and is not claimed fixed.
