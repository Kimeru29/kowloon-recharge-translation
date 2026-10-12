"""Run the real callsites, including paths skipped by r67.14x."""
import struct
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "local/r67-14t-lion-and-tablets.elf"
TASK, GREEN, STACK = 0x1000000, 0x7A5060, 0x1F00000


class Machine:
    def __init__(self, elf, record=2, slot=0, state=11, active=True):
        self.elf = elf
        self.r = [0] * 32
        self.r[16], self.r[17], self.r[29] = TASK, 0x1100000, STACK
        self.r[4:8] = [2, 0x68 + slot, 0x43AD0000432C0000, 0]
        self.r[31] = 0xABC000
        self.mem = {}
        self.writes = []
        self.calls = []
        self.put(TASK + 4, record & 0xFFFF, 2)
        self.put(TASK + 2, state, 2)
        self.put(TASK + 0x2F8, slot & 0xFFFF, 2)
        self.put(TASK + 0x58, GREEN if active else 0)
        self.put(GREEN + 0x93, 1, 1)
        self.put(GREEN + 0x82, 2, 2)
        self.put(GREEN + 0x84, 0x68 + slot, 2)
        self.dirty()
        self.writes.clear()

    def put(self, at, value, size=4):
        for n in range(size):
            self.mem[at+n] = (value >> (n*8)) & 255
        self.writes.append((at, size))

    def get(self, at, size=4):
        return sum(self.mem.get(at+n, 0) << (n*8) for n in range(size))

    def dirty(self):
        # An earlier long AFK/L1 consumer can leave the shared metadata changed.
        for at in (0x450AC4, 0x450AF4):
            for n, value in enumerate((224., 144., 52., 141.)):
                self.put(at+n*4, struct.unpack('<I', struct.pack('<f', value))[0])
        for frame in range(3):
            for n, value in enumerate((222., 130., 52., 130.)):
                self.put(0x450B24+frame*48+n*4,
                         struct.unpack('<I', struct.pack('<f', value))[0])

    def word(self, pc):
        off = pc - 0xFFF80 if pc < 0x902F00 else pc - 0x902F00 + 0x803150
        return struct.unpack_from('<I', self.elf, off)[0]

    def run(self, start, stop):
        pc, pending = start, None
        for _ in range(600):
            if pc == stop:
                return
            if pc in (0x107D60, 0x167980):
                self.calls.append((pc, tuple(self.r[4:8]), dict(self.mem)))
                if pc == 0x167980:
                    # Model a later native callback mutating resources.
                    self.dirty()
                self.r[2] = GREEN
                pc = self.r[31]
                continue
            w = self.word(pc)
            op, rs, rt = w >> 26, (w >> 21) & 31, (w >> 16) & 31
            imm = w & 65535
            signed = imm - 65536 if imm & 32768 else imm
            next_target, jump = pending, None
            pending = None
            if op == 3:
                self.r[31] = pc + 8
                jump = (w & 0x3FFFFFF) * 4
            elif op in (4, 5):
                equal = self.r[rs] == self.r[rt]
                jump = pc + 4 + signed*4 if equal == (op == 4) else pc + 8
            elif op == 0:
                fn, rd, sh = w & 63, (w >> 11) & 31, (w >> 6) & 31
                if fn == 8:
                    jump = self.r[rs]
                elif fn in (33, 45):
                    self.r[rd] = (self.r[rs] + self.r[rt]) & 0xFFFFFFFFFFFFFFFF
                elif fn == 0:
                    self.r[rd] = (self.r[rt] << sh) & 0xFFFFFFFF
                else:
                    raise AssertionError(f'unsupported {pc:#x} {w:#x}')
            elif op == 15:
                self.r[rt] = imm << 16
            elif op == 13:
                self.r[rt] = self.r[rs] | imm
            elif op == 9:
                self.r[rt] = (self.r[rs] + signed) & 0xFFFFFFFF
            elif op == 11:
                self.r[rt] = int((self.r[rs] & 0xFFFFFFFF) < (signed & 0xFFFFFFFF))
            elif op in (33, 35, 36, 37, 55):
                size = {33:2, 35:4, 36:1, 37:2, 55:8}[op]
                value = self.get(self.r[rs] + signed, size)
                if op == 33 and value & 32768:
                    value = (value - 65536) & 0xFFFFFFFF
                self.r[rt] = value
            elif op in (43, 63):
                self.put(self.r[rs] + signed, self.r[rt], 8 if op == 63 else 4)
            else:
                raise AssertionError(f'unsupported {pc:#x} {w:#x}')
            self.r[0] = 0
            pending = jump
            pc = next_target if next_target is not None else pc + 4
        raise AssertionError('native helper did not return')

    def shape(self, slot):
        return tuple(struct.unpack('<f', struct.pack('<I', self.get(0x450AC4+slot*48+n*4)))[0]
                     for n in range(4))


