---
name: draft-push-parameters
summary: B4 推送草稿箱：验收包核验与指纹链、六接口口径、字段参数上限、WAF 501 绕行、发布权限与发布前必设四项；自 draft 技能完整并入（5.0.0），并在 5.1.0 收编验收包必查与结论内联。
---

# B4 推送草稿箱：接口、参数与验收包核验

官方文档：草稿管理和商品卡片（`https://developers.weixin.qq.com/doc/offiaccount/`）。
统一 CLI 是根 `scripts/wx_api.py`，一次调用完成「取 token → 上传封面 → 提交」。
凭据环境变量见仓库根 `SKILL.md`。**B3 验收包（`acceptance.json`）是推送的唯一前置**，
本文自带执行所需的全部口径；`references/gotchas.md` 与 `references/api-docs.md` 供溯源。

## 前置：验收包三查（`push_gate.py`，缺一不放行）

```bash
python Write/references/b4-push/scripts/push_gate.py push \
    --html article.html --acceptance article_acceptance.json \
    --title "<短句>" --digest "<摘要>" [--cover cover.png] [-o push.json] [--dry]
```

1. **存在**：`--acceptance` 必填。旧版 `--b5/--b3/--b4` 散装可选参数「漏传就绕过」的问题
   从接口上消除——验收包整体缺失、overall 不是 PASS（**PENDING 也不放行**：子闸没真跑完
   ≠ 通过）都推不了。
2. **指纹**：验收包里的 `html_sha256` 必须等于当前 HTML 的 sha256——防止
   「验收的是 A 版、推送的是 B 版」。
3. **留痕**：推送成功后 `push.json` 落盘 `{"media_id","html","html_sha256","acceptance"}`，
   B5 回读直接消费，media_id 不靠人工复制，哈希成为「改了没重推」的判定基准。

`--dry` 只跑本地核验（验收包 + 指纹 + 参数），不取 token 不发请求。
`precheck` 子命令只核参数与验收包，不产生草稿。

## 六个接口

| 操作 | 命令 | 说明 |
|---|---|---|
| 新增草稿 | `python scripts/wx_api.py draft-add --title "短标题" --digest "摘要" --content ".\article-wx.html" [--cover ".\cover.png"] [--author "名"]` | 返回 `media_id` |
| 更新草稿 | `python scripts/wx_api.py draft-update --media "<media_id>" --title "新标题" --digest "新摘要" --content ".\article-wx.html" [--cover ...]` | 改标题/正文后重推同一篇；不传 `--cover` 时自动回读原封面（避免 `40007`）；遇 WAF 501 自动 delete+add 绕行并打印 `MEDIA_ID_CHANGED old=… new=…` |
| 单篇详情 | `python scripts/wx_api.py draft-get "<media_id>"` | 获取草稿详情 |
| 草稿列表 | `python scripts/wx_api.py draft-list --offset 0 --count 20` | `no_content:1` |
| 草稿总数 | `python scripts/wx_api.py draft-count` | 返回 total |
| 删除草稿 | `python scripts/wx_api.py draft-delete "<media_id>"` | 返回 `{"errcode":0}` 即成功 |

回读核验（`check_draft.py` / `readback_check.py`）是 B5 的对象，判据见
`../b5-readback/readback-verification.md`。

## 参数上限（B4 自有职责，超限本地判掉）

| 参数 | 约束 |
|---|---|
| `--title` | ≤ **64 字节**（≈21 个汉字，中文 3 字节/字）。**只有草稿/分享卡的 `title` 受限，正文内的大标题可以更长**——草稿标题取正文标题的短句，完整标题放 HTML 正文里 |
| `--digest` | ≤ **120 字符**，可选，超过会报错或截断 |
| `--content` | 本地 HTML 文件路径，必须已过 B3 验收（纯 `<section>` 片段、内联样式，红线见 `../b3-acceptance/wx-html-redlines.md`） |
| `--cover` | 本地图片路径；可选，缺省则草稿无封面。上传见 `../b1-images/image-upload-interfaces.md` |

