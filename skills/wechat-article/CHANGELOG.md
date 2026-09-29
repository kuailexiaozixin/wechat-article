# CHANGELOG — wechat-article

本技能变更记录（与 git 提交一一对应）。

## 4.1.0（2026-09-28）publish 子技能移除 · 发布知识并入母技能 · 排版主题通用化（可外发整改）

- **publish 子技能整体移除**：实测个人主体/未认证账号调用发布接口族（freepublish/submit|get|batchget|delete）
  一律返回 48001（2025-09 与 2026-09 两轮实测），子技能主体内容失效。有效内容并入：
  - 根 SKILL.md 新增「发布（个人未认证账号实测）」节：check-perm 权限探测、后台手动发布引导、
    「发布前四项后台手动设置」清单（开赞赏/声明原创/选择合集/创作来源 AI 生成，合集名按账号实际调整，
    不再绑定任何系列名）；draft/SKILL.md 第 4 步同步替换。
  - references/gotchas.md：保留 A3（48001/53010 接口族实测），删除 F1（发布状态码表，随接口失效）。
- **脚本清理**：删除 scripts/publish_status.py；wx_api.py 移除 publish/publish-get/publish-list/publish-delete
  四个子命令（保留 check-perm 权限探测）；py_compile 通过。
- **排版主题通用化**：write/references/theme-fasterp.md 更名 theme-default.md，去除系列品牌表述，
  改为「通用排版主题（默认主题）」；write/SKILL.md 四处引用同步；materials/gen_cover.py 去系列品牌。
- **母 SKILL.md 去个人化**：WECHAT_AUTHOR 示例值改为占位符；「FastERP 系列排版资产/封面生成器」
  表述改为通用表述；版本 4.0.5 -> 4.1.0。

## 4.0.5（2026-09-21）draft-add 作者字段 45110 修复（FastFPA 29 篇全链路实测）

全系列 29 篇教程推送实测发现并修复：

- **author 字段 45110 修复（关键 bug）**：`wx_api.py` 与 `wx_draft_push.py` 的默认作者名
  「数据舞者Ivy Notes」本身超过部分账号 author 字段长度上限，凡未配置 `WECHAT_AUTHOR`
  的用户 `draft-add` 必然报 `45110 author size out of limit`。修复：两脚本默认作者改为空，
  author 为空时**整体省略该字段**（不再发送）；docstring 与根 SKILL.md 同步更新。
  实测：配置 `WECHAT_AUTHOR` 后 29 篇全部推送成功。
- **SKILL.md 示例作者名**更新为实际使用值「作者名」。
- **实测确认可执行（2026-09-21，29 篇全链路）**：token / cover（永久素材）/ uploadimg（正文图
  换 mmbiz URL）/ draft-add / draft-get / draft-count / draft-list / draft-delete /
  check_draft（回读核验）/ validate_wx_html 全部按文档行为工作。
- **实测补充两条接口事实（已回写 FastFPA 教程写作纪律）**：
  1. `draft-list` 单页上限 20 条，批量对账须按 total_count 翻页，否则误判缺稿；
  2. `publish-list` 对未认证账号返回 48001，箱内草稿缺失无法经接口核实原因，
     重推前必须先与用户确认是否已在后台人工发布/删除（发布后草稿会离开草稿箱）。
- 本次 29 篇推送的媒体资产：封面 29 张（add_material 永久素材）+ 正文图约 60 张（uploadimg），
  均在官方限额内。


## 4.0.1（2026-09-18）清理无法执行的内容

按用户要求清理技能中无法执行/过时的内容，全部经实测验证：

- **命令路径修正（关键）**：`publish/SKILL.md` 能力表 5 处 `python wx_api.py ...`
  与 `draft/SKILL.md` 6 处、`materials/SKILL.md` 2 处 `python wx_api.py ...`
  统一为 `python ../scripts/wx_api.py ...`（此前在子技能目录下直接跑
  `wx_api.py` 会因文件不存在而无法执行；根目录/scripts 目录写法不受影响）。
- **去除外部技能依赖**：read/SKILL.md 原两处引用 browser-automation（含 browser4-cli / playwright-mcp）的连接方法已全部移除；新建 `read/references/cdp-edge.md` 将「读取 DevToolsActivePort 直连 WebSocket」方法搬运为技能内自包含文档（含禁止 Origin 头、帧 masked、 UUID 每次重启变化、HTTP 端点 404、CDP 消息 id 循环匹配等已验证细节）。 全技能外部技能引用扫描归零。
- **wx_api.py**：docstring `publish-delete <publish_id>` 修正为 `<article_id>`
  （官方接口 freepublish/delete 实收 article_id）；注释「gotchas 19」修正为
  「gotchas B5」（gotchas 已重组为 A–G 分组编号）。
