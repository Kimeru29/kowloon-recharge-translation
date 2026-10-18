import struct
import unittest
from pathlib import Path
from tools import r67_15j_help_layout as layout

ROOT = Path(__file__).resolve().parents[1]


class HelpLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT/'local/r67-15i-hant-text-item-details.elf').read_bytes()
        cls.raw, cls.report = layout.build(cls.source)

    def test_every_icon_remains_attached_to_its_instruction(self):
        self.assertEqual(len(self.report['pages']), 5)
        for key, page in self.report['pages'].items():
            with self.subTest(page=key):
                self.assertEqual(len(page['icons']), page['source_icons'])
                for icon in page['icons']:
                    self.assertEqual(icon['row'], icon['instruction_row'])
                self.assertEqual(page['intersections'], [])
                self.assertLessEqual(len(page['rows']), 80)
                self.assertTrue(all(len(row)<=28 for row in page['rows']))

    def test_actual_groups_and_signed_pivots_not_group_two(self):
        self.assertEqual(layout.frames(self.source,0,3)[0], (24,24,0,0))
        self.assertEqual(layout.frames(self.source,38,10)[0], (33,33,1,1))
        self.assertEqual(layout.frames(self.source,38,60)[0], (24,24,8,8))
        self.assertEqual(layout.frames(self.source,38,11)[0], (24,32,3,-2))
        self.assertEqual(len(layout.frames(self.source,38,10)),6)

    def test_synthesis_icons_share_units_and_page_is_compact(self):
        page = self.report['pages']['item_synthesis']
        self.assertLessEqual(len(page['rows']), 28)
        self.assertEqual(page['icons'][3]['row'],page['icons'][4]['row'])
        for index, phrase in ((0,'1st item'),(1,'2nd item'),(2,'cannot be compounded'),(4,'compounding guide')):
            icon = page['icons'][index]
            self.assertIn(phrase, icon['official_text'])

    def test_item_screen_capacity_and_each_category_have_separate_blocks(self):
        page=self.report['pages']['item_screen']
        for index, phrase in ((11,'Room storage'),(12,'Assault vest'),
                             (13,'Firearms'),(14,'Melee'),(15,'Projectile'),
                             (16,'Underwear'),(17,'Accessory'),(18,'Medicine'),
                             (19,'Edibles'),(21,'Yellow'),(22,'Green')):
            self.assertIn(phrase,page['icons'][index]['official_text'])
        self.assertEqual(len({page['icons'][i]['row'] for i in range(13,20)}),7)

    def test_published_strings_are_exact_official_units_except_existing_ps2_controls(self):
        for page in self.report['pages'].values():
            for block in page['blocks']:
                reconstructed=' '.join(row.strip() for row in page['rows'][block['row']:block['end_row']] if row.strip())
                self.assertEqual(reconstructed, block['text'])
                self.assertTrue(block['provenance'])

    def test_only_descriptors_change_and_hant_visibility_safety_is_preserved(self):
        allowed=set(range(0x64,0x68))
        for spans in layout.ALLOWED_SOURCE_RANGES.values():
            for lo,hi in spans: allowed.update(range(lo,hi))
        changed={i for i,(a,b) in enumerate(zip(self.source,self.raw)) if a!=b}
        self.assertFalse(changed-allowed)
        for lo,hi in ((0x18FDD4,0x18FECC),(0x18F000,0x18F100)):
            self.assertEqual(self.source[lo:hi],self.raw[lo:hi])
        self.assertEqual(struct.unpack_from('<I',self.raw,0x64)[0],len(self.raw)-0x803150)

    def test_native_twelve_pixel_glyph_quads_clear_every_sprite_envelope(self):
        from tests.r67_native_geometry import render
        for key,page in self.report['pages'].items():
            for row,line in enumerate(page['rows']):
                if not line: continue
                result=render(self.source,line,scale_x=1.,scale_y=1.,
                              origin=(85.,131.+row*16),font_descriptor=0x5D7800)
                self.assertLessEqual(result.bounds.right,420.)
                for node in result.nodes:
                    if node.control>=0xFFFFFF00: continue
                    left=min(q.left for q in node.quads);right=max(q.left for q in node.quads)+1
                    top=min(q.top for q in node.quads);bottom=max(q.top for q in node.quads)+1
                    for icon in page['icons']:
                        x,y,w,h=icon['rect']
                        self.assertFalse(left<x+w and x<right and top<y+h and y<bottom,
                                         (key,row,icon['index']))

    def test_five_pixel_native_scroll_sweeps_reach_every_row_without_pool_overrun(self):
        from tests.test_r67_15i_hant_text import run_viewport, HANDLES
        for key,page in self.report['pages'].items():
            count=len(page['rows'])
            maximum=max(0,count*21-222)  # unchanged native extent, not a 16-row model
            positions=sorted(set([*range(0,maximum+1,5),maximum]))
            seen=set()
            for scroll in positions:
                expected=[i for i in range(count) if 89<131+16*i-scroll<383]
                seen.update(expected)
                _,calls,_,faults=run_viewport(self.raw,count=count,scroll=scroll)
                self.assertEqual(faults,[])
                handles=[handle for handle,_ in calls]
                self.assertEqual(handles,list(HANDLES[:len(expected)]),(key,scroll))
                self.assertEqual([text for _,text in calls],[f'row-{i}'.encode() for i in expected])
            self.assertEqual(seen,set(range(count)),key)
