# -*- coding: utf-8 -*-
"""A2 结构 · 章节树骨架、形状校验与章节图导出。

子命令：
    init  [-o outline.json]                        写空白章节树
    check <outline.json> [--thesis thesis.json]    结构校验（可选核对 claim_ref 回指）
    graph <outline.json> [-o outline.mmd]          导出 Mermaid 章节关系图

为什么要有这一步：结构错的地方 A3 会跟着错——素材按错误的章节去搜集，收完才发现
某一节根本不该存在。本脚本把「章节能不能回指分论点」「章节之间有没有交接」变成
可查的形状，判据口径见同目录 structure-patterns.md。

退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误或文件不存在。
"""
import argparse
import io
import json
import os
import sys

METHODS = ("pyramid", "problem-solution", "case-driven",
           "inverted-pyramid", "scqa", "controversy")
FLOWS = ("递进式", "并列式", "总分式", "对比式")
REL_TYPES = ("递进", "并列", "因果", "回扣主线", "依赖")

# 体裁 → 推荐推进法（不匹配只 WARNING：标准框架是起点不是牢笼）
CATEGORY_METHOD = {
    "政策解读": ("problem-solution", "inverted-pyramid"),
    "理论分析": ("pyramid", "controversy"),
    "案例分析": ("case-driven",),
    "操作指引": ("problem-solution",),
}

# 对仗小标题与空洞标题：研究性文章的标题要能当索引，不能当书法
DECOR_HEADINGS = ("之道", "之术", "之智", "之美", "之思", "探微", "拾遗",
                  "浅析", "刍议", "初探", "漫谈", "略论")

WORD_BUDGET_TOL = 0.20   # 各节字数之和允许偏离目标 20%
SECTION_SHARE_MAX = 0.45  # 单节占比上限，越界只 WARN

TEMPLATE = {
    "thesis_ref": "thesis.json",
    "method": "problem-solution",
    "flow": "递进式",
    "word_budget": 3000,
    "sections": [{
        "id": "s1",
        "heading": "这一节要讲清的具体内容（不要写成「之道」「之术」这类对仗）",
        "claim_ref": "s1",
        "role": "该节在论证里干什么：背景 / 条文及适用范围 / 分析 / 反驳 / 建议 / 结论",
        "words": 700,
        "evidence_kinds": ["准则原文", "应用指南", "裁判文书"],
    }],
    "relations": [{
        "from": "s1", "to": "s1", "type": "递进",
        "note": "前一节给后一节交了什么（不许留空）",
    }],
}


def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f), None
    except OSError:
        return None, "读不到文件：%s" % path
    except ValueError as e:
        return None, "不是合法 JSON：%s（%s）" % (path, e)


