# -*- coding: utf-8 -*-
"""390px 移动端渲染验收（推送前自动化闸门，静态校验查不出的渲染层问题由此把关）。

用法:
    python qa_mobile.py <article.html> [--width 390] [--screenshot out.png]
                        [--no-image-check] [--json]

检查项:
  1. 横向溢出: 文档 scrollWidth 超出视口宽度即 FAIL，并列出越界最多的元素
     （标签/尺寸/文本片段）。
  2. 布局降级: computed style 层面统计 display:table* / grid / flex。
     display:table*（div 伪表格）与 grid 判 FAIL —— 与宽度无关，390px 溢出
     判据抓不到（窄视口会把固定宽的 table-cell 压缩），微信手机端则堆叠成
     纯文本；display:flex 记 WARNING（部分机型换行/对齐异常）。
  3. 坏图: <img> 加载后 naturalWidth==0 即 FAIL（配图未显示在推送前暴露）。
     无网络环境可 --no-image-check 关闭本项（其余项不受影响）。
  4. 整页截图存盘（默认 <输入名>_qa<宽>.png），交付用户人工核对观感。

浏览器 fallback 链（复用 render_mermaid.launch_browser）:
    系统 Edge(msedge) → 系统 Chrome(chrome) → Playwright 默认 Chromium。
退出码: 0 = 通过; 1 = 有 FAIL。凭据无关，纯本地渲染。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_mermaid import launch_browser  # noqa: E402  复用浏览器 fallback 链

OVERFLOW_JS = """
(w) => {
  const de = document.documentElement;
  const out = { scrollWidth: Math.max(de.scrollWidth, document.body.scrollWidth), culprits: [] };
  if (out.scrollWidth > w + 1) {
    const nodes = document.querySelectorAll('body *');
    for (const el of nodes) {
      const r = el.getBoundingClientRect();
      if (r.right > w + 2 && r.width > 24) {
        out.culprits.push({
          tag: el.tagName.toLowerCase(),
          width: Math.round(r.width),
          right: Math.round(r.right),
          text: (el.textContent || '').trim().slice(0, 30)
        });
        if (out.culprits.length >= 5) break;
      }
    }
  }
  return out;
}
"""

IMG_JS = """
() => {
  const bad = [];
  for (const im of document.images) {
    if (im.complete && im.naturalWidth === 0 && (im.src || '')) bad.push(im.src.slice(0, 100));
  }
  return { total: document.images.length, bad };
}
"""

# 渲染层布局检测：微信手机端会把 display:table* 堆叠成纯文本（历史草稿实测，
# 与宽度无关，390px 溢出判据抓不到），在真实浏览器 computed style 层面直接判 FAIL；
# display:flex 记 WARNING（部分机型换行/对齐异常，静态校验同为 WARN 级）。
LAYOUT_JS = r"""
() => {
  const table = [], flex = [], grid = [];
  for (const el of document.querySelectorAll('body *')) {
    const d = getComputedStyle(el).display;
    const info = { tag: el.tagName.toLowerCase(),
                   text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 24) };
    if (d.startsWith('table')) table.push(info);
    else if (d === 'flex') flex.push(info);
    else if (d === 'grid' || d === 'inline-grid') grid.push(info);
  }
  return { table, flex, grid };
}
"""


def qa(html_path, width=390, screenshot=None, image_check=True):
    if not os.path.exists(html_path):
        return {"ok": False, "errors": ["文件不存在: " + html_path],
                "warnings": [], "scroll_width": None, "images": None, "layout": None}
    url = "file:///" + os.path.abspath(html_path).replace(os.sep, "/")
    shot = screenshot or (os.path.splitext(html_path)[0] + "_qa%d.png" % width)
    from playwright.sync_api import sync_playwright
    result = {"ok": True, "errors": [], "warnings": [], "scroll_width": None,
              "images": None, "layout": None, "screenshot": None}
    with sync_playwright() as p:
        browser, bname = launch_browser(p)
        try:
            page = browser.new_page(viewport={"width": width, "height": 844})
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(1500)
            if image_check:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:  # 网络慢不算失败，坏图判定继续
                    pass
            probe = page.evaluate(OVERFLOW_JS, width)
            result["scroll_width"] = probe["scrollWidth"]
            if probe["scrollWidth"] > width + 1:
                culprits = "; ".join(
                    "%s(%dpx→%d)「%s」" % (c["tag"], c["width"], c["right"], c["text"])
                    for c in probe["culprits"]) or "未定位到具体元素"
                result["errors"].append(
                    "横向溢出: scrollWidth=%d > %d。越界元素: %s"
                    % (probe["scrollWidth"], width, culprits))
            if image_check:
                im = page.evaluate(IMG_JS)
                result["images"] = im
                if im["bad"]:
                    result["errors"].append(
                        "坏图 %d/%d: %s" % (len(im["bad"]), im["total"],
                                            " | ".join(im["bad"][:3])))
            lay = page.evaluate(LAYOUT_JS)
            result["layout"] = {k: len(v) for k, v in lay.items()}
            for kind, label in (("table", "display:table*（微信手机端堆叠成纯文本）"),
                                ("grid", "display:grid（微信端不支持）")):
                if lay[kind]:
                    sample = "; ".join('%s「%s」' % (x["tag"], x["text"])
                                       for x in lay[kind][:5])
                    result["errors"].append(
                        "%s 布局 %d 处: %s" % (label, len(lay[kind]), sample))
            if lay["flex"]:
                result["warnings"].append(
                    "display:flex %d 处（部分机型换行/对齐异常，建议改条目卡片）: %s"
                    % (len(lay["flex"]),
                       "; ".join('%s「%s」' % (x["tag"], x["text"])
                                 for x in lay["flex"][:3])))
            page.screenshot(path=shot, full_page=True)
            result["screenshot"] = shot
            result["browser"] = bname
        finally:
            browser.close()
    result["ok"] = not result["errors"]
    return result


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("html")
    ap.add_argument("--width", type=int, default=390)
    ap.add_argument("--screenshot")
    ap.add_argument("--no-image-check", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    r = qa(args.html, args.width, args.screenshot, not args.no_image_check)
    if args.json:
        print(json.dumps(r, ensure_ascii=False))
    else:
        print("=== 390px 移动端渲染验收: %s (浏览器: %s) ===" % (args.html, r.get("browser", "-")))
        print("  scrollWidth: %s" % r.get("scroll_width"))
        if r.get("images"):
            print("  图片: %d 张，坏图 %d 张" % (r["images"]["total"], len(r["images"]["bad"])))
        if r.get("layout"):
            print("  布局: table×%d · grid×%d · flex×%d"
                  % (r["layout"]["table"], r["layout"]["grid"], r["layout"]["flex"]))
        if r.get("screenshot"):
            print("  截图: %s" % r["screenshot"])
        for e in r["errors"]:
            print("  [FAIL]", e)
        for w in r.get("warnings", []):
            print("  [WARN]", w)
        print("[PASS] 渲染验收通过" if r["ok"] else "[FAIL] 存在渲染问题，修复后再推送")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
