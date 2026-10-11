"""67.06 isolated rendering candidates on verified 67.05.

Only relocate the dungeon target-selection overlay (sprite background, button
assets, and text share a 120.0f screen-space offset), restore the full
'Change target' caption, reflow two lines under Basic Attack icon rows, and
preserve every original chamber story-comment pointer.

Never alter the approved Lion Statue inspection/pedestal/Turn-Based Combat,
global item catalogue name, general AFK/L1 geometry, or memory card namespace.
These candidates REQUIRE visual game validation before release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

from tools.localization import encode_ps2_english
from tools.r67_05_layout import HANT_ROWS, ROTATE_SLOT, ROTATE_LENGTH
from tools.first_save_help import _metadata, _icon_reservations

BASE_SHA = 'a1e5665be7ee71d1ad6b5b9f442d8155abc313a8303537962dc4b4ebe61a8f92'
# Proven M_DngItemUseDraw2 action header: source font position offset and the
# corresponding two buttons/black backing offsets use one consistent X origin.
# VA = file offset + 0xFFF80. Four identical changes translate their grouping
# left by 100 native pixels instead of independently shifting only the words.
TARGET_X = {
    0x1A67FC: (0x3C0242F0, 0x3C0241A0),  # first action sprite 120 -> 20
    0x1A6820: (0x3C0242F2, 0x3C0241A8),  # second sprite 121 -> 21
    0x1A6880: (0x3C0242F0, 0x3C0241A0),  # backing origin 120 -> 20
    0x1A6AD4: (0x3C0242F0, 0x3C0241A0),  # text origin 120 -> 20
}
HANT_REPLACEMENTS = {
    17: '       with AP remaining.',
    20: '     Each action uses AP.',
}
CAPTION_PREVIOUS = 'Target'
CAPTION_RESTORED = 'Change target'


def sha(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def render_text(txt: str) -> bytes:
    return encode_ps2_english(txt, collapse_spaces=False) + b'\0'


def apply(pristine: bytes, base: bytes, pages: list[dict]) -> tuple[bytes, dict]:
    if sha(base) != BASE_SHA:
        raise ValueError('67.05 executable drift; refusing renderer patch')
    fo, va, sz, reserve = (struct.unpack_from('<I', base, i)[0] for i in (0x58, 0x5c, 0x64, 0x68))
    if fo + sz != len(base) or va != 0x902f00 or reserve != 0x100000:
        raise ValueError('Translation PT_LOAD layout changed')

    result = bytearray(base)
    allowed = set(range(0x64, 0x68))
    fixed = {}
    for pos, (expected, new) in TARGET_X.items():
        if struct.unpack_from('<I', base, pos)[0] != expected or struct.unpack_from('<I', pristine, pos)[0] != expected:
            raise ValueError(f'Dungeon-specific x-origin caller changed: {pos:#x}')
        struct.pack_into('<I', result, pos, new)
        allowed.update(range(pos, pos+4))
        fixed[hex(pos)] = [hex(expected), hex(new)]

    existing = render_text(CAPTION_PREVIOUS).ljust(ROTATE_LENGTH, b'\0')
    replacement = render_text(CAPTION_RESTORED).ljust(ROTATE_LENGTH, b'\0')
    if base[ROTATE_SLOT:ROTATE_SLOT + ROTATE_LENGTH] != existing or len(render_text(CAPTION_RESTORED)) > ROTATE_LENGTH:
        raise ValueError('Current Lion Statue caption slot changed')
    result[ROTATE_SLOT:ROTATE_SLOT+ROTATE_LENGTH] = replacement
    allowed.update(range(ROTATE_SLOT, ROTATE_SLOT+ROTATE_LENGTH))

    page = next(p for p in pages if p['key'] == 'basic_attack')
    reserved, _ = _icon_reservations(page, _metadata(pristine, page))
    idx = fo + struct.unpack_from('<I', base, page['descriptor_offset'])[0] - va
    if page['rows'] != len(HANT_ROWS):
        raise ValueError('Native H.A.N.T. page cardinality changed')

    def append(txt: str) -> int:
        if len(result) & 1:result.append(0)
        dest = va + len(result) - fo
        result.extend(render_text(txt))
        return dest

    help_changes = []
    for row, content in HANT_REPLACEMENTS.items():
        if len(content) > 28 or any(c < len(content) and content[c] != ' ' for c in reserved[row]):
            raise ValueError('Basic Attack icon collision at row ' + str(row))
        ptr_idx = idx + row*4
        original_ptr = struct.unpack_from('<I', base, ptr_idx)[0]
        old_content = HANT_ROWS[row]
        old_idx = fo + original_ptr - va
        if base[old_idx:old_idx + len(render_text(old_content))] != render_text(old_content):
            raise ValueError('Basic Attack owner preimage mismatch')
        struct.pack_into('<I', result, ptr_idx, append(content))
        allowed.update(range(ptr_idx, ptr_idx+4))
        help_changes.append({'row':row, 'previous':old_content,'text':content,'owner':hex(ptr_idx)})
    for locked in ('turn_based_combat','entering_battle'):
        item = next(p for p in pages if p['key'] == locked)
        for x in ('descriptor_offset','metadata_descriptor_offset'):
            p=item[x]
            if base[p:p+4] != result[p:p+4]:
                raise ValueError('Accepted ' + locked + ' metadata drift')
        off=fo+struct.unpack_from('<I', base, item['descriptor_offset'])[0]-va
        length=(item['rows']+1)*4
        if base[off:off+length] != result[off:off+length]:
            raise ValueError('Approved Help table changed: ' + locked)

    if len(result)-fo > reserve:
        raise ValueError('Translation memory reserve exceeded')
    struct.pack_into('<I', result, 0x64, len(result)-fo)
    for i,(x,y) in enumerate(zip(base,result)):
        if x != y and i not in allowed:
            raise ValueError(f'Unexpected change in approved executable: {i:#x}')

    return bytes(result), {
        'previous_sha256':sha(base),'sha256':sha(result),
        'previous_size':len(base),'new_size':len(result),
        'native_position_words':fixed,
        'full_caption':CAPTION_RESTORED,
        'basic_attack_changes':help_changes,
        'unresolved':[ 'vertical history actual renderer', 'yellow Lion Statue pickup title width', 'story-comment blue backing needs visual confirmation'],
        'visual_acceptance':False,
        'save_namespace_modified':False,
    }


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('pristine','baseline','manifest','output','report'):
        parser.add_argument('--'+arg,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise FileExistsError('Refusing overwrite')
    raw,report=apply(args.pristine.read_bytes(),args.baseline.read_bytes(),json.loads(args.manifest.read_text())['pages'])
    args.output.write_bytes(raw)
    args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print('67.06 candidate',report['sha256'],report['full_caption'])
if __name__=='__main__':main()
