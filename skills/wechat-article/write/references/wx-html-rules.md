# wx 内联版 HTML 硬规范（微信兼容）

违反本文任一条，推送后要么内容丢失，要么显示异常。可机检部分全部落在 `write/scripts/validate_wx_html.py`（静态）与 `write/scripts/qa_mobile.py`（真实浏览器渲染），本文只写「为什么」与模板。

## 一、产物形态（硬性）

- **单一 HTML 文件，交付纯 `<section>` 正文片段**——不包 `<!DOCTYPE>`/`<html>`/`<head>`/`<body>`。公众号只认正文片段，文档外壳会被丢弃或干扰。
- 禁止 `<style>` 块、禁止外部 CSS/JS 引用、禁止 `<script>`（微信全部剥离或拒绝）。
- 全部样式内联在元素 `style` 属性上。
- 正文图片必须为 `mmbiz.qpic.cn` URL（先 `uploadimg`，见 `materials/`）；**禁止本地相对路径**（如 `../assets/xxx.png`，微信端必不显示）。
- **一步到位原则**：写 HTML 时直接引用 `uploadimg` 返回的 mmbiz URL——先批量上传全部配图得到 URL 清单，再排版引用。「先写本地路径、事后替换」的中间态是历史返工来源：本地路径 HTML 一旦误推，图片全部不显示，修复需重推整篇。
- **base64 内联版仅按需归档**：只有用户明确要求「离线存档、图片内联、可断网打开」时才另生成，与推送版是两个文件、互不覆盖，不双份维护。微信端不识别 base64 图片，归档版绝不能直接推送。存量 base64 存档需重推时，按「解码 base64 → `uploadimg` → 替换 src → 校验 → 重推」一次性转换。

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
| 正文出现禁用词（「本文」「读者」「首先」等） | ERROR | 写作纪律项，见 `writing-discipline.md` |
| 中文后紧跟半角 `, ; ! ?`、英文直引号 | WARN | 排版观感，代码块内不计 |

其余要点：

- 代码内 `<` `>` `&` 必须转义为 `&lt;` `&gt;` `&amp;`。
- 行内缩进空格转 `&nbsp;`（4 空格 = 4 个 `&nbsp;`）；代码空行用 `<p style="...">&nbsp;</p>`。
- 样式级红线只查元素 `style` 属性值——代码块文本里写的 CSS 示例不算违规。
- 标题层级用 `<p>` + 加粗/字号实现，不用 `<h1>`–`<h6>`。
- 避免大面积深色/紫色系配色；代码块深灰底浅字是例外。

## 三、模板

### 代码块（`<section>` + 逐行 `<p>`）

```html
<section style="background:#F6F8FA;border:1px solid #E4E7EC;border-radius:8px;padding:14px 16px;margin:16px 0;overflow-x:auto;">
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;def create_order(oid, customer_id):</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if oid &lt; 0: raise ValueError("invalid id")</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;return order</p>
</section>
```

每行一个 `<p>`、`margin:0`、`text-indent:0`；`line-height:1.6` 保证行距可读；高亮行可给该行 `color:#B35900;font-weight:bold`；超过 15 行的代码只截关键片段。

### 条目卡片（表格的微信安全替代）

表格一律用条目卡片：每行一个 `<section>` + 内联样式，纯块级布局，微信端稳定。

```html
<section style="margin:0 0 12px;padding:12px 16px;background:#F7F8FA;border-left:4px solid #B08D3E;border-radius:6px;">
  <p style="margin:0 0 6px;font-size:16px;color:#1F3864;font-weight:bold;line-height:1.6;">条目名<span style="color:#8A8A8A;font-weight:normal;font-size:14px;">　副说明</span></p>
  <p style="margin:0;font-size:15px;color:#555555;line-height:1.7;">条目说明文字</p>
</section>
```

条目名 16px 加粗深蓝，副说明灰色小字，说明行 15px 灰。需要「表格」语义时，表头写成一行提示句（如「四类职责，各有各的落点：」），表体用卡片逐条列出。数据列多、必须保持行列结构的，渲染成图片（Mermaid 或 HTML 截图），不拼 HTML 表格。

条目卡片不在 `theme-default.md` 组件表内（该表只收录已验证产物用过的样式）；首次使用前先按本文模板验证一轮，再考虑并入主题表。

## 四、正文排版（套用主题资产）

- 样式单一来源：`theme-default.md`。主色深蓝 `#1F3864` + 点缀金 `#B08D3E`，大标题 22px 居中 + 金线装饰，章节标题 18px 加粗左竖条，正文 16px/1.9/首行缩进 2em，代码块 `#F6F8FA` 底，行内代码 `#C7254E`，图注 12.5px 灰。
- 手写样式容易漂移。**优先用 `write/scripts/build_blocks.py` 从 JSON 生成**：组件名与参数见脚本内 `BLOCKS`，生成物与 `theme-default.md` 逐字一致（`tests/test_theme_blocks.py` 比对，改文档或改脚本任一侧不一致即报红）。
- 需要新主题时，以 `theme-default.md` 为模板另建 `theme-<名称>.md`，并遵守「样式必须来自已验证产物」原则。
- 引用框、要点框：用 `<section>` 内边距 + 左边框，不用 flex 双栏。

## 五、配图与渲染

- **封面**：`materials/scripts/gen_cover.py` 生成——`python materials/scripts/gen_cover.py --out cover.png [--pattern layers|guard|grid|circuit] [--seed N]`；`--seed` 缺省随机，保证每篇不同。纯几何、无文字（避免字体缺失与版权问题）；宽比 2.35:1（2048×880，大卡 900×383 展示最佳）。
- **示意图**优先用 Mermaid（流程、状态机、架构），渲染为 PNG 后 `uploadimg` 换 mmbiz URL 再放入正文；图下配图注（theme-default 组件 8）。
- **Mermaid 渲染**：`write/scripts/render_mermaid.py <a.mmd> [b.mmd ...]`，输出同目录同名 PNG。浏览器 fallback 链：系统 Edge（msedge）→ 系统 Chrome（chrome）→ Playwright 默认 Chromium；全部不可用时给出明确报错与安装指引（`playwright install chromium`）。
- **正文图尺寸**：受正文图上传接口限制，格式与大小口径、超限错误码、上传前预检行为统一见 `materials/SKILL.md`「图片限制」与 `references/api-docs.md`「官方限额」；排版阶段只要求 `<img src>` 已是 `mmbiz.qpic.cn` URL。
