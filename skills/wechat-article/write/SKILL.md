---
name: write
description: '公众号文章写作与 wx 内联版 HTML 排版：写作纪律（去 AI 味、不虚构场景/数据、代码即论据）、微信兼容 HTML 硬规范（内联样式、禁 <pre>、代码块 section+逐行<p>、< > & 转义、正文图 mmbiz URL、纯 section 片段、封面 2.35:1）、确定性合规校验（validate_wx_html.py）、通用排版主题资产（theme-default.md）、本地预览（wrap_preview.py）、标题/摘要长度约束、推送前检查清单。当用户要求“写一篇公众号文章”“做公众号排版”“转 wx 内联版”时使用。产出物为单一 HTML 文件（纯正文片段），供 draft/ 推送。'
---

# 公众号文章写作（Write）

从写作到「wx 内联版 HTML」的完整规范。**产出物 = 单一 HTML 文件（纯 `<section>` 正文片段）**：全部样式内联、无外部资源、正文图为 `mmbiz.qpic.cn` URL，可直接 `draft-add` 推送。本子技能不负责推送（`../draft/`）与图片上传（`../materials/`）。

## 〇、产物形态：mmbiz 单版本优先（不维护双版本）

**正式产物只有一个：mmbiz 推送版**——写作时按「一步到位」原则直接引用 `uploadimg` 返回的 `mmbiz.qpic.cn` URL，产物即最终可推送、可在线查看的版本，存 Tutorial 目录。

- **写作流程**：渲染/制作配图 → 批量 `uploadimg` 换 mmbiz URL（见 `../materials/`）→ 写 HTML 时直接引用 mmbiz URL → `validate_wx_html.py` 校验 → `draft-add` 推送。**不存在任何"先本地路径/先 base64、事后替换"的中间态**。
- **base64 内联版仅按需归档**：只有用户明确要求"离线存档、图片内联、可断网打开"时才生成，作为可选归档副本，**不作为写作常态、不与 mmbiz 版双份维护**。归档版与推送版是两个文件，互不覆盖。
- **存量 base64 存档版**：早期按要求内联的历史文章保留现状（线上已发布版即 mmbiz，本地存档仅供离线查看）；需要重新推送时按「解码 base64 → `uploadimg` → 替换 src → 校验 → 重推」转换，一次性完成。
- 微信端**不识别 base64 图片**：base64 版只用于本地查看，绝不能直接推送。

## 一、写作纪律（先于排版，不满足不进入排版）

1. **内容须有真实来源**：代码、数据必须来自真实仓库源码或真实文档，可逐行对照验证；**不得虚构场景、不得虚构数据**；教学/演示性质的金额与编号须明确标注「教学示例」「演示数据」「合成数据」。
2. **去 AI 味、去模板化、去八股**：
   - 禁止「本文」「读者」「首先/其次/最后」「总而言之」等套话（`validate_wx_html.py` 会命中禁用词）；
   - 禁止空洞概括（"该模块功能强大""通过以上代码我们可以看到"）；每一段都要有具体内容与证据；
   - 不堆砌同构排比，句式长短交错。
3. **生动有趣、通俗易懂、专业严谨**：可借鉴优秀财经/学术普及读物的叙事方式——用问题或现象开头，以代码/事实为证据推进，以结论收束；专业名词首次出现给出解释。
4. **代码即论据**：核心观点必须配真实代码片段，代码嵌入正文而非附录；代码前后有解释，说明"为什么这样写"。
5. **每篇一个主题**：逻辑自洽，结构为「问题/背景 → 证据（代码+数据）→ 机制解释 → 结论/延伸」；多篇成系列时每篇可独立阅读。
6. 语言风格与平台：中文简体；面向公众号读者，避免过于学术化的长难句。
7. **散文质感（活人感写作）**：非虚构成文按 `references/human-writing-nonfiction.md` 执行——材料门槛（1200 字需五件有来路的材料，不足则研究/追问/缩短）、动笔前五问说话位置、按局部问题推进、中文韵律（主干先交出来/连词减半/名词化还原）、事实边界与改稿七遍；成稿硬禁令（翻案腔/破折号/提示性冒号/黑话）用 `../scripts/check_prose.py` 清零（详见该文件第八、九节）。

