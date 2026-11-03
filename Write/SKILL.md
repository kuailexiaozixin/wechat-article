---
name: write
description: '面向财务、税务、法律、金融、经济领域的研究性专业文章写作与微信兼容 HTML 排版：A 轨道五阶段（A1 立意 → A2 结构 → A3 素材 → A4 逻辑图 → A5 成文）把判断立住，B 轨道五阶段（B1 配图 → B2 排版 → B3 验收 → B4 推送 → B5 回读）把它安全送进草稿箱；每个阶段的说明文档与脚本在同名目录下，阶段自足。当用户要求"写一篇专业文章""写一篇公众号文章""做公众号排版""这段文字 AI 味重""把这篇推草稿箱""回读核验刚才那篇"时使用。读取已有文章属 Read/，按关键词搜索文章属 Search/。'
---

# 公众号文章写作与交付（Write）

**产出物 = 单一 HTML 文件（纯 `<section>` 正文片段）+ 一个已核验的草稿箱 `media_id`**：
样式全部内联、无外部资源、正文图为 `mmbiz.qpic.cn` URL。

**体裁只有一种**：面向财务、税务、法律、金融、经济领域的**研究性专业文章**。读者是同行，
他们要的是可复用的判断，不是情绪与故事。

任务分两条轨道：**A 轨道**管判断怎么立起来、文章怎么写出来，**B 轨道**管它怎么安全进微信。
A 轨道没走完不要开始 B 轨道——B 轨所有闸的输入都是 A 轨的定稿，先排版后改稿会把 B2-B5 全部重跑。

两条轨道同构：**一阶段 = 一个唯一交付物 + 一个出口判据 + 一份规则所有权**；
每阶段目录自足（执行所需口径都在目录内），跨阶段靠调用上游能力，不靠引用外部文档。

## 一、规范在哪（本文只留流程与指针，规则不重复）

| 要解决的事 | 文件 | 轨道 |
|---|---|---|
| 立意与结论（六要素、四类体裁、结论具体性） | `Write/references/a1-thesis/thesis-six-elements.md` | A1 |
| 章节结构（六种推进法、章节交接） | `Write/references/a2-structure/structure-patterns.md` | A2 |
| 素材门槛与来源身份 | `Write/references/a3-materials/material-ledger-spec.md` | A3 |
| 逻辑图与四类校验 | `Write/references/a4-logic/logic-graph-spec.md` | A4 |
| 行文工艺 | `Write/references/a5-draft/research-prose-craft.md` | A5 |
| 成稿禁令、七遍改稿、词表维护（判据源） | `Write/references/a5-draft/revision-protocol.md` | A5（同时是 B3 词表维护源） |
| 去 AI 味操作手册 | `Write/references/a5-draft/de-ai-playbook.md` | A5 |
| 代码块与条目卡片模板、正文排版写法 | `Write/references/b2-typeset/wx-html-templates.md`（同目录 `theme-default.md` 是样式单一来源） | B2 |
| 微信兼容红线与产物形态（判据权威） | `Write/references/b3-acceptance/wx-html-redlines.md` | B3 |
| B1-B5 各阶段的判据与命令 | 各阶段目录下的说明文档，见下表「文档」列 | B |

## 二、A 轨道：内容（五阶段，按判断的建立顺序划分，顺序不可调换）

| 阶段 | 唯一交付物 | 出口判据 | 文档 | 脚本 |
|---|---|---|---|---|
| **A1 立意** | `thesis.json` | 六要素齐备、结论带判断与边界 | `Write/references/a1-thesis/thesis-six-elements.md` | `Write/references/a1-thesis/scripts/thesis_check.py` |
| **A2 结构** | `outline.json` | 每节回指分论点、交接关系齐、字数预算一致 | `Write/references/a2-structure/structure-patterns.md` | `Write/references/a2-structure/scripts/outline_check.py` |
| **A3 素材** | `materials.json` | 每节材料达门槛、每条有来源、pending 清零 | `Write/references/a3-materials/material-ledger-spec.md` | `Write/references/a3-materials/scripts/material_ledger.py` |
| **A4 逻辑** | `logic.json` | 四类查询全过：孤证章节／空 warrant／术语漂移／系列冲突 | `Write/references/a4-logic/logic-graph-spec.md` | `Write/references/a4-logic/scripts/logic_graph.py` |
| **A5 成文** | `draft.md` | `check_prose` 清零 + 无重复段落 + 七遍改稿走完 | `Write/references/a5-draft/research-prose-craft.md`、`Write/references/a5-draft/revision-protocol.md`、`Write/references/a5-draft/de-ai-playbook.md` | `Write/references/a5-draft/scripts/check_prose.py`、`Write/references/a5-draft/scripts/check_duplicates.py` |

