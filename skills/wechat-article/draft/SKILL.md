---
name: draft
description: '微信公众号草稿箱管理：draft add/update/get/batchget/count/delete 六个接口的调用口径，推送前内置排版校验、推送后回读核验（正文与源文件逐字比对），改标题/正文重推同一篇与腾讯 WAF 501 的 delete+add 绕行都在本技能。当用户要求"推送到公众号草稿箱""改标题重推这篇""看草稿列表""删除草稿""回读核验刚才那篇"时使用。正文怎么写与怎么排版属 write/，图片换 mmbiz URL 属 materials/。'
---

# 草稿箱管理（draft）

通过微信公众号官方「草稿管理」接口管理草稿箱。官方文档：草稿管理和商品卡片（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 能力与命令

统一 CLI：`scripts/wx_api.py`，一次调用完成「取 token → 上传封面 → 提交」。凭据环境变量见 `SKILL.md`。

| 操作 | 命令 | 说明 |
|---|---|---|
| 新增草稿 | `python scripts/wx_api.py draft-add --title "短标题" --digest "摘要" --content ".\article-wx.html" [--cover ".\cover.png"] [--author "名"]` | 返回 `media_id` |
| 更新草稿 | `python scripts/wx_api.py draft-update --media "<media_id>" --title "新标题" --digest "新摘要" --content ".\article-wx.html" [--cover ...]` | 改标题/正文后重推同一篇；不传 `--cover` 时自动回读原封面（避免 40007）；遇 WAF 501 自动 delete+add 绕行并打印 `MEDIA_ID_CHANGED old=… new=…` |
| 单篇详情 | `python scripts/wx_api.py draft-get "<media_id>"` | 获取草稿详情 |
| 回读自动核验 | `python scripts/check_draft.py "<media_id>" --source ".\article-wx.html" [--expect-imgs N] [--json]` | 推送后必跑；断言标题/摘要/封面/图数/代码块结构，`--source` 额外比对正文与源文件是否一致 |
| 草稿列表 | `python scripts/wx_api.py draft-list --offset 0 --count 20` | `no_content:1` |
| 草稿总数 | `python scripts/wx_api.py draft-count` | 返回 total |
| 删除草稿 | `python scripts/wx_api.py draft-delete "<media_id>"` | 返回 `{"errcode":0}` 即成功 |

**简易推送**：仅需"推一篇草稿"时可用 `scripts/wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`（先跑内置 validate 闸，ERROR>0 直接拒推且不取 token；通过后自动 token→封面→草稿，成功输出 `DRAFT_OK media_id:`）。查询/更新/删除走 wx_api.py。

## 参数约束

| 参数 | 约束 |
|---|---|
| `--title` | ≤ **64 字节**（≈21 个汉字，中文 3 字节/字）。草稿标题取正文标题的短句；完整标题放 HTML 正文里 |
| `--digest` | ≤ **120 字符**，可选，超过会报错或截断 |
| `--content` | 本地 HTML 文件路径，**必须内联样式**（微信剥离 `<style>`） |
| `--cover` | 本地图片路径；可选，缺省则草稿无封面。上传见 `materials/` |

## 正文 HTML 约束（微信兼容）

**唯一权威定义见 `write/references/wx-html-rules.md`**（含产物形态、标签与样式红线、代码块与条目卡片模板、mmbiz 图一步到位；流程与闸口顺序见 `write/SKILL.md`）。此处仅列推送侧要点：

- `--content` 必须是**纯 `<section>` 正文片段**（不包文档外壳），样式全部内联。
- 代码块必须用 `<section>` + 逐行 `<p>`（`margin:0;text-indent:0`）+ 空格转 `&nbsp;` + 空行 `<p>&nbsp;</p>`——**禁 `<pre>`**（微信剥离并折叠空格/换行）。
- 代码内 `<` `>` `&` 转义（`&lt;` `&gt;` `&amp;`）。
- 正文图片必须为 `mmbiz.qpic.cn` URL（先 `uploadimg`，见 `materials/`），`draft-add` 只处理 `--cover`。
- 封面宽比 2.35:1（900×383）展示最佳；API 接受任意图并自动裁剪。
- **推送前必跑校验**：`write/scripts/validate_wx_html.py <article.html>`（ERROR=0 才推，`wx_draft_push.py` 内置同一道闸）；渲染层再加 `write/scripts/qa_mobile.py <article.html>`（390px 横向溢出与伪表格）。

