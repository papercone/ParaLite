# ParaLite

**ParaLite** is a text-to-Minecraft map-art generator. It uses the **Mojangles (Minecraft)** font and [`litemapy`](https://github.com/SmylerMC/litemapy) to rasterize text into a block grid and export it as a `.litematic` schematic.

The renderer uses the actual glyph advance widths from the font and keeps glyph baselines aligned. A PNG preview is also generated so the result can be checked before importing the schematic into Minecraft.

## Status

**v0.1.0**

- Mojangles / Mojang Seven is currently the only tested font.
- Text is rendered as a pixel-style block map.
- Supports horizontal (ground) and vertical (wall) layouts.
- Supports one material for the whole document, per-paragraph materials, or per-line materials.
- Supports an optional background block.
- Exports both `.litematic` and `.png` files.

## Requirements

- Python **3.12 or newer**
- [`uv`](https://docs.astral.sh/uv/)

## Installation

```bash
git clone https://github.com/papercone/ParaLite.git
cd ParaLite
uv sync
```

`uv sync` creates the project environment and installs the required dependencies, including:

- `litemapy`
- `fonttools`
- `numpy`
- `pillow`

## Quick Start

Put the text you want to render into `content.txt`, then run:

```bash
uv run main.py
```

By default, ParaLite:

1. Reads `content.txt`.
2. Uses `font/minecraft_font.ttf`.
3. Renders the entire document with `minecraft:white_concrete`.
4. Places the result on a horizontal plane.
5. Generates an automatically named `.litematic`.
6. Generates a PNG preview next to the `.litematic`.

A typical run therefore produces:

```text
<generated-name>.litematic
<generated-name>.png
```

## Input: `content.txt`

Paste the text you want to render into `content.txt`.

Spaces and line breaks are preserved. A trailing newline is ignored.

Characters that are not available in the bundled font may be replaced with readable ASCII fallbacks. For example:

| Character | Fallback |
| --- | --- |
| `§` | `?` |
| `…` | `...` |
| `—` | `-` |

Other unsupported glyphs may be left blank.

> The current fallback table is intentionally small and depends on what the bundled font can represent.

## Material Modes

Use `--mode` to decide how materials are assigned.

| Mode | Unit | Material assignment |
| --- | --- | --- |
| `same` | Entire document | One material from `--material` |
| `paragraph` | Paragraphs separated by blank lines | One material per paragraph |
| `line` | Every line | One material per line |

### `same`

This is the default:

```bash
uv run main.py \
  --mode same \
  --material minecraft:white_concrete
```

The entire text uses the same block.

### `paragraph`

Blank lines divide the input into paragraphs:

```text
First paragraph
continues here

Second paragraph
continues here

Third paragraph
```

In `paragraph` mode, `--choices` defines a **material palette**. Each material is assigned an index starting from `0`.

For example:

```bash
uv run main.py \
  --mode paragraph \
  --choices minecraft:red_concrete minecraft:blue_concrete minecraft:gold_block
```

creates the following palette:

```text
[0] minecraft:red_concrete
[1] minecraft:blue_concrete
[2] minecraft:gold_block
```

ParaLite then asks you to manually select a material for each paragraph:

```text
Material palette:
  [0] minecraft:red_concrete
  [1] minecraft:blue_concrete
  [2] minecraft:gold_block

[0] 'First paragraph'
Choose material [0-2]: 0

[1] 'Second paragraph'
Choose material [0-2]: 2

[2] 'Third paragraph'
Choose material [0-2]: 1
```

The selected materials are therefore:

```text
Paragraph 0 → red_concrete
Paragraph 1 → gold_block
Paragraph 2 → blue_concrete
```

The number of materials in `--choices` does **not** need to match the number of paragraphs. It only defines the available palette.

### `line`

Every line is treated as a separate material unit.

```bash
uv run main.py \
  --mode line \
  --choices minecraft:red_concrete minecraft:blue_concrete minecraft:green_concrete
```

The same palette is created:

```text
[0] minecraft:red_concrete
[1] minecraft:blue_concrete
[2] minecraft:green_concrete
```

ParaLite then asks for a material index for every line:

```text
[0] 'Hello'
Choose material [0-2]: 0

[1] 'World'
Choose material [0-2]: 1

[2] 'ParaLite'
Choose material [0-2]: 2
```

This allows arbitrary material layouts instead of automatically cycling through the palette.

### Material Selection Summary

The three modes have different material-selection behavior:

| Mode | Unit | Material selection |
| --- | --- | --- |
| `same` | Entire document | Uses `--material`; no prompt |
| `paragraph` | Paragraph separated by blank lines | Manually choose a palette index for each paragraph |
| `line` | Every line | Manually choose a palette index for each line |

`--choices` is therefore a **palette definition**, not an automatic assignment list.

### Block IDs

Materials are specified using Minecraft block IDs, for example:

```text
minecraft:white_concrete
minecraft:black_concrete
minecraft:gold_block
minecraft:diamond_block
```

If a valid block ID is supplied but is not included in ParaLite's preview color table, the PNG preview falls back to white. The actual block ID is still preserved in the `.litematic`.

## Command-Line Options

| Option | Default | Description |
| --- | --- | --- |
| `--content` | `content.txt` | Input text file |
| `--font` | `font/minecraft_font.ttf` | Mojangles TTF font |
| `--mode` | `same` | `same`, `paragraph`, or `line` |
| `--output`, `-o` | automatic | Output `.litematic` filename |
| `--material` | `minecraft:white_concrete` | Default material / material used by `same` mode |
| `--choices` | none | Material palette for `paragraph` / `line` mode; materials are indexed from `0` to `n-1` |
| `--background` | none | Block used to fill empty pixels; omitted means air |
| `--plane` | `horizontal` | `horizontal` for ground; `vertical` for a wall |
| `--layers` | `1` | Vertical stack height for each pixel on a horizontal plane |
| `--line-height` | `9` | Height of each rendered text row |
| `--y` | `0` | Y coordinate of the schematic region |
| `--image` | automatic | PNG preview path |
| `--name` | output filename stem | Schematic name |
| `--author` | `ParaLite` | Schematic author |
| `--description` | automatic | Schematic description |

Run:

```bash
uv run main.py --help
```

for the complete command-line help.

## Examples

### 1. White concrete text on the ground

```bash
uv run main.py \
  --mode same \
  --material minecraft:white_concrete
```

### 2. Two-block-high ground map art

```bash
uv run main.py \
  --mode same \
  --material minecraft:white_concrete \
  --layers 2
```

### 3. Gold text on a black wall

```bash
uv run main.py \
  --mode same \
  --plane vertical \
  --material minecraft:gold_block \
  --background minecraft:black_concrete
```

### 4. Different materials for different paragraphs

Define the palette with `--choices`, then select the material index interactively for each paragraph:

```bash
uv run main.py \
  --mode paragraph \
  --choices minecraft:red_concrete minecraft:blue_concrete minecraft:gold_block
```

For example, selecting `0`, `2`, and `1` assigns:

```text
Paragraph 0 → red_concrete
Paragraph 1 → gold_block
Paragraph 2 → blue_concrete
```

### 5. Different materials for different lines

```bash
uv run main.py \
  --mode line \
  --choices minecraft:white_concrete minecraft:red_concrete minecraft:blue_concrete
```

Each line is prompted individually, so the material pattern can be chosen manually.

### 6. Custom input and output paths

```bash
uv run main.py \
  --content my_text.txt \
  --output my_map_art.litematic \
  --image my_map_art.png
```

## Coordinate and Layout Behavior

### Horizontal

For `--plane horizontal`:

- X increases from left to right.
- Z increases with successive text rows.
- Each rendered pixel becomes a vertical stack of blocks.
- `--layers` controls the stack height.
- `--y` controls the base Y coordinate.

### Vertical

For `--plane vertical`:

- X increases from left to right.
- Y increases upward.
- Z is fixed to a single layer.
- The first text line is placed at the top of the region.

This makes the vertical mode suitable for wall-mounted text.

## Output Filename

If `--output` is not specified, ParaLite generates a filename from:

- the first non-empty line of the content,
- the current date,
- a short SHA-1 hash of the input content.

For example:

```text
hello-world-260906-a1b2c3d4.litematic
hello-world-260906-a1b2c3d4.png
```

The hash helps avoid accidentally overwriting outputs generated from different input content.

## Preview Colors

ParaLite contains a small built-in RGB preview palette for commonly used:

- wool
- concrete
- terracotta
- natural blocks
- selected resource blocks

The preview color is only an approximation of the final Minecraft appearance. Lighting, texture, shaders, resource packs, and the actual block appearance in Minecraft can all affect the final result.

For blocks outside the preview palette, the PNG uses white as a fallback while the selected block ID remains unchanged in the schematic.

## Limitations

- Only the bundled **Mojangles / Mojang Seven** font is currently tested.
- Font support depends on the glyphs available in the selected TTF.
- Unsupported glyphs may be replaced or left blank.
- The preview RGB values are approximations, not Minecraft's exact rendered colors.
- Blocks outside the built-in preview palette appear white in the PNG preview.
- `paragraph` mode uses **blank lines** to separate paragraphs.
- `line` mode treats every line as an independent material unit.
- The current renderer is designed around an 8-pixel-high Minecraft-style glyph layout. Compatibility not tested.

## Project Structure

```text
ParaLite/
├── main.py
├── content.txt
├── font/
│   └── minecraft_font.ttf
├── pyproject.toml
└── README.md
```

## Roadmap

- [ ] Support more fonts
  - [ ] General TTF fonts with configurable glyph size
  - [ ] More pixel fonts
- [ ] Expand the block preview palette
- [ ] Improve handling of unsupported glyphs
- [ ] Add more flexible material assignment
- [ ] Improve preview accuracy

## License

See the repository for the project's license information.