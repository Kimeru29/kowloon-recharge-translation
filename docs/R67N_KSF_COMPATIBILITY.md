# r67.15n KSF choices

The PS2 reader locates scenario records by ordinal and scans a variable-length record. Each active choice has 30 inline bytes and needs a NUL inside those bytes. The historical importer instead measured from the start of a label to the next nonzero byte. That can include later flags or another record header. The diagnostic overlay restores eleven malformed pre-existing choices from pristine disc data. The source images and executables remain intact. This is static validation only.

## Coverage

| Population | Result |
|---|---:|
| Entire retail ADV KSF tree, exact EOF walks | 1,516 files |
| Active physical labels in retail, all NUL-terminated in-field | 1,136 |
| Exact PS2 and PS4 mapped files | 144 |
| Official keys aligned to active choices in those files | 920 |
| Inherited official choices fitting the accepted space convention after repair | 857 |
| Historically approved constrained DG00 choices retained | 2 |
| Previously unresolved fullwidth-space rows proven exact without a write | 4 |
| Previously reported overflows retaining Japanese | 46 |
| Newly identified malformed inherited fits restored to Japanese | 11 |

The older 48 overflows include the two DG00 exceptions. The recovered raw maps use runs of spaces on 728 of 920 rows. Under the accepted convention that collapses repeated ASCII spaces, 59 full labels exceed 29 bytes, comprising those 48 plus the 11 unsafe prior imports. Preserving every raw source space puts 112 over the limit. The old 48 consume 31–48 bytes normalized and 35–56 bytes raw. No tested row can reclaim inline space from an adjacent field. The 216 remaining physical retail labels sit outside this exact-map population and may include duplicate wording and structurally different remaster counterparts.

## Record and renderer evidence

All native addresses below are PS2 EE virtual addresses. The first load segment maps VA `0x100000` to ELF file offset `0x80`. The evidence JSON records the exact address ranges, file offsets and SHA-256 digests checked across all three executables.

| Native operation | Evidence |
|---|---|
| Select the KSF | `0x215648..0x215658` formats `adv/%s.KSF`. `0x2156b0..0x2156c8` formats the numbered scene name. `0x22c0b4` retrieves the loaded buffer, stored at scenario state `+0x3158` by `0x22c0c0`. `0x22c0fc` reads the first little-endian 16 bits as the count. |
| Locate a scenario | `0x22d0b0` masks the ordinal to 16 bits, starts at file +2 and advances once for each preceding record. Its direct callers in the inspected code are `0x22c0d0`, `0x22c260`, `0x22c2f0`, `0x22c508`, `0x22c5a4`, `0x22c87c`, `0x22cbac`, `0x22cebc` and `0x258598`. |
| Skip the fixed part | `0x22d0c8`, `0x22d0d8..0x22d0ec` and `0x22d100..0x22d114` advance 38, five times 30, then nineteen times 112 bytes. The first choice flag is at record +`0x90c`. |
| Skip the variable tail | Four flag bytes are always counted. For slot `i`, `0x22d12c..0x22d144` probes record + `0x90c + 31*i` and adds exactly 30 when the byte equals one. Physical records have consecutive active flag + payload pairs followed by any inactive flag bytes. The parser verifies the computed native next-record size against the packed size before advancing to any following record. A guessed byte-offset pointer table is unnecessary. |
| Assemble choice text | `0x22c2e8..0x22c30c` obtains the current record and requires type 2 for this branch. `0x22c338..0x22c340` checks the flag, `0x22c384..0x22c388` copies from flag +1, and `0x22c400` advances 31 after an active entry. Four iterations terminate at `0x22c408`. The copy at `0x39f708`, including its byte loop at `0x39f7f8..0x39f810`, stops at a zero byte. |
| Store and preprocess | `0x22c364..0x22c378` clears 101 scratch bytes at stack +`0x90`; `0x22c394` calls `0x24d5a0`, which also uses 101-byte scratch buffers. `0x22c39c..0x22c3c0` copies into state +`0x298 + 108*i`. The four rows end before max-length state at `+0x444` (the measured stride alone does not establish all 108 bytes as text). `0x22c3d4..0x22c3fc` records the longest string's byte count. |
| Draw and animate | `0x2514d4..0x25150c` halves the max byte count for layout. `0x251650..0x2516a8` preprocesses and supplies a 101-byte scratch string to the text setter. `0x2516cc..0x2516f8` passes floor(byte length / 2) to `0x18c670`. It allocates `0x98` bytes and initializes two adjacent 16-pointer blocks at `+0x18` and `+0x58` (`0x18c6a8`, `0x18c73c`, `0x18c75c..0x18c774`). The callback writes a handle to `+0x18 + 4*i` at `0x18c8d0`, comparing `i` only with the supplied count at `0x18c8d8..0x18c8e0`. |

A side lookup keyed by the current KSF filename and the label offset could supply a different text pointer at `0x22c384`. The parser and choice IDs could in principle stay unchanged. The renderer remains a distinct blocker. From 34 input bytes onward the callback writes past its first 16 declared handle slots and into its adjacent pointer block. All 48 historical overflows with raw spacing and 29 with normalized spacing cross that boundary. No clipping, cursor alignment, complete ASCII glyph coverage or safe longer-handle ownership was established. A general change would need a choice-specific renderer fix and runtime acceptance. The release includes only the source-proven data correction.

