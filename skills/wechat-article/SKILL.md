---
name: wechat-article
description: '微信公众号文章全链路：写作与 wx 内联版 HTML 排版（Write）、素材图片上传（materials）、草稿箱管理（draft）、文章读取（Read）、文章搜索（Search）。覆盖写作纪律（去 AI 味/不虚构）、微信兼容 HTML 硬规范（内联样式/禁 <pre> 与 <table>/代码块 section+逐行 p/表格 div 伪表格/mmbiz 正文图/纯 section 片段）、确定性合规校验（含 AI 味启发式 WARNING）、草稿回读自动核验（check_draft.py）、access_token、封面生成与上传、正文图批量上传（token 复用+频率退避）、草稿新增/更新/查询/列表/计数/删除（draft-update 遇 WAF 501 自动 delete+add 绕行）、发布接口权限探测（check-perm）与后台手动发布指引、跨篇重复段落检测。当用户要求“写一篇公众号文章”“做公众号排版”“推送到公众号草稿箱”“发公众号文章”“删除草稿”“看看公众号草稿列表”“读取某篇公众号文章”“搜索公众号文章/公众号”时使用。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。本技能按能力域拆为五个子技能，入口只负责身份、凭据、路由与公共注意。'
version: 4.1.0
display_name: "微信公众号文章（写作·排版·草稿）"
display_name_en: "WeChat Article (Write · Design · Draft)"
description_zh: "微信公众号文章全链路：写作纪律与 wx 内联版 HTML 排版、素材上传、草稿管理、文章读取与搜索；发布走公众号后台手动操作（发布接口族对个人未认证账号无权限）。"
description_en: "Full WeChat article pipeline: writing discipline & wx-compatible inline HTML, materials upload, draft management, article reading and search. Publishing is done manually in the MP backend (freepublish APIs are unauthorized for unverified personal accounts)."
---

# 微信公众号文章（wechat-article）

本技能封装**微信公众号官方开放接口**（`api.weixin.qq.com/cgi-bin`）+ 公众号写作/排版方法。官方文档：**微信公众平台开发文档**（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 目录与路由

本技能位于 `user_skills/wechat-article/`。按能力域拆为 5 个子技能，**按任务自动路由**：

| 用户需求 | 子技能 | 覆盖能力 |
|---|---|---|
| **写**公众号文章、wx 内联版 HTML 排版 | `Write/` | 写作纪律（去 AI 味/不虚构）+ 微信兼容 HTML 硬规范（禁 `<pre>`/`<table>`/div 伪表格、表格用条目卡片、内联样式、mmbiz 图一步到位、纯 section 片段）+ `validate_wx_html.py` 确定性校验 + 通用排版主题资产 + 本地预览 |
| 制作/推送/查看/删除**草稿** | `draft/` | `draft/*` 全接口 + 参数约束 + 回读核验 + 发布前后台手动设置清单 |
| 上传**封面/正文图**（换 mmbiz URL） | `materials/` | 封面永久素材 + `uploadimg` + 批量预上传 |
| 读取/提取/解析某篇公众号文章正文 | `Read/` | 四层渐进式提取 + HTML 解析 + 验证墙处理 |
| 搜索/定位公众号文章或某个公众号 | `Search/` | 搜狗 type=1/2 搜索 + 302 跳转还原 |

- 接口与官方文档章节映射、请求体与 article 字段、官方限额：`references/api-docs.md`。
- 真实失败模式与修复：`references/gotchas.md`（调试前先读）。
- 变更记录：`CHANGELOG.md`。

## 凭据（安全）

- 从环境变量读取，**禁止**硬编码、写文件、打印、进日志：
  - `WECHAT_APPID` — 公众号 AppID
  - `WECHAT_SECRET` — 公众号 AppSecret
  - `WECHAT_AUTHOR` — 作者名（可选，缺省省略 author 字段；部分账号作者字段长度很小，超限报 45110）
- 若用户把密钥粘贴在对话里：仅本次会话使用，并建议用户重置 AppSecret（旧 secret 立即失效）。
- access_token 有效期 7200 秒（2 小时），每次调用现取现用，不长期缓存。

## 统一 CLI

两个脚本，凭据均从环境变量注入：

```powershell
$env:WECHAT_APPID="wx..."; $env:WECHAT_SECRET="..."; $env:WECHAT_AUTHOR="<你的作者名>"; $env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
```

