# wx 排版模板与正文写法（B2 排版阶段规范）

本文是 B2 排版阶段的「怎么写」规范，收编自原 `wx-html-rules.md` 的模板章与正文排版章。
「不能有什么」的红线判据在 B3 验收阶段（`../b3-acceptance/wx-html-redlines.md`），
本阶段只对交付物负责成文与组装，不重复校验红线。

来源与许可：检查项清单参考自一个 AGPL-3.0 许可的外部同类排版工具，实现代码独立编写，
不依赖其任何文件；来源与许可记录见仓库 `CHANGELOG.md`。

## 一、代码块模板（`<section>` + 逐行 `<p>`）

```html
<section style="background:#F6F8FA;border:1px solid #E4E7EC;border-radius:8px;padding:14px 16px;margin:16px 0;overflow-x:auto;">
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;def create_order(oid, customer_id):</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if oid &lt; 0: raise ValueError("invalid id")</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;return order</p>
</section>
```

- 每行一个 `<p>`、`margin:0`、`text-indent:0`；`line-height:1.6` 保证行距可读。
- 代码内 `<` `>` `&` 必须转义为 `&lt;` `&gt;` `&amp;`；行内缩进空格转 `&nbsp;`（4 空格 = 4 个
  `&nbsp;`）；代码空行用 `<p style="...">&nbsp;</p>`。
- 高亮行可给该行 `color:#B35900;font-weight:bold`；超过 15 行的代码只截关键片段。
- **禁 `<pre>`**：微信剥离并折叠空格与换行，代码缩进全丢（红线判据见 B3）。

## 二、条目卡片（表格的微信安全替代）

表格一律用条目卡片：每行一个 `<section>` + 内联样式，纯块级布局，微信端稳定。

```html
<section style="margin:0 0 12px;padding:12px 16px;background:#F7F8FA;border-left:4px solid #B08D3E;border-radius:6px;">
  <p style="margin:0 0 6px;font-size:16px;color:#1F3864;font-weight:bold;line-height:1.6;">条目名<span style="color:#8A8A8A;font-weight:normal;font-size:14px;">　副说明</span></p>
  <p style="margin:0;font-size:15px;color:#555555;line-height:1.7;">条目说明文字</p>
</section>
```

- 条目名 16px 加粗深蓝，副说明灰色小字，说明行 15px 灰。
- 需要「表格」语义时，表头写成一行提示句（如「四类职责，各有各的落点：」），表体用卡片逐条列出。
- 数据列多、必须保持行列结构的，渲染成图片（B1 的 `gen_table.py` 出的表格图，或 Mermaid），
  不拼 HTML 表格（`<table>` 在手机端整表不渲染，见 B3 红线表）。
- 选型判据：条目少、每行文字多、需逐条强调 → 条目卡片；数据列多、需保持行列对齐、单元格
  文字短 → 图片表格。两者都不得拼 HTML `<table>`。
- 条目卡片已并入 `theme-default.md` 组件表（组件 10），可用 `build_blocks.py` 的 `card` 块
  直接生成（参数：`name`、`desc`，`sub` 可选），不必手写。

## 三、正文排版（套用主题资产）

- 样式单一来源：本目录 `theme-default.md`。主色深蓝 `#1F3864` + 点缀金 `#B08D3E`，大标题 22px
  居中 + 金线装饰，章节标题 18px 加粗左竖条，正文 16px/1.9/首行缩进 2em，代码块 `#F6F8FA` 底，
  行内代码 `#C7254E`，图注 12.5px 灰。
- 手写样式容易漂移。**优先用本目录 `Write/references/b2-typeset/scripts/build_blocks.py` 从 JSON 生成**：组件名与参数见脚本内
  `BLOCKS`，生成物与 `theme-default.md` 逐字一致（`tests/test_theme_blocks.py` 比对，改文档或改
  脚本任一侧不一致即报红）。
- 需要新主题时，以 `theme-default.md` 为模板另建 `theme-<名称>.md`，并遵守「样式必须来自已验证
  产物」原则。
- 引用框、要点框：用 `<section>` 内边距 + 左边框，不用 flex 双栏。
- 标题层级用 `<p>` + 加粗/字号实现，不用 `<h1>`–`<h6>`（`theme-default.md` 的 `h1`/`h2` 组件
  就是这个实现）。
- 避免大面积深色/紫色系配色；代码块深灰底浅字是例外。
