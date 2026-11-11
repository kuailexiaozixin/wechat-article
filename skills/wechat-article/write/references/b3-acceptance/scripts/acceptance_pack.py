#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 验收 · 三子闸合一的验收包编排器。

**不重新实现任何判据**。三个子闸各自委托本目录既有实现：
  静态子闸 —— validate_wx_html.py 的 validate()（与 static_check.py 同一调用方式）
  渲染子闸 —— qa_mobile.py（子进程 --json；本机无 playwright 时 status=PENDING，不算通过）
  人工子闸 —— manual_signoff.py record 产出的签字 json（note 非空 + 截图文件仍在）
另做两件编排层的事：
  图数一致性 —— HTML 内 mmbiz 引用数 == B1 清单正文图数（取代原 B1 scan，消除环形依赖）
  指纹冻结 —— 对 HTML 原始字节算 sha256 写入验收包；B4 推送前比对此值，
              B5 回读时用推送记录里的哈希替代 mtime 判断「改了没重推」。

可选开关：--strict（WARNING 也判失败，对外发布建议开）；
         --no-image-check（离线环境跳过渲染子闸的坏图检测）。

产物 acceptance.json 是 B4 推送的**唯一**前置输入——散装三参数时代「漏传就绕过」的问题
从接口上消除。overall 语义：
  PASS     三子闸全绿（渲染子闸必须真跑过，PENDING 不算绿）
  PENDING  渲染子闸因环境不满足未跑（其余子闸已核）——不许推送，补环境后重跑
  FAIL     任一子闸不合格
