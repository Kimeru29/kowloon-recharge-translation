from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import struct
import unittest

from unicorn import UC_HOOK_CODE, mips_const as reg

from tests.r67_native_text_pipeline import NativeTextPipeline, NATIVE_GP, RETURN, STACK
from tools.localization import encode_ps2_english


ROOT = Path(__file__).resolve().parents[1]
N_ELF = ROOT / "local/r67n-release/67.15n-official-script-diagnostic.elf"
PS4_ADV = ROOT / "local/r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV"
BRACKET_INPUT = 0x1101000
ADV_STATE = 0x1110000
ACTOR_STATE = 0x1120000
LOWER = ((0x250530, 0x250750), (0x2523C0, 0x2525E0), (0x2525E0, 0x252ACC),
         (0x256470, 0x2567B0), (0x39F300, 0x39F42C), (0x12F600, 0x12F798))
PARSER_STOP = 0x250704
PX_STOP = 0x24D7F4
# Activate the stock libc byte paths in the private Unicorn image. The EE
# aligned paths use MMI opcodes unavailable on Unicorn's MIPS64 CPU.
SCALAR = (
    (0x39F310, 0x14400038, 0x39F3F4),  # strcat
    (0x39F5C8, 0x54400049, 0x39F6F0),  # strcmp
    (0x39F714, 0x14400038, 0x39F7F8),  # strcpy
    (0x39F824, 0x14400043, 0x39F934),  # strlen
    (0x39FCD4, 0x14400054, 0x39FE28),  # strncpy
)


