"""Build a separately versioned description-wrap diagnostic and audit its disc."""
import hashlib
import json
import mmap
from pathlib import Path

from tools import r67_15g_iso_release as g, r67_15h_iso_release as h
from tools import r67_15i_iso_release as i, r67_15j_iso_release as j
from tools import r67_15h_item_layout as old_layout, r67_15h_hant_pool as old_pool
from tools import r67_15k_description_layout as layout
from tools.r67_15h_rofs_audit import audit as audit_rofs
from tools.r67_15g_route_audit import ORIGINAL_ISO
from tools.iso9660_patch import find_record, index_iso, patch_directory_record
from tools.startup_acceptance import verify_startup_candidate

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ELF = j.OUTPUT_ELF
SOURCE_ISO = j.OUTPUT_ISO
SOURCE_ISO_SHA256 = '26ced321471b4415c2a855079c778502ed7c043d2e9467c8c1edc1833b58a079'
OUTPUT_ISO = ROOT / 'local/r67-candidates/67.15k-description-word-wrap.iso'
OUTPUT_ELF = ROOT / 'local/r67-15k-description-word-wrap.elf'
OUTPUT_REPORT = ROOT / 'local/r67-15k-description-word-wrap.json'
OUTPUT_AUDIT = ROOT / 'local/r67-15k-whole-iso-audit.json'
INCOMPLETE_ISO = OUTPUT_ISO.with_suffix('.incomplete')


def prepare(source):
    if hashlib.sha256(source).hexdigest() != layout.SOURCE_SHA256:
        raise ValueError('15j input ELF hash mismatch')
    owners = {'owned_description_calls': tuple(span for span in layout.ALLOWED_SOURCE_RANGES
                                              if span[0] >= 0x68)}
    return h._prepare_stages(source, (('description_wrap', layout.build, owners),))


def runtime_status():
    return {**j.runtime_status(), 'prior_other_j_fixes_user_confirmed': True,
            'description_screenshot_discrepancy_reproduced': False,
            'runtime_verified': False, 'gameplay_approved': False}


def build():
    for path in (OUTPUT_ISO, OUTPUT_ELF, OUTPUT_REPORT, OUTPUT_AUDIT, INCOMPLETE_ISO):
        if path.exists():
            raise FileExistsError(f'Refusing to overwrite release artifact: {path}')
    if g.sha_file(SOURCE_ISO) != SOURCE_ISO_SHA256:
        raise ValueError('15j input ISO hash mismatch')
    source = SOURCE_ELF.read_bytes()
    prepared = prepare(source)
    with SOURCE_ISO.open('rb') as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        exe, offset, *_ = g._installed_records(image)
        if bytes(image[offset:offset + exe.size]) != source:
            raise ValueError('15j installed executable mismatch')
    regenerated_g, g_report = h._compose_pinned_15g()
    regenerated_h = h._prepare_stages(regenerated_g, (
        ('item_layout', old_layout.build, old_layout.ALLOWED_SOURCE_RANGES),
        ('hant_pool', old_pool.build, old_pool.ALLOWED_SOURCE_RANGES)))
    regenerated_i = i.prepare(regenerated_h.candidate)
    regenerated_j = j.prepare(regenerated_i.candidate)
    if regenerated_j.candidate != source:
        raise ValueError('independent 15j reconstruction mismatch')
    approved = g._read_approved_inputs()
    changes = dict(g_report['_changed_bytes'])
    stages = (regenerated_h, regenerated_i, regenerated_j, prepared)
    for stage in stages:
        changes.update(stage.changed_existing)
    preservation = g._verify_15f_preservation(approved.source_elf, prepared.candidate,
                                              g._source_group4_bytes())
    locks = g._verify_static_locks(approved.source_elf, prepared.candidate)
    components = tuple(g_report['components']) + tuple(row for stage in stages for row in stage.components)
    iso_prepared = g.PreparedELF(approved.source_elf, prepared.candidate, components, {}, changes,
                                approved.cvm_sha256, preservation, locks)
    g.source_executable_capacity(len(prepared.candidate))
    g._copy_on_write(g.SOURCE_ISO, INCOMPLETE_ISO)
    with INCOMPLETE_ISO.open('r+b') as stream, mmap.mmap(stream.fileno(), 0) as image:
        _, records = index_iso(image)
        exe = find_record(records, g.EXECUTABLE_NAME)
        offset = exe.extent * g.SECTOR_BYTES
        image[offset:offset + len(prepared.candidate)] = prepared.candidate
        patch_directory_record(image, exe.record_offset, size=len(prepared.candidate))
        image.flush()
    audit = g.audit_finished_iso(g.SOURCE_ISO, INCOMPLETE_ISO, iso_prepared, approved.cvm_sha256)
    rofs = audit_rofs(ORIGINAL_ISO, INCOMPLETE_ISO)
    if rofs['embedded_rofs_file_records'] != 10656:
        raise ValueError('finished ROFS inventory changed')
    startup = verify_startup_candidate(INCOMPLETE_ISO, g.HELP_GRAPHICS)
    static = g._static_reports(prepared.candidate, startup, approved.source_elf)
    if (static['startup_raw']['checks_passed'], static['startup_scoped']['checks_passed']) != (154, 155):
        raise ValueError('startup acceptance changed')
    report = {'release': 'r67.15k', 'status': 'BUILT_STATIC_VERIFIED_RUNTIME_PENDING', **runtime_status(),
              'candidate_iso_sha256': audit['candidate_iso_sha256'],
              'candidate_elf_sha256': hashlib.sha256(prepared.candidate).hexdigest(),
              'input_iso_sha256': SOURCE_ISO_SHA256, 'input_elf_sha256': layout.SOURCE_SHA256,
              'components': list(prepared.components), 'whole_iso_audit': audit,
              'finished_resource_lookup': rofs, 'r67_15f_preservation': preservation,
              'static_locks': locks, **static, 'route_evidence': h._read_route_context()}
    h._write_exclusive(OUTPUT_ELF, prepared.candidate)
    h._write_exclusive(OUTPUT_AUDIT, (json.dumps(audit, indent=2, sort_keys=True) + '\n').encode())
    h._write_exclusive(OUTPUT_REPORT, (json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
    INCOMPLETE_ISO.rename(OUTPUT_ISO)
    return report


if __name__ == '__main__':
    result = build()
    print(json.dumps({key: result[key] for key in ('release', 'candidate_iso_sha256',
                                                   'candidate_elf_sha256', 'whole_iso_audit')}, indent=2))
