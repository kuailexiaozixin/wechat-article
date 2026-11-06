#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 wx 内联版 HTML 包成浏览器预览页（临时预览工具，不是交付物）。

单文件铁律：全链路只维护一份 `article-wx.html`。本脚本默认把预览外壳写到
**系统临时目录**，不在稿件目录落下第二份 HTML；校验与推送始终对原文件跑。

配图可见性：
  - 原文件已回填 `mmbiz.qpic.cn` URL 时，直接双击原文件即可看到全部配图，通常不必用本脚本；
  - 原文件仍是 `__MMP__:<filename>` 占位时，用 `--figures` 指向配图目录，脚本把占位
    临时换成 data URI（只作用于预览副本，**绝不写回原文件**），本地即可核图。

用法：
    wrap_preview.py <section.html> [--figures <配图目录>] [--output <输出路径>]
    兼容旧用法：wrap_preview.py <section.html> <输出路径>

预览外壳含 <style>，只用于本地浏览，绝不能作为推送产物。
"""
import base64
import io
import os
import re
import sys
import tempfile

TEMPLATE = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  body { margin:0; background:#f0f0f0; }
  #article { max-width:680px; margin:40px auto; background:#fff;
             padding:32px 28px; border-radius:8px; box-shadow:0 2px 12px rgba(0,0,0,.06); }
  #article p, #article section { max-width:100%; }
  #article img { max-width:100%; height:auto; display:block; margin:0 auto; }
</style></head><body>
<div id="article"><!--GZH_CONTENT--></div>
</body></html>"""

PLACE_RX = re.compile(r'src="__MMP__:([^"]+)"')
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp"}


def inline_placeholders(content, figures):
    """只改预览副本：把 __MMP__ 占位换成本地图的 data URI。"""
    replaced, missing = [], []

    def sub(m):
        fn = m.group(1)
        path = os.path.join(figures, fn)
        if not os.path.isfile(path):
            missing.append(fn)
            return m.group(0)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        mime = MIME.get(os.path.splitext(fn)[1].lower(), "image/png")
        replaced.append(fn)
        return 'src="data:%s;base64,%s"' % (mime, b64)

    return PLACE_RX.sub(sub, content), replaced, missing


def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print(__doc__)
        return 0
    argv = sys.argv[1:]
    if not argv:
        print("用法: wrap_preview.py <section.html> [--figures <配图目录>] [--output <输出路径>]")
        return 1
    src = argv[0]
    if not os.path.isfile(src):
        print("找不到文件: %s" % src)
        return 1

    figures, out = None, None
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == "--figures" and i + 1 < len(argv):
            figures = argv[i + 1]
            i += 2
        elif a == "--output" and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        elif not a.startswith("--"):
            if out is None:      # 兼容旧版第二位置参数
                out = a
            i += 1
        else:
            i += 1

    content = io.open(src, encoding="utf-8").read().strip()
    left = PLACE_RX.findall(content)
    if figures:
        content, replaced, missing = inline_placeholders(content, figures)
        print("占位图临时内联 %d 张（仅预览副本，原文件未改）" % len(replaced))
        for m in missing:
            print("  [WARN] 找不到配图，保留占位: %s" % m)
    elif left:
        print("[提示] 原文件仍有 %d 个 __MMP__ 占位，预览里图片不显示。" % len(left))
        print("       加 --figures <配图目录> 可临时内联，或先跑 B1 回填 mmbiz URL。")

    stem = os.path.splitext(os.path.basename(src))[0]
    out = out or os.path.join(tempfile.gettempdir(), stem + "_wx临时预览.html")
    io.open(out, "w", encoding="utf-8").write(
        TEMPLATE.replace("{{TITLE}}", stem).replace("<!--GZH_CONTENT-->", content))
    print("临时预览页（非交付物）: %s" % out)
    print("唯一交付物始终是 %s；校验与推送都对它跑。" % src)
    return 0


if __name__ == "__main__":
    sys.exit(main())
