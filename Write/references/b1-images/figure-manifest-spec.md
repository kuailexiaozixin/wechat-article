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

## 与材料的关系

`source_basis` 不是可选装饰。内容轨道成稿时，每张图的依据段落/来源必须能指回去；指不回去的图
属于凭空加内容，B2 的 `typeset_plan.py audit` 会在排版层再拦一次「凭空加段」，两层查的不是
同一件事：B1 查图有没有出处，B2 查正文有没有被排版过程改动。
