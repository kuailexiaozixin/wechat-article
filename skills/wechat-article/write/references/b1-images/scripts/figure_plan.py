# -*- coding: utf-8 -*-
"""B1 配图 · 分层配图需求分析与清单生成（读 A3 逻辑台账（article-ledger.md）各层结论，决定配什么图）。

设计前提（对齐 5.2.0 逻辑层重构）：
  A3 逻辑改用「文章台账 article-ledger.md」作为 AI 做语义分析的载体，各层逻辑写在台账里、
  由 AI 填写，不靠脚本解析。本脚本**不解析台账自然语言**——它只认一份结构化产物
  `figure-requirements.json`（由 AI 读完台账各层后产出），做两件确定性的事：

  1) check <figure-requirements.json>   校验配图需求清单：每条需求必须带 层级/图类型/
     触发判据/建议 tool，且 tool 与层级匹配（架构→mermaid、法条→screenshot 等），
     防止 AI 把「法条拆解」配成思维导图这类层级错配。
  2) from-ledger <figure-requirements.json> [-o manifest.json]
     把需求清单展开成 figure_manifest.py 的清单条目（缺的必填字段自动按层级补默认），
     接回既有的 check / upload / 回填流程。

层级→图形式映射（判据权威见 figure-manifest-spec.md「分层配图判据」）：
  L1 架构     章数≥5 或分论点交叉          → 架构总览（思维导图/流程）  tool=mermaid
  L2/L3 章节   单节段落>6 或节内对照关系     → 章节逻辑（流程图）         tool=mermaid
  L4 法条     论证边引用法条条文            → 法条拆解（卡片/表格）      tool=screenshot(gen_table)
  数据        有量化对比/趋势               → 趋势/构成（柱状/饼）       tool=screenshot(外部图表)
  封面        每篇必配                      → 几何+字                    tool=cover(gen_cover)

退出码：0 = 通过；1 = 有 FAIL；2 = 用法错误/文件不存在。
"""
import argparse
import io
import json
import os
import sys

# 层级枚举：需求必须落在其中一层（封面单列，不进 A3 逻辑五层但每篇必配）
LAYERS = ("L1架构", "L2L3章节", "L4法条", "数据", "封面")

# 层级 → 允许/建议的 tool（错配会拦）
LAYER_TOOLS = {
    "L1架构": ("mermaid",),
    "L2L3章节": ("mermaid",),
    "L4法条": ("screenshot", "mermaid"),
    "数据": ("screenshot",),
    "封面": ("cover",),
}

# 需求必填字段（id/filename 由 from-ledger 按层级+序号生成，AI 填的是判断类字段）
REQ_MUST = ("layer", "figure_type", "trigger", "tool")

# 层级 → figure_type 默认值（AI 没填 figure_type 时按层级给一个，可被覆盖）
LAYER_FIGURE_DEFAULT = {
    "L1架构": "架构总览图",
    "L2L3章节": "章节逻辑图",
    "L4法条": "法条拆解卡",
    "数据": "数据趋势图",
    "封面": "封面",
}


def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f), None
    except OSError:
        return None, "读不到文件：%s" % path
    except ValueError as e:
        return None, "不是合法 JSON：%s（%s）" % (path, e)


def check_requirements(data):
    """校验配图需求清单。返回 (fails, warns)。"""
    fails, warns = [], []
    reqs = data.get("requirements")
    if not isinstance(reqs, list):
        return ["requirements 缺失或不是数组——AI 读完台账各层后应产出这份需求清单"], warns
    if not reqs:
        warns.append("requirements 为空——本判不配图（合法：短文/纯叙事可无图），但封面通常仍要")
    seen = set()
    for i, r in enumerate(reqs, 1):
        tag = r.get("id") or ("req%d" % i)
        layer = r.get("layer")
        tool = r.get("tool")
        miss = [k for k in REQ_MUST if not str(r.get(k, "")).strip()]
        if miss:
            fails.append("%s 缺必填字段：%s" % (tag, "、".join(miss)))
            continue
        if layer not in LAYERS:
            fails.append("%s 的 layer=%r 不在 %s 内" % (tag, layer, "、".join(LAYERS)))
            continue
        # tool 必须与层级匹配（层级错配 = 拿错了图形式，比不配图更糟）
        if tool not in LAYER_TOOLS[layer]:
            fails.append("%s 层级 %s 配了 tool=%r，该层只用 %s——层级与图形式错配"
                         % (tag, layer, tool, "/".join(LAYER_TOOLS[layer])))
        # trigger 是「为什么这张图该配」的判据，不能空着或写「更直观」
        tr = str(r.get("trigger")).strip()
        if tr in ("", "更直观", "更清晰", "丰富多样"):
            fails.append("%s 的 trigger 没写清触发判据（%r）——说不清凭什么配，就不该有这张图"
                         % (tag, tr))
        fid = r.get("filename")
        if fid in seen:
            fails.append("%s 的 filename 与前面需求重复：%s" % (tag, fid))
        else:
            seen.add(fid)
        # L4 法条层图上若带条文文字，必须可回溯到台账 L4 的具体论证边
        if layer == "L4法条" and not str(r.get("source_basis", "")).strip() \
                and not str(r.get("text_in_image", "")).strip():
            warns.append("%s 是法条拆解图但未标 source_basis/text_in_image——"
                         "条文须能指回台账 L4 的哪条论证边" % tag)
    return fails, warns