## 二、wx 内联版 HTML 硬规范（微信兼容，违反即推送失败或显示异常）

### 产物形态（硬性）
- **单一 HTML 文件，交付纯 `<section>` 正文片段**——不包 `<!DOCTYPE>`/`<html>`/`<head>`/`<body>`（公众号只认正文片段，文档外壳会被丢弃或干扰）。
- 禁止 `<style>` 块、禁止外部 CSS/JS 引用、禁止 `<script>`（微信全部剥离或拒绝）。
- 全部样式内联在元素 `style` 属性上。

### 标签与样式红线
- **禁止 `<pre>` 代码块**：微信会剥离 `<pre>` 并折叠空格/换行，缩进全丢、代码不可读。代码块必须用 `<section>` 容器 + 逐行 `<p>`。
- **禁止 `<table>`**（ERROR 级；实测教训：0088 用 `<table>` 排"四层结构职责表"，微信手机端整表不渲染、表格消失）。**同时禁止 div + `display:table` 伪表格**——0088 改伪表格后微信预览端仍堆叠成纯文本（display:table 渲染不可靠）。表格一律用「条目卡片」`<section>` 结构（模板见下），列多必须保持行列结构的渲染成图片。
- `<div>` 为 **WARN 级**（非 ERROR）：API 推送路径实测微信不清洗、样式保留（theme-default 组件 2 在用）；但编辑器粘贴路径会被改写，官方红线不建议——**能用 `<section>` 就用 `<section>`**。
- 禁止 `class`/`id` 属性、禁止 `position:fixed/absolute/sticky`、`float`、`@media`、`@keyframes`、`display:grid`、CSS 变量、外部字体（样式级红线只查元素 style 属性，代码块文本中的 CSS 示例不算违规）。
- `display:flex` 为 **WARN 级**：微信端部分机型换行/对齐异常；多列布局优先用「条目卡片」或渲染成图片，单列容器无需 flex。
- 代码内 `<` `>` `&` 必须转义为 `&lt;` `&gt;` `&amp;`。
- 行内缩进空格转 `&nbsp;`（4 空格 = 4 个 `&nbsp;`）；代码空行用 `<p style="...">&nbsp;</p>`。
- 正文图片必须为 `mmbiz.qpic.cn` URL（先 `uploadimg` 换 URL，见 `../materials/`）；**禁止本地相对路径**（如 `../assets/xxx.png`，微信端必不显示）。
- **一步到位原则**：生成 wx 内联版 HTML 时，图片 URL 直接写入 `uploadimg` 返回的 mmbiz URL——先批量上传全部配图得到 URL 清单，再写作/排版时直接引用，**不存在"先写本地路径、事后替换"的中间态**。该中间态是历史教训：本地路径 HTML 一旦被误推，图片全部不显示，且事后替换需重推整篇。

### 代码块模板（可直接套用）

```html
<section style="background:#F6F8FA;border:1px solid #E4E7EC;border-radius:8px;padding:14px 16px;margin:16px 0;overflow-x:auto;">
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;def create_order(oid, customer_id):</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if oid &lt; 0: raise ValueError("invalid id")</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;</p>
  <p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;font-size:13.5px;color:#24292E;text-indent:0;">&nbsp;&nbsp;&nbsp;&nbsp;return order</p>
</section>
```

要点：每行一个 `<p>`、`margin:0`、`text-indent:0`；`line-height:1.6` 保证代码行距可读；高亮行可给该行 `color:#B35900;font-weight:bold`；行数多的代码块（>15 行）在正文中截取关键片段，完整代码注明仓库路径供对照。

### 条目卡片模板（表格的微信安全替代，禁止 `<table>` 与 div 伪表格）

**实测结论（2026-09-19，0088 两次打脸）**：`<table>` 在微信端整表不渲染、表格消失；改用 div + `display:table` 伪表格后，微信预览端仍堆叠成纯文本（display:table 渲染不可靠）。**表格一律改用「条目卡片」**——每行一个 `<section>` + 内联样式，纯块级布局，微信 100% 稳定：

