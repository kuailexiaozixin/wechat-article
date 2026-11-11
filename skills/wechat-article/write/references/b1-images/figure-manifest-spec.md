---
name: figure-manifest-spec
summary: B1 图片清单的字段定义、必填判据与图上文字可追溯规则；清单是 B1 的产出物，先过清单再上传。
---

# B1 图片清单规范

`Write/references/b1-images/scripts/figure_manifest.py` 的四条子命令，判据都以这份清单为输入。B1 的产出物不是
一堆图片文件，而是这份清单——图片是清单的执行结果。

## 生成骨架

```bash
python Write/references/b1-images/scripts/figure_manifest.py template -o manifest.json
```

字段含义（一张图一条，写在 `figures` 数组里）：

| 字段 | 必填 | 写什么 |
|---|---|---|
| `id` | ✅ | 图片编号，如 `f01` |
| `kind` | — | `body`（默认，正文图）或 `cover`（封面，走 media_id） |
| `position` | ✅ | 插在稿件哪一处，写到段（如「第三节 段2 之后」） |
| `purpose` | ✅ | 这张图替读者省掉了哪一段文字。**不写「更直观」**——说不出省了哪段，就是不该有这张图 |
| `visual_content` | ✅ | 画什么：主体 / 关系 / 数字 |
| `text_in_image` | — | 图上文字逐字列出；空串表示无字图 |
| `labels_traceable` | 条件 | 图上文字非空时必须为 `true` |
| `source_basis` | ✅ | 图上的数字/结论来自稿件第几段或哪条来源 |
| `tool` | — | `mermaid` \| `imagegen` \| `screenshot` \| `none`。`screenshot` 用于表格/结构化排版，用 `gen_table.py` 渲染（选型见 `image-flow-steps.md`「配图工具选型」） |
| `filename` | ✅ | 落盘文件名，全清单内不可重复 |
| `aspect_ratio` | — | 如 `16:9` |

## 判据（`check` 子命令）

```bash
python Write/references/b1-images/scripts/figure_manifest.py check manifest.json [--json]
```

FAIL（拦死，退出码 1）：

- 清单不是合法 JSON、`figures` 为空或不是数组——B1 的产出物就是这份清单，没有它流程没起点。
- 缺必填字段（`id`/`position`/`purpose`/`visual_content`/`filename`/`source_basis` 任一为空）。
- `filename` 与前面条目重复——同名会互相覆盖，上传映射也会错位。
- 图上文字非空但未声明 `labels_traceable=true`：图上每个词都要能在正文或来源里指回去。
- 正文图非 jpg/png（`media/uploadimg` 只收这两种，不符报 `40005`）。
- 正文图 > 1MB（超限报 `40009`；先压缩再传，别指望接口放过）。
- 封面 > 10MB，或封面读不出尺寸。

WARN（提醒，不拦）：

- 含图上文字：生成后若有错别字或糊，**改提示词重新生成，禁止用 Pillow/SVG 在位图上盖字修补**。
- 图片尚未落盘：允许先出清单再出图，但进 B2 前必须补齐。
- 正文图宽超出 `[500, 2400]` px 建议区间：过宽微信端会压缩且浪费体积，过窄手机端偏糊（未装 Pillow 时该项 SKIP）。
- 封面宽高比离 2.35:1 超过 ±12%：大卡裁剪会丢构图。

SKIP：未装 Pillow 时跳过封面宽高比与正文图宽度核对（SKIP 不等于通过，输出里会明确列出）。

## 另外几条子命令

- `plan-mermaid <dir>`：扫描目录下 `.mmd` 文件，生成对应的 `tool: "mermaid"` 清单条目骨架，
  再交给 `render_mermaid.py` 渲染。
- `verify <manifest.json> [--html H] [--map M] [--json]`：核清单里的正文图是否都已上传
  （`--map` 中有 URL）、都已排进正文（`--html` 中出现该 URL）；正文引用了不在清单里的
  mmbiz URL 记 WARN。与 `check` 互补——`check` 只看清单自身，`verify` 看清单 ↔ map ↔ HTML
  三者是否对得上。属可选交叉核验：只给 `--map` 时可在传图后即跑（不依赖 B2 排版产物）；
  加 `--html` 时在 B2 之后跑，可精确定位「清单里的哪一张没排进正文」。

