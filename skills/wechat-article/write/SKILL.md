---
name: write
description: '面向财务、税务、法律、金融、经济领域的研究性专业文章写作与微信兼容 HTML 排版：A 轨道（写作：立判断 → 定结构 → 备材料 → 成文，进入 B1 前必须把文章整理为符合 wx-HTML 规范的 HTML 文档）把判断立住，B 轨道五阶段（B1 配图 → B2 排版核对 → B3 验收 → B4 推送 → B5 回读）把它安全送进草稿箱；每个阶段的说明文档与脚本在同名目录下，阶段自足。当用户要求"写一篇专业文章""写一篇公众号文章""做公众号排版""这段文字 AI 味重""把这篇推草稿箱""回读核验刚才那篇"时使用。读取已有文章属 read/，按关键词搜索文章属 search/。'
---

# 公众号文章写作与交付（Write）

**产出物只有一个**：单一 HTML 文件 `article-wx.html`（纯 `<section>` 正文片段，样式全内联、无外部资源、正文图为 `mmbiz.qpic.cn` URL）+ 一个已核验的草稿箱 `media_id`。
**单文件铁律（硬性）**：本地预览与公众号后台共用同一份 `article-wx.html`。mmbiz URL 公网可达，B1 回填后直接双击这一个文件就能看到全部配图；**禁止再生成「本地预览版」「base64 存档版」「待推送版」等第二份 HTML 交付物**，也禁止为「本地看效果」另存一份。`wrap_preview.py` 生成的临时外壳只写系统临时目录，属预览工具、不算产物。全链路文件名与路径不变：A 轨写 `__MMP__` 占位 → B1 上传后原地回填 → B3/B4 校验推送。
**体裁只有一种**：面向财务、税务、法律、金融、经济领域的研究性专业文章——读者是同行，要可复用的判断，不要情绪与故事。

两条轨道，按序走完才算交付：**A 轨道管判断怎么立起来、文章怎么写出来、并整理成 wx-HTML 文档；B 轨道（B1-B5）管它怎么安全进微信。**
A 轨道没走完不要开始 B 轨道——B 轨每个闸的输入都是 A 轨直出的 HTML，先排版后改稿会把 B2-B5 全部重跑。
进入 B1 之后文字即冻结；再改稿会撞上 B3 冻结的 `html_sha256`，B4 指纹核对直接 FAIL。

所有步骤共用三条不变式：

1. **一步 = 一个唯一交付物 + 一个出口判据 + 一份规则所有权**——判据不过，不得进入下一步，也不许带着病走。
2. **每步目录自足**：执行所需口径都在该步目录下，规范指针只指向本步目录内的文档，跨步靠调用上游交付物，不靠外部文档。
3. **各道判据互不覆盖**：B2 查排版有没有偷偷改内容，B3 查标签词法/像素/内容观感，B4 查「验收 A 版推送 B 版」，B5 查「改了没重推」。跑了一道不等于另一道可以省。

工作流全链（顺序不可调换）：

```
A 轨道（立判断 → 定结构 → 备材料 → 成文 → 整理为符合 wx-HTML 规范的 article-wx.html）──▶ B1 配图 → B2 排版核对 → B3 验收(冻结哈希) → B4 推送(核哈希) → B5 回读(验哈希)
```

---

## A 轨道：把文章写出来，并整理成 wx-HTML 文档

A 轨道只交付一件事：**一份符合 wx-HTML 规范的 HTML 文档**（`article-wx.html`）。判断怎么立、结构怎么搭、材料怎么备、句子怎么写，全部在这一步内部完成——**入口是选题，出口是文档**。

- **输入**：选题（一个研究问题）
- **动作**（顺序不可倒：先有判断才有结构，先有结构才知道要哪些材料，材料连成图才查得出哪节结论悬空）：
  1. **立判断**：写下核心判断与它的边界（适用前提、失效条件）。结论不能是复述已知，要能回答「所以该怎么判」
  2. **定结构**：按判断推出章节架构，每节标注【依据】【形式】【待核验】三标注；章节编号连续、无裸编号
  3. **备材料**：按章节登记材料、来源身份（一手事实／当事人自述／二手概括／作者推断／未核实）与 `verified_at`。**每 240 字至少一件有来路的材料**（1200 字需 5 件、3000 字需 13 件），**全篇至少一条一手事实**。材料不够只有三条路：能查的先查（准则、解释、文书、统计、文献）、一次问完最多三个问题、缩小题目——**不能靠形容词把字数填满**。材料台账落 `materials.json`，B1 的图注数字要能回指它
  4. **成文**：从具体条文/交易/数字起手，不用「随着……发展」这类万能开头；强断言带限定词；空推理桥清零；术语一节一钉，不在同篇内漂移
