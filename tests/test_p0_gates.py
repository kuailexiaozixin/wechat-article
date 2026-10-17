# -*- coding: utf-8 -*-
"""P0 三处闸口离线测试（不联网、不需凭据；全部用假数据打桩）。

覆盖：
  1. wx_draft_push.py —— 含 <table> 的 HTML 必须在取 token 之前被拦下（进程退出码 1，
     输出 PUSH_BLOCKED，且不得出现 "TOKEN ok"）。
  2. wx_api.py draft-update —— 腾讯 WAF 501 绕行成功后必须打印 MEDIA_ID_CHANGED
     old/new 与「对新 id 重跑 check_draft.py」提示。
  3. check_draft.py --source —— 源稿改过未重推时，一致比必须判 FAIL；
     源稿与草稿一致时必须判 PASS。
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BAD_HTML = os.path.join(HERE, "fixtures", "wx_block_table.html")
GOOD_HTML = os.path.join(HERE, "fixtures", "wx_block_clean.html")


def _load(name, relpath):
    path = os.path.join(ROOT, relpath)
    sys.path.insert(0, os.path.dirname(path))     # check_draft.py 同目录 import wx_api
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_push_gate():
    fails = []
    env = dict(os.environ, WECHAT_APPID="fake", WECHAT_SECRET="fake")
    for html, want_blocked in ((BAD_HTML, True), (GOOD_HTML, False)):
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "wx_draft_push.py"),
                            "--html", html, "--title", "闸口测试标题",
                            "--digest", "测试摘要"],
                           capture_output=True, text=True, encoding="utf-8", env=env)
        out = (r.stdout or "") + (r.stderr or "")
        blocked = "PUSH_BLOCKED" in out
        if blocked != want_blocked:
            fails.append("%s: 期望拦截=%s 实得拦截=%s｜%s"
                         % (os.path.basename(html), want_blocked, blocked, out[:200]))
        if "TOKEN ok" in out:
            fails.append("%s: 校验闸口未前置，已走到取 token" % os.path.basename(html))
    return fails


def test_waf_bypass_notice():
    api = _load("wx_api_t", os.path.join("scripts", "wx_api.py"))
    os.environ["WECHAT_APPID"], os.environ["WECHAT_SECRET"] = "fake", "fake"
    calls = []

    def fake(url, data=None, headers=None, method=None):
        calls.append(url)
        if "/token" in url:
            return {"access_token": "T", "expires_in": 7200}
        if "/draft/get" in url:
            return {"news_item": [{"thumb_media_id": "THUMB", "title": "旧标题"}]}
        if "/draft/update" in url:
            return {"errcode": 501, "errmsg": "WAF block"}
        if "/draft/delete" in url:
            return {"errcode": 0}
        if "/draft/add" in url:
            return {"media_id": "NEW_MID_123"}
        return {"errcode": 0}

    api.http_json = fake
    html = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8")
    html.write("<section><p>正文</p></section>")
    html.close()
    err = io.StringIO()
    sys.argv = ["wx_api.py", "draft-update", "--media", "OLD_MID", "--title", "标题",
                "--digest", "摘要", "--content", html.name]
    try:
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            api.main()
    except SystemExit:
        pass
    finally:
        os.unlink(html.name)
    text = err.getvalue()
    fails = []
    if "MEDIA_ID_CHANGED" not in text:
        fails.append("501 绕行成功但未打印 MEDIA_ID_CHANGED：%s" % text[:200])
    if "OLD_MID" not in text or "NEW_MID_123" not in text:
        fails.append("MEDIA_ID_CHANGED 未带上新旧 id：%s" % text[:200])
    if "check_draft" not in text:
        fails.append("绕行出口未提示对新 id 重跑核验：%s" % text[:200])
    return fails


def test_source_consistency():
    cd = _load("check_draft_t", os.path.join("scripts", "check_draft.py"))
    src = os.path.join(HERE, "fixtures", "wx_block_clean.html")
    with open(src, encoding="utf-8") as f:
        source_html = f.read()
    cd.get_token = lambda a, s: {"access_token": "T"}
    fails = []

    def make_draft(content):
        def _dg(token, media_id):
            return {"news_item": [{"title": "标题", "digest": "摘要",
                                   "thumb_media_id": "THUMB", "content": content}]}
        cd.draft_get = _dg

    make_draft(source_html)
    res = cd.check("MID", source_path=src)
    names = {n: st for n, st, _ in res["checks"]}
    if names.get("正文与源一致") != "PASS":
        fails.append("源稿与草稿一致却判 FAIL：%s" % names)

    make_draft(source_html.replace("闸口测试", "闸口测试-已改"))
    res2 = cd.check("MID", source_path=src)
    names2 = {n: (st, d) for n, st, d in res2["checks"]}
    st, detail = names2.get("正文与源一致", ("MISSING", ""))
    if st != "FAIL":
        fails.append("源稿改过未重推却判 PASS（一致比失效）：%s" % st)
    if "首个差异" not in detail:
        fails.append("FAIL 未给出首个差异位置，人工无从定位：%s" % detail)
    return fails


def run():
    fails = []
    for fn in (test_push_gate, test_waf_bypass_notice, test_source_consistency):
        sub = fn()
        print("%-24s %s" % (fn.__name__, "OK" if not sub else "FAIL ×%d" % len(sub)))
        fails += ["%s: %s" % (fn.__name__, f) for f in sub]
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