@unittest.skipUnless(SOURCE.exists(), 'requires local accepted t ELF')
class EventLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SOURCE.read_bytes()
        from tools.r67_14y_event_lifecycle import apply
        cls.candidate, cls.report = apply(cls.source)

    def test_initial_creation_restores_geometry_before_native_allocation(self):
        for slot in (0, 1):
            m = Machine(self.candidate, slot=slot, state=9)
            args = tuple(m.r[4:8])
            m.run(0x165E60, 0x165E68)
            self.assertEqual(m.shape(slot), (288., 80., (67., 125.)[slot], 77.))
            self.assertEqual(m.calls[0][1], args, '64-bit packed XY must survive')
            at = 0x450AC4 + slot*48
            snapshot = m.calls[0][2]
            self.assertEqual(bytes(snapshot[at+n] for n in range(16)),
                             struct.pack('<4f',288.,80.,(67.,125.)[slot],77.),
                             'restoration must precede the real constructor')
            self.assertEqual(m.r[29], STACK)

    def test_same_slot_and_later_frames_restore_after_native_callbacks(self):
        for slot in (0, 1):
            m = Machine(self.candidate, slot=slot)
            m.run(0x166820, 0x166828)
            self.assertEqual(m.shape(slot), (288., 80., (67., 125.)[slot], 77.))
            self.assertEqual([x[0] for x in m.calls], [0x167980])
            self.assertEqual(m.r[29], STACK)

    def test_every_event_and_slot_satisfies_same_visible_text_bounds(self):
        for record in range(601):
            for slot in (0, 1):
                m = Machine(self.candidate, record, slot)
                m.run(0x166820, 0x166828)
                _, height, _, pivot = m.shape(slot)
                self.assertEqual(m.shape(slot), (288.,80.,(67.,125.)[slot],77.))
                top = 346. - pivot
                # Native 80-high sprite contains a 56-high rectangular body.
                self.assertGreaterEqual(280., top + 7.)
                self.assertLessEqual(300. + 16., top + height - 24. - 7.)

    def test_afk_and_inactive_tasks_do_not_restore_event_geometry(self):
        for record, state, active in [(r,11,True) for r in range(601,1201)] + [(-1,11,True),
                                       (2,8,True),(2,14,True),(2,11,False)]:
            m = Machine(self.candidate, record, state=state, active=active)
            m.run(0x166820, 0x166828)
            self.assertEqual(m.shape(0), (224.,144.,52.,141.))

    def test_invalid_slots_and_foreign_or_freed_sprites_are_excluded(self):
        for slot in (-1,2,32767):
            m = Machine(self.candidate, slot=slot)
            m.run(0x166820,0x166828)
            self.assertEqual(m.shape(0),(224.,144.,52.,141.))
        for field,value,size in ((0x93,0,1),(0x82,4,2),(0x84,0x6A,2)):
            m = Machine(self.candidate)
            m.put(GREEN+field,value,size)
            m.run(0x166820,0x166828)
            self.assertEqual(m.shape(0),(224.,144.,52.,141.))

    def test_hook_removal_mutations_reproduce_the_missed_restore(self):
        for site,callee in ((0x165E60,0x107D60),(0x166820,0x167980)):
            mutated = bytearray(self.candidate)
            struct.pack_into('<I',mutated,site-0xFFF80,0x0C000000|(callee>>2))
            m = Machine(mutated)
            m.run(site,site+8)
            self.assertNotEqual(m.shape(0),(288.,80.,67.,77.))

    def test_metadata_constant_mutation_is_detectable(self):
        mutated = bytearray(self.candidate)
        helper = int(self.report['hooks'][1]['helper_va'],16)-0x902F00+0x803150
        target = struct.pack('<I',0x3C0F4390)  # lui t7, float(288) high
        at = mutated.index(target,helper)
        mutated[at:at+4] = struct.pack('<I',0x3C0F43A0)
        m = Machine(mutated)
        m.run(0x166820,0x166828)
        self.assertNotEqual(m.shape(0),(288.,80.,67.,77.))

    def test_q_t_immutable_locks_pass_without_masking_any_bytes(self):
        import json
        from tools.r67_14q_approved_lock import verify_approved, MANIFEST
        from tools.r67_14t_approved_ui_lock import verify_ui, MANIFEST as T
        self.assertEqual(verify_approved(self.candidate,json.loads(MANIFEST.read_text()))['approved_regions'],4)
        self.assertEqual(verify_ui(self.candidate,json.loads(T.read_text()))['overwide_rows'],0)


if __name__ == '__main__':
    unittest.main()