def cmd_check(args):
    data, err = load(args.req)
    if err:
        print("ERR", err)
        return 2
    fails, warns = check_requirements(data)
    if args.json:
        print(json.dumps({"fail": fails, "warn": warns}, ensure_ascii=False))
        return 1 if fails else 0
    print("=== B1 分层配图需求校验: %s ===" % args.req)
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    if fails:
        print("[FAIL] %d 项——修需求清单再进 from-ledger" % len(fails))
        return 1
    print("[PASS] 需求清单 %d 条通过（WARN %d 项人工确认）"
          % (len(data.get("requirements") or []), len(warns)))
    return 0


def req_to_figure(r, idx):
    """把一条需求展开成 figure_manifest.py 的清单条目（补齐必填字段）。"""
    layer = r.get("layer") or "L1架构"
    fig = {
        "id": r.get("id") or ("f%02d" % (idx + 1)),
        "kind": "cover" if layer == "封面" else "body",
        # position：AI 应已填到「第X节 第Y段」；没填给占位提示，from-ledger 后人工补
        "position": r.get("position") or "（TODO：按台账定位到 第X节 第Y段）",
        "purpose": r.get("purpose") or r.get("trigger"),
        "visual_content": r.get("visual_content") or r.get("figure_type") or LAYER_FIGURE_DEFAULT.get(layer, ""),
        "text_in_image": r.get("text_in_image", ""),
        "labels_traceable": bool(str(r.get("text_in_image", "")).strip()) or None,
        "source_basis": r.get("source_basis") or "（TODO：图上的数字/条文指回台账哪条）",
        "tool": r.get("tool") or "mermaid",
        # filename：AI 没定就给层级前缀+序号，保证全清单唯一
        "filename": r.get("filename") or ("%s_%02d.png" % (layer, idx + 1)),
        "aspect_ratio": r.get("aspect_ratio") or ("16:9" if layer != "封面" else "2.35:1"),
        # 把需求原字段留在条目里，便于追溯这张图是哪层为什么配的
        "_from_layer": layer,
        "_figure_type": r.get("figure_type") or LAYER_FIGURE_DEFAULT.get(layer, ""),
        "_trigger": r.get("trigger"),
    }
    return fig


def cmd_from_ledger(args):
    data, err = load(args.req)
    if err:
        print("ERR", err)
        return 2
    fails, _ = check_requirements(data)
    if fails:
        print("[FAIL] 需求清单未过校验，先修再 from-ledger：")
        for f in fails:
            print("  -", f)
        return 1
    reqs = data.get("requirements") or []
    manifest = {"topic": data.get("topic", ""), "figure_requirements_src": args.req,
                "figures": [req_to_figure(r, i) for i, r in enumerate(reqs)]}
    out = args.out or os.path.splitext(args.req)[0] + "-manifest.json"
    io.open(out, "w", encoding="utf-8", newline="\n").write(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print("=== B1 从需求清单生成 manifest：%s ===" % out)
    print("  %d 条需求 → %d 个清单条目" % (len(reqs), len(manifest["figures"])))
    for f in manifest["figures"]:
        print("    %-4s [%s] %-14s tool=%-10s %s"
              % (f["id"], f["_from_layer"], f["filename"], f["tool"],
                 f["tool"] if f["_from_layer"] != "L4法条" else f"（法条走 gen_table）"))
    print("下一步：figure_manifest.py check %s（补齐 TODO 的 position/source_basis 后进 B2）" % out)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    c = sub.add_parser("check", help="校验配图需求清单（层级/tool/触发判据）")
    c.add_argument("req")
    c.add_argument("--json", action="store_true")
    fl = sub.add_parser("from-ledger", help="把需求清单展开成 figure_manifest 条目")
    fl.add_argument("req")
    fl.add_argument("-o", "--out")
    a = ap.parse_args()
    if a.cmd == "check":
        return cmd_check(a)
    if a.cmd == "from-ledger":
        return cmd_from_ledger(a)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
