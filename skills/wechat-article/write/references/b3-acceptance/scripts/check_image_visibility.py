#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B3 图片可见性闸：在「与编辑器一致的 http://127.0.0.1 静态服务」里验证配图真能看见。

为什么需要这道闸（5.16.2）：
  旧版 qa_mobile.py 用 file:// 打开做坏图检测，微信图床在 file:// 下能加载，
  于是判据全绿；但用户在 WorkBuddy 编辑器 / Edge 里打开的是
  http://127.0.0.1:<port>/static-html/... ，外链可能被 CSP、防盗链、代理或断网拦掉，
  看到的是破图图标。判据环境与查看环境不一致 = 假绿。
  红线文档还断言「mmbiz URL 公网可达，浏览器直接打开即可看到全部配图」，
  把本地可见性完全押在外网上，并禁止内嵌兜底——这是规范层面的错误。

本闸跑两轮，两轮都必须过：
  A 在线轮：不拦截，所有 <img> naturalWidth > 0
  B 离线轮：掐断全部 mmbiz 请求，所有 <img> 仍可见
            （onerror 换成内嵌 src，或 background-image 兜底且元素有实际高度）
无 <img>（例如全内联 SVG 的自包含图形）直接 PASS。
无 playwright 时返回 PENDING，不算通过。

5.16.3 稳定性修复：在线轮原本固定等 2.5 秒就探测，微信图床偶发慢时，
后半段图片仍在加载会被 naturalWidth=0 误判成坏图（假 FAIL）。
改为先等所有 <img> 结束加载（上限 timeout 秒）再探测；加载失败的图
complete 也为 true，仍会被判出，不会放过真坏图。

用法:
    check_image_visibility.py <article-wx.html> [--json out.json] [--timeout 15]
退出码: 0 = PASS；1 = FAIL；2 = PENDING / 用法错误
纯自动，不需要任何人工操作。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import importlib.util
import io
import json
import os
import re
import socketserver
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
RENDER_MERMAID = os.path.normpath(
    os.path.join(HERE, "..", "..", "b1-images", "scripts", "render_mermaid.py"))


def _launcher():
    spec = importlib.util.spec_from_file_location("render_mermaid", RENDER_MERMAID)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.launch_browser


def serve(directory):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


PROBE_JS = """() => Array.from(document.images).map(i => {
    const r = i.getBoundingClientRect();
    const bg = getComputedStyle(i).backgroundImage;
    return {
        nw: i.naturalWidth,
        inline: i.src.startsWith('data:'),
        bg: bg && bg.startsWith('url('),
        h: Math.round(r.height)
    };
})"""


def probe(browser, url, offline, timeout):
    ctx = browser.new_context(viewport={"width": 390, "height": 900})
    page = ctx.new_page()
    if offline:
        page.route("**/*mmbiz.qpic.cn/**", lambda route: route.abort())
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
        if offline:
            # 外链被掐断后图片立即 complete，短等即可让背景兜底完成布局
            page.wait_for_timeout(800)
        else:
            # 5.16.3：CDN 偶发慢时，固定等 2.5 秒会把「仍在加载」误判成坏图。
            # 先等所有 <img> 结束加载（上限 timeout 秒），等不到再按现状探测；
            # 真正加载失败的图仍会由 naturalWidth=0 判出，不会放过坏图。
            try:
                page.wait_for_function(
                    "() => Array.from(document.images).every(i => i.complete)",
                    timeout=timeout * 1000)
            except Exception:
                pass
            page.wait_for_timeout(300)
        imgs = page.evaluate(PROBE_JS)
        if offline:
            # 离线时允许两条兜底路径中的任意一条生效
            ok = [x for x in imgs
                  if x["nw"] > 0 or (x["bg"] and x["h"] > 50)]
        else:
            ok = [x for x in imgs if x["nw"] > 0]
        return {"total": len(imgs), "visible": len(ok),
                "bad": [i + 1 for i, x in enumerate(imgs)
                        if not (x["nw"] > 0 or (offline and x["bg"] and x["h"] > 50))]}
    finally:
        ctx.close()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("html")
    ap.add_argument("--json", dest="json_out")
    ap.add_argument("--timeout", type=int, default=15)
    a = ap.parse_args()

    if not os.path.isfile(a.html):
        print("ERR HTML 不存在：%s" % a.html)
        return 2
    html_path = os.path.abspath(a.html)
    text = io.open(html_path, encoding="utf-8", errors="replace").read()
    if not re.search(r"<img[\s>]", text, re.I):
        result = {"status": "PASS", "reason": "无 <img> 标签（可能为内联 SVG 自包含图形），无需外链可见性检查",
                  "images": 0}
    else:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            result = {"status": "PENDING", "reason": "本机无 playwright，图片可见性未真正跑过"}
        else:
            httpd, port = serve(os.path.dirname(html_path))
            url = "http://127.0.0.1:%d/%s" % (port, os.path.basename(html_path))
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser, name = _launcher()(p)
                    try:
                        online = probe(browser, url, False, a.timeout)
                        offline = probe(browser, url, True, a.timeout)
                    finally:
                        browser.close()
                ok_a = online["total"] == online["visible"]
                ok_b = offline["total"] == offline["visible"]
                result = {
                    "status": "PASS" if (ok_a and ok_b) else "FAIL",
                    "browser": name, "origin": url,
                    "online": online, "offline": offline,
                    "reason": "" if (ok_a and ok_b) else
                              ("在线轮坏图 %s" % online["bad"] if not ok_a else "") +
                              ("；离线轮坏图 %s（外链被拦后无内嵌兜底）" % offline["bad"] if not ok_b else ""),
                }
            finally:
                httpd.shutdown()

    print("[%s] 图片可见性 —— %s" % (result["status"], result.get("reason") or "在线/离线两轮全部可见"))
    if result.get("online"):
        print("  在线：%d/%d 可见 · 离线（外链全掐断）：%d/%d 可见"
              % (result["online"]["visible"], result["online"]["total"],
                 result["offline"]["visible"], result["offline"]["total"]))
    if a.json_out:
        json.dump(result, io.open(a.json_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    return {"PASS": 0, "FAIL": 1, "PENDING": 2}[result["status"]]


if __name__ == "__main__":
    sys.exit(main())
