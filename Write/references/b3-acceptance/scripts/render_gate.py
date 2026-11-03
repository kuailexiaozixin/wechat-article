# -*- coding: utf-8 -*-
"""B4 渲染 · 390px 真机渲染的调用、留痕与截图核对。

**不重新实现渲染判据**。渲染层唯一实现是同目录的 `qa_mobile.py`
（横向溢出 / display:table*|grid / 坏图 / 整页截图）。本脚本管 qa_mobile 不管的三件事：

    preflight  —— 跑之前查环境（浏览器、playwright、图是否已是 mmbiz），
                  把「跑不起来」和「跑了但没过」分开报，避免把环境问题读成内容问题
    run        —— 调 qa_mobile --json，落盘结构化结果 + 记录截图路径与尺寸
    review     —— 核对截图本身（存在、非空、宽 == 目标宽、高度合理），
                  并汇总「人工该看截图的哪几处」——这是 B5 的输入

为什么截图也要核：`qa_mobile` 的退出码只覆盖像素与 computed style 的可测项。
截图没落盘、只有半屏、宽度和 --width 不一致，都不会反映在退出码里，
但会让 B5 的「人工观感确认」变成对着空气签字。

退出码：0 = 通过；1 = 有 FAIL；2 = 环境不满足（不是稿件问题，别改稿）。
"""
import argparse
import io
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
QA_NAME = "qa_mobile.py"
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def find_ref_script(name):
    d = HERE
    for _ in range(8):
        for cand in (os.path.join(d, name),
                     os.path.join(d, "scripts", name),
                     os.path.join(d, "Write", "scripts", name)):
            if os.path.isfile(cand):
                return cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


def _png_size(path):
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:  # noqa: BLE001
        return "unreadable"


def cmd_preflight(args):
    fails, warns, notes = [], [], []
    qa = find_ref_script(QA_NAME)
    if qa is None:
        fails.append("找不到 %s（自 %s 上溯 8 层）" % (QA_NAME, HERE))
    else:
        notes.append("渲染判据源：%s" % qa)
    try:
        import playwright  # noqa: F401
        notes.append("playwright 已安装")
    except ImportError:
        fails.append("未安装 playwright —— qa_mobile 无法启动浏览器；"
                     "按本机 uv 规则装到 D:\\Python，勿用灵犀内置 python-env")
    found = next((b for b in BROWSERS if os.path.isfile(b)), None)
    if found:
        notes.append("可启动的浏览器：%s" % found)
    else:
        warns.append("未在标准路径找到 Edge/Chrome；qa_mobile 会退到 Playwright 默认 "
                     "Chromium，若也没装则整体失败（环境未满足，非稿件问题）")
    if args.html:
        if not os.path.isfile(args.html):
            fails.append("待渲染文件不存在：%s" % args.html)
        else:
            src = io.open(args.html, encoding="utf-8", errors="replace").read()
            local = [u for u in __import__("re").finditer(r'src="([^"]+)"', src)
                     if not u.group(1).startswith(("http://", "https://", "data:"))]
            if local:
                fails.append("仍有 %d 处本地图片路径——B4 的坏图检测会因此全红，"
                             "先回 B1 换 mmbiz URL" % len(local))
            if not args.allow_offline and "mmbiz.qpic.cn" in src:
                notes.append("含 mmbiz 图：需联网，否则 naturalWidth==0 会被判坏图；"
                             "离线跑请加 --no-image-check（本脚本会转记 SKIP）")
    print("=== B4 渲染前置体检 ===")
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    for x in notes:
        print("  [INFO]", x)
    if fails:
        print("[FAIL] 环境/前置不满足 —— 先修环境，别改稿")
        return 2 if not any("待渲染文件" in x or "本地图片" in x for x in fails) else 1
    print("[PASS] 前置满足，可以跑 qa_mobile")
    return 0


