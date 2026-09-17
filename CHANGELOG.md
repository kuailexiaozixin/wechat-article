# CHANGELOG — wechat-article

本技能变更记录（与 git 提交一一对应）。

> **许可合规说明（AGPL-3.0）**：`Write/scripts/extract_docx.py` 逐字移植自
> gzh-design-skill（AGPL-3.0，作者 甲木 × 摸鱼小李）；`validate_wx_html.py`、
> `wrap_preview.py`、`format-normalize.md` 借鉴其方法体系。上述文件均已标注
> 来源与许可。本技能如对外分发，涉及这些文件的部分须遵循 AGPL-3.0 开源。
> 源技能 gzh-design-skill 已于 2026-09-17 移入
> `fasterp_ledger_backup\gzh-design-skill\`（保留备查）。

## 3.0.1（2026-09-17）板块六实战检验修复

板块六第 1 篇（0047 复式记账原理）写作与推送全链路实测，发现并修复：

### 修复 1：`<div>` 标签级别三处矛盾统一
- 现象：`Write/SKILL.md` 红线节与校验说明节仍写「禁止 `<div>`」，而校验器实测 `<div>` 为 WARN（API 推送路径不清洗、板块五已发布文章在用），且 `theme-fasterp.md` 组件 2 装饰线正是 `<div>`——技能内部三处互相矛盾。
- 本质：规范文本滞后于校验器实现与真实产物。
- 解决：`Write/SKILL.md` 两处、`theme-fasterp.md`「与校验的关系」节统一为「`<div>` WARN 级、能用 `<section>` 用 `<section>`」。

### 修复 2：`upload_imgs.py` 的 WX 路径指向不存在的文件
- 现象：批量上传 `FAIL fig6-1-events.png`，而直接调 `scripts/wx_api.py uploadimg` 成功。
- 根因：`upload_imgs.py` 内 `WX = 同目录/wx_api.py`，但 `wx_api.py` 实际在技能根 `scripts/`（`materials/scripts/` 下只有 upload_imgs.py）。
- 解决：WX 改为三级上级目录拼接 `scripts/wx_api.py`；修复后批量上传成功。

## 3.0.0（2026-09-17）全面重构（批判后完善）

依据对技能的批判与 gzh-design-skill 借鉴，完成以下变更：

### 身份与结构
- **frontmatter `name` 由 `wechat-mp-api` 改为 `wechat-article`**，display_name 改为「微信公众号文章（写作·排版·草稿·发布）」——名实相符。
- 主 SKILL.md 收敛为纯入口：身份、路由、凭据、统一 CLI、公共排障、三条安全习惯；批量发布/状态码/四项后台设置等工作流全部归位到 `publish/`（原本分散在主 SKILL）。
- 正文 HTML 约束唯一权威定义收敛到 `Write/SKILL.md`，`draft/` 与 `references/gotchas.md` 改为引用（消除三处重复维护）。

### 新增能力（借鉴 gzh-design-skill）
- `Write/scripts/validate_wx_html.py` — 确定性合规校验器（API 推送路径版）：禁标签/属性、图片必须 mmbiz 域名、纯 section 片段、禁用词、半角标点；ERROR=0 才可推送。把「推送前检查清单」从模型自觉变为确定性兜底。
  - **实现要点（实测校准）**：样式红线只检查元素 `style` 属性（代码块文本里的 CSS 示例不算违规——FastERP 文章常展示 `.app{display:grid;var(--rail)}` 这类代码）；`<code>` 标签计入代码区（行内代码的半角符号不误报）；`<div>` 实测 API 推送不清洗、显示正常（板块五已发布文章在用），降为 WARN 并注明编辑器粘贴路径会被改写。
  - 双向验证：0035 mmbiz 版（已推送）→ ERROR=0；0042 旧版（本地路径）→ 检出 3 处图片 ERROR。
- `Write/references/theme-fasterp.md` — FastERP 系列排版资产（从板块五已发布文章 `push_tmp/*-mmbiz.html` 逐条提取，样式与产物逐字一致）：主色深蓝 #1F3864 + 金 #B08D3E，9 个已验证组件 + 映射规则 + 系列约定。装饰线组件按真实产物为 `<div>`（API 路径实测可用）。
- `Write/scripts/wrap_preview.py` — 推送前本地预览页（模拟公众号阅读 + 一键复制）。
- `Write/scripts/extract_docx.py` + `Write/references/format-normalize.md` — 素材归一化（docx/pdf/纯文本/网页 → Markdown），移植自 gzh-design-skill（零依赖）。
- `Read/`、`Search/` 增加脆弱性标注（外部路径可能随平台改版失效，使用前即时验证）。
- `git init` + 本 CHANGELOG：技能迭代可追溯。

### 既有能力保留
- `scripts/wx_api.py`（13 子命令）、`scripts/wx_draft_push.py`、`materials/scripts/upload_imgs.py`、`Write/scripts/render_mermaid.py`。
- 六子技能路由、凭据安全、发布前四项后台设置、48001 发布权限实测结论。

## 2.1.1（2026-09-17）
- 撤销 `Verify/` 子技能（借鉴来源 web-app-function-test 被用户更正为误引用）；路由表回退为 6 子技能。

## 2.1.0（2026-09-17）
- 纳入 `wx_draft_push.py` 为简易推送脚本；新增 `Write/` 子技能（写作纪律 + wx 内联版 HTML 硬规范）。

## 2.0.0（2026-09-17）
- 全面完善：新增 `Write/`（首版）、`Read/`、`Search/` 子技能；publish 状态码全表、48001 实测结论、批量按序发布工作流；gotchas 扩至 13 条；wx_api.py 增加 `--full`/`--source-url`。