```html
<section style="margin:0 0 12px;padding:12px 16px;background:#F7F8FA;border-left:4px solid #B08D3E;border-radius:6px;">
  <p style="margin:0 0 6px;font-size:16px;color:#1F3864;font-weight:bold;line-height:1.6;">条目名<span style="color:#8A8A8A;font-weight:normal;font-size:14px;">　副说明</span></p>
  <p style="margin:0;font-size:15px;color:#555555;line-height:1.7;">条目说明文字</p>
</section>
```

要点：每条一个 `<section>`（背景浅灰 `#F7F8FA`、左边框金 `#B08D3E`）；条目名 16px 加粗深蓝，副说明灰色小字；说明行 15px 灰。需要"表格"语义时，表头用一行提示句（如"四类职责，各有各的落点："），表体用卡片逐条列出。数据列多、必须保持行列结构的，**渲染成图片**（mermaid/HTML 截图）而不是拼 HTML 表格。

### 正文排版（套用通用主题资产）

- **系列文章一律套用 `references/theme-default.md`**（通用排版主题，样式单一来源）：主色深蓝 `#1F3864` + 点缀金 `#B08D3E`，大标题 22px 居中 + 金线装饰，章节标题 18px 加粗左竖条，正文 16px/1.9/首行缩进 2em，代码块 `#F6F8FA` 底，行内代码 `#C7254E`，图注 12.5px 灰。
- 非系列文章可自行排版，但不得违反「二、硬规范」红线；正文默认 15–16px、`line-height:1.75`、段间距 `margin:12px 0`、颜色 `#333`/`#2c2c2c`。
- 标题层级用 `<p>` + 加粗/字号实现（不用 h1–h6）。
- 避免大面积深色/紫色系配色；代码块深灰底浅字是例外。
- 表格：**禁止 `<table>` 与 div 伪表格**（微信端整表不渲染/堆叠，实测教训 0088 两次）——用「条目卡片」`<section>` 结构（模板见上）；列多必须保持行列结构的渲染成图片。
- 引用/要点框：用 `<section>` 内边距 + 左边框。

### 标题与摘要（草稿参数）
- 草稿 `--title` ≤ **64 字节**（中文 3 字节/字，约 21 字）：取正文大标题的短句，完整标题放 HTML 正文首行。
- 草稿 `--digest` ≤ **120 字符**：一句话摘要，突出主题与卖点。
- 作者名由 `WECHAT_AUTHOR` 环境变量控制。

### 配图规范（系列文章）
- **封面每篇更换**：用 `../materials/scripts/gen_cover.py` 生成——`python gen_cover.py --out cover-<篇号>.png [--pattern layers|guard|grid|circuit] [--seed N]`；`--seed` 缺省随机保证每篇不同。纯几何、无文字（避免字体缺失与版权问题）；宽比 2.35:1（2048×880，大卡 900×383 展示最佳）。
- 示意图优先用 **Mermaid 图**（流程、状态机、架构），渲染为 PNG 后 `uploadimg` 换 mmbiz URL 再放入正文；图下配图注（见 theme-default 组件 8）。
- **Mermaid 渲染工具**：`scripts/render_mermaid.py <a.mmd> [b.mmd ...]` 渲染输出同目录同名 PNG。浏览器 fallback 链：系统 Edge（msedge）→ 系统 Chrome（chrome）→ Playwright 默认 Chromium；全部不可用时给出明确报错与安装指引（`playwright install chromium`）。

## 三、推送前校验（确定性兜底，必跑）

把产物写入文件后，**必须运行校验脚本，ERROR 清零才算完成**：

```bash
python scripts/validate_wx_html.py <article.html>
```

它确定性检查：禁标签（`<style>/<script>/<link>/<pre>/<table>`；`<div>` 为 WARN）、禁属性（class/id）、禁样式（position/float/@media/grid/变量/外部字体，只查 style 属性；flex 为 WARN）、图片必须 mmbiz 域名（本地路径 ERROR）、产物为纯 section 片段、写作纪律禁用词、正文半角标点（WARNING）、**AI 味启发式**（空洞修辞短语 / 感叹号 >3 / 最长段落 >120 字 / 段落平均 >80 字 / 编号排比，WARNING 级，见 `../references/gotchas.md` D3）。**ERROR 必须修复到 0；WARNING 也逐项确认**——半角标点、图片域名与空洞修辞是实际返工最高频的三类。

