# -*- coding: utf-8 -*-
"""草稿回读自动核验器（推送后必跑，替代人工逐项核对）。

用法:
    python check_draft.py <media_id> [--expect-imgs N] [--json]

检查项（对 draft-get 返回的草稿断言）:
  - title  <= 64 字节（UTF-8 编码长度，中文 3 字节/字）
  - digest <= 120 字符
  - thumb_media_id 非空（封面已设置）
  - content 不含 <pre>（代码块结构合规，未被微信剥离）
  - content 不含 <style>（样式必须内联）
  - content 不含 display:table/table-cell 伪表格（微信端堆叠，0088 实测）
  - content 中 mmbiz.qpic.cn 图片数 == --expect-imgs（给定 N 时）
  - content 不含本地图片路径（../assets/ 之类）

输出: 逐项 [PASS]/[FAIL] + 摘要行；--json 输出结构化结果。
退出码: 0 = 全部 PASS; 1 = 有 FAIL（必须修复后重推）。

凭据从环境变量 WECHAT_APPID / WECHAT_SECRET 读取（同 wx_api.py）。
"""
import os
import re
import sys
import json

from wx_api import get_token, http_json, API


def draft_get(token, media_id):
    return http_json(
        f"{API}/draft/get?access_token={token}",
        data=json.dumps({"media_id": media_id}, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )


def b_len(s):
    return len(s.encode("utf-8"))


def char_len(s):
    return len(s)


def check(media_id, expect_imgs=None):
    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET")
    if not appid or not secret:
        return {"ok": False, "checks": [("凭据", "FAIL", "WECHAT_APPID / WECHAT_SECRET 未设置")]}

    tok = get_token(appid, secret)
    if "access_token" not in tok:
        return {"ok": False, "checks": [("token", "FAIL", json.dumps(tok, ensure_ascii=False))]}
    token = tok["access_token"]

    res = draft_get(token, media_id)
    if "news_item" not in res:
        return {"ok": False, "checks": [("draft-get", "FAIL",
                                         json.dumps(res, ensure_ascii=False)[:200])]}

    art = (res.get("news_item") or [{}])[0]
    title = art.get("title", "")
    digest = art.get("digest", "")
    thumb = art.get("thumb_media_id", "")
    content = art.get("content", "")

    checks = []
    ok = True

    def add(name, passed, detail=""):
        nonlocal ok
        if not passed:
            ok = False
        checks.append((name, "PASS" if passed else "FAIL", detail))

    add("title<=64B", b_len(title) <= 64, f"{b_len(title)}B / {title[:20]}")
    add("digest<=120", char_len(digest) <= 120, f"{char_len(digest)}字")
    add("thumb 非空", bool(thumb), thumb[:24])
    n_pre = len(re.findall(r"<pre[\s>]", content, re.I))
    add("无 <pre>", n_pre == 0, f"<pre>×{n_pre}")
    n_style = len(re.findall(r"<style[\s>]", content, re.I))
    add("无 <style>", n_style == 0, f"<style>×{n_style}")
    n_pseudo = len(re.findall(r"display\s*:\s*table(?:-cell|-row|-column)?\b", content, re.I))
    add("无 div 伪表格", n_pseudo == 0, f"display:table×{n_pseudo}")

    n_mmbiz = len(re.findall(r'mmbiz\.qpic\.cn', content))
    n_local = len(re.findall(r'<img[^>]*\bsrc\s*=\s*["\'](?!https?://)[^"\']*["\']', content, re.I))
    if expect_imgs is not None:
        add(f"mmbiz 图数=={expect_imgs}", n_mmbiz == int(expect_imgs),
            f"实际 mmbiz 引用×{n_mmbiz}")
    else:
        add("有正文图", n_mmbiz > 0, f"mmbiz 引用×{n_mmbiz}")
    add("无本地图片路径", n_local == 0, f"本地路径×{n_local}")

    summary = {
        "media_id": media_id,
        "title": title,
        "digest_len": char_len(digest),
        "title_bytes": b_len(title),
        "has_thumb": bool(thumb),
        "mmbiz_imgs": n_mmbiz,
        "local_imgs": n_local,
        "pre_count": n_pre,
        "pseudo_table": n_pseudo,
    }
    return {"ok": ok, "checks": checks, "summary": summary}


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        sys.exit(1)
    media_id = argv[0]
    expect_imgs = None
    as_json = False
    i = 1
    while i < len(argv):
        if argv[i] == "--expect-imgs" and i + 1 < len(argv):
            expect_imgs = int(argv[i + 1]); i += 2
        elif argv[i] == "--json":
            as_json = True; i += 1
        else:
            i += 1

    result = check(media_id, expect_imgs)
    if as_json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"=== 草稿回读核验: {media_id} ===")
        s = result.get("summary", {})
        if s:
            print(f"  标题: {s.get('title','')[:40]}")
            print(f"  标题 {s.get('title_bytes')}B · 摘要 {s.get('digest_len')}字 · "
                  f"封面 {'有' if s.get('has_thumb') else '无'} · "
                  f"mmbiz图×{s.get('mmbiz_imgs')} · 本地路径×{s.get('local_imgs')} · "
                  f"<pre>×{s.get('pre_count')} · 伪表格×{s.get('pseudo_table')}")
        for name, st, detail in result.get("checks", []):
            print(f"  [{st}] {name}  {detail}")
        print("[PASS] 核验全部通过，可交付" if result.get("ok") else "[FAIL] 存在未通过项，须修复后重推")
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
