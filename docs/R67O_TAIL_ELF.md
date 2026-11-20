# r67.15o outer ISO ELF growth

The r67.15n source ISO already places `SLPM_665.11` at the end of the allocated outer files. Its allocation ends at sector 1,018,893, leaving 4,243 sectors within the declared volume. Relocating a larger ELF requires at least 4,350 sectors, even if the ELF grows by only one sector.

```text
Original ELF allocation    1,014,544 + 4,349 = 1,018,893
Available trailing sectors 1,023,136 - 1,018,893 = 4,243
```

When DATA.CVM grows, its existing tail shift first moves the ELF extent by the same number of sectors. The builder can then extend the ELF at that extent when all of these conditions hold.

- The replacement needs more sectors than the original ELF.
- The original ELF's exclusive end equals the highest exclusive end in the outer ISO index.
- Every other indexed outer record ends at or before the original ELF start.
- The shifted ELF start plus the replacement's sector count fits within the original declared outer volume.

The existing append relocation path handles larger ELF replacements that fail this check. The build raises an insufficient-slack error when that relocation cannot fit. For in-place growth, the report sets `elf_extended_in_place` to true and `elf_relocated` to false. The reported output extent still includes any DATA.CVM tail shift.

The builder writes the exact replacement ELF with any required ROFS updates, pads the remainder of its final sector with zeros, and updates the ISO9660 extent and size in both byte orders. The outer volume and ISO file length are fixed. The release workflow supplies a fresh staging destination.

Synthetic tests cover exact-fit growth, growth after a DATA.CVM tail shift, fallback relocation for earlier and shared extents, and rejection when the combined growth exceeds the volume. They verify the installed ELF and padding, directory metadata, the neighboring payload, and source-image byte identity.
