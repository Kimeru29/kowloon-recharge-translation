import struct
import unittest

from tools.localization import encode_ps2_english
from tools.mtx import MtxFile


def mtx_regions(*regions):
    starts, offset = [], 8
    aligned = [region + b"\0" * (-len(region) % 4) for region in regions]
    for region in aligned:
        starts.append(offset // 4)
        offset += len(region)
    return struct.pack("<4H", starts[0], starts[1], starts[1], 0) + b"".join(aligned)


class SpeakerScriptTests(unittest.TestCase):
    def test_translates_only_header_at_native_dispatch_boundaries(self):
        from tools.r67o_speakers import Speaker, SpeakerCorpus, patch_script

        jp = "【八千穂】".encode("cp932")
        en = encode_ps2_english("【Yachiho】")
        word = "言葉".encode("cp932")
        corpus = SpeakerCorpus((Speaker("【八千穂】", "【Yachiho】", jp, en, ()),), {}, {})
        source = mtx_regions(
            jp + b"r" + word + jp + b"r" + word + b"wc" + jp + b"rpx" + word + b"wc_",
            b"ds01s3ci50ch00200" + jp + b"rl" + word + b"(" + word + b")r" + jp + b"r" + word
            + b"wcx" + jp + b"r" + word + b"wcpx" + jp + b"r" + word + b"wc_",
        )
        output, report = patch_script(source, corpus)
        expected = (
            en + b"r" + word + jp + b"r" + word + b"wc" + en + b"rpx" + word + b"wc_",
            b"ds01s3ci50ch00200" + en + b"rl" + word + b"(" + word + b")r" + jp + b"r" + word
            + b"wcx" + jp + b"r" + word + b"wcpx" + jp + b"r" + word + b"wc_",
        )
        starts = MtxFile.parse(output).pointer_offsets
        self.assertEqual((starts[1], 0), starts[2:])
        self.assertEqual(3, len(report["occurrences"]))
        for region, start, end in zip(expected, starts, (starts[1], len(output))):
            self.assertTrue(output[start:end].startswith(region))
            self.assertFalse(output[start + len(region):end].strip(b"\0"))
        for row in report["occurrences"]:
            start, end = row["input_span"]
            after, finish = row["output_span"]
            self.assertEqual(jp, source[start:end])
            self.assertEqual(en, output[after:finish])


    def test_final_native_region_without_terminator_needs_no_alignment_padding(self):
        from tools.r67o_speakers import Speaker, SpeakerCorpus, patch_script

        jp = "【八千穂】".encode("cp932")
        en = encode_ps2_english("【Yachiho】")
        word = "仮".encode("cp932")
        corpus = SpeakerCorpus((Speaker("【八千穂】", "【Yachiho】", jp, en, ()),), {}, {})
        source = mtx_regions(jp + b"r" + word + b"wc_", jp + b"r" + word + b"wc").rstrip(b"\0")
        output, report = patch_script(source, corpus)
        final = MtxFile.parse(output).pointer_offsets[1]
        self.assertEqual(en + b"r" + word + b"wc", output[final:])
        self.assertEqual(2, len(report["occurrences"]))
        self.assertEqual(0, report["regions"][-1]["alignment_nul_added"])

    def test_label_split_across_distinct_pointer_spans_is_held(self):
        from tools.r67o_speakers import Speaker, SpeakerCorpus, patch_script

        jp = "【八千穂】".encode("cp932")
        en = encode_ps2_english("【Yachiho】")
        corpus = SpeakerCorpus((Speaker("【八千穂】", "【Yachiho】", jp, en, ()),), {}, {})
        source = mtx_regions(jp[:4], jp[4:] + b"r" + "仮".encode("cp932") + b"wc_")
        output, report = patch_script(source, corpus)
        self.assertEqual(source, output)
        self.assertEqual([], report["occurrences"])

    def test_pointer_growth_fails_closed_before_u16_quarter_offset_overflow(self):
        from tools.r67o_speakers import Speaker, SpeakerCorpus, patch_script

        jp = "【八千穂】".encode("cp932")
        en = encode_ps2_english("【Yachiho】")
        corpus = SpeakerCorpus((Speaker("【八千穂】", "【Yachiho】", jp, en, ()),), {}, {})
        terminal = jp + b"r" + "仮".encode("cp932") + b"wc_"
        source = struct.pack("<4H", 2, 0xFFFF, 0xFFFF, 0)
        source += terminal.ljust(0xFFFF * 4 - len(source), b"\0")
        source += terminal
        with self.assertRaisesRegex(ValueError, "exceeds u16 quarter-offset"):
            patch_script(source, corpus)