- **read/SKILL.md**：依赖库标注 `beautifulsoup4` 为可选（本机未安装，
  缺失时降级 html.parser / 纯正则路径，实测降级链有效）；
  确认 browser-automation 技能与 playwright-mcp / Chrome-DevTools-MCP /
  browser4-cli 子技能存在，CDP 引用有效。
- **实测确认可执行**：10 个脚本 py_compile 全过；gen_cover 4 图案 +
  --help 正常；wrap_preview 生成预览页正常；upload_imgs --help / 快速失败正常；
  render_mermaid --help / 文件缺失快速失败正常（不启动浏览器）。
- **草稿箱现状**：实查 total_count=0（全部 67 篇已发布并清空）；
  publish 接口族仍 48001，发布核对以公众号后台为准。

## 4.0.0（2026-09-18）十二项改进全部落地

按用户拍板的 12 条建议全部实现并验证（草稿回读核验 / WAF 501 自动绕行 / 发布权限预探测 /
AI 味启发式 / 封面生成器入技能 / 批量上传 token 复用 / mermaid fallback / 发布状态台账联动 /
gotchas 主题重组 / 跨篇重复检测 / 发布不可逆确认 / 凭据泄露提醒）。

### 新增脚本（4 个）
- `scripts/check_draft.py` — 草稿回读自动核验：断言标题 ≤64B、摘要 ≤120 字符、thumb 非空、
  无 `<pre>`/`<style>`、mmbiz 图数=预期、无本地图片路径；`[PASS]/[FAIL]` 逐项输出，退出码 0/1；
  `--json` 结构化输出。
- `scripts/publish_status.py` — 发布状态台账联动：分页拉已发布文章（标题/URL/日期）→ 按标题
  子串匹配（≥4 字防误匹配）更新 xlsx 状态列「已发布 YYYY-MM-DD」；`--dry-run` 预览；修改前自动
  备份；48001 不改台账并说明。
- `materials/scripts/gen_cover.py` — FastERP 封面生成器入技能：4 种几何图案
  （layers/guard/grid/circuit），`--seed` 缺省随机保证每篇不同，`--size` 可调，纯几何无文字。
- `write/scripts/check_duplicates.py` — 跨篇重复段落检测：字符 4-gram Jaccard，跨文件相似段落
  报告，`--fail` 可阻断。

### 修改脚本（3 个）
- `scripts/wx_api.py`：
  - `draft-update` 遇 WAF 501（`non-JSON response`）自动绕行：回读原封面 → `draft-delete` →
    `draft-add`，返回新 media_id 并标注 `bypass:true`（gotchas B5 从人工绕行升级为自动）。
  - 新增 `check-perm` 子命令（只读探测发布接口权限）。
  - `publish` 必须 `--yes`（不可逆确认，缺省退出码 2）；执行前自动权限预探测
    （48001/53010 直接引导后台手动发布，退出码 3，不提交）。
- `write/scripts/validate_wx_html.py` — 新增 AI 味启发式（WARNING 级）：空洞修辞短语 22 个、
  正文感叹号 >3、最长段落 >120 字、段落平均 >80 字、「其一其二其三」「一是二是三是」编号排比；
  单测通过（命中组 7 项 WARN / 对照组零 AI 味误报）。
- `materials/scripts/upload_imgs.py` — 一次取 token 循环上传全部图片（不再逐张 subprocess 现取）；
  45009 自动退避重试（3s/6s/9s，最多 3 次）；复用 wx_api.py 的 get_token/multipart_upload。
- `write/scripts/render_mermaid.py` — 浏览器 fallback 链：msedge → chrome → Playwright 默认
  Chromium；全部不可用给出明确报错与 `playwright install chromium` 指引。

### 文档更新
- `references/gotchas.md` — 按主题重组：A 凭据与权限 / B 草稿推送 / C 正文与图片 /
  D 校验与写作 / E 环境与编码 / F 发布状态 / G 封面；新增 D3（AI 味启发式）；原 19 条编号改为
  主题编号（A1–G1），内容全部保留。
- 根 `SKILL.md` — version 3.1.0 → 4.0.0；description 补全新能力；辅助脚本清单更新；
  操作前安全习惯第 2 条改为「validate + check_draft 双校验」。
- `write/SKILL.md` — 校验章节加 AI 味 WARNING 与 check_duplicates；配图规范加 gen_cover.py
  与 mermaid fallback。
- `materials/SKILL.md` — 加 gen_cover.py 封面生成器、upload_imgs token 复用说明。
- `draft/SKILL.md` — 回读核验步骤改为 `check_draft.py`；能力表加 check_draft；501 自动绕行说明。
- `publish/SKILL.md` — 能力表加 check-perm / publish --yes / publish_status.py；工作流加权限
  预探测与台账联动步骤。

### 验证
- 全部 10 个脚本 py_compile 通过；check_draft/publish_status/gen_cover(4 pattern)/
  check_duplicates/validate(AI 味)/wx_api(501 分支) 均做功能单测或冒烟。
