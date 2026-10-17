# r67.15h — animated area-loading stall investigation

## User-observed failure

From a normal save at the Soul Well in the tutorial dungeon, the user used Aqua
Regia on Gold Chains and entered the next doorway. The next-area loading
animation continued indefinitely. The user subsequently confirmed opening and
scrolling at least four or five HANT Help pages earlier in that same run.

Do not classify an animated loading screen as a CPU freeze. Do not identify a
particular file wait, event wait or corruption cause solely from that image.

## Evidence captured without operating the emulator

The open-file listing and emulator log identified the exact 15g partial image.
The executable size was 8,871,244 bytes and its logged MD5 was
`5915143a3274fd6587b974937ebf184a`. The staged ELF SHA-256 is
`74e812b1dc51429c62affc63f357b0f4f68bf446552a931de21db2479c077bee`.
The log reported game CRC `D8A20438`.

At about 276.04 seconds, the log recorded this ordering:

1. X setter `0x18AAB0`: read at `0x41`, write at `0x14`.
2. Text geometry builder `0x18CB50`: low-address reads, including `4`, `0x24`
   and `0x10`.
3. Y setter `0x18AAE0`: read at `0x41`, write at `0x18`; builder repeats.
4. Text replacement `0x18A080`, glyph cleanup `0x188940`, and low-address
   writes at `0x51`, `0x52`, and subsequent bytes.

The captured log contains no explicit failed next-area file read. Absence of a
logged error is not proof that every I/O request or event completed. PCSX2 later
closed independently; this task did not launch, pause, reset, attach a debugger
to, or control it. No live register/stack capture exists for the stall.

Ignored evidence directory: `local/r67-15h-evidence/`. It contains the four user
screenshots and an unmodified copy of the run's `emulog.txt`. Proprietary images,
game binaries, save data and logs are not committed.

## Confirmed independent defect: HANT viewport handle overrun

The native HANT class has 16 text handles at private offset `0x17A0`. Its draw
predicate accepts any row whose origin satisfies `89 < Y < 383`. Help rows use
16-pixel pitch, so ordinary scrolling can expose 19 rows, including blank rows.
The allocation cap and draw-pool limit disagree with this geometry.

```text
row Y = 131 + 16 * index - scroll
scroll 0:  16 eligible rows
scroll 5:  17 eligible rows
scroll 40: 19 eligible rows

pool[16] = private[0x17A0 + 4*16] = private[0x17E0]
private[0x17E0] = active state 5
invalid text handle 5 -> handle+0x3C = 0x41
```

The viewport calls the X setter, Y setter and text replacement in exactly the
logged order. Its supposed assertion calls `0x1C66D0`, which is `jr ra; nop` and
does not stop the out-of-bounds access. This is a confirmed native memory-safety
defect, with a strong match to the recorded faults and an exposure confirmed by
the user. See the HANT component documentation for the repair and native tests.

It is **not yet a proven cause of the later door-loading stall**. TLB misses
establish attempted invalid accesses, not successful low-memory writes or a
particular downstream state change. Do not turn the matching address pattern
into a claim that the next area has been tested or that the loading issue is
resolved.

## Loading metadata check

An independent read-only check used the original PS2 ISO and original ELF to
identify each embedded ROFS filename/size/sector record, then compared the
corresponding 15g ELF values with the actual 15g DATA.CVM nested directory.

| Result | Count |
| --- | ---: |
| Original file records uniquely matched | 10,656 |
| Files resized or relocated since pristine | 969 |
| Incorrect installed size/sector pairs | 0 |
| Missing or ambiguous matches | 0 |

This rules out stale embedded ROFS size/sector metadata for the installed image.
It does not prove runtime scheduling, event completion, archive contents or
cross-release save compatibility. The previous 15g complete-disc audit also
established that DATA.CVM was unchanged from 15f; 15g's new changes were in the
executable and its directory size metadata.

## Runtime acceptance and next diagnostic boundary

Test a new executable from a cold boot and a normal save, not an old
executable-bearing savestate. Keep the original save unchanged.

1. Check the reported Details and recipe cases.
2. Open and fully scroll the four corrected Help pages; close and reopen them.
3. Use Aqua Regia on Gold Chains and enter the next area. Capture the loaded
   destination, not only disappearance of the loading text.
4. If it still stalls, retain that run's log and exact image hash. A live,
   read-only guest-state capture during the stall would then distinguish file,
   task and event waits. Enabling a debugging interface, creating a savestate,
   restarting the emulator or changing its settings requires separate consent;
   this document does not authorize those actions.

No timeout, forced transition, guessed pointer guard in a shared text routine,
or unverified resource edit is an acceptable substitute for the remaining
runtime evidence.