- **行文硬纪律**（下列词与形态**不进正文**）：
  - 制作痕迹：「全文」「稿件」「对应台账」「结尾交代」「下面按」「标注推断」等创作过程自述
  - 空洞修辞：感叹号 >3 个、最长段 >120 字、段均 >80 字、「其一其二其三」「一是二是三是」编号排比
  - 传说表述：无出处的「业内普遍认为」「众所周知」；未核实的数字与结论
- **出口闸（A 轨总闸，进 B1 前的唯一判据）**：
  1. **文章必须已整理为符合 wx-HTML 规范的 HTML 文档** `article-wx.html`：纯 `<section>` 正文片段，样式全内联、无外部资源，正文图为 `__MMP__` 占位；不产出 Markdown 中间稿，不包 `<!DOCTYPE>`/`<html>` 外壳。**全程只维护这一份文件**：A 轨写占位 → B1 上传后原地回填 mmbiz URL → B3/B4 校验推送，文件名与路径不变。占位态本地看不到图时，用 `wrap_preview.py --figures` 生成临时预览外壳（系统临时目录），**不许另存第二份 HTML**。规范权威：`write/references/b3-acceptance/wx-html-redlines.md`（红线与产物形态）、`write/references/b2-typeset/wx-html-templates.md`（结构模板）、`write/references/b2-typeset/theme-default.md`（样式单一来源）
  2. `python write/references/b3-acceptance/scripts/validate_wx_html.py article-wx.html` **ERROR 归零**——这是「符合 wx-HTML 规范」的可执行判据（禁词、制作痕迹、AI 味、长段、`<pre>` 残留、外部资源等）
  3. `__MMP__` 占位与 B1 图清单一一对应，无遗漏无多余
  → 三项全过才进 B1。**未整理成 wx-HTML 文档就进 B1，B2-B5 全部要重跑。**

---

## B 轨道：把定稿安全送进草稿箱

接口层三支共用脚本留在仓库根 `scripts/`：`scripts/wx_api.py`（token 与接口封装）、`scripts/wx_draft_push.py`（推送）、`scripts/check_draft.py`（草稿回读）——B1/B4/B5 的脚本以委托方式使用，不重复实现。

### B1 配图

- **输入**：A 轨直出的 `article-wx.html`（图是 `__MMP__` 占位）+ `materials.json`（图注数字要能回指）
- **规范**：`write/references/b1-images/figure-manifest-spec.md`（清单规格）、`write/references/b1-images/image-flow-steps.md`（流程）、`write/references/b1-images/image-upload-interfaces.md`（上传接口与错误码）
- **动作**（按稿件所需取用）：
  1. 建 `manifest.json` 并预检：`python write/references/b1-images/scripts/figure_manifest.py check manifest.json`
  2. 需要图时：mermaid 出图 `write/references/b1-images/scripts/render_mermaid.py`；表格/结构化内容 `write/references/b1-images/scripts/gen_table.py`；封面 `write/references/b1-images/scripts/gen_cover.py`；正文图先 `write/references/b1-images/scripts/compress_img.py` 压到 1MB 以下
  3. 上传：`python write/references/b1-images/scripts/upload_imgs.py --manifest manifest.json --map mmbiz_map.json`（按 `filename` 批量传正文图；也可 `--html`/`--img`），产出 `mmbiz_map.json`（键为 `filename`，封面另存 media_id）
  4. 回填：`python write/references/b1-images/scripts/fill_placeholders.py --html article-wx.html --map mmbiz_map.json` 把 A 轨占位 `__MMP__:<filename>` 换成 mmbiz URL
  5. 体检：`python write/references/b1-images/scripts/check_urls.py --html article-wx.html --map mmbiz_map.json` 核对 mmbiz URL 可达、无漏传、无残留 `__MMP__` 占位
  6. 图注闸：`python write/references/b1-images/scripts/check_captions.py --manifest manifest.json --requirements figure-requirements.json --html article-wx.html --json captions-check.json`（图注只写图里的内容，禁「对应台账第一节」「对应第二节段4」这类内部坐标与作者动作）
  7. 本地可见性自检：`upload_imgs.py` 返回的 URL 统一为 `https://mmbiz.qpic.cn/...`；排版时每张图必须同时写入 `data-fallback` 内嵌兜底与 `background-image` 背景兜底（见红线「离线可见铁律」）。跑 `python write/references/b3-acceptance/scripts/check_image_visibility.py article-wx.html` ——在 `http://127.0.0.1` 静态服务里做「在线 / 掐断全部外链」两轮渲染，两轮都必须每张图可见；再跑 `check_single_artifact.py --dir <稿件目录>` 应 PASS。浏览器**直接打开这一个文件**即可看到全部配图，不许另存一份 HTML
- **出口闸**：清单预检全绿 + 占位回填（残留清零）+ URL 全活 + 图注闸退出 0 + 产物唯一性 PASS + 图片可见性两轮 PASS 才进 B2

### B2 排版核对（A 轨已直出 HTML，本步降级为核对）