- gotchas 结构校验：A–G 七组、编号连续、D3 在 D 组内、内容 20 条无丢失。

## 3.3.2（2026-09-18）清除 Write 中 Markdown 相关内容

按用户要求删除 Write 子技能内所有涉及 Markdown 的内容，写作流程改为直接产出 wx 内联版 HTML（不存在 Markdown 中间产物）。

### 删除文件（4 个）
- `write/scripts/build_wx.py`（Markdown 母本 → wx 内联版 HTML 转换器）
- `write/scripts/fix_quotes.py`（Markdown 母本引号全角化）
- `write/scripts/extract_docx.py`（Word docx → Markdown 提取器）
- `write/references/format-normalize.md`（素材归一化：万物先转 Markdown）

### 修改文档（5 个）
- `write/SKILL.md`：删除「〇、素材归一化」节与「Markdown 母本 → wx 内联版」节；写作流程改为「直接写 wx 内联版 HTML，图片 URL 一步到位」；description 移除「素材归一化」。
- `write/references/theme-fasterp.md`：删除「映射规则（Markdown → 组件）」表，保留 HTML 组件库本体。
- 主 `SKILL.md`：辅助脚本列表移除 build_wx/fix_quotes/extract_docx；Write 行能力描述移除「素材归一化」。
- `references/gotchas.md`：删除第 15 条「转换器路径」；重编号 16–20 → 15–19；改写 `<div>` WARN 说明与 mmbiz-map 条目中的 build_wx 引用（改为「写作排版按图名查 URL」）；顺带清除 79/80 行历史混入的 / 控制字符。
- `materials/scripts/upload_imgs.py`：两处注释移除 build_wx 引用。

### 验证
- 全技能扫描 `build_wx|fix_quotes|extract_docx|format-normalize|母本` 残留为 0；gotchas 条目编号连续 1–19；剩余脚本 py_compile 全部通过。

## 3.3.1（2026-09-18）板块九复核修复

板块九三篇（0066/0067/0069）反复核实查验，逐段与 FastERP 仓库源码对照；每篇新增 1 张配图（快照构成 / SSE 时序 / 三条红线），修复 6 类内容问题，升级 fix_quotes 保护行内代码。

### 修复 1：fix_quotes.py 误全角化行内代码引号（脚本层）
- 现象：已推送草稿的行内代码出现弯引号，如 `json.loads(chunk[6:]).get(“token”)`、`if provider in (“xai”, “openai”)`，不符合 Python 语法观感。
- 本质：fix_quotes 只跳过 ``` 代码块，行内代码 `...` 内的英文引号被正则 `"([^"]*)"` 一并全角化。
- 解决：升级 fix_quotes.py——先用 ``(`[^`]*`)`` 拆出行内代码段，只全角化非代码部分；三篇母本中 6 处已误全角化的行内代码引号手动改回半角。
- 验证：重建后 validate ERROR=0，draft-get 回读行内代码引号为半角。

### 修复 2：内容核实修正 6 处（写作层）
- 0066：“四个函数”与标题“三个聚合函数”矛盾 → 改“三个函数，三层聚合”；“客户欠我们多少钱”含人称 → 改“客户欠了多少钱”；“只做一件事”表述不精确 → 改“主要动作只有一个”；时效段逻辑绕 → 重写为“快照只在提问的瞬间计算”。
- 0067：开篇虚构金额举例（84,920/85,000）→ 改为不出现具体数字的表述。
- 0069：“每一问一答都有时间戳”补充依据——SQLite 分支 INSERT 显式写入 `datetime('now')`（db.py 第 169–170 行）。

### 修复 3：PowerShell Set-Content 编码损坏母本（流程警示）
- 现象：0067/0069 母本经 PowerShell `Set-Content -Encoding utf8` 写回后变为 0 字节。
- 本质：PowerShell 5.1 的 Set-Content 数组写回与编码处理不可靠，且去 BOM 逻辑叠加后数据全失。
- 解决：母本重建改用 Write 工具（UTF-8 直接写入），文件写回一律走 Python `open(p,'w',encoding='utf-8')`，不再使用 PowerShell Set-Content 写中文内容。
- 固化：写作流程要求母本创建/修改只用 Write 工具或 Python，禁止 PowerShell Set-Content。

### 图片增强
- 每篇新增 1 张 mermaid 渲染配图（与既有图同配色：金 #B08D3E 边框、深蓝 #1F3864 文字）：0066 快照构成（1484×119）、0067 SSE 时序图（1484×624）、0069 三条红线（1484×874）。
- 三张新图 uploadimg 换 mmbiz URL 后写入对应 map JSON（各 2 条）；三篇重建 validate ERROR=0；draft-update 重推（带原封面）全部 errcode 0；draft-get 回读核验：标题/摘要/封面齐全、正文 mmbiz 图×2、无 <pre>、行内代码引号半角。
- 板块九目录三篇 HTML 已更新为双图版并经 inline_images 全量内联（0 miss、0 残留 http 引用），assets 目录已清理。

## 3.2.2（2026-09-17）板块七复核修复

板块七三篇（0055/0057/0059）反复核实查验，逐段与 FastERP 仓库源码对照；按用户要求删除母本内 mermaid 源码块（只保留渲染图引用）。
### 修复 1：draft-update 被腾讯 WAF 501 拦截，绕行 delete+add（流程层）
- 现象：0055 最终版 `draft-update` 连续三次返回 `{"errcode":501,"errmsg":"non-JSON response"}`（raw 为 `waf.tencent.com/501page.html`），退避 20s/60s 重试均无效；同批 0057 draft-update 成功、0055 的 draft-get 正常。
- 本质：腾讯网关对特定草稿的 `draft/update` 写请求（约 47KB）做风控拦截，与重试次数无关。
- 解决：`draft-delete` 旧草稿 + `draft-add` 新草稿（同标题/摘要/封面），新 media_id 内容一致。delete/add 实测不受拦截。
- 固化：`references/gotchas.md` 新增第 20 条。
### 修复 2：母本 mermaid 源码块移除（写作层）
- 现象：母本中 ```mermaid 代码块经 build_wx 落入 wx 内联版，公众号编辑器粘贴路径下会显示源码文本而非渲染图。
- 解决：按用户指示，母本只保留 `![图注](assets/fig/xxx.png)` 渲染图引用，mermaid 块从母本删除；.mmd 源文件与渲染脚本仍留存于板块 assets/fig/ 供复现。
- 验证：三篇重建后 validate 全部 ERROR=0（0059 改写一处正文半角引号触发行后 WARNING 清零），draft-get 回读无 flowchart/graph 残留、mmbiz 图×2、封面/标题/摘要齐全。