（原 `scan` 子命令已删：「清单里的图 vs 正文里真出现的图」的一致性改由 B3 验收包的
图数一致性子闸核，见 `../b3-acceptance/acceptance-gates.md`——原设计里 scan 要先有
排版后的 HTML 才能跑，与「先传图后排版」构成环形依赖。）

## 分层配图判据（配图需求须随 A 轨各层结论生成，不事后补图）

A3 逻辑走「文章台账 article-ledger.md」逐层构建文章，配图需求跟着各层结论走，不是文末统一补。
AI 读完台账 L1→L4 后产出一份 `figure-requirements.json`（配图需求清单），再用
`Write/references/b1-images/scripts/figure_plan.py` 校验并展开成 manifest：

```bash
# 1. AI 读台账各层 → 手填 figure-requirements.json（每条：layer/figure_type/trigger/tool/filename/...）
# 2. 校验需求（层级↔图形式是否错配、触发判据是否写清）
python Write/references/b1-images/scripts/figure_plan.py check figure-requirements.json
# 3. 展开成 manifest（缺的 position/source_basis 会留 TODO，补齐后进原 check 流程）
python Write/references/b1-images/scripts/figure_plan.py from-ledger figure-requirements.json -o manifest.json
```

### 层级 × 图形式 × 触发条件（什么层配什么图）

| A 轨层级 | 判断依据（读台账哪段） | 何时需配图 | 图形式 | tool |
|---|---|---|---|---|
| L1 架构 | 台账一、各章↔分论点映射 | 章数 ≥ 5 或分论点交叉支撑 | 架构总览（思维导图/流程） | `mermaid` |
| L2/L3 章节 | 台账二/三、章间过渡 + 段落承接 | 单节段落 > 6 或节内含对照/递进关系 | 章节逻辑图（流程图） | `mermaid` |
| L4 法条 | 台账四、Toulmin 论证边引用条文 | 某条论证边引用法条/条文 | 法条拆解卡（条文→要件→适用） | `screenshot`(gen_table) |
| 数据 | 台账内出现量化对比/趋势 | 有数字对比、占比、时间线 | 柱状/饼/时间线 | `screenshot`(外部图表库) |
| 封面 | 每篇必配 | — | 几何 + 题字 | `cover`(gen_cover) |

判据权威：`figure_plan.py` 的 `LAYER_TOOLS` 映射（层级错配直接拦 FAIL，比不配图更糟——
拿法条拆解用思维导图是层级错配）。需求清单的 `trigger` 字段必须写清「为什么这张图该配」，
「更直观/丰富多样」不算判据，会被拦。

## 占位 key 约定（A3→B1 交接）

A3 逻辑直出的正文里图位写 `![](__MMP__:<filename>|图注)`，`<filename>` 必须等于本清单的
`filename` 字段，也即 `upload_imgs.py` 映射表 `mmbiz_map.json` 的键（basename）。
三者同名同键，一条约定串起 A3 占位 → B1 上传 → 回填：

- 写 `article.md` 时图位 key 用 `filename`（如 `f01`、`stage-diagram`），不用中文描述；
- 出图时落盘文件名与 `filename` 一致（本规范 §生成骨架已要求）；
- `upload_imgs.py --manifest manifest.json` 按 `filename` 批量上传正文图；
- `fill_placeholders.py --html article-wx.html --map mmbiz_map.json` 把占位换成 mmbiz URL；
- `check_urls.py --html article-wx.html --map mmbiz_map.json` 核残留占位清零（有 `__MMP__` 即 FAIL）。

## 与材料的关系

`source_basis` 不是可选装饰。内容轨道成稿时，每张图的依据段落/来源必须能指回去；指不回去的图
属于凭空加内容，B2 的 `typeset_plan.py audit` 会在排版层再拦一次「凭空加段」，两层查的不是
同一件事：B1 查图有没有出处，B2 查正文有没有被排版过程改动。
