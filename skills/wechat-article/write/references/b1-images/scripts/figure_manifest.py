# -*- coding: utf-8 -*-
"""B1 配图 · 配图清单与上传前预检（不上传、不生图，只把这两件事的依据钉住）。

子命令：
    template [-o manifest.json]              写空白配图清单
    check <manifest.json> [--json]           清单字段 + 图片文件 + 尺寸/格式/宽度预检
    verify <manifest.json> [--html H] [--map M] [--json]
                                             清单图 vs 正文/映射一致性（清单有图正文没排、漏传）
    plan-mermaid <dir>                       列 .mmd 与已渲染 PNG 的差集

为什么要有这份清单：一步到位原则要求「先批量上传拿到 URL、再排版直接引用」，
但真正踩坑的地方在上传**之前**——图没规划（为凑组件补一张）、gif 当成 jpg 传、
2MB 的图直接送进 1MB 上限的接口、图上的数字在正文里没有来路。这四件事
`upload_imgs.py` 拦不住或拦得太晚，本脚本在规划阶段就拦。

退出码：0 = 通过；1 = 有 FAIL；2 = 用法错误。
"""
import argparse
import io
import json
import os
import re
import sys

IMG_MAX_BYTES = 1 * 1024 * 1024          # media/uploadimg 官方口径
COVER_MAX_BYTES = 10 * 1024 * 1024       # material/add_material?type=image 口径
COVER_RATIO, COVER_TOL = 2.35, 0.12      # 大卡 900×383；允许 ±12%（微信端自行裁剪）
BODY_MIN_W, BODY_MAX_W = 500, 2400       # 正文图宽度建议区间（px，含 2x 渲染；越界仅 WARN）
ALLOWED_EXT = (".jpg", ".jpeg", ".png")
MUST_FIELDS = ("id", "position", "purpose", "visual_content", "filename", "source_basis")

MMBIZ_RE = re.compile(r'src="(https?://mmbiz\.qpic\.cn/[^"]+)"')

TEMPLATE = {
    "topic": "",
    "figures": [{
        "id": "f01", "kind": "body",
        "position": "第三节 段2 之后",
        "purpose": "这张图替读者省掉了哪一段文字（不写「更直观」）",
        "visual_content": "画什么：主体 / 关系 / 数字",
        "text_in_image": "图上文字逐字列出；空串表示无字图",
        "labels_traceable": True,
        "source_basis": "图上的数字/结论来自稿件第几段或哪条来源",
        "tool": "mermaid | imagegen | screenshot | none",
        "filename": "f01-flow-example.png",
        "aspect_ratio": "16:9",
    }],
}


def _px(path):
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001
        return "unreadable"


def cmd_template(args):
    text = json.dumps(TEMPLATE, ensure_ascii=False, indent=2)
    if args.out:
        io.open(args.out, "w", encoding="utf-8").write(text + "\n")
        print("TEMPLATE ->", args.out)
    else:
        print(text)
    return 0


