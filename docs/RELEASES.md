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
