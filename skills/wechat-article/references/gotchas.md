# WeChat MP API — Gotchas & Checklist

真实推送/发布中遇到过的失败模式与修复，调试前先读。

## A. 凭据与权限

### A1. IP 白名单 — errcode 40164
**症状：** token 调用返回 `{"errcode":40164,"errmsg":"invalid ip <IP> ... not in whitelist"}`。
**原因：** 公众号开启了「API 调用 IP 白名单」（设置与开发 → 基本配置 → IP白名单），当前出口 IP 不在名单内。
**修复：** 把报错里的 IP 加入白名单后重试。出口 IP 会随会话变化——再失败就再读新 IP 再加。

### A2. 凭据处理（安全）
- AppID/AppSecret 只从环境变量读，不硬编码、不写日志。
- 用户粘贴在对话里的密钥：仅本次会话使用，建议重置 AppSecret（旧 secret 立即失效）。

### A3. 发布权限 — errcode 48001 / 53010
**症状（实测）：** 发布接口族（`freepublish/submit`）返回 `{"errcode":48001,"errmsg":"api unauthorized"}`；**`freepublish/batchget`（已发布列表）与 `publish-get`（`freepublish/get`）同样返回 48001**（2025-09 实测）——整个发布接口族对无权限账号都不可用，包括只读的列表查询。
**原因：** 发布能力接口需要账号权限；个人主体账号、企业主体未认证账号及不支持认证的账号已被回收（2025-07 起）。`draft/*` 草稿接口不受影响。
**修复：** 判定接口无权限后**不要重试**，引导用户在 公众号后台 → 内容管理 → 草稿箱 手动发布；无权限账号的已发布结果也查不到（`publish-list` 同样 48001），以公众号后台「已发表」页为准。`53010` 为同类发布限制错误。

### A4. access_token 有效期
7200 秒（2 小时）。每次调用现取现用，不长期缓存。一次推送只需取一次 token（token → 封面 → 草稿 一次跑完）。

## B. 草稿推送

### B1. GET 代替 POST — errcode 43002
**症状：** 上传封面或提交草稿时返回 `{"errcode":43002,"errmsg":"require POST method"}`。
**原因：** HTTP 客户端带了 body 却强制 GET（urllib 里显式 `method="GET"` + `data`）。
**修复：** 有 body 时不要设置 method，urllib 自动用 POST。

### B2. 标题长度 — 最多 64 字节
`title` ≤ 64 字节（中文 3 字节/字，约 21 个汉字）。文章正文内的大标题可以更长，只有草稿/分享卡的 `title` 参数受限。
**实践：** 草稿标题取正文标题的短句；完整标题放 HTML 正文里。

### B3. 摘要长度 — 最多 120 字符
可选。超过 120 字符报错或截断。

### B4. draft-update 必须携带有效 thumb_media_id
- 现象：`draft-update` 不带 `--cover` 重推 0011 返回 `{"errcode":40007,"errmsg":"invalid media_id"}`，而 `draft-get` 同一 media_id 完全正常；手动携带原封面 thumb 后 `errcode 0`。
- 根因：`draft/update` 接口要求 `articles.thumb_media_id` 为有效素材 id——**省略该键或传空串都判 40007**，报错文案误导为 media_id 无效。`draft/get` 的 media_id 与 `draft/update` 相同，无效的是封面字段而非草稿 id。
- 解决（3.2.1 起）：`wx_api.py` 的 `draft-update` 未传 `--cover` 时自动 `draft-get` 回读原草稿 `thumb_media_id` 再提交，封面保持不变；**`article` 必须在 thumb 回读之后构建**（先构建后回读，article 里仍是空封面，照样 40007）。
- 验证：0011 修正后经脚本重推 `errcode 0`，draft-get 回读标题/摘要/封面/正文图/代码块全部合格。

### B5. draft-update 被腾讯 WAF 501 拦截 — 绕行 delete+add
- 现象：0055 最终版 `draft-update` 连续三次返回 `{"errcode":501,"errmsg":"non-JSON response"}`，raw 为腾讯 WAF 拦截页（`waf.tencent.com/501page.html`）；退避 20s/60s 重试均无效。
- 对照：同一账号、同一批操作中 `draft-get`（同一 media_id）正常、`draft-add` 正常、`draft-delete` 正常、另一篇 0057 的 `draft-update` 成功——被拦的只有这一条 `draft/update` 请求（写操作、请求体约 47KB）。
- 根因：腾讯网关对特定草稿的 `draft/update` 做风控拦截，返回 HTML 而非 JSON；`http_json` 已把非 JSON 包装为 `{"errcode":code,"errmsg":"non-JSON response","raw":...}` 便于诊断（3.0.2 起）。此类拦截与重试次数无关，退避无效。
- 解决（3.2.2 起）：`draft-update` 连续 501 时**不要继续重试**，改走 `draft-delete <media_id>` + `draft-add`（同标题/摘要/封面/正文）生成新草稿。delete 与 add 实测不受 WAF 拦截，新 media_id 内容完全一致。
- 验证：0055 删除旧草稿后重新 add，`media_id` 更新，draft-get 核验标题/摘要/封面/正文 mmbiz 图×2/代码块结构与最终 wx 内联版一致。

### B6. 草稿箱可能被外部删改
**症状：** 按历史记录里的 `media_id` 操作草稿返回 `40007`，或 `draft-count` 数量与记忆不符。
**原因：** 草稿箱可在公众号后台手动删除，或他人/他进程操作。
**修复：** 每次操作前先 `draft-count` + `draft-list` 实查；`media_id` 以本次实查为准。批量发布前必须实查全部目标草稿。

