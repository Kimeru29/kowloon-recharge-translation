"""67.02 freeze and owner regression tests; require user-owned source assets."""
from __future__ import annotations
import hashlib, json, struct, unittest
from pathlib import Path
from tools.r67_02_layout import INSPECTIONS, TABLET_KEYS, STORY_COMMENTS, BASIC_ATTACK, FIXED_PICKUP, apply, sha
from tools.r67_playtest_history import append_history_layout
from tools.localization import encode_ps2_english
from tools.inspect_english_bytes import parse
from tools.first_save_help import _metadata, _icon_reservations, _MAX_CELLS

R=Path(__file__).resolve().parents[1]
ORIGINAL=R.parent/'startup-flow-v10/fixtures/elf/SLPM_665.11'
OFFICIAL=Path('/private/tmp/kowloon-ps4-recovered/CUSA27034/Media/StreamingAssets/data/English.bytes')
BASE=R/'local/r67-playtest-safe-v4.elf'
CANDIDATE=R/'local/r67-02-layout.elf'
HISTORY=R/'local/r67-02-history.elf'
HELP=R/'translations/r67_help_owners.json'
OWNERS=R/'translations/first_save_pointer_owners.json'

class Layout67_02Tests(unittest.TestCase):
    def test_readable_basic_attack_has_original_icon_safe_cardinality(self):
        self.assertEqual(15,len(BASIC_ATTACK))
        self.assertTrue(BASIC_ATTACK[0].startswith("Basic"))
        self.assertTrue(any("R Stick" in line for line in BASIC_ATTACK))
        self.assertTrue(any("AP" in line for line in BASIC_ATTACK))
        self.assertTrue(all(len(s)<=_MAX_CELLS for s in BASIC_ATTACK))
        self.assertEqual(len(INSPECTIONS),15)
        self.assertEqual(len(STORY_COMMENTS),2)
        self.assertTrue(all(len(x)<=14 for x in STORY_COMMENTS.values()))

    @unittest.skipUnless(all(p.exists() for p in (ORIGINAL,OFFICIAL,BASE,CANDIDATE,HISTORY,HELP,OWNERS)),
                         "Private PS2/PS4 sources and assembled test executables unavailable")
    def test_official_correspondence_all_sources_and_exact_binary_repro(self):
        source=ORIGINAL.read_bytes()
        base=BASE.read_bytes()
        help_pages=json.loads(HELP.read_text())['pages']
        previous=json.loads(OWNERS.read_text())['owners']
        output,report=apply(source,base,parse(OFFICIAL),help_pages,previous)
        self.assertEqual(CANDIDATE.read_bytes(),output)
        self.assertEqual('aba86a5fd8b1f81e12c50f5c1d15cb40fdb44d8fffa50b3ee7530128f77b4727',sha(output))
        self.assertEqual(22,len(report['changes']))
        self.assertEqual(15,report['help_rows'])
        self.assertEqual(1006,report['appended_bytes'])
        for entry in report['changes']:
            if entry['name'].startswith('inspection') or entry['name'].startswith('comment'):
                self.assertLessEqual(len(entry['english']),22)
        for p in help_pages:
            off=p['descriptor_offset']
            if p['key'] in ('entering_battle','turn_based_combat','basic_attack'):
                self.assertEqual(base[off:off+4],output[off:off+4])
            if p['key'] in ('entering_battle','turn_based_combat'):
                self.assertEqual(
                    base[p['metadata_descriptor_offset']:p['metadata_descriptor_offset']+4],
                    output[p['metadata_descriptor_offset']:p['metadata_descriptor_offset']+4]
                )
        b=next(x for x in help_pages if x['key']=='basic_attack')
        foff,va=struct.unpack_from('<II',base,0x58)
        table=foff+struct.unpack_from('<I',base,b['descriptor_offset'])[0]-va
        self.assertEqual(base[table+60:table+92],output[table+60:table+92])
        self.assertNotEqual(base[table:table+60],output[table:table+60])
        # Native code (except START-modal JAL in separate step) and saved-game
        # identity are outside this reflow's declared mutation set.
        self.assertEqual(base[0x1514f0:0x151740],output[0x1514f0:0x151740])
        self.assertEqual(base[0x14e940:0x14e980],output[0x14e940:0x14e980])

    @unittest.skipUnless(CANDIDATE.exists() and HISTORY.exists(),
                         "Locally built MIPS history candidate unavailable")
    def test_start_history_is_additive_separate_and_opt_in(self):
        source=CANDIDATE.read_bytes()
        result,details=append_history_layout(source)
        self.assertEqual(HISTORY.read_bytes(),result)
        self.assertEqual(72,details["helper_bytes"])
        self.assertEqual("horizontal",details["new_orientation"])
        self.assertEqual(0x159D54,details["source_jal"])
        bad=bytearray(source)
        bad[0x159D54:0x159D58]=b"\0"*4
        with self.assertRaisesRegex(ValueError,"Unexpected r67"):
            append_history_layout(bytes(bad))

    @unittest.skipUnless(ORIGINAL.exists() and BASE.exists() and OFFICIAL.exists() and HELP.exists() and OWNERS.exists(),
                         "Private PS2/PS4 corpus unavailable")
    def test_rejects_original_source_and_existing_elf_mutations(self):
        pristine=ORIGINAL.read_bytes()
        base=BASE.read_bytes()
        hp=json.loads(HELP.read_text())['pages']
        owners=json.loads(OWNERS.read_text())['owners']
        corpus=parse(OFFICIAL)
        bad=bytearray(base)
        bad[0x590be0]^=1
        with self.assertRaisesRegex(ValueError,"fingerprint"):
            apply(pristine,bytes(bad),corpus,hp,owners)
        bad=bytearray(pristine)
        bad[0x590be0]^=1
        with self.assertRaises(ValueError):
            apply(bytes(bad),base,corpus,hp,owners)

if __name__=="__main__":
    unittest.main()
