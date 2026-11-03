# A4 逻辑建模：五层关系图与四类校验

A4 的唯一交付物是 `logic.json`，出口判据是**四类查询全部通过**——无孤证章节、无 warrant 为空的论证、无术语与术语表不一致、与同系列冲突的结论已标 `rebuttal`。

前三步（立意、结构、素材）都是"清单"，这一步把它们连成"图"。清单能回答"我有什么"，图才能回答"这些够不够支撑我说的话"。

```bash
python Write/references/a4-logic/scripts/logic_graph.py init --outline outline.json --materials materials.json -o logic.json
python Write/references/a4-logic/scripts/logic_graph.py check logic.json --thesis thesis.json
python Write/references/a4-logic/scripts/logic_graph.py graph logic.json -o logic.mmd
```

`init` 会把 A2 的章节、A3 的材料自动建成节点与骨架边，你只需要补关系类型和 warrant。

## 一、五层关系（研究性文章的骨架）

研究性专业文章的逻辑不是一层，是**五层嵌套**。每层的节点与边不同，混在一起就查不出问题。

| 层 | 节点 | 边（关系） | 关系类型 | 检查什么 |
|---|---|---|---|---|
| 1 篇章 | 每篇文章 | 前篇 / 后续 / 支撑 / 反驳 / 共用概念 | 篇章关系 | 系列文章之间的结论是否打架 |
| 2 章节 | 每个章节 | 递进 / 并列 / 因果 / 回扣主线 / 依赖 | 结构关系 | 章节顺序是否有依赖倒置 |
| 3 段落 | 每个段落 | 支持 / 反驳 / 转折 / 举例 / 承接 | 段落关系（RST） | 段落是否在原地打转 |
| 4 句子 | 每个句子 | 前提 / 推论 / 证据 / 让步 | 论证关系（Toulmin） | 推论有没有 warrant |
| 5 术语与词汇 | 论点、证据、概念、术语 | 主张—证据—推理桥 / 同义 / 上下位 | 论证与语义关系 | 术语是否前后一致 |

**第 5 层的范围**：本技能落到"**术语一致**"这一件事——`terms` 表列出全篇定义过的术语及其唯一写法，正文出现同义混用（"开发支出"写成"开发费用"）由 `check` 的术语查询发现。词汇搭配的选择交给 A5 的行文规范与词表，不在 `logic.json` 里逐词建图：逐词建图的 JSON 会长到没人愿意维护，维护成本一旦超过收益，这一步就会被跳过，反而什么都没有。

## 二、Toulmin 结构：为什么要 warrant

第 4 层的每条论证边都要写 `warrant`——**把证据和主张连起来的那条前提**。这是研究性文章与评论文章的分水岭。

| 字段 | 含义 | 例子 |
|---|---|---|
| `claim` | 主张 | 样机对外销售应按存货结转 |
| `ground` | 证据（指向 A3 的材料 id） | m08《存货准则》第四条 |
| `warrant` | 推理桥：凭这条证据为什么能得出这个主张 | 第四条要求同时满足"持有目的为出售""可销售状态"两个条件；样机对外销售即满足第一条，且达到可销售状态即满足第二条 |
| `backing` | 支撑 warrant 的东西（可选） | 财政部准则实施问答对"可销售状态"的解释 |
| `rebuttal` | 反例或例外（可选但重要） | 样机仅用于内部测试、不对外销售的，不适用 |

**`warrant` 为空 = 这条论证是断的**。写不出 warrant，通常是两种情况：证据不支撑主张（换证据或改主张），或者你自己也没想清中间那一步（那正是文章最该讲清的地方）。

## 三、四类查询（出口判据）

这四条对应写完后的自查清单，`check` 全部自动执行：

### 查询 1：有没有哪个章节没有支撑它的证据

**按本节自己派的材料判，不按所属分论点判。** 一个分论点可以拆成几节展开，几节共用同一分论点——如果按分论点判，某节的材料一条都没进图，也会因为兄弟节有料而跟着过关，那正是空壳章节藏身的地方。

判据三层：

1. 本节在 `materials.json` 里一条材料都没有 → **ERROR**（这一节不该存在，回 A2）。
2. 本节有材料，但一条都没在 `edges` 里连出去 → **ERROR**（材料存在但没连到主张，等于没用上）。
3. 本节进了图的材料全部来自 `二手概括` 或 `作者推断` → **WARNING**（可能只是过渡或背景，但要确认）。

### 查询 2：有没有论证边 `warrant` 为空

任何缺少 `warrant` 的 `argues` 边都报 ERROR。这是四条里最常命中的。

### 查询 3：有没有术语与术语表不一致

`terms` 表里每个术语有 `canonical`（唯一写法）与 `aliases_ok`（可接受的简称）。`check` 会扫 `statements` 与 `warrant` 文本，发现同一概念用了表外写法就报 ERROR。

**为什么这条重要**：财税法律领域同一个概念在不同文件里叫法不同（"开发支出"与"开发费用"、"资本化"与"予以资本化"）。一篇之内混用，读者会以为是两个东西。

### 查询 4：有没有与同系列冲突的结论没标 `rebuttal`

