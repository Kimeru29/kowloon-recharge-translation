# Choice correspondence across PS2 and PS4 KSF records

Of the 43 historical KSF keys held for record mismatch, **37 keys across 16 type-2 records** have source-proven choice identity. The six remaining keys belong to PS4 `MS/MS01_03.KSF`. Their numbered PS2 records lack active choices. The PS2 root program cannot supply the missing matches because its active chapter has different MTX context. This tool writes a proof report only.

| Native PS2 KSF | Chapter ordinals | Proven keys |
| --- | --- | ---: |
| `DG/DG13_02.KSF` | 10 | 2 |
| `MS/MS01_00.KSF` | 22, 47, 60, 78, 182, 216, 233, 237 | 19 |
| `MS/MS04_01.KSF` | 166 | 2 |
| `MS/MS13_00.KSF` | 11, 13, 37, 41 | 8 |
| `MS/MS13_03.KSF` | 0, 12 | 6 |

The analysis verifies all 20 KSF files and all 169 histories from the prior structural pass against the official DC arrays and installed n resource digests. It checks only the 43 previously recorded mismatches for new correspondence.

## Native and source evidence

The numbered loader constructs names such as `adv/ms/MS01_00.KSF`. The KSF reader at `0x22c2e8` asks the native record walker at `0x22d0b0` for the current chapter ordinal. For type 2, the label loop accepts exactly flag value 1 at `0x22c338..0x22c340`, passes `flag+1` to the copy routine and advances by 31 bytes for an active slot. Eight proven records include a nonzero inactive packed byte. The proof retains those bytes and requires exact agreement across source and installed records.

For each record the analysis requires:

- The same live chapter ordinal and MTX pointer-slot tuple, including all aliases. The entire Japanese and control byte region must match. The region can reside at a different offset in each port.
- Identical type-2 KSF header bytes through offset `0x26` exclusive. The resolver at `0x22c598..0x22c7dc` handles default, alternative and conditional record links and passes the chapter ordinal to `0x215820` for MTX pointer resolution. The proof also compares the five conditional link halfwords.
- Exact packed flags and every active sibling in slot order. Thirty-five Japanese fields match all 30 bytes literally. The two fields in `MS04_01.KSF` chapter 166 use `革ジャン` in PS2 and `皮ジャン` in PS4, both denoting a leather jacket. The exception is bound to both original KSF digests, that chapter, those two slots and an exact match of the remaining 28 bytes.
- The exact full installed n record preimage, including the header, effect bytes, packed flags and every 30-byte payload. The proof lists all original PS2-to-PS4 record difference ranges, including effect data. The source records are read-only.

The report keys an official label by DC path, original array index and numeric key. It records the native request name, installed header and payload offsets, exact packed flag bytes, original and installed preimages, and source record and MTX evidence. The renderer can look up the text through the pinned DC asset and use the complete sibling preimages as its record guard.

## Rendering census

The 37 labels use glyphs already present in the existing style-0 choice census, with no additional name markers. The longest is `MS01_00.KSF` key 111480 at 52 logical cells and 92 bytes in the approved mixed representation. Eleven labels wrap. The maximum including a display-only line break is 93 bytes, with measured lines at most 448 pixels wide. These values fit the existing renderer's 56-cell and 100-byte limits. In-game presentation remains unverified by this proof.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m tools.r67o_choice_correspondence \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --baseline-iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --historical-report local/r67n-ksf-structural/report.json \
  --output-dir local/r67o-choice-correspondence-reproduction

PYTHONDONTWRITEBYTECODE=1 local/r67m-integration/venv314/bin/python -m unittest \
  tests.test_r67o_choice_correspondence tests.test_r67n_ksf \
  tests.test_r67n_ksf_structural tests.test_ksf_import
```

The report SHA-256 is `fd5a25976b29dc2fec00c43e9f53309a73121e401be6af479a5ec61514201a35`.
