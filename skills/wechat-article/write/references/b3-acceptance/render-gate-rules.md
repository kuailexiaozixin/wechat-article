---
name: render-gate-rules
summary: B3 验收阶段渲染子闸的判据、环境前置检查、截图核对与 exit 2 / exit 1 的分界；渲染判据的唯一实现是 qa_mobile.py。
---

# 渲染子闸（移动端真机渲染）

静态校验查不出的渲染层问题，在这一道起真浏览器把关。

## 判据（`qa_mobile.py`）

```bash
python write/references/b3-acceptance/scripts/qa_mobile.py <article.html> \
    [--width 390] [--screenshot out.png] [--no-image-check] [--json]
```

1. **横向溢出**：文档 `scrollWidth` 超出视口宽度即 FAIL，并列出越界最多的元素（标签/尺寸/文本片段）。
2. **布局降级**：computed style 层面统计 `display:table*` / `grid` / `flex`。
   `display:table*`（div 伪表格）与 `grid` 判 FAIL——与宽度无关，390px 溢出判据抓不到
   （窄视口会把固定宽的 table-cell 压缩），而微信手机端会堆叠成纯文本；`display:flex` 记
   WARNING（部分机型换行/对齐异常）。
3. **坏图**：`<img>` 加载后 `naturalWidth==0` 即 FAIL——配图未显示要在推送前暴露。
   无网络环境可 `--no-image-check` 关闭本项（其余项不受影响，但输出会写明关掉了哪一项）。
4. **整页截图存盘**（默认 `<输入名>_qa<宽>.png`），交付人工核对观感。

浏览器 fallback 链：系统 Edge(msedge) → 系统 Chrome(chrome) → Playwright 默认 Chromium。
凭据无关，纯本地渲染。退出码：`0` 通过；`1` 有 FAIL。

## 门禁 `render_gate.py`

`write/references/b3-acceptance/scripts/render_gate.py` **不重新实现渲染判据**，只调 `qa_mobile.py`，
管它不管的三件事：

```bash
python write/references/b3-acceptance/scripts/render_gate.py preflight <article.html> [--width 390]
python write/references/b3-acceptance/scripts/render_gate.py run <article.html> [--json out.json]
python write/references/b3-acceptance/scripts/render_gate.py review --json <B4 结果> [--width 390]
```

- `preflight`：跑之前查环境（浏览器是否存在、playwright 是否可用、图是否已换成 mmbiz）。
  **把「跑不起来」和「跑了但没过」分开报**——环境问题被读成内容问题，会诱导人去改一份本来没问题的稿子。
- `run`：调 `qa_mobile --json`，落盘结构化结果 + 记录截图路径与尺寸。
- `review`：核对截图本身（存在、≥ 2000 字节、宽 == `--width`、高 > 宽），并汇总人工该看截图的
  哪几处——这是人工子闸的输入。

**为什么截图也要核**：`qa_mobile` 的退出码只覆盖像素与 computed style 的可测项。截图没落盘、
只有半屏、宽度和 `--width` 不一致，都不会反映在退出码里，但会让人工子闸的「观感确认」
变成对着空气签字。

退出码：`0` 通过；`1` 有 FAIL（稿件不合格）；`2` **环境不满足**（不是稿件问题，别改稿）。

## 本机环境实测

本机未安装 playwright（按用户规则禁止 `playwright install`，且严禁安装任何新的
Chrome/Chromium），因此 `qa_mobile.py` 与 `tests/test_qa_mobile.py` 在本机只能 SKIP，
`render_gate.py preflight` 正确返回 `exit 2` 并提示按本机 uv 规则装到 `D:\Python`。
**SKIP 不等于通过**：在有 playwright 的环境必须补跑这一道，交付说明里要写明本道闸的实际执行状态。

## 与相邻子闸的分工

静态子闸能判「有 `display:table`」但判不了「390px 下具体溢出多少像素、哪句被压断」；
渲染子闸能判像素但抓不到禁用词。本子闸输出的截图交人工子闸看四件事：首屏是否有完整一句、
代码有没有折断、图是否居中、有没有大面积深色块。