退出码：0 = PASS；1 = FAIL；2 = PENDING 或用法/环境错误。
"""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# 图数一致性：数带 mmbiz src 的 <img> 标签（见 gate_figcount 说明）
IMG_MMBIZ_TAG = re.compile(r'<img[^>]*\bsrc\s*=\s*["\'][^"\']*mmbiz\.qpic\.cn', re.I)


def _load_validate():
    path = os.path.join(HERE, "validate_wx_html.py")
    if not os.path.isfile(path):
        raise SystemExit("ERR 找到不到静态规则源 %s——验收判据只有一份，本脚本不重复实现。" % path)
    spec = importlib.util.spec_from_file_location("validate_wx_html", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.validate


def gate_static(html_path, html_text, strict=False):
    validate = _load_validate()
    errors, warnings, checker = validate(html_text, html_path)
    bad = bool(errors) or (strict and bool(warnings))
    return {"status": "FAIL" if bad else "PASS", "strict": strict,
            "errors": errors, "warnings": warnings,
            "counts": {"img": checker.n_img, "p": checker.n_p, "section": checker.n_section}}


def gate_render(html_path, no_image_check=False):
    qa = os.path.join(HERE, "qa_mobile.py")
    if not os.path.isfile(qa):
        return {"status": "PENDING", "reason": "找不到 qa_mobile.py（%s）" % qa}
    cmd = [sys.executable, qa, html_path, "--json"]
    if no_image_check:
        cmd.append("--no-image-check")
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    data = None
    for line in (p.stdout or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                data = json.loads(line)
                break
            except ValueError:
                pass
    if "No module named" in (p.stderr or "") or "playwright" in (p.stderr or ""):
        return {"status": "PENDING", "reason": "本机无 playwright，渲染子闸未跑（不装新浏览器/不跑 playwright install；"
                                              "需按本机 uv 规则装到 D:\\Python 后重跑）",
                "stderr": (p.stderr or "")[-300:]}
    if data is None:
        return {"status": "PENDING", "reason": "qa_mobile 未返回 JSON（exit=%s）" % p.returncode,
                "stderr": (p.stderr or "")[-300:]}
    data["status"] = "PASS" if (p.returncode == 0 and data.get("ok")) else "FAIL"
    return data


def gate_manual(signoff_path):
    if not signoff_path:
        return {"status": "PENDING", "reason": "未提供人工签字记录（--signoff）；人工抽查是验收子闸，不可缺"}
    if not os.path.isfile(signoff_path):
        return {"status": "FAIL", "reason": "签字记录不存在：%s" % signoff_path}
    d = json.load(io.open(signoff_path, encoding="utf-8"))
    note = (d.get("note") or "").strip()
    shot = d.get("qa_screenshot")
    if not note or not shot or not os.path.isfile(shot):
        return {"status": "FAIL",
                "reason": "签字记录不完整（note 为空或截图已不在）——B3 人工子闸拒绝空签"}
    return {"status": "PASS", "signed_at": d.get("signed_at", "?"),
            "note": note, "qa_screenshot": shot}


def gate_figcount(html_text, manifest_path):
    # 数「带 mmbiz src 的 <img> 标签」，不是「域名字符串出现次数」——后者在正文里
    # 出现该域名（如代码示例）时会多算，与实际正文图数不符。
    # 断点修复：图数不符时输出 missing=[fXX]，指回 B1/B2 哪张图漏替换，而非只报数字差。
    n = len(IMG_MMBIZ_TAG.findall(html_text))
    if not manifest_path:
        return {"status": "PENDING", "reason": "未提供 --manifest，图数一致性未核（mmbiz×%d）" % n,
                "mmbiz_imgs": n}
    d = json.load(io.open(manifest_path, encoding="utf-8"))
    figs = d.get("figures") or []
    body = [f for f in figs if f.get("kind", "body") != "cover"]
    if not body:
        return {"status": "FAIL", "mmbiz_imgs": n, "expect": 0,
                "reason": "清单里没有正文图——无正文图时不要传 --manifest"}
    ok = n == len(body)
    missing = []
    if not ok:
        # 按 manifest 的 body 图顺序，HTML 里应出现 n 个 mmbiz <img>；
        # 若实际图数 < 清单数，把"按位置可能漏替的图"报出（filename 集合差）。
        # 这里无法精确到"第几张漏了"（HTML 未带 filename 注释），故报出清单里全部
        # 正文图 filename，提示回 B2 embed 核对哪个占位符没换成 mmbiz URL。
        if n < len(body):
            missing = [f.get("filename") or f.get("id") for f in body]
    result = {"status": "PASS" if ok else "FAIL", "mmbiz_imgs": n, "expect": len(body),
              "reason": "" if ok else "清单 %d 张正文图，HTML 里 mmbiz×%d——漏图或清单虚报" % (len(body), n)}
    if missing:
        result["missing_candidates"] = missing
        result["hint"] = "HTML 图数少于清单：回 B2 查哪些 __MMP__ 占位符没被 embed 替换成 mmbiz URL"
    return result


def gate_artifact_unique(html_path):
    """产物唯一性：稿件目录里只能有一份 wx-HTML（单文件铁律的机器判据）。

    委托同目录 check_single_artifact.py，不重复实现判据。B4 推送以本验收包为唯一
    前置输入，所以「多生成一份本地预览版」在这里会被拦下，而不是靠人记住规范。
    """
    script = os.path.join(HERE, "check_single_artifact.py")
    if not os.path.isfile(script):
        return {"status": "PENDING", "reason": "找不到 check_single_artifact.py"}
    directory = os.path.dirname(os.path.abspath(html_path))
    proc = subprocess.run(
        [sys.executable, script, "--dir", directory,
         "--main", os.path.basename(html_path)],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    status = {0: "PASS", 1: "FAIL", 2: "PENDING"}.get(proc.returncode, "FAIL")
    detail = (proc.stdout or proc.stderr or "").strip()[:400]
    return {"status": status, "reason": "" if status == "PASS" else detail}


def cmd_pack(args):
    if not os.path.isfile(args.html):
        print("ERR HTML 不存在：%s" % args.html)
        return 2
    raw = open(args.html, "rb").read()
    html_text = raw.decode("utf-8", errors="replace")
    sha = hashlib.sha256(raw).hexdigest()

    gates = {"static": gate_static(args.html, html_text, strict=args.strict),
             "render": gate_render(args.html, no_image_check=args.no_image_check),
             "manual": gate_manual(args.signoff),
             "figcount": gate_figcount(html_text, args.manifest),
             "artifact_unique": gate_artifact_unique(args.html)}

    statuses = [g["status"] for g in gates.values()]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "PENDING" in statuses:
        overall = "PENDING"
    else:
        overall = "PASS"

    pack = {"step": "B3-acceptance", "html": os.path.abspath(args.html),
            "html_sha256": sha, "overall": overall, "gates": gates}
    out = args.out or (os.path.splitext(args.html)[0] + "_acceptance.json")
    json.dump(pack, io.open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    for name, g in gates.items():
        print("  [%s] %s %s" % (g["status"], name,
                                ("— " + g.get("reason", "")) if g.get("reason") else ""))
    tag = {"PASS": "[PASS] 验收包已冻结（sha256 前 12 位 %s）——可进 B4 推送" % sha[:12],
           "PENDING": "[PENDING] 有子闸未真正跑完（见上）——不许推送，补齐后重跑本命令",
           "FAIL": "[FAIL] 有子闸不合格——修复后重跑 B2/B3"}[overall]
    print(tag)
    print("saved -> %s" % out)
    return {"PASS": 0, "PENDING": 2, "FAIL": 1}[overall]


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "-h" in argv or "--help" in argv or not argv:
        print(__doc__)
        return 0 if argv else 2
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--html", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--signoff")
    ap.add_argument("--screenshot", help="仅留痕：人工看过的截图路径（核验在签字 json 里）")
    ap.add_argument("--strict", action="store_true", help="WARNING 也判失败（对外发布建议开）")
    ap.add_argument("--no-image-check", action="store_true",
                    help="离线环境跳过渲染子闸的坏图检测（其判据仍在 B3 渲染子闸，此处只关联网那项）")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    return cmd_pack(a)


if __name__ == "__main__":
    sys.exit(main())