1. **`scripts/wx_api.py`** — 全能力 CLI。子命令：`token` · `cover` · `uploadimg` · `draft-add` · `draft-update` · `draft-get` · `draft-list` · `draft-count` · `draft-delete` · `check-perm`（完整用法见各子技能）。
2. **`scripts/wx_draft_push.py`** — 简易单命令推送：`python wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`，自动 token→封面→草稿，成功输出 `DRAFT_OK media_id:`。仅推送；查询/删除走 wx_api.py。

辅助脚本（见各子技能）：`materials/scripts/upload_imgs.py`（批量预上传正文图，一次 token 复用 + 45009 退避）、`materials/scripts/gen_cover.py`（公众号封面生成器，纯几何无文字）、`Write/scripts/validate_wx_html.py`（推送前合规校验 + AI 味启发式 WARNING）、`Write/scripts/check_duplicates.py`（跨篇重复段落检测）、`Write/scripts/check_prose.py`（成稿散文硬禁令检测：翻案句/黑话/硬停词，判定源见 `Write/references/human-writing-nonfiction.md`）、`Write/scripts/render_mermaid.py`（mermaid 渲染，msedge→chrome→默认 Chromium fallback 链）、`Write/scripts/wrap_preview.py`（本地预览）、`scripts/check_draft.py`（草稿回读自动核验，推送后必跑）。

## 参数/内容硬约束

- 草稿参数：`--title` ≤ **64 字节**（≈21 个汉字）；`--digest` ≤ **120 字符**；`--content` 为本地 HTML 且必须内联样式。
- 正文 HTML 硬规范、代码块结构、产物形态：见 `Write/SKILL.md`（唯一权威定义）。
- 完整接口参数表：`references/api-docs.md`。

## 发布（个人未认证账号实测：接口族无权限，走后台手动发布）

**实测结论（2025-09）**：个人主体/未认证账号调用发布接口族（`freepublish/submit|get|batchget|delete`）均返回 `{"errcode":48001,"errmsg":"api unauthorized"}`；`53010` 为同类限制错误。`draft/*` 草稿接口不受影响。

流程：

1. 推草稿并回读核验（见 `draft/SKILL.md`）。
2. 用户要求发布 → 先 `python scripts/wx_api.py check-perm` 探测（只读）：
   - 返回 `perm:false`（48001/53010）→ **不要重试**，引导用户到 公众号后台 → 内容管理 → 草稿箱 手动发布；已发布结果以后台「已发表」页或用户提供的文章链接为准。
   - 返回 `perm:true`（认证账号）→ 可用 `freepublish/submit` 等接口发布（本技能默认不封装该路径；如需可按官方文档 Draft_Box/Publish 章节自行扩展）。
3. **发布前必设清单（API 无对应字段，只能在后台发布流程手动设置；`draft-add` 成功后必须附此提醒）**：
   1. **开赞赏** — 发布页「赞赏」开关（需账号已开通赞赏功能）。
   2. **声明原创** — 编辑器底部「声明原创」，选类型「文字」。
   3. **合集** — 发布页「合集」下拉选择目标合集（按账号实际创建的合集名）。
   4. **创作来源「内容由AI生成」** — 发布页「创作来源」/「文章设置」选择。

固定话术（每次推送后附在结果里）：
「草稿已推送。发布前请在公众号后台完成四项设置：①开赞赏 ②声明原创（文字）③选择合集 ④创作来源选『内容由AI生成』。API 不支持这些字段，必须手动勾选。」

## 公共排障

先读 `references/gotchas.md`。最常见：`40164`（IP 白名单）、`43002`（GET 代替 POST）、`45009`（频率超限）、`40007`（无效 media_id）、`48001`/`53010`（发布接口权限，实测个人未认证账号 48001 覆盖整个发布接口族，见上节）。

## 操作前安全习惯（三条，跨子技能通用）

1. **实查草稿箱**：草稿箱可能被后台/他处外部删改。凡操作具体草稿前，先 `draft-count` + `draft-list` 确认 `media_id` 与标题一一对应，**不凭记忆里的 media_id 直接操作**。
2. **推送前校验正文**：`validate_wx_html.py <article.html>` 必须 ERROR=0（WARNING 逐项确认，含 AI 味启发式）；推送后**必跑 `check_draft.py <media_id> [--expect-imgs N]`** 自动核验标题/摘要/封面/图数/代码块结构，FAIL 即修复重推。
3. **发布权限预判**：先 `check-perm` 探测——个人主体/未认证账号整个发布接口族返回 `48001`，直接引导后台手动发布，不要反复重试。

详细工作流：推送/回读见 `draft/SKILL.md`；发布前后台手动设置清单见上节与 `draft/SKILL.md`。
