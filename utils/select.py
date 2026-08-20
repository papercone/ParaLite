"""
Material selection: pick one material per unit (paragraph / line).

Interactive mode prompts the user per unit; the answer can be:

- ``0`` -> material_0 (e.g. minecraft:white_concrete)
- ``1`` -> material_1 (e.g. minecraft:black_concrete)
- a block id not in the presets, e.g. ``minecraft:gold_block``
"""

from __future__ import annotations

import re

from .map import _normalize

_BLOCK_ID_RE = re.compile(r"^[a-z0-9_]+(?::[a-z0-9_]+)?$")


def materialselect(
    count: int,
    material_0: str,
    material_1: str,
    previews: list[str] | None = None,
) -> list[str]:
    """Prompt the user for one material per unit.

    :param count:      number of units (paragraphs/lines) to ask about.
    :param material_0: normalized block id used for answer ``0``.
    :param material_1: normalized block id used for answer ``1``.
    :param previews:   optional per-unit preview text shown in the prompt.
    :returns:          a list of *count* normalized block ids.
    """
    materials: list[str] = []
    for i in range(count):
        preview = (previews[i] if previews else "")[:44]
        while True:
            ans = (
                input(
                    f"[unit {i + 1}/{count}] 0={material_0} 1={material_1} | {preview} > "
                )
                .strip()
                .lower()
            )
            if ans == "0":
                materials.append(material_0)
                break
            if ans == "1":
                materials.append(material_1)
                break
            if _BLOCK_ID_RE.match(ans):
                materials.append(_normalize(ans))
                break
            print("    please enter 0, 1, or a block id like minecraft:gold_block")
    return materials
