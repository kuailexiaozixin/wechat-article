# -*- coding: utf-8 -*-
"""A4 逻辑建模 · 五层关系图的骨架、四类校验与导出。

子命令：
    init --outline outline.json [--materials materials.json] [--thesis thesis.json] [-o logic.json]
    check <logic.json> [--thesis thesis.json] [--materials materials.json]
    graph <logic.json> [-o logic.mmd]

为什么要有这一步：立意、结构、素材都是清单，清单只能回答「我有什么」，
回答不了「这些够不够支撑我说的话」。四类查询（孤证章节 / 空 warrant /
术语漂移 / 系列冲突未标 rebuttal）是研究性文章最典型的四种塌方，
本脚本把它们变成可执行的口径，判据见同目录 logic-graph-spec.md。

退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误或文件不存在。
"""
import argparse
import io
import json
import os
import sys

NODE_KINDS = ("section", "claim", "evidence", "concept", "paragraph", "sentence")
LAYER_RELS = {
    "篇章": ("前篇", "后续", "支撑", "反驳", "共用概念"),
    "结构": ("递进", "并列", "因果", "回扣主线", "依赖"),
    "段落": ("支持", "反驳", "转折", "举例", "承接"),
    "论证": ("前提", "推论", "证据", "让步"),
    "语义": ("主张", "同义", "上下位"),
}
# 这两类论证边必须写出推理桥，否则论证是断的
NEED_WARRANT = ("证据", "推论")
# 只有这两类来源能独立撑起一个章节
SOLID_SOURCES = ("一手事实", "当事人自述")


def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f), None
    except OSError:
        return None, "读不到文件：%s" % path
    except ValueError as e:
        return None, "不是合法 JSON：%s（%s）" % (path, e)


def cmd_init(args):
    outline, err = load(args.outline)
    if err:
        print("ERR", err)
        return 2
    materials = {"items": []}
    if args.materials:
        materials, err = load(args.materials)
        if err:
            print("ERR", err)
            return 2
    thesis = {"subclaims": [], "series": {}}
    if args.thesis:
        thesis, err = load(args.thesis)
        if err:
            print("ERR", err)
            return 2

    nodes, edges = [], []
    for s in outline.get("sections") or []:
        nodes.append({"id": "n_%s" % s.get("id"), "kind": "section",
                      "ref": s.get("id"), "text": s.get("heading") or ""})
    sub_ids = set()
    for sc in thesis.get("subclaims") or []:
        sub_ids.add(str(sc.get("id")))
        nodes.append({"id": "n_c_%s" % sc.get("id"), "kind": "claim",
                      "ref": sc.get("id"), "text": sc.get("text") or ""})
    # 结构边按 A2 的 claim_ref 连：一节回指哪个分论点，就是哪条 claim 撑它。
    # 多个节回指同一分论点是合法结构（一个分论点分几节展开）。
    for s in outline.get("sections") or []:
        cref = s.get("claim_ref")
        if cref is not None and str(cref) in sub_ids:
            edges.append({"from": "n_c_%s" % cref, "to": "n_%s" % s.get("id"),
                          "type": "结构", "rel": "依赖",
                          "note": "分论点靠这一节立住（A2 的 claim_ref 指向 %s）" % cref})
        else:
            edges.append({"from": "n_%s" % s.get("id"), "to": "n_%s" % s.get("id"),
                          "type": "结构", "rel": "回扣主线",
                          "note": "TODO 这节没有回指分论点，补一条指向它所属分论点的结构边"})
    sec_claim = {s.get("id"): s.get("claim_ref") for s in outline.get("sections") or []}
    for m in materials.get("items") or []:
        if m.get("status") == "dropped":
            continue
        nodes.append({"id": "n_%s" % m.get("id"), "kind": "evidence",
                      "ref": m.get("id"), "text": m.get("claim") or ""})
        # 材料挂到它所在节回指的那个分论点上；warrant 留空，check 会逐条提醒补推理桥。
        cref = sec_claim.get(m.get("section"))
        if cref is not None and str(cref) in sub_ids:
            edges.append({"from": "n_%s" % m.get("id"), "to": "n_c_%s" % cref,
                          "type": "论证", "rel": "证据", "warrant": "",
                          "backing": "",
                          "rebuttal": "TODO 补推理桥：凭这条证据为什么能得出这个主张"})

    data = {
        "thesis_ref": "thesis.json",
        "outline_ref": args.outline,
        "materials_ref": args.materials or "materials.json",
        "series": thesis.get("series") or {"name": "", "index": 0},
        "terms": [{"term": "", "canonical": "", "aliases_ok": [], "banned": [],
                   "definition": "全篇出现的关键术语先列在这里，定唯一写法"}],
        "nodes": nodes,
        "edges": edges,
        "statements": [],
        "series_links": [],
    }
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print("逻辑图骨架已写入 %s（%d 节点 / %d 边，warrant 待补）"
              % (args.out, len(nodes), len(edges)))
    else:
        print(text)
    return 0


