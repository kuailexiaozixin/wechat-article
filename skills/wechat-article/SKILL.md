---
name: wechat-article
description: '微信公众号文章全链路技能：按写作纪律成文并排成微信兼容的 HTML 正文片段，上传封面与正文图，把文章推进草稿箱并回读核验，也能读取已有文章正文、按关键词搜索公众号文章。用户提出写一篇公众号文章、公众号排版、推送或管理草稿、读取与搜索公众号文章时使用。发布接口族对个人未认证账号无权限，发布走公众号后台手动。'
version: 4.5.0
---

# 微信公众号文章（wechat-article）

本技能封装**微信公众号官方开放接口**（`api.weixin.qq.com/cgi-bin`）+ 公众号写作/排版方法。官方文档：**微信公众平台开发文档**（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 目录与路由

本技能目录 `wechat-article/` 下按能力域拆为 5 个子技能，**按任务自动路由**（下文相对路径均以本技能目录为根）：

| 用户需求 | 子技能 | 该子技能负责的一件事 |
|---|---|---|
| **写**文章、做 wx 内联版排版 | `write/` | 成文与正文 HTML 的产出，以及文字/静态/渲染三道验收 |
| 新建、改、查、删**草稿** | `draft/` | `draft/*` 六个接口、推送前后的核验、发布前手动清单 |
| 上传**封面/正文图** | `materials/` | 换 `mmbiz.qpic.cn` URL 与封面永久素材 |
| **读取**某篇已知链接的文章 | `read/` | 取正文与元信息转 Markdown |
| 按关键词**搜索**文章 | `search/` | 搜狗 `type=2` 检索与跳转还原 |

每行的能力细则、命令、参数与验收判据只在对应子技能正文里写一份；本表不重复展开。

**跨子技能依赖（改名或删文件前先查这三条边）**：`scripts/wx_draft_push.py` 的推送闸口加载
`write/scripts/validate_wx_html.py` 的 `validate()`（复用，不重复实现）；`write/references/theme-default.md`
是 `tests/test_theme_blocks.py` 逐字比对的唯一来源；`tests/` 的 `test_prose_pivots.py`、`test_qa_mobile.py`、
`test_validate_rules.py`、`test_theme_blocks.py` 四支按目录名加载 `write/scripts/` 下的脚本。
`write/` 一改，推送闸与这四支判据同时受影响，不是只影响写作侧——这条边由 `tests/test_evals_routes.py`
的「路径引用大小写核对」守：引用与磁盘目录名逐字符不符即报红。

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

其余脚本一律归属各子技能，用法与判据在子技能正文各写一份，根不重复列（`write/`、`materials/`、`read/`、`search/` 各自的 `scripts/`）。
上面「跨子技能依赖」那一节是另一件事：它按文件名列出会被连带改动的边，只登记依赖、不展开用法。

## 参数/内容硬约束

跨子技能只提一句会被反复踩的口径：**草稿标题取正文标题的短句，完整标题放 HTML 正文里**（标题字节上限与各参数约束表在 `draft/SKILL.md`「参数约束」，接口层取值域在 `references/api-docs.md`）。正文 HTML 的硬规范、代码块结构、产物形态唯一权威见 `write/references/wx-html-rules.md`。

## 发布（个人未认证账号无接口权限，走后台手动发布）

**判据**：用户要求发布时，先 `python scripts/wx_api.py check-perm`（只读探测）。返回 `perm:false` → **不重试**，转公众号后台手动发布；返回 `perm:true`（认证账号）才谈 `freepublish/*` 接口路径。**具体步骤、发布前必设四项清单、固定话术与已发布结果的核对口径都归 `draft/SKILL.md`「制作→预览工作流」第 4 步**，根不重复列。

实测范围与错误码（`48001` 覆盖整个发布接口族，含只读查询；`53010` 同类）唯一一份写在 `references/gotchas.md` A3；草稿接口 `draft/*` 不受影响。

## 公共排障

`references/gotchas.md` 是唯一一份错误码与失效模式清单（按组编号），调试前先读；根不再抄一遍错误码。

## 操作前安全习惯（三条，跨子技能通用）

1. **实查草稿箱**：草稿箱可能被后台/他处外部删改。凡操作具体草稿前，先 `draft-count` + `draft-list` 确认 `media_id` 与标题一一对应，**不凭记忆里的 media_id 直接操作**。
2. **推送前三道闸，推送后一道核验**（顺序固定，跨子技能才需要这条总线；每道闸各自查什么、用什么脚本查、怎么改，归 `write/SKILL.md` 与 `scripts/` 三个入口的用法行）：
   写作硬禁令 → 排版红线静态校验 → 390px 真机渲染 → 推送（`wx_draft_push.py` 内置同一道排版校验，ERROR>0 直接退出、不取 token）→ 回读逐字比对（`check_draft.py --source`）。任一 FAIL 就修复后重推，不带错交付。
3. **发布权限预判**：见上节「发布」判据，不重复重试。

跨子技能的工作流细节一律在子技能正文：推送与回读、发布前手动四项见 `draft/SKILL.md`；写作与排版九步见 `write/SKILL.md`。
