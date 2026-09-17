---
name: wechat-article
description: '微信公众号文章全链路：写作与 wx 内联版 HTML 排版（Write）、素材图片上传（materials）、草稿箱管理（draft）、发布能力（publish）、文章读取（Read）、文章搜索（Search）。覆盖写作纪律（去 AI 味/不虚构）、微信兼容 HTML 硬规范（内联样式/禁 <pre>/代码块 section+逐行 p/mmbiz 正文图/纯 section 片段）、确定性合规校验、access_token、封面与正文图上传、草稿新增/更新/查询/列表/计数/删除、草稿发布（freepublish）、发布状态/列表/删除。当用户要求“写一篇公众号文章”“做公众号排版”“推送到公众号草稿箱”“发公众号文章”“删除草稿”“发布草稿”“看看公众号草稿列表”“读取某篇公众号文章”“搜索公众号文章/公众号”时使用。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。本技能按能力域拆为六个子技能，入口只负责身份、凭据、路由与公共注意。'
version: 3.0.0
display_name: "微信公众号文章（写作·排版·草稿·发布）"
display_name_en: "WeChat Article (Write · Design · Draft · Publish)"
description_zh: "微信公众号文章全链路：写作纪律与 wx 内联版 HTML 排版、素材上传、草稿管理、发布、文章读取与搜索。"
description_en: "Full WeChat article pipeline: writing discipline & wx-compatible inline HTML, materials upload, draft management, publishing, article reading and search."
---

# 微信公众号文章（wechat-article）

本技能封装**微信公众号官方开放接口**（`api.weixin.qq.com/cgi-bin`）+ 公众号写作/排版方法。官方文档：**微信公众平台开发文档**（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 目录与路由

本技能位于 `user_skills/wechat-article/`。按能力域拆为 6 个子技能，**按任务自动路由**：

| 用户需求 | 子技能 | 覆盖能力 |
|---|---|---|
| **写**公众号文章、wx 内联版 HTML 排版 | `Write/` | 写作纪律（去 AI 味/不虚构）+ 微信兼容 HTML 硬规范（禁 `<pre>`、内联样式、mmbiz 图一步到位、纯 section 片段）+ `validate_wx_html.py` 确定性校验 + FastERP 系列排版资产 + 素材归一化 + 本地预览 |
| 制作/推送/查看/删除**草稿** | `draft/` | `draft/*` 全接口 + 参数约束 + 回读核验 |
| **发布**草稿、查发布状态、已发布列表、删已发布 | `publish/` | `freepublish/*` 全接口 + 状态码表 + 发布前必设清单 + 权限说明 + 批量发布 |
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
  - `WECHAT_AUTHOR` — 作者名（可选，默认「数据舞者Ivy Notes」）
- 若用户把密钥粘贴在对话里：仅本次会话使用，并建议用户重置 AppSecret（旧 secret 立即失效）。
- access_token 有效期 7200 秒（2 小时），每次调用现取现用，不长期缓存。

## 统一 CLI

两个脚本，凭据均从环境变量注入：

```powershell
$env:WECHAT_APPID="wx..."; $env:WECHAT_SECRET="..."; $env:WECHAT_AUTHOR="贺新"; $env:PYTHONIOENCODING="utf-8"; $env:PYTHONUTF8="1"
```

1. **`scripts/wx_api.py`** — 全能力 CLI。子命令：`token` · `cover` · `uploadimg` · `draft-add` · `draft-update` · `draft-get` · `draft-list` · `draft-count` · `draft-delete` · `publish` · `publish-get` · `publish-list` · `publish-delete`（完整用法见各子技能）。
2. **`scripts/wx_draft_push.py`** — 简易单命令推送：`python wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`，自动 token→封面→草稿，成功输出 `DRAFT_OK media_id:`。仅推送；查询/发布走 wx_api.py。

辅助脚本（见各子技能）：`materials/scripts/upload_imgs.py`（批量预上传正文图）、`Write/scripts/validate_wx_html.py`（推送前合规校验）、`Write/scripts/render_mermaid.py`（系统 Edge 渲染 mermaid）、`Write/scripts/wrap_preview.py`（本地预览）、`Write/scripts/extract_docx.py`（docx→Markdown）。

## 参数/内容硬约束

- 草稿参数：`--title` ≤ **64 字节**（≈21 个汉字）；`--digest` ≤ **120 字符**；`--content` 为本地 HTML 且必须内联样式。
- 正文 HTML 硬规范、代码块结构、产物形态：见 `Write/SKILL.md`（唯一权威定义）。
- 完整接口参数表：`references/api-docs.md`。

## 公共排障

先读 `references/gotchas.md`。最常见：`40164`（IP 白名单）、`43002`（GET 代替 POST）、`45009`（频率超限）、`40007`（无效 media_id）、`48001`/`53010`（发布接口权限，实测个人未认证账号 48001 覆盖整个发布接口族）。

## 操作前安全习惯（三条，跨子技能通用）

1. **实查草稿箱**：草稿箱可能被后台/他处外部删改。凡操作具体草稿前，先 `draft-count` + `draft-list` 确认 `media_id` 与标题一一对应，**不凭记忆里的 media_id 直接操作**。
2. **推送前校验正文**：`validate_wx_html.py <article.html>` 必须 ERROR=0；推送后 `draft-get <media_id>` 抽查（图片为 mmbiz URL、代码块未被剥离、标题/摘要/封面齐全）。
3. **发布权限预判**：个人主体/未认证账号整个发布接口族返回 `48001`——直接引导后台手动发布，不要反复重试。

详细工作流：推送/回读见 `draft/SKILL.md`；发布/状态码/四项后台设置见 `publish/SKILL.md`。
