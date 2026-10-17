---
name: wechat-article
description: '微信公众号文章全链路技能：写文章并排成微信兼容的 HTML、上传封面与正文图、把文章推进草稿箱并回读核验、管理草稿（增删改查）、读取已有公众号文章正文、按关键词搜索公众号文章。当用户要求"写一篇公众号文章""做公众号排版""推送到公众号草稿箱""改标题重推这篇""删除草稿""看草稿列表""读取某篇公众号文章""搜索公众号文章"时使用。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。能力细则见正文与五个子技能。'
version: 4.3.0
display_name: "微信公众号文章（写作·排版·草稿）"
display_name_en: "WeChat Article (Write · Design · Draft)"
description_zh: "微信公众号文章全链路：写作纪律与 wx 内联版 HTML 排版、素材上传、草稿管理、文章读取与搜索；发布走公众号后台手动操作（发布接口族对个人未认证账号无权限）。"
description_en: "Full WeChat article pipeline: writing discipline & wx-compatible inline HTML, materials upload, draft management, article reading and search. Publishing is done manually in the MP backend (freepublish APIs are unauthorized for unverified personal accounts)."
---

# 微信公众号文章（wechat-article）

本技能封装**微信公众号官方开放接口**（`api.weixin.qq.com/cgi-bin`）+ 公众号写作/排版方法。官方文档：**微信公众平台开发文档**（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 目录与路由

本技能目录 `wechat-article/` 下按能力域拆为 5 个子技能，**按任务自动路由**（下文相对路径均以本技能目录为根）：

| 用户需求 | 子技能 | 覆盖能力 |
|---|---|---|
| **写**公众号文章、wx 内联版 HTML 排版 | `write/` | 写作纪律（去 AI 味/不虚构）+ 微信兼容 HTML 硬规范（内联样式、禁 `<pre>`/`<table>`/div 伪表格、表格改用条目卡片、mmbiz 正文图、纯 section 片段）+ 三道闸：`check_prose.py` 散文硬禁令、`validate_wx_html.py` 排版红线、`qa_mobile.py` 390px 真机渲染 |
| 制作/推送/查看/删除**草稿** | `draft/` | `draft/*` 全接口 + 参数约束 + `check_draft.py --source` 回读核验 + 发布前后台手动设置清单 |
| 上传**封面/正文图**（换 mmbiz URL） | `materials/` | 封面永久素材 + `uploadimg`（1MB 预检）+ 批量预上传 + 封面几何图生成 |
| 读取/提取/解析某篇公众号文章正文 | `read/` | 四层渐进式提取 + 非空正文质量门 + 验证墙 CDP 兜底 |
| 搜索/定位公众号文章或某个公众号 | `search/` | 搜狗 type=2 关键词搜文章 + 跳转链接三形态还原 + 反爬停手判据 |

- 接口与官方文档章节映射、请求体与 article 字段、官方限额：`references/api-docs.md`。
- 真实失败模式与修复：`references/gotchas.md`（调试前先读）。
- 变更记录：`CHANGELOG.md`。
- 路由评测用例（话术 → 子技能与命令）：`evals/evals.json`，由 `tests/test_evals_routes.py` 核对引用与选项。
- 判据测试：`tests/`（`python tests/run_all.py` 一次跑完，全部可证伪——变异即报红）。

## 凭据（安全）

- 从环境变量读取，**禁止**硬编码、写文件、打印、进日志：
  - `WECHAT_APPID` — 公众号 AppID
  - `WECHAT_SECRET` — 公众号 AppSecret
  - `WECHAT_AUTHOR` — 作者名（可选，缺省省略 author 字段；部分账号作者字段长度很小，超限报 45110）
- 若用户把密钥粘贴在对话里：仅本次会话使用，并建议用户重置 AppSecret（旧 secret 立即失效）。
- access_token 有效期 7200 秒（2 小时），每次调用现取现用，不长期缓存。

## 统一 CLI

入口脚本三个，凭据均从环境变量注入：