def cmd_run(args):
    qa = find_ref_script(QA_NAME)
    if qa is None:
        print("ERR 找不到 qa_mobile.py，无法执行渲染验收")
        return 2
    width = args.width
    shot = args.screenshot or (os.path.splitext(args.html)[0] + "_qa%d.png" % width)
    cmd = [sys.executable, qa, args.html, "--width", str(width),
           "--screenshot", shot, "--json"]
    if args.no_image_check:
        cmd.append("--no-image-check")
    print("$ " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=args.timeout)
    except subprocess.TimeoutExpired:
        print("[FAIL] 渲染超时 %ds（浏览器可能被登录框/更新弹窗卡住）" % args.timeout)
        return 2
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    data = None
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                break
            except ValueError:
                pass
    if data is None:
        print("[FAIL] 未取到 qa_mobile 的 JSON 输出；原样转述：")
        if out:
            print(out)
        if err:
            print(err, file=sys.stderr)
        return 2
    if args.out:
        json.dump(data, io.open(args.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("saved ->", args.out)
    passed = proc.returncode == 0
    print("=== B4 渲染结果（判据源 qa_mobile.py，未改写）===")
    print(json.dumps(data, ensure_ascii=False, indent=1)[:1500])
    print("qa_mobile 退出码 = %d → %s" % (proc.returncode, "PASS" if passed else "FAIL"))
    if not passed:
        print("[FAIL] 渲染层未过 —— 回 B2 改布局（不是改文案），修完重跑 B3+B4")
    return 0 if passed else 1


def cmd_review(args):
    """核对截图本身，并打印 B5 的人工观感清单。"""
    fails, warns, items = [], [], []
    shot = args.screenshot
    if not os.path.isfile(shot):
        fails.append("截图不存在：%s ——「人工已确认观感」这句话不能签" % shot)
    else:
        size = os.path.getsize(shot)
        if size < 2000:
            fails.append("截图仅 %d 字节，几乎确定是空白/失败产物" % size)
        dims = _png_size(shot)
        if dims is None:
            warns.append("未装 Pillow，跳过截图尺寸核对（本项记 SKIP，不冒充通过）")
        elif dims == "unreadable":
            fails.append("截图读不出尺寸，可能不是合法 PNG")
        else:
            w, h = dims
            items.append("截图 %d×%d 字节 %d" % (w, h, size))
            if args.width and abs(w - args.width) > 2:
                fails.append("截图宽 %d 与目标视口 %d 不符——截图来自别的宽度，"
                             "不能作为 390px 验收证据" % (w, args.width))
            if h < w:
                fails.append("截图高 %d < 宽 %d，不像整页截图（只截了首屏？）" % (h, w))
            elif h > 60000:
                warns.append("截图高 %d 异常大，确认整页渲染没有被长表格撑爆" % h)
            else:
                items.append("整页高度 %dpx ≈ 手机屏 %d 屏，逐屏核对下列四项："
                             % (h, max(1, round(h / 780.0))))
    print("=== B4 截图核对与人工观感入口 ===")
    for x in fails:
        print("  [FAIL]", x)
    for x in warns:
        print("  [WARN]", x)
    for x in items:
        print("  [INFO]", x)
    print("  人工看截图的四件事（脚本查不到）：")
    print("   1. 首屏有没有一句完整的话（滚动前必须交代清主题）")
    print("   2. 代码块是否换行折断、缩进是否还看得出层级")
    print("   3. 每张图是否居中、图注编号与出现顺序是否一致")
    print("   4. 有没有大面积深色/紫底色块（theme-default 避开，代码块深灰底除外）")
    if fails:
        print("[FAIL] 截图证据不成立 —— 重跑 qa_mobile，不要跳过观感确认")
        return 1
    print("[PASS] 截图证据成立，转 B5 人工自查")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("preflight", help="跑之前查环境")
    p.add_argument("html", nargs="?")
    p.add_argument("--allow-offline", action="store_true")
    r = sub.add_parser("run", help="调 qa_mobile 并留痕")
    r.add_argument("html")
    r.add_argument("--width", type=int, default=390)
    r.add_argument("--screenshot")
    r.add_argument("--no-image-check", action="store_true")
    r.add_argument("--timeout", type=int, default=120)
    r.add_argument("-o", "--out", help="结构化结果落盘 json")
    v = sub.add_parser("review", help="核对截图本身")
    v.add_argument("screenshot")
    v.add_argument("--width", type=int, default=390)
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 2
    return {"preflight": cmd_preflight, "run": cmd_run, "review": cmd_review}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
