---
name: static-gate-rules
summary: B3 验收阶段静态子闸的规则源、ERROR/WARNING 口径、批量闸用法，以及与推送闸共用同一套判据的约束。
---

# 静态合规子闸

## 规则源只有一份

`Write/references/b3-acceptance/scripts/validate_wx_html.py` 是微信兼容红线的**唯一实现**：
检查禁用标签/属性/样式、代码块结构、图片域名、转义、禁用词与半角标点，并核对产物是否为
纯 `<section>` 片段。根 `scripts/wx_draft_push.py` 的推送闸加载的就是它的 `validate()`——
两处必须同一套判据，所以推送闸不需要、也不允许再有一套自己的规则。

判据表的原始口径在 `references/gotchas.md` D 组；词表（`BANNED_WORDS` /
`AI_FLAVOR_PHRASES`）的维护规则在 `Write/references/a5-draft/de-ai-playbook.md` 第七节，
与 `Write/references/a5-draft/scripts/check_prose.py` 的硬禁词表必须同一轮更新。

退出码：`1` = 有 ERROR（会被微信过滤或显示异常，必须修复）；`0` = 通过（WARNING 建议人工确认）。

```bash
python Write/references/b3-acceptance/scripts/validate_wx_html.py <file.html>
python Write/references/b3-acceptance/scripts/validate_wx_html.py --stdin < file.html
```

## 批量闸 `static_check.py`

`Write/references/b3-acceptance/scripts/static_check.py` **不重新实现任何判据**，只委托同目录的
`validate()`，管单文件校验器不管的三件事：批量（一次扫一个目录/多份 HTML）、门禁
（把「ERROR=0」变成可接进流水线的一条命令，非零即断）、留痕（机器可读 JSON，供验收包与交付说明引用）。

```bash
python Write/references/b3-acceptance/scripts/static_check.py <文件或目录> [...] \
    [--json out.json] [--strict] [--skip-preview] [--validate-dir <目录>]
```

- `--strict`：WARNING 也判失败。系列稿件交付、对外发布建议开。
- `--skip-preview`：跳过 `*_预览.html`（同目录 `wrap_preview.py` 产出的外壳文件不参与校验）。
- 空扫（一份 HTML 都没匹配到）**判 FAIL**——「没有文件所以全部通过」是假绿。
- 找不到 `validate_wx_html.py` 时明确报错退出，**绝不静默降级为「视为通过」**。
  这条是本仓库反复踩过的坑：脚本被拷走、路径层级变了，静默通过比报错危险得多。

退出码：`0` 全部 ERROR=0；`1` 至少一份有 ERROR（`--strict` 下含 WARNING）；`2` 用法错误。

## ERROR / WARNING 的分界

ERROR 的判据是「微信端一定会出问题」：`<style>` 被剥离、`class`/`id` 被剥、`<pre>` 折叠空格、
正文图不是 mmbiz、`display:table` 伪表格手机端堆叠、文档外壳、禁用词与半角标点。
WARNING 是「可能没问题，但需要人看一眼」：字数、段落长度、启发式检出的 AI 味句式。

`--strict` 把 WARNING 也升级为失败，用在对外发布；平时不强制，是为了避免
「为了让工具变绿而改内容」这种反向动机。

## 与其他两道子闸的分工

渲染子闸查真机像素，人工子闸查观感与内容判断。静态校验只看标签与 style 属性，
抓不到「`display:table` 在微信端堆叠」这类渲染层问题——那要起浏览器才知道；
渲染子闸只看像素与 computed style，抓不到禁用词与句式——那在静态子闸。三道子闸判据互不覆盖，
不能因为跑了一道就认为另一道可以省。

## 测试

`tests/test_validate_rules.py` 逐条命中 16 条 ERROR 规则；改判据后必跑 `python tests/run_all.py`。
