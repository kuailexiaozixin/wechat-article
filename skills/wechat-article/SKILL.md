---
name: wechat-article
description: '微信公众号文章全链路技能（parent）：封装微信公众平台开放接口与公众号写作/排版方法论，按子技能路由——Write/ 负责研究性专业文章的写作与微信兼容 HTML 排版（A 轨道：立判断 → 定结构 → 备材料 → 成文，进入 B1 前必须把文章整理为符合 wx-HTML 规范的 HTML 文档；B 轨道：B1 配图 → B2 排版核对 → B3 验收 → B4 推送 → B5 回读）、Read/ 读取已有文章正文、Search/ 按关键词搜索公众号文章。写作规范与方法论详见 Write/ 子技能及其 references/ 目录。发布接口族对个人未认证账号无权限，发布走公众号后台手动。用户要写/排版/推送/管理草稿、读取或搜索公众号文章时使用。'
version: 5.16.3
---

# 微信公众号文章（wechat-article）

本技能封装**微信公众号官方开放接口**（`api.weixin.qq.com/cgi-bin`）+ 公众号写作/排版方法。官方文档：**微信公众平台开发文档**（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 目录与路由

本技能目录 `wechat-article/` 下拆为 3 个子技能，**按任务自动路由**（下文相对路径均以本技能目录为根）：

| 用户需求 | 子技能 | 该子技能负责的一件事 |
|---|---|---|
| **写**文章、做 wx 内联版排版、传图、推送草稿箱、回读核验 | `Write/` | A 轨道（立判断 → 定结构 → 备材料 → 成文，出口是把文章整理为符合 wx-HTML 规范的 HTML 文档），再走 B1 配图上传 → B2 排版核对 → B3 验收（三子闸合一）→ B4 推送 → B5 回读 |
| **读取**某篇已知链接的文章 | `Read/` | 取正文与元信息转 Markdown |
| 按关键词**搜索**文章 | `Search/` | 搜狗 `type=2` 检索与跳转还原 |

每行的能力细则、命令、参数与验收判据只在对应子技能正文里写一份；本表不重复展开。

**跨目录依赖（改名或删文件前先查这四条边）**：
1. `scripts/wx_draft_push.py` 的推送闸口加载 `Write/references/b3-acceptance/scripts/validate_wx_html.py`
   的 `validate()`（复用，不重复实现；找不到该文件即报错退出，不静默跳过推送闸）。
2. `Write/references/b2-typeset/theme-default.md`（位于 b2-typeset 目录内）是
   `tests/test_theme_blocks.py` 逐字比对的唯一来源，
   同目录 `build_blocks.py` 的 BLOCKS 键与它一致；样式值不得在别处复写。
3. `tests/` 的 `test_qa_mobile.py`、`test_validate_rules.py`、`test_caption_gate.py` 加载
   `Write/references/b3-acceptance/scripts/` 与 `Write/references/b1-images/scripts/`，
   `test_theme_blocks.py` 加载 `Write/references/b2-typeset/scripts/`。
4. `Write/references/b1-images/scripts/upload_imgs.py` 与 `Write/references/b5-readback/scripts/readback_check.py`
   在运行期逐级上溯定位根 `scripts/wx_api.py` / `scripts/check_draft.py`；根三支脚本是共用接口层，
   搬动会牵动 B1/B4/B5 与 `tests/test_p0_gates.py`，所以留在原位。
5. B 轨五阶段的哈希链：B3 验收包冻结 `html_sha256` → B4 推送核验并写进 push.json →
   B5 回读用它与当前源文件比对（「改了没重推」的判定基准）。改任何一环的哈希口径，
   三处必须同轮改。

`Write/references/` 一改，推送闸与上述判据同时受影响，不是只影响写作侧——路径类断链由
`tests/test_evals_routes.py` 的「路径引用大小写核对」守：引用与磁盘目录名逐字符不符即报红。

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

