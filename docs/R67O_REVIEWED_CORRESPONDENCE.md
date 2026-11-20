# r67.15o inherited MTX correspondence

The verifier establishes source correspondence for nine official DC entries in seven historical MTX clusters. It reads the original PS2 and PS4 sources, the finalized r67.15n inventory, and the supplied ISO. It writes a fingerprints-only report. These nine entries are already installed, and verification writes no game payloads. Gameplay reachability and approval require separate runtime evidence.

| Native MTX | PS4 span | PS2 span | DC keys | Source difference |
| --- | --- | --- | --- | --- |
| DG/DG13_02 | 7088–7125 | 7088–7127 | 7088, 7113 | PS4 missing a kana and line break placement differs |
| FN/FN13_16 | 1646–1691 | 1646–1691 | 1646 | Orthographic choice for the same verb |
| MS/MS05_01 | 28761–28787 | 28761–28785 | 28761 | PS4 extra particle |
| MS/MS05_03 | 8738–8767 | 8738–8767 | 8738 | Ruby readings differ over identical base characters |
| MS/MS05_03 | 16985–17043 | 16985–17048 | 16985, 17002 | Colloquial glyph, verb spelling, and ruby display |
| MS/MS06_01 | 10651–10676 | 10651–10678 | 10651 | PS4 missing a kana |
| MS/MS11_03 | 7267–7304 | 7267–7306 | 7267 | Ruby readings differ over identical base characters |

All byte ranges are half-open. The exact ranges and official DC group ordinals came from the historical structural report. The map hashes, installed file hashes, and offsets came from the final r67.15n inventory, cross-checked with the historical semantic-entry research. The verifier fixes the correspondence scope in code and rederives the source fingerprints on each run.

The source check decodes CP932, recognizes the native display break `r` and ruby markup `l漢字(読み)`, then keeps the ruby base. Each explicitly reviewed PS4 spelling or typo substitution must occur once in its own cluster. The resulting Japanese must match the PS2 code points exactly. The source spans must occupy the same MTX pointer-table slots and retain the exact native boundary controls at both ends. Raw boundary hashes pin each platform's start-left, start-right, end-left, and end-right bytes in that order, including the known terminal NUL padding after the DG boundary.

The installed check reads each affected MTX through the ISO's current DATA.CVM filesystem and verifies its whole-file hash. Each DC key must match the original array index and group geometry. Each English line must match the pinned inventory fingerprint and the encoded official map value at its exact installed offset. The report records absolute ISO positions from the supplied image.

```sh
local/r67m-integration/venv314/bin/python -m tools.r67o_reviewed \
  --iso local/r67n-release/67.15n-official-script-diagnostic.iso \
  --ps2-adv local/r67n-sources/assets/ADV \
  --ps4-adv local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV \
  --inventory local/r67n-inventory-final \
  --output local/r67o-reviewed/report.json
```

This verifier uses the unchanged r67.15n image and its final inventory. Speaker-label replacements in r67.15o move some installed ranges, so the r67.15o inventory separately projects these nine proven entries through the verified MTX edits and rereads their final bytes from the candidate. Do not run the baseline verifier against relocated files using the old whole-file hashes. Each baseline report entry carries the original inventory fields plus `correspondence_id`, `status`, and `proof`. `correspondence_id` joins the entry to its cluster record. The report's `iso_sha256` and `manifest_sha256` identify the baseline image and fingerprint manifest.
