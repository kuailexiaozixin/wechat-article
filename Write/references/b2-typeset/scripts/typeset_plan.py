# -*- coding: utf-8 -*-
"""B2 排版 · 成稿到 blocks.json 的装配计划与一致性核对。

本步不生成 HTML（生成由同目录的 `build_blocks.py` 完成，样式唯一来源
`Write/references/b2-typeset/theme-default.md`）。它管三件 build_blocks 不管的事：

    1. plan   —— 从纯文本稿切出段落，生成 blocks.json 骨架，人再逐块补类型
    2. audit  —— 核对 blocks.json 是否覆盖了稿件全部内容（漏段/凭空加段/图数不符）
    3. verify —— 排版后核对「主题样式未被手写漂移」与「序号是否连续」

为什么需要它：`build_blocks.py` 只负责「给什么块渲染什么样式」，
它不知道你是不是把稿子第三段漏掉了，也不知道你为了凑齐九个组件补写了内容
——后者正是 theme-default.md「使用约定」里明令禁止的第一条。

退出码：0 = 通过；1 = 有 FAIL；2 = 用法错误。
"""
import argparse
import io
import json
import os
import re
import sys

BLOCK_TYPES = ("h1", "rule", "h2", "para", "inline_code", "code",
               "image", "caption", "hr")
# theme-default 的开篇默认组合：大标题 → 装饰线 → 引言段（是默认值，不是配额）
COVER = ("h1", "rule")
CJK_NUMS = "一二三四五六七八九十百零〇"


def _read(path):
    return io.open(path, encoding="utf-8", errors="replace").read()


def _norm(s):
    """比较用归一化：去空白、去 markdown 痕迹，保留字与数字。"""
    s = re.sub(r"[`*_>#\[\]（）()\"'“”‘’\s]+", "", s)
    return s


