"""
Text rendering: turn (material, text) rows into an RGBA image.

The renderer is duck-typed: it only needs ``advance_px(ch)`` and
``glyph_row(ch)`` (see ``MojanglesRenderer`` in main.py).
"""

from __future__ import annotations

from PIL import Image

from .map import BLOCK_COLORS


def text2image(
    rows: list[tuple[str | None, str]],
    renderer,
    spacing: str = "proportional",
    line_height: int = 9,
) -> Image.Image:
    """Render ``rows`` ([(material, text), ...]) to an RGBA image.

    One row of the image corresponds to one line of text.

    - ``spacing="proportional"``: glyphs are placed at their true advance
      width and baseline-aligned (HTML/print standard); rows are
      ``line_height`` px tall.
    - ``spacing="mono"``: every glyph is centered in a fixed 8x8 cell.

    Materials not present in the curated color palette render as white in
    the preview (the .litematic itself keeps the exact block id).
    """
    m = len(rows)
    if spacing == "mono":
        cell = 8
        n = max((len(t) for _, t in rows), default=1)
        img = Image.new("RGBA", (n * cell, m * line_height), (0, 0, 0, 0))
        tile_cache: dict[tuple, Image.Image] = {}
        for i, (mat, text) in enumerate(rows):
            rgb = BLOCK_COLORS.get(mat) or (255, 255, 255)
            x = 0
            for ch in text:
                wpx, hpx, top_px, bits = renderer.glyph_row(ch)
                key = (ch, rgb)
                tile = tile_cache.get(key)
                if tile is None:
                    tile = Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))
                    tp = tile.load()
                    for r in range(hpx):
                        for c in range(wpx):
                            if bits[r][c]:
                                tp[c, r] = (rgb[0], rgb[1], rgb[2], 255)
                    tile_cache[key] = tile
                ox = (cell - wpx) // 2
                img.paste(tile, (x + ox, i * line_height + top_px), tile)
                x += cell
        return img

    # proportional layout
    line_widths = [sum(renderer.advance_px(ch) for ch in text) for _, text in rows]
    n = max(line_widths, default=1)
    img = Image.new("RGBA", (n, m * line_height), (0, 0, 0, 0))
    tile_cache: dict[tuple, Image.Image] = {}
    for i, (mat, text) in enumerate(rows):
        rgb = BLOCK_COLORS.get(mat) or (255, 255, 255)
        x = 0
        for ch in text:
            wpx, hpx, top_px, bits = renderer.glyph_row(ch)
            key = (ch, rgb)
            tile = tile_cache.get(key)
            if tile is None:
                tile = Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))
                tp = tile.load()
                for r in range(hpx):
                    for c in range(wpx):
                        if bits[r][c]:
                            tp[c, r] = (rgb[0], rgb[1], rgb[2], 255)
                tile_cache[key] = tile
            img.paste(tile, (x, i * line_height + top_px), tile)
            x += renderer.advance_px(ch)
    return img
