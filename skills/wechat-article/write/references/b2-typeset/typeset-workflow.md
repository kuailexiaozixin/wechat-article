---
name: typeset-workflow
summary: B2 排版流程的组件选用规则、blocks.json 契约、漏段与凭空加段检测、图注编号规则，以及产物形态的自检点。
---

# B2 排版：从纯文本稿到 `<section>` 片段

输入是内容轨道产出的纯文本稿 + B1 的图片清单与 mmbiz URL；输出是**单一 HTML 文件**
（纯 `<section>` 正文片段，样式全部内联）。

样式值只有一个来源：`write/references/b2-typeset/theme-default.md`。十类组件
（`h1` / `rule` / `h2` / `para` / `inline_code` / `code` / `image` / `caption` / `hr` / `card`）
的模板由 `write/references/b2-typeset/scripts/build_blocks.py` 承载，与那份 md 逐字一致，由 `tests/test_theme_blocks.py`
守着——**不要在别处再抄一份样式**。

## 组件选用的前提

主题 md 里写着：为使用某组件而补写内容，是本主题最禁止的用法。所以先问「这段内容需要不需要
这个组件」，不要问「这篇稿子还缺哪个组件」。`typeset_plan.py audit` 会在十类组件全部出现在
一篇短稿里时给 WARN，那是提醒回头检查，不是要求补齐组件。

代码块与条目卡片（表格的微信安全替代）的写法模板在本目录 `wx-html-templates.md`，
本文不重复。

## 命令一览

```bash
# 分步
python write/references/b2-typeset/scripts/typeset_plan.py plan <draft.md> -o blocks.json
python write/references/b2-typeset/scripts/typeset_plan.py embed blocks.json --map mmbiz_map.json -o blocks.embedded.json
python write/references/b2-typeset/scripts/build_blocks.py blocks.embedded.json -o <article.html>
python write/references/b2-typeset/scripts/typeset_plan.py audit blocks.embedded.json --draft <draft.md>
python write/references/b2-typeset/scripts/typeset_plan.py verify <article.html>

# 一条命令走完（有图时带 --map 启用 embed）
python write/references/b2-typeset/scripts/typeset_plan.py all <draft.md> -o <article.html> --map mmbiz_map.json
```

`plan` 把纯文本稿切成 blocks 骨架（标题/代码/图片/图注/分割线(hr)/引用/列表/加粗按稿件顺序落位），
它只是省手的起点，组件选择和图片插入仍要按稿子内容判断。`embed` 把 image 块的本地路径换成
mmbiz URL（一步到位原则的中继）。`audit` 与 `verify` 是 B2 的两道自检，卡的是
**排版过程本身有没有改内容、样式有没有手写漂移**，与 B3 的微信兼容红线、B4 的渲染层表现互不重叠。

## `audit` 判据

FAIL：

- 块类型不是 theme-default 组件（列出可用组件名）。
- `image.url` 是外链但不是 mmbiz 域名；或仍是本地路径 → B1 没做完就进排版了。
- **漏段**：稿件里有、blocks 里找不到的段落（漏排，或改稿后没同步 blocks）。
- **凭空加段**：blocks 里有、稿件中不存在的段落——排版阶段新增的内容必须回到稿件落字，
  不能只在 HTML 里出现。这条是「改稿只在源头改」纪律在排版层的兜底。
- 图注编号未从 1 连续递增、重复或倒序。

WARN：

- `caption` 紧跟的不是 `image`（编号容易错位）。
- image 与 caption 数量不等（每张图都应有图注）。
- 图注未以「图 N」开头（此时编号核对跳过，明确告知没有真的核）。
- 十类组件全出现在一篇短稿里。

## `verify` 判据（产物形态）

FAIL：产物含非 theme-default 的 style（手写漂移）——每个 style 必须能在 build_blocks 渲染的
组件样式集合里找到；这是 B2「样式单一来源」的兜底。
WARN：起始标签非 `<section>/<p>/<div>`；章节标题缺中文序号（分章则用「一、二、三」）；
未检出 theme-default 正文段样式指纹（`font-size:16px;color:#3f3f3f`）。

产物形态与微信兼容红线（`<style>`/`<script>`/`<pre>`/`class`/`id`/文档外壳/图片域名）是
B3 验收的判据，verify 不重复（旧版四项与 `validate_wx_html.py` 全重叠，属判据双写，已删）。

## 与相邻闸的分工

| 闸 | 抓什么 | 抓不到什么 |
|---|---|---|
| B2 `audit/verify` | 排版有没有改内容、组件用得对不对、产物形态 | 微信兼容性红线、真机像素 |
| B3 `validate_wx_html` | 标签/属性/样式红线、禁用词、标点 | 渲染层表现（窄视口会掩盖问题） |
| B4 `qa_mobile` | 390px 溢出、`display:table*`/grid、坏图 | 文字层面的禁用词与句式 |

三道都要跑，顺序不能调换；调换了会出现「过了后面的闸、其实前面还不合格」。
