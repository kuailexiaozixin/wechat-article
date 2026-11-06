#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B1 图注合规闸（5.16.0）：图注只描述图里的内容，不写内部台账坐标与作者动作。

背景：B1 的 caption 字段与 article-wx.html 的图注此前不受任何词表扫描，
曾把「对应台账第一节与第二节」「对应第二节段4」这类段落编号直接推给读者。
本脚本把 B3 的禁用词表与制作痕迹规则复用到图注上，并额外管两类图注专有病：
  1. 内部坐标（第 X 节 / 段 N / 台账 / 稿件）
  2. 空洞图注（只写「示意图」「如图所示」，没有说出图里到底是什么）

用法:
    check_captions.py --manifest manifest.json [--requirements figure-requirements.json]
                      [--html article-wx.html] [--json captions-check.json]
退出码: 0 = 通过（可含 WARN）；1 = 有 ERROR；2 = 输入错误
纯自动，不需要任何人工操作。
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VALIDATE_PATH = os.path.abspath(
    os.path.join(HERE, "..", "..", "b3-acceptance", "scripts", "validate_wx_html.py")
)

COORD_RX = (
    re.compile(r"对应(?:台账)?第[一二三四五六七八九十\d]+节(?:段\d+)?"),
    re.compile(r"(?:第[一二三四五六七八九十\d]+节|段\d+|台账|稿件|本节|全文|文中)"),
    re.compile(r"来源\s*[:：]\s*(?:稿件|台账|文章|第)"),
)
VAGUE_RX = re.compile(r"^(?:图\s*\d+\s*)?(?:示意图|如图所示|见下图|相关图示|流程图|架构图)[。.]?$")
CAPTION_RX = re.compile(
    r"<p[^>]*font-size:12\.5px[^>]*>(.*?)</p>", re.S | re.I
)


def load_validator():
    spec = importlib.util.spec_from_file_location("_wx_validate", VALIDATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iter_captions(manifest, requirements):
    """产出 (来源, id, 图注文本)。"""
    for key, doc in (("manifest", manifest), ("requirements", requirements)):
        if not doc:
            continue
        for item in (doc.get("figures") or doc.get("requirements") or []):
            cap = item.get("caption") or item.get("note") or ""
            if cap:
                yield key, item.get("id") or item.get("filename") or "?", cap


def html_captions(html_path):
    if not html_path or not os.path.isfile(html_path):
        return []
    text = io.open(html_path, encoding="utf-8").read()
    out = []
    for raw in CAPTION_RX.findall(text):
        out.append(re.sub(r"<[^>]+>", "", raw).strip())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--requirements")
    ap.add_argument("--html")
    ap.add_argument("--json", dest="json_out")
    args = ap.parse_args()

    try:
        manifest = json.load(io.open(args.manifest, encoding="utf-8"))
        requirements = (
            json.load(io.open(args.requirements, encoding="utf-8"))
            if args.requirements and os.path.isfile(args.requirements)
            else None
        )
    except (OSError, ValueError) as exc:
        print("读取配图清单失败：%s" % exc, file=sys.stderr)
        return 2

    validator = load_validator()
    banned = tuple(validator.BANNED_WORDS)
    rules = tuple(validator.PROCESS_TRACE_RULES)
    errors, warnings, checked = [], [], []

    entries = list(iter_captions(manifest, requirements))
    for i, cap in enumerate(html_captions(args.html), 1):
        entries.append(("html", "图注%d" % i, cap))

    if not entries:
        errors.append("没有找到任何图注，B1 清单或 HTML 图注结构异常")

    for source, ident, cap in entries:
        rec = {"source": source, "id": ident, "caption": cap}
        cap_hits = [w for w in banned if w in cap]
        rule_hits = [rx.pattern for rx in rules if rx.search(cap)]
        coord_hits = [rx.pattern for rx in COORD_RX if rx.search(cap)]
        rec["banned"] = cap_hits
        rec["rules"] = rule_hits
        rec["coords"] = coord_hits
        if cap_hits or rule_hits or coord_hits:
            errors.append(
                "图注含内部坐标或制作痕迹 [%s/%s]：%s（命中 %s）"
                % (source, ident, cap, "、".join(cap_hits + rule_hits + coord_hits))
            )
        if VAGUE_RX.match(cap.strip()):
            warnings.append("图注空洞 [%s/%s]：%s——写出图里到底有什么" % (source, ident, cap))
        if source == "html" and not re.match(r"^图\s*\d+", cap):
            warnings.append("图注缺编号 [%s]：%s" % (ident, cap))
        checked.append(rec)

    print("图注合规：检查 %d 条，ERROR %d，WARN %d" % (len(checked), len(errors), len(warnings)))
    for item in errors:
        print("  [ERROR]", item)
    for item in warnings:
        print("  [WARN]", item)
    if not errors and not warnings:
        print("  图注全部为内容性说明，未发现内部坐标。")

    if args.json_out:
        payload = {
            "checked": len(checked),
            "errors": errors,
            "warnings": warnings,
            "captions": checked,
        }
        io.open(args.json_out, "w", encoding="utf-8", newline="\n").write(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        )

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