def _solids(materials):
    """材料 id → 来源身份，用来判「抽不扎实的章节」。"""
    if not materials:
        return {}
    return {m.get("id"): m.get("source_type") for m in (materials.get("items") or [])}


def check_graph(d, thesis=None, materials=None):
    fails, warns = [], []
    nodes = d.get("nodes") or []
    edges = d.get("edges") or []
    terms = d.get("terms") or []

    if not nodes:
        fails.append("nodes 为空——逻辑图没有节点")
    if not edges:
        fails.append("edges 为空——只有节点没有关系，等于没有论证")
    if not terms or not any((t.get("canonical") or "").strip() for t in terms):
        fails.append("terms 为空或没有填 canonical——术语表要把全篇关键概念的写法钉住")

    kinds = {}
    sec_nodes = set()
    for i, n in enumerate(nodes):
        tag = "nodes[%d]" % i
        nid = n.get("id")
        if not nid:
            fails.append("%s 缺 id" % tag)
            continue
        if nid in kinds:
            fails.append("%s 的 id %r 重复" % (tag, nid))
        kind = n.get("kind")
        if kind not in NODE_KINDS:
            fails.append("%s 的 kind=%r 不在 %s 内" % (tag, kind, "/".join(NODE_KINDS)))
        if not (n.get("text") or "").strip():
            fails.append("%s 缺 text" % tag)
        kinds[nid] = kind
        if kind == "section":
            sec_nodes.add(nid)

    degree = {nid: 0 for nid in kinds}
    for i, e in enumerate(edges):
        tag = "edges[%d]" % i
        a, b = e.get("from"), e.get("to")
        t, rel = e.get("type"), e.get("rel")
        if a not in kinds:
            fails.append("%s 的 from=%r 不是已定义节点" % (tag, a))
        if b not in kinds:
            fails.append("%s 的 to=%r 不是已定义节点" % (tag, b))
        if a in degree:
            degree[a] += 1
        if b in degree:
            degree[b] += 1
        allowed = LAYER_RELS.get(t)
        if allowed is None:
            fails.append("%s 的 type=%r 不在 %s 内" % (tag, t, "/".join(LAYER_RELS)))
        elif rel not in allowed:
            fails.append("%s 在「%s」层用了 %r，该层只允许 %s"
                         % (tag, t, rel, "/".join(allowed)))
        if t == "论证" and rel in NEED_WARRANT and not (e.get("warrant") or "").strip():
            fails.append("%s 是「论证·%s」边但没有 warrant——证据到主张之间的桥没写，"
                         "这条论证是断的" % (tag, rel))

    # 查询 1：每节自己带的材料有没有进图、且连得到扎实来源
    # 判本节而不是判 claim：多节回指同一分论点是合法结构，但材料是按节派的单——
    # 某节的材料一条都没进图，这一节就是空壳，不能因为兄弟节有料就跟着过关。
    solid_ids = {k for k, v in _solids(materials).items() if v in SOLID_SOURCES}
    if materials is None:
        warns.append("未提供 materials.json，跳过「章节有没有扎实证据」的核对")
    else:
        used = {e.get("from") for e in edges if e.get("type") == "论证"}
        sec_mats = {}
        for m in materials.get("items") or []:
            if m.get("status") == "dropped":
                continue
            sec_mats.setdefault(m.get("section"), []).append(m.get("id"))
        for sn in sorted(sec_nodes):
            ref = None
            for n in nodes:
                if n.get("id") == sn:
                    ref = n.get("ref")
            mine = sec_mats.get(ref) or []
            if not mine:
                fails.append("节节点 %s（%s）在 materials.json 里没有任何材料——"
                             "这一节的结论是悬空的" % (sn, ref or "无 ref"))
                continue
            in_graph = [mid for mid in mine if ("n_%s" % mid) in used]
            if not in_graph:
                fails.append("节节点 %s（%s）的 %d 条材料一条都没进图——材料存在但没连到主张，"
                             "等于没用上" % (sn, ref or "无 ref", len(mine)))
                continue
            if not any(mid in solid_ids for mid in in_graph):
                warns.append("节 %s 的支撑材料全部来自二手概括或作者推断——"
                             "确认它确实只是背景或过渡" % (ref or sn))

    # 查询 3：术语一致性
    banned_map = {}
    canon = set()
    for t in terms:
        c = (t.get("canonical") or "").strip()
        if c:
            canon.add(c)
        for b in t.get("banned") or []:
            if b and c:
                banned_map[b] = c
    stmts = d.get("statements") or []
    if not stmts:
        fails.append("statements 为空——术语一致性没有扫描对象，把每节主题句与结论句列进来")
    for i, s in enumerate(stmts):
        for b, c in banned_map.items():
            if b in s:
                fails.append("statements[%d] 用了 %r，术语表规定写 %r" % (i, b, c))

    # 查询 4：系列冲突
    series = d.get("series") or {}
    links = d.get("series_links") or []
    if (series.get("name") or "").strip():
        if not links:
            fails.append("声明了系列 %r 却没有 series_links——系列之间必须标清关系" % series.get("name"))
        for i, l in enumerate(links):
            tag = "series_links[%d]" % i
            t = l.get("type")
            if t not in LAYER_RELS["篇章"]:
                fails.append("%s 的 type=%r 不在 %s 内"
                             % (tag, t, "/".join(LAYER_RELS["篇章"])))
            if t == "支撑" and l.get("conflict"):
                fails.append("%s 声明「支撑」却标了 conflict——结论相冲的两篇不能写成支撑关系"
                             % tag)
            if t == "反驳" and not (l.get("rebuttal") or "").strip():
                fails.append("%s 声明「反驳」但没写 rebuttal——要说明冲突在哪一点上" % tag)

    # WARNING：孤立节点、句子覆盖不足、单条二手证据撑一个主张
    for nid, deg in degree.items():
        if deg == 0:
            warns.append("节点 %s 没有任何连线——孤立节点要么补关系要么删掉" % nid)
    if stmts and sec_nodes and len(stmts) < len(sec_nodes):
        warns.append("statements 只有 %d 条，少于 %d 节——每节至少列一条主题句或结论句"
                     % (len(stmts), len(sec_nodes)))
    if materials is not None:
        types = _solids(materials)
        ev_per_claim = {}
        for e in edges:
            if e.get("type") == "论证" and kinds.get(e.get("from")) == "evidence":
                mid = (e.get("from") or "")[2:]
                ev_per_claim.setdefault(e.get("to"), []).append(types.get(mid))
        for cid, ts in ev_per_claim.items():
            if len(ts) == 1 and ts[0] not in SOLID_SOURCES:
                warns.append("主张 %s 只有一条证据且来源是 %s——再找一条或降调门"
                             % (cid, ts[0]))

    return fails, warns