## Safety fallback

All 1,516 KSF payloads on k and m were byte-identical. Replaying the old importer reproduces 143 exact mapped files byte for byte. The remaining file, `DG/DG00_00.KSF`, also matches after applying its hash-pinned approved manifest. The two 28-byte DG00 exceptions at keys 9339 and 11689 remain NUL-terminated in their own fields.

| File | Unterminated key(s) | First NUL distance(s) in m | Structural bytes restored |
|---|---|---|---|
| `DG/DG06_00.KSF` | 2350 | 31 | 2380 |
| `FN/FN12_16.KSF` | 39559 | 51 | None, read crossed the next active label |
| `MS/MS03_03.KSF` | 134889, 251250 | 55, 33 | 251280; first read crossed the next active label |
| `MS/MS06_02.KSF` | 83670 | 33 | 83700–83702, including next record byte 0 (`79` → `00`) |
| `MS/MS10_01.KSF` | 51130 | 33 | 51160–51162, including next record byte 0 (`65` → `00`) |
| `MS/MS10_02.KSF` | 4670 | 30 | None, read used the inactive flag's NUL |
| `MS/MS10_03.KSF` | 153150, 169510, 299701 | 30, 32, 34 | 169540–169541 and 299731–299733, including next record bytes 0–1 (`6f 6d` → `00 00`) |
| `MS/MS11_03.KSF` | 69810 | 32 | 69840–69841 |

Each fallback restores its 30-byte pristine payload and only the neighboring structural bytes altered by the replayed historical write. Across eight files this changes 345 bytes, including 11 inactive flag bytes and four following record-header bytes. Record boundaries did not drift on these baselines, although the previous executable could read the changed header values and over-read label boundaries. No English substitution or shortening was introduced. Every final structural byte and unmapped choice matches pristine, and every mapped output has an in-field NUL. Generated outputs match independent in-memory reconstruction SHA-256 values.

## U+3000 verification

The four values in `MS/MS09_03.KSF` occupy the four active slots of record 50 (zero-based). Keys 118379, 118410, 118441 and 118472 contain respectively 4, 6, 3 and 5 repetitions of U+3000. CP932 encodes each as `81 40`. The PS4 English map, PS4 template, pristine PS2, k and m already agree byte for byte on each text plus terminator. The finding establishes their exact content. Their visual function was not tested.

## Artifacts and reproduction

`local/r67n-research/ksf-evidence.json` records every exact-map key, raw official string, source text, footprint, hashes, and native anchors. Its safety fallback section pins pre/post file and field bytes. `local/r67n-ksf/report.json` is the generator's independent result with the 920 per-key classification, hashes and ranges. `local/r67n-ksf/overlay` contains precisely eight ADV-relative files. Source ISO SHA-256 is `29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476`, k is `ad706667ff82b3e3374ada0426193f8527c6af3714ed7462b5db05166d509b53`, and m is `3ad3945909d6764388984c9ae1c8796b0f4c4713ac918a5345a411c99ba22a6f`. The separately verified k ELF SHA-256 is `fb359414f16e2b7e9bbd5de7b349802c3e2653c0c30a488550dc3427ce2b917d`.

```sh
python3 -m tools.r67n_ksf \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --installed-iso local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso \
  --output local/r67n-ksf
python3 -m unittest tests.test_r67n_ksf tests.test_ksf_import tests.test_ksf_corpus_import tests.test_ksf_report
```

16 focused tests passed, including complete-source reproducibility, stale-output rejection and native-anchor drift detection. Input inventory SHA-256 is `98d47250eae57a9ae34dc1da11f5cb9da1d196a530a3a90047e31c96bd9a089e`. Overlay inventory SHA-256 is `ccb9eb4a16313f75341a609bb09f69ac2e340006f558dcf5d58679f7bc7e2d71`.

## Additional official choices from structurally changed files

The original exact importer omitted 169 official DC entries in 20 nonidentical KSF assets. The new `tools.r67n_ksf_structural` compares complete native event records at the same scenario ordinal and choice index. It requires byte-identical fixed metadata, flags and all Japanese label payloads, verifies that each key begins an active PS4 field, and retains the pristine PS2 file as its installation preimage. This proves 126 records; 116 official strings fit the 29-byte plus NUL limit and are installed across 15 files. Ten proven strings exceed capacity, and 43 entries lack complete record correspondence. No operand or text normalization establishes a match. Only the established repeated-space display convention is applied to the proven official English.

`local/r67n-ksf-structural/report.json` contains every one of the 169 entries, source/map/output hashes, original record and choice indexes, field offsets and exact context evidence. Reproduction requires a fresh directory:

```sh
python -m tools.r67n_ksf_structural \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --installed-iso local/r67m-integration/release-pinned-20261031/67.15m-cumulative-script-wheel.iso \
  --output local/r67n-ksf-structural-reproduction
```

Across all 1,089 mapped KSF entries the final inventory distinguishes 973 installed official choices, four official blank no-ops, two inherited approved constrained choices, 56 over-capacity official strings, eleven safety fallbacks and 43 unresolved record correspondences. The latter two Japanese populations are not classified as PS2-exclusive.
