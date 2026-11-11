---
name: readback-verification
summary: B5 推送后回读核验：判据委托关系、media_id 留痕链、哈希比对取代 mtime、WAF 绕行后的重跑；判据只有一份，来自根 scripts/check_draft.py。
---

# B5 回读核验

推送命令成功不等于内容进对了。B5 只做一件事：**从平台把这篇草稿读回来，逐字核对**。
`draft-add` 返回 `media_id` 只是「接口收下了请求」，正文是否被改、图是否掉、标题是否被截，
都要靠回读才能知道。

## 判据清单（不得省略，自动执行）

由 `scripts/check_draft.py <media_id> --source <article.html> [--expect-imgs N] [--json]` 自动断言：

- `--title` ≤ 64 字节、`--digest` ≤ 120 字符
- 封面 `thumb_media_id` 非空
- 正文无 `<pre>`、无 `<style>`、无 `display:table*` 伪表格
- mmbiz 图数 = 预期 N；未显式给 N 时按源文件中的 mmbiz 引用计数得出
- 无本地图片路径
- **正文与源文件逐字比对**：把回读 content 与本地源 HTML 归一化（统一换行、剥 mmbiz 查询参数、
  去标签间与连续空白）后要求相等

API 推送路径微信不清洗正文，所以**不相等即「推的不是这份文件」**——改了源文件没重推，
这一步必 FAIL。输出逐项 `[PASS]/[FAIL]`，FAIL 即修复后 `draft-update`（或 delete+add）重推。

回读层**不检查图片能否真的加载**（`naturalWidth==0` 的坏图）——那是 B3 渲染子闸的判据，
回读只数 mmbiz 引用次数。URL 存在但已失效这类问题，B3 关不掉、B5 看不见，
要靠 `../b1-images/image-upload-interfaces.md`「URL 失效处理」的定期抽查。

## `Write/references/b5-readback/scripts/readback_check.py` 补的三件事

本脚本**不重新实现任何回读判据**，逐条比对全部委托根 `scripts/check_draft.py --json`，
规则源只有一份。它只管 check_draft 覆盖不到的留痕：

1. **media_id 不靠人工复制**：默认从 B4 `push_gate.py` 落盘的 push.json
   （`{"media_id","html","html_sha256","acceptance","overall","pushed_at"}`）读取，`--source` 也顺带从同一记录取。
   `--media-id` 仅供排障临时使用。
2. **拦「改了没重推」——哈希优先，mtime 兜底**：推送记录里的 `html_sha256` 与当前源文件
   sha256 比对，不一致直接 FAIL 并 **exit 2**，不发这次接口调用——这次比对注定不一致，
   省下频率额度。旧格式记录（无哈希字段）退回 mtime 比较，但**复制文件、换机器时 mtime
   不可信**，属已知局限；建议用 B4 重推一次以升级记录格式。
3. **图数从 B1 清单来**：`--manifest` 时按清单里的**正文图**条数算 `--expect-imgs`
   （`kind: "cover"` 不计，封面走 media_id 不写进正文）。避免「少排了一张图，但回读只校验
   图数 > 0」这种漏检。

```bash
python Write/references/b5-readback/scripts/readback_check.py --record push.json
python Write/references/b5-readback/scripts/readback_check.py --record push.json --manifest manifest.json
python Write/references/b5-readback/scripts/readback_check.py --record push.json --check-urls
python Write/references/b5-readback/scripts/readback_check.py --media-id MEDIA_ID --source article.html --json
```

`--check-urls` 在回读之外追加一次 mmbiz 图 URL 可达性体检（HTTP GET），**仅警示、不改变退出码**，
补上「回读只数引用数、看不到 URL 已失效」这一环。

## 退出码（FAIL 回哪一步，两条分支）

`0` 全部 PASS；`1` 有 FAIL（**见下表，按 FAIL 类型回不同步**）；
`2` 前置条件不满足（记录缺失、源码哈希不符、找不到 check_draft.py、凭据缺失）。
**2 与 1 必须分开**：环境问题报成内容不合格，会让人去改一份本来没问题的稿子。
（三阶段退出码统一口径见 `../b3-acceptance/acceptance-gates.md`「交付链退出码语义」。）

| FAIL 类型 | 怎么修 | 回哪一步 |
|---|---|---|
| 逐字比对不一致（check_draft 的正文字段 FAIL） | 改了 HTML，需重新走「验收→推送→回读」 | **B2**（改稿）→ B3 重验收 → B4 重推 → B5 重跑 |
| 源码哈希不符（pre 项「源码未重推」FAIL，exit 2） | 验/推之后改过稿但没重推；稿本身没问题，重推即可 | 直接 **B4 重推**（B2 不用动）→ B5 重跑 |
| mmbiz 图数/本地路径 FAIL | 图没回填或清单虚报 | **B1 回填 + B2 排版** → B3 → B4 → B5 |

**旧 media_id 已失效（WAF 绕行后）**：推送记录里的 `media_id_history` 记录变更轨迹，
当前 `media_id` 字段始终是最末的新 id。若手上有绕行之前的旧 id，回读只会 40007——
对新 id 重跑，旧 id 的结果不算数。

## 与相邻阶段的边界

- 推送本身、参数上限、WAF 501 绕行、发布前必设四项 → `../b4-push/draft-push-parameters.md`。
- 图片 URL 与清单 → `../b1-images/image-upload-interfaces.md`、`../b1-images/figure-manifest-spec.md`。
- 回读 FAIL 之后：按上方「退出码（FAIL 回哪一步，两条分支）」表回对应步——
  逐字不符回 B2 改稿、哈希不符直接 B4 重推、图数不符回 B1 回填 + B2 排版；
  重走「B3 重验收 → B4 重推 → 再跑一次 B5」。若中途触发过 WAF 绕行，`media_id` 已变，
  必须对新 id 重跑，旧 id 的结果不算数。

## 实测记录

本机凭据 + 不存在的 media_id 跑通到平台层，返回 `40007 invalid media_id`，
说明委托链（token → draft/get → 逐项断言）可用；`--expect-imgs` 从清单取数、
「源码未重推」哈希拦截、记录缺 `media_id` 拒绝等分支均已正反例验证。
