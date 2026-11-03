# -*- coding: utf-8 -*-
"""A3 素材 · 按章节派单、逐条回填、出口前核实。

子命令：
    init --outline outline.json [-o materials.json]   按章节生成派单骨架
    check <materials.json> [--outline outline.json]   门槛 + 来源身份 + 核实状态校验
    report <materials.json>                           按节统计的材料覆盖报告

为什么要有台账：研究性文章的材料是「依据」，不是「举例」。依据不足时，写出来的
是通顺的空话——每一句都对，每一句都没出处。台账把这件本该在动笔前做的清点
变成一道可以卡住的口子，判据口径见同目录 material-ledger-spec.md。

退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误或文件不存在。
"""
import argparse
import datetime
import io
import json
import math
import os
import sys

SOURCE_TYPES = ("一手事实", "当事人自述", "二手概括", "作者推断", "未核实")
STATUSES = ("done", "pending", "dropped")
MUST = ("id", "section", "claim", "source", "source_type", "verified_at", "status")

WORDS_PER_ITEM = 240      # 每 240 字至少一件有来路的材料（1200 字 → 5 件）
INFERENCE_MAX = 0.50      # 作者推断占比上限
STALE_DAYS = 365          # verified_at 超过一年提示复核


def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f), None
    except OSError:
        return None, "读不到文件：%s" % path
    except ValueError as e:
        return None, "不是合法 JSON：%s（%s）" % (path, e)


def cmd_init(args):
    out, err = load(args.outline)
    if err:
        print("ERR", err)
        return 2
    sections = out.get("sections") or []
    items = []
    n = 0
    for s in sections:
        sid = s.get("id")
        kinds = s.get("evidence_kinds") or []
        words = s.get("words") or 0
        need = max(1, int(math.ceil(words / float(WORDS_PER_ITEM)))) if words else 1
        for k in range(need):
            n += 1
            items.append({
                "id": "m%02d" % n,
                "section": sid,
                "claim": "这条材料用来证明什么（一句话，A4 会把它变成证据节点）",
                "quote": "",
                "source": "出处：文件全名 + 条款号 / 案号 / 报告名与页码 / 文献题名",
                "source_type": "一手事实",
                "locator": "",
                "verified_at": "",
                "status": "pending",
                "note": (("本节预计材料类型：%s" % "、".join(kinds)) if kinds and k == 0 else ""),
            })
    data = {
        "thesis_ref": "thesis.json",
        "outline_ref": args.outline,
        "target_words": out.get("word_budget") or 0,
        "items": items,
    }
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print("派单骨架已写入 %s（%d 节 / %d 条待填）" % (args.out, len(sections), len(items)))
    else:
        print(text)
    return 0


def _parse_date(s):
    try:
        return datetime.date(*[int(x) for x in str(s).split("-")[:3]])
    except (ValueError, TypeError):
        return None


