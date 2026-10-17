---
name: write
description: '公众号文章写作与微信兼容 HTML 排版：按写作纪律成文（去 AI 味、不虚构、材料门槛），产出单一 <section> 正文片段与内联样式，再由三支脚本逐级验收——散文硬禁令、排版红线静态校验、390px 真机渲染。当用户要求"写一篇公众号文章""做公众号排版""这段文字 AI 味重""换个不那么死的结构"时使用。推送草稿箱属 draft/，图片换 URL 属 materials/，本技能不出网络请求。'
---

# 公众号文章写作与排版（Write）

**产出物 = 单一 HTML 文件（纯 `<section>` 正文片段）**：样式全部内联、无外部资源、正文图为 `mmbiz.qpic.cn` URL，可直接推送草稿箱。推送不属于本子技能（`draft/`），图片上传不属于本子技能（`materials/`）。

## 一、规范在哪（本文只留流程，规则不重复）

| 要解决的事 | 文件 |
|---|---|
| 内容能不能写、怎么写、去 AI 味、草稿标题/摘要约束 | `write/references/writing-discipline.md`（配套 `write/references/de-ai-measures.md`、`write/references/human-writing-nonfiction.md`） |
| 微信兼容红线、代码块与条目卡片模板、主题资产用法、配图与渲染 | `write/references/wx-html-rules.md`（样式单一来源 `write/references/theme-default.md`） |

## 二、工作流主线（按序执行，每步有产出物）

| 步 | 动作 | 命令 | 产出物 / 出口 |
|---|---|---|---|
| 1 | 素材准备 | 读仓库源码/文档取真实代码片段；有示意图则渲染 | 代码片段清单；`<name>.png`（Mermaid 经 `render_mermaid.py`） |
| 2 | 配图上传 | `python materials/scripts/upload_imgs.py --html <草稿.html> --map mmbiz_map.json`（或先传图再引用） | `mmbiz_map.json`（键为图片 basename）；>1MB 图在此步即 FAIL |
| 3 | 成文（纯文本） | 按 `write/references/writing-discipline.md` 写稿，再 `python write/scripts/check_prose.py <稿件.md>` | 硬禁令清零的纯文本稿 |
| 4 | 排版 | `python write/scripts/build_blocks.py blocks.json -o <article.html>`（或手写，样式取 `write/references/theme-default.md`） | `<article.html>`，图片直接写 mmbiz URL |
| 5 | 静态合规 | `python write/scripts/validate_wx_html.py <article.html>` | ERROR=0；WARNING 逐项确认 |
| 6 | 移动端渲染 | `python write/scripts/qa_mobile.py <article.html>` | 390px 无横向溢出、无 `display:table*`/grid；整页截图 `<article>_qa390.png` |
| 7 | 人工自查 | `python write/scripts/wrap_preview.py <article.html>` → 浏览器打开预览页 | 观感确认（外壳文件不参与校验） |
| 8 | 推送 | `python scripts/wx_draft_push.py --html <article.html> --title "<短句>" --digest "<摘要>" [--cover <img>]`（全能力版走 `scripts/wx_api.py draft-add`） | `DRAFT_OK media_id:`；推送脚本内置第 5 步校验，ERROR>0 直接拒推 |
| 9 | 回读核验 | `python scripts/check_draft.py "<media_id>" --source <article.html> [--expect-imgs N]` | 标题/摘要/封面/图数/代码块结构 + **正文与源稿一致**逐项 PASS；FAIL 即修复后 `draft-update` 重推 |

跨篇重复检测（系列文章）在第 5 步前后各跑一次：`python write/scripts/check_duplicates.py <成品目录> [--min-len 40] [--threshold 0.8]`。

## 三、闸口顺序（不得调换）

`check_prose`（文字）→ `validate_wx_html`（静态合规）→ `qa_mobile`（渲染）→ 推送（内置 validate 硬拦）→ `check_draft --source`（回读 + 源一致性）。

前三道各自的判据互不覆盖：静态校验只看标签与 style 属性，抓不到「`display:table` 在微信端堆叠」这类渲染层问题；渲染验收只看像素与 computed style，抓不到禁用词与句式。第 9 步的 `--source` 比对能抓住最后一类事故：改了源文件忘了重推，草稿里还是旧内容。

## 四、人工抽查项（脚本查不到的）

- [ ] 金额/编号类演示数据已标注「教学示例/演示数据」
- [ ] 代码片段与仓库源码逐行一致（抽查关键行）
- [ ] `--title` 取正文标题的短句、与正文标题有差异；字节与字符上限见 `draft/SKILL.md`「参数约束」
- [ ] 封面已准备且与账号内已推过的篇目不同
- [ ] `qa_mobile.py` 截图在手机宽度下观感可接受
- [ ] 推送后附「发布前必设四项」提醒（清单与固定话术见 `draft/SKILL.md`「制作→预览工作流」第 4 步）

## 五、脚本清单

| 脚本 | 产出物 |
|---|---|
| `write/scripts/check_prose.py` | 成稿纯文本硬禁令报告（翻案句及变形、黑话、硬停词、模型路标、破折号/提示性冒号） |
| `write/scripts/validate_wx_html.py` | wx 合规 ERROR/WARNING 清单 + AI 味启发式（判据表见 `references/gotchas.md` D 组） |
| `write/scripts/qa_mobile.py` | 390px 渲染验收结果 + 整页截图（浏览器 fallback：msedge→chrome→Chromium） |
| `write/scripts/build_blocks.py` | 与 `write/references/theme-default.md` 逐字一致的正文片段 |
| `write/scripts/render_mermaid.py` | Mermaid PNG |
| `write/scripts/wrap_preview.py` | 本地预览页（可一键复制进编辑器） |
| `write/scripts/check_duplicates.py` | 跨篇重复段落报告 |

判据测试在仓库根 `tests/`：`python tests/run_all.py` 一次跑完（改判据或改文档后必跑）。
