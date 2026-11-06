# -*- coding: utf-8 -*-
"""表格 → PNG 渲染器（微信正文不能渲染 <table>，表格一律截图成图片）。

背景：微信公众号端不渲染正文里的 <table> 元素（窄视口会堆叠成纯文字），
因此对照表、分录块、情形表这类结构化内容必须渲染成 PNG，再走 uploadimg 换 mmbiz URL。

用法:
    python gen_table.py <spec.json> [spec2.json ...] [--out-dir <dir>]

spec 结构（JSON，UTF-8）:
{
  "out": "tab_judge.png",              # 必填：输出文件名（--out-dir 缺省时落在 spec 同目录）
  "width": 1080,                        # 可选：表格 CSS 宽（默认 1080）
  "cols": [                             # 必填：列定义，非空
    {"label": "研发产出", "width": 260, "cls": "case"},
    {"label": "资产属性判断重点", "width": 400},
    {"label": "满足确认条件后的科目归属", "width": 360, "cls": "eval"}
  ],
  "rows": [                             # 必填：行，非空
    {"cells": ["用于对外销售的样机、样品", "相关经济利益是否很可能流入企业", "库存商品"]},
    {"section": "小节标题行（可选，整行高亮）"},
    {"cells": [{"t": "主文案", "sub": "灰色补充", "cls": "case"}, "..."]}
  ]
}

单元格可以是字符串，也可以是 {"t": 正文, "sub": 灰色小字, "cls": 语义类}：
  cls 取值 case（深蓝加粗）/ eval（灰字），缺省无类。

依赖：playwright（浏览器 fallback 链复用 render_mermaid.launch_browser：
      系统 Edge → 系统 Chrome → Playwright 默认 Chromium；本脚本不装任何新浏览器）。
退出码：0 = 全部渲染成功；1 = 有 spec 失败或参数错误。
"""
import argparse
import importlib.util
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))

STYLE = """
<style>
  body { margin: 0; padding: 20px; background: #ffffff;
         font-family: 'Microsoft YaHei', 'SimHei', sans-serif; }
  table { border-collapse: collapse; background: #ffffff; }
  th { background: #1F3864; color: #ffffff; font-weight: bold;
       padding: 12px 14px; text-align: left; font-size: 16px;
       border: 1px solid #1F3864; }
  td { padding: 11px 14px; font-size: 15px; color: #3f3f3f;
       line-height: 1.7; border: 1px solid #D5DCE6; vertical-align: top; }
  tr.alt td { background: #F7F8FA; }
  tr.section td { background: #FDF9F0; color: #1F3864; font-weight: bold;
       font-size: 15px; border-top: 2px solid #B08D3E; }
  td.case { font-weight: bold; color: #1F3864; }
  td .sub { font-weight: normal; color: #8A8A8A; font-size: 13px; }
  td.eval { color: #555555; }
</style>
"""


def _load_launch_browser():
    """复用 render_mermaid.py 的 launch_browser（浏览器 fallback 链的唯一实现）。

    render_mermaid.py 属同目录兄弟文件；其 playwright 为函数内延迟 import，
    import 期不触发浏览器依赖，故此处 exec_module 安全。
    """
    cand = os.path.join(HERE, "render_mermaid.py")
    if not os.path.isfile(cand):
        raise SystemExit("ERR 找不到 render_mermaid.py（期望 %s）——"
                         "浏览器 fallback 链 msedge→chrome→Chromium 的唯一实现。" % cand)
    spec = importlib.util.spec_from_file_location("render_mermaid", cand)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "launch_browser"):
        raise SystemExit("ERR render_mermaid.py 未提供 launch_browser()——本脚本依赖其 fallback 链。")
    return mod.launch_browser, getattr(mod, "crop_whitespace", None)


def _cell_html(spec, cls=None):
    if isinstance(spec, dict):
        t = spec.get("t", "")
        sub = spec.get("sub")
        c = spec.get("cls", cls)
        extra = ' class="' + c + '"' if c else ""
        subhtml = ('<br/><span class="sub">' + str(sub) + '</span>') if sub else ""
        return "<td" + extra + ">" + str(t) + subhtml + "</td>"
    extra = ' class="' + cls + '"' if cls else ""
    return "<td" + extra + ">" + str(spec) + "</td>"