def check_ledger(d, outline=None):
    fails, warns = [], []
    items = d.get("items") or []
    if not items:
        fails.append("items 为空——没有材料就不要写这篇")
        return fails, warns

    target = d.get("target_words")
    if not isinstance(target, int) or target <= 0:
        warns.append("target_words 缺失或非正整数，跳过总数门槛核对")
        target = 0

    sec_ids = None
    sec_need = {}
    if outline is not None:
        sec_ids, sec_need = set(), {}
        for s in outline.get("sections") or []:
            sid = s.get("id")
            sec_ids.add(sid)
            w = s.get("words") or 0
            sec_need[sid] = max(1, int(math.ceil(w / float(WORDS_PER_ITEM)))) if w else 1

    ids, per_sec, n_infer, n_primary, ref = set(), {}, 0, 0, set()
    today = datetime.date.today()

    for i, m in enumerate(items):
        tag = "items[%d]" % i
        for k in MUST:
            if m.get(k) in (None, ""):
                fails.append("%s 缺 %s" % (tag, k))

        mid = m.get("id")
        if mid:
            if mid in ids:
                fails.append("%s 的 id %r 重复" % (tag, mid))
            ids.add(mid)

        st = m.get("source_type")
        if st and st not in SOURCE_TYPES:
            fails.append("%s 的 source_type=%r 不在 %s 内" % (tag, st, "/".join(SOURCE_TYPES)))
        if st == "未核实":
            fails.append("%s 标了未核实——这类材料不得进正文，核实或删掉" % tag)
        if st == "作者推断":
            n_infer += 1
        if st == "一手事实":
            n_primary += 1
            if not (m.get("quote") or "").strip():
                warns.append("%s 是一手事实却没摘原文——多半没查原文" % tag)

        status = m.get("status")
        if status and status not in STATUSES:
            fails.append("%s 的 status=%r 不在 %s 内" % (tag, status, "/".join(STATUSES)))
        if status == "pending":
            fails.append("%s 还是 pending——出口前必须清零（补齐或标 dropped）" % tag)

        sec = m.get("section")
        if sec:
            per_sec[sec] = per_sec.get(sec, 0) + 1
            ref.add(sec)
            if sec_ids is not None and sec not in sec_ids:
                fails.append("%s 的 section=%r 在 outline.json 里不存在" % (tag, sec))

        va = m.get("verified_at")
        if va:
            dt = _parse_date(va)
            if dt is None:
                fails.append("%s 的 verified_at=%r 不是 YYYY-MM-DD" % (tag, va))
            elif (today - dt).days > STALE_DAYS:
                warns.append("%s 的核对日期 %s 已超过一年——税率/门槛/条号可能已变，重核一次"
                             % (tag, va))

    if sec_ids is not None:
        for sid in sec_ids:
            if per_sec.get(sid, 0) == 0:
                fails.append("节 %s 没有任何材料——这一节不该存在，回 A2 删掉或改结构" % sid)
            elif per_sec[sid] < sec_need.get(sid, 1):
                warns.append("节 %s 只有 %d 条材料，按字数应≥%d 条——这一节多半会写空"
                             % (sid, per_sec[sid], sec_need[sid]))
        orphans = ref - sec_ids
        if orphans:
            warns.append("有材料指向不存在的节：%s" % "、".join(sorted(orphans)))

    live = [m for m in items if m.get("status") != "dropped"]
    if target:
        need = int(math.ceil(target / float(WORDS_PER_ITEM)))
        if len(live) < need:
            fails.append("材料 %d 条，目标 %d 字需≥%d 条——先研究或缩小题目，不要靠形容词填充"
                         % (len(live), target, need))

    if n_primary == 0:
        fails.append("全篇没有一条一手事实——研究性文章不带规则原文，结论没有落点")
    if live and n_infer / float(max(1, len(live))) >= INFERENCE_MAX:
        fails.append("作者推断占 %.0f%%，达到上限 %.0f%%——推断只能作论证桥，不能承担论证"
                     % (n_infer * 100.0 / len(live), INFERENCE_MAX * 100))

    return fails, warns


def cmd_check(args):
    d, err = load(args.ledger)
    if err:
        print("ERR", err)
        return 2
    outline = None
    if args.outline:
        outline, err = load(args.outline)
        if err:
            print("ERR", err)
            return 2
    fails, warns = check_ledger(d, outline)
    print("=== A3 素材核验：%s ===" % os.path.basename(args.ledger))
    for x in warns:
        print("  [WARN]", x)
    for x in fails:
        print("  [FAIL]", x)
    if fails:
        print("[FAIL] %d 项——材料没到位就开写，写出来的是通顺的空话" % len(fails))
        return 1
    print("[PASS] 材料台账通过%s" % ("，有 %d 项 WARNING 待人工确认" % len(warns) if warns else ""))
    return 0


def cmd_report(args):
    d, err = load(args.ledger)
    if err:
        print("ERR", err)
        return 2
    items = [m for m in (d.get("items") or []) if m.get("status") != "dropped"]
    per, types = {}, {}
    for m in items:
        per[m.get("section")] = per.get(m.get("section"), 0) + 1
        types[m.get("source_type")] = types.get(m.get("source_type"), 0) + 1
    print("=== 材料覆盖报告：%s ===" % os.path.basename(args.ledger))
    print("target_words=%s  有效材料 %d 条" % (d.get("target_words"), len(items)))
    for sid in sorted(per, key=lambda x: str(x)):
        print("  %-6s %d 条" % (sid, per[sid]))
    print("来源构成：" + "、".join("%s %d" % (k, v) for k, v in sorted(types.items())))
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="A3 素材：按章节派单、逐条回填、出口前核实",
        epilog="判据口径见同目录 material-ledger-spec.md")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="按 outline.json 生成派单骨架")
    i.add_argument("--outline", required=True)
    i.add_argument("-o", "--out")
    c = sub.add_parser("check", help="校验材料台账")
    c.add_argument("ledger")
    c.add_argument("--outline")
    r = sub.add_parser("report", help="按节统计的材料覆盖报告")
    r.add_argument("ledger")
    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "check":
        return cmd_check(args)
    if args.cmd == "report":
        return cmd_report(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