请求体的原始口径（`draft/add` 传 `{"articles":[...]}` 数组、`draft/update` 传单对象且
`index:0` 为单图文第一篇、article 字段表）见根 `references/api-docs.md`，溯源用，不读也能执行。

## 推送与预览工作流

1. B3 验收包冻结（`acceptance_pack.py`，含 `html_sha256`）。
2. `push_gate.py push` → `draft-add` → 得到 `media_id` 与 `push.json`；
   告诉用户去 公众号后台 → 草稿箱 预览。
3. **回读核验（不得省略，自动执行）**——见 `../b5-readback/readback-verification.md`。
4. 用户验收后要求发布 → 先 `scripts/wx_api.py check-perm` 探测权限（只读）。

   **发布权限（结论内联，溯源 `references/gotchas.md` A3）**：个人主体/企业未认证账号
   **整个发布接口族无权限**——不只是提交，`freepublish/batchget`、`publish-get` 等只读查询
   同样 48001（2025-09 实测）。判定无权限后**不要重试**，引导用户到 公众号后台 → 内容管理 →
   草稿箱 手动发布；已发布结果以后台「已发表」页为准（接口查不到）。`53010` 为同类限制。
   认证账号（`perm:true`）可按官方 Draft_Box/Publish 章节扩展 `freepublish/submit`，
   本技能默认不封装。

   **发布前必设四项**（API 无对应字段，只能在后台发布流程手动勾选；`draft-add` 成功后必须把
   这段附在结果里）：

   - ① **开赞赏** —— 发布页「赞赏」开关（需账号已开通赞赏）
   - ② **声明原创** —— 编辑器底部「声明原创」，类型选「文字」
   - ③ **合集** —— 发布页「合集」下拉，选目标合集（按账号实际创建的合集名）
   - ④ **创作来源「内容由 AI 生成」** —— 发布页「创作来源」/「文章设置」选择

   固定话术：「草稿已推送。发布前请在公众号后台完成四项设置：①开赞赏 ②声明原创（文字）
   ③选择合集 ④创作来源选『内容由AI生成』。API 不支持这些字段，必须手动勾选。」
5. 用户要求删除草稿 → `draft-delete <media_id>`（`{"errcode":0}` 即成功）。

## 已内联的排障结论（溯源 `references/gotchas.md`）

- **token 7200 秒**（A4）：现取现用不缓存；一次推送只取一次（token → 封面 → 草稿一次跑完）。
- **`40007` 空封面**（B4）：`draft-update` 不带 `--cover` 重推时，`articles.thumb_media_id`
  **省略或空串都判 40007**，报错文案误导为草稿 id 无效——无效的是封面字段。`wx_api.py`
  3.2.1 起自动回读原 thumb 再提交。
- **WAF 501 绕行**（B5）：`draft-update` 大请求体（约 47KB 实测）可能被腾讯网关风控拦截返回
  HTML 而非 JSON；与重试次数无关，**退避无效，不要继续重试**。`wx_api.py` 4.3.0 起内置
  「回读原封面 → delete → add」自动绕行，成功打印 `MEDIA_ID_CHANGED old=<旧id> new=<新id>`。
  **绕行等于换了草稿身份**：旧 `media_id` 立即失效（对旧 id 回读只会 40007），必须对新 id
  重跑回读。绕行失败打印 `ERR BYPASS_FAILED`——此时草稿状态未知，先 `draft-list` 实查再决定。
- **草稿箱外部删改**（B6）：草稿箱可在后台被手动删改。**再次操作某篇草稿前**，先
  `draft-count` + `draft-list` 实查确认 `media_id` 与标题一一对应，**不凭历史记录直接
  update/delete/get**。
- `draft-list --count 30` 返回为**倒序**（最新在前），按标题而非返回顺序对应文章编号。
- 其他错误码（`40164`/`43002`/`45009`）见 `../b1-images/image-upload-interfaces.md`「排障」。
- 正文图在预览时不显示 → 图片未换成 `mmbiz.qpic.cn` URL，重新 `uploadimg` 并替换 HTML 后
  过 B3 验收再 `draft-update` 重推。
