from __future__ import annotations

from dataclasses import dataclass

from tools.localization import encode_ps2_english


@dataclass(frozen=True)
class ElfFixedStringPatch:
    offset: int
    capacity: int
    expected: str
    text: str
    encoding: str = "ascii"

    def expected_bytes(self) -> bytes:
        return self.expected.encode("cp932")

    def replacement_bytes(self) -> bytes:
        if self.encoding == "ascii":
            try:
                encoded = self.text.encode("ascii")
            except UnicodeEncodeError as exc:
                raise ValueError("ELF replacement text must be ASCII") from exc
        elif self.encoding == "ps2-wide":
            encoded = encode_ps2_english(self.text)
        elif self.encoding == "ps2-wide-fixed":
            encoded = encode_ps2_english(self.text, collapse_spaces=False)
        else:
            raise ValueError(f"Unsupported ELF string encoding: {self.encoding}")
        if len(encoded) >= self.capacity:
            raise ValueError(
                f"Replacement needs {len(encoded)} bytes plus a NUL terminator, "
                f"but the ELF slot is only {self.capacity} bytes"
            )
        return encoded


def patch_fixed_strings(raw: bytes, patches: tuple[ElfFixedStringPatch, ...]) -> bytes:
    result = bytearray(raw)
    ordered = sorted(patches, key=lambda patch: patch.offset)
    previous_end = 0

    for patch in ordered:
        if patch.offset < 0 or patch.capacity <= 0:
            raise ValueError("Invalid ELF fixed string slot")
        end = patch.offset + patch.capacity
        if end > len(result):
            raise ValueError("ELF fixed string slot extends beyond file")
        if patch.offset < previous_end:
            raise ValueError("ELF fixed string slots overlap")

        expected = patch.expected_bytes()
        if len(expected) >= patch.capacity:
            raise ValueError("Expected source string does not fit inside its ELF slot")
        actual = bytes(result[patch.offset:patch.offset + len(expected)])
        if actual != expected or result[patch.offset + len(expected)] != 0:
            raise ValueError(
                f"ELF expected source mismatch at {patch.offset:#x}: "
                f"expected source {patch.expected!r}"
            )

        replacement = patch.replacement_bytes()
        result[patch.offset:end] = replacement + b"\x00" * (patch.capacity - len(replacement))
        previous_end = end

    return bytes(result)
