---
name: draft
description: '微信公众号草稿箱管理：新增/更新/获取/列表/计数/删除草稿（draft add/update/get/batchget/count/delete），及公众号正文 HTML 的微信兼容制作规范（内联样式、代码块用 section+逐行<p>、正文图换 mmbiz URL、封面 2.35:1）。当用户要求“推送到公众号草稿箱”“新建/更新/删除/查看草稿”“做一篇公众号文章”时使用。凭据从 WECHAT_APPID / WECHAT_SECRET 环境变量读取。'
---

# 草稿箱管理（draft）

通过微信公众号官方「草稿管理」接口管理草稿箱。官方文档：草稿管理和商品卡片（`https://developers.weixin.qq.com/doc/offiaccount/`）。

## 能力与命令

统一 CLI：`../scripts/wx_api.py`，一次调用完成「取 token → 上传封面 → 提交」。凭据环境变量见 `../SKILL.md`。

| 操作 | 命令 | 说明 |
|---|---|---|
| 新增草稿 | `python ../scripts/wx_api.py draft-add --title "短标题" --digest "摘要" --content ".\article-wx.html" [--cover ".\cover.png"] [--author "名"]` | 返回 `media_id` |
| 更新草稿 | `python ../scripts/wx_api.py draft-update --media "<media_id>" --title "新标题" --digest "新摘要" --content ".\article-wx.html" [--cover ...]` | 改标题/正文后重推同一篇；遇 WAF 501 自动 delete+add 绕行并返回新 media_id |
| 单篇详情 | `python ../scripts/wx_api.py draft-get "<media_id>"` | 获取草稿详情 |
| 回读自动核验 | `python ../scripts/check_draft.py "<media_id>" [--expect-imgs N] [--json]` | 推送后必跑；断言标题/摘要/封面/图数/代码块结构 |
| 草稿列表 | `python ../scripts/wx_api.py draft-list --offset 0 --count 20` | `no_content:1` |
| 草稿总数 | `python ../scripts/wx_api.py draft-count` | 返回 total |
| 删除草稿 | `python ../scripts/wx_api.py draft-delete "<media_id>"` | 返回 `{"errcode":0}` 即成功 |

**简易推送**：仅需"推一篇草稿"时可用 `../scripts/wx_draft_push.py --html <path> --title "<标题>" --digest "<摘要>" [--cover <img>]`（自动 token→封面→草稿，成功输出 `DRAFT_OK media_id:`）。查询/更新/删除/发布走 wx_api.py。

## 参数约束

| 参数 | 约束 |
|---|---|
| `--title` | ≤ **64 字节**（≈21 个汉字，中文 3 字节/字）。草稿标题取正文标题的短句；完整标题放 HTML 正文里 |
| `--digest` | ≤ **120 字符**，可选，超过会报错或截断 |
| `--content` | 本地 HTML 文件路径，**必须内联样式**（微信剥离 `<style>`） |
| `--cover` | 本地图片路径；可选，缺省则草稿无封面。上传见 `../materials/` |

## 正文 HTML 约束（微信兼容）

**唯一权威定义见 `../write/SKILL.md`「二、wx 内联版 HTML 硬规范」**（含产物形态、标签红线、代码块模板、mmbiz 图一步到位）。此处仅列推送侧要点：

- `--content` 必须是**纯 `<section>` 正文片段**（不包文档外壳），样式全部内联。
- 代码块必须用 `<section>` + 逐行 `<p>`（`margin:0;text-indent:0`）+ 空格转 `&nbsp;` + 空行 `<p>&nbsp;</p>`——**禁 `<pre>`**（微信剥离并折叠空格/换行）。
- 代码内 `<` `>` `&` 转义（`&lt;` `&gt;` `&amp;`）。
- 正文图片必须为 `mmbiz.qpic.cn` URL（先 `uploadimg`，见 `../materials/`），`draft-add` 只处理 `--cover`。
- 封面宽比 2.35:1（900×383）展示最佳；API 接受任意图并自动裁剪。
- **推送前必跑校验**：`../write/scripts/validate_wx_html.py <article.html>`，ERROR=0 才推。

## 制作→预览工作流

1. 制作 wx 内联版 HTML（单一交付物，含 mmbiz 正文图）。
2. `draft-add` 推草稿 → 得到 `media_id`，告诉用户去 公众号后台 → 草稿箱 预览。
3. **回读核验（不得省略，自动执行）**：`../scripts/check_draft.py <media_id> [--expect-imgs N]`——自动断言标题 ≤64 字节、摘要 ≤120 字符、封面 thumb 非空、正文无 `<pre>`/`<style>`、mmbiz 图数 = 预期（给定 N 时）、无本地图片路径；输出逐项 `[PASS]/[FAIL]`，FAIL 即修复后 `draft-update`（或 delete+add）重推。
4. 用户验收后要求发布 → 先 `../scripts/wx_api.py check-perm` 探测权限。个人主体/未认证账号实测整个发布接口族返回 48001/53010（不要重试）→ 引导用户到 公众号后台 → 内容管理 → 草稿箱 手动发布，并附「发布前四项后台手动设置」提醒（见根 `../SKILL.md`「发布」节：开赞赏 / 声明原创 / 选择合集 / 创作来源 AI 生成——API 无对应字段，必须手动勾选）。
5. 用户要求删除草稿 → `draft-delete <media_id>`（`{"errcode":0}` 即成功）。

> `draft-update` 遇腾讯 WAF 501（请求体较大时可能触发）已由 `wx_api.py` 自动绕行：回读原封面 → delete 旧草稿 → add 新草稿，返回新 `media_id`（旧 media_id 失效，注意更新记录）。

## 已推送草稿的管理

- 草稿箱可能被后台或他处外部删改：**再次操作某篇草稿前**，先 `draft-list` 实查确认其 `media_id` 仍在（不要凭历史记录里的 media_id 直接 update/delete/get）。
- 改标题/正文后重推同一篇：`draft-update --media <media_id> --title ... --digest ... --content <html>`（`index:0` 指单图文第一篇；`--cover` 不传则保留原封面）。
- 多篇场景：`draft-list --count 30` 返回为**倒序**（最新在前），按标题而非返回顺序对应文章编号。

## 排障

- 上传封面失败 → 见 `../materials/` 与 `../references/gotchas.md`。
- 常见错误码 `40164` / `43002` / `45009` / `40007` → `../references/gotchas.md`。
- 正文图在预览时不显示 → 图片未换成 `mmbiz.qpic.cn` URL，按 `../materials/` 重新 `uploadimg` 并替换 HTML 后 `draft-update` 重推。