板块二四篇（0010/0011/0014/0015）反复核实查验，逐段与 FastERP 仓库源码对照。

### 修复 1：draft-update 不带 --cover 返回 40007（wx_api.py）
- 现象：0011 母本修正后 `draft-update` 重推，返回 `{"errcode":40007,"errmsg":"invalid media_id"}`；`draft-get` 同一 media_id 完全正常。手动携带原封面 thumb 后 `errcode 0`。
- 本质：`draft/update` 要求 `articles.thumb_media_id` 为有效素材 id——省略或空串均判 40007，报错文案误导为 media_id 无效。先前 `build_article` 在空封面时省略该键，仍失败。
- 解决：`draft-update` 未传 `--cover` 时先 `draft-get` 回读原 `thumb_media_id` 再构建 article；`article` 构建移到 thumb 解析之后（先构建后回读仍带空封面）。脚本路径验证 `errcode 0`。
- `references/gotchas.md` 新增第 19 条。

### 修复 2：0011 母本令牌签发代码块改为真实逐行形态（写作层面）
- 现象：0011 第三节「隐式的上下文管理」代码块为拼接形态（`with self._db() as db:` 下平铺 `_issue_token` 的 DELETE+INSERT SQL），与真实源码 `_issue_token(self, db, ...)`（db 为调用方传入的参数）不一致。
- 解决：改为 forgot 的真实逐行形态（`with self._db() as db:` 内 SELECT 校验 + `_issue_token(db, row["id"], "reset", 3600)` 调用），正文说明 `with sqlite3.connect(...)` 的 commit/rollback 语义与 `_issue_token` 内部两条写操作。
- 验证：build_wx → validate ERROR=0 → draft-update 重推 `errcode 0` → draft-get 回读标题/摘要/封面/正文 mmbiz 图 ×2/代码块新形态全部合格。

## 3.1.0（2026-09-17）板块八实战检验修复

板块八 4 篇（0060/0062/0063/0064）写作推送全链路实测，发现并修复：

### 修复 1：Markdown 母本转换器缺失（最大缺口）
- 现象：新板块首次构建时 `build_wx.py`/`fix_quotes.py` 不存在于技能内，只能从板块六 assets 复制；技能文档写着"可先写 Markdown 母本再转 wx 内联版"，但转换器本身不是技能资产，散落各板块。
- 本质：方法描述与工具资产分离——规范承诺的能力没有对应的可复用实现。
- 解决：`build_wx.py`（母本 → wx 内联版，theme-fasterp 组件）与 `fix_quotes.py`（正文引号全角化）纳入 `write/scripts/`；`write/SKILL.md` 新增「Markdown 母本 → wx 内联版（转换器，首选路径）」小节与流程第 5 步转换器路径；根 SKILL.md 辅助脚本清单补齐。

