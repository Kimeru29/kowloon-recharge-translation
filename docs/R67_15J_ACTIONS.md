# r67.15j action-label provenance and limits

## Scope

`tools/r67_15j_action_labels.py` redirects native text pointers to append-only
PS2-font encodings of unique exact rows from the owned CUSA27034 PS4
`English.bytes` corpus. The corpus remains external to the repository and is
pinned by SHA-256 `b8eb78a98bf9e4cde1b76887daa740ebeb7f9f856780bafdd9da1317aec6a17b`.

The builder composes over other appended ELF modules. It validates the current
PT_LOAD shape, each source pointer and string (or an already translated exact
string), the official corpus rows, and explicit dungeon sentinels. It does not
require a whole-image source hash. `ALLOWED_SOURCE_RANGES` contains only the
half-open pointer-word ranges owned by this patch; PT_LOAD `p_filesz` at
`0x64..0x68` is separate metadata. Any unrelated input changes are retained.

## H_Item selector and constructor path

The 16-entry action pointer table begins at file offset `0x386320` (runtime
address `0x4862A0`). Native code at `0x114B6C..0x114B98` reads the action ID
from the live object at `+0x18`, indexes that table, and passes the selected
string to text constructor `0x189E40`. The parent action-bubble path creates
background resource types `0x5F` and `0x5E` through `0x107D60` at `0x114AA0`
and `0x114AC8`. The r67.15e/f helpers adjust only the existing Can’t (ID 1)
and Compound (ID 3) presentations.

| ID | Owner | Japanese source | Official English | PS4 record | r67.15j action |
|---:|---:|---|---|---:|---|
| 0 | `0x386320` | 交換 | Swap | `0x461D2` | Redirect |
| 1 | `0x386324` | 禁止 | Can't | `0x461E4` | Preserve r67.15e pointer/string |
| 2 | `0x386328` | 使う | Use | `0x461F7` | Redirect |
| 3 | `0x38632C` | 調合 | Compound | `0x46208` | Preserve r67.15d pointer/string |
| 4 | `0x386330` | リロード | Reload | `0x4621E` | Redirect |
| 5 | `0x386334` | 使用不可 | Not usable | `0x46238` | Redirect |
| 6 | `0x386338` | 飲む | Drink | `0x46256` | Redirect |
| 7 | `0x38633C` | 飲む！ | Drink! | `0x46269` | Redirect |
| 8 | `0x386340` | 食べる | Eat | `0x46280` | Redirect |
| 9 | `0x386344` | 食べる！ | Eat! | `0x46294` | Redirect |
| 10 | `0x386348` | なめる | Lick | `0x462AC` | Redirect |
| 11 | `0x38634C` | 充電 | Charge | `0x462C1` | Redirect |
| 12 | `0x386350` | 治療 | Cure | `0x462D5` | Redirect |
| 13 | `0x386354` | 使用 | Use | `0x462E7` | Redirect |
| 14 | `0x386358` | 自室収納 | Room storage | `0x462F8` | Redirect |
| 15 | `0x38635C` | 置く | Place | `0x46318` | Redirect |

All 16 source keys have one exact official row. IDs 1 and 3 are verified and
left byte-identical at their owners. The existing item-card title budget of
196 px, 16 px base glyph advance, 8 px halfwidth-space advance, and 18 px line
height belongs to the separate title path (`0x10DAC4` / `0x189E40` wrapper in
r67.15f); it is not evidence that these action captions fit their bubbles.
The separate layout component measures the native type-0x5E frame: width 96,
pivot X -29, caption origin +51. Its 66px budget reserves an 8px right inset.
IDs 1 and 3 retain their accepted geometry; all other captions use the bounded
instance-only fitter. Full official names remain intact.

## Dungeon action options

The dungeon option data spans pointer fields `0x594F84..0x594FBC`; aliases
remain explicit. M_ObjDtl creates its action animation at `0x29B2C8`.
The nearby `0x2A6040`/`0x2A6060` path belongs to item-use names and is not
evidence for the bounds or scaling of these action options. No hook into that
unrelated path is authorized by this pointer patch.

| Owner | Source / existing label | Official English | PS4 record | Status |
|---:|---|---|---:|---|
| `0x594F84`, `0x594F88` | つかむ / Grasp | Grasp | `0xD0B41` | Preserve existing 14y translation |
| `0x594F8C` | 取る | Take | `0xD0B57` | Redirect |
| `0x594F90`, `0x594F94`, `0x594FAC` | 開く / Open | Open | `0xD0B69` | Preserve existing English aliases |
| `0x594F98` | 開錠 | Unlock | `0xD0B7B` | Redirect |
| `0x594F9C` | `0x795B9C` | — | — | Empty sentinel; preserve |
| `0x594FA0` | アイテムを使う / Use Item | Use Item | `0xD0B8F` | Preserve existing English |
| `0x594FA4` | 地上へ帰還する | Return Above | `0xD0BB4` | Redirect |
| `0x594FA8`, `0x594FB4` | 触れる | Touch | `0xD0BDD` | Redirect both aliases |
| `0x594FB0` | 記録する / Record | Record | `0xD0BF3` | Preserve existing 14y translation |
| `0x594FBC` | 入る | No exact key | — | Preserve; report unresolved |

`0x594F80` is a second `0x795B9C` empty sentinel and is guarded too. The
official corpus has no exact Japanese-key row for `入る`; r67.15j leaves its
native pointer unchanged. It does not infer an English phrase from nearby
options.

## Fit and runtime limits

Official provenance proves wording, not geometry. The integrated release adds
per-owner fitters and tests their output with the original native glyph builder.
The dungeon action frame is group 2/type 0x9D; its 164px caption budget preserves
the original left edge. The source-only label report still marks layout as a
separate responsibility; the following components provide that proof. Neither
component claims gameplay or GPU rendering approval.

The dungeon block also contains inline Japanese backing bytes at
`0x594F50..0x594F7A` for Use Item, Return Above, and Record; their registered
pointer owners are `0x594FA0`, `0x594FA4`, and `0x594FB0`. Those bytes remain
unchanged. `0x594F4C` is a separate pointer to `ゆうなぎ　やまと`, outside the
action-option table.