```powershell
$env:WECHAT_APPID="wx..."; $env:WECHAT_SECRET="..."; $env:WECHAT_AUTHOR="<你的作者名>"; $env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
```

1. **`scripts/wx_api.py`** — 全能力 CLI。子命令：`token` · `cover` · `uploadimg` · `draft-add` · `draft-update` · `draft-get` · `draft-list` · `draft-count` · `draft-delete` · `check-perm`（完整用法见各子技能）。
2. **`scripts/wx_draft_push.py`** — 简易单命令推送：`python wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`，自动「校验闸 → token → 封面 → 草稿」，成功输出 `DRAFT_OK media_id:`。仅推送；查询/删除走 wx_api.py。
3. **`scripts/check_draft.py`** — 推送后回读核验：`python check_draft.py <media_id> --source <article.html> [--expect-imgs N] [--json]`，逐项 `[PASS]/[FAIL]`，退出码 0=全过、1=有 FAIL。

三个入口脚本都支持 `-h/--help`：打印用法即退出，不读凭据、不发请求。`wx_api.py` 的未知子命令同样先于 token 请求报错。

辅助脚本（见各子技能）：`materials/scripts/upload_imgs.py`（批量预上传正文图，一次 token 复用 + 45009 退避 + 上传前 1MB 逐张预检）、`materials/scripts/gen_cover.py`（公众号封面生成器，纯几何无文字）、`write/scripts/build_blocks.py`（按组件 JSON 产出与 `write/references/theme-default.md` 逐字一致的 HTML）、`write/scripts/validate_wx_html.py`（推送前排版红线校验 + AI 味启发式 WARNING）、`write/scripts/qa_mobile.py`（390px 真机渲染：横向溢出、计算样式伪表格/grid/flex、破图、截图）、`write/scripts/check_prose.py`（成稿散文硬禁令检测：翻案句/黑话/硬停词，判定源见 `write/references/human-writing-nonfiction.md`，改写手法与词表维护见 `write/references/de-ai-measures.md`）、`write/scripts/check_duplicates.py`（跨篇重复段落检测）、`write/scripts/render_mermaid.py`（mermaid 渲染，msedge→chrome→默认 Chromium fallback 链）、`write/scripts/wrap_preview.py`（本地预览，产物不作推送）、`read/scripts/read_wechat.py`（四层渐进式取正文）、`search/scripts/search_wechat.py`（搜狗搜文章 + 跳转还原）、`scripts/check_draft.py`（草稿回读自动核验，推送后必跑）。

## 参数/内容硬约束

- 草稿参数：`--title` ≤ **64 字节**（≈21 个汉字）；`--digest` ≤ **120 字符**；`--content` 为本地 HTML 且必须内联样式。
- 正文 HTML 硬规范、代码块结构、产物形态：`write/references/wx-html-rules.md`（样式单一来源 `write/references/theme-default.md`；流程与闸口顺序 `write/SKILL.md`）。
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
2. **推送前三道闸，推送后一道核验**（顺序固定，互不重复覆盖）：
   `check_prose.py <正文或源文件>`（散文硬禁令）→ `validate_wx_html.py <article.html>`（排版红线，ERROR 必须为 0；WARNING 逐项确认，含 AI 味启发式）→ `qa_mobile.py <article.html>`（390px 渲染，FAIL 即改结构）→ 推送（`wx_draft_push.py` 会再跑一次 validate，ERROR>0 直接退出、不取 token）→ `check_draft.py <media_id> --source <article.html>`（回读断言标题/摘要/封面/图数/代码块结构，并比对正文与源文件归一化后是否一致——改过源文件却没重推，这一步必须 FAIL）。FAIL 即修复重推，不带错交付。
3. **发布权限预判**：先 `check-perm` 探测——个人主体/未认证账号整个发布接口族返回 `48001`，直接引导后台手动发布，不要反复重试。

详细工作流：推送/回读见 `draft/SKILL.md`；发布前后台手动设置清单见上节与 `draft/SKILL.md`。