### 修复 2：装饰线 `<div>` → `<section>`（WARN 清零）
- 现象：`validate_wx_html.py` 每篇报 1 处 `<div>` WARN，来源是 `build_wx.py` 的 `P_LINE` 装饰线。
- 本质：历史产物用 `<div>`（API 路径实测可用），但新产物可完全避免——`<section>` 默认 display:block，样式与 `<div>` 一致，两条推送路径都安全。
- 解决：技能内 `build_wx.py` 的 `P_LINE` 改为 `<section>`；板块八 4 篇 wx 产物重建后校验 WARN 清零（已推送草稿保持原状，`<div>` 在 API 路径安全，不重推）。

### 修复 3：`draft-get` 输出 BOM 陷阱
- 现象：PowerShell `Out-File -Encoding utf8` 写 BOM，`json.load` 报 `Unexpected UTF-8 BOM`。
- 本质：调用侧编码问题，非技能脚本缺陷。
- 解决：`references/gotchas.md` 新增第 16 条（draft-get 输出用 `utf-8-sig` 读或 `utf8NoBOM` 写）。

### 修复 4：转换器用法文档化
- `references/gotchas.md` 新增第 15 条（转换器路径：fix_quotes → upload_imgs → build_wx → 校验 → 推送；母本无 BOM 要求）。

## 3.0.3（2026-09-17）板块六实战检验修复

