"""
ParaLite utils package.

Public API:

- ``BLOCK_COLORS``, ``color_of``, ``nearest_block`` — curated block palette.
- ``convert_image_to_blocks`` / ``image2blocks`` — RGBA image -> block grid.
- ``text2image`` — (material, text) rows -> RGBA image.
- ``materialselect`` — interactive per-unit material picking.
- ``_normalize`` — coerce a block id to the ``minecraft:...`` form.
"""

from __future__ import annotations

from .map import (
    BLOCK_COLORS,
    _normalize,
    color_of,
    convert_image_to_blocks,
    nearest_block,
)
from .select import materialselect
from .text import text2image

# README name for the image -> blocks step
image2blocks = convert_image_to_blocks

__all__ = [
    "BLOCK_COLORS",
    "_normalize",
    "color_of",
    "nearest_block",
    "convert_image_to_blocks",
    "image2blocks",
    "text2image",
    "materialselect",
]