def check_manifest(path):
    fails, warns, skips = [], [], []
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return ["manifest 不是合法 JSON：%s" % e], [], []
    figs = data.get("figures")
    if not isinstance(figs, list) or not figs:
        return ["figures 为空或不是数组——B1 的产出物就是这份清单"], [], []
    base = os.path.dirname(os.path.abspath(path))
    seen = set()
    for i, f in enumerate(figs, 1):
        tag = f.get("id") or "#%d" % i
        miss = [k for k in MUST_FIELDS if not str(f.get(k, "")).strip()]
        if miss:
            fails.append("%s 缺必填字段：%s" % (tag, "、".join(miss)))
        fn = f.get("filename", "")
        if fn in seen:
            fails.append("%s filename 与前面条目重复：%s" % (tag, fn))
        seen.add(fn)
        kind = f.get("kind", "body")
        txt = str(f.get("text_in_image", "")).strip()
        if txt and f.get("labels_traceable") is not True:
            fails.append("%s 图上有文字但未声明 labels_traceable=true——"
                         "图上每个词都要能在正文或来源里指回去" % tag)
        if txt and kind == "body":
            warns.append("%s 含图上文字：生成后若错别字或糊，改提示词重生成，"
                         "禁止用 Pillow/SVG 在位图上盖字修补" % tag)
        p = os.path.normpath(os.path.join(base, fn)) if fn else None
        if p and not os.path.exists(p):
            warns.append("%s 图片尚未生成：%s（允许先出清单再出图，但进 B2 前必须补齐）"
                         % (tag, fn))
            continue
        if not p:
            continue
        ext = os.path.splitext(p)[1].lower()
        size = os.path.getsize(p)
        if kind == "cover":
            if size > COVER_MAX_BYTES:
                fails.append("%s 封面 %d 字节 > 10MB 上限" % (tag, size))
            dims = _px(p)
            if dims is None:
                skips.append("%s 未装 Pillow，跳过封面宽高比核对" % tag)
            elif dims == "unreadable":
                fails.append("%s 封面读不出尺寸" % tag)
            elif dims[1]:
                r = dims[0] / float(dims[1])
                if abs(r - COVER_RATIO) > COVER_TOL * COVER_RATIO:
                    warns.append("%s 封面宽高比 %.2f:1 离 2.35:1 偏远（%d×%d），"
                                 "大卡裁剪会丢构图" % (tag, r, dims[0], dims[1]))
        else:
            if ext not in ALLOWED_EXT:
                fails.append("%s 正文图 %s 非 jpg/png（media/uploadimg 只收这两种，不符报 40005）"
                             % (tag, ext or "无扩展名"))
            if size > IMG_MAX_BYTES:
                fails.append("%s 正文图 %d 字节 > 1MB（超限报 40009；先压缩再传，"
                             "别指望接口放过）" % (tag, size))
            dims = _px(p)
            if dims is None:
                skips.append("%s 未装 Pillow，跳过图片宽度核对" % tag)
            elif dims == "unreadable":
                warns.append("%s 图片读不出尺寸，跳过宽度核对" % tag)
            elif dims[0] > BODY_MAX_W:
                warns.append("%s 正文图宽 %dpx > %dpx：微信端会压缩、体积浪费，"
                             "建议缩小到 %dpx 内" % (tag, dims[0], BODY_MAX_W, BODY_MAX_W))
            elif dims[0] < BODY_MIN_W:
                warns.append("%s 正文图宽 %dpx < %dpx：偏窄，手机端偏糊，"
                             "建议放大到 %dpx 以上" % (tag, dims[0], BODY_MIN_W, BODY_MIN_W))
    return fails, warns, skips


def cmd_check(args):
    fails, warns, skips = check_manifest(args.manifest)
    if args.json:
        print(json.dumps({"fail": fails, "warn": warns, "skip": skips}, ensure_ascii=False))
        return 1 if fails else 0
    print("=== B1 配图清单预检: %s ===" % args.manifest)
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    for x in skips:
        print("  [SKIP]", x)
    if fails:
        print("[FAIL] %d 项不通过——先修清单或图片，再进 B2" % len(fails))
        return 1
    print("[PASS] 清单通过（WARN %d 项人工确认，SKIP %d 项未覆盖）" % (len(warns), len(skips)))
    return 0


