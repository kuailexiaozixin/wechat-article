# B3 验收：三子闸合一（静态 · 渲染 · 人工）

## 为什么三道合成一个阶段

静态校验、真机渲染、人工抽查对的是**同一份 HTML**，合起来才有「这份稿子可以推」这一个结论。
拆成三个独立编号阶段时出过真实问题：旧七阶段布局里推送阶段的 `--b5/--b3/--b4` 都是可选参数，
**漏传就绕过**，三道闸变成三道建议。合并后 B4 推送只认一个输入——`acceptance.json`，
缺了就推不了，可选性问题从接口上消失。

三道子闸的判据**互不覆盖**，这也是必须三条都过的原因：

| 子闸 | 抓什么 | 抓不到什么 |
|---|---|---|
| 静态 | 标签/属性/样式红线、禁用词、标点（规则唯一权威：`wx-html-redlines.md`） | 真机像素；窄视口会掩盖 `display:table` 堆叠 |
| 渲染 | 390px 横向溢出、`display:table*`/grid、坏图、整页截图 | 禁用词与句式（文字层） |
| 人工 | 内容对不对、观感好不好（六项核对单） | 任何可机检项——所以它不替代前两道 |

## 四个子闸与唯一编排器

```bash
python write/references/b3-acceptance/scripts/acceptance_pack.py \
    --html article.html --manifest manifest.json --signoff article_B5.json \
    [-o article_acceptance.json]
```

`acceptance_pack.py` **不重新实现判据**，四个子项各自委托本目录既有实现：

- **静态**：`validate_wx_html.py` 的 `validate()`（与 `static_check.py` 同一调用方式）。
  批量场景（多份 HTML）仍用 `static_check.py`，单篇验收走 pack。
- **渲染**：`qa_mobile.py`（390px 溢出 / `display:table*`·grid / 坏图 / 整页截图；
  环境预检与截图核对用 `render_gate.py`）。判据细节见 `render-gate-rules.md`。
- **人工**：`manual_signoff.py` 的签字记录 + `wrap_preview.py` 的本地预览。
  六项核对单与拒签规则见 `manual-signoff-checklist.md`。
- **图数一致性**：HTML 内 mmbiz 引用数 == B1 清单正文图数（`kind: cover` 不计）。
  取代原 B1 的 `scan` 子命令——原设计里「先传图后排版」与「scan 要先有 HTML」构成环形依赖，
  收到验收层后 B1→B2→B3 单向。

## 指纹冻结（验收包的出口）

pack 对 HTML **原始字节**算 `sha256` 写入验收包。后续链条：

- **B4 推送**：推送前重算当前 HTML 哈希，与验收包记录不一致即拒绝——防止
  「验收的是 A 版、推送的是 B 版」。
- **B5 回读**：推送记录里的哈希与当前源文件比对，取代 mtime 判断「改了没重推」
  （mtime 在复制文件、换机器时不可信）。

## overall 语义与退出码（三态，不许含糊）

| overall | 含义 | 退出码 |
|---|---|---|
| `PASS` | 四子项全绿，**渲染子闸必须真跑过** | 0 |
| `PENDING` | 渲染子闸因环境不满足未跑，或未提供签字/清单 | 2 |
| `FAIL` | 任一子闸不合格 | 1 |

**PENDING 不算通过**：本机无 playwright（按本机规则不装、严禁装新 Chrome/Chromium）时，
渲染子闸永远 PENDING，此时不许推送——比把 SKIP 混在测试输出里诚实。
补环境的口径：playwright 按本机 uv 规则装到 `D:\Python`，不跑 `playwright install`，
不安装任何新的 Chrome/Chromium（fallback 链用系统 Edge/Chrome）。

## 交付链退出码语义（B3/B4/B5 统一）

三阶段编排器都用 0/1/2 三态，且 **2 一律表示「没跑成 / 前置不满足」，不是「内容不合格」**——
避免把环境问题读成内容问题，去改一份本来没问题的稿子。

| 阶段 | 工具 | 0 | 1 | 2 |
|---|---|---|---|---|
| B3 验收 | `acceptance_pack.py` | PASS | 有子闸 FAIL | PENDING（渲染子闸未跑）或用法/环境错误 |
| B4 推送 | `push_gate.py` | 放行 / 推送成功 | 前置未过或推送失败 | 用法/环境错误（找不到根脚本等） |
| B5 回读 | `readback_check.py` | 全部 PASS | 有 FAIL（须回 B2 改稿重推） | 前置不满足（记录缺失 / 源码哈希不符 / 无凭据） |

各子闸脚本（`validate_wx_html.py` / `qa_mobile.py` / `render_gate.py` / `static_check.py` /
`manual_signoff.py`）的退出码在各自文档另述；本表只统一三阶段编排器的口径。

## 词表维护点

`validate_wx_html.py` 的 `BANNED_WORDS`/`AI_FLAVOR_PHRASES`/`PROCESS_TRACE_RULES` 是**全仓唯一一份**
禁词与 AI 味判据：A 轨写作纪律与 B3 静态红线共用它，根 `scripts/wx_draft_push.py` 推送闸加载的
也是同一个 `validate()`。改词表只改这一处，改完跑 `python tests/run_all.py`；别处只引不改。
`tests/test_caption_gate.py` 核制作痕迹词在 `validate_wx_html.py` 与 `check_captions.py` 两侧都仍在，
删除共享词即报红——这就是「同轮更新」的可执行化。