## 制作→预览工作流

1. 制作 wx 内联版 HTML（单一交付物，含 mmbiz 正文图）。
2. `draft-add` 推草稿 → 得到 `media_id`，告诉用户去 公众号后台 → 草稿箱 预览。
3. **回读核验（不得省略，自动执行）**：`scripts/check_draft.py <media_id> --source <article.html> [--expect-imgs N]`——自动断言标题 ≤64 字节、摘要 ≤120 字符、封面 thumb 非空、正文无 `<pre>`/`<style>`/`display:table` 伪表格、mmbiz 图数 = 预期（未显式给 N 时按源文件计数得出）、无本地图片路径，并把回读正文与源 HTML 归一化后逐字比对（归一化=统一换行、剥 mmbiz 查询参数、去标签间与连续空白）。**改了源文件没重推，这一步必 FAIL**——API 推送路径微信不清洗正文，不相等即「推的不是这份文件」。输出逐项 `[PASS]/[FAIL]`，FAIL 即修复后 `draft-update`（或 delete+add）重推。
4. 用户验收后要求发布 → 先 `scripts/wx_api.py check-perm` 探测权限（只读）。个人主体/未认证账号实测整个发布接口族无权限（错误码与实测范围见 `references/gotchas.md` A3，**不要重试**）→ 引导用户到 公众号后台 → 内容管理 → 草稿箱 手动发布。**发布前必设四项（API 无对应字段，只能在后台发布流程手动勾选；`draft-add` 成功后必须把这段附在结果里）**：①**开赞赏**——发布页「赞赏」开关（需账号已开通赞赏）；②**声明原创**——编辑器底部「声明原创」，类型选「文字」；③**合集**——发布页「合集」下拉，选目标合集（按账号实际创建的合集名）；④**创作来源「内容由AI生成」**——发布页「创作来源」/「文章设置」选择。

   固定话术：「草稿已推送。发布前请在公众号后台完成四项设置：①开赞赏 ②声明原创（文字）③选择合集 ④创作来源选『内容由AI生成』。API 不支持这些字段，必须手动勾选。」

   认证账号（`check-perm` 返回 `perm:true`）可改用 `freepublish/submit` 等接口发布；本技能默认不封装该路径，需要时按官方文档 Draft_Box/Publish 章节自行扩展。已发布结果以后台「已发表」页或用户提供的文章链接为准。
5. 用户要求删除草稿 → `draft-delete <media_id>`（`{"errcode":0}` 即成功）。

> **`draft-update` 遇腾讯 WAF 501 的处理（`wx_api.py` 已内建，无需手工绕行）**：请求体较大时可能触发 WAF 拦截，退避重试无效，脚本自动「回读原封面 → delete 旧草稿 → add 新草稿」，成功时打印 `MEDIA_ID_CHANGED old=<旧id> new=<新id> 请对新 id 重跑 check_draft.py` 并返回 `{"errcode":0,"bypass":true,...}`。绕行等于换了草稿身份：旧 media_id 立即失效，历史记录要跟着换，且必须对新 id 重跑回读核验。绕行不成功时打印 `ERR BYPASS_FAILED`，此时草稿状态未知，先 `draft-list` 实查再决定重推或删除。

## 已推送草稿的管理

- 草稿箱可能被后台或他处外部删改：**再次操作某篇草稿前**，先 `draft-list` 实查确认其 `media_id` 仍在（不要凭历史记录里的 media_id 直接 update/delete/get）。
- 改标题/正文后重推同一篇：`draft-update --media <media_id> --title ... --digest ... --content <html>`（`index:0` 指单图文第一篇；`--cover` 不传则保留原封面）。
- 多篇场景：`draft-list --count 30` 返回为**倒序**（最新在前），按标题而非返回顺序对应文章编号。

## 排障

- 上传封面失败 → 见 `materials/` 与 `references/gotchas.md`。
- 常见错误码 `40164` / `43002` / `45009` / `40007` → `references/gotchas.md`。
- 正文图在预览时不显示 → 图片未换成 `mmbiz.qpic.cn` URL，按 `materials/` 重新 `uploadimg` 并替换 HTML 后 `draft-update` 重推。