- **输入**：`article-wx.html`（A 轨直出）+ `mmbiz_map.json`（B1 回填后）
- **规范**：`write/references/b2-typeset/typeset-workflow.md`（流程）、`write/references/b2-typeset/wx-html-templates.md`（代码块/条目卡片模板与正文排版写法）、`write/references/b2-typeset/theme-default.md`（样式单一来源，改样式只改它）
- **动作**（A 轨已按 theme-default 直出，样式与编号核对照跑；仅当需要重排时才用 build_blocks 重建）：
  1. 内容审计：`python write/references/b2-typeset/scripts/typeset_plan.py audit blocks.json --draft draft.md`
  2. 样式核对：`python write/references/b2-typeset/scripts/typeset_plan.py verify article.html`
- **出口闸**：漏段/凭空加段清零、样式与编号合格才进 B3。**B2 只管排版有没有偷偷改内容，微信红线不在这里查**（已移交 B3）

### B3 验收

- **输入**：`article.html` + `manifest.json`
- **规范**：`write/references/b3-acceptance/acceptance-gates.md`（四子闸总纲）、`write/references/b3-acceptance/wx-html-redlines.md`（微信兼容红线与产物形态，判据权威）、`write/references/b3-acceptance/static-gate-rules.md`、`write/references/b3-acceptance/render-gate-rules.md`、`write/references/b3-acceptance/manual-signoff-checklist.md`；词表与禁词判据的唯一维护点是 `write/references/b3-acceptance/scripts/validate_wx_html.py` 自身（`BANNED_WORDS`/`AI_FLAVOR_PHRASES`/`PROCESS_TRACE_RULES`），启发式判据表另见 `references/gotchas.md` D 组
- **动作**（四子闸顺序执行，人工签字在打包之前）：
  1. 静态：`python write/references/b3-acceptance/scripts/static_check.py`（可先用 `write/references/b3-acceptance/scripts/validate_wx_html.py` 单跑定位，其 AI 味启发式词表与 gotchas 同步）；产物唯一性 `python write/references/b3-acceptance/scripts/check_single_artifact.py --dir <稿件目录>`——多一份 wx-HTML 即 FAIL，该判据已并入 `acceptance_pack.py`，B4 推送前必过
  2. 渲染：`python write/references/b3-acceptance/scripts/qa_mobile.py` 出 390px 截图（`render_gate.py` 管环境预检与留痕）；**图片可见性** `python write/references/b3-acceptance/scripts/check_image_visibility.py article-wx.html`——判据环境与编辑器一致（`http://127.0.0.1` 静态服务），并强制跑「掐断外链」的离线轮，外链被拦时内嵌兜底必须仍然可见。`qa_mobile.py` 用 `file://` 打开，外链能加载不代表编辑器里能加载，两者都要跑。本地预览直接双击 `article-wx.html`；需要栏宽外壳时用 `wrap_preview.py`，它默认写系统临时目录、不是交付物、不参与校验
  3. 人工签字：`python write/references/b3-acceptance/scripts/manual_signoff.py record --html article.html --qa article_qa390.png --note "<结论>"`（截图取自渲染子闸）
  4. 打包冻结：`python write/references/b3-acceptance/scripts/acceptance_pack.py --html article.html --manifest manifest.json --signoff article_B5.json -o article_acceptance.json`——把四子闸合一为只读验收包，**冻结 `html_sha256`**
- **出口闸**：静态 + 渲染 + 人工签字 + 图数一致性 + 产物唯一性 + 图片可见性全绿、渲染真跑过、`acceptance.json` overall=PASS 才进 B4；**改稿回来必须重走 B3，指纹会拦住旧包**

### B4 推送

- **输入**：`acceptance.json`（overall=PASS）
- **规范**：`write/references/b4-push/draft-push-parameters.md`（标题/摘要/封面参数合规与错误码处置）
- **动作**：`python write/references/b4-push/scripts/push_gate.py push --html article.html --acceptance article_acceptance.json --title "<短句>" --digest "<摘要>" -o push.json`
- **出口闸**：验收包存在 + 指纹与当前 HTML 一致 + 参数合规，脚本内置同一道 B3 校验（ERROR>0 直接退出、不取 token），推完捕获 `media_id` 写入 `push.json`；指纹不一致 → 回 B3 重跑验收，禁止绕过

### B5 回读

- **输入**：`push.json`
- **规范**：`write/references/b5-readback/readback-verification.md`（回读口径与不一致处置）
- **动作**：`python write/references/b5-readback/scripts/readback_check.py --record push.json --manifest manifest.json`
- **出口闸**：正文与源逐字一致 + 源哈希 == 推送记录哈希 → `readback.json` 落盘。**交付完成**：把 `media_id` 与草稿标题交给用户

---

## 改判据或文档之后（维护步）

- 改判据脚本或文档判据后必跑：`python tests/run_all.py` 一次跑完全部判据测试（跳过项是环境缺口，如实说明，不能当通过引用）
- `write/references/` 下目录与文档名由 `tests/test_evals_routes.py` 逐字符核对，改名必须同步全部引用
