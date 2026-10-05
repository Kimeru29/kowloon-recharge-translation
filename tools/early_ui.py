from __future__ import annotations

from tools.adv_layout import patch_adv_horizontal_layout
from tools.companion_hud import relocated_companion_entries
from tools.dungeon_ui import dungeon_code_references, relocated_dungeon_entries
from tools.elf_strings import ElfFixedStringPatch
from tools.menu_ui import fixed_menu_patches, patch_menu_labels, relocated_menu_entries
from tools.hant_ui import patch_hant_tutorial
from tools.startup_ui import STARTUP_FIXED_PATCHES, build_startup_ui_elf


# Backwards-compatible flattened list used by the CLI and older regression tests.
# The semantic source of truth for menu labels is tools.menu_ui.MENU_LABELS.
EARLY_UI_PATCHES: tuple[ElfFixedStringPatch, ...] = STARTUP_FIXED_PATCHES + fixed_menu_patches()


def build_early_ui_elf(raw: bytes) -> bytes:
    startup = build_startup_ui_elf(raw)
    menus = patch_menu_labels(startup)
    menu_entries = relocated_menu_entries(menus)
    horizontal_adv = patch_adv_horizontal_layout(menus)
    dungeon_entries = relocated_dungeon_entries(horizontal_adv)
    dungeon_refs = dungeon_code_references(horizontal_adv)
    companion_entries = relocated_companion_entries(horizontal_adv)
    translated, _ = patch_hant_tutorial(
        horizontal_adv,
        extra_entries=(*menu_entries, *dungeon_entries, *companion_entries),
        extra_code_references=dungeon_refs,
    )
    return translated
