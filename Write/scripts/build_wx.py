# -*- coding: utf-8 -*-
"""FastERP 系列：Markdown 母本 → wx 内联版 HTML（theme-fasterp 组件）。

用法：
  python build_wx.py <母本.md> [mmbiz-map.json]
输出：同目录 <母本名>-wx.html（纯 <section> 正文片段）。

- 图片引用 `![图注](assets/xxx.png)`：从 mmbiz-map.json 查 URL，缺失则保留本地路径（供 upload_imgs --html 兜底）。
- 正文内行内代码 `` `code` `` 转 <code>；代码块 ``` ``` 转 <section>+逐行 <p>。
- 标题：`# ` 大标题+装饰线；`## ` 章节标题。
"""
import html as _html
import json
import os
import re
import sys

P_TITLE = ('<p style="font-size:22px;color:#1F3864;text-align:center;font-weight:bold;'
           'margin:24px 0 10px;line-height:1.6;">{}</p>')
P_LINE = '<section style="width:64px;height:3px;background:#B08D3E;margin:12px auto 26px;"></section>'
P_H2 = ('<p style="font-size:18px;color:#1F3864;font-weight:bold;margin:28px 0 14px;'
        'padding-left:10px;border-left:4px solid #B08D3E;">{}</p>')
P_BODY = ('<p style="font-size:16px;color:#3f3f3f;line-height:1.9;letter-spacing:0.02em;'
          'text-indent:2em;margin:0 0 14px;text-align:justify;">{}</p>')
P_CODE_LINE = ('<p style="margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;'
               'font-size:13.5px;color:#24292E;text-indent:0;">{}</p>')
SEC_CODE = ('<section style="background:#F6F8FA;border:1px solid #E4E7EC;border-radius:8px;'
            'padding:14px 16px;margin:16px 0;overflow-x:auto;">{}</section>')
P_IMG = '<img src="{src}" alt="{alt}" style="max-width:100%;border-radius:10px;margin-bottom:6px;">'
P_CAP = '<p style="font-size:12.5px;color:#9A9A9A;text-align:center;margin:6px 0 18px;">{}</p>'

CODE_RE = re.compile(r"`([^`]+)`")
IMG_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


SPLIT_RE = re.compile(r"(`[^`]+`|!\[[^\]]*\]\([^)]+\))")


def inline(s):
    """正文行内处理：图片、行内代码、转义（按段处理，避免标签被二次转义）。"""
    def img(m):
        alt, src = m.group(1), m.group(2)
        url = mmbiz.get(src) or mmbiz.get(os.path.basename(src)) or src
        return P_IMG.format(src=url, alt=_html.escape(alt, quote=True))

    def code(seg):
        return ('<code style="background:#F0F2F5;color:#C7254E;border-radius:4px;'
                'padding:1px 4px;font-size:14px;">' +
                _html.escape(seg[1:-1], quote=False) + '</code>')

    out = []
    for seg in SPLIT_RE.split(s):
        if not seg:
            continue
        if seg.startswith("`") and seg.endswith("`") and len(seg) > 1:
            out.append(code(seg))
        elif seg.startswith("!["):
            m = IMG_RE.match(seg)
            if m:
                out.append(img(m))
                continue
            out.append(_html.escape(seg, quote=False))
        else:
            out.append(_html.escape(seg, quote=False))
    return "".join(out)


def code_block(lines):
    out = []
    for ln in lines:
        if not ln.strip():
            out.append(P_CODE_LINE.format("&nbsp;"))
            continue
        esc = _html.escape(ln, quote=False).replace(" ", "&nbsp;")
        out.append(P_CODE_LINE.format(esc))
    return SEC_CODE.format("".join(out))


def convert(md_path):
    global mmbiz
    mmbiz = {}
    if len(sys.argv) > 2 and os.path.exists(sys.argv[2]):
        raw = json.load(open(sys.argv[2], encoding="utf-8"))
    elif os.path.exists(os.path.join(os.path.dirname(md_path), "assets", "mmbiz-map.json")):
        raw = json.load(open(os.path.join(os.path.dirname(md_path), "assets", "mmbiz-map.json"), encoding="utf-8"))
    else:
        raw = {}
    mmbiz = {k.replace("\\", "/"): v for k, v in raw.items()}
    text = open(md_path, encoding="utf-8-sig").read().lstrip("\ufeff")
    lines = text.split("\n")
    out, i, n = [], 0, len(lines)
    while i < n:
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if ln.startswith("# "):
            out.append(P_TITLE.format(_html.escape(ln[2:].strip(), quote=False)))
            out.append(P_LINE)
            i += 1
            continue
        if ln.startswith("## "):
            out.append(P_H2.format(_html.escape(ln[3:].strip(), quote=False)))
            i += 1
            continue
        if ln.startswith("```"):
            block = []
            i += 1
            while i < n and not lines[i].startswith("```"):
                block.append(lines[i])
                i += 1
            i += 1  # 跳过结尾 ```
            out.append(code_block(block))
            continue
        out.append(P_BODY.format(inline(ln.strip())))
        i += 1
    return "".join(out)


if __name__ == "__main__":
    md = sys.argv[1]
    out_path = md[:-3] + "-wx.html" if md.endswith(".md") else md + "-wx.html"
    html = convert(md)
    # 图注：紧跟 img 的段落若以「图 N 」开头则独立成图注（母本中已单独成段）
    html = re.sub(
        r'(<img [^>]+>)\n?<p style="font-size:16px;[^"]*text-indent:2em[^"]*">(图\s*\d+[^<]*)</p>',
        lambda m: m.group(1) + "\n" + P_CAP.format(m.group(2)),
        html,
    )
    open(out_path, "w", encoding="utf-8").write(html)
    print("WROTE", out_path, len(html), "bytes")
