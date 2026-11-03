# A2 结构：章节树与六种推进法

A2 的唯一交付物是 `outline.json`，出口判据是**每个章节都能回指一个分论点、章节间关系逐条标注、字数预算有数**。
结构不是排版，也不是写作技巧——它是**论证的承载架**。架子搭错，A3 的素材会填进错误的位置，A4 的逻辑图会长出断头路。

```bash
python Write/references/a2-structure/scripts/outline_check.py init -o outline.json
python Write/references/a2-structure/scripts/outline_check.py check outline.json --thesis thesis.json
python Write/references/a2-structure/scripts/outline_check.py graph outline.json -o outline.mmd
```

`check --thesis` 会核对 `claim_ref` 是否都能在 `thesis.json` 的 `subclaims` 里找到对应项。这是 A1→A2 唯一的接口。

## 一、六种推进法（`method`）

研究性专业文章只有一个体裁，但**推进路径**有六条。选哪条取决于你要论证的东西的形状，不取决于个人喜好。

### 1. 金字塔法（`pyramid`）

把结论放最上面，问"凭什么这么说"，答案就是几个分论点；再问"凭什么这么说"，答案就是证据。

- **规则**：分论点之间**相互独立、全部覆盖**（MECE）。写"留抵退税兑现慢"，分论点可以是审批环节多、部门间信息不互通、资金层层拨付——三条并列，没有重叠。
- **关键**：每个分论点都要能回答"所以呢"，都能指回结论。指向别处的分论点删掉。
- **适合**：`理论分析`。观点先立，再层层举证。

### 2. 问题解法式（`problem-solution`）

背景 → 问题 → 原因 → 对策。

| 段落角色 | 内容 |
|---|---|
| 政策背景 | 规则变化的时间、文件、口径 |
| 条文及适用范围 | 谁适用、什么情形适用、例外 |
| 实务操作指引 | 一步一步怎么做 |
| 合规风险提示 | 哪里会错、错了什么后果 |

- **适合**：`政策解读`、`操作指引`。这是本领域最常用的结构。
- **优点**：读者读完知道"是什么、为什么、怎么办"。

### 3. 案例驱动法（`case-driven`）

案件详情 → 企业端分析 → 征管/裁判端分析 → 防控建议或政策反思。

- 案例只当引子，分析才是重点。案情写完必须马上转入规则层面的讨论，否则变成故事会。
- **进阶**：多个案例做**类型化**——"为诈骗团伙开发定制话术软件的"与"只提供通用服务器租赁的"，主观罪过不能等同。这是裁判文书类文章常用的"小切口、深纵深"。
- **适合**：`案例分析`。

### 4. 倒金字塔（`inverted-pyramid`）

第一段直接放最重要的三个变化/结论，后面按重要性递减排列。

- **适合**：财经分析、行业研究、数据解读。公众号读者常只看前几屏，结论必须最前面。
- **补充**：每 500 字左右加一个阶段性小结，帮读者回过神来。

### 5. SCQA（`scqa`）

- **S（情境）**：同行都熟悉的现状
- **C（冲突）**：但出现了反常
- **Q（问题）**：为什么会这样
- **A（答案）**：你的结论

例子：「增值税法已经实施，多数企业按合同日期处理跨期业务（情境），结果多缴了税（冲突），问题出在哪（问题），出在纳税义务发生时点的判断上（答案）。」

- **适合**：开头难写、或结论反直觉的文章。

### 6. 争议式（`controversy`）

先写"多数观点认为……"，逐条反驳，最后亮出自己的观点。

- **要求**：反面观点要选**最强的版本**。挑一个漏洞百出的说法去打，同行立刻看穿。
- **适合**：`理论分析` 里存在实质争点的题目。

## 二、按推进方向分类（`flow`）

推进法决定"章节怎么排"，推进方向决定"章节之间靠什么连接"：

| `flow` | 推进方式 | 适合 |
|---|---|---|
| `递进式` | 一层比一层深，后者依赖前者 | 理论分析、学术型 |
| `并列式` | 几个分论点地位相同 | 操作指引、多案例对比 |
| `总分式` | 先给结论，再分点展开 | 观点型 |
| `对比式` | 新旧对比、横向对比同行 | 政策变化、行业研究 |

`flow` 与 `method` 不冲突：`pyramid` + `并列式` 是常见的组合（结论在上，三个并列分论点各自举证）。

## 三、按体裁的标准框架（`category` → 推荐 `method`）

`outline_check.py check` 会比对 `thesis.json` 的 `category` 与 `outline.json` 的 `method`：不匹配只报 **WARNING**，不拦。

