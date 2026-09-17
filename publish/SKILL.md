---
name: publish
description: '微信公众号发布能力（freepublish）：发布草稿、查发布状态（含状态码 0-6 全表）、已发布列表（含文章正式 URL）、删除已发布文章，及发布前必须在公众号后台手动勾选的四项设置清单（开赞赏/声明原创/合集/创作来源 AI 生成）、发布权限限制（个人未认证账号 48001）。当用户要求“发布到公众号”“发布草稿”“看发布状态”“删已发布文章”时使用。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。'
---

# 发布能力（freepublish）

通过微信公众号官方「发布能力」接口管理已发布内容。官方文档：发布能力（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 能力与命令

统一 CLI：`scripts/wx_api.py`。凭据环境变量见 `../SKILL.md`。

| 操作 | 命令 | 说明 |
|---|---|---|
| 发布草稿 | `python wx_api.py publish "<media_id>"` | 返回 `publish_id`（后续查询句柄） |
| 发布状态 | `python wx_api.py publish-get "<publish_id>"` | 见下方状态码表；成功后含正式文章 URL |
| 已发布列表 | `python wx_api.py publish-list --offset 0 --count 20` | 默认 `no_content:1`（不含正文/URL）；**加 `--full` 返回含文章 URL** |
| 删除已发布 | `python wx_api.py publish-delete "<article_id>"` | **不可逆**，删除前先向用户确认 |

## 发布状态码（publish-get 的 publish_status）

| 值 | 含义 | 处理 |
|---|---|---|
| 0 | 成功 | 完成；从响应 `article_detail[].url` 取正式文章链接 |
| 1 | 发布中 | 继续轮询（间隔 5 秒，最多约 60 秒） |
| 2 | 原创校验失败 | 文章疑似未声明原创/原创判定失败，检查后台原创声明设置 |
| 3 | 常规失败 | 查看 `fail_idx`/`errmsg` 定位 |
| 4 | 平台审核不通过 | 内容审核未过，需修改后重新发布 |
| 5 | 成功后用户删除文章 | 文章已被删 |
| 6 | 成功后用户封禁文章 | 文章已被封禁 |

## 发布工作流

1. 用户在 `../draft/` 推草稿并预览验收。
2. 用户要求发布 → `publish <media_id>` → 拿 `publish_id` → `publish-get` 轮询至 `publish_status == 0`。
3. 取文章 URL：`publish-get` 响应 `article_detail[].url`；若 publish_id 丢失，用 `publish-list --full` 定位。
4. 删除已发布 → `publish-delete <article_id>`（`publish-list` 返回的 `article_id`；不可逆，先向用户确认）。

## 发布前必设清单（API 不支持，需后台手动勾选）

以下四项在官方接口中**没有对应字段**（draft/add 与 freepublish/* 均不含），只能由账号运营者在公众号后台发布流程中手动设置。每次 `draft-add` 成功后推送结果必须附上此提醒，不得省略：

1. **开赞赏** — 发布页「赞赏」开关（需账号已开通赞赏功能）。
2. **声明原创** — 编辑器底部「声明原创」，选类型「文字」。
3. **合集选择 FastERP** — 发布页「合集」下拉选择「FastERP」（按账号实际创建的合集名调整）。
4. **创作来源「内容由AI生成」** — 发布页「创作来源」/「文章设置」选择「内容由AI生成」。

固定话术（每次推送后附在结果里）：
「草稿已推送。发布前请在公众号后台完成四项设置：①开赞赏 ②声明原创（文字）③合集选 FastERP ④创作来源选『内容由AI生成』。API 不支持这些字段，必须手动勾选。」

## 发布权限注意（实测）

**实测结论**：个人主体/未认证账号调用发布接口族均返回 `{"errcode":48001,"errmsg":"api unauthorized"}`——**不止 `freepublish/submit`（发布草稿），`freepublish/batchget`（已发布列表）与 `freepublish/get`（发布状态）同样无权限**（2025-09 实测：`publish-list` 返回 48001）。`draft/*` 草稿接口不受影响。`53010` 为同类发布限制错误（部分账号）。

处置：
- 首次调用发布接口族任一个返回 `48001`/`53010` 即判定该账号无发布接口权限，**不要重试**，引导用户到 公众号后台 → 内容管理 → 草稿箱 手动发布（顺序发布时逐篇手动）。
- 无权限账号也无法用 `publish-list` 查询已发布文章——核对发布结果需以公众号后台「已发表」页或用户提供的文章链接为准。
- 若用户确认账号已完成微信认证、权限应可用，可再次尝试。

## 排障

常见错误码 → `../references/gotchas.md`。