为什么是这个顺序：**先有判断，才有结构；先有结构，才知道要哪些材料；材料连成图，才查得出哪节的结论是悬空的**。
反过来做（先写再补依据）是最常见的失败路径——写出来的每一句都对，每一句都没出处。

A 轨典型一条链：

```bash
python Write/references/a1-thesis/scripts/thesis_check.py init -o thesis.json
python Write/references/a1-thesis/scripts/thesis_check.py check thesis.json
python Write/references/a2-structure/scripts/outline_check.py init -o outline.json
python Write/references/a2-structure/scripts/outline_check.py check outline.json --thesis thesis.json
python Write/references/a3-materials/scripts/material_ledger.py init --outline outline.json -o materials.json
python Write/references/a3-materials/scripts/material_ledger.py check materials.json --outline outline.json
python Write/references/a4-logic/scripts/logic_graph.py init --outline outline.json --materials materials.json --thesis thesis.json -o logic.json
python Write/references/a4-logic/scripts/logic_graph.py check logic.json --materials materials.json
python Write/references/a5-draft/scripts/check_prose.py draft.md
python Write/references/a5-draft/scripts/check_duplicates.py <成品目录> [--min-len 40] [--threshold 0.8]
```

材料不够时只有三条路：能查的先查（准则、解释、裁判文书、统计、文献）、一次问完最多三个问题、
缩小题目。**不能靠形容词把字数填满**——1200 字需 5 件有来路的材料，3000 字需 13 件。

## 三、B 轨道：交付（五个阶段，按产物划分，顺序不可调换）

划分依据：**一阶段 = 一个唯一交付物 + 一个出口判据 + 一份规则所有权**。
每阶段目录自足（本阶段执行所需口径都在目录内），跨阶段靠调用上游能力，不靠引用外部文档。

| 阶段 | 唯一交付物 | 出口判据 | 文档 | 脚本目录 |
|---|---|---|---|---|
| **B1 配图** | `manifest.json` + `mmbiz_map.json`（封面另有 media_id） | 清单预检过 | `Write/references/b1-images/image-upload-interfaces.md`、`image-flow-steps.md`、`figure-manifest-spec.md` | `Write/references/b1-images/scripts/` |
| **B2 排版** | `article.html` | 漏段/凭空加段清零；样式与编号合格 | `Write/references/b2-typeset/typeset-workflow.md`、`wx-html-templates.md`、`theme-default.md` | `Write/references/b2-typeset/scripts/` |
| **B3 验收** | `acceptance.json`（四子闸合一 + `html_sha256`） | 静态 + 渲染 + 人工签字 + 图数一致性，全绿且渲染真跑过 | `Write/references/b3-acceptance/acceptance-gates.md`、`wx-html-redlines.md`、`static-gate-rules.md`、`render-gate-rules.md`、`manual-signoff-checklist.md` | `Write/references/b3-acceptance/scripts/` |
| **B4 推送** | `push.json`（media_id + `html_sha256`） | 验收包存在、overall=PASS、指纹一致、参数合规 | `Write/references/b4-push/draft-push-parameters.md` | `Write/references/b4-push/scripts/` |
| **B5 回读** | `readback.json` | 正文与源逐字一致 + 源哈希 == 推送记录哈希 | `Write/references/b5-readback/readback-verification.md` | `Write/references/b5-readback/scripts/` |

典型一条链（B1-B5 全走）：

```bash
python Write/references/b1-images/scripts/figure_manifest.py check manifest.json
python Write/references/b1-images/scripts/upload_imgs.py --html draft-wx.html --map mmbiz_map.json
python Write/references/b2-typeset/scripts/build_blocks.py blocks.json -o article.html
python Write/references/b2-typeset/scripts/typeset_plan.py audit blocks.json --draft draft.md
python Write/references/b2-typeset/scripts/typeset_plan.py verify article.html
python Write/references/b3-acceptance/scripts/acceptance_pack.py --html article.html \
    --manifest manifest.json --signoff article_B5.json -o article_acceptance.json
python Write/references/b4-push/scripts/push_gate.py push --html article.html \
    --acceptance article_acceptance.json --title "<短句>" --digest "<摘要>" -o push.json
python Write/references/b5-readback/scripts/readback_check.py --record push.json --manifest manifest.json
```

（人工签字在 pack 之前：`python Write/references/b3-acceptance/scripts/manual_signoff.py record
--html article.html --qa article_qa390.png --note "<结论>"`，截图来自渲染子闸。）

## 四、闸口顺序（不得调换）