> **许可合规说明（AGPL-3.0）**：`write/scripts/extract_docx.py` 逐字移植自
> gzh-design-skill（AGPL-3.0，作者 甲木 × 摸鱼小李）；`validate_wx_html.py`、
> `wrap_preview.py`、`format-normalize.md` 借鉴其方法体系。上述文件均已标注
> 来源与许可。本技能如对外分发，涉及这些文件的部分须遵循 AGPL-3.0 开源。
> 源技能 gzh-design-skill 已于 2026-09-17 移入
> `fasterp_ledger_backup\gzh-design-skill\`（保留备查）。

### 修复 6：validate_wx_html.py 对英文词内撇号误报
- 现象：0048 正文含科目名 Owner\'s Equity，校验器 ASCII_QUOTE 将撇号判为半角直引号，误报 WARNING。
- 本质：ASCII 单引号检测未区分「英文所有格撇号」与「中文语境直引号」。
- 解决：新增 APOSTROPHE_WORD（[A-Za-z]'\w 等），检测前先剔除英文词内撇号；0047/0048 均回归通过。
## 3.0.2（2026-09-17）板块六实战再修复

### 修复 3：`wx_api.py` http_json 对非 JSON 错误响应崩溃
- 现象：`draft-update` 返回 501（腾讯 WAF 拦截页，HTML 而非 JSON），`json.loads` 直接抛 `JSONDecodeError`，真实错误被吞。
- 本质：错误路径只假设"永远是微信 JSON 错误体"，遇到网关/防火墙 HTML 页就崩。
- 解决：HTTPError 分支先尝试解析 JSON，失败则返回 `{"errcode": code, "errmsg": "non-JSON response", "raw": ...}` 供诊断。

### 修复 4：`upload_imgs.py` `--map` 覆盖写丢失旧映射
- 现象：先传流程图生成 map，再传封面 `--map` 同文件，旧映射被整份覆盖，HTML 里流程图退回本地路径。
- 解决：写 map 前先读已有文件合并，只增不覆盖。

### 修复 5（转换器侧，非技能）：md 母本 BOM 导致标题降级为正文
- 现象：草稿正文顶部显示「# 复式记账：一张凭证为什么必须记两笔」而非标题样式。
- 根因：PowerShell `Set-Content -Encoding utf8` 写入 BOM，build_wx.py 的 `startswith("# ")` 匹配失败，标题行落入正文段。
- 解决：build_wx.py 以 `utf-8-sig` 读母本并 `lstrip("\ufeff")`；正文顶部按公众号惯例加封面头图（mmbiz）。

## 3.0.1（2026-09-17）板块六实战检验修复

板块六第 1 篇（0047 复式记账原理）写作与推送全链路实测，发现并修复：

### 修复 1：`<div>` 标签级别三处矛盾统一
- 现象：`write/SKILL.md` 红线节与校验说明节仍写「禁止 `<div>`」，而校验器实测 `<div>` 为 WARN（API 推送路径不清洗、板块五已发布文章在用），且 `theme-fasterp.md` 组件 2 装饰线正是 `<div>`——技能内部三处互相矛盾。
- 本质：规范文本滞后于校验器实现与真实产物。
- 解决：`write/SKILL.md` 两处、`theme-fasterp.md`「与校验的关系」节统一为「`<div>` WARN 级、能用 `<section>` 用 `<section>`」。

### 修复 2：`upload_imgs.py` 的 WX 路径指向不存在的文件
- 现象：批量上传 `FAIL fig6-1-events.png`，而直接调 `scripts/wx_api.py uploadimg` 成功。
- 根因：`upload_imgs.py` 内 `WX = 同目录/wx_api.py`，但 `wx_api.py` 实际在技能根 `scripts/`（`materials/scripts/` 下只有 upload_imgs.py）。
- 解决：WX 改为三级上级目录拼接 `scripts/wx_api.py`；修复后批量上传成功。

## 3.0.0（2026-09-17）全面重构（批判后完善）

依据对技能的批判与 gzh-design-skill 借鉴，完成以下变更：

### 身份与结构
- **frontmatter `name` 由 `wechat-mp-api` 改为 `wechat-article`**，display_name 改为「微信公众号文章（写作·排版·草稿·发布）」——名实相符。
- 主 SKILL.md 收敛为纯入口：身份、路由、凭据、统一 CLI、公共排障、三条安全习惯；批量发布/状态码/四项后台设置等工作流全部归位到 `publish/`（原本分散在主 SKILL）。
- 正文 HTML 约束唯一权威定义收敛到 `write/SKILL.md`，`draft/` 与 `references/gotchas.md` 改为引用（消除三处重复维护）。

### 新增能力（借鉴 gzh-design-skill）
- `write/scripts/validate_wx_html.py` — 确定性合规校验器（API 推送路径版）：禁标签/属性、图片必须 mmbiz 域名、纯 section 片段、禁用词、半角标点；ERROR=0 才可推送。把「推送前检查清单」从模型自觉变为确定性兜底。
  - **实现要点（实测校准）**：样式红线只检查元素 `style` 属性（代码块文本里的 CSS 示例不算违规——FastERP 文章常展示 `.app{display:grid;var(--rail)}` 这类代码）；`<code>` 标签计入代码区（行内代码的半角符号不误报）；`<div>` 实测 API 推送不清洗、显示正常（板块五已发布文章在用），降为 WARN 并注明编辑器粘贴路径会被改写。
  - 双向验证：0035 mmbiz 版（已推送）→ ERROR=0；0042 旧版（本地路径）→ 检出 3 处图片 ERROR。
- `write/references/theme-fasterp.md` — FastERP 系列排版资产（从板块五已发布文章 `push_tmp/*-mmbiz.html` 逐条提取，样式与产物逐字一致）：主色深蓝 #1F3864 + 金 #B08D3E，9 个已验证组件 + 映射规则 + 系列约定。装饰线组件按真实产物为 `<div>`（API 路径实测可用）。
- `write/scripts/wrap_preview.py` — 推送前本地预览页（模拟公众号阅读 + 一键复制）。
- `write/scripts/extract_docx.py` + `write/references/format-normalize.md` — 素材归一化（docx/pdf/纯文本/网页 → Markdown），移植自 gzh-design-skill（零依赖）。
- `read/`、`search/` 增加脆弱性标注（外部路径可能随平台改版失效，使用前即时验证）。
- `git init` + 本 CHANGELOG：技能迭代可追溯。

### 既有能力保留
- `scripts/wx_api.py`（13 子命令）、`scripts/wx_draft_push.py`、`materials/scripts/upload_imgs.py`、`write/scripts/render_mermaid.py`。
- 六子技能路由、凭据安全、发布前四项后台设置、48001 发布权限实测结论。

## 2.1.1（2026-09-17）
- 撤销 `Verify/` 子技能（借鉴来源 web-app-function-test 被用户更正为误引用）；路由表回退为 6 子技能。

## 2.1.0（2026-09-17）
- 纳入 `wx_draft_push.py` 为简易推送脚本；新增 `write/` 子技能（写作纪律 + wx 内联版 HTML 硬规范）。

## 2.0.0（2026-09-17）
- 全面完善：新增 `write/`（首版）、`read/`、`search/` 子技能；publish 状态码全表、48001 实测结论、批量按序发布工作流；gotchas 扩至 13 条；wx_api.py 增加 `--full`/`--source-url`。
## 3.2.0（2026-09-17）板块二实战检验修复

板块二 4 篇（0010/0011/0014/0015）写作推送全链路实测，发现并修复：

### 修复 1：upload_imgs --map 键为绝对路径，build_wx 匹配失败（本轮最大问题）
- 现象：0010 首次 validate 报 3 处图片 ERROR（ssets/fig/xxx.png 本地路径未替换为 mmbiz URL）。
- 本质：两个脚本的键约定不一致——upload_imgs.py 用 os.path.normpath 绝对路径作 map 键（含非 ASCII 时控制台显示乱码），uild_wx.py 匹配逻辑 mmbiz.get(src) or mmbiz.get(os.path.basename(src)) 只认相对路径/basename，绝对路径键永远匹配不上。
- 解决：upload_imgs.py 写 map 时键统一为 os.path.basename(p)（3.2.0 起新产物直接正确）；旧 map 需重建（basename 键）；write/SKILL.md 转换器段标注 map 键约定；
eferences/gotchas.md 新增第 17 条。
- 验证：0010 重建后 ERROR=0；四篇推送后 draft-get 正文 mmbiz 图数 = 配图数（每篇 2 张）。

### 修复 2：draft/materials 子技能 wx_api.py 路径引用失效
- 现象：按 draft/SKILL.md 的 scripts/wx_api.py 执行报「路径不存在」——脚本实际在技能根 scripts/。
- 本质：3.0.0 重构将 wx_api.py 提到根 scripts/，子技能文档路径引用未同步（3.0.1 只修了 upload_imgs.py 内部 WX 拼接，没修文档）。
- 解决：draft/SKILL.md、materials/SKILL.md 内 scripts/wx_api.py 全部改为 ../scripts/wx_api.py。

### 修复 3：validate 禁用词命中「首先」的替代表达沉淀
- 现象：0011 正文「它首先是文档」命中禁用词扫描 ERROR。
- 本质：写作纪律禁用词与表达习惯冲突，需要可用替代表达而非只能改写。
- 解决：
eferences/gotchas.md 新增第 18 条（禁用词替代表达清单，「首先→第一身份/一方面」等实测替换）。

### 补充：板块二 4 篇全链路产物与台账
- 0010/0011/0014/0015 母本 + mermaid 配图（1484px）+ 几何封面（每篇唯一 seed）+ wx 内联版（validate ERROR=0）+ 已推送草稿并回读核验（标题/摘要/封面/正文图/代码块结构齐全）。
- 台账 FastERP_82篇教程台账-最终版.xlsx 板块二 4 行状态与标题已同步。

## 3.2.1（2026-09-18）板块十实战修复：validate class/id 误报代码块文本
### 修复：validate_wx_html.py class/id 属性检查误伤代码块文本
- 现象：0088 正文含 SQL `WHERE id=?`、Python `row["id"]`，validate 报「id 属性会被剥离（命中 1 处）」ERROR。
- 本质：标签级检查的 `\sid\s*=` / `\sclass\s*=` 是全文宽松正则；代码块文本经 build_wx 转义（`<`→`&lt;`、空格→`&nbsp;`）后仍保留 `id=`/`class=` 字样，宽松正则无法区分「真实标签属性」与「代码文本」，而样式级红线（FORBIDDEN_STYLES）已豁免代码块、属性检查未豁免——两条检查的豁免口径不一致。
- 解决：class/id 检查正则限定为「真实标签内」：`<[a-z][^>]*\sclass\s*=` 与 `<[a-z][^>]*\sid\s*=`（代码块内不可能出现 `<标签` 形态，因 `<` 已转义）。
- 验证：0088 重跑 validate ERROR=0；含 `WHERE id=?` 的 0087 复跑同样 ERROR=0（回归通过）。

## 3.3.0（2026-09-18）板块九实战检验修复

板块九三篇（0066 先算账再说话 / 0067 斜杠命令与 SSE / 0069 提示词与安全）写作推送全链路实测。本次重点为技能体检：清理垃圾文件、核对 validate 机制、验证内联收尾。

### 修复 1：根目录 4 个垃圾文件清理（技能维护）
- 现象：技能根目录存在 `--help`（一个 PNG 误存 116.3KB）、`多公司：company_id 贯穿与按公司隔离`（33B 截断文件）、`扩展点与自研 ERP：注册机制与规模边界`（40.5KB）、`系统架构与分层：单向依赖与不可变账本`（39.4KB，后两者为板块十文章副本）。
- 本质：历史误写与板块产物误落技能根，非运行必需。
- 解决：4 个文件全部删除；技能现 21 文件 9 脚本，`py_compile` 全过。

### 修复 2：validate 禁词规则误伤内容性表述（写作层，0069）
- 现象：0069 母本"回答边界在最后，因为它是总闸"命中禁词 `最后，`，validate ERROR=1。
- 本质：规则设计为拦截连接词"最后，"，但内容性表述"在最后，因为"同样触发；属规则的字面匹配边界，非缺陷。
- 解决：改写为"回答边界排在末位"，validate ERROR=0。沉淀：母本中一切"在最后/首先/其次"式内容表述都应避开字面组合。

### 修复 3：板块九收尾内联与清理（流程验证）
- 现象：新板块三篇 wx 产物在 work 区，Tutorial 板块九目录为空。
- 解决：按既有收尾流程——wx HTML 落入板块目录 → `inline_images.py` 全目录内联（本次全 Tutorial 134 图 map=3 dl=0 miss=0，板块九三篇 dataURI 内联无 mmbiz 残留）→ 删除板块 assets。
- 验证：板块九目录仅存 0066/0067/0069 三个自包含 HTML。

### 已推送草稿（三篇均 draft-get 回读核验通过）
- 0066 先算账，再说话：FastERP 的 AI 助手与快照问答
- 0067 不接大模型也能问账：斜杠命令与 SSE 打字机
- 0069 系统提示词的四句话与三条红线：数据不出边界
- 每篇：标题≤64 字节、摘要≤120 字符、封面独立（guard/layers 几何图）、正文 mmbiz 配图×1、无 <pre>、validate ERROR=0。

## 4.0.2（2026-09-19）表格红线与架构文章修复

0088《系统架构与分层设计》发布后实测发现两个问题，修复并沉淀为技能规则：

- **新增 `<table>` 红线（ERROR 级）**：0088 用 `<table>` 排"四层结构职责表"，微信手机端整表不渲染、表格消失——与 `<pre>` 同类，属微信编辑器不支持标签。`write/scripts/validate_wx_html.py` 的 FORBIDDEN_TAGS 增加 `<table>` 检查；`write/SKILL.md` 原「简单表格用 `<table>`」的错误建议改为**禁止 `<table>`、一律用 div + display:table 伪表格**，并新增可直接套用的「表格模板」小节；`display:flex` 降为 WARN 级（微信部分机型异常，多列优先 display:table-cell）；主 SKILL.md 描述与路由表同步更新。
- **0088 内容补齐（写作文档同步确认）**：0088 标题承诺「关注点分离、高内聚低耦合」但正文 0 处展开——修复版补入三段论证：模块化设计与关注点分离（四层职责的软件工程命名）、业务域维度模块化（fasterp/ 五个服务类）、高内聚与低耦合度量（db.py 数据收敛 + 窄接口单向依赖），素材全部取自 AGENTS.md 原文与仓库目录结构。
- **0088 修复版重推**：表格转 div 伪表格 + 补内容后，母本已同步更新；解码内联图重传 mmbiz（0088-img-1/2 → mmbiz_map_0088.json）；新草稿 media_id=yEeJgNlLG2-6CUjvfN_kX9wn_4L0LEazsQ6jDoPrrAjQqb6Em2nl4gce21env2WM，check_draft 全 PASS。已发布旧版不可编辑，需删除旧文重新发布。

## 4.0.3（2026-09-19）产物形态改为 mmbiz 单版本优先

用户质疑「何必两个版本并存」：双版本（base64 存档版 + mmbiz 推送版）源自早期一次「图像全部内联」的历史指令，非写作常态。经确认改为：

- **单版本优先**：正式产物只有一个 mmbiz 推送版（写作时一步到位直接引用 uploadimg URL）；base64 内联版降为「用户明确要求离线归档时才生成」的可选动作，不作双份维护。
- write/SKILL.md「〇、产物形态」一节重写；存量 base64 存档版保留现状，重新推送时才走「解码→uploadimg→替换」一次性转换。

## 4.0.4（2026-09-19）div 伪表格红线化，表格改条目卡片

0088 表格问题两次实测打脸，沉淀为规则：

- **问题链条**：`<table>` 微信端整表不渲染（4.0.2 已加 ERROR 红线）→ 改用 div + `display:table` 伪表格 → 微信预览端仍堆叠成纯文本。结论：`display:table/table-cell` 在微信渲染不可靠，div 伪表格不成立。
- **新规则**：表格一律用「条目卡片」——每条一个 `<section>`（浅灰底 #F7F8FA + 金左边框 #B08D3E + 条目名加粗深蓝 + 说明行灰字），纯块级布局微信 100% 稳定；列多必须保持行列结构的渲染成图片。write/SKILL.md 红线段、表格模板、正文排版、检查清单、主 SKILL.md 路由表全部同步。
- **0088 已修复**：四层职责表替换为 4 张条目卡片，validate ERROR=0，草稿重推（WAF501 自动 delete+add 绕行）。

## 4.0.5（2026-09-19）全面检验：脚本与文档对齐、伪表格确定性兜底

对六个子技能 + 主 SKILL.md + 全部脚本交叉核对，发现问题并修复：

- **版本号不同步**：主 SKILL.md version 停在 4.0.2，CHANGELOG 已到 4.0.4 → 升至 4.0.4（本轮再记 4.0.5）。
- **validate_wx_html.py 与 4.0.4 文档冲突**：`<table>`/`display:grid`/`display:flex` 的报错文案仍推荐"div 伪表格"（已废弃路线）→ 文案全部改为「条目卡片或渲染成图片」。
- **实现缺失**：文档承诺"无 div 伪表格（自动）"但脚本不查 display:table → 新增 `display:table/table-cell/table-row/table-column` ERROR 红线（实测三样本：伪表格 ERROR、table 标签 ERROR、代码块"本文"不误报）。
- **禁用词误报风险**：BANNED_WORDS 原来直接全文子串匹配，代码块注释里的"本文"会误报 ERROR → 改为只查非代码区正文（checker.texts），实测代码块含"本文"通过。
- **check_draft.py 缺伪表格回读**：回读层不查 display:table → 新增「无 div 伪表格」检查项 + summary 字段 + 摘要行显示；0088 实跑 PASS（伪表格×0）。
- 全技能扫描确认无过时表述残留（剩余命中均为禁令记录本身）。
