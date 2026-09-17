# WeChat MP API — Gotchas & Checklist

真实推送/发布中遇到过的失败模式与修复，调试前先读。

## 1. IP 白名单 — errcode 40164
**症状：** token 调用返回 `{"errcode":40164,"errmsg":"invalid ip <IP> ... not in whitelist"}`。
**原因：** 公众号开启了「API 调用 IP 白名单」（设置与开发 → 基本配置 → IP白名单），当前出口 IP 不在名单内。
**修复：** 把报错里的 IP 加入白名单后重试。出口 IP 会随会话变化——再失败就再读新 IP 再加。

## 2. GET 代替 POST — errcode 43002
**症状：** 上传封面或提交草稿时返回 `{"errcode":43002,"errmsg":"require POST method"}`。
**原因：** HTTP 客户端带了 body 却强制 GET（urllib 里显式 `method="GET"` + `data`）。
**修复：** 有 body 时不要设置 method，urllib 自动用 POST。

## 3. 标题长度 — 最多 64 字节
`title` ≤ 64 字节（中文 3 字节/字，约 21 个汉字）。文章正文内的大标题可以更长，只有草稿/分享卡的 `title` 参数受限。
**实践：** 草稿标题取正文标题的短句；完整标题放 HTML 正文里。

## 4. 摘要长度 — 最多 120 字符
可选。超过 120 字符报错或截断。

## 5. 凭据处理（安全）
- AppID/AppSecret 只从环境变量读，不硬编码、不写日志。
- 用户粘贴在对话里的密钥：仅本次会话使用，建议重置 AppSecret（旧 secret 立即失效）。

## 6. access_token 有效期
7200 秒（2 小时）。每次调用现取现用，不长期缓存。一次推送只需取一次 token（token → 封面 → 草稿 一次跑完）。

## 7. 封面图
微信大卡封面比例 2.35:1（900×383）；API 接受任意图自动裁剪。封面建议宽构图（如 2048×880），裁剪损失小。
`draft-list` 返回的 `thumb_url` 为 `mmbiz.qpic.cn` 封面链接，可用来核对封面是否上传成功。

## 8. 正文 HTML 约束（关键）
**唯一权威定义在 `Write/SKILL.md`「二、wx 内联版 HTML 硬规范」**。此处只列失败模式：
- **样式必须内联**：微信剥离 `<style>` 块。
- **`<pre>` 代码块会被微信剥离**，空格/换行被折叠，缩进全丢、代码不可读。**必须**用 `<section>` + 逐行 `<p>`（`margin:0;text-indent:0`）+ 空格转 `&nbsp;` + 空行 `<p>&nbsp;</p>`。
- 代码内 `<` `>` `&` 转义为 `&lt;` `&gt;` `&amp;`。
- 正文图片必须用 `mmbiz.qpic.cn` 域名（先 `media/uploadimg` 上传换 URL），否则微信端图片不显示；**本地相对路径（`../assets/xxx.png`）必不显示**。
- 产物应为纯 `<section>` 正文片段（不包 `<!DOCTYPE>`/`<html>` 外壳）。
- **推送前必跑 `Write/scripts/validate_wx_html.py`**（ERROR=0 才推）；推草稿后必须 `draft-get` 抽查：确认正文图 URL、代码块结构、标题/摘要/封面齐全，再交付验收。

## 9. Windows 编码
PowerShell/cmd 下 GBK stdout 会在 emoji/非 ASCII 打印时崩溃。调用前设 `PYTHONIOENCODING=utf-8` 和 `PYTHONUTF8=1`。

## 10. 发布权限 — errcode 48001 / 53010（实测）
**症状（实测）：** `publish`（`freepublish/submit`）返回 `{"errcode":48001,"errmsg":"api unauthorized"}`；**`publish-list`（`freepublish/batchget`）与 `publish-get`（`freepublish/get`）同样返回 48001**（2025-09 实测）——整个发布接口族对无权限账号都不可用，包括只读的列表查询。
**原因：** 发布能力接口需要账号权限；个人主体账号、企业主体未认证账号及不支持认证的账号已被回收（2025-07 起）。`draft/*` 草稿接口不受影响。
**修复：** 判定接口无权限后**不要重试**，引导用户在 公众号后台 → 内容管理 → 草稿箱 手动发布；无权限账号的已发布结果也查不到（`publish-list` 同样 48001），以公众号后台「已发表」页为准。`53010` 为同类发布限制错误。

## 11. 草稿箱可能被外部删改（实测）
**症状：** 按历史记录里的 `media_id` 操作草稿返回 `40007`，或 `draft-count` 数量与记忆不符。
**原因：** 草稿箱可在公众号后台手动删除，或他人/他进程操作。
**修复：** 每次操作前先 `draft-count` + `draft-list` 实查；`media_id` 以本次实查为准。批量发布前必须实查全部目标草稿。

## 12. 发布状态码（publish-get 的 publish_status）
0 成功 · 1 发布中（继续轮询）· 2 原创校验失败 · 3 常规失败 · 4 平台审核不通过 · 5 成功后用户删除 · 6 成功后用户封禁。
发布后取文章正式 URL：`publish-get` 响应 `article_detail[].url`；publish_id 丢失时用 `publish-list --full`（no_content:0）定位。

## 13. 正文图 URL 失效排查
`uploadimg` 返回的 mmbiz URL 官方口径长期有效。若图片不显示：先 `draft-get` 确认 HTML 中确为 mmbiz URL（而非本地 `../assets/` 路径——本地路径微信端必不显示）；确为 mmbiz URL 仍不显示，重新 `uploadimg` 换新 URL 后 `draft-update` 重推。

## 14. 校验脚本（validate_wx_html.py）
- 用法：`python Write/scripts/validate_wx_html.py <article.html>`；退出码 1 = 有 ERROR，0 = 通过（WARNING 人工确认）。
- ERROR 高频来源（实测排序）：图片本地路径/非 mmbiz 域名、`<pre>` 残留、禁用词（「本文」等）、style 属性里的红线样式（position/grid/var/外部字体）。
- 样式红线只查**元素 style 属性**——代码块文本里的 CSS 示例（如 `.app{display:grid;...}`）不算违规。
- `<div>` 为 WARN：API 推送路径实测不清洗（板块五已发布文章在用），编辑器粘贴路径会被改写。
- 历史教训：本地路径 HTML 一旦误推，图片全部不显示，事后替换需重推整篇——所以「一步到位 + 推送前校验」是硬流程，不是建议。
