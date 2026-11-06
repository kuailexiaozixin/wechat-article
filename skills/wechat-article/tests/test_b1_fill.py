# -*- coding: utf-8 -*-
"""A3→B1 图位占位回填交接判据：fill_placeholders / check_urls 残留 / upload_imgs.manifest_need。

背景（5.4.1）：A3 逻辑 L5 直出的正文图是 `__MMP__:<filename>` 占位，B1 上传后由
`fill_placeholders.py` 回填、`check_urls.py --html` 核残留清零。本判据固化这条交接，
防止「占位符 B1 不认识、回填无人做」的断点复现。
纯本地（不含凭据与网络）：用临时 fixture 驱动。
"""
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
B1 = os.path.join(ROOT, "Write", "references", "b1-images", "scripts")
FILL = os.path.join(B1, "fill_placeholders.py")
CHECK = os.path.join(B1, "check_urls.py")
UPLOAD = os.path.join(B1, "upload_imgs.py")

def _run(script, *args):
    p = subprocess.run([sys.executable, script, *args], capture_output=True, text=True,
                       encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def run():
    fails = []
    import tempfile
    d = tempfile.mkdtemp()

    # 语法可编译
    import py_compile
    for f in (FILL, CHECK, UPLOAD):
        try:
            py_compile.compile(f, doraise=True)
        except Exception as e:  # noqa: BLE001
            fails.append("语法失败 %s：%s" % (os.path.basename(f), e))
            return fails

    # 1. fill 正向：key 全在 map
    html1 = os.path.join(d, "a1.html")
    io.open(html1, "w", encoding="utf-8", newline="\n").write(
        '<img src="__MMP__:f01"><img src="__MMP__:f02">')
    m1 = os.path.join(d, "m1.json")
    io.open(m1, "w", encoding="utf-8").write(json.dumps(
        {"f01": "https://mmbiz.qpic.cn/a", "f02": "https://mmbiz.qpic.cn/b"}))
    rc, out = _run(FILL, "--html", html1, "--map", m1)
    body = io.open(html1, encoding="utf-8").read()
    if rc != 0:
        fails.append("fill 正向应退出 0，实际 %d：%s" % (rc, out[:200]))
    if "__MMP__" in body:
        fails.append("fill 正向后 HTML 仍残留占位：%s" % body[:120])
    if "https://mmbiz.qpic.cn/a" not in body or "https://mmbiz.qpic.cn/b" not in body:
        fails.append("fill 正向未回填 mmbiz URL：%s" % body[:120])

    # 2. fill 反向：缺 key
    html2 = os.path.join(d, "a2.html")
    io.open(html2, "w", encoding="utf-8", newline="\n").write(
        '<img src="__MMP__:f01"><img src="__MMP__:f02">')
    m2 = os.path.join(d, "m2.json")
    io.open(m2, "w", encoding="utf-8").write(json.dumps({"f01": "https://mmbiz.qpic.cn/a"}))
    rc, out = _run(FILL, "--html", html2, "--map", m2, "--dry-run")
    if rc != 1 or "f02" not in out:
        fails.append("fill 反向缺 key 应退出 1 且列出 f02，实际 %d：%s" % (rc, out[:150]))

    # 3. check_urls 残留占位判据
    html3 = os.path.join(d, "a3.html")
    io.open(html3, "w", encoding="utf-8", newline="\n").write('<img src="__MMP__:f99">')
    m3 = os.path.join(d, "m3.json")
    io.open(m3, "w", encoding="utf-8").write(json.dumps({"z": "http://127.0.0.1:1/z.png"}))
    rc, out = _run(CHECK, "--map", m3, "--html", html3)
    if "残留占位" not in out:
        fails.append("check_urls --html 未检出残留占位判据：%s" % out[:150])

    # 4. upload_imgs.manifest_need：按 filename 收集正文图路径
    import importlib.util
    spec = importlib.util.spec_from_file_location("upload_imgs_mod", UPLOAD)
    up = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(up)
    except SystemExit:
        # wx_api 缺失等情况下 import 期 SystemExit；仅验证 parse/manifest_need 逻辑
        fails.append("upload_imgs import 期异常，无法测 manifest_need")
    else:
        man = os.path.join(d, "manifest.json")
        io.open(man, "w", encoding="utf-8").write(json.dumps({"figures": [
            {"id": "f01", "kind": "body", "tool": "mermaid", "filename": "f01.png"},
            {"id": "c01", "kind": "cover", "tool": "none", "filename": "cover.png"},
            {"id": "x01", "kind": "body", "tool": "none", "filename": "none.png"},
        ]}))
        got = up.manifest_need(man, None)
        basenames = sorted(os.path.basename(g) for g in got)
        if basenames != ["f01.png"]:
            fails.append("manifest_need 只应收正文图 f01.png（非 cover、非 tool=none），实际 %s" % basenames)
        # parse 识别 --manifest / --img-root
        p = up.parse(["--manifest", man, "--img-root", d, "--html", "h.html", "--map", "m.json"])
        if not (p[0] == "h.html" and p[3] == man and p[4] == d and p[2] == "m.json"):
            fails.append("upload parse 未正确解析新参数：%s" % (p,))

    if fails:
        for f in fails:
            print("FAIL", f)
    print("B1 占位回填交接判据：%s" % ("全部通过" if not fails else "%d 项失败" % len(fails)))
    return fails

if __name__ == "__main__":
    sys.exit(1 if run() else 0)
