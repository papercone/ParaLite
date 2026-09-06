#ParaLite

**ParaLite** 是一个将文本转换为 Minecraft 地图画（map-art）的生成器。它利用 **Mojangles (Minecraft)** 字体和 [`litemapy`](https://github.com/SmylerMC/litemapy) 库，将文本光栅化为方块网格，并导出为 `.litematic` 结构文件（schematic）。

渲染器使用字体实际的字形进距（advance width）并保持字形基线对齐。程序还会生成 PNG 预览图，以便在将结构文件导入 Minecraft 之前检查效果。

## 状态

**v0.1.0**

- 目前仅测试了 Mojangles / Mojang Seven 字体。
- 文本被渲染为像素风格的方块地图。
- 支持水平（地面）和垂直（墙面）布局。
- 支持为整个文档、每个段落或每行文本指定材质。
- 支持设置可选的背景方块。
- 同时导出 `.litematic` 和 `.png` 文件。

## 要求

- Python **3.12 或更高版本**
- [`uv`](https://docs.astral.sh/uv/)

## 安装

```bash
git clone https://github.com/papercone/ParaLite.git
cd ParaLite
uv sync
```

`uv sync` 会创建项目环境并安装必要的依赖项，包括：

- `litemapy`
- `fonttools`
- `numpy`
- `pillow`

## 快速入门

将您想要渲染的文本放入 `content.txt`，然后运行：

```bash
uv run main.py
```

默认情况下，ParaLite 会：

1. 读取 `content.txt`。
2. 使用 `font/minecraft_font.ttf` 字体。
3. 使用 `minecraft:white_concrete`（白色混凝土）渲染整个文档。
4. 将结果放置在水平面上。
5. 生成一个自动命名的 `.litematic` 文件。
6. 在 `.litematic` 文件旁生成 PNG 预览图。因此，一次典型的运行会生成：

```text
<generated-name>.litematic
<generated-name>.png
```

## 输入：`content.txt`

将您想要渲染的文本粘贴到 `content.txt` 中。

程序会保留空格和换行符，但会忽略末尾的换行符。

如果内置字体中不包含某些字符，这些字符可能会被替换为可读的 ASCII 替代字符。例如：

| 字符 | 替代字符 |
| --- | --- |
| `§` | `?` |
| `...` | `...` |
| `—` | `-` |

其他不支持的字形可能会显示为空白。

> 目前的替代字符表特意保持精简，具体取决于内置字体所支持的字符范围。

## 材质模式

使用 `--mode` 参数来决定如何分配材质。

| 模式 | 单位 | 材质分配方式 |
| --- | --- | --- |
| `same` | 整个文档 | 使用 `--material` 指定的单一材质 |
| `paragraph` | 由空行分隔的段落 | 每个段落使用一种材质 |
| `line` | 每一行 | 每一行使用一种材质 |

### `same`

这是默认模式：

```bash
uv run main.py \
--mode same \
--material minecraft:white_concrete
```

整段文本使用同一种方块材质。

### `paragraph`

空行将输入内容划分为多个段落：

```text
First paragraph
continues here

Second paragraph
continues here

Third paragraph
```

在 `paragraph` 模式下，`--choices` 参数用于定义**palette**。每种材质都会被分配一个从 `0` 开始的索引值。例如：

```bash
uv run main.py \
--mode paragraph \
--choices minecraft:red_concrete minecraft:blue_concrete minecraft:gold_block
```

将创建以下调色板：

```text
[0] minecraft:red_concrete
[1] minecraft:blue_concrete
[2] minecraft:gold_block
```

随后，ParaLite 会要求你为每个段落手动选择一种材质：

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

因此，选定的材质如下：

```text
Paragraph 0 → red_concrete
Paragraph 1 → gold_block
Paragraph 2 → blue_concrete
```

`--choices` 中的材质数量无需与段落数量一致。它仅定义了可用的材质选项。

### `line`

每一行都被视为一个独立的材质单元。

```bash
uv run main.py \
--mode line \
--choices minecraft:red_concrete minecraft:blue_concrete minecraft:green_concrete
```

将创建同样的调色板：

```text
[0] minecraft:red_concrete
[1] minecraft:blue_concrete
[2] minecraft:green_concrete
```

随后，ParaLite 会要求为每一行指定材质索引：

```text
[0] 'Hello'
Choose material [0-2]: 0

[1] 'World'
Choose material [0-2]: 1

[2] 'ParaLite'
Choose material [0-2]: 2
```

这允许自定义材质布局，而无需在调色板中自动循环选择。

### 材质选择总结

这三种模式具有不同的材质选择行为：

| 模式 | 单元 | 材质选择 |
| --- | --- | --- |
| `same` | 整个文档 |使用 `--material`；无提示 |
| `paragraph` | 以空行分隔的段落 | 为每个段落手动选择调色板索引 |
| `line` | 每一行 | 为每一行手动选择调色板索引 |

因此，`--choices` 是一个**调色板定义**，而非自动分配列表。

### 方块 ID

材质通过 Minecraft 方块 ID 指定，例如：

```text
minecraft:white_concrete
minecraft:black_concrete
minecraft:gold_block
minecraft:diamond_block
```

如果提供了有效的方块 ID，但该 ID 未包含在 ParaLite 的预览颜色表中，PNG 预览将默认显示为白色。实际的方块 ID 仍会保留在 `.litematic` 文件中。

## 命令行选项

| 选项 | 默认值 | 描述 |
| --- | --- | --- |
| `--content` | `content.txt` | 输入文本文件 |
| `--font` | `font/minecraft_font.ttf` | Mojangles TTF 字体 |
| `--mode` | `same` | `same`（相同）、`paragraph`（段落）或 `line`（行）模式 |
| `--output`, `-o` | 自动生成 | 输出的 `.litematic` 文件名 |
| `--material` | `minecraft:white_concrete` | 默认材质 / `same` 模式使用的材质 |
| `--choices` | 无 | `paragraph` / `line` 模式的材质调色板；材质索引范围为 `0` 到 `n-1` |
| `--background` | 无 | 用于填充空白像素的方块；省略则视为空气 |
| `--plane` | `horizo​​ntal` | `horizo​​ntal`（水平）用于地面；`vertical`（垂直）用于墙面 |
| `--layers` | `1` | 水平面上每个像素的垂直堆叠高度 |
| `--line-height` | `9` | 每行渲染文本的高度 |
| `--y` | `0` | 结构（schematic）区域的 Y 坐标 |
| `--image` | 自动生成 | PNG 预览文件路径 |
| `--name` | 输出文件名（不带扩展名） | 结构名称 |
| `--author` | `ParaLite` | 结构作者 |
| `--description` | 自动生成 | 结构描述 |

运行：

```bash
uv run main.py --help
```

以查看完整的命令行帮助信息。 ## 示例

### 1. 地面上的白色混凝土文字(默认情况)

```bash
uv run main.py \
--mode same \
--material minecraft:white_concrete
```

### 2. 两格高度的地面文字

```bash
uv run main.py \
--mode same \
--material minecraft:white_concrete \
--layers 2
```

### 3. 黑色墙面+金色文字

```bash
uv run main.py \
--mode same \
--plane vertical \
--material minecraft:gold_block \
--background minecraft:black_concrete
```

### 4. 不同段落使用不同材质

使用 `--choices` 定义材质选项，然后为每个段落交互式选择材质索引：

```bash
uv run main.py \
--mode paragraph \
--choices minecraft:red_concrete minecraft:blue_concrete minecraft:gold_block
```

例如，选择 `0`、`2` 和 `1` 将分配如下：

```text
段落 0 → red_concrete
段落 1 → gold_block
段落 2 → blue_concrete
```

### 5. 不同行使用不同材质

```bash
uv run main.py \
--mode line \
--choices minecraft:white_concrete minecraft:red_concrete minecraft:blue_concrete
```

程序会逐行提示，以便手动选择材质模式。

### 6. 自定义输入和输出路径

```bash
uv run main.py \
--content my_text.txt \
--output my_map_art.litematic \
--image my_map_art.png
```

## 坐标与布局行为

### 水平方向 (Horizo​​ntal)

对于 `--plane horizo​​ntal`：

- X 轴从左向右增加。
- Z 轴随文本行数增加。
- 每个渲染的像素对应一列垂直堆叠的方块。
- `--layers` 控制堆叠高度。
- `--y` 控制基础 Y 坐标。

### 垂直方向 (Vertical)

对于 `--plane vertical`：

- X 轴从左向右增加。
- Y 轴向上增加。
- Z 轴固定在单层。 - 文本的第一行位于该区域的顶部。

这使得垂直模式适用于制作墙面文字。

## 输出文件名

如果未指定 `--output` 参数，ParaLite 将根据以下内容生成文件名：

- 内容的第一行非空文本，
- 当前日期，
- 输入内容的短 SHA-1 哈希值。

例如：

```text
hello-world-260906-a1b2c3d4.litematic
hello-world-260906-a1b2c3d4.png
```

哈希值有助于避免意外覆盖由不同输入内容生成的输出文件。

## 预览颜色

ParaLite 内置了一个小型 RGB 预览调色板，涵盖了常用的：

- 羊毛 (wool)
- 混凝土 (concrete)
- 陶瓦 (terracotta)
- 天然方块 (natural blocks)
- 精选资源方块 (selected resource blocks)

预览颜色仅为 Minecraft 最终外观的近似值。光照、纹理、着色器、资源包以及方块在 Minecraft 中的实际外观都会影响最终效果。

对于不在预览调色板中的方块，PNG 预览将使用白色作为替代显示，而结构文件 (schematic) 中记录的方块 ID 保持不变。

## 局限性

- 目前仅测试了内置的 **Mojangles / Mojang Seven** 字体。
- 字体支持情况取决于所选 TTF 字体文件中包含的字形。
- 不支持的字形可能会被替换或留空。
- 预览 RGB 值仅为近似值，并非 Minecraft 实际渲染的颜色。
- 不在内置预览调色板中的方块在 PNG 预览中显示为白色。
- `paragraph`（段落）模式使用**空行**来分隔段落。
- `line`（行）模式将每一行视为独立的材质单元。
- 当前渲染器是基于 8 像素高的 Minecraft 风格字形布局设计的。

## 项目结构

```text
ParaLite/
├── main.py
├── content.txt
├── font/
│   └── minecraft_font.ttf
├── pyproject.toml
└── README.md
```

## 更多功能（或许）

- [ ] 支持更多字体
- [ ] 支持可配置字形大小的通用 TTF 字体
- [ ] 支持其他像素字体