class SpeakerNative:
    def __init__(self, source):
        self.pipeline = NativeTextPipeline(source, lower_ranges=LOWER)
        self.uc = self.pipeline.uc
        self.uc.mem_write(NATIVE_GP - 0x1DAC, struct.pack("<I", ADV_STATE))
        self.uc.mem_write(NATIVE_GP - 0x1D74, struct.pack("<I", ACTOR_STATE))
        for address, expected, target in SCALAR:
            if struct.unpack("<I", self.uc.mem_read(address, 4))[0] != expected:
                raise AssertionError(f"stock libc scalar entry preimage changed at {address:#x}")
            op = 0x50000000 if address == 0x39F5C8 else 0x10000000
            self.uc.mem_write(address, struct.pack("<I", op | ((target - address - 4) // 4 & 0xFFFF)))
        # strstr's empty-haystack path contains MOVZ, unavailable with Unicorn's
        # stock R4000. Express just that condition as a plain branch.
        if self.uc.mem_read(0x39FE8C, 12) != bytes.fromhex("2d1000000800e0030a108300"):
            raise AssertionError("stock strstr empty-input preimage changed")
        self.uc.mem_write(0x39FE8C, struct.pack("<3I", 0x1460001B, 0, 0x00801025))
        self.lookup_inputs = []
        for target in (0x256470, 0x256650):
            self.uc.hook_add(UC_HOOK_CODE, self._observe_lookup, begin=target, end=target)
        for stop in (PARSER_STOP, PX_STOP):
            self.uc.hook_add(UC_HOOK_CODE, lambda uc, *_: uc.emu_stop(), begin=stop, end=stop)

    def _observe_lookup(self, uc, address, *_):
        a0 = uc.reg_read(reg.UC_MIPS_REG_A0)
        value = bytes(uc.mem_read(a0, 33)).split(b"\0", 1)[0]
        self.lookup_inputs.append((address, value))

    def execute(self, start, stop, a0, *, stack=STACK):
        for register, value in ((reg.UC_MIPS_REG_A0, a0), (reg.UC_MIPS_REG_SP, stack),
                                (reg.UC_MIPS_REG_RA, RETURN), (reg.UC_MIPS_REG_GP, NATIVE_GP)):
            self.uc.reg_write(register, value)
        self.uc.emu_start(start, RETURN, timeout=3_000_000)
        actual = self.uc.reg_read(reg.UC_MIPS_REG_PC)
        if actual != stop:
            raise AssertionError(f"native execution stopped at {actual:#x}, expected {stop:#x}")
        return self.uc.reg_read(reg.UC_MIPS_REG_V0) & 0xFFFFFFFF

    def extract(self, label):
        self.lookup_inputs.clear()
        self.uc.mem_write(BRACKET_INPUT, label + b"r" + "仮".encode("cp932") + b"r_\0")
        self.execute(0x250530, PARSER_STOP, BRACKET_INPUT)
        identity = struct.unpack("<2b", self.uc.mem_read(ACTOR_STATE + 0xC, 2))
        adv_identity = struct.unpack("<2b", self.uc.mem_read(ADV_STATE + 0x31B9, 2))
        if identity != adv_identity:
            raise AssertionError("native actor and dynamic-name contexts disagree")
        display = bytes(self.uc.mem_read(ADV_STATE + 0x198, 101)).split(b"\0", 1)[0]
        return identity, display

    def px(self, label, names):
        # Input starts at the native px arm after its common string/macro
        # scratch initialization. It consumes the real parser-written ADV
        # state. The branch only needs s4, a valid frame and current name fields.
        self.extract(label)
        for address, name in zip((0x7C4BC0, 0x7C4BA0), names, strict=True):
            self.uc.mem_write(address, name.ljust(32, b"\0"))
        line = "君は".encode("cp932") + b"px" + "か。".encode("cp932")
        self.uc.mem_write(BRACKET_INPUT, line + b"\0")
        self.uc.reg_write(reg.UC_MIPS_REG_S4, BRACKET_INPUT)
        self.uc.mem_write(STACK - 0x350, bytes(0x350))
        self.execute(0x24D704, PX_STOP, BRACKET_INPUT, stack=STACK - 0x350)
        output = bytes(self.uc.mem_read(BRACKET_INPUT, 101)).split(b"\0", 1)[0]
        if output == line or not (output.startswith("君は".encode("cp932"))
                                  and output.endswith("か。".encode("cp932"))):
            raise AssertionError(f"native px did not preserve the prefix and suffix: {output.hex()}")
        return output


def verify_native(stock_elf, candidate_elf, corpus, report):
    """Replay actual parser, stock native identities and the bounded bridge."""
    stock, candidate = SpeakerNative(stock_elf), SpeakerNative(candidate_elf)
    digest = lambda raw: sha256(raw).hexdigest()
    proofs = {}
    for pair in corpus.speakers:
        expected, jp_display = stock.extract(pair.original)
        native_inputs = tuple(stock.lookup_inputs)
        restored, restored_display = candidate.extract(pair.original)
        localized, en_display = candidate.extract(pair.localized)
        if (expected != restored or expected != localized or jp_display != restored_display
                or en_display != pair.localized
                or tuple(candidate.lookup_inputs) != native_inputs
                or native_inputs != ((0x256470, jp_display), (0x256650, jp_display))):
            raise AssertionError(f"native speaker identity or display changed for {pair.japanese} → {pair.english}")
        proofs[digest(pair.original)] = {
            "stock_actor": expected[0], "stock_alias_column": expected[1],
            "original_tag_normalized": jp_display != pair.original,
            "verified_stock_lookup_inputs": [address for address, _ in native_inputs],
            "native_japanese_sha256": digest(jp_display), "native_english_sha256": digest(en_display),
        }

    sample_jp = "【八千穂】".encode("cp932")
    sample_en = encode_ps2_english("【Yachiho】")
    if stock.extract(sample_en)[0] != (-1, -1) or stock.extract(sample_jp)[0] != (3, 0):
        raise AssertionError("stock negative control did not reproduce the English identity failure")

    ambiguous = {}
    for japanese, details in corpus.excluded.items():
        if details.get("reason") != "ambiguous_english_reverse":
            continue
        tag = japanese.encode("cp932")
        before, before_display = stock.extract(tag)
        after, after_display = candidate.extract(tag)
        english = details["english"]
        if before != after or before_display != after_display or candidate.extract(encode_ps2_english(english))[0] != (-1, -1):
            raise AssertionError(f"ambiguous reverse label is not safely preserved: {japanese}")
        ambiguous[japanese] = {"english": english, "stock_actor": before[0], "stock_alias_column": before[1],
                               "reversed_english_result": [-1, -1]}

    guard_cases = guard_wrappers(candidate, report)
    px = {}
    for context, names in {"stock_default": ("葉佩", "九龍"), "custom": ("青山", "悠真")}.items():
        native_names = tuple(name.encode("cp932") for name in names)
        expected = stock.px(sample_jp, native_names)
        actual = candidate.px(sample_en, native_names)
        if actual != expected:
            raise AssertionError(f"native px speaker-selected result changed for {context}")
        px[context] = {"actor": 3, "alias_column": 0, "output_sha256": digest(actual)}

    return {"validated_pairs": len(proofs), "identities": proofs, "reverse_exclusions": ambiguous,
            "guard_cases": guard_cases, "px": px, "stock_unknown_yachiho": [-1, -1],
            "harness": "NativeTextPipeline with SQ/LQ lowering and stock scalar EE libc paths"}


def guard_wrappers(native, report):
    sentinel = bytes([0xB5]) * 0x100
    protected = {
        getattr(reg, f"UC_MIPS_REG_S{index}"): 0x1234567800000000 + index
        for index in range(8)
    }
    protected[reg.UC_MIPS_REG_FP] = 0x123456789ABC0000
    tags = {
        "overlong_unknown": encode_ps2_english("【" + "Z" * 34 + "】") + b"\0",
        "unterminated_at_100": encode_ps2_english("【" + "Z" * 49),
        "malformed_cp932": b"\x81\x79\x81\x39\x81\x7a\0",
        "dangling_lead": b"\x81\x79\x82\0",
        "missing_open": b"A\0",
        "missing_close": b"\x81\x79Z\0",
        "tail_after_close": "【仮】".encode("cp932") + b"A\0",
    }
    for site in report["call_sites"]:
        for description, tag in tags.items():
            address = 0x1200000 - len(tag)
            native.uc.mem_write(address, tag)
            native.uc.mem_write(STACK - 0x100, sentinel)
            for register, value in protected.items():
                native.uc.reg_write(register, value)
            value = native.execute(site["target"], RETURN, address)
            if (value != 0xFFFFFFFF or native.uc.mem_read(STACK - 0x100, 0x100) != sentinel
                    or native.uc.mem_read(address, len(tag)) != tag
                    or any(native.uc.reg_read(register) != guard for register, guard in protected.items())
                    or any(native.uc.reg_read(register) != guard for register, guard in (
                        (reg.UC_MIPS_REG_SP, STACK), (reg.UC_MIPS_REG_RA, RETURN), (reg.UC_MIPS_REG_GP, NATIVE_GP)))):
                raise AssertionError(f"native speaker guard wrote past its ownership: {description}")
    return sorted(tags)


@lru_cache(maxsize=1)
def candidate_fixture():
    from tools.r67o_speakers import build, load_corpus

    source = N_ELF.read_bytes()
    corpus = load_corpus(PS4_ADV)
    patched, report = build(source, corpus)
    return source, patched, corpus, report


@unittest.skipUnless(N_ELF.is_file() and PS4_ADV.is_dir(), "local r67.15n and official PS4 fixtures")
class SpeakerNativeTests(unittest.TestCase):
    def test_official_pairs_preserve_native_identity_and_px_paths(self):
        source, patched, corpus, report = candidate_fixture()
        self.assertEqual(214, len(corpus.speakers))
        proof = verify_native(source, patched, corpus, report)
        self.assertEqual(214, proof["validated_pairs"])
        self.assertEqual(11, sum(row["original_tag_normalized"] for row in proof["identities"].values()))
        self.assertEqual(6, len(proof["reverse_exclusions"]))
        self.assertNotEqual(proof["px"]["stock_default"]["output_sha256"], proof["px"]["custom"]["output_sha256"])

    def test_all_existing_bytes_outside_two_native_calls_and_pt_load_survive(self):
        source, patched, _corpus, report = candidate_fixture()
        allowed = {i for start, end in report["allowed_existing_ranges"] for i in range(start, end)}
        self.assertEqual((0x2506BC, 0x2506E4), tuple(row["address"] for row in report["call_sites"]))
        self.assertTrue(all(a == b or offset in allowed for offset, (a, b) in enumerate(zip(source, patched))))
        self.assertEqual([len(source), len(patched)], report["appended_extent"])

    def test_mutated_base_cannot_reach_the_native_patcher(self):
        from tools.r67o_speakers import build

        source, _patched, corpus, report = candidate_fixture()
        changed = bytearray(source)
        changed[report["call_sites"][0]["file_offset"]] ^= 1
        with self.assertRaisesRegex(ValueError, "pinned n"):
            build(bytes(changed), corpus)
