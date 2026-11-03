# -*- coding: utf-8 -*-
"""B5 人工 · 机器查不到的项目核对单与签字留痕。

wrap_preview.py（同目录）把已校验的 HTML 包成本地预览页供人工看；本脚本管另一件事：
把「人工自查项」变成一张必须逐条确认、可留痕的核对单。三道闸只覆盖可测项，
下面这几条脚本查不到，只有人看过才能签——不签字就没有 B6 的推送依据。

子命令：
    checklist [-o checklist.md]        打印/落盘核对单（未勾选状态）
    record --html <a.html> --qa <shot.png> --note "<看了什么>"  记一次人工确认
    require --json <record.json>       供 B6 调用：核对是否有人工签字记录

退出码：0 / 1 / 2（用法）。
"""
import argparse
import datetime
import io
import json
import os
import sys

ITEMS = [
    "金额/编号类演示数据已标注「教学示例/演示数据」",
    "代码片段与仓库源码逐行一致（抽查关键行）",
    "--title 取正文标题的短句、与正文标题有差异；字节与字符上限见 "
    "Write/references/b4-push/draft-push-parameters.md「参数上限」",
    "封面已准备，且与账号内已推过的篇目不重复",
    "qa_mobile 整页截图在手机宽度下观感可接受（首屏有完整一句、代码未折断、图居中、无大面积深色块）",
    "推送后需附「发布前必设四项」提醒——清单与固定话术见 "
    "Write/references/b4-push/draft-push-parameters.md「推送与预览工作流」第 4 步",
]


def cmd_checklist(args):
    lines = ["# B5 人工自查核对单", ""]
    for it in ITEMS:
        lines.append("- [ ] " + it)
    text = "\n".join(lines) + "\n"
    if args.out:
        io.open(args.out, "w", encoding="utf-8").write(text)
        print("CHECKLIST ->", args.out)
    else:
        print(text)
    return 0


def cmd_record(args):
    missing = []
    if not os.path.isfile(args.html):
        missing.append("待预览的 HTML 不存在：%s" % args.html)
    if not os.path.isfile(args.qa):
        missing.append("390px 截图不存在：%s（没有截图就没法核对观感，别空签）" % args.qa)
    if not args.note.strip():
        missing.append("--note 为空：至少写一句「看了截图的哪几处、结论是什么」")
    if missing:
        print("=== B5 人工确认记录 ===")
        for m in missing:
            print("  [FAIL]", m)
        print("[FAIL] 依据不足，不能签字")
        return 1
    rec = {
        "step": "B5-manual",
        "html": os.path.abspath(args.html),
        "qa_screenshot": os.path.abspath(args.qa),
        "checked_items": len(ITEMS),
        "note": args.note.strip(),
        "signed_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    out = args.out or (os.path.splitext(args.html)[0] + "_B5.json")
    json.dump(rec, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("=== B5 人工确认已记录 ===")
    print("  截图：%s" % rec["qa_screenshot"])
    print("  确认人述：%s" % rec["note"])
    print("  -> %s（B6 推送闸据此放行）" % out)
    return 0


def cmd_require(args):
    try:
        rec = json.load(io.open(args.json, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("[FAIL] 读不到 B5 人工签字记录：%s（%s）" % (args.json, e))
        print("       B6 推送必须有 B5 留痕，不接受「口头确认过」")
        return 1
    ok = bool(rec.get("note", "").strip()) and bool(rec.get("qa_screenshot")) \
        and os.path.isfile(rec["qa_screenshot"])
    print("[PASS] B5 人工签字在案：%s" % rec.get("signed_at", "?")) if ok \
        else print("[FAIL] B5 记录不完整（缺 note 或截图已不在）")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("checklist"); c.add_argument("-o", "--out")
    r = sub.add_parser("record")
    r.add_argument("--html", required=True); r.add_argument("--qa", required=True)
    r.add_argument("--note", default=""); r.add_argument("-o", "--out")
    q = sub.add_parser("require"); q.add_argument("--json", required=True)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return 2
    return {"checklist": cmd_checklist, "record": cmd_record,
            "require": cmd_require}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
