---
name: image-flow-steps
summary: B1 配图流程的执行顺序、七支脚本的分工与产物、按 tool 字段的配图工具选型，以及配图相关禁令的出处。
---

# B1 配图流程：执行顺序与脚本分工

B1 的产出物是两样：**一份图片清单** + **清单里每张图对应的 mmbiz URL（或封面的 media_id）**。
规格、限制、退避、失效处理等口径见 `image-upload-interfaces.md`；清单字段与判据见
`figure-manifest-spec.md`。本文只管顺序。

## 顺序（不可颠倒）

| 步 | 命令 | 出口 |
|---|---|---|
| 0 分层配图需求 | AI 读 A3 逻辑台账（`article-ledger.md`）各层（L1 架构/L2L3 章节/L4 法条/数据）→ 手填 `figure-requirements.json`（每条：`layer`/`figure_type`/`trigger`/`tool`/`filename`） | 每张图都带「哪层、为什么配、用什么形式」 |
| 0.5 校验需求 + 出清单 | `python Write/references/b1-images/scripts/figure_plan.py check figure-requirements.json` 后 `figure_plan.py from-ledger figure-requirements.json -o manifest.json` | 层级↔图形式不错配、触发判据写清、manifest 条目生成（TODO 字段人工补齐） |
| 1 出清单 | `python Write/references/b1-images/scripts/figure_manifest.py template -o manifest.json` 后逐条填实（若第 0.5 步已 from-ledger，本步只补 TODO） | 每张图有 `purpose`（省掉了哪段文字）与 `source_basis`（依据哪段/哪条来源） |
| 2 出图 | 按清单 `tool` 字段选渲染器：`mermaid` 走 `render_mermaid.py`；表格/结构化排版走 `gen_table.py`；封面走 `gen_cover.py`；`imagegen` 用外部工具。出图后自动调 `crop_whitespace` 裁切四周白色留白并加对称 padding，使内容居中 | 图片落盘，文件名与清单 `filename` 一致；内容居中无偏移 |
| 3 清单预检 | `python Write/references/b1-images/scripts/figure_manifest.py check manifest.json` | FAIL 清零（>1MB、非 jpg/png、缺字段、filename 重复、图上文字无出处） |
| 4 批量上传 | `python Write/references/b1-images/scripts/upload_imgs.py --manifest manifest.json --map mmbiz_map.json`（或 `--html` / `--img`） | `mmbiz_map.json`（键为图片 basename，与 `filename` 同名）；封面另用 `python scripts/wx_api.py cover .\cover.png` 取 `media_id` |
| 4.5 回填占位 | `python Write/references/b1-images/scripts/fill_placeholders.py --html <article-wx.html> --map mmbiz_map.json` | 把 A3 直出 HTML 里的 `__MMP__:<filename>` 替换为 mmbiz URL；残留即 FAIL |
| 4.6 体检 | `python Write/references/b1-images/scripts/check_urls.py --html <article-wx.html> --map mmbiz_map.json` | mmbiz URL 全活 + 无残留 `__MMP__` 占位 + 无漏传 |
（原第 5 步 `scan` 子命令已删：清单一说三张、正文只排两张的漏排，改由 B3 验收包的
图数一致性子闸核——原设计里 scan 要先有 B2 的 HTML 才能跑，与「先传图后排版」
构成环形依赖；收到验收层后 B1→B2→B3 单向。另备可选的 `figure_manifest.py verify`
做清单↔map↔HTML 交叉核验：`--map` 档传图后即可跑、不依赖 B2，`--html` 档在 B2 之后跑，
两档均不进强制顺序。）

第 3 步在第 4 步之前，是因为 `upload_imgs.py` 的尺寸预检虽然也会拦超限图，但那时你已经
为构图和生成花了时间；清单层先拦，成本更低。

## 脚本分工

