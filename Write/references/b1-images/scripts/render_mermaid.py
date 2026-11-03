# -*- coding: utf-8 -*-
"""用 Playwright 渲染 mermaid 图为 PNG（不安装新浏览器，按可用性依次尝试）。

用法：python render_mermaid.py <a.mmd> [b.mmd ...] [--offline] [--refresh-cache]
输出：每个 .mmd 的同目录同名 .png。
依赖：playwright（本机按 uv 规则装到 D:\\Python），mermaid 运行时见下。

mermaid 运行时加载（3 项健壮性改进，5.x 起）:
  1. 本地优先：按 env MERMAID_JS → 脚本同目录 mermaid.min.js → 用户缓存目录 的顺序找本地
     runtime，命中即内联进页面（不走网络，离线可用）。
  2. 缓存下载：本地缺失时从 CDN 下载到用户缓存目录（%LOCALAPPDATA%\\wechat-article 或
     ~/.cache/wechat-article），下次离线可用；下载失败则退回 CDN 外链。
  3. 超时重试：set_content 超时重试 1 次；失败信息区分「runtime 加载失败」与「mermaid 语法错误」。
  --offline 强制只用本地 runtime（不下载、不退回 CDN），本地缺失即报错退出，绝不静默产空图。
  --refresh-cache 忽略本地缓存，重新从 CDN 下载并覆盖缓存。

浏览器 fallback 链：系统 Edge（channel=msedge）→ 系统 Chrome（channel=chrome）
→ Playwright 默认 Chromium（本机已有 ms-playwright 浏览器时可用；本技能不跑 playwright install，
也不安装任何新的 Chrome/Chromium）。全部不可用时打印明确原因并退出码 1，不静默产出空图。

rendered 之外的约定：launch_browser(playwright) 是浏览器 fallback 链的唯一实现，
B3 的 qa_mobile.py 直接复用它——改本文件必须保留该函数签名与语义。
"""
import os
import sys
import urllib.request

MERMAID_CDN = "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"

HTML_TMPL = """<!DOCTYPE html><html><head><meta charset="utf-8">
__MERMAID_LOADER__
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


def _cache_dir():
    """用户级缓存目录（不落在技能仓库内，避免仓库体积膨胀）。"""
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("TEMP") or "."
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "wechat-article")


def _cache_file():
    return os.path.join(_cache_dir(), "mermaid.min.js")


def _local_candidates():
    """本地 runtime 候选路径（按优先级）。"""
    here = os.path.dirname(os.path.abspath(__file__))
    return [p for p in (os.environ.get("MERMAID_JS"),
                        os.path.join(here, "mermaid.min.js"),
                        _cache_file()) if p]


def _download_runtime(dest):
    try:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with urllib.request.urlopen(MERMAID_CDN, timeout=30) as r:
            data = r.read()
        if len(data) < 10000:  # 明显不是完整 runtime
            return False
        with open(dest, "wb") as f:
            f.write(data)
        return True
    except Exception:  # noqa: BLE001
        return False


def resolve_loader(offline=False, refresh_cache=False):
    """返回 (loader_html, source_desc)。source_desc 用于日志/排障。"""
    if not refresh_cache:
        for cand in _local_candidates():
            if cand and os.path.isfile(cand) and os.path.getsize(cand) > 10000:
                try:
                    with open(cand, encoding="utf-8", errors="ignore") as f:
                        js = f.read()
                    return ("<script>" + js + "</script>", "local:" + cand)
                except Exception:  # noqa: BLE001
                    continue
    if offline:
        raise SystemExit(
            "ERR --offline 但本地无可用 mermaid runtime。\n"
            "   解决：把 mermaid.min.js 放到 %s，或设 MERMAID_JS 指向它，"
            "或不加 --offline 联网下载一次。" % _cache_file())
    if _download_runtime(_cache_file()):
        with open(_cache_file(), encoding="utf-8", errors="ignore") as f:
            return ("<script>" + f.read() + "</script>", "downloaded:" + _cache_file())
    # 下载失败：退回 CDN 外链（需联网）
    return ('<script src="%s"></script>' % MERMAID_CDN, "cdn:" + MERMAID_CDN)


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
        "   解决: 本技能不装任何新的 Chrome/Chromium，也不代跑 playwright install——"
        "三档 fallback 只用现有浏览器，请确认本机已装并启动过 Microsoft Edge 或 Chrome。\n"
        "   环境预检：python Write/references/b3-acceptance/scripts/render_gate.py preflight <article.html>")


def render_one(browser, browser_name, mmd_path, out_png, loader_html):
    with open(mmd_path, encoding="utf-8") as f:
        code = f.read()
    html = (HTML_TMPL
            .replace("__MERMAID_LOADER__", loader_html)
            .replace("__MERMAID_CODE__", code))
    page = browser.new_page(viewport={"width": 1500, "height": 1100})
    try:
        for attempt in (1, 2):  # 超时重试 1 次
            try:
                page.set_content(html, wait_until="networkidle", timeout=60000)
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 1:
                    print("WARN set_content 超时/失败，重试一次：%s" % str(e)[:120], file=sys.stderr)
                    continue
                print("ERR render", os.path.basename(mmd_path),
                      "页面加载失败（超时或断言错误）：%s" % str(e)[:160])
                return False
        # runtime 是否就绪：区分「加载失败」与「语法错误」
        has_mermaid = page.evaluate("typeof mermaid !== 'undefined'")
        if not has_mermaid:
            print("ERR render", os.path.basename(mmd_path),
                  "mermaid runtime 未加载——多为 CDN/网络问题（--offline 或预置本地 mermaid.min.js 可规避）")
            return False
        page.evaluate("window.__render()")
        title = page.title()
        if not title.startswith("OK:"):
            print("ERR render", os.path.basename(mmd_path),
                  "mermaid 语法/渲染错误：" + title[:160])
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
    offline = "--offline" in argv
    refresh = "--refresh-cache" in argv
    argv = [a for a in argv if a not in ("--offline", "--refresh-cache")]
    if not argv:
        print(__doc__)
        sys.exit(1)
    # 先校验全部输入文件存在（启动浏览器前快速失败，避免空跑）
    for t in argv:
        if not os.path.exists(t):
            print("ERR 文件不存在:", t)
            sys.exit(1)
    # 解析 mermaid runtime 加载方式（本地优先 → 缓存下载 → CDN 外链）
    loader_html, src = resolve_loader(offline=offline, refresh_cache=refresh)
    print("mermaid runtime:", src if len(src) < 120 else src[:117] + "...")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERR 未安装 playwright，无法渲染——本技能不代你安装浏览器（严禁装新的 Chrome/Chromium），"
              "playwright 需按本机 uv 规则装到 D:\\Python。跳过本步不等于通过：Mermaid 图未落盘时"
              " B1 清单预检会报「图片尚未生成」。")
        sys.exit(2)
    with sync_playwright() as p:
        browser, browser_name = launch_browser(p)
        try:
            for t in argv:
                out = t[:-4] + ".png" if t.lower().endswith(".mmd") else t + ".png"
                if not render_one(browser, browser_name, t, out, loader_html):
                    sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
