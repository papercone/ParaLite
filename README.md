# ParaLite

Print text onto a plane as a **Minecraft `.litematic` projection**, rendered
with the **Mojangles** (Minecraft) font via the
[litemapy](https://github.com/SmylerMC/litemapy) library.

Newlines and spaces are preserved exactly; every glyph is laid out at its
true font advance width (HTML/print style) with baseline alignment, so the
result looks like real text rather than a monospace grid.

## Features

- True proportional glyph layout from the TTF outline data (not a pixel font)
- Three material modes: **same** (one material), **paragraph** (blank-line
  separated), **line** (per line) — see [Modes](#modes)
- Interactive material picking per paragraph/line, or batch `--choices`
- Custom block ids accepted anywhere (`minecraft:gold_block`, ...)
- Horizontal (ground) or vertical (wall) plane, stacking `--layers`,
  configurable line height, optional background board
- Always writes two files: the `.litematic` projection + a PNG preview
  (the preview *is* the intermediate rendering step)

## Versions

| Version | Notes |
| --- | --- |
| v0.1.0 | Font supports Mojangles only (others untested) |

## Installation

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```sh
git clone <repo-url>
cd ParaLite
uv sync          # creates .venv and installs litemapy, fonttools, numpy, pillow
```

## Usage

```sh
uv run main.py                          # renders content.txt with default options
uv run main.py --content my_text.txt    # another input file
uv run main.py --mode paragraph --choices 0101 ...   # batch material choices
```

`main.py` reads `content.txt` (or `--content FILE`) and writes:

- `<output>.litematic` — the projection
- `<output>.png` — preview image of the rendered text

### content.txt

Just paste the text you want to project. All newlines and spaces are kept.

Glyphs missing from the Mojangles font are replaced with readable ASCII
(`§`→`?`, `…`→`...`, smart quotes → straight quotes, `—`→`-`, `■`→`?`) or
left blank.

### Modes

| Mode | Unit | Default material per unit |
| --- | --- | --- |
| `same` (default) | the whole file | `--material` (always, no prompts) |
| `paragraph` | blank-line separated paragraphs | prompt / `--choices` |
| `line` | every line | prompt / `--choices` |

In `paragraph` / `line` mode with no `--choices`, each unit is prompted
interactively. The answer can be:

- `0` → `--material`
- `1` → `--alt-material`
- any block id, e.g. `minecraft:gold_block` (kept exactly in the projection)

Batch mode: `--choices` takes a 0/1 string with one character per unit
(units beyond the string default to `0`):

```sh
uv run main.py --mode paragraph --choices 01010101
```

> Note: line-level `[block]` prefixes are **not** parsed (so text like
> `[playername]` is not misinterpreted); the whole unit uses the picked material.

### utils package

The `utils/` package exposes reusable building blocks:

| Function | Purpose |
| --- | --- |
| `text2image(rows, renderer, spacing, line_height)` | text rows → RGBA image |
| `convert_image_to_blocks(image, background)` / `image2blocks` | image → block grid |
| `materialselect(count, m0, m1, previews)` | interactive per-unit material picking |
| `BLOCK_COLORS`, `color_of`, `nearest_block` | curated block palette (wool, concrete, terracotta, naturals, and a few extras) |
| `_normalize(id)` | coerce a block id to `minecraft:...` form |

## Options

| Option | Default | Description |
| --- | --- | --- |
| `--content` | `content.txt` | input text file |
| `--font` | `font/minecraft_font.ttf` | Mojangles TTF (other fonts untested) |
| `--mode` | `same` | `same` \| `paragraph` \| `line` (see [Modes](#modes)) |
| `--output` / `-o` | auto | output `.litematic` filename |
| `--material` | `minecraft:white_concrete` | material for choice `0` (and `same` mode) |
| `--alt-material` | `minecraft:black_concrete` | material for choice `1` |
| `--choices` | none | batch material choices: 0/1 string, one char per unit |
| `--background` | none (air) | block for empty pixels, e.g. a white board |
| `--plane` | `horizontal` | `horizontal` = on the ground; `vertical` = on a wall |
| `--spacing` | `proportional` | `proportional` = true glyph width; `mono` = fixed cell |
| `--layers` | 1 | blocks stacked per pixel on the Y axis (horizontal plane) |
| `--line-height` | 9 | row height in blocks (glyphs are 8 px tall; e.g. `14` for airier rows) |
| `--y` | 0 | base Y level (horizontal plane) |
| `--image` | auto | preview PNG path (default: same stem as the output file) |
| `--name` / `--author` / `--description` | — | projection metadata |

### Output filenames

- With `--output/-o`: use the given name.
- Without: auto-generated from the content, e.g.
  `i-see-the-player-you-mean-a1b2c3d4.litematic` — different content always
  yields a different file (content hash), so nothing is ever overwritten.

## Examples

```sh
# Whole text in white concrete, 2 blocks thick, on the ground
uv run main.py --mode same --material minecraft:white_concrete --layers 2

# Alternating paragraphs: white / black concrete, batch mode
uv run main.py --mode paragraph --choices 0101 \
    --material minecraft:white_concrete --alt-material minecraft:black_concrete

# Text on a wall, gold letters on a black background board
uv run main.py --mode same --plane vertical \
    --material minecraft:gold_block --background minecraft:black_concrete

# Interactive: pick a material per paragraph (0, 1, or any block id)
uv run main.py --mode paragraph
```

## Limitations

- Only the Mojangles font ships with the repo and is tested.
- The preview color of a block id outside the curated palette is shown as
  white, but the `.litematic` always keeps the exact block id you chose.
- Unknown glyphs are substituted or left blank (see [content.txt](#contenttxt)).
