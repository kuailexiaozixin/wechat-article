#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把已校验的 wx 内联版 HTML 包成浏览器预览页（推送前本地自查用）。

用法:
    wrap_preview.py <section.html> [output.html]
    默认输出 <原文件去扩展名>_预览.html

预览页模拟公众号阅读效果（正文 16px/行距 1.9、容器宽度 680px），
并附「复制到公众号」按钮（等价手动全选复制，样式全保留）。
按钮与 JS 只在预览外壳里、不在正文 section 内——校验仍对原文件跑。

功能思路借鉴自 gzh-design-skill（scripts/wrap_preview.py，AGPL-3.0，
作者 甲木 × 摸鱼小李）；模板与实现为本文件独立编写。
"""
import os
import sys

TEMPLATE = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
<style>
  body { margin:0; background:#f0f0f0; }
  #toolbar { position:fixed; top:0; left:0; right:0; z-index:99;
             background:#fff; border-bottom:1px solid #e0e0e0;
             padding:10px 20px; display:flex; align-items:center; gap:12px;
             font:14px/1.4 system-ui, sans-serif; }
  #toolbar button { background:#1F3864; color:#fff; border:none; border-radius:6px;
                    padding:8px 18px; font-size:14px; cursor:pointer; }
  #toolbar span { color:#666; }
  #article { max-width:680px; margin:64px auto 40px; background:#fff;
             padding:32px 28px; border-radius:8px; box-shadow:0 2px 12px rgba(0,0,0,.06); }
  #article p, #article section { max-width:100%; }
  #article img { max-width:100%; height:auto; display:block; margin:0 auto; }
</style></head><body>
<div id="toolbar"><button onclick="copyArticle()">复制到公众号</button>
<span>点按钮复制后，到公众号编辑器 Ctrl/⌘+V 粘贴；预览仅用于本地检查，样式以公众号端为准。</span></div>
<div id="article"><!--GZH_CONTENT--></div>
<script>
function copyArticle(){
  var box = document.getElementById('article');
  var sel = window.getSelection();
  var range = document.createRange();
  range.selectNodeContents(box);
  sel.removeAllRanges(); sel.addRange(range);
  try { document.execCommand('copy'); alert('已复制，去公众号编辑器粘贴'); }
  catch(e) { alert('复制失败，请手动全选复制'); }
  sel.removeAllRanges();
}
</script></body></html>"""


def main():
    if len(sys.argv) < 2:
        print("用法: wrap_preview.py <section.html> [output.html]")
        sys.exit(1)
    src = sys.argv[1]
    if not os.path.isfile(src):
        print(f"✗ 找不到文件: {src}")
        sys.exit(1)
    content = open(src, encoding="utf-8").read().strip()
    title = os.path.splitext(os.path.basename(src))[0]
    out_html = TEMPLATE.replace("{{TITLE}}", title).replace("<!--GZH_CONTENT-->", content)
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.splitext(src)[0] + "_预览.html"
    open(out, "w", encoding="utf-8").write(out_html)
    print(f"✓ 已生成预览页: {out}")
    print("  浏览器打开自查；推送前仍须跑 validate_wx_html.py 校验原文件。")


if __name__ == "__main__":
    main()
