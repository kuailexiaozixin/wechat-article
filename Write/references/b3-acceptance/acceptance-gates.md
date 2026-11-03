# B3 验收：三子闸合一（静态 · 渲染 · 人工）

## 为什么三道合成一个阶段

静态校验、真机渲染、人工抽查对的是**同一份 HTML**，合起来才有「这份稿子可以推」这一个结论。
拆成三个独立编号阶段时出过真实问题：B6 推送的 `--b5/--b3/--b4` 都是可选参数，
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
python Write/references/b3-acceptance/scripts/acceptance_pack.py \
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

## 词表同步（本阶段与 A 轨的唯一交点）

`validate_wx_html.py` 的 `BANNED_WORDS`/`AI_FLAVOR_PHRASES` 与 A 轨 `Write/references/a5-draft/scripts/check_prose.py`
的硬禁词表，维护规则同源（A 轨 `Write/references/a5-draft/de-ai-playbook.md` 第七节：三处词表须同轮更新）。
改词表必须同时改两支脚本并在同一轮跑 `python tests/run_all.py`；两支脚本各自持有词表是
已知债，一致性测试（`test_prose_lexicon_sync.py`）待建——建好后此处更新指向该测试。
