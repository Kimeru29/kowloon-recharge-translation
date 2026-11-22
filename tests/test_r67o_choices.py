from collections import Counter
from functools import lru_cache
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / 'local'
ELF = LOCAL / 'r67n-release/67.15n-official-script-diagnostic.elf'
ISO = ELF.with_suffix('.iso')
PRISTINE = LOCAL / 'r67n-sources/SLPM_665.11'
PS2 = LOCAL / 'r67n-sources/assets/ADV'
PS4 = LOCAL / 'r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/data/ADV'
RESEARCH = LOCAL / 'r67o-research/ksf-design-evidence.json'
INVENTORY = LOCAL / 'r67n-inventory-final/files.json'
SUPPLEMENT = LOCAL / 'r67o-choice-correspondence/report.json'


@lru_cache(maxsize=1)
def checked_corpus(include_supplement=False):
    from tools.r67o_choices import load_corpus

    return load_corpus(ELF.read_bytes(), PRISTINE.read_bytes(), ISO, PS2, PS4, RESEARCH, INVENTORY,
                       SUPPLEMENT if include_supplement else None)


@unittest.skipUnless(all(path.exists() for path in (ELF, ISO, PRISTINE, PS2, PS4, RESEARCH, INVENTORY)),
                     'Pinned r67.15n and official KSF sources are unavailable')
class ChoiceSourceTests(unittest.TestCase):
    def test_complete_source_records_are_guarded_without_disk_changes(self):
        self.assertTrue((ROOT / 'tools/r67o_choices.py').exists(), 'choice side table generator is missing')
        corpus = checked_corpus()
        self.assertEqual(159, len(corpus.files))
        self.assertEqual(425, len(corpus.records))
        self.assertEqual({1: 28, 2: 253, 3: 68, 4: 76}, Counter(len(r.rows) for r in corpus.records))
        self.assertEqual(4, len(corpus.blank_rows))
        self.assertTrue(all(set(row.text) == {'\u3000'} for row in corpus.blank_rows))
        rows = [row for record in corpus.records for row in record.rows]
        self.assertEqual(1042, len(rows))
        self.assertEqual(664, len({row.text for row in rows + list(corpus.blank_rows)}))
        self.assertEqual(
            {'FN/FN06_01.KSF': 1, 'ID/ID00_04.KSF': 1, 'ID/ID00_26.KSF': 1, 'MS/MS06_01.KSF': 1},
            Counter(row.path for row in rows if row.dynamic))
        self.assertEqual(96, max(len(row.encoded) for row in rows))
        self.assertTrue(all(len(row.preimage) == len(row.pristine) == 30 for row in rows))

    @unittest.skipUnless(SUPPLEMENT.is_file(), 'Pinned KSF supplemental inputs are unavailable')
    def test_supplement_adds_37_complete_choices_without_changing_existing_bindings(self):
        base, supplemental = checked_corpus(), checked_corpus(True)
        self.assertEqual(163, len(supplemental.files))
        self.assertEqual(441, len(supplemental.records))
        self.assertEqual(1079, sum(len(group.rows) for group in supplemental.records))
        self.assertEqual(4, len(supplemental.blank_rows))
        identities = {(group.loaded_name, group.ordinal): group for group in supplemental.records}
        self.assertTrue(all(identities[group.loaded_name, group.ordinal] == group for group in base.records))
        self.assertEqual(37, sum(row.status == 'proven native correspondence'
                                 for group in supplemental.records for row in group.rows))

    def test_source_and_evidence_drift_fail_before_packaging(self):
        self.assertTrue((ROOT / 'tools/r67o_choices.py').exists(), 'choice side table generator is missing')
        from tools.r67o_choices import load_corpus

        source = ELF.read_bytes()
        changed = bytearray(source)
        changed[0x22C388 - 0xFFF80] ^= 1
        with self.assertRaisesRegex(ValueError, 'unchanged r67.15n ELF'):
            load_corpus(bytes(changed), b'', ISO, PS2, PS4, RESEARCH, INVENTORY)

        with tempfile.TemporaryDirectory() as tmp:
            changed_evidence = Path(tmp) / RESEARCH.name
            changed_evidence.write_bytes(RESEARCH.read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'KSF research evidence'):
                load_corpus(source, PRISTINE.read_bytes(), ISO, PS2, PS4, changed_evidence, INVENTORY)