def cmd_verify(args):
    """核清单里的正文图是否都上传、都排进正文（与 check 互补：check 只看清单自身，
    verify 看清单 ↔ map ↔ HTML 三者是否对得上）。"""
    fails, warns = [], []
    try:
        data = json.load(io.open(args.manifest, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        print("ERR manifest 不是合法 JSON：%s" % e, file=sys.stderr)
        return 1
    figs = data.get("figures")
    if not isinstance(figs, list) or not figs:
        print("ERR figures 为空或不是数组", file=sys.stderr)
        return 1

    mapping = {}
    if args.map:
        if not os.path.isfile(args.map):
            print("ERR map 不存在：%s" % args.map, file=sys.stderr)
            return 1
        try:
            mapping = json.load(io.open(args.map, encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print("ERR map 不是合法 JSON：%s" % e, file=sys.stderr)
            return 1

    html = ""
    if args.html:
        if not os.path.isfile(args.html):
            print("ERR html 不存在：%s" % args.html, file=sys.stderr)
            return 1
        html = io.open(args.html, encoding="utf-8").read()

    body_figs = [f for f in figs if f.get("kind", "body") != "cover"]
    used_urls = set()
    for f in body_figs:
        tag = f.get("id") or f.get("filename") or "?"
        fn = f.get("filename", "")
        base = os.path.basename(fn) if fn else ""
        url = mapping.get(base) if mapping else None
        if mapping and not url:
            fails.append("%s 未上传：map 中无 %s" % (tag, base or "（filename 为空）"))
            continue
        if url:
            used_urls.add(url)
            if html and url not in html:
                fails.append("%s 清单有图但正文未引用：%s" % (tag, url[:80]))
    if html:
        html_urls = set(MMBIZ_RE.findall(html))
        if mapping:
            for u in sorted(u for u in html_urls if u not in used_urls)[:20]:
                warns.append("正文引用了不在清单中的 mmbiz URL：%s" % u[:80])
        else:
            warns.append("传了 --html 但未传 --map，无法核对 mmbiz URL 归属；"
                         "建议同时给 --map 以完整核验")

    if args.json:
        print(json.dumps({"fail": fails, "warn": warns,
                          "body_figures": len(body_figs)}, ensure_ascii=False))
        return 1 if fails else 0
    print("=== B1 清单/正文一致性核验: %s ===" % args.manifest)
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    if not args.map and not args.html:
        print("  [INFO] 未传 --map/--html，仅完成清单加载（无交叉核验项）")
    if fails:
        print("[FAIL] %d 项不通过" % len(fails))
        return 1
    print("[PASS] 清单 %d 张正文图核验通过（WARN %d 项）" % (len(body_figs), len(warns)))
    return 0


# scan 子命令已删：图数一致性与本地路径红线改由 B3 验收包核
# （acceptance_pack.py 的 figcount/静态子闸）——原设计里 scan 要先有 B2 的 HTML
# 才能跑，与「一步到位要求先传图」构成环形依赖，收到验收层后 B1→B2→B3 单向。

def cmd_plan_mermaid(args):
    mmds = []
    for dirpath, dirnames, filenames in os.walk(args.dir):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
        mmds += [os.path.join(dirpath, f) for f in filenames if f.endswith((".mmd", ".mermaid"))]
    print("=== B1 Mermaid 渲染差集: %s ===" % args.dir)
    if not mmds:
        print("  无 .mmd 源文件")
        return 0
    todo = 0
    for p in sorted(mmds):
        png = os.path.splitext(p)[0] + ".png"
        if os.path.exists(png):
            print("  [OK]   %s" % os.path.basename(p))
        else:
            todo += 1
            print("  [TODO] %s（未渲染）" % os.path.basename(p))
    if todo:
        print("[INFO] 渲染：python render_mermaid.py <a.mmd> [b.mmd ...]")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    t = sub.add_parser("template"); t.add_argument("-o", "--out")
    c = sub.add_parser("check"); c.add_argument("manifest"); c.add_argument("--json")
    v = sub.add_parser("verify"); v.add_argument("manifest")
    v.add_argument("--html"); v.add_argument("--map"); v.add_argument("--json", action="store_true")
    m = sub.add_parser("plan-mermaid"); m.add_argument("dir")
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help(); return 2
    return {"template": cmd_template, "check": cmd_check, "verify": cmd_verify,
            "plan-mermaid": cmd_plan_mermaid}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
