# ParaLite: 文字投影生成器
本项目的功能是基于 [litemapy](https://github.com/SmylerMC/litemapy) 库，把文本用 **Mojangles（Minecraft）字体**打印到平面上，生成 `.litematic` 投影文件。换行和空格全部保留，每个字形按字体真实宽度排版（HTML/印刷体标准），基线对齐。

### versions
v0.1.0: 字体仅支持 mojangles (mojang seven)

## 安装

需要 Python ≥ 3.12 与 [uv](https://docs.astral.sh/uv/)。

    git clone <repo-url>
    cd ParaLite
    uv sync   # 创建 .venv 并安装 litemapy、fonttools、numpy、pillow

## 使用

    uv run main.py                                  # 用默认选项渲染 content.txt
    uv run main.py --content my_text.txt            # 指定输入文件
    uv run main.py --mode paragraph --choices 0101  # 批量材质选择

每次运行输出 **2 个文件**：

- `<输出名>.litematic` — 投影文件
- `<输出名>.png` — 文字渲染预览图（其实就是中间步骤拿出来的）

### content.txt

将要生成的文本全部粘贴进去即可，换行与空格全部保留。

字体缺少的字形会自动替换为可读的 ASCII 字符（`§`→`?`、`…`→`...`、智能引号→直引号、`—`→`-`、`■`→`?`）或留空。

### 模式（--mode）

| 模式 | 划分单位 | 每单位材质 |
| --- | --- | --- |
| `same`（默认） | 全部内容 | 一律使用 `--material`，不提问 |
| `paragraph` | **空行分隔**的段落 | 逐段提示 / `--choices` |
| `line` | **换行分隔**的每行 | 逐行提示 / `--choices` |

在 `paragraph` / `line` 模式下不给 `--choices` 时，会逐段（逐行）交互提示，回答可以是：

- `0` → `--material`
- `1` → `--alt-material`
- 任意方块 id（如 `minecraft:gold_block`），投影中会原样保留

批量模式：`--choices` 一次性给出每段选择（每段一个 0/1 字符，超出部分按 0 处理）：

    uv run main.py --mode paragraph --choices 01010101

> 注意：**不解析行级 `[block]` 前缀**（避免 `[playername]` 这类文本被误判），整段统一使用所选材质。

### utils 包

`utils/` 包提供可复用的构建模块：

| 函数 | 用途 |
| --- | --- |
| `text2image(rows, renderer, spacing, line_height)` | 文本行 → RGBA 图片 |
| `convert_image_to_blocks(image, background)` / `image2blocks` | 图片 → 方块网格 |
| `materialselect(count, m0, m1, previews)` | 命令行交互选择材质 |
| `BLOCK_COLORS` / `color_of` / `nearest_block` | 预设常见建材色板（羊毛、混凝土、陶瓦、自然方块及少量常用方块） |
| `_normalize(id)` | 把方块 id 规范成 `minecraft:...` 形式 |

## 选项

| 选项 | 默认 | 说明 |
| --- | --- | --- |
| `--content` | content.txt | 输入文本文件 |
| `--font` | font/minecraft_font.ttf | Mojangles 字体，其他字体未测试 |
| `--mode` | same | `same`=整篇同材质（默认）\| `paragraph`=空行分段 \| `line`=每行一段 |
| `--output` / `-o` | 自动 | 输出 .litematic 文件名 |
| `--material` | minecraft:white_concrete | 选择 0 的材质（same 模式也用它） |
| `--alt-material` | minecraft:black_concrete | 选择 1 的材质 |
| `--choices` | 无 | 批量材质选择：0/1 串，每段一个字符 |
| `--background` | 无(空气) | 背景板，如纯白背景或别的方块 |
| `--plane` | horizontal | horizontal=地面；vertical=墙面 |
| `--spacing` | proportional | proportional=真实字宽；mono=固定格子 |
| `--layers` | 1 | 每个像素在 Y 方向堆叠的层数（水平地面时 region 高度） |
| `--line-height` | 9 | 行高（8px 字形 + 间隔；行距可调，如 14） |
| `--y` | 0 | 基准 Y 高度（水平地面） |
| `--image` | 自动 | 预览 PNG 路径（默认与输出文件同名） |
| `--name` / `--author` / `--description` | - | 投影元数据 |

### 输出文件名

- 给 `--output/-o`：用指定文件名。
- 不给：根据内容自动生成，如 `i-see-the-player-you-mean-a1b2c3d4.litematic` —— 内容不同 → 文件名不同（内容哈希），无需担心版本覆盖；预览图默认同名 `.png`。

## 示例

    # 整篇白混凝土，叠 2 层，铺在地面
    uv run main.py --mode same --material minecraft:white_concrete --layers 2

    # 段落交替白/黑混凝土（批量模式）
    uv run main.py --mode paragraph --choices 0101 \
        --material minecraft:white_concrete --alt-material minecraft:black_concrete

    # 墙面金色文字 + 黑色背景板
    uv run main.py --mode same --plane vertical \
        --material minecraft:gold_block --background minecraft:black_concrete

    # 交互式逐段选材质（0 / 1 / 任意方块 id）
    uv run main.py --mode paragraph

## 限制

- 仓库只附带并测试了 Mojangles 字体。
- 色板之外的方块 id 在预览图中显示为白色，但 `.litematic` 中会原样保留你选择的方块 id。
- 缺失字形会被替换或留空（见 content.txt 一节）。