1. **`scripts/wx_api.py`** — 全能力 CLI。子命令：`token` · `cover` · `uploadimg` · `draft-add` · `draft-update` · `draft-get` · `draft-list` · `draft-count` · `draft-delete` · `check-perm`（完整用法见各阶段说明文档与 `Write/references/b4-push/draft-push-parameters.md`）。
2. **`scripts/wx_draft_push.py`** — 简易单命令推送：`python wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`，自动「校验闸 → token → 封面 → 草稿」，成功输出 `DRAFT_OK media_id:`。仅推送；查询/删除走 wx_api.py。
3. **`scripts/check_draft.py`** — 推送后回读核验：`python check_draft.py <media_id> --source <article.html> [--expect-imgs N] [--json]`，逐项 `[PASS]/[FAIL]`，退出码 0=全过、1=有 FAIL。

三个入口脚本都支持 `-h/--help`：打印用法即退出，不读凭据、不发请求。`wx_api.py` 的未知子命令同样先于 token 请求报错。

其余脚本一律归属各流程目录，用法与判据在对应说明文档各写一份，根不重复列（`Write/references/b1-images/`…`b5-readback/` 各自的 `scripts/`，以及 `Read/scripts/`、`Search/scripts/`）。
上面「跨子技能依赖」那一节是另一件事：它按文件名列出会被连带改动的边，只登记依赖、不展开用法。

## 参数/内容硬约束

跨子技能只提一句会被反复踩的口径：**草稿标题取正文标题的短句，完整标题放 HTML 正文里**（标题字节上限与参数约束表在 `Write/references/b4-push/draft-push-parameters.md`「参数上限」，接口层取值域在 `references/api-docs.md`）。正文 HTML 的红线与产物形态唯一权威见 `Write/references/b3-acceptance/wx-html-redlines.md`，代码块结构与模板见 `Write/references/b2-typeset/wx-html-templates.md`。

## 发布（个人未认证账号无接口权限，走后台手动发布）

**判据**：用户要求发布时，先 `python scripts/wx_api.py check-perm`（只读探测）。返回 `perm:false` → **不重试**，转公众号后台手动发布；返回 `perm:true`（认证账号）才谈 `freepublish/*` 接口路径。**具体步骤、发布前必设四项清单、固定话术与已发布结果的核对口径都归 `Write/references/b4-push/draft-push-parameters.md`「推送与预览工作流」第 4 步**，根不重复列。

实测范围与错误码（`48001` 覆盖整个发布接口族，含只读查询；`53010` 同类）唯一一份写在 `references/gotchas.md` A3；草稿接口 `draft/*` 不受影响。

## 公共排障

`references/gotchas.md` 是唯一一份错误码与失效模式清单（按组编号），调试前先读；根不再抄一遍错误码。

## 操作前安全习惯（三条，跨子技能通用）

1. **实查草稿箱**：草稿箱可能被后台/他处外部删改。凡操作具体草稿前，先 `draft-count` + `draft-list` 确认 `media_id` 与标题一一对应，**不凭记忆里的 media_id 直接操作**。
2. **推送前闸序固定，推送后核验**（跨流程才需要这条总线；每道闸各自查什么、用什么脚本查、怎么改，归 `Write/SKILL.md` 与各阶段目录的说明文档）：
   A 轨出口（文章已整理为符合 wx-HTML 规范的文档，`Write/references/b3-acceptance/scripts/validate_wx_html.py` ERROR=0）→ 排版自检（`Write/references/b2-typeset/scripts/typeset_plan.py`）→ B3 验收包（`Write/references/b3-acceptance/scripts/acceptance_pack.py`，静态红线 + 390px 渲染 + 人工签字 + 图数一致性四子闸合一，冻结 html_sha256）→ B4 推送（验收包必查 + 指纹核对；`wx_draft_push.py` 内置同一道 B3 校验，ERROR>0 直接退出、不取 token）→ B5 回读逐字比对 + 哈希核验（`check_draft.py --source`）。任一 FAIL 就修复后重推，不带错交付。
3. **发布权限预判**：见上节「发布」判据，不重复重试。

跨流程的工作流细节一律在 `Write/`：A1-A3 内容轨道与 B1-B5 交付轨道总表见 `Write/SKILL.md`；推送、发布前手动四项见 `Write/references/b4-push/draft-push-parameters.md`；回读核验见 `Write/references/b5-readback/readback-verification.md`。
