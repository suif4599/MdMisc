# MdMisc

这是一个用于存放与排版有关的杂项工具的仓库

## 1. `mdcss/mdcss.py`

这是一个增强 vscode/markdown-preview-enhanced 插件功能的脚本，旨在拓展 markdown 的排版能力，让相对轻量的排版需求不必使用 $\LaTeX$

脚本生成的配置文件允许为PDF导出设置单独的主题，同时实现了图片的排版增强、表格的合并单元格、自定义字体、自定义页边距等功能

注意，脚本提供的部分功能必须使用 **Chrome (Puppeteer)** 才能生效

### 1.1 使用示例

```bash
python mdcss/mdcss.py \
    --font ~/.local/share/fonts/HanSans/CN/SourceHanSansCN-Regular.otf \
    --code-font ~/.local/share/fonts/maple-NF-CN/MapleMonoNL-NF-CN-Regular.ttf \
    --main-css preview_theme/github-light.css \
    --codeblock-css prism_theme/github.css \
    --print-margin "5mm" \
    --enable-parser
```

### 1.2 支持的功能

1. 打印样式
	1. 使用 `--main-css` 来设置打印时使用的正文主题，传入的相对路径在 `{EXTENSION_DIR}/crossnote` 中搜索
	2. 使用 `--codeblock-css` 来设置打印时使用的代码块主题，传入的相对路径在 `{EXTENSION_DIR}/crossnote` 中搜索
2. 图片
    1. 宽度设置：在alt中以1-2位整数开头，设置宽度百分比，`--enable-parser` 启用时还支持添加单位 `px` 来设置绝对宽度
    2. 单行多图布局：在alt中添加 `r`
    3. 左右对齐：在alt中添加 `L/R`
    4. 文字环绕图片：在alt中添加 `f`
    5. 反相：在alt中添加 `i`，反相仅在预览时生效
    6. 去除背景（实验性）：在alt中添加 `m`，原理为设置混合模式为 `multiply`，去除背景仅在预览时生效，该功能为实验性功能，可能存在部分异常
    7. 亮度反转（实验性）：当 `--enable-parser` 启用时，可以在alt中添加 `I`，亮度反转仅在预览时生效，该功能为实验性功能，可能存在部分异常
    8. 图片标题：当 `--enable-parser` 启用时，可以在alt中使用 `([.]title)` 来插入标题，开头的`.`会被替换成递增的 `图N:`，对于 `r` 样式的图片，可以在第一个子图中添加 `([.]subfigure-title([.]figure-title))` 来添加整体标题
3. 字体
    1. 使用 `--font` 设置全局字体，只需要给出一个字体文件，程序会自动解析同族字体
    2. 使用 `--code-font` 设置代码块字体，只需要给出一个字体文件，程序会自动解析同族字体
    3. 对于公式，始终使用默认字体
4. 多列排版（当 `--enable-parser` 启用时生效）
	1. 创建排版
		- 使用 `|||-` 来开始一个多列排版，`|||` 来分隔列，`-|||` 来结束多列排版，可以添加参数用来设置列宽和对齐方式
		- 多列排版支持除了浮动布局的图片之外的所有语法
	2. 设置列宽
		- 列宽支持百分比和像素的设置方式，使用 `%` 与 `px`，默认使用百分比
		- 不填写列宽时会平均分配（不是按内容宽度分配）
	3. 竖直对齐
		- 默认竖直对齐方式为向上对齐，使用 `:` 来指定对齐方式
		- 比如 `:240px` 表示列宽 240px 且向上对齐
		- 比如 `:50%:` 表示列宽 50% 且居中对齐
5. 页边距
    - 使用 `--print-margin` 设置页边距
6. 小标题编号（当 `--enable-parser` 启用时生效）
	1. 在标题开头的 `.` 会被替换成编号
	2. 编号有多种样式
		- `latin[Upper]`: `a)`, `b)`, `c)`
		- `roman[Upper]`: `i)`, `ii)`, `iii)`，上限3999
		- `chinese`: `一、`, `二、`, `三、`
		- `number`: `1. `, `2. `, `3. `，且 `number` 在连续使用时可以生成 `1.1. `, `1.2. `, `1.3. `
		- `none`: 不编号
	 3. 设置 `--auto-count` 参数为 `,` 分割的六个编号样式，默认 `none, chinese, number, number, latin, roman`
7. 段落缩进（当 `--enable-parser` 启用时生效）
   - 在文档开头添加 `@indent` 或 `<indent>` 来为该文档启用段落缩进
8. PDF导入居中（当 `--enable-parser` 启用时生效）
    -  `@import` 导入的PDF会居中显示
9.  表格增强（当 `--enable-parser` 启用时生效）
    1. 使用 `\` 删除单元格（包括标题），如需要输入`\`，请使用`\\\\`
    2. 使用 `c\d` 和 `d\d` 的前缀来表示合并单元格，使用 `:` 为单元格单独设置对齐
    3. 例子
        ```markdown
        | c2: 标题1 |      \     |     标题2    | 标题3 |
        | --------- | ---------- | ------------ | ----- |
        |   文本1   | :c2: 文本2 |       \      |  \\\  |
        |  r2 文本3 |    文本4   | :r2c2: 文本5 |   \   |
        |     \     |    文本6   |       \      |   \   |
        ```
10. 代码块不会另起一页，而是直接跟随上一页


## 2. `test/`

存放测试用markdown