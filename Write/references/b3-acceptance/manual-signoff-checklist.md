---
name: manual-signoff-checklist
summary: B3 验收阶段人工子闸的六项核对单、签字留痕机制与拒绝空签的判据；预览页外壳不参与校验，签字记录是 B4 推送闸的放行依据。
---

# 人工自查子闸与签字留痕

静态与渲染两道子闸只覆盖可测项。下面这几条脚本查不到，只有人看过才能签——
**不签字就没有 B4 推送闸的放行依据**。

## 两件事分开

- `Write/references/b3-acceptance/scripts/wrap_preview.py <article.html>`：把已校验的 HTML 包成本地
  预览页，供浏览器打开看观感、一键复制进编辑器。**预览页是外壳文件，不参与校验**——它带
  `<style>`/文档外壳是给本地浏览器用的，微信侧的交付物仍是里面那份 `<section>` 片段。
  B3 批量闸的 `--skip-preview` 就是为跳过这类文件而存在的。
- `Write/references/b3-acceptance/scripts/manual_signoff.py`：把核对单变成可留痕的记录。

## 六项核对单

```bash
python Write/references/b3-acceptance/scripts/manual_signoff.py checklist [-o checklist.md]
```

- [ ] 金额/编号类演示数据已标注「教学示例/演示数据」
- [ ] 代码片段与仓库源码逐行一致（抽查关键行）
- [ ] `--title` 取正文标题的短句、与正文标题有差异；字节与字符上限见
      `Write/references/b4-push/draft-push-parameters.md`「参数上限」
- [ ] 封面已准备，且与账号内已推过的篇目不重复
- [ ] `qa_mobile` 整页截图在手机宽度下观感可接受（首屏有完整一句、代码未折断、图居中、无大面积深色块）
- [ ] 推送后需附「发布前必设四项」提醒——清单与固定话术见
      `Write/references/b4-push/draft-push-parameters.md`「推送与预览工作流」第 4 步

第 5 项对应的四件事由渲染子闸 `render_gate.py review` 打印，逐屏核对（它会按整页高度换算成
几个手机屏）。第 3、6 项在 B4 推送，但必须在签字前就看一眼——签完再发现标题超限，等于白签。

## 签字与拒签

```bash
python Write/references/b3-acceptance/scripts/manual_signoff.py record \
    --html <article.html> --qa <article_qa390.png> --note "<看了截图的哪几处、结论是什么>"
python Write/references/b3-acceptance/scripts/manual_signoff.py require --json <article_B5.json>
```

`record` 拒绝空签，三种情况直接 `[FAIL]` 且不留记录：HTML 不存在、390px 截图不存在
（没有截图就没法核对观感）、`--note` 为空。通过则落 `<article>_B5.json`，记
`html` / `qa_screenshot` / `checked_items` / `note` / `signed_at`。

`require` 供 B4 消费：核对记录里有没有非空 `note`、`qa_screenshot` 指向的文件是否还在。
**截图被删掉的旧签字不算在案**——留痕的意义是「当时确实看过这份东西」，文件没了就证明不了。

不接受「口头确认过」。B4 `push_gate.py precheck --html <a.html> --acceptance <json>` 读不到签字记录（或验收包非 PASS）会挡在那里。

## 为什么这一道不做成脚本能查的

这六项的本质是「内容对不对、观感好不好」，需要判断而不是匹配。把它们写成关键词检查会得到
一堆假阳性，进而逼人为了让工具变绿去改内容。所以本道的产出物不是「通过」，
而是**一条可追溯的签字记录**：谁在什么时候、看过哪张截图、结论是什么。
