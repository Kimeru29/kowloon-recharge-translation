# Numbered testing releases

Use the plain numeric version in both the GitHub Release title and tag:
`67.01`, `67.02`, `67.03`, etc. Use `67.01.iso` locally.

Until the New Game → Soul Well route has gameplay approval, releases are
GitHub **prereleases**, never treated as fully approved r67. Publishing a
testing prerelease must not merge changes into `main`. Release assets
contain a reproducible binary patch and an apply script, **not** a full
copyrighted game ISO.

67.01: Basic Attack freeze-safety rollback; H.A.N.T. heading/dotted leader
formatting; independent story comment compacted. The original and output
ISO SHA-256 checksums are in the release notes. PCSX2 approval pending.

67.02: improved inspection/description boundaries, item names, Basic Attack
help (15 existing rows only), compact story speech and experimental horizontal
Start-key history modal. Entering Battle and Turn-Based Combat are locked.
User PCSX2 approval pending.

67.03: Compact Lion Statue, pedestal, large-vase and common state descriptions;
translate Use Item action; reformat icon-preserving Basic Attack/Turn-Based
Combat Help and nudge first chamber speech text right. Door, Stone tablet,
Treasure Vase and Entering Battle frozen. START history and story speech
background/vertical offset remain open; user PCSX2 validation required.

67.04: Official Change target label for the Lion Statue L1/R1 interaction and
Basic Attack Help copy cleanup within the original 15 occupied rows only.
Pablo accepted Turn-Based Combat, Stone Tablet, physical Lion Statue inspection,
Large Container, Stone Pedestal, and Treasure Vase: these are frozen. The
pickup-name clipping, Use Item slight clipping, START history and story-comment
speech placement remain unsolved. 67.04 is a partial testing prerelease, built
as a small incremental xdelta update from 67.03 and never merged to main.

67.05: shorter L1/R1 Target caption (full text visible within native width) and
additional Basic Attack captions on native controller-icon rows 16 and 19.
Stone Pedestal Push/Use Item action explicitly frozen. Other approved panels,
Turn-Based Combat and AFK/L1 unchanged. History, old-man blue backing/text and
Lion Statue pickup title remain blocked on independent renderer ownership.
This is another partial testing prerelease, not full first-save acceptance.