| 脚本（均在 `Write/references/b1-images/scripts/`） | 产出物 |
|---|---|
| `figure_plan.py` | 分层配图需求校验（`check`）与需求→manifest 展开（`from-ledger`）；读 A3 逻辑台账各层结论决定配什么图 |
| `figure_manifest.py` | 清单骨架、清单预检报告、清单/正文一致性核验、mermaid 目录转清单条目 |
| `render_mermaid.py` | Mermaid PNG（浏览器 fallback：msedge → chrome → Chromium；本地 runtime 优先、离线可用；出图后 `crop_whitespace` 自动裁切居中） |
| `gen_table.py` | 表格/结构化内容 → PNG（spec JSON 驱动；微信正文不渲染 `<table>`，表格一律截图；出图后 `crop_whitespace` 自动裁切居中） |
| `gen_cover.py` | 封面 PNG（深蓝 `#1F3864` + 金 `#B08D3E`，四种 `--pattern`；可选 `--title/--subtitle`） |
| `compress_img.py` | 把 >1MB 的正文图压到 1MB 以下（JPEG 降质量 / PNG 量化 + 降分辨率） |
| `upload_imgs.py` | mmbiz URL 列表与 `--map` 映射；上传前逐张尺寸预检 |
| `check_urls.py` | mmbiz URL 批量可达性体检 + 正文引用与 map 的漏传核对 + 残留 `__MMP__` 占位清零 |
| `fill_placeholders.py` | A3 直出 HTML 的 `__MMP__:<filename>` 占位回填为 mmbiz URL（上传与回填职责分离） |

接口层只由 `upload_imgs.py` 复用根 `scripts/wx_api.py` 的 `get_token` / `multipart_upload` /
`http_json`（import 期上溯定位 wx_api.py，找不到即明确报错，不重复实现）；`gen_table.py`
复用 `render_mermaid.py` 的 `launch_browser`（浏览器 fallback 链的唯一实现，B3 的
`qa_mobile.py` 同样复用它）；其余脚本（`gen_cover.py` / `compress_img.py` / `check_urls.py`）
不依赖凭据，纯本地渲染 / 处理 / 只读体检。

## 配图的三条禁令（出处标明，不在此重新论证）

1. **不用 SVG/HTML 代替位图交付**，**图上有错字改提示词重新生成，禁止用 Pillow/SVG 在位图上
   盖字修补**——借自 `baoyu-article-illustrator` 技能的纪律，落在
   `figure_manifest.py check` 的 WARN 文案里。
2. **禁止先写本地图片路径再事后替换**——见 `image-upload-interfaces.md`「一步到位原则」。
   （「不为用组件而补写内容」属 B2 排版阶段的组件选用纪律，见
   `../b2-typeset/theme-default.md`，B1 不需要它。）



## 配图工具选型（按 `tool` 字段路由）

不同图用不同渲染器，不要一刀切用 Mermaid：

| 图的类型 | `tool` | 渲染器 | 说明 |
|---|---|---|---|
| 流程图、状态机、架构图 | `mermaid` | `render_mermaid.py` | 文本源码可 diff，`.mmd` 可版本控制 |
| 思维导图、时间线 | `mermaid` | `render_mermaid.py` | mermaid mindmap/timeline 语法原生支持 |
| **表格、对照表、分录块** | `screenshot` | `gen_table.py` | 微信不渲染 `<table>`；Mermaid 表格语法弱（不支持合并单元格/多行换行），须 HTML 截图 |
| 饼图、柱状图等图表 | `screenshot` | 外部图表库出图 + 截图 | Mermaid 无原生图表能力 |
| 需要照片/插画感的配图 | `imagegen` | 外部生图工具 | 图上文字须一次画对，禁止事后盖字修补 |
| 封面 | （走 `gen_cover.py`） | `gen_cover.py` | 大卡 900×383 展示最佳，建议 2048×880 |

图下均配图注（排版层的 caption 组件，即 theme-default 组件 8，编号规则由
`Write/references/b2-typeset/scripts/typeset_plan.py audit` 核）。

示意图/表格渲染后、封面生成后，正文图统一 `uploadimg` 换 mmbiz URL 再放入正文。
封面可用 `gen_cover.py --title/--subtitle` 原生叠字（属正当的原生绘制，非「盖字修补」；
不传即纯几何无字，与旧版一致）。

## 与相邻流程

- 内容轨道没成稿前不要开始配图：`position` 字段要写到「第三节 段2 之后」，
  稿子结构还在变时填不了。
- 图片 URL 会不会掉、掉几张，最终由 B5 回读的 mmbiz 计数把关
  （`Write/references/b5-readback/readback-verification.md`）。
