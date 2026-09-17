# -*- coding: utf-8 -*-
"""用 Playwright + 系统已有 Edge 渲染 mermaid 图为 PNG（channel=msedge，不安装新浏览器）。

用法：python render_mermaid.py <a.mmd> [b.mmd ...]
输出：每个 .mmd 的同目录同名 .png。
依赖：playwright（已安装）；系统装有 Edge（channel=msedge）。
"""
import os, sys
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


def render_one(playwright, mmd_path, out_png):
    with open(mmd_path, encoding='utf-8') as f:
        code = f.read()
    html = HTML_TMPL.replace('__MERMAID_CODE__', code)
    browser = playwright.chromium.launch(channel='msedge')
    page = browser.new_page(viewport={'width': 1500, 'height': 1100})
    page.set_content(html, wait_until='networkidle', timeout=60000)
    page.evaluate('window.__render()')
    title = page.title()
    if not title.startswith('OK:'):
        print('ERR render', os.path.basename(mmd_path), title[:160])
        browser.close()
        return False
    w, h = title[3:].split('x')
    page.locator('.mermaid').screenshot(path=out_png, timeout=30000)
    browser.close()
    print('OK', os.path.basename(mmd_path), '->', os.path.basename(out_png), w + 'x' + h)
    return True


def main():
    if not sys.argv[1:]:
        print(__doc__); sys.exit(1)
    with sync_playwright() as p:
        for t in sys.argv[1:]:
            if not os.path.exists(t):
                print('ERR 文件不存在:', t); sys.exit(1)
            out = t[:-4] + '.png' if t.lower().endswith('.mmd') else t + '.png'
            if not render_one(p, t, out):
                sys.exit(1)


if __name__ == '__main__':
    main()
