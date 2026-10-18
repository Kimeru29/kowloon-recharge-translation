import struct
import unittest
from pathlib import Path
from tests.test_r67_15j_item_layout import execute, codes_for
from tests.r67_native_geometry import render
from tools import r67_15j_inspection_layout as layout

ROOT=Path(__file__).resolve().parents[1]


class InspectionLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=(ROOT/'local/r67-15i-hant-text-item-details.elf').read_bytes()
        cls.raw,cls.report=layout.build(cls.source)

    def test_shared_animation_is_unchanged_and_only_registered_callers_redirect(self):
        self.assertEqual(self.source[0x299F30-0xFFF80:0x29A710-0xFFF80],
                         self.raw[0x299F30-0xFFF80:0x29A710-0xFFF80])
        allowed=set(range(0x64,0x68))
        for spans in layout.ALLOWED_SOURCE_RANGES.values():
            for lo,hi in spans: allowed.update(range(lo,hi))
        changed={i for i,(a,b) in enumerate(zip(self.source,self.raw)) if a!=b}
        self.assertFalse(changed-allowed)

    def test_copies_keep_native_state_machine_branches_and_scope_text_update(self):
        for key,data in self.report['animations'].items():
            callback=data['callback_va']; table=data['switch_va']; constructor=data['constructor_va']
            f=lambda va: va-0x902F00+0x803150
            cases=struct.unpack_from('<6I',self.raw,f(table))
            original=struct.unpack_from('<6I',self.source,0x7864D0-0xFFF80)
            self.assertEqual(cases,tuple(callback+x-0x299F30 for x in original))
            for delta in range(0,0x510,4):
                word=struct.unpack_from('<I',self.source,0x299F30-0xFFF80+delta)[0]
                actual=struct.unpack_from('<I',self.raw,f(callback)+delta)[0]
                if delta not in (0xBC,0xC0,0x190): self.assertEqual(word,actual)
            update=struct.unpack_from('<I',self.raw,f(callback)+0x190)[0]
            self.assertEqual((update&0x3FFFFFF)<<2,data['fitter_va'])
            self.assertGreater(constructor,callback)

    def test_native_panel_bounds_and_text_origins_are_pinned(self):
        from tools.r67_15j_help_layout import frames
        self.assertEqual(frames(self.source,2,0x93)[-1],(360,78,180,-109))
        self.assertEqual(frames(self.source,2,0x9D)[0],(232,24,-52,11))
        for va,word in {0x29ABF0:0x3C024320,0x29AC00:0x3C024100,
                        0x29AD38:0x3C024400,0x29AC40:0x3C024190}.items():
            self.assertEqual(struct.unpack_from('<I',self.source,va-0xFFF80)[0],word)

    def test_long_descriptions_titles_and_actions_execute_fitter_then_native_geometry(self):
        for key,data in self.report['animations'].items():
            for text in ("Ancient Heracleion epigraph.","Strong Kirlian effect detected.",
                         "Isis' Inscription"*3, 'A'*100, 'Long description '*5):
                with self.subTest(owner=key,text=text):
                    origin=(88.,348.) if key=='body' else (256-len(text)*8.,321.) if key=='title' else (304.,248.)
                    words,(sx,sy),pitch,calls,context=execute(self.raw,codes_for([text]),
                        target_override=data['fitter_va'],update=True,origin=origin,return_context=True)
                    self.assertEqual(context['return'],0xABCD)
                    self.assertEqual(len(calls),1)
                    native=[w if w>=0xFFFFFF00 else ord('A') for w in words[:-1]]
                    result=render(self.source,native,scale_x=sx,scale_y=sy,origin=context['origin'])
                    self.assertLessEqual(result.bounds.right-result.bounds.left,data['width']+.001)
                    if key=='title':
                        self.assertGreaterEqual(result.bounds.left,88-.001)
                        self.assertLessEqual(result.bounds.right,424+.001)
                    if len(text)*16>data['width']:
                        self.assertEqual(context['cursor_origin'],context['origin'][0])
                        self.assertEqual(context['animation_origin'],context['origin'][0])
                        self.assertLessEqual((16+context['animation_tracking'])*len(text),data['width']+.01)

    def test_accepted_short_inspection_strings_keep_original_metrics_and_spaces(self):
        for key,data in self.report['animations'].items():
            text='Gold Chains' if key!='action' else 'Take'
            codes=codes_for([text])
            words,scale,_,calls=execute(self.raw,codes,target_override=data['fitter_va'],update=True)
            self.assertEqual(words,codes)
            self.assertEqual(scale,(1.,1.))
            self.assertEqual(len(calls),1)

    def test_reading_uses_real_twelve_pixel_font_and_centered_bounds(self):
        words,(sx,sy),_,calls,context=execute(self.raw,codes_for(['Long reading '*5]),
            target_override=self.report['reading_helper_va'],update=True,
            font_descriptor=0x5D7800,return_context=True)
        self.assertEqual(len(calls),1)
        result=render(self.source,[w if w>=0xFFFFFF00 else ord('A') for w in words[:-1]],
            scale_x=sx,scale_y=sy,origin=context['origin'],font_descriptor=0x5D7800)
        self.assertGreaterEqual(result.bounds.left,88-.001)
        self.assertLessEqual(result.bounds.right,424+.001)

    def test_all_six_fields_of_every_native_object_record_fit(self):
        records=layout.catalogue(self.source)
        self.assertEqual(len(records),600)
        tested=set()
        for record,fields in records.items():
            for index,text in enumerate(fields):
                # Identical aliases share metrics; still enumerate every owner.
                role='title' if index==0 else 'reading' if index==5 else 'body'
                if not text or (role,text) in tested: continue
                tested.add((role,text))
                with self.subTest(record=hex(record),field=index):
                    font=0x5D7800 if role=='reading' else 0x5D77D0
                    fw=12 if role=='reading' else 16
                    origin=(88.,348.) if role=='body' else (256-len(text)*fw/2,321.)
                    target=self.report['reading_helper_va'] if role=='reading' else self.report['animations'][role]['fitter_va']
                    words,(sx,sy),_,calls,context=execute(self.raw,codes_for([text]),target_override=target,
                        update=True,font_descriptor=font,origin=origin,return_context=True)
                    self.assertEqual(len(calls),1)
                    result=render(self.source,[w if w>=0xFFFFFF00 else ord('A') for w in words[:-1]],
                        scale_x=sx,scale_y=sy,origin=context['origin'],font_descriptor=font)
                    self.assertGreaterEqual(result.bounds.left,88-.001)
                    self.assertLessEqual(result.bounds.right,424+.001)
        self.assertGreater(len(tested),600)

    def test_extreme_unsupported_space_only_input_fails_closed(self):
        codes=codes_for([' '*100])
        words,scale,_,calls=execute(self.raw,codes,target_override=self.report['animations']['body']['fitter_va'],update=True)
        self.assertEqual(words,codes)
        self.assertEqual(scale,(1.,1.))
        self.assertEqual(calls,[])

    def test_only_official_deleted_duplicate_readings_are_suppressed(self):
        deletions=self.report['official_deleted_readings']
        self.assertEqual({row['owner'] for row in deletions},{0x58A1C4,0x592A84})
        for row in deletions:
            self.assertEqual(row['official_record'],400151)
            self.assertEqual(struct.unpack_from('<I',self.raw,row['owner'])[0],0x795B9C)

    def test_copied_callback_dispatch_runs_update_and_advances_native_phase(self):
        for role,data in self.report['animations'].items():
            with self.subTest(role=role):
                words,(sx,sy),_,calls,context=execute(self.raw,codes_for(['Long description '*3]),
                    target_override=data['callback_va'],origin=(88.,348.),
                    callback=True,return_context=True,lower_start=data['fitter_va'])
                self.assertEqual(context['animation_phase'],3)
                self.assertEqual(context['return'],0)
                self.assertEqual(len(calls),1)
                result=render(self.source,[w if w>=0xFFFFFF00 else ord('A') for w in words[:-1]],
                    scale_x=sx,scale_y=sy,origin=context['origin'])
                self.assertLessEqual(result.bounds.right-result.bounds.left,data['width']+.001)
