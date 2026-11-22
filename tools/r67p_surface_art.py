"""Verify r67.15p atlas ownership, disposition the historical ports, and build the recording popup port."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
import mmap
from pathlib import Path
import struct

from tools import r67_15l_native_coverage as wheel
from tools.first_save_graphics_port import get_english_pixels, translated_asset
from tools.iso9660_patch import find_record, index_iso
from tools.r67m_cumulative import sha_file
from tools.r67n_release import GROUP4_SHA256, WHEEL_SHA256
from tools.tmx import decode_tmx_rgba, find_tmx_entry

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "local"
O_ISO = LOCAL / "r67o-release/67.15o-cumulative-official-diagnostic.iso"
O_ISO_SHA256 = "049b68c70c74f99b195975000c90e064b5106cbe18cf0dc89f87b44526081b13"
O_ELF_SHA256 = "fd4760a3c96260ef0fde8cf113a9cc49d46fe732a7f7b0087357f612f1182787"
K_ISO = LOCAL / "r67-candidates/67.15k-description-word-wrap.iso"
K_ELF = LOCAL / "r67-15k-description-word-wrap.elf"
JP_ISO = LOCAL / "r67n-sources/ps2/Kowloon Youma Gakuenki re-charge (Japan).iso"
JP_ISO_SHA256 = "29e305e344c146e1416cca498e2d288718075380552d37886d9b469717779476"
PS4_BUNDLES = LOCAL / "r67-15k-source-recovery/extracted/uroot/Media/StreamingAssets/BLBRD"
HISTORICAL_ROOT = LOCAL / "r67-english-graphics-85"
HISTORICAL_REPORT = LOCAL / "r67-english-graphics-85-report.json"
SOURCE_MANIFEST = ROOT / "translations/r67_graphics_owners.json"
WHEEL_REPORT = ROOT / "translations/r67_15l_native_coverage.json"
POPUP_PATH = "BLBRD/B_GP059.BIN"
POPUP_BEFORE_SHA256 = "2dd9d977b3bcd4c5cecfa29bbc5902b93b044461156b25c82810a4355527362d"
POPUP_AFTER_SHA256 = "f0ba2ba39ea16940c46e3a73d3966b41a346448f06a536f04dcd68c99c55ffb3"
POPUP_BUNDLES = {
    "b_gp059": "5060b99e77993ca7de609dcbd5008935dc10ea968a2b9ce05423c12ff0243ae5",
    "b_gp059_en": "db29847ddf47bde1624147ea9e8a474a65d1ac05d6174a56ab3ca32273e77ac9",
}
ELF_BIAS = 0xFFF80
FRAME_COUNTS = {
    1: 146, 2: 164, 3: 66, 4: 182, 6: 58, 7: 86, 8: 66, 10: 12, 13: 176,
    17: 6, 18: 10, 20: 68, 21: 4, 22: 12, 54: 20, 55: 16, 56: 18, 59: 6,
}

# The windows pin the actual resource/display paths, including the page's state
# table dispatch, native action masks, sprite creation, UVs and frame timing.
POPUP_OWNERS = {
    (0x292920, 0x293044): "bd625cdf841b9500475f2aec477d9f8c3ab4195456d2d66f97c831e55b433e51",
    (0x106014, 0x106034): "5bfa9fd6e4f4e5c39a676ec1ae506d078d690d52665cbcd41cd82f14de7bbf5c",
    (0x106194, 0x106234): "9c3e349cd9e993d98d059e9e322454efffa3d8c072be26cddba61b2949df5da9",
    (0x473B90, 0x4744F0): "9070b5e873e2d07fcdd1a80d13ba541b3e7a4c03266b8d931aeb9533d19c8185",
    (0x483F90, 0x483FC0): "e72affcb5fde9c3c832ee2b5cd28a290be534c0a7d8ab0d99524ce79184b5573",
}


def digest(raw) -> str:
    return sha256(raw).hexdigest()


def read_artwork(path: Path, expected_sha256: str | None = None) -> tuple[bytes, dict[str, bytes]]:
    """Read installed ELF and all BLBRD containers via the nested ISO directory."""
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as image:
        if expected_sha256 and digest(image) != expected_sha256:
            raise ValueError(f"ISO identity changed: {path}")
        _, outer = index_iso(image)
        exe = find_record(outer, "SLPM_665.11")
        elf_start = exe.extent * 2048
        elf = bytes(image[elf_start:elf_start + exe.size])
        base = find_record(outer, "DATA.CVM").extent * 2048 + 0x1800
        _, records = index_iso(image, base)
        containers = {}
        for record in records:
            if record.path.startswith("BLBRD/") and record.path.endswith(".BIN"):
                start = base + record.extent * 2048
                containers[record.path] = bytes(image[start:start + record.size])
        return elf, containers


def _word(elf, address: int) -> int:
    return struct.unpack_from("<I", elf, address - ELF_BIAS)[0]


def _cstring(elf, address: int) -> str:
    offset = address - ELF_BIAS
    if not 0 <= offset < len(elf):
        raise ValueError(f"Native string address outside the ELF: {address:#x}")
    return elf[offset:offset + 0x40].split(b"\0", 1)[0].decode("ascii")


def texture_owner(elf: bytes, group: int, name: str, size: tuple[int, int]) -> dict:
    """Resolve the loaded texture index and every native descriptor crop using it."""
    filename_owner = 0x43A030 + group * 4
    filename = _cstring(elf, _word(elf, filename_owner))
    if filename != f"BLBRD/B_GP{group:03d}.BIN":
        raise ValueError(f"Native group filename drift: {group}")
    lookup_owner = 0x4409F0 + group * 4
    resources = _word(elf, lookup_owner)
    texture_name = "BLBRD/" + name.removesuffix(".TMX")
    matches = []
    for index in range(30):
        resource = _cstring(elf, _word(elf, resources + index * 4))
        if not resource:
            break
        if resource == texture_name:
            matches.append(index)
    if len(matches) != 1:
        raise ValueError(f"Native texture-name selection unresolved: {texture_name}")
    texture_index = matches[0]
    group_owner = 0x485240 + group * 4
    descriptors = _word(elf, group_owner)
    regions = defaultdict(list)
    for sprite_id in range(FRAME_COUNTS[group]):
        descriptor = descriptors + sprite_id * 8
        address, count = struct.unpack_from("<II", elf, descriptor - ELF_BIAS)
        if count > 256 or (count and address == 0):
            raise ValueError(f"Invalid native descriptor {group}:{sprite_id}")
        for frame_index in range(count):
            frame_va = address + frame_index * 48
            fields = struct.unpack_from("<HH11f", elf, frame_va - ELF_BIAS)
            if fields[1] != texture_index:
                continue
            geometry = fields[2:10]
            if any(not math.isfinite(value) for value in geometry):
                raise ValueError(f"Non-finite sprite geometry {group}:{sprite_id}/{frame_index}")
            w, h, px, py, u0, v0, u1, v1 = geometry
            # Coordinates are recorded in atlas pixels, including flipped or
            # intentionally extended native UVs, where present.
            crop = (u0 * size[0], v0 * size[1], u1 * size[0], v1 * size[1])
            regions[(crop, (w, h), (px, py))].append([sprite_id, frame_index, frame_va])
    rows = [
        {"uv_in_atlas_pixels": crop, "frame_dimensions": dimensions, "pivot": pivot,
         "sprite_id_frame_number_frame_va": consumers}
        for (crop, dimensions, pivot), consumers in regions.items()
    ]
    return {"container": filename, "native_loader_va": 0x105FE0,
            "native_name_loader_va": 0x106110, "native_sprite_constructor_va": 0x107D60,
            "filename_pointer_va": filename_owner,
            "texture_name_pointer_va": resources + texture_index * 4,
            "texture_registry_pointer_va": lookup_owner,
            "sprite_registry_pointer_va": group_owner, "sprite_table_va": descriptors,
            "native_texture_index": texture_index, "sprite_frame_regions": rows}


def verify_hant_recording_owner(elf: bytes) -> dict:
    for (start, end), expected in POPUP_OWNERS.items():
        if digest(elf[start - ELF_BIAS:end - ELF_BIAS]) != expected:
            raise ValueError(f"H.A.N.T. recording owner changed at {start:#x}")
    owner = texture_owner(elf, 59, "GRP059/GP059_00.TMX", (512, 512))
    region = next((row for row in owner["sprite_frame_regions"]
                   if [0, 0, 0x473B90] in row["sprite_id_frame_number_frame_va"]), None)
    if (region is None or region["uv_in_atlas_pixels"] != (0, 40, 272, 208)
            or region["frame_dimensions"] != (272, 168) or region["pivot"] != (136, 84)):
        raise ValueError("H.A.N.T. recording owner lost the native popup crop")
    owner.update(loader_call=0x2929F8, sprite_constructor_call=0x292B48,
                 input_branches=[0x292F14, 0x292F3C], source="installed ELF")
    return owner


def build_overlays(
    source_iso: Path, ps4_bundles: Path = PS4_BUNDLES,
) -> dict[str, bytes]:
    """Build the authorized, source-pinned same-extent H.A.N.T. recording artwork."""
    elf, containers = read_artwork(source_iso, O_ISO_SHA256)
    if digest(elf) != O_ELF_SHA256:
        raise ValueError("Installed r67.15o ELF identity changed")
    verify_hant_recording_owner(elf)
    before = containers[POPUP_PATH]
    if digest(before) != POPUP_BEFORE_SHA256:
        raise ValueError("H.A.N.T. recording container preimage changed")
    for name, expected in POPUP_BUNDLES.items():
        if digest((ps4_bundles / name).read_bytes()) != expected:
            raise ValueError(f"Official H.A.N.T. recording source changed: {name}")
    jp, en, size, jp_sha, en_sha = get_english_pixels(ps4_bundles, 59, 0)
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    row, = [row for row in manifest["assets"] if (row["group"], row["index"]) == (59, 0)]
    if (jp_sha, en_sha) != (row["jp_pixel_sha256"], row["en_pixel_sha256"]):
        raise ValueError("Official H.A.N.T. recording pixel preimage changed")
    after, evidence = translated_asset(before, jp, en, size, 59, 0)
    if (evidence["result_sha256"] != POPUP_AFTER_SHA256
            or evidence["result_sha256"] != row["expected_output_sha256"]):
        raise ValueError("Historical H.A.N.T. recording port did not reproduce")
    entry = find_tmx_entry(before, evidence["texture"])
    first = entry.palette_offset
    end = entry.pixel_offset + entry.pixel_bytes
    if before[:first] != after[:first] or before[end:] != after[end:]:
        raise ValueError("H.A.N.T. recording port escaped native palette and image bytes")
    return {POPUP_PATH: after}


def verify_wheel(elf: bytes, texture: bytes) -> dict:
    """Re-run inherited wheel descriptor/selector proof against the installed executable."""
    if digest(texture) != WHEEL_SHA256:
        raise ValueError("Installed wheel texture fingerprint changed")
    expected = json.loads(WHEEL_REPORT.read_text())
    frames = wheel._group1_frames(elf)
    calls = wheel._direct_calls(elf)
    # The inherited harness requires the complete approved ELF. Its seeded mapper
    # reads only this function and dispatch table. Prove both match the installed
    # code/data before executing those identical bytes through that harness.
    approved = K_ELF.read_bytes()
    for start, end in ((0x154880, 0x154960), (0x77C260, 0x77C284)):
        lo, hi = start - ELF_BIAS, end - ELF_BIAS
        if elf[lo:hi] != approved[lo:hi]:
            raise ValueError(f"Installed wheel mapper preimage changed at {start:#x}")
    selections = wheel.execute_selection_mapper(approved)["results"]
    checks = {
        "resource_binding": wheel._resource_binding(elf),
        "selection_label_crosswalk": wheel._native_selection_crosswalk(
            elf, frames, wheel.SELECTION_SLOTS, calls),
        "scenario_slot_initialization": wheel._scenario_event_slot_initialization(
            elf, wheel.SELECTION_SLOTS),
        "wheel_variant_routing": wheel._wheel_variant_routing(elf, frames),
        "adv_task_creation_route": wheel._adv_creation_route(elf, calls),
        "task_command_label_branches": wheel._mode_branches(elf),
    }
    if (frames != expected["group1"]["resource_records"]
            or any(result != expected[key] for key, result in checks.items())):
        raise ValueError("Installed wheel native routing or UV geometry changed")
    if any(case["command"] != case["expected_command"]
           or case["return_value"] != case["expected_return"] for case in selections):
        raise ValueError("Installed wheel native mapper selection changed")
    return {"frames": sum(len(row["frames"]) for row in frames),
            "mapper_cases": len(selections), "forced_modes": 8,
            "texture_sha256": WHEEL_SHA256, "normal_and_forced_mode": checks["wheel_variant_routing"],
            "mapper_executions": selections,
            "evidence_boundary": "ELF dispatch and frame geometry, bounded native mapper, exact installed artwork. GPU and gameplay require playthrough."}


# Contact-sheet findings refer to decoded PS2 pixels. The owner lookup above
# independently supplies actual sprite IDs and crops for each individual row.
HOLD_DETAILS = {
    (1, 0): ("Dungeon HUD frame, effects and icon atlas",
             "No specific Japanese label confirmed in the native HUD crops. Full-atlas port also changes protected wheel container."),
    (2, 1): ("Combat panel with baked Critical and Treasure labels",
             "English labels are visible in the atlas. Trace which combat state and exact subframes expose both labels, and check adjacent L1/AFK visuals before replacing the broad texture."),
    (3, 0): ("Baked profile form with dozens of Japanese headings",
             "PS2 profile form also uses localized executable text. Identify the native states sampling each printed field and whether ported fields duplicate or cover the live text."),
    (3, 1): ("Active/Passive Skill, stat list and control micro-labels",
             "JP-to-PS2 alpha match 0.76801. The broad port requires a crop-by-crop comparison of skill and help cases against live text and stock controls."),
    (3, 2): ("Confirmation window with Japanese question and Yes/No buttons",
             "Accepted PS2 confirm flow already draws English words and has a separate focus renderer. Trace animated control ownership before substituting baked English."),
    (3, 4): ("Facsimile profile, skill panes and character portrait",
             "Need the profile state proving whether both skill panes are sampled alongside live labels. Whole atlas also changes the portrait."),
    (4, 6): ("Ammo labels and shine overlay",
             "Protected approved Group 4. Verify ammo-state text and animation crops in a newly approved atlas change."),
    (4, 12): ("Weapon, equipment and item class labels",
              "Protected approved Group 4. Historical English alpha fit is 0.49294. Each category needs a verified crop and read order before review."),
    (4, 14): ("Native numeric/stat/attribute labels",
              "Protected approved Group 4. The historical port would replace the later bounded art with arrows and different packed labels; native 15f mapping governs."),
    (4, 18): ("Storage location banner, vest/room selectors and prompts",
              "Protected approved Group 4. Earlier full phrase did not fit native 128 px cells. Installed 15b bounded port is different by design."),
    (4, 19): ("Items action captions for Details, Compound, Swap, Discard, Recycle",
              "Protected approved Group 4. Historical action labels substitute different words and alpha coverage; installed action mapping governs."),
    (6, 0): ("Gold map/radar frame and destination instructions",
             "Need active route witnesses for the bottom instructions and their control labels; full port also affects the approved map/radar visuals."),
    (7, 0): ("Companion/dungeon options, stamps, prompts and action rectangle",
             "Historic geometry exception: English alpha match 0.80497. Translate only verified companion prompts after matching each live selector and indicator crop."),
    (8, 3): ("Shopping controls with price, quantity and checkout",
             "Historic geometry exception: English alpha match 0.88842. Identify the live purchase and cancel sprite routes and verify control binding."),
    (8, 7): ("Shopping equipment-stat labels and ammo icon",
             "Historic geometry exception: English alpha match 0.49686. Different glyph widths and the native stat row allocation require per-label proof."),
    (10, 0): ("Inventory strip with small keyboard/menu prompts",
              "JP-to-PS2 alpha match 0.68046. Need the native item state and each micro-label crop to distinguish platform-specific text and live executable overlay."),
    (10, 2): ("Order/list backing and total fields",
              "Field translations visible in lower strip. Confirm which native columns actually display these baked strings and whether separate total controls overlap."),
    (13, 4): ("Status/skill key tiles, including compact help labels",
              "Numerous independently sampled tiles. Need ID-to-state and crop proof for each prompt before using the broad port."),
    (17, 0): ("Current Items/Room/Special labels and menu prompts",
              "Inherited inventory/item panels use layered live text and approved controls. Identify states displaying the baked captions and preserve accepted fit."),
    (18, 3): ("Save, Load and Back on a shared banner",
              "Current baked controls already read LOAD SAVE BACK. Preserve the later save-art owner and its order; the earlier port changes the label layout."),
    (20, 2): ("H.A.N.T. booklet and controller/status accents",
              "Accepted H.A.N.T. surface. No confirmed need to replace the printed booklet metadata. Preserve loaded neighbor GP020_03 menu repaint."),
    (21, 0): ("H.A.N.T. green panel with map/status labels",
              "English labels visibly differ, including Boss and Save Point. Need verified owning page and sampled captions/cursor destinations for each translated subregion."),
    (22, 1): ("New Game/Load Game text and yin-yang variants",
              "Accepted title path has separate GP088 presentation and native focus/backing. Verify whether this secondary atlas still presents visible Japanese before changing it."),
    (22, 2): ("Two vertical title-logo variants",
              "Historical English geometry 0.69078. Identify the live secondary title owner and its layout independently of accepted GP088; port changes silhouette and width."),
}
CARD_LABELS = {
    54: ("No Data", "Uneme", "Monozane", "Okorobi", "Hitsugi", "Shihotaru", "Ubuya",
         "Naoroi", "Araragi", "Saniwa", "Kagachi", "Kawahori", "Fuyu", "Hiruko", "Umara",
         "Sasagani", "Tsuchikure", "Himorogi", "Iwakura", "Relic Dawn"),
    55: ("", "Izanami", "Kagutsuchi", "Amaterasu", "Tsukuyomi", "Iware", "Ninigi", "Onamuchi",
         "Futsunushi", "Yamata-no-Orochi", "Izanagi", "Takeminakata", "Susanoo", "Kamimusubi",
         "Arahabakigami", "Anubis"),
    56: ("", "Kotaro Minakami", "Teito Amori", "Toya Izawa", "Mitsuru Kandori", "Sakie Futaki",
         "Hosuke Sumiki", "Taizo Higo", "Shigemi Sudo", "Kamachi Toride", "Rika Shiina",
         "Kensuke Mariya", "Moriya Monobe", "Thoth", "Mackensen", "Phantom", "Yamato Yunagi"),
}


def disposition(group: int, index: int, current_status: str) -> dict:
    protections = {
        1: "Exact installed r67.15l wheel container lock",
        3: "Accepted startup/name/confirmation rendering owners",
        4: "Exact gameplay-approved r67.15k Group 4 container lock",
        18: "Accepted save UI and stock save namespace",
        20: "Accepted r66-derived GP020_03 visual repaint and H.A.N.T. owners",
        22: "Accepted startup/title rendering owners",
    }
    protection = protections.get(group, "Keep original native group IDs, UVs, dimensions and surrounding bytes")
    if group == 59:
        return {"decision": "installed for diagnostic",
                "visible_content": "Recording states Pause / Record / Saving and Saved into H.A.N.T. popup with View Data / View Later",
                "protection": protection,
                "older_port": "Valid, with exact official source and native popup route and crop proven",
                "blocker": None}
    if current_status == "historical_port":
        return {"decision": "retained existing port",
                "visible_content": {
                    3: "Store in room banner", 5: "Item panel and control labels",
                    15: "Store in room background", 16: "Store in assault vest background",
                    17: "Items Obtained heading",
                }[index],
                "protection": protection,
                "older_port": "Same decoded image as the installed approved art",
                "blocker": None}
    if group == 1 and index != 0:
        return {"decision": "retained newer wheel art",
                "visible_content": {
                    2: "Default emotion pairs", 3: "Gold single emotion labels and wheel layers",
                    8: "Eight animated emotion glows", 10: "Forced-mode paired plaques",
                }[index],
                "protection": protection,
                "older_port": "Superseded by the bounded r67.15l English palette and per-UV art",
                "blocker": "Whole-texture port changes the wheel's exact payload and replaces the bounded English variants."}
    if group in CARD_LABELS:
        label = CARD_LABELS[group][index]
        if (group, index) == (54, 0):
            return {"decision": "retained existing English",
                    "visible_content": "Native green card already displays No Data in English",
                    "protection": protection,
                    "older_port": "Changes the already-English lettering, color and scanline treatment",
                    "blocker": "No untranslated label to address. A different artwork style is outside this pass."}
        return {"decision": "held",
                "visible_content": f"Green card portrait with baked Japanese name, historical card labeled {label}",
                "protection": protection,
                "older_port": "Official JP/EN pair and same native crop; gameplay consumer and selected presentation remain unproven",
                "blocker": f"Sprite {group}:{index} resolves by UV, but its consuming state and real selection path have not been established. Verify the rendered portrait and name on that path."}
    content, blocker = HOLD_DETAILS[group, index]
    reason = ("Superseded; the candidate uses a different approved/native layout" if current_status == "different_version"
              else "Suitable only after the stated sampled-state check")
    return {"decision": "held", "visible_content": content, "protection": protection,
            "older_port": reason, "blocker": blocker}


def _tmx_fingerprints(container: bytes, name: str) -> tuple[tuple[int, int], str, str, tuple[int, int]]:
    entry = find_tmx_entry(container, name)
    start, end = entry.base_offset, entry.base_offset + entry.chunk_size
    return (entry.width, entry.height), digest(container[start:end]), digest(
        decode_tmx_rgba(container, entry)), (start, end)


def artwork_census(candidate: Path, *, ps4_bundles: Path = PS4_BUNDLES,
                   source_only: bool = False) -> dict:
    """Reconcile every historical candidate and independently verify installed resources."""
    _, original = read_artwork(JP_ISO, JP_ISO_SHA256)
    _, approved = read_artwork(K_ISO, wheel.APPROVED_ISO_SHA256)
    baseline_elf, baseline = read_artwork(O_ISO, O_ISO_SHA256)
    if digest(baseline_elf) != O_ELF_SHA256:
        raise ValueError("Installed r67.15o ELF identity changed")
    if source_only:
        candidate = O_ISO
        installed_elf, installed = baseline_elf, baseline
    else:
        installed_elf, installed = read_artwork(candidate)
    if approved.keys() != baseline.keys() or baseline.keys() != installed.keys() or len(installed) != 150:
        raise ValueError("BLBRD inventory differs from 150 source containers")
    if {path for path in approved if approved[path] != baseline[path]} != {"BLBRD/B_GP001.BIN"}:
        raise ValueError("Approved and baseline BLBRD delta differs from the wheel-only port")
    allowed_changes = set() if source_only else {POPUP_PATH}
    if {path for path in baseline if baseline[path] != installed[path]} != allowed_changes:
        raise ValueError("Installed BLBRD delta differs from the verified native popup scope")
    if digest(installed["BLBRD/B_GP004.BIN"]) != GROUP4_SHA256:
        raise ValueError("Approved Group 4 artwork changed")
    popup_expected = POPUP_BEFORE_SHA256 if source_only else POPUP_AFTER_SHA256
    if digest(installed[POPUP_PATH]) != popup_expected:
        raise ValueError("Installed H.A.N.T. popup does not match the expected payload")
    popup_owner = verify_hant_recording_owner(installed_elf)
    wheel_report = verify_wheel(installed_elf, installed["BLBRD/B_GP001.BIN"])

    manifest = json.loads(SOURCE_MANIFEST.read_text())["assets"]
    report = json.loads(HISTORICAL_REPORT.read_text())["assets"]
    if len({(row["group"], row["index"]) for row in manifest}) != 85 or len(report) != 85:
        raise ValueError("Historical artwork census does not contain 85 unique candidates")
    historical_by_name = {row["texture"]: row for row in report}
    paths = {f"BLBRD/B_GP{row['group']:03d}.BIN" for row in manifest}
    historical = {path: (HISTORICAL_ROOT / path).read_bytes() for path in paths}
    bundle_hashes = {}
    for group in FRAME_COUNTS:
        for suffix in ("", "_en"):
            name = f"b_gp{group:03d}{suffix}"
            bundle_hashes[name] = digest((ps4_bundles / name).read_bytes())

    rows = []
    for manifest_row in manifest:
        group, index = manifest_row["group"], manifest_row["index"]
        name = f"GRP{group:03d}/GP{group:03d}_{index:02d}.TMX"
        path = f"BLBRD/B_GP{group:03d}.BIN"
        historical_row = historical_by_name[name]
        jp_size, jp_chunk, jp_rgba, offset = _tmx_fingerprints(original[path], name)
        o_size, o_chunk, o_rgba, baseline_offset = _tmx_fingerprints(baseline[path], name)
        historical_size, historical_chunk, historical_rgba, historical_offset = _tmx_fingerprints(
            historical[path], name)
        p_size, p_chunk, p_rgba, installed_offset = _tmx_fingerprints(installed[path], name)
        if len({jp_size, o_size, p_size, historical_size}) != 1 or len({
                offset, baseline_offset, installed_offset, historical_offset}) != 1:
            raise ValueError(f"Native texture layout drift: {name}")
        if (jp_chunk != historical_row["source_tmx_sha256"]
                or historical_chunk != historical_row["result_tmx_sha256"]
                or historical_row["result_sha256"] != manifest_row["expected_output_sha256"]):
            raise ValueError(f"Historical port changed: {name}")
        _, _, size, jp_ps4_sha, en_ps4_sha = get_english_pixels(ps4_bundles, group, index)
        if (jp_ps4_sha, en_ps4_sha) != (manifest_row["jp_pixel_sha256"], manifest_row["en_pixel_sha256"]):
            raise ValueError(f"Current owned official source pixels differ from historical manifest: {name}")
        status = "pristine" if o_rgba == jp_rgba else "historical_port" if o_rgba == historical_rgba else "different_version"
        desc = disposition(group, index, status)
        if source_only and group == 59:
            desc["decision"] = "validated for diagnostic"
        owner = texture_owner(installed_elf, group, name, p_size)
        row = {"texture": name, "dimensions": p_size, "tmx_byte_range_in_container": offset,
               "baseline_pixel_status": status, "ps2_owner": owner,
               "payloads": {
                   "pristine_ps2": {"tmx_sha256": jp_chunk, "rgba_sha256": jp_rgba},
                   "r67_15o": {"tmx_sha256": o_chunk, "rgba_sha256": o_rgba},
                   "historical_port": {"tmx_sha256": historical_chunk, "rgba_sha256": historical_rgba},
                   "installed": {"tmx_sha256": p_chunk, "rgba_sha256": p_rgba},
               },
               "official_ps4_source": {
                   "texture": f"GP{group:03d}_{index:02d}", "dimensions": size,
                   "jp": {"bundle": f"b_gp{group:03d}", "bundle_sha256": bundle_hashes[f"b_gp{group:03d}"],
                          "rgba_sha256": jp_ps4_sha},
                   "en": {"bundle": f"b_gp{group:03d}_en", "bundle_sha256": bundle_hashes[f"b_gp{group:03d}_en"],
                          "rgba_sha256": en_ps4_sha},
               },
               "historical_registration_checks": {
                   key: historical_row[key] for key in ("jp_geometry_dice", "en_geometry_dice",
                                                        "manual_source_layout_review", "text_repaint_exception")
               }, **desc}
        rows.append(row)
    counts = Counter(row["baseline_pixel_status"] for row in rows)
    if counts != {"pristine": 72, "historical_port": 5, "different_version": 8}:
        raise ValueError("Baseline decoded artwork counts differ from the audit")
    return {"baseline_iso_sha256": O_ISO_SHA256, "installed_iso": str(candidate), "source_only": source_only,
            "installed_iso_sha256": O_ISO_SHA256 if source_only else sha_file(candidate),
            "installed_elf_sha256": digest(installed_elf), "wheel": wheel_report,
            "group4_sha256": GROUP4_SHA256, "hant_recording_popup": popup_owner,
            "baseline_dispositions": counts, "item_decision_counts": Counter(row["decision"] for row in rows),
            "approved_to_baseline_changed_containers": ["BLBRD/B_GP001.BIN"],
            "baseline_to_installed_changed_containers": sorted(allowed_changes),
            "containers": [{"path": path, "baseline_sha256": digest(baseline[path]),
                            "installed_sha256": digest(installed[path])} for path in sorted(installed)],
            "assets": rows}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, default=O_ISO)
    parser.add_argument("--ps4-bundles", type=Path, default=PS4_BUNDLES)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("use a new report path")
    evidence = artwork_census(args.iso, ps4_bundles=args.ps4_bundles, source_only=args.source_only)
    args.report.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
