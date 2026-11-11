# wx 内联版 HTML 红线（B3 验收阶段的判据权威）

违反本文任一条，推送后要么内容丢失，要么显示异常。本文是「不能有什么」的唯一权威：
`Write/references/b3-acceptance/scripts/validate_wx_html.py`（静态机检）与 `Write/references/b3-acceptance/scripts/qa_mobile.py`（真机渲染机检）实现的就是
这张表；「怎么写」（模板与排版）在 `../b2-typeset/wx-html-templates.md`，两边互不重复。
B2 不再自查产物形态——那是本阶段的职责。

来源与许可：检查项清单参考自一个 AGPL-3.0 许可的外部同类排版工具，实现代码为本仓库独立编写，
来源与许可记录见仓库 `CHANGELOG.md`。

## 一、产物形态（硬性）

- **单文件铁律**：全链路只维护一份 `article-wx.html`。本地预览与公众号后台共用同一份文件。
- **图片链接口径**：`<img src>` 必须是 `https://mmbiz.qpic.cn/...`（微信端只认它）。
  本地用 `file://` 直接打开时，微信图床防盗链会返回占位图（HTTP 200，内容是
  「未经允许不可引用」），`onerror` 兜底不会触发——本地看不到真图是预期行为，
  不算稿件问题，真图以公众号后台/编辑器预览为准；需本地核图时用 `wrap_preview.py`
  生成临时预览（写系统临时目录，不算产物）。
  **禁止另生成「本地预览版」「base64 存档版」「待推送版」等第二份 HTML 交付物**，也禁止为「本地看效果」另存一份。
  `wrap_preview.py` 生成的临时外壳只写系统临时目录，属预览工具、不算产物；
  B3 静态闸的「产物唯一性」判据（`check_single_artifact.py`）会在本机目录里拦下多出来的 HTML。
- **单一 HTML 文件，交付纯 `<section>` 正文片段**——不包 `<!DOCTYPE>`/`<html>`/`<head>`/`<body>`。
  公众号只认正文片段，文档外壳会被丢弃或干扰。
- 禁止 `<style>` 块、禁止外部 CSS/JS 引用、禁止 `<script>`（微信全部剥离或拒绝）；全部样式内联
  在元素 `style` 属性上。
- 正文图片必须为 `mmbiz.qpic.cn` URL（先 `uploadimg`，操作口径见
  `../b1-images/image-upload-interfaces.md`）；**禁止本地相对路径**（如 `../assets/xxx.png`，
  微信端必不显示）。
- **一步到位原则**：写 HTML 时直接引用 `uploadimg` 返回的 mmbiz URL——先批量上传全部配图得到
  URL 清单，再排版引用。「先写本地路径、事后替换」的中间态是历史返工来源：本地路径 HTML 一旦
  误推，图片全部不显示，修复需重推整篇。
- **base64 内联版仅按需归档，且不作为 wx-HTML 交付物**：只有用户明确要求「离线存档、图片内联、可断网打开」时才另生成，
  必须与 `article-wx.html` 分开命名、明确标注为离线存档，不得被当作推送版，也不得当作「本地预览版」。
  微信端不识别以 base64 作 `src` 的图片，归档版绝不能直接推送。存量 base64 存档需重推时，按「解码 base64 → `uploadimg` → 替换 src →
  校验 → 重推」一次性转换（上传操作见 `../b1-images/image-upload-interfaces.md`）。

## 二、标签与样式红线

| 写法 | 级别 | 微信端实际行为 |
|---|---|---|
| `<style>` / `<script>` / `<link>` | ERROR | 标签被剥离，样式与脚本全部失效 |
| `<pre>` | ERROR | 被剥离并折叠空格与换行，代码缩进全丢、不可读 |
| `<table>` | ERROR | 手机端整表不渲染，表格内容消失 |
| div + `display:table*` 伪表格 | ERROR | 预览端把单元格堆叠成纯文本，行列关系丢失（渲染不可靠，与视口宽度无关） |
| `class` / `id` 属性 | ERROR | 属性被剥离，选择器样式全部失效 |
| `position:fixed/absolute/sticky`、`float`、`@media`、`@keyframes`、`@import`、`display:grid`、`var(--x)`、外部字体 `url()` | ERROR | 不支持，样式被丢弃 |
| 本地路径或非 mmbiz 域名的 `<img src>` | ERROR | 图片不显示 |
| `<div>` | WARN | API 推送路径实测不清洗、样式保留（theme-default 组件 2 在用）；编辑器粘贴路径会被改写，官方不建议——能用 `<section>` 就用 `<section>` |
| `display:flex` | WARN | 部分机型换行/对齐异常 |
| 正文出现禁用词（「本文」「读者」「首先」等） | ERROR | 写作纪律项，词表 `BANNED_WORDS` 在 `Write/references/b3-acceptance/scripts/validate_wx_html.py` 内是**全仓唯一一份**，此处只引不改 |
| 中文后紧跟半角 `, ; ! ?`、英文直引号 | WARN | 排版观感，代码块内不计 |

其余要点：

- 样式级红线只查元素 `style` 属性值——代码块文本里写的 CSS 示例不算违规。
- 错误码与失效模式的原始出处：`references/gotchas.md` C1（正文 HTML 约束）与 D1–D3
  （校验脚本、禁用词、AI 味启发式）——本表与其结论一致，排障时按溯源去读对应组。

## 三、图数一致性（本阶段核，B1 不再自查）

HTML 里的 mmbiz 图引用数必须等于 B1 清单（`../b1-images/figure-manifest-spec.md`）里的正文图条数
（`kind: cover` 不计）。清单一说三张、正文只出现两张，说明排版漏图或清单虚报——在验收层拦下，
而不是等推送后图片消失才发现。此判据取代原 B1 的 `scan` 子命令，消除了「要先有 HTML 才能核图」
的环形依赖。