## C. 正文与图片

### C1. 正文 HTML 约束（关键）
**唯一权威定义在 `write/SKILL.md`「二、wx 内联版 HTML 硬规范」**。此处只列失败模式：
- **样式必须内联**：微信剥离 `<style>` 块。
- **`<pre>` 代码块会被微信剥离**，空格/换行被折叠，缩进全丢、代码不可读。**必须**用 `<section>` + 逐行 `<p>`（`margin:0;text-indent:0`）+ 空格转 `&nbsp;` + 空行 `<p>&nbsp;</p>`。
- 代码内 `<` `>` `&` 转义为 `&lt;` `&gt;` `&amp;`。
- 正文图片必须用 `mmbiz.qpic.cn` 域名（先 `media/uploadimg` 上传换 URL），否则微信端图片不显示；**本地相对路径（`../assets/xxx.png`）必不显示**。
- 产物应为纯 `<section>` 正文片段（不包 `<!DOCTYPE>`/`<html>` 外壳）。
- **推送前必跑 `write/scripts/validate_wx_html.py`**（ERROR=0 才推）；推草稿后必须 `draft-get` 抽查：确认正文图 URL、代码块结构、标题/摘要/封面齐全，再交付验收。

### C2. 正文图 URL 失效排查
`uploadimg` 返回的 mmbiz URL 官方口径长期有效。若图片不显示：先 `draft-get` 确认 HTML 中确为 mmbiz URL（而非本地 `../assets/` 路径——本地路径微信端必不显示）；确为 mmbiz URL 仍不显示，重新 `uploadimg` 换新 URL 后 `draft-update` 重推。

### C3. mmbiz-map 键约定：必须 basename
- 现象：0010 首次校验报 3 处图片 ERROR（本地路径未替换），草稿正文图不显示。
- 根因：upload_imgs.py --map 旧版用**绝对路径**作 map 键（含非 ASCII 时控制台显示乱码），而写作排版按图片 basename 查 URL——src 是素材里的相对路径（assets/fig/xxx.png），与绝对路径键永远匹配不上。
- 解决（3.2.0 起）：upload_imgs.py 写 map 时键统一为 os.path.basename(p)，写作排版按 basename 命中即换 URL。旧版本生成的 map 文件（绝对路径键）需重建：{os.path.basename(k): v for k, v in raw.items()}。
- 验证：板块二 0010/0011/0014/0015 全部按 basename 键重建后校验 ERROR=0，推送后 draft-get 正文 mmbiz 图数 = 配图数。

## D. 校验与写作

### D1. 校验脚本（validate_wx_html.py）
- 用法：`python write/scripts/validate_wx_html.py <article.html>`；退出码 1 = 有 ERROR，0 = 通过（WARNING 人工确认）。
- ERROR 高频来源（实测排序）：图片本地路径/非 mmbiz 域名、`<pre>` 残留、禁用词（「本文」等）、style 属性里的红线样式（position/grid/var/外部字体）。
- 样式红线只查**元素 style 属性**——代码块文本里的 CSS 示例（如 `.app{display:grid;...}`）不算违规。
- `<div>` 为 WARN：API 推送路径实测不清洗（板块五已发布文章在用），编辑器粘贴路径会被改写。**新产物一律用 `<section>`**——装饰线用 `<section>` 实现，校验 WARN 清零。
- 历史教训：本地路径 HTML 一旦误推，图片全部不显示，事后替换需重推整篇——所以「一步到位 + 推送前校验」是硬流程，不是建议。

### D2. 写作禁用词替代表达（validate 命中 ERROR）
正文写作时避开「本文 / 读者 / 首先 / 其次 / 最后 / 总而言之 / 综上所述 / 需要注意的是 / 让我们」等；命中即 ERROR，需改稿重跑校验。实测替代表达：
- 「它首先是文档」→「它第一身份是文档」（0011 实测）
- 「首先，X；其次，Y」→「X 是一层；Y 是另一层」或「一方面…另一方面…」

### D3. AI 味启发式检查（validate 3.4.0 起，WARNING 级）
`validate_wx_html.py` 新增 WARNING 检查：空洞修辞短语（功能强大/赋能/闭环/事半功倍/一目了然等 22 个）、正文感叹号 >3、最长段落 >120 字、段落平均 >80 字、「其一其二其三」「一是二是三是」编号排比。命中不阻断推送（退出码仍只看 ERROR），但逐项人工确认——空洞修辞与长段是 AI 味最高发点。

## E. 环境与编码

### E1. Windows 编码
PowerShell/cmd 下 GBK stdout 会在 emoji/非 ASCII 打印时崩溃。调用前设 `PYTHONIOENCODING=utf-8` 和 `PYTHONUTF8=1`。

### E2. draft-get 输出编码（PowerShell 调用侧）
`wx_api.py draft-get` 输出 JSON 到 stdout；PowerShell `Out-File -Encoding utf8` 会写 BOM，`json.load` 报 `Unexpected UTF-8 BOM`。改用 `python -c "json.load(open(f, encoding='utf-8-sig'))"` 或 `| Set-Content -Encoding utf8NoBOM`。

## F. 发布状态

## G. 封面

### G1. 封面图
微信大卡封面比例 2.35:1（900×383）；API 接受任意图自动裁剪。封面建议宽构图（如 2048×880），裁剪损失小。
`draft-list` 返回的 `thumb_url` 为 `mmbiz.qpic.cn` 封面链接，可用来核对封面是否上传成功。