def cmd_init(args):
    text = json.dumps(TEMPLATE, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print("模板已写入 %s" % args.out)
    else:
        print(text)
    return 0


def _subclaim_ids(thesis_path):
    d, err = load(thesis_path)
    if err:
        return None, err
    subs = d.get("subclaims") or []
    return {str(x.get("id")) for x in subs if isinstance(x, dict) and x.get("id")}, None


def check_outline(d, sub_ids=None):
    fails, warns = [], []

    method, flow = d.get("method"), d.get("flow")
    if method not in METHODS:
        fails.append("method 取值 %r 不在 %s 内" % (method, "/".join(METHODS)))
    if flow not in FLOWS:
        fails.append("flow 取值 %r 不在 %s 内" % (flow, "/".join(FLOWS)))

    budget = d.get("word_budget")
    if not isinstance(budget, int) or budget <= 0:
        fails.append("word_budget 必须是正整数（当前 %r）" % budget)
        budget = 0

    sections = d.get("sections") or []
    if len(sections) < 2:
        fails.append("sections 只有 %d 节——研究性专业文章至少两节" % len(sections))

    ids, total, null_ref = [], 0, 0
    for i, s in enumerate(sections):
        tag = "sections[%d]" % i
        sid = s.get("id")
        if not sid:
            fails.append("%s 缺 id" % tag)
        elif sid in ids:
            fails.append("%s 的 id %r 重复" % (tag, sid))
        else:
            ids.append(sid)

        head = (s.get("heading") or "").strip()
        if not head:
            fails.append("%s 缺 heading" % tag)
        else:
            hit = [w for w in DECOR_HEADINGS if w in head]
            if hit:
                fails.append("%s 的标题命中对仗/空洞词 %s——标题要能当索引" % (tag, "、".join(hit)))

        if not (s.get("role") or "").strip():
            fails.append("%s 缺 role（这节在论证里干什么）" % tag)

        w = s.get("words")
        if not isinstance(w, int) or w <= 0:
            fails.append("%s 的 words 必须是正整数（当前 %r）" % (tag, w))
        else:
            total += w

        ref = s.get("claim_ref")
        if ref is None or ref == "":
            null_ref += 1
            if null_ref > 1:
                fails.append("%s 的 claim_ref 为空——全篇最多允许 1 个纯过渡节" % tag)
        elif sub_ids is not None and str(ref) not in sub_ids:
            fails.append("%s 的 claim_ref=%r 在 thesis.json 的 subclaims 里找不到" % (tag, ref))

    if null_ref == 1:
        warns.append("有 1 节 claim_ref 为空（纯过渡节）——确认它确实只是呼应，不承载论证")

    if budget and total:
        dev = abs(total - budget) / float(budget)
        if dev > WORD_BUDGET_TOL:
            fails.append("各节字数之和 %d 与 word_budget %d 偏差 %.0f%%（上限 %.0f%%）"
                         % (total, budget, dev * 100, WORD_BUDGET_TOL * 100))
        for s in sections:
            w = s.get("words")
            if isinstance(w, int) and w > 0 and w / float(total) > SECTION_SHARE_MAX:
                warns.append("「%s」一节占全文 %.0f%%——单节吃掉近一半通常该拆" %
                             (s.get("heading", s.get("id")), w * 100.0 / total))

    rels = d.get("relations") or []
    if not rels and len(sections) >= 2:
        warns.append("relations 为空——章节之间没有标注交接关系")
    has_backbone = False
    for i, r in enumerate(rels):
        tag = "relations[%d]" % i
        a, b, t = r.get("from"), r.get("to"), r.get("type")
        if a not in ids:
            fails.append("%s 的 from=%r 不是已定义的节 id" % (tag, a))
        if b not in ids:
            fails.append("%s 的 to=%r 不是已定义的节 id" % (tag, b))
        if t not in REL_TYPES:
            fails.append("%s 的 type=%r 不在 %s 内" % (tag, t, "/".join(REL_TYPES)))
        if t == "回扣主线":
            has_backbone = True
        if not (r.get("note") or "").strip():
            fails.append("%s 的 note 为空——要写清前一节给后一节交了什么" % tag)
    if rels and not has_backbone:
        warns.append("没有「回扣主线」类型的边——中段与结尾至少回扣一次核心问题")

    return fails, warns


def cmd_check(args):
    d, err = load(args.outline)
    if err:
        print("ERR", err)
        return 2
    sub_ids = None
    if args.thesis:
        sub_ids, err = _subclaim_ids(args.thesis)
        if err:
            print("ERR", err)
            return 2

    fails, warns = check_outline(d, sub_ids)

    # 体裁与推进法匹配（需要 thesis.json 才能判，缺它就是 WARNING 级别的信息不足）
    if args.thesis:
        t, _ = load(args.thesis)
        cat = (t or {}).get("category")
        ok = CATEGORY_METHOD.get(cat)
        if ok and d.get("method") not in ok:
            warns.append("体裁 %s 通常配 %s，当前用 %s——标准框架是起点不是牢笼，确认是有意为之"
                         % (cat, "/".join(ok), d.get("method")))

    print("=== A2 结构核验：%s ===" % os.path.basename(args.outline))
    for x in warns:
        print("  [WARN]", x)
    for x in fails:
        print("  [FAIL]", x)
    if fails:
        print("[FAIL] %d 项——结构没立住，A3 会按错的章节去搜素材" % len(fails))
        return 1
    print("[PASS] 章节树%d节，回指与交接关系齐备%s"
          % (len(d.get("sections") or []),
             "，有 %d 项 WARNING 待人工确认" % len(warns) if warns else ""))
    return 0


def cmd_graph(args):
    d, err = load(args.outline)
    if err:
        print("ERR", err)
        return 2
    lines = ["graph TD"]
    for s in d.get("sections") or []:
        sid = s.get("id")
        head = (s.get("heading") or "").strip().replace('"', "'")
        w = s.get("words")
        lines.append('    %s["%s<br/>%s字"]' % (sid, head, w) if w else '    %s["%s"]' % (sid, head))
    for r in d.get("relations") or []:
        lines.append("    %s -->|%s| %s" % (r.get("from"), r.get("type"), r.get("to")))
    text = "\n".join(lines) + "\n"
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("章节图已写入 %s" % args.out)
    else:
        print(text)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="A2 结构：章节树骨架、形状校验与章节图导出",
        epilog="判据口径见同目录 structure-patterns.md")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="写空白章节树")
    i.add_argument("-o", "--out")
    c = sub.add_parser("check", help="校验章节树")
    c.add_argument("outline")
    c.add_argument("--thesis", help="可选的 thesis.json：核对 claim_ref 回指与体裁匹配")
    g = sub.add_parser("graph", help="导出 Mermaid 章节关系图")
    g.add_argument("outline")
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
