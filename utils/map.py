"""
general .png to .litematic.

Converts an RGBA image into a grid of Minecraft blocks by matching each
non-transparent pixel to the nearest block color from a curated palette
(concrete / wool / terracotta / a few naturals).
"""

from __future__ import annotations

import numpy as np
from PIL import Image

_WOOL = {
    "white": (233, 236, 236),
    "orange": (240, 118, 19),
    "magenta": (189, 68, 179),
    "light_blue": (58, 175, 217),
    "yellow": (248, 198, 39),
    "lime": (112, 185, 25),
    "pink": (237, 141, 172),
    "gray": (62, 68, 71),
    "light_gray": (142, 142, 134),
    "cyan": (21, 137, 145),
    "purple": (121, 42, 172),
    "blue": (53, 57, 157),
    "brown": (114, 71, 40),
    "green": (84, 109, 27),
    "red": (158, 43, 39),
    "black": (20, 21, 25),
}

_CONCRETE = {
    "white": (207, 213, 214),
    "orange": (224, 97, 1),
    "magenta": (169, 48, 159),
    "light_blue": (35, 137, 198),
    "yellow": (241, 175, 21),
    "lime": (94, 169, 25),
    "pink": (214, 101, 143),
    "gray": (55, 58, 62),
    "light_gray": (125, 125, 115),
    "cyan": (21, 119, 136),
    "purple": (100, 32, 156),
    "blue": (45, 47, 143),
    "brown": (96, 60, 32),
    "green": (73, 91, 36),
    "red": (142, 33, 33),
    "black": (8, 10, 15),
}

_TERRACOTTA = {
    "white": (210, 178, 161),
    "orange": (161, 83, 37),
    "magenta": (149, 87, 108),
    "light_blue": (112, 108, 138),
    "yellow": (186, 133, 35),
    "lime": (103, 117, 52),
    "pink": (160, 77, 78),
    "gray": (57, 42, 35),
    "light_gray": (135, 107, 98),
    "cyan": (86, 91, 91),
    "purple": (118, 70, 86),
    "blue": (74, 60, 91),
    "brown": (96, 59, 31),
    "green": (101, 111, 48),
    "red": (143, 61, 47),
    "black": (37, 22, 16),
}

_NATURALS = {
    "stone": (125, 125, 125),
    "cobblestone": (110, 110, 110),
    "dirt": (134, 96, 67),
    "sand": (219, 205, 162),
    "gravel": (123, 125, 123),
    "oak_planks": (162, 130, 78),
    "bricks": (146, 82, 72),
}

_EXTRAS = {
    "gold_block": (249, 206, 42),
    "iron_block": (220, 220, 220),
    "diamond_block": (98, 219, 214),
    "emerald_block": (41, 199, 94),
    "lapis_block": (30, 72, 154),
    "netherite_block": (68, 57, 55),
    "quartz_block": (236, 231, 220),
    "coal_block": (16, 16, 16),
    "redstone_block": (177, 17, 8),
    "obsidian": (21, 19, 31),
    "glowstone": (249, 199, 108),
    "prismarine": (101, 167, 161),
    "purpur_block": (170, 130, 165),
    "end_stone": (220, 222, 179),
    "moss_block": (89, 131, 58),
}

BLOCK_COLORS: dict[str, tuple[int, int, int]] = {}
for _name, _rgb in _WOOL.items():
    BLOCK_COLORS[f"minecraft:{_name}_wool"] = _rgb
for _name, _rgb in _CONCRETE.items():
    BLOCK_COLORS[f"minecraft:{_name}_concrete"] = _rgb
for _name, _rgb in _TERRACOTTA.items():
    BLOCK_COLORS[f"minecraft:{_name}_terracotta"] = _rgb
for _name, _rgb in _NATURALS.items():
    BLOCK_COLORS[f"minecraft:{_name}"] = _rgb
for _name, _rgb in _EXTRAS.items():
    BLOCK_COLORS[f"minecraft:{_name}"] = _rgb

_PALETTE_IDS = sorted(BLOCK_COLORS.keys())
_PALETTE_RGB = np.array([BLOCK_COLORS[b] for b in _PALETTE_IDS], dtype=np.float32)


def color_of(block_id: str) -> tuple[int, int, int] | None:
    """Return the approximate RGB of a block id, or None if unknown."""
    block_id = _normalize(block_id)
    return BLOCK_COLORS.get(block_id)


def nearest_block(rgb: tuple[int, int, int]) -> str:
    """Return the palette block whose colour is closest to *rgb*."""
    q = np.asarray(rgb, dtype=np.float32)
    d = ((_PALETTE_RGB - q) ** 2).sum(axis=1)
    return _PALETTE_IDS[int(d.argmin())]


def convert_image_to_blocks(
    image: Image.Image,
    background: str | None = None,
    chunk: int = 131072,
) -> list[list[str | None]]:
    """
    Convert an RGBA image into a block grid.

    :param image:      RGBA image (non-transparent pixels are converted).
    :param background: if given, transparent pixels become this block;
                       otherwise they stay ``None`` (air).
    :param chunk:      pixel batch size for the nearest-colour search.
    :returns:          ``grid[row][col]`` -> block id or ``None``.
    """
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    arr = np.asarray(image, dtype=np.uint8)  # (H, W, 4)
    rgb = arr[:, :, :3].astype(np.float32).reshape(-1, 3)
    alpha = arr[:, :, 3].reshape(-1)

    out_ids: list[str | None] = [None] * rgb.shape[0]
    opaque = np.nonzero(alpha > 0)[0]
    for start in range(0, len(opaque), chunk):
        sel = opaque[start : start + chunk]
        q = rgb[sel]
        d = ((q[:, None, :] - _PALETTE_RGB[None, :, :]) ** 2).sum(axis=2)
        best = d.argmin(axis=1)
        for j, idx in zip(sel, best):
            out_ids[int(j)] = _PALETTE_IDS[int(idx)]

    if background is not None:
        bg = _normalize(background)
        for i, v in enumerate(out_ids):
            if v is None:
                out_ids[i] = bg

    h, w = arr.shape[:2]
    return [out_ids[r * w : (r + 1) * w] for r in range(h)]


def _normalize(block_id: str) -> str:
    block_id = block_id.strip()
    if block_id.startswith("minecraft:"):
        return block_id
    return f"minecraft:{block_id}"