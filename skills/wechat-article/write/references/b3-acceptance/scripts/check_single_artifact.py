#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 · 产物唯一性判据：稿件目录里只能有一份 wx-HTML。

「单文件铁律」的机器判据。全链路只维护 `article-wx.html`；图片回填 mmbiz URL 后
公网可达，本地预览与公众号后台共用同一份文件，禁止再生成「本地预览版」
「待推送版」「base64 存档版」等第二份 HTML 交付物。

用法：
    check_single_artifact.py --dir <稿件目录> [--main article-wx.html] [--json out.json]

判据：
    PASS     目录内除主文件外没有第二份 wx-HTML 候选
    FAIL     列出多余文件与命中原因（退出码 1）
    PENDING  主文件或目录不存在（退出码 2）

候选识别（控制误报）：文件名带「预览/本地/待推送/存档/wx/…」等字样，或内容同时含
`<section` 与 `__MMP__` / `mmbiz.qpic.cn`。纯自动，不需要任何人工确认步骤。
"""
import argparse
import io
import json
import os
import re
import sys

NAME_HINTS = ("预览", "preview", "local", "本地", "wx", "push", "待推送",
              "存档", "archive", "inline", "内嵌")
SECTION_RX = re.compile(r"<section", re.I)
WXLINK_RX = re.compile(r"__MMP__:|mmbiz\.qpic\.cn", re.I)


def scan(directory, main):
    extras = []
    for fn in sorted(os.listdir(directory)):
        path = os.path.join(directory, fn)
        if not os.path.isfile(path) or not fn.lower().endswith((".html", ".htm")):
            continue
        if fn == main:
            continue
        low = fn.lower()
        hits = [h for h in NAME_HINTS if h in low]
        if hits:
            why = "文件名疑似第二个预览/推送版本（命中 %s）" % "、".join(hits)
        else:
            try:
                text = io.open(path, encoding="utf-8", errors="replace").read(200000)
            except OSError:
                text = ""
            if SECTION_RX.search(text) and WXLINK_RX.search(text):
                why = "内容含 wx 内联正文片段与图片占位/URL"
            else:
                why = ""
        if why:
            extras.append({"file": path, "reason": why})
    return extras


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", required=True, help="稿件目录")
    ap.add_argument("--main", default="article-wx.html", help="唯一交付物文件名")
    ap.add_argument("--json", dest="json_out", help="机器可读结果落盘路径")
    args = ap.parse_args()

    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print("[PENDING] 目录不存在: %s" % directory)
        return 2

    status = "PASS"
    if not os.path.isfile(os.path.join(directory, args.main)):
        status = "PENDING"
        print("[PENDING] 主产物不存在: %s" % os.path.join(directory, args.main))

    extras = scan(directory, args.main)
    if extras:
        status = "FAIL"
        print("[FAIL] 产物唯一性不合格：除 %s 外还有 %d 份 wx-HTML 候选"
              % (args.main, len(extras)))
        for item in extras:
            print("  - %s  %s" % (os.path.basename(item["file"]), item["reason"]))
        print("      单文件铁律：本地预览直接打开主文件即可（mmbiz URL 公网可达）；")
        print("      临时外壳用 wrap_preview.py 写到系统临时目录，不算交付物。")
    elif status == "PASS":
        print("[PASS] 产物唯一：%s（目录内无第二份 wx-HTML）" % args.main)

    result = {"status": status, "main": args.main, "dir": directory, "extras": extras}
    if args.json_out:
        json.dump(result, io.open(args.json_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return {"PASS": 0, "FAIL": 1, "PENDING": 2}[status]


if __name__ == "__main__":
    sys.exit(main())
