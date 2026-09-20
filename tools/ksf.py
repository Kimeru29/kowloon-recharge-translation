from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KsfFixedStringPatch:
    offset: int
    capacity: int
    text: str
    constrained: bool = False

    def encoded(self) -> bytes:
        try:
            encoded = self.text.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ValueError("KSF vertical-slice probe text must be ASCII") from exc
        if len(encoded) > self.capacity:
            raise ValueError(
                f"Text needs {len(encoded)} bytes but only a {self.capacity}-byte KSF field is available"
            )
        return encoded


def patch_fixed_strings(raw: bytes, patches: tuple[KsfFixedStringPatch, ...]) -> bytes:
    result = bytearray(raw)
    ordered = sorted(patches, key=lambda patch: patch.offset)
    previous_end = 0
    for patch in ordered:
        if patch.offset < 0 or patch.capacity <= 0:
            raise ValueError("Invalid KSF fixed string field")
        end = patch.offset + patch.capacity
        if end > len(result):
            raise ValueError("KSF fixed string field extends beyond file")
        if patch.offset < previous_end:
            raise ValueError("KSF fixed string fields overlap")
        encoded = patch.encoded()
        result[patch.offset:end] = encoded + (b"\x00" * (patch.capacity - len(encoded)))
        previous_end = end
    return bytes(result)
