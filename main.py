# from utils import *
# import litemapy

# def main():
#     print("Welcome to ParaLite! A tool to convert English text into Minecraft schematica.")


from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import numpy as np
import math
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw
from litemapy import BlockState, Region, Schematic

from utils import *

DEFAULT_FONT = Path(__file__).resolve().parent / "font" / "minecraft_font.ttf"
DEFAULT_MATERIAL = "minecraft:white_concrete"

# Glyphs missing from the TTF -> readable substitutions
FALLBACK_CHARS = {
    "§": "?",
    "…": "...",
}

LINE_RE = re.compile(r"^\[([^\]]+)\]\s*(.*)$")


class MojanglesRenderer:
    """Rasterize TTF glyphs to crisp bitmaps from the outline data."""

    def __init__(self, font_path: str | Path):
        self.font = TTFont(str(font_path))
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap()
        self._cache: dict[tuple, object] = {}

    def _rasterize(self, ch: str, S: int) -> tuple[int, int, list[list[int]]]:
        """Rasterize a glyph to (wpx, hpx, bits) covering its full ink bbox."""
        key = ("raster", ch, S)
        if key in self._cache:
            return self._cache[key]  # type: ignore[return-value]
        name = self.cmap.get(ord(ch))
        if name is None:
            res = (1, 1, [[0]])
            self._cache[key] = res
            return res
        bpen = BoundsPen(self.gs)
        self.gs[name].draw(bpen)
        if bpen.bounds is None:
            res = (1, 1, [[0]])
            self._cache[key] = res
            return res
        x0, y0, x1, y1 = bpen.bounds
        wpx = max(1, math.ceil((x1 - x0) / 128.0))
        hpx = max(1, math.ceil((y1 - y0) / 128.0))
        img = Image.new("L", (wpx * S, hpx * S), 0)
        d = ImageDraw.Draw(img)
        pen = RecordingPen()
        self.gs[name].draw(pen)

        def to_canvas(x: float, y: float) -> tuple[float, float]:
            return ((x - x0) / 128.0 * S, (y1 - y) / 128.0 * S)

        cur: list[tuple[float, float]] = []
        for op, args in pen.value:
            if op == "moveTo":
                cur = [to_canvas(*args[0])]
            elif op == "lineTo":
                cur.append(to_canvas(*args[0]))
            elif op in ("closePath", "endPath"):
                if len(cur) >= 3:
                    d.polygon(cur, fill=255)
                cur = []
        px = img.load()
        gbits: list[list[int]] = []
        for r in range(hpx):
            row: list[int] = []
            for c in range(wpx):
                tot = 0
                for yy in range(r * S, (r + 1) * S):
                    for xx in range(c * S, (c + 1) * S):
                        if px[xx, yy] > 127:
                            tot += 1
                row.append(1 if tot >= (S * S) // 2 else 0)
            gbits.append(row)
        res = (wpx, hpx, gbits)
        self._cache[key] = res
        return res

    def advance_px(self, ch: str) -> int:
        """Character advance width in pixels (128 font units = 1 px)."""
        name = self.cmap.get(ord(ch))
        if name is None:
            return 2
        adv = self.font["hmtx"][name][0]
        return max(1, round(adv / 128.0))

def parse_paragraphs(
    text: str,
    material_0: str,
    material_1: str,
    choices: str | None = None,
) -> list[tuple[str | None, str]]:
    """Split text into paragraphs (blank-line separated), pick a material per
    paragraph, and return [(material, text), ...] rows for rendering.

    Each paragraph gets 0 (material_0, e.g. sand) or 1 (material_1, e.g.
    gravel). In interactive mode the user is prompted per paragraph; in batch
    mode *choices* is a string of 0/1 (one char per paragraph, excess
    paragraphs default to 0). A trailing newline's empty piece is dropped;
    interior blank lines are kept as blank rows.
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    # group non-blank lines into paragraphs
    paras: list[list[str]] = []
    cur: list[str] = []
    for raw in lines:
        if raw.strip() == "":
            if cur:
                paras.append(cur)
                cur = []
        else:
            cur.append(raw)
    if cur:
        paras.append(cur)

    if choices is None:
        choices = ""
        for i, para in enumerate(paras):
            preview = para[0][:44]
            while True:
                ans = input(f"[paragraph {i + 1}/{len(paras)}] 0=sand 1=gravel | {preview} > ").strip()
                if ans in ("0", "1"):
                    break
                print("    please enter 0 or 1")
            choices += ans
    choices = choices.ljust(len(paras), "0")[: len(paras)]

    rows: list[tuple[str | None, str]] = []
    for para_idx, para in enumerate(paras):
        mat = _normalize(material_0 if choices[para_idx] == "0" else material_1)
        for raw in para:
            txt = raw
            for k, v in FALLBACK_CHARS.items():
                txt = txt.replace(k, v)
            rows.append((mat, txt))
        rows.append((None, ""))  # paragraph separator
    if rows and rows[-1][1] == "":
        rows.pop()  # drop trailing separator
    return rows

def render_text_image(
    rows: list[tuple[str, str]],
    renderer: MojanglesRenderer,
    spacing: str = "proportional",
    line_height: int = 9,
) -> Image.Image:
    """Render text to an RGBA image.

    spacing="proportional": glyphs placed at their true advance width and
    baseline-aligned (HTML/print standard); rows are line_height px tall.
    spacing="mono": every glyph centered in a fixed cell x cell square.
    """
    m = len(rows)
    if spacing == "mono":
        n = max((len(t) for _, t in rows), default=1)
        n = max(n, 1)
        img = Image.new("RGBA", (n * cell, m * cell), (0, 0, 0, 0))
        tile_cache: dict[tuple, Image.Image] = {}
        for i, (mat, text) in enumerate(rows):
            rgb = BLOCK_COLORS.get(mat) or (255, 255, 255)
            for ci, ch in enumerate(text):
                key = (ch, rgb)
                tile = tile_cache.get(key)
                if tile is None:
                    bits = renderer.bits(ch)
                    tile = Image.new("RGBA", (cell, cell), (0, 0, 0, 0))
                    tp = tile.load()
                    for r in range(cell):
                        for c in range(cell):
                            if bits[r][c]:
                                tp[c, r] = (rgb[0], rgb[1], rgb[2], 255)
                    tile_cache[key] = tile
                img.paste(tile, (ci * cell, i * cell), tile)
        return img

    # proportional layout
    line_widths = [sum(renderer.advance_px(ch) for ch in text) for _, text in rows]
    n = max(line_widths, default=1)
    n = max(n, 1)
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

def grid_to_region(
    grid: list[list[str | None]],
    plane: str,
    y: int = 0,
    layers: int = 1,
) -> Region:
    """
    Turn the map-art block grid into a litemapy Region (bulk palette path).

    grid[row][col] = block id or None (air). One block per image pixel.
    Horizontal: X right, Z back; each pixel is repeated vertically `layers`
    times (a stack of layers blocks). Region origin at (0, y, 0).
    Vertical:   X right, Y up, Z = 0 (text on a wall facing +Z).
    """
    m = len(grid)
    n = len(grid[0]) if m else 0
    if plane == "horizontal":
        width, height, length = n, layers, m
    else:
        width, height, length = n, m, 1
    region = Region(0, y, 0, width, height, length)
    palette = [BlockState("minecraft:air")]
    idx = {"minecraft:air": 0}
    arr = np.zeros((width, height, length), dtype=np.uint32)
    for z in range(m):
        for x in range(n):
            b = grid[z][x]
            if b is None:
                continue
            if b not in idx:
                idx[b] = len(palette)
                palette.append(BlockState(b))
            if plane == "horizontal":
                for ly in range(layers):
                    arr[x, ly, z] = idx[b]
            else:
                arr[x, z, 0] = idx[b]
    region._Region__palette = palette
    region._Region__blocks = arr
    return region

def auto_output_name(content: str, rows: list[tuple[str | None, str]], spacing: str = "proportional") -> str:
    """Derive a .litematic filename from the content (different content -> different file)."""
    first = next((t for _, t in rows if t.strip()), "text")
    slug = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-")[:40] or "text"
    h = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
    tag = "-choose" if spacing == "proportional" else "-choose-mono"
    return f"{slug}{tag}-{h}.litematic"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Print content.txt with the Mojangles font onto a plane as a .litematic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--content", default="content.txt", help="input text file")
    ap.add_argument("--font", default=str(DEFAULT_FONT), help="Mojangles TTF font")
    ap.add_argument(
        "--output", "-o", default=None,
        help="output .litematic filename (default: auto-name derived from content)",
    )
    ap.add_argument(
        "--material", default="minecraft:sand",
        help="material for choice 0 (default: sand)",
    )
    ap.add_argument(
        "--alt-material", default="minecraft:gravel",
        help="material for choice 1 (default: gravel)",
    )
    ap.add_argument(
        "--choices", default=None,
        help="batch material choices: a string of 0/1, one char per paragraph "
             "(default: interactive prompts)",
    )
    ap.add_argument(
        "--background", default=None,
        help="optional block for empty pixels (default: air)",
    )
    ap.add_argument(
        "--plane", choices=["horizontal", "vertical"], default="horizontal",
        help="horizontal = text on the ground; vertical = text on a wall",
    )
    ap.add_argument(
        "--line-height", type=int, default=9,
        help="row height in pixels/blocks for proportional layout (glyphs are 8px tall)",
    )
    ap.add_argument("--layers", type=int, default=1, help="stack height in blocks for each pixel (horizontal plane)")
    ap.add_argument("--image", default=None, help="also save the 8n x 8m preview image here")
    ap.add_argument("--name", default=None, help="schematic name (default: output stem)")
    ap.add_argument("--author", default="para-litema", help="schematic author")
    ap.add_argument("--description", default="", help="schematic description")
    args = ap.parse_args(argv)

    content_path = Path(args.content)
    if not content_path.exists():
        print(f"error: {content_path} not found", file=sys.stderr)
        return 1
    content = content_path.read_text(encoding="utf-8")

    rows = parse_paragraphs(content, args.material, args.alt_material, choices=args.choices)
    if not rows:
        print("error: content is empty", file=sys.stderr)
        return 1

    renderer = MojanglesRenderer(args.font)
    img = render_text_image(rows, renderer, spacing=args.spacing, line_height=args.line_height)
    n, m = img.width, img.height
    print(f"lines: {m // args.line_height}, image {img.width}x{img.height} px (spacing={args.spacing}, line_height={args.line_height})")

    if args.image:
        img.save(args.image)
        print(f"preview image saved: {args.image}")

    grid = convert_image_to_blocks(img, background=args.background)
    placed = sum(1 for row in grid for b in row if b is not None)
    print(f"map-art grid: {len(grid[0])}x{len(grid)}, non-air blocks: {placed}")

    region = grid_to_region(grid, args.plane, y=args.y, layers=args.layers)
    out = args.output or auto_output_name(content, rows, args.spacing)
    if not out.endswith(".litematic"):
        out += ".litematic"
    out_path = Path(out)
    stem = args.name or out_path.stem
    schem = Schematic(
        name=stem,
        author=args.author,
        description=args.description or f"rendered by para-litema ({len(rows)} lines)",
        regions={"main": region},
    )
    schem.save(str(out_path))
    print(f"saved: {out_path}  (region {region.width}x{region.height}x{region.length})")
    return 0

# if __name__ == "__main__":
#     main()
