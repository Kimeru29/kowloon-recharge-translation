from pathlib import Path

ps2_root = Path('/tmp/khc-ps2-assets/ADV')
ps4_root = Path('/tmp/khc-ps4-extracted/CUSA27034/Media/StreamingAssets/data/ADV')
rows = []
for ps2 in sorted(ps2_root.rglob('*.KSF')):
    rel = ps2.relative_to(ps2_root)
    ps4 = ps4_root / rel
    if not ps4.exists():
        continue
    a_size = ps2.stat().st_size
    b_size = ps4.stat().st_size
    if a_size != b_size:
        rows.append((str(rel), a_size, b_size, b_size-a_size))
print('size_different', len(rows))
for row in rows[:200]:
    print(*row)
