# r67.15o ADV speaker headers

The speaker overlay projects 7,402 fixed official English headers into 478 staged ADV MTX files. It preserves each body, control sequence, pointer slot, and alias. It starts from 1,516 MTXs extracted from the exact r67.15n ISO with the three verified r67.15o bundle and KWLNSCR payloads already applied.

## Official source and native role

Each of the 214 accepted Japanese-to-English pairs has a complete CP932 bracket label associated with one official bracketed PS4 DC row immediately before a native `r`. The source census covered 1,028 PS4 MTX/DC sibling pairs. `FN/FN02_31.MTX` has duplicate DC keys and contributes no eligible whole-group proof. `【荒吐神】` has a non-header DC presentation. The report records PS4 paths, hashes, group keys, and exact source spans.

Six Japanese labels share three English reverse keys and stay unresolved. Native replay identified different actor/alias results for the two spellings of Madame Butterfly and for the two masked male student labels.

| Official English label | Excluded Japanese labels |
| --- | --- |
| Madame Butterfly | `【マダムバタフライ】`, `【マダム・バタフライ】` |
| Masked male student | `【覆面の男子生徒】`, `【覆面の男生徒】` |
| Students | `【生徒たち】`, `【生徒達】` |

The ADV dispatcher routes CP932 `81 79` to the bracket speaker path at `0x250B10`. A projected span is complete within a single pointer region and follows a pointer start, a recognized initial command run, or a recognized run containing the native `wc` page flush. It ends before the native `r`, optionally followed by body `px` or ruby control. The command matcher accepts a conservative subset of observed runs. The report holds 55 otherwise source-proven occurrences with unconfirmed dispatch boundaries and records additional headers with no official proof. These counts describe fixed bracket candidates.

## Native identity

The parser at `0x250530` writes the visible normalized header to global ADV state `+0x198`. Its two identity calls at `0x2506BC` and `0x2506E4` strip the outer brackets into 29-byte local buffers and search the stock Japanese alias table. A direct English substitution can lose the actor and alias column. It can also overrun these local buffers when the stripped English body exceeds 29 bytes.

Two leaf bridges redirect only those calls. Each validates a complete NUL-terminated CP932 header within 100 bytes. An exact, bidirectionally unique English key supplies the original Japanese lookup representation and tail-calls the original actor or alias lookup. The stock parser normalizes eleven accepted Japanese strings using its 24-entry glyph conversion table. The reverse table stores that exact representation, as checked by executing the stock parser. Every accepted English tag is unchanged by the native display normalizer. Unknown tags can enter stock lookup only when their stripped length is at most 28 bytes. Malformed, oversized, or unterminated tags return `-1` directly.

The private Unicorn harness uses the existing `NativeTextPipeline` SQ/LQ compatibility and the stock byte-string paths for EE libc. Both native lookups executed for all 214 pairs with byte-identical normalized Japanese inputs and identical stock actor/column outputs. Eighty-four labels resolved to nonnegative actor and alias IDs. The harness also checks original Japanese fallback behavior, the six ambiguous source labels, bounded malformed/long inputs with stack and register canaries, and the actual native `px` arm with default and custom name fields.

## File ownership and verification

The combined ELF starts with the verified choice component. Speaker writes are the translation PT_LOAD file size at offset `0x64`, JAL words at offsets `0x15073C` and `0x150764`, and a new extent from `9074704` through `9087919`. The stock speaker parser, display buffer, original lookup routines, and original alias table remain in place.

The MTX report records preimages and relocated spans with source and native-identity references. Each pointer region is checked against the original with only the named replacements and verified alignment NULs. `FD/FD00_20.MTX` has a WC-only final region. Its aligned prefix is compiled with the standard MTX writer and the final body is replayed at the relocated last pointer with no extra trailing padding. The overlay retains the original end control.

The longest label is the complete 34-cell `【Voice speaking in broken English】`. The report flags labels longer than the largest original Japanese header for in-game visual review. Header fit, scene playback, and custom-name gameplay still need PCSX2 verification.

## Reproduce

Run from the checkout with the established Python 3.14.7 environment and source assets. Use a new output directory for every run.

```sh
local/r67m-integration/venv314/bin/python -m tools.r67o_speakers \
  --elf local/r67o-choices/67.15o-ksf-choice-diagnostic.elf \
  --base-elf local/r67n-release/67.15n-official-script-diagnostic.elf \
  --choice-report local/r67o-choices/report.json \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --script-root local/r67o-speaker-inputs/ADV \
  --script-provenance local/r67o-speaker-inputs/provenance.json \
  --output-dir local/r67o-speakers
```

The command revalidates the official inventory, staged hashes, ELF ownership, and native identity before emitting `patched.elf`, `overlay/`, and `report.json`.

```sh
local/r67m-integration/venv314/bin/python -m unittest -v \
  tests.test_r67o_speakers tests.test_r67o_speakers_native
```
