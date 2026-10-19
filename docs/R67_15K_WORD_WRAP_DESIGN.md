# r67.15k description word wrapping

Status: owner-local implementation and corrected release audit complete.
See R67_15K_HANDOFF.md for final verification totals and runtime limits.
Visual approval remains pending.

## Scope

The latest screenshots reject the r67.15j Item SELECT Details and dungeon
inspection body layouts. Everything else in j is user-approved and must remain
unchanged. The user booted from an in-game memory-card save, not a savestate;
the ISO was probably j but its filename was not confirmed conclusively.

Implement reusable, font-metric-driven word wrapping for these two owner
families. Preserve complete official text, untranslated fallbacks, numeric
columns, recipes, titles, action labels, HANT, doorway loading, saves, and all
previous release artifacts. No emulator/session/settings changes are authorized.

## Evidence collected

- The 41 existing j focused tests pass on the current branch. They synthesize
  glyph lists and stub the text constructor/updater. This is not a reproduction
  of the user's failure and must not be represented as one.
- Native conversion of the actual grenade and ammunition sparse strings
  produces the expected full-space, newline, and terminator controls. A
  synthetic FF10 rejection is not evidence that FF10 caused these screenshots.
- Native GP is `0x79B1F0`, not a font-data address.
- Details constructor hook is VA `0x11518C`, file offset `0x1520C`.
  The official selector is `0x975A78`; native construction is `0x189E40`.
- Inspection creates four text handles at owner offsets `0x38..0x44`.
  Its body font constructor call is `0x29ACBC`; the body reveal constructor
  call is `0x29BADC`. Native line pitch is 18 pixels.
- Native font private data: descriptor `+0x10`, origin `+0x14/+0x18`,
  constructor extents `+0x1C/+0x20`, tracking `+0x28`, line spacing `+0x2C`,
  scale `+0x48/+0x4C`, node head `+0x04`. `+0x25` is a draw conversion mode,
  not a wrapping flag.
- Native glyph builder `0x18CB50` produces four vertices at node offsets
  `0x10`, `0x50`, `0x90`, and `0xD0`; each vertex begins with float X/Y.
  Node links are at `+0x120/+0x124`, and node stride is `0x130`.
- Native draw callback `0x188420` passes those vertices to the drawing backend
  at `0x1888F4..0x18890C` when the conversion flag is zero.
- Task creation `0x1A1260` stores the callback at task `+0x34`, destructor at
  `+0x38`, and private pointer at `+0x3C` (`0x1A1378..0x1A1380`).
- Native font allocation is 0x254 bytes at `0x188B3C`. Any added owner metadata
  needs an explicitly enlarged owner-local allocation, not an unused-looking
  word or a stale global pointer cache.
- There are 431 Details catalogue entries and 600 native inspection records.
  Preserving inspection source-line boundaries can require five wrapped rows,
  so independently wrapping four fixed-Y objects would overlap them.

## Replacement contract

1. A shared pure layout policy consumes complete ordered glyph/control streams,
   owner bounds, live font dimensions, scale, tracking, and line pitch.
2. Wrap before a whole word when its last visible glyph would cross the right
   content edge. Discard only separator padding at a newly wrapped line edge;
   never discard visible characters. Existing generated Details line breaks
   can be soft boundaries; inspection fields remain paragraph boundaries.
3. Treat Japanese runs and a word wider than an entire line explicitly. A word
   cannot mathematically fit unchanged in a narrower box: tests must expose
   this condition rather than silently clipping or dropping it.
4. Measure all rows before mutation. Wrap at the requested metrics first. If
   the entire paragraph exceeds the available height, use the largest bounded
   uniform presentation factor that fits after rewrapping. Report that factor;
   do not alter the stored requested font scales, clip, or omit characters.
   Repeated draws must not accumulate scaling. This safeguard is necessary for
   future font growth in a fixed-size panel; it is not a substitute for wrapping.
5. The preferred integration is an owner-local final-draw callback, leaving the
   shared renderer untouched. Reflow must be deterministic across repeated
   draws, text replacement, opacity updates, and live font changes. Preserve
   glyph IDs, links, texture coordinates, colours, and native object lifetime.
6. Inspection's four handles form one layout group. Resolve their vertical
   positions together; do not append newlines independently at fixed Y origins.
7. No source wording edits, global font changes, permanent shrink-to-fit
   replacement for wrapping, or new truncation/clipping.

## Outstanding diagnosis and decisions

- The reason j's static results differ from the screenshots is not yet proven.
  Native parser/node and final-draw tests now pass. Do not select a cause by
  elimination alone or treat the user's uncertain ISO filename as a diagnosis.
- Each inspection callback resolves and reflows the complete four-handle
  group, without relying on draw order. Its copied native allocator reserves
  0x258 bytes and stores the owning M_ObjDtl private pointer at +0x254.
  Native allocation, stack arguments, callback registration and metadata are
  covered by execution tests. The original destructor address is preserved;
  this is not yet a full execution test of destruction and owner teardown.
- The inspection backing comprises sprites 0x91/0x92/0x93, all anchored at
  (256,256), or Y=-32 for a high-positioned panel. The lower backing reaches
  anchorY+187. Body starts at anchorY+92; a 90-pixel content height leaves five
  pixels below it and accommodates five 18-pixel rows. Do not confuse the
  lower sprite's individual 78-pixel height with the entire body content area.
- Native converter, parser, real opacity rebuild and draw submission now keep
  four reported item examples within j's configured 198x60 test rectangle.
  This rules out the proposed control/lifecycle causes in that harness; it does
  not confirm which executable or precise backing bounds produced the images.
- No running PCSX2 process or current-release RAM snapshot was available.
  Historical snapshots are resource evidence only, not j runtime validation.
- The C kernel is built with pinned Apple clang 21.0.0 and llvmlite 0.50.0 /
  LLVM 22.1.0. The backend's MIPS III/o32 combination failed instruction
  selection; use the MIPS II subset supported by the EE, with an instruction
  allowlist and explicit finite-input comparison lowering. Only HI16/LO16 and
  local J26 relocations are accepted. Current kernel stack usage is 64 bytes.
- Raw EE COP1 audit rejects generic-MIPS-only encodings. EE LT/LE use functions
  0x34/0x36, not 0x3C/0x3E. Only unordered 0x35/0x37 are lowered to 0x34/0x36
  for finite layout inputs. A first unpublished build using the wrong mapping
  was quarantined; the corrected release hash is locked independently.
- All requested ordinary layout uses live font metrics. Unknown controls,
  malformed pointers or more than 1024 nodes reject before any geometry write.
  This is a safety boundary, not proof that arbitrary new control types wrap.

## Release gate

Use a new r67.15k artifact without overwriting any release. Require all-catalogue
layout tests, native execution tests, mutations for font growth and skipped
wrapping, accepted-region locks, the full suite, raw startup 154/scoped 155 with
the existing exception only, protected history 4/4, save descriptors 15/15,
resource lookup checks, and complete ISO audit with zero unexplained changes.
Static results are not gameplay approval. Record any runtime uncertainties and
the exact screenshots needed before claiming the visible defect is fixed.