def cmd_check(args):
    d, err = load(args.logic)
    if err:
        print("ERR", err)
        return 2
    thesis = None
    if args.thesis:
        thesis, err = load(args.thesis)
        if err:
            print("ERR", err)
            return 2
    materials = None
    if args.materials:
        materials, err = load(args.materials)
        if err:
            print("ERR", err)
            return 2

    fails, warns = check_graph(d, thesis, materials)
    print("=== A4 逻辑图核验：%s ===" % os.path.basename(args.logic))
    for x in warns:
        print("  [WARN]", x)
    for x in fails:
        print("  [FAIL]", x)
    if fails:
        print("[FAIL] %d 项——四类查询没全过：孤证章节、断头论证、术语漂移、系列冲突"
              % len(fails))
        return 1
    print("[PASS] 四类查询全过%s" % ("，有 %d 项 WARNING 待人工确认" % len(warns) if warns else ""))
    return 0


def cmd_graph(args):
    d, err = load(args.logic)
    if err:
        print("ERR", err)
        return 2
    nodes = {n.get("id"): n for n in d.get("nodes") or []}
    lines = ["graph LR"]
    style = {"section": "n_s", "claim": "n_c", "evidence": "n_e"}
    for nid, n in nodes.items():
        txt = (n.get("text") or "").strip().replace('"', "'")
        if len(txt) > 24:
            txt = txt[:24] + "…"
        lines.append('    %s["%s"]' % (nid, txt))
    for e in d.get("edges") or []:
        a, b = e.get("from"), e.get("to")
        if a not in nodes or b not in nodes:
            continue
        label = "%s·%s" % (e.get("type"), e.get("rel"))
        lines.append("    %s -->|%s| %s" % (a, label, b))
    for kind, cls in style.items():
        ids = [k for k, v in nodes.items() if v.get("kind") == kind]
        if ids:
            lines.append("    classDef %s fill:#eef,stroke:#88a" % cls)
            lines.append("    class %s %s" % (",".join(ids), cls))
    text = "\n".join(lines) + "\n"
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("逻辑图已写入 %s" % args.out)
    else:
        print(text)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="A4 逻辑建模：五层关系图的骨架、四类校验与导出",
        epilog="判据口径见同目录 logic-graph-spec.md")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="从 outline/materials/thesis 生成逻辑图骨架")
    i.add_argument("--outline", required=True)
    i.add_argument("--materials")
    i.add_argument("--thesis")
    i.add_argument("-o", "--out")
    c = sub.add_parser("check", help="四类查询")
    c.add_argument("logic")
    c.add_argument("--thesis")
    c.add_argument("--materials")
    g = sub.add_parser("graph", help="导出 Mermaid 逻辑图")
    g.add_argument("logic")
    g.add_argument("-o", "--out")
    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "graph":
        return cmd_graph(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