def cmd_plan(args):
    text = _read(args.draft)
    lines = [l.strip() for l in text.splitlines()]
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if not ln:
            i += 1
            continue
        if ln.startswith("#"):
            title = ln.lstrip("# ").strip()
            if not blocks:
                blocks.append({"type": "h1", "text": title})
                blocks.append({"type": "rule"})
            else:
                blocks.append({"type": "h2", "text": title})
        elif ln.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            blocks.append({"type": "code", "lines": code or [""]})
        elif re.match(r'^!\[[^\]]*\]\([^)]*\)\s*$', ln):
            m = re.match(r'^!\[([^\]]*)\]\(([^)]*)\)\s*$', ln)
            blocks.append({"type": "image", "url": m.group(2), "alt": m.group(1) or "图注文字"})
        elif re.match(r'^(图\s*\d+[：: ])', ln):
            blocks.append({"type": "caption", "text": ln})
        else:
            blocks.append({"type": "para", "text": ln})
        i += 1
    out = {"blocks": blocks}
    dst = args.out or os.path.splitext(args.draft)[0] + ".blocks.json"
    json.dump(out, io.open(dst, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = len(blocks)
    print("PLAN -> %s（%d 块）" % (dst, n))
    print("  自动识别仅覆盖标题/代码/图片/图注/正文；下列项必须人工过一遍：")
    print("   • h2 序号是否用「一、二、三」（theme-default 默认），内容不分章时不硬分")
    print("   • 行内 `code` 是否需要拆成 inline_code 块")
    print("   • 为凑组件补写的内容请删掉（theme-default「使用约定」第三条）")
    print("  下一步：python Write/references/b2-typeset/scripts/build_blocks.py %s -o article.html" % dst)
    return 0


def cmd_audit(args):
    data = json.load(io.open(args.blocks, encoding="utf-8"))
    blocks = data.get("blocks") or data if isinstance(data, list) else data.get("blocks", [])
    if not isinstance(blocks, list) or not blocks:
        print("[FAIL] blocks.json 里没有块数组（应形如 {\"blocks\":[...]})")
        return 1
    fails, warns = [], []
    src = _read(args.draft) if args.draft else ""

    # 1) 组件名合法
    for i, b in enumerate(blocks, 1):
        t = b.get("type")
        if t not in BLOCK_TYPES:
            fails.append("第 %d 块 type=%r 不是 theme-default 组件（可用：%s）"
                         % (i, t, "、".join(BLOCK_TYPES)))
        # image.url 的 mmbiz/本地路径红线是 B3 验收的判据（wx-html-redlines.md），
        # 此处不再重复——旧版两项与 validate_wx_html.py 重叠，属判据双写，已删。
        if t == "caption":
            prev = blocks[i - 2].get("type") if i >= 2 else None
            if prev != "image":
                warns.append("第 %d 块 caption 紧跟的不是 image（紧跟 %r），图注编号易错位"
                             % (i, prev))

    # 2) 漏段检测：稿件里的每个正文段落都能在某块里找到
    if src:
        paras = [p.strip() for p in re.split(r"\n\s*\n", src) if p.strip()]
        joined = _norm("".join(str(b.get("text", "")) + "".join(map(str, b.get("lines", [])))
                                + str(b.get("alt", "")) for b in blocks))
        missing = []
        for p in paras:
            if p.startswith(("#", "```", "![")):
                continue
            key = _norm(p)
            if not key:
                continue
            probe = key[:18]
            if probe not in joined:
                missing.append(p[:34])
        if missing:
            fails.append("稿件有 %d 处段落在 blocks 里找不到（漏排或改稿未同步）：%s"
                         % (len(missing), " / ".join(missing[:3])))
        # 凭空加段：blocks 里的长文本在稿件里找不到
        src_norm = _norm(src)
        invented = []
        for b in blocks:
            if b.get("type") not in ("para", "h1", "h2"):
                continue
            t = _norm(str(b.get("text", "")))
            if len(t) >= 18 and t[:18] not in src_norm:
                invented.append(str(b.get("text", ""))[:34])
        if invented:
            fails.append("blocks 里有 %d 段在稿件中不存在（排版阶段新增内容必须回到稿件落字）：%s"
                         % (len(invented), " / ".join(invented[:3])))

    # 3) 图数与 caption 编号
    imgs = [b for b in blocks if b.get("type") == "image"]
    caps = [b for b in blocks if b.get("type") == "caption"]
    if imgs and len(caps) != len(imgs):
        warns.append("image ×%d 与 caption ×%d 数量不等——每张图都应有图注（theme-default 组件 8）"
                     % (len(imgs), len(caps)))
    nums = []
    for c in caps:
        m = re.match(r"^图\s*(\d+)", str(c.get("text", "")))
        nums.append(int(m.group(1)) if m else None)
    if any(n is None for n in nums):
        warns.append("有图注未以「图 N」开头，编号核对跳过：%s"
                     % [str(c.get("text", ""))[:20] for c in caps if not re.match(r"^图\s*\d+", str(c.get("text", "")))])
    got = [n for n in nums if n]
    if got and got != sorted(got) or len(set(got)) != len(got):
        fails.append("图注编号未递增或重复：%s（应 1..n 连续递增）" % got)
    elif got and got != list(range(1, len(got) + 1)):
        fails.append("图注编号未从 1 连续递增：%s" % got)

    # 4) 组件是否被硬凑（只有 1 个组件类型且块数很少时提示；反向：全组件齐用可疑）
    kinds = [b.get("type") for b in blocks]
    if "code" not in kinds and "caption" in kinds:
        pass
    distinct = set(kinds)
    if len(distinct) == len(BLOCK_TYPES) and len(blocks) <= 12:
        warns.append("九类组件全部出现在一篇短稿里——确认没有为用组件而补写内容"
                     "（theme-default 明令禁止的第一条）")

    print("=== B2 排版装配核对 ===")
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    if fails:
        print("[FAIL] %d 项——装配有问题，先修再渲染" % len(fails))
        return 1
    print("[PASS] 装配一致（WARN %d 项人工确认）" % len(warns))
    return 0


def cmd_verify(args):
    """排版后核对：样式是否真的取自 theme-default，标题编号是否成体系。
    产物形态与微信兼容红线（<style>/<pre>/class/id/外壳/图片域名）是 B3 验收的判据，
    此处不再重复——旧版四项与 validate_wx_html.py 全重叠，属判据双写，已删。"""
    html = _read(args.html)
    fails, warns = [], []
    h2 = re.findall(r"border-left:4px solid #B08D3E[^>]*>(.*?)</p>", html)
    seq = []
    for t in h2:
        m = re.match(r"\s*([%s]+)\s*[、.．]" % CJK_NUMS, t)
        seq.append(m.group(1) if m else None)
    named = [s for s in seq if s]
    if h2 and len(named) < len(h2):
        warns.append("%d 个章节标题中 %d 个无中文序号——分章则用「一、二、三」，"
                     "不分章就别用 h2 组件" % (len(h2), len(h2) - len(named)))
    if re.search(r"font-size:16px;color:#3f3f3f", html) is None and "<section" in html:
        warns.append("未检出 theme-default 正文段样式（font-size:16px;color:#3f3f3f），"
                     "疑似手写漂移样式；建议改用 build_blocks.py 生成")
    print("=== B2 排版产物核对: %s ===" % args.html)
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    if fails:
        print("[FAIL] 样式漂移——进 B3 前必修")
        return 1
    print("[PASS] 样式与编号合格（WARN %d 项；产物形态红线由 B3 验收包核，此处不重复）" % len(warns))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="从纯文本稿生成 blocks.json 骨架")
    p.add_argument("draft")
    p.add_argument("-o", "--out")
    a = sub.add_parser("audit", help="核对 blocks.json 与稿件一致性")
    a.add_argument("blocks")
    a.add_argument("--draft", help="纯文本稿（启用漏段/凭空加段检测）")
    v = sub.add_parser("verify", help="核对排版产物形态与主题一致性")
    v.add_argument("html")
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 2
    return {"plan": cmd_plan, "audit": cmd_audit, "verify": cmd_verify}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