`check_prose`（散文硬禁令）→ B2 `audit/verify`（排版有没有改内容、样式是否漂移）→
B3 `acceptance_pack`（静态红线 + 390px 渲染 + 人工签字 + 图数一致性，**冻结 html_sha256**）→
B4 推送（验收包必查 + 指纹核对 + 内置同一道 B3 校验，ERROR>0 直接退出、不取 token）→
B5 `check_draft --source`（回读 + 源一致性 + 哈希比对）。

各道判据**互不覆盖**：B2 只管排版有没有偷偷改内容（红线已全部移交 B3，旧版四项重叠判据已删）；
B3 静态查标签与词法、渲染查像素、人工查内容与观感；B4 的指纹核对防「验收 A 版推送 B 版」；
B5 的哈希比对防「改了没重推」。跑了一道不等于另一道可以省。

## 五、脚本清单

| 脚本 | 产出物 |
|---|---|
| `Write/references/a1-thesis/scripts/thesis_check.py` | 立意卡骨架 / 六要素与结论具体性校验 |
| `Write/references/a2-structure/scripts/outline_check.py` | 章节树骨架 / 结构校验 / 章节关系图 |
| `Write/references/a3-materials/scripts/material_ledger.py` | 按节派单 / 材料门槛与来源身份校验 / 覆盖报告 |
| `Write/references/a4-logic/scripts/logic_graph.py` | 逻辑图骨架 / 四类查询 / 论证图导出 |
| `Write/references/a5-draft/scripts/check_prose.py` | 成稿纯文本硬禁令报告（翻案句及变形、黑话、硬停词、模型路标、破折号/提示性冒号） |
| `Write/references/a5-draft/scripts/check_duplicates.py` | 跨篇重复段落报告 |
| `Write/references/b1-images/scripts/figure_manifest.py` | 清单骨架 / 预检 / 清单-正文一致性核验 / mermaid 目录转条目 |
| `Write/references/b1-images/scripts/render_mermaid.py` | Mermaid PNG（本地 runtime 优先，离线可用） |
| `Write/references/b1-images/scripts/gen_table.py` | 表格/结构化内容 → PNG（spec JSON 驱动） |
| `Write/references/b1-images/scripts/gen_cover.py` | 封面 PNG（几何构图，可选标题/副标题文字） |
| `Write/references/b1-images/scripts/compress_img.py` | 正文图压到 1MB 以下 |
| `Write/references/b1-images/scripts/upload_imgs.py` | mmbiz URL 与 `--map` 映射；上传前逐张尺寸预检 |
| `Write/references/b1-images/scripts/check_urls.py` | mmbiz URL 可达性体检 + 漏传核对 |
| `Write/references/b2-typeset/scripts/build_blocks.py` | 与 `theme-default.md` 逐字一致的正文片段 |
| `Write/references/b2-typeset/scripts/typeset_plan.py` | 排版计划 / 漏段与凭空加段审计 / 样式与编号核对 |
| `Write/references/b3-acceptance/scripts/validate_wx_html.py` | wx 合规 ERROR/WARNING 清单 + AI 味启发式（判据表见 `references/gotchas.md` D 组） |
| `Write/references/b3-acceptance/scripts/static_check.py` | 批量静态闸 + 机器可读 JSON |
| `Write/references/b3-acceptance/scripts/qa_mobile.py` | 390px 渲染验收 + 整页截图 |
| `Write/references/b3-acceptance/scripts/render_gate.py` | 环境预检 / 渲染调用留痕 / 截图核对 |
| `Write/references/b3-acceptance/scripts/wrap_preview.py` | 本地预览页（外壳文件，不参与校验） |
| `Write/references/b3-acceptance/scripts/manual_signoff.py` | 核对单 / 签字记录 / 供验收包校验签字 |
| `Write/references/b3-acceptance/scripts/acceptance_pack.py` | 四子闸合一只读验收，冻结 `html_sha256` |
| `Write/references/b4-push/scripts/push_gate.py` | 验收包三查 / 参数预检 / 推送并捕获 media_id |
| `Write/references/b5-readback/scripts/readback_check.py` | 回读门禁（委托 `check_draft.py`）+ 哈希留痕 |

接口层三支留在仓库根 `scripts/`（`wx_api.py`、`wx_draft_push.py`、`check_draft.py`）——
被多个阶段共用，B1/B4/B5 的脚本以委托方式使用它们，不重复实现。

判据测试在仓库根 `tests/`：`python tests/run_all.py` 一次跑完（改判据或改文档后必跑）。
`Write/references/` 下的目录与文档名由 `tests/test_evals_routes.py` 逐字符核对，改名要同步引用。