只在 `series` 有值时才检查。`logic.json` 的 `series_links` 记录与其他篇的关系（前篇/后续/支撑/反驳/共用概念）。声明 `支撑` 但结论方向相反，报 ERROR；声明了 `反驳` 但没在该篇写 `rebuttal` 字段说明冲突点，也报 ERROR。

## 四、`logic.json` 字段全表

```json
{
  "thesis_ref": "thesis.json",
  "outline_ref": "outline.json",
  "materials_ref": "materials.json",
  "series": {"name": "研发支出会计处理", "index": 2},
  "terms": [
    {"term": "开发支出", "canonical": "开发支出", "aliases_ok": ["资本化支出"], 
     "banned": ["开发费用", "开发成本"], "definition": "开发阶段满足资本化条件的支出归集科目"}
  ],
  "nodes": [
    {"id": "n_s1", "kind": "section", "ref": "s1", "text": "准则把研发过程切成研究与开发两段"},
    {"id": "n_c1", "kind": "claim", "ref": "s1", "text": "研发支出须区分研究阶段与开发阶段"},
    {"id": "n_e1", "kind": "evidence", "ref": "m01", "text": "准则第六条第八条原文"}
  ],
  "edges": [
    {"from": "n_c1", "to": "n_s1", "type": "结构", "rel": "依赖", "note": "结论要靠这一节的条文立住"},
    {"from": "n_e1", "to": "n_c1", "type": "论证", "rel": "证据", 
     "warrant": "准则第八条明确要求分期，分期即区分", "backing": "", "rebuttal": ""}
  ],
  "statements": ["正文里会出现的完整句子，供术语一致性扫描使用"],
  "series_links": [
    {"target": "研发支出资本化的时点", "type": "前篇", "conflict": false}
  ]
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `terms[]` | 是（至少 1 条） | 术语表：`term` / `canonical` / `aliases_ok` / `banned` / `definition` |
| `nodes[].id` | 是 | 唯一；建议前缀 `n_` |
| `nodes[].kind` | 是 | `section` / `claim` / `evidence` / `concept` / `paragraph` / `sentence` |
| `nodes[].ref` | 否 | 指向 `sections[].id` / `subclaims[].id` / `materials[].id` |
| `nodes[].text` | 是 | 节点内容；为 `sentence` 时要写完整句子 |
| `edges[].type` | 是 | 五层之一：`篇章` / `结构` / `段落` / `论证` / `语义` |
| `edges[].rel` | 是 | 该层允许的关系（见上表） |
| `edges[].warrant` | `type=论证` 且 `rel=证据/推论` 时必填 | 推理桥 |
| `edges[].rebuttal` | 否 | 例外与反例 |
| `statements[]` | 是（至少 1 条） | 待扫描术语一致性的正文句子 |
| `series_links[]` | 有 `series` 时必填 | 与其他篇的关系 |

## 五、怎么建这张图（实操顺序）

1. **`init` 生成骨架**：章节变 `section` 节点，材料变 `evidence` 节点，立意卡的分论点变 `claim` 节点。
2. **补 `terms` 表**：先列全篇会出现的关键术语，定 canonical 与 banned。这一步花十分钟，能省掉后面通篇改名。
3. **连结构边**：每个 claim 挂到它所属的 section（`type=结构`）。
4. **连论证边**：每条 evidence 连到它支撑的 claim，**这时写 warrant**。写不出来的先标 TODO，`check` 会拦。
5. **补 `statements`**：把准备写进正文的关键句子先列进来（通常是每节的主题句与结论句），术语扫描才有对象。
6. **跑 `check`**，逐条消 ERROR。

## 六、`check` 的判据

- **ERROR**：JSON 结构缺失（`nodes`/`edges`/`terms` 任一为空）；节点 id 重复；`edges` 引用不存在的节点；`type`/`rel` 不在枚举内或组合非法（如 `type=论证` 配 `rel=并列`）；`type=论证` 且 `rel∈{证据,推论}` 而 `warrant` 为空；某章节在 `materials.json` 里没有任何材料，或本节的材料一条都没进 `edges`；`statements` 里出现 `terms[].banned` 的写法；同一概念出现 `banned` 别名；`series_links` 声明 `支撑` 但 `conflict=true`；声明 `反驳` 但缺少 `rebuttal` 文本。
- **WARNING**：某章节只有 `二手概括` 材料支撑；`statements` 少于章节数（句子没列全，术语扫描覆盖不足）；节点没有入边也没有出边（孤立节点）；某条 `claim` 只有一条证据且来源是 `二手概括`。

退出码：`0` 无 ERROR；`1` 有 ERROR；`2` 用法错误或文件不存在。

## 七、导出图

```bash
python Write/references/a4-logic/scripts/logic_graph.py graph logic.json -o logic.mmd
```

导出按层着色的 Mermaid 图。这张图有两个用途：自查时看断头路；需要配图时交 B1 的 `render_mermaid.py` 渲染成文章里的论证结构图。

## 八、出口

`logic_graph.py check logic.json --thesis thesis.json` 退出码 0，四类查询全过。之后进 `Write/references/a5-draft/`。

改判据要同步 `tests/test_a_track_gates.py`，并跑 `python tests/run_all.py`。