| 体裁 | 推荐 method | 标准章节序列 |
|---|---|---|
| `政策解读` | `problem-solution` | 背景 → 适用范围 → 实务指引 → 风险提示 |
| `案例分析` | `case-driven` | 案情 → 多角度分析 → 防控建议 |
| `操作指引` | `problem-solution` | 痛点 → 合规路径（附风险对比）→ 操作清单 |
| `理论分析` | `pyramid` / `controversy` | 问题提出 → 文献（按主题分，不按作者分）→ 方法 → 分析 → 讨论 → 结论 |

财经分析类题目归 `政策解读` 或 `操作指引`，用 `inverted-pyramid`：最重要的变化放前面 → 数据论证 → 分角色给建议。

## 四、`outline.json` 字段全表

```json
{
  "thesis_ref": "thesis.json",
  "method": "problem-solution",
  "flow": "递进式",
  "word_budget": 3000,
  "sections": [
    {
      "id": "s1",
      "heading": "研发支出的阶段划分在准则里怎么落",
      "claim_ref": "s1",
      "role": "条文及适用范围",
      "words": 700,
      "evidence_kinds": ["准则原文", "应用指南"]
    }
  ],
  "relations": [
    {"from": "s1", "to": "s2", "type": "递进", "note": "先定阶段，才能谈资本化条件"}
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `method` | 是 | 六选一：`pyramid` / `problem-solution` / `case-driven` / `inverted-pyramid` / `scqa` / `controversy` |
| `flow` | 是 | 四选一：`递进式` / `并列式` / `总分式` / `对比式` |
| `word_budget` | 是 | 目标字数；各 `sections[].words` 之和与它的偏差 ≤ 20% |
| `sections[].id` | 是 | `s1`、`s2`… 唯一 |
| `sections[].heading` | 是 | 章节标题，写**内容本身**，不写"抽丝剥茧之道"这类对仗 |
| `sections[].claim_ref` | 是 | 回指 `thesis.json` 的 `subclaims[].id`；`null` 只允许用于前后呼应性的过渡节，且全篇最多 1 个 |
| `sections[].role` | 是 | 该节在论证里干什么（背景/条文/分析/反驳/建议/结论…） |
| `sections[].words` | 是 | 字数预算，正整数 |
| `sections[].evidence_kinds` | 否 | 这节预计要什么类型的材料，A3 按它派名单 |
| `relations[].type` | 是 | 五选一：`递进` / `并列` / `因果` / `回扣主线` / `依赖` |

## 五、起承转合与过渡

`relations` 里每条边都要写 `note`，说清"前一节给后一节交了什么"。这是研究性文章最容易被读者察觉的地方——章节之间没有交接，读起来就是一叠互不相干的笔记。

三条硬规矩：

1. **每节开头接住上一节的结论**，不接住就补一句过渡，或者把这一节挪走。
2. **回扣主线**至少出现一次（通常在中段和结尾），把读者拉回核心问题。
3. **过渡不用路标**。"首先/其次/最后""综上所述"这些是模型腔，见 A5 的禁令。交接靠内容：上一节讲完"阶段划分"，下一节直接问"划完阶段，资本化条件怎么判"。

## 六、`check` 的判据

- **ERROR**：`method`/`flow` 不在枚举内；`sections` 为空或不足 2 节；`sections[].id` 重复；有节缺 `heading`/`role`/`words`；`words` 非正整数；各节字数之和与 `word_budget` 偏差 > 20%；`claim_ref` 非空的节对应的 id 在 `thesis.json` 的 `subclaims` 里找不到；`relations` 引用了不存在的节 id；`relations[].type` 不在枚举内；`relations[].note` 为空；`claim_ref=null` 的节超过 1 个；章节标题命中 A5 禁令里的对仗词或空洞词。
- **WARNING**：`method` 与 `category` 不匹配；没有 `回扣主线` 类型的边；某节 `words` 占比 > 45%（单节吃掉全文一半，通常该拆）。

退出码：`0` 无 ERROR；`1` 有 ERROR；`2` 用法错误或文件不存在。

## 七、导出章节图

```bash
python Write/references/a2-structure/scripts/outline_check.py graph outline.json -o outline.mmd
```

导出 Mermaid `graph TD`，边上的标签就是 `relations[].type`。这张图是 A4 逻辑图的骨架——A4 在它下面继续挂段落、句子、证据三层关系，所以**章节 id 必须稳定**，A4 的 `logic.json` 用同一套 id 引用。

配图需要时，这张 mmd 可直接交 `Write/references/b1-images/scripts/render_mermaid.py` 渲染（B1 阶段执行）。

## 八、出口

`outline_check.py check outline.json --thesis thesis.json` 退出码 0。之后进 `Write/references/a3-materials/`。

改判据要同步 `tests/test_a_track_gates.py`，并跑 `python tests/run_all.py`。