def build_html(spec):
    width = spec.get("width", 1080)
    cols = spec["cols"]
    ths = "".join(
        '<th style="width:{w}px;">{label}</th>'.format(
            w=c.get("width", 180), label=c["label"]) for c in cols)
    head = ('<table style="width:' + str(width) + 'px;"><thead><tr>'
            + ths + '</tr></thead><tbody>')
    body = []
    alt = False
    for r in spec["rows"]:
        if r.get("section"):
            body.append('<tr class="section"><td colspan="%d">%s</td></tr>'
                        % (len(cols), r["section"]))
            alt = False
            continue
        cells = list(r["cells"])
        if len(cells) < len(cols):
            cells += [""] * (len(cols) - len(cells))
        elif len(cells) > len(cols):
            print("WARN 单元格数超过列数，截断:", spec.get("out"), len(cells), file=sys.stderr)
            cells = cells[:len(cols)]
        tds = [_cell_html(cells[0], "case")]
        for i, c in enumerate(cells[1:], start=1):
            tds.append(_cell_html(c, cols[i].get("cls")))
        tr_cls = ' class="alt"' if alt else ""
        body.append("<tr" + tr_cls + ">" + "".join(tds) + "</tr>")
        alt = not r.get("section")
    return STYLE + head + "\n".join(body) + "</tbody></table>"


def validate(spec, path):
    errs = []
    if not isinstance(spec, dict):
        return ["spec 顶层不是对象"]
    if not str(spec.get("out", "")).strip():
        errs.append("缺 out（输出文件名）")
    cols = spec.get("cols")
    if not isinstance(cols, list) or not cols:
        errs.append("缺 cols 或 cols 为空")
    elif not all(isinstance(c, dict) and c.get("label") for c in cols):
        errs.append("cols 每列必须含 label")
    rows = spec.get("rows")
    if not isinstance(rows, list) or not rows:
        errs.append("缺 rows 或 rows 为空")
    else:
        for i, r in enumerate(rows, 1):
            if not isinstance(r, dict):
                errs.append("rows[%d] 不是对象" % i)
            elif not r.get("section") and not isinstance(r.get("cells"), list):
                errs.append("rows[%d] 既无 section 也无 cells" % i)
    return errs


def main():
    ap = argparse.ArgumentParser(description="表格 → PNG（微信正文以图片呈现表格）")
    ap.add_argument("specs", nargs="+", help="一个或多个 spec JSON 路径")
    ap.add_argument("--out-dir", default=None, help="输出目录（缺省落在各 spec 同目录）")
    args = ap.parse_args()

    loaded = []
    for f in args.specs:
        if not os.path.isfile(f):
            print("ERR spec 不存在:", f, file=sys.stderr)
            return 1
        try:
            # utf-8-sig：兼容带 BOM 的 spec（Windows 记事本默认会写 BOM，纯 utf-8 会解析失败）
            spec = json.loads(io.open(f, encoding="utf-8-sig").read())
        except Exception as e:  # noqa: BLE001
            print("ERR spec 不是合法 JSON：%s（%s）" % (f, e), file=sys.stderr)
            return 1
        errs = validate(spec, f)
        if errs:
            for e in errs:
                print("FAIL %s：%s" % (f, e), file=sys.stderr)
            return 1
        base = os.path.dirname(os.path.abspath(f))
        out = os.path.join(args.out_dir or base, spec["out"])
        loaded.append((spec, out))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERR 未安装 playwright，无法渲染——本技能不代你安装浏览器"
              "（严禁装新的 Chrome/Chromium），playwright 需按本机 uv 规则装到 D:\\Python。",
              file=sys.stderr)
        return 1

    launch_browser, crop_ws = _load_launch_browser()
    ok = 0
    with sync_playwright() as p:
        browser, browser_name = launch_browser(p)
        try:
            for spec, out in loaded:
                html = build_html(spec)
                page = browser.new_page(viewport={"width": 1400, "height": 1000},
                                        device_scale_factor=2)
                try:
                    page.set_content('<div id="wrap" style="display:inline-block">'
                                     + html + '</div>', wait_until="domcontentloaded")
                    page.wait_for_timeout(250)
                    page.locator("#wrap").screenshot(path=out, timeout=30000)
                    if crop_ws:
                        crop_ws(out)
                    print("OK", spec["out"], "->", out, "(%s)" % browser_name)
                    ok += 1
                finally:
                    page.close()
        finally:
            browser.close()
    return 0 if ok == len(loaded) else 1


if __name__ == "__main__":
    sys.exit(main())
