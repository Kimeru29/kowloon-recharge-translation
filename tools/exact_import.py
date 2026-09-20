from __future__ import annotations

from typing import Any

from tools.localization import DcLocalization
from tools.mtx import MtxFile, MtxReplacement


class ExactImportError(ValueError):
    """Raised when an exact-tier import cannot be proven safe."""


def import_exact_mtx(ps2_raw: bytes, ps4_raw: bytes, dc: dict[str, Any]) -> bytes:
    """Import official English into a byte-identical MTX or fail closed."""

    if ps2_raw != ps4_raw:
        raise ExactImportError("Exact MTX import requires byte-identical PS2 and PS4 sources")

    try:
        localization = DcLocalization.from_json(ps2_raw, dc)
        original = MtxFile.parse(ps2_raw)
        replacements = tuple(
            MtxReplacement(group.anchor, group.replace_end, group.encoded_replacement())
            for group in localization.groups
        )
        result = original.apply_replacements(replacements).compile()
        MtxFile.parse(result)
    except (KeyError, TypeError, ValueError) as exc:
        raise ExactImportError(str(exc)) from exc

    return result