**跨篇重复检测（系列文章）**：`python scripts/check_duplicates.py <Tutorial目录> [--min-len 40] [--threshold 0.8]`，扫描目录内全部 HTML 的跨文件重复段落（字符 4-gram Jaccard）。系列文章多，跨篇照搬段落会稀释每篇独立价值，发布前对新篇跑一次（`--fail` 可让重复时退出码 1）。

**散文硬禁令检测（成稿文本）**：`python scripts/check_prose.py <稿件.md/.txt>`——查翻案句（含变形）、黑话、硬停词、模型路标、破折号与提示性冒号（判定源见 `../references/human-writing-nonfiction.md` 第八节）。在正文纯文本阶段跑（HTML 成稿可提取正文纯文本后检查），失败项清零后再排版。

本地预览（推送前自查排版效果）：

```bash
python scripts/wrap_preview.py <article.html>
```

生成 `<原文件>_预览.html`，浏览器打开可模拟公众号阅读并一键复制。预览外壳不影响校验（校验对原文件跑）。

## 四、写作 → 推送流程

1. **素材准备**：读取仓库源码/文档，抽取真实代码片段；核算数据口径；渲染 mermaid 配图（如有）。
2. **预上传图片（一步到位）**：将全部配图批量 `uploadimg`（见 `../materials/`），得到「图片 ↔ mmbiz URL」清单（`--map` 写 JSON，键为图片 basename）。
3. **直接写 wx 内联版 HTML**：按「一、写作纪律」成文 + 按「二、硬规范」排版，HTML 中所有 `<img src="...">` 直接写 mmbiz URL。**不存在 Markdown 中间产物**——正文、代码块、图片 URL 全部在 HTML 生成时一步到位。
4. **校验 + 预览**：`validate_wx_html.py` ERROR=0；`wrap_preview.py` 本地自查。
5. **推送**：`../draft/` 的 `draft-add`（或简易版 `../scripts/wx_draft_push.py`）推草稿 → `draft-get` 抽查 → 交付预览。

> 兼容路径（仅历史遗留）：若手里已有引用本地路径的 HTML，才需要"上传 → 替换 → 重推"的事后补救；**新写文章一律按第 2–3 步一步到位**。

## 五、推送前检查清单（校验脚本兜底 + 人工抽查）

- [ ] `validate_wx_html.py` 输出 ERROR=0（自动）
- [ ] `check_prose.py` 硬禁令清零（翻案句/黑话/硬停词/冒号/破折号；自动）
- [ ] 产物为纯 `<section>` 片段，无文档外壳（自动 WARNING）
- [ ] 无 `<pre>`、无 `<table>`、无 div 伪表格；代码块为 `<section>` + 逐行 `<p>`，表格为条目卡片（自动）
- [ ] 代码内 `<` `>` `&` 已转义；缩进用 `&nbsp;`（自动抽查）
- [ ] 全部图片为 `mmbiz.qpic.cn` URL，无本地路径（自动）
- [ ] 无禁用词/套话（「本文」「读者」「首先其次」等按项目纪律清零，自动）
- [ ] 金额/编号类演示数据已标注「教学示例/演示数据」（人工）
- [ ] 代码片段与仓库源码一致（人工抽查关键行）
- [ ] `--title` ≤64 字节、`--digest` ≤120 字符（人工）
- [ ] 封面图已准备且每篇不同（人工）

## 六、与其他子技能的关系

- 产出 HTML → `../materials/`（uploadimg 换图）→ `../draft/`（draft-add 推送、draft-get 抽查）；发布走公众号后台手动操作（个人未认证账号发布接口族 48001，见根 `../SKILL.md`「发布」节）。
- 两个 CLI 均可推送：`../scripts/wx_api.py draft-add`（全能力）与 `../scripts/wx_draft_push.py --html ... --title ... --digest ... [--cover ...]`（简易单命令版）。
- 读取已发布文章作为参考：`../Read/`；查找文章：`../Search/`。
