from __future__ import annotations

from dataclasses import dataclass
import struct


HEADER_SIZE = 0x1800
SECTOR_SIZE = 2048


@dataclass(frozen=True)
class CvmHeader:
    raw: bytes
    total_size: int
    zone_chunk_length: int
    payload_size: int

    @classmethod
    def parse(cls, raw: bytes) -> "CvmHeader":
        if len(raw) != HEADER_SIZE:
            raise ValueError(f"Expected a {HEADER_SIZE}-byte CVM header, got {len(raw)}")
        if raw[:4] != b"CVMH":
            raise ValueError("CVMH signature not found")
        if raw[0x800:0x804] != b"ZONE":
            raise ValueError("ZONE signature not found")
        total_size = struct.unpack_from(">I", raw, 0x20)[0]
        zone_chunk_length = struct.unpack_from(">I", raw, 0x808)[0]
        payload_size = struct.unpack_from(">I", raw, 0x834)[0]
        if total_size - HEADER_SIZE != payload_size:
            raise ValueError("CVM total and payload size fields are inconsistent")
        if total_size - 0x80C != zone_chunk_length:
            raise ValueError("CVM ZONE chunk length is inconsistent with total size")
        return cls(raw, total_size, zone_chunk_length, payload_size)

    def grow_payload(self, amount: int) -> "CvmHeader":
        if amount <= 0 or amount % SECTOR_SIZE:
            raise ValueError("CVM payload growth must be a positive 2048-byte sector multiple")
        updated = bytearray(self.raw)
        new_total = self.total_size + amount
        new_zone = self.zone_chunk_length + amount
        new_payload = self.payload_size + amount
        for offset, value in ((0x20, new_total), (0x808, new_zone), (0x834, new_payload)):
            if value > 0xFFFFFFFF:
                raise ValueError("CVM size exceeds 32-bit header field")
            struct.pack_into(">I", updated, offset, value)
        return CvmHeader.parse(bytes(updated))

    def compile(self) -> bytes:
        return self.raw
