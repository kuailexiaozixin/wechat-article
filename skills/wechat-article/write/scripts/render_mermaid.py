# -*- coding: utf-8 -*-
"""用 Playwright 渲染 mermaid 图为 PNG（不安装新浏览器，按可用性依次尝试）。

用法：python render_mermaid.py <a.mmd> [b.mmd ...]
输出：每个 .mmd 的同目录同名 .png。
依赖：playwright（已安装）。
浏览器 fallback 链（3.4.0 起）：系统 Edge（channel=msedge）→ 系统 Chrome（channel=chrome）
→ Playwright 默认 Chromium（需已装 ms-playwright 浏览器）。全部不可用时给出明确报错。
"""
import os
import sys

from playwright.sync_api import sync_playwright

HTML_TMPL = """<!DOCTYPE html><html><head><meta charset="utf-8">
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
</head><body>
<div class="mermaid">__MERMAID_CODE__</div>
<script>
mermaid.initialize({
  startOnLoad: false,
  theme: 'base',
  themeVariables: {
    primaryColor: '#FFFFFF',
    primaryBorderColor: '#B08D3E',
    primaryTextColor: '#1F3864',
    lineColor: '#1F3864',
    fontFamily: 'Microsoft YaHei, SimHei, sans-serif',
    fontSize: '15px'
  },
  flowchart: {htmlLabels: true, curve: 'basis'},
  securityLevel: 'loose'
});
window.__render = async function() {
  try {
    const el = document.querySelector('.mermaid');
    const {svg} = await mermaid.render('graphDiv', el.textContent);
    el.innerHTML = svg;
    const r = el.getBoundingClientRect();
    document.title = 'OK:' + Math.ceil(r.width) + 'x' + Math.ceil(r.height);
  } catch(e) {
    document.title = 'ERR:' + e.message;
  }
};
</script></body></html>"""


def launch_browser(playwright):
    """按 fallback 链启动 Chromium 系浏览器：msedge → chrome → 默认。"""
    attempts = [
        ("msedge", {"channel": "msedge"}),
        ("chrome", {"channel": "chrome"}),
        ("default", {}),
    ]
    last_err = None
    for name, kw in attempts:
        try:
            return playwright.chromium.launch(**kw), name
        except Exception as e:  # noqa: BLE001
            last_err = e
    raise SystemExit(
        "ERR 无法启动浏览器（已尝试 msedge / chrome / 默认 Chromium）。\n"
        f"   最后错误: {last_err}\n"
        "   解决: 安装 Microsoft Edge 或 Chrome；或运行 `playwright install chromium` "
        "安装 Playwright 默认浏览器。")


def render_one(browser, browser_name, mmd_path, out_png):
    with open(mmd_path, encoding="utf-8") as f:
        code = f.read()
    html = HTML_TMPL.replace("__MERMAID_CODE__", code)
    page = browser.new_page(viewport={"width": 1500, "height": 1100})
    try:
        page.set_content(html, wait_until="networkidle", timeout=60000)
        page.evaluate("window.__render()")
        title = page.title()
        if not title.startswith("OK:"):
            print("ERR render", os.path.basename(mmd_path), title[:160])
            return False
        w, h = title[3:].split("x")
        page.locator(".mermaid").screenshot(path=out_png, timeout=30000)
        print("OK", os.path.basename(mmd_path), "->", os.path.basename(out_png),
              w + "x" + h, "(" + browser_name + ")")
        return True
    finally:
        page.close()


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return
    if not argv:
        print(__doc__)
        sys.exit(1)
    # 先校验全部输入文件存在（启动浏览器前快速失败，避免空跑）
    for t in argv:
        if not os.path.exists(t):
            print("ERR 文件不存在:", t)
            sys.exit(1)
    with sync_playwright() as p:
        browser, browser_name = launch_browser(p)
        try:
            for t in argv:
                out = t[:-4] + ".png" if t.lower().endswith(".mmd") else t + ".png"
                if not render_one(browser, browser_name, t, out):
                    sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
