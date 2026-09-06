from __future__ import annotations

import argparse
import hashlib
import math
import re
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont
from litemapy import BlockState, Region, Schematic
from PIL import Image, ImageChops, ImageDraw


DEFAULT_FONT = Path(__file__).resolve().parent / "font" / "minecraft_font.ttf"
DEFAULT_MATERIAL = "minecraft:white_concrete"
DEFAULT_ALT_MATERIAL = "minecraft:black_concrete"
BASELINE_PX = 7  # 8px-tall glyphs: baseline at row 7; descenders occupy row 7
BLOCK_ID_RE = re.compile(r"^[a-z0-9_.:-]+$")

# Glyphs missing from the TTF -> readable substitutions
FALLBACK_CHARS = {
    "§": "?",
    "…": "...",
    "—": "-",
}

# Unknown block ids render as white; the .litematic keeps the real id.
# (RGBA no A) Does glass matter?
# colors: maybe put into utils later
WOOL = {
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
CONCRETE = {
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
TERRACOTTA = {
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
NATURALS = {
    "stone": (125, 125, 125),
    "cobblestone": (110, 110, 110),
    "dirt": (134, 96, 67),
    "sand": (219, 205, 162),
    "gravel": (123, 125, 123),
    "oak_planks": (162, 130, 78),
    "bricks": (146, 82, 72),
}
EXTRAS = {
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
for name, rgb in WOOL.items():
    BLOCK_COLORS[f"minecraft:{name}_wool"] = rgb
for name, rgb in CONCRETE.items():
    BLOCK_COLORS[f"minecraft:{name}_concrete"] = rgb
for name, rgb in TERRACOTTA.items():
    BLOCK_COLORS[f"minecraft:{name}_terracotta"] = rgb
for name, rgb in NATURALS.items():
    BLOCK_COLORS[f"minecraft:{name}"] = rgb
for name, rgb in EXTRAS.items():
    BLOCK_COLORS[f"minecraft:{name}"] = rgb


def normalize(block_id: str) -> str:
    block_id = block_id.strip()
    if ":" in block_id:
        return block_id
    return f"minecraft:{block_id}"


def apply_fallbacks(text: str) -> str:
    for src, dst in FALLBACK_CHARS.items():
        text = text.replace(src, dst)
    return text

def preview_rgb(material: str | None) -> tuple[int, int, int]:
    if not material:
        return (255, 255, 255)
    return BLOCK_COLORS.get(material) or (255, 255, 255)


def quad_samples(
    start: tuple[float, float],
    points: tuple,
    steps: int = 8,
) -> list[tuple[float, float]]:
    """Flatten a TrueType qCurveTo into sampled on-curve points."""
    offs = list(points[:-1])
    end = points[-1]
    if end is None:
        end = start
    if not offs:
        return [end]
    samples: list[tuple[float, float]] = []
    cur = start
    for i, ctrl in enumerate(offs):
        nxt = end if i == len(offs) - 1 else (
            (ctrl[0] + offs[i + 1][0]) / 2.0,
            (ctrl[1] + offs[i + 1][1]) / 2.0,
        )
        for t in range(1, steps + 1):
            u = t / steps
            x = (1 - u) ** 2 * cur[0] + 2 * (1 - u) * u * ctrl[0] + u ** 2 * nxt[0]
            y = (1 - u) ** 2 * cur[1] + 2 * (1 - u) * u * ctrl[1] + u ** 2 * nxt[1]
            samples.append((x, y))
        cur = nxt
    return samples


class MojanglesRenderer:
    """
    based on fonttools
    Rasterize TTF glyphs to crisp bitmaps from the outline data.
    """

    def __init__(self, font_path: str | Path, supersample: int = 4):
        self.font = TTFont(str(font_path))
        self.gs = self.font.getGlyphSet()
        self.cmap = self.font.getBestCmap() or {}
        self.supersample = supersample
        self.cache: dict[tuple, object] = {}

    def glyph_name(self, ch: str) -> str | None:
        if len(ch) != 1:
            return None
        return self.cmap.get(ord(ch))

    def advance_px(self, ch: str) -> int:
        """Character advance width in pixels (128 font units = 1 px)."""
        name = self.glyph_name(ch)
        if name is None:
            return 2
        adv = self.font["hmtx"][name][0]
        return max(1, round(adv / 128.0))

    def glyph_row(self, ch: str) -> tuple[int, int, int, list[list[int]]]:
        """Return (width, height, top_px, bits) for a single glyph.

        ``top_px`` is the row within an 8px-tall cell at which the bitmap
        should be pasted so the baseline stays aligned.
        """
        key = ("row", ch, self.supersample)
        cached = self.cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]

        name = self.glyph_name(ch)
        if name is None:
            res = (0, 0, 0, [])
            self.cache[key] = res
            return res

        bpen = BoundsPen(self.gs)
        self.gs[name].draw(bpen)
        if bpen.bounds is None:
            res = (0, 0, 0, [])
            self.cache[key] = res
            return res

        x0, y0, x1, y1 = bpen.bounds
        scale = self.supersample
        wpx = max(1, math.ceil((x1 - x0) / 128.0))
        hpx = max(1, math.ceil((y1 - y0) / 128.0))
        img = Image.new("1", (wpx * scale, hpx * scale), 0)

        def to_canvas(x: float, y: float) -> tuple[float, float]:
            return ((x - x0) / 128.0 * scale, (y1 - y) / 128.0 * scale)

        pen = RecordingPen()
        self.gs[name].draw(pen)
        cur: list[tuple[float, float]] = []
        start: tuple[float, float] | None = None
        contours: list[list[tuple[float, float]]] = []

        def flush(close: bool) -> None:
            nonlocal cur, start
            if close and start is not None and (not cur or cur[-1] != start):
                cur.append(start)
            if len(cur) >= 3:
                contours.append(cur)
            cur = []
            start = None

        for op, args in pen.value:
            if op == "moveTo":
                flush(close=False)
                pt = to_canvas(*args[0])
                cur = [pt]
                start = pt
            elif op == "lineTo":
                cur.append(to_canvas(*args[0]))
            elif op == "qCurveTo":
                if not cur:
                    continue
                last = cur[-1]
                raw_last = (
                    last[0] / scale * 128.0 + x0,
                    y1 - last[1] / scale * 128.0,
                )
                for pt in quad_samples(raw_last, args):
                    cur.append(to_canvas(*pt))
            elif op == "closePath":
                flush(close=True)
            elif op == "endPath":
                flush(close=False)

        flush(close=False)

        mask = Image.new("1", img.size, 0)
        for contour in contours:
            tmp = Image.new("1", img.size, 0)
            ImageDraw.Draw(tmp).polygon(contour, fill=1)
            mask = ImageChops.logical_xor(mask, tmp)

        px = mask.load()
        bits: list[list[int]] = []
        thresh = (scale * scale) // 2
        for r in range(hpx):
            row: list[int] = []
            for c in range(wpx):
                tot = 0
                for yy in range(r * scale, (r + 1) * scale):
                    for xx in range(c * scale, (c + 1) * scale):
                        if px[xx, yy]:
                            tot += 1
                row.append(1 if tot >= thresh else 0)
            bits.append(row)

        top_px = BASELINE_PX - math.ceil(y1 / 128.0)
        res = (wpx, hpx, top_px, bits)
        self.cache[key] = res
        return res

def pick_materials(previews, material=DEFAULT_MATERIAL, choices=None):
    """
    Build a material palette and manually assign one material
    to each paragraph/line.

    ``choices`` defines the palette:
        0 -> choices[0]
        1 -> choices[1]
        ...

    The user is then prompted to enter a material index
    for each text unit.
    """
    if choices:
        palette = [normalize(c) for c in choices]
    else:
        palette = [normalize(material)]
    if not palette:
        raise ValueError("no material choices available")
    print("\nMaterial palette:")
    for i, mat in enumerate(palette):
        print(f"  [{i}] {mat}")

    picked = []
    for i, preview in enumerate(previews):
        while True:
            try:
                choice = input(
                    f"\n[{i}] {preview!r}\n"
                    f"Choose material [0-{len(palette) - 1}]: "
                ).strip()

                index = int(choice)
                if 0 <= index < len(palette):
                    picked.append(palette[index])
                    break
                print(
                    f"Please enter a number between "
                    f"0 and {len(palette) - 1}."
                )
            except ValueError:
                print("Please enter a valid material index.")
    return picked

def parse_paragraph(text, material, mode, choices=None):
    """
    Based on function pick_materials().
    Split text into rows of ``(material, text)`` for rendering.

    ``same``: the whole file uses ``material_0``.
    ``paragraph``: blank-line separated paragraphs, each with its own material.
    ``line``: every line is a unit.

    Newlines and spaces are preserved. A trailing newline's empty piece is
    dropped; interior blank lines are kept as blank rows. Line-level
    ``[block]`` prefixes are not parsed (so ``[playername]`` stays as text).
    """
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    lines = [apply_fallbacks(ln) for ln in lines]
    if not lines:
        return []

    if mode == "same":
        mat = normalize(material)
        return [(mat, ln) for ln in lines]

    if mode == "line":
        previews = lines
        picked = pick_materials(previews, material, choices)
        return [(picked[i],line) for i, line in enumerate(lines)]

    # split basis: paragraph: group non-blank lines, keep interior blank lines as blank rows
    paras = []
    cur = []
    for i, raw in enumerate(lines):
        if raw.strip() == "":
            if cur:
                paras.append(cur)
                cur = []
        else:
            cur.append(i)
    if cur:
        paras.append(cur)

    previews = [lines[p[0]] for p in paras]
    picked = pick_materials(previews, material, choices)
    line_mat: dict[int, str] = {}
    for para, mat in zip(paras, picked):
        for i in para:
            line_mat[i] = mat
    return [(line_mat.get(i), ln) for i, ln in enumerate(lines)]

def blit_glyph(img, grid, x, y, bits, material, rgb): 
    if material is None or not bits:
        return
    px = img.load()
    h = len(bits)
    w = len(bits[0]) if h else 0
    iw, ih = img.size
    for r in range(h):
        gy = y + r
        if gy < 0 or gy >= ih:
            continue
        for c in range(w):
            if not bits[r][c]:
                continue
            gx = x + c
            if gx < 0 or gx >= iw:
                continue
            px[gx, gy] = (rgb[0], rgb[1], rgb[2], 255)
            grid[gy][gx] = material

def text2img(rows, renderer, line_height=9):
    """
    Render text to an RGBA preview and a parallel block-id grid.
    ``line_height`` is the height of a text row in pixels/blocks (glyphs are 8px tall). Blank rows use the same height so newlines stay visible.
    """
    if line_height < 7:
        line_height = 7   # mojang 7
    m = len(rows)
    line_widths = [sum(renderer.advance_px(ch) for ch in text) for _, text in rows]
    width = max(line_widths, default=1)
    width = max(width, 1)
    height = max(m * line_height, 1)
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    grid: list[list[str | None]] = [[None] * width for _ in range(height)]
    tile_bits: dict[str, tuple[int, int, int, list[list[int]]]] = {}

    for i, (mat, text) in enumerate(rows):
        rgb = preview_rgb(mat)
        x = 0
        for ch in text:
            cached = tile_bits.get(ch)
            if cached is None:
                cached = renderer.glyph_row(ch)
                tile_bits[ch] = cached
            wpx, hpx, top_px, bits = cached
            blit_glyph(img, grid, x, i * line_height + top_px, bits, mat, rgb)
            x += renderer.advance_px(ch)

    return img, grid

def background(grid, background):
    """Fill empty pixels with ``background`` (air if omitted)."""
    if background is None:
        return grid
    bg = normalize(background)
    return [[bg if cell is None else cell for cell in row] for row in grid]

def img2litema(grid, plane, y, layers):
    """
    Turn the image into a litemapy Region (bulk palette path).
    Based on litemapy
    grid[row][col] = block id or None (air). One block per image pixel.
    Horizontal: X right, Z back; each pixel is repeated vertically ``layers``
    times (a stack of layers blocks). Region origin at (0, y, 0).
    Vertical:   X right, Y up, Z = 0 (text on a wall facing +Z). First text
    line is placed at the top of the region.
    """
    if layers < 1:
        layers = 1
    m = len(grid)
    n = len(grid[0]) if m else 0
    if n == 0 or m == 0:
        raise ValueError("empty grid")
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
            pi = idx[b]
            if plane == "horizontal":
                for ly in range(layers):
                    arr[x, ly, z] = pi
            else:
                arr[x, m - 1 - z, 0] = pi
    region._Region__palette = palette
    region._Region__blocks = arr
    return region


def output(content: str, rows: list[tuple[str | None, str]]) -> str:
    """Auto filename from the first line + date + content hash (YYMMDD)."""
    first = next((t for _, t in rows if t.strip()), "text")
    slug = re.sub(r"[^a-z0-9]+", "-", first.lower()).strip("-")[:40] or "text"
    day = datetime.now().strftime("%y%m%d")
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()[:8]
    return f"{slug}-{day}-{digest}.litematic"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print content.txt with the Mojangles font onto a plane as a .litematic.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--content", default="content.txt", help="input text file")
    parser.add_argument("--font", default=str(DEFAULT_FONT), help="Mojangles TTF font")
    parser.add_argument(
        "--mode",
        choices=["same", "paragraph", "line"],
        default="same",
        help="same=whole file one material; paragraph=blank-line units; line=per line",
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="output .litematic filename (default: auto-name derived from content)",
    )
    parser.add_argument(
        "--material", default=DEFAULT_MATERIAL,
        help="material for choice 0 / same mode",
    )
    parser.add_argument(
        "--background", default=None,
        help="optional block for empty pixels (default: air)",
    )
    parser.add_argument(
        "--plane", choices=["horizontal", "vertical"], default="horizontal",
        help="horizontal = text on the ground; vertical = text on a wall",
    )
    parser.add_argument(
        "--layers", type=int, default=1,
        help="stack height in blocks for each pixel (horizontal plane)",
    )
    parser.add_argument("--choices", nargs="+", default=None, help="materials for each line/paragraph; one value is reused for all")
    parser.add_argument("--alt-material", default=DEFAULT_ALT_MATERIAL, help="reserved alternate material")
    parser.add_argument("--line-height", type=int, default=9, help="height of each rendered text row")
    parser.add_argument("--y", type=int, default=0, help="Y coordinate of the schematic region")
    parser.add_argument("--image", default=None, help="preview PNG filename")
    parser.add_argument("--name", default=None, help="schematic name")
    parser.add_argument("--author", default="ParaLite", help="schematic author")
    parser.add_argument("--description", default=None, help="schematic description")
    args = parser.parse_args(argv)

    content_path = Path(args.content)
    if not content_path.exists():
        print(f"error: {content_path} not found", file=sys.stderr)
        return 1
    font_path = Path(args.font)
    if not font_path.exists():
        print(f"error: font {font_path} not found", file=sys.stderr)
        return 1

    content = content_path.read_text(encoding="utf-8")
    rows = parse_paragraph(
        content,
        args.material,
        args.mode,
        choices=args.choices if args.mode != "same" else None,
    )
    if not rows or all(not t for _, t in rows):
        print("error: content is empty", file=sys.stderr)
        return 1

    renderer = MojanglesRenderer(font_path)
    img, grid = text2img(rows, renderer, line_height=args.line_height)
    print(
        f"lines: {len(rows)}, image {img.width}x{img.height} px "
        f"(mode={args.mode}, line_height={args.line_height})"
    )

    grid = background(grid, background=args.background)
    placed = sum(1 for row in grid for b in row if b is not None)
    print(f"map-art grid: {len(grid[0])}x{len(grid)}, non-air blocks: {placed}")

    region = img2litema(grid, args.plane, y=args.y, layers=args.layers)
    out = args.output or output(content, rows)
    if not out.endswith(".litematic"):
        out += ".litematic"
    out_path = Path(out)
    image_path = Path(args.image) if args.image else out_path.with_suffix(".png")
    img.save(image_path)
    print(f"preview image saved: {image_path}")

    stem = args.name or out_path.stem
    schem = Schematic(
        name=stem,
        author=args.author,
        description=args.description or f"rendered by ParaLite ({len(rows)} lines)",
        regions={"main": region},
    )
    schem.save(str(out_path))
    print(
        f"saved: {out_path}  "
        f"(schematic region size: {region.width}x{region.height}x{region.length})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())