# -*- coding: utf-8 -*-
"""B4 推送 · 验收包核验 + 参数预检 + 调根 wx_draft_push.py + 捕获 media_id。

**不重复实现任何判据**。真正发请求的是根 `scripts/wx_draft_push.py`，它内部已加载
B3 的 validate() 作为硬闸（ERROR>0 直接退出、不取 token）；本脚本的形态检查只有它自己
的接口参数（title 字节 / digest 字符），不再粗筛正文标签——那是 B3 验收包的职责，
这里只核「验收包本身合格且对的是这份 HTML」：

    1. 验收包必查 —— --acceptance 必需，overall 必须为 PASS（PENDING 也不放行：
       渲染子闸没跑过 ≠ 通过），缺包即挡。旧版 --b5/--b3/--b4 散装可选参数
       「漏传就绕过」的问题由此从接口上消除。
    2. 指纹核对 —— 验收包里的 html_sha256 必须等于当前 HTML 的 sha256：
       防止「验收的是 A 版、推送的是 B 版」。
    3. 捕获句柄 —— 从 stdout 抠出 media_id，连同 html_sha256 落盘 push.json
       直接喂给 B5 回读，避免人工复制 id、并为「改了没重推」提供哈希基准。

子命令：
    precheck --html <a.html> --acceptance <json> [--title .. --digest ..]
    push     --html <a.html> --acceptance <json> --title ".." --digest ".."
             [--cover <img>] [--dry] [-o push.json]

--dry 只跑本地核验（验收包 + 指纹 + 参数），不取 token 不发请求。
退出码：0 = 放行；1 = 有 FAIL；2 = 用法/环境错误。
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys


def _root_scripts():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        cand = os.path.join(d, "scripts", "wx_draft_push.py")
        if os.path.isfile(cand):
            return cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


def _utf8_bytes(s):
    return len(s.encode("utf-8"))


def _html_sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def check_acceptance(html, acc_path):
    """验收包三查：存在、overall==PASS、指纹对得上这份 HTML。返回 fails 列表。"""
    fails = []
    if not acc_path:
        return ["缺少 --acceptance：B3 验收包是推送的唯一前置，没有它不许推"
                "（python Write/references/b3-acceptance/scripts/acceptance_pack.py ...）"]
    if not os.path.isfile(acc_path):
        return ["验收包不存在：%s" % acc_path]
    try:
        acc = json.load(io.open(acc_path, encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        return ["验收包不是合法 JSON：%s（%s）" % (acc_path, e)]
    overall = acc.get("overall")
    if overall != "PASS":
        detail = {g.get("status"): k for k, g in (acc.get("gates") or {}).items()}
        fails.append("验收包 overall=%s（%s）——PENDING 也不放行：子闸没真正跑完 ≠ 通过"
                     % (overall, detail or "无子闸明细"))
    sha = acc.get("html_sha256")
    cur = _html_sha256(html)
    if not sha:
        fails.append("验收包缺少 html_sha256——旧格式包，请用 acceptance_pack.py 重新生成")
    elif sha != cur:
        fails.append("指纹不一致：验收包记录 %s…，当前 HTML %s…——"
                     "验收后改过稿，回 B3 重跑验收" % (str(sha)[:12], cur[:12]))
    return fails


def cmd_precheck(args):
    fails = []
    if not os.path.isfile(args.html):
        return _report(["待推送 HTML 不存在：%s" % args.html])

    # 1) 接口参数预检（B4 自有职责；正文红线在 B3，不在此重复）
    if args.title is not None:
        b = _utf8_bytes(args.title)
        if b > 64:
            fails.append("--title %d 字节 > 64（约 21 个汉字，中文 3 字节/字）；"
                         "草稿标题取正文标题的短句，先缩短而不是截断" % b)
    if args.digest:
        if len(args.digest) > 120:
            fails.append("--digest %d 字符 > 120，会被截断或报错" % len(args.digest))

    # 2) 验收包三查（存在 / overall==PASS / 指纹一致）
    fails += check_acceptance(args.html, args.acceptance)
    return _report(fails)


def _report(fails):
    print("=== B4 推送前置核验 ===")
    for x in fails:
        print("  [FAIL]", x)
    if fails:
        print("[FAIL] %d 项——先补齐再推，不带错推送" % len(fails))
        return 1
    print("[PASS] 前置满足，可交 wx_draft_push.py 执行")
    return 0


def cmd_push(args):
    if cmd_precheck(args) != 0:
        print("[FAIL] 前置未过，取消推送")
        return 1
    sha = _html_sha256(args.html)
    if args.dry:
        print("[DRY] 仅本地核验，未取 token、未发请求、未产生草稿（指纹 %s…）" % sha[:12])
        return 0
    script = _root_scripts()
    if script is None:
        print("ERR 找不到根 scripts/wx_draft_push.py（自本文件上溯 8 层）")
        return 2
    cmd = [sys.executable, script, "--html", args.html,
           "--title", args.title or "", "--digest", args.digest or ""]
    if args.cover:
        cmd += ["--cover", args.cover]
    print("$ wx_draft_push.py（内置 B3 validate 硬闸：ERROR>0 直接退出、不取 token）")
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")
    out = proc.stdout or ""
    err = proc.stderr or ""
    print(out.rstrip())
    if err.strip():
        print(err.rstrip(), file=sys.stderr)
    m = re.search(r"DRAFT_OK media_id:\s*(\S+)", out)
    if proc.returncode == 0 and m:
        mid = m.group(1)
        print("MEDIA_ID=%s" % mid)
        if args.out:
            json.dump({"media_id": mid, "html": os.path.abspath(args.html),
                       "html_sha256": sha, "acceptance": os.path.abspath(args.acceptance)},
                      io.open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
            print("saved ->", args.out)
        print("[PASS] 已入草稿箱，必须进 B5 回读核验（readback_check.py --record）")
        return 0
    print("[FAIL] 推送未成功（退出码 %d）——按输出定位，别当已交付" % proc.returncode)
    return 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd")
    for name in ("precheck", "push"):
        p = sub.add_parser(name)
        p.add_argument("--html", required=True)
        p.add_argument("--acceptance", required=True,
                       help="B3 验收包 json（acceptance_pack.py 产出），必填")
        p.add_argument("--title")
        p.add_argument("--digest")
        if name == "push":
            p.add_argument("--cover")
            p.add_argument("--dry", action="store_true")
            p.add_argument("-o", "--out")
    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 2
    return {"precheck": cmd_precheck, "push": cmd_push}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
