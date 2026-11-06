#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从少量 JSON 生成 theme-default 逐字排版的正文片段（把手写样式从流程里去掉）。

用法:
    python build_blocks.py blocks.json -o out.html
    python build_blocks.py blocks.json                 # 打到标准输出
    python build_blocks.py --demo -o out.html          # 输出全部组件的示例片段
    echo '[{"type":"h1","text":"标题"}]' | python build_blocks.py -

输入格式: {"blocks":[{...},...]} 或直接一个数组。每个块是
    {"type": "<组件名>, ...参数}
组件名与参数见 BLOCKS；样式一律取自 theme-default，脚本不接收自定义 style，
生成物与 write/references/b2-typeset/theme-default.md 逐字一致（tests/test_theme_blocks.py 比对）。

代码块的行内缩进写实空格：每 4 个前导空格转 4 个 &nbsp;，`<` `>` `&` 自动转义，
空行输出 <p>&nbsp;</p>。正文段子里用反引号包裹的行内代码（`xxx`）转行内代码样式，
`**xxx**` 转 <strong>（保留加粗语义）。

组件与参数（type + 必填参数，缺参数即明确报错，不静默降级）：
    h1 / h2 / caption: text；image: url、alt（可选）；code: lines（每行一个字符串）；
    card: name、desc，sub 可选；rule / hr: 无参数（rule 可加 edit_path=true 出 <p> 变体）。
属性值（src / alt）会净化裸双引号，避免截断 HTML 属性；不写 &quot;（会被二次转义成乱码）。

`--demo` 输出的是**判据样张**（十个组件各一段，供 tests/test_theme_blocks.py 与 md 逐字比对），
不是文章骨架：写文章时按内容取块，没有代码就不放 code 块，不得为凑组件补写内容。

生成后照旧走闸口（顺序固定）:
    成文即在 A 轨道内整理为符合 wx-HTML 规范的 article-wx.html（见 write/SKILL.md「A 轨道」出口闸）
    python write/references/b3-acceptance/scripts/validate_wx_html.py out.html    # 排版红线，ERROR=0
    python write/references/b3-acceptance/scripts/qa_mobile.py out.html           # 390px 渲染验收
"""
import argparse
import json
import re
import sys

# ---- 设计变量（与 theme-default.md「设计变量」表同值；改动须同步 md 与一致性测试） ----
V = {
    "primary": "#1F3864",
    "gold": "#B08D3E",
    "text": "#3f3f3f",
    "code_bg": "#F6F8FA",
    "code_border": "#E4E7EC",
    "code_text": "#24292E",
    "inline_bg": "#F0F2F5",
    "inline_text": "#C7254E",
    "caption": "#9A9A9A",
    "divider": "#D5DCE6",
    "card_bg": "#F7F8FA",
    "card_sub": "#8A8A8A",
    "card_desc": "#555555",
}

CODE_P_STYLE = ("margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;"
                "font-size:13.5px;color:%s;text-indent:0;" % V["code_text"])

LINE_RX = re.compile(r"^(\s*)", re.S)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _para(t):
    return t if t is not None else ""


def _attr_text(s):
    """属性值（alt 等）安全化：转义 <>&，并把会截断属性的裸双引号换成全角引号。
    不写 &quot;——公众号端会二次转义成乱码；属性值不是正文显示文字，可安全净化。"""
    return esc(s if s is not None else "").replace('"', "’")


def _attr_url(s):
    """URL 属性值安全化：只消除会截断属性的裸双引号（URL 内的 & 不做实体转义，
    以免破坏 mmbiz 查询串；<>& 在 URL 属性中本就安全）。"""
    return (s if s is not None else "").replace('"', "’")


def bl_h1(d):
    return ('<p style="font-size:22px;color:%s;text-align:center;font-weight:bold;'
            'margin:24px 0 10px;line-height:1.6;">%s</p>' % (V["primary"], _para(d.get("text"))))


def bl_rule(d):
    style = 'width:64px;height:3px;background:%s;margin:12px auto 26px;' % V["gold"]
    if d.get("edit_path"):
        # 编辑器粘贴路径用 <p> 变体（API 推送路径实测 <div> 不被清洗；见 theme-default 组件 2 注）。
        # 样式串与 <div> 版一致，故 verify 的样式指纹不会误判为漂移。
        return '<p style="%s">&nbsp;</p>' % style
    return '<div style="%s"></div>' % style


def bl_h2(d):
    return ('<p style="font-size:18px;color:%s;font-weight:bold;margin:28px 0 14px;'
            'padding-left:10px;border-left:4px solid %s;">%s</p>'
            % (V["primary"], V["gold"], _para(d.get("text"))))


def bl_para(d):
    text = esc(_para(d.get("text")))
    text = re.sub(r"`([^`]+)`",
                  lambda m: ('<code style="background:%s;color:%s;border-radius:4px;'
                             'padding:1px 4px;font-size:14px;">%s</code>'
                             % (V["inline_bg"], V["inline_text"], m.group(1))),
                  text)
    # markdown 加粗 **x** → <strong>x</strong>（保留语义；DEMO 无加粗，逐字测试不受影响）
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: '<strong>%s</strong>' % m.group(1), text)
    return ('<p style="font-size:16px;color:%s;line-height:1.9;letter-spacing:0.02em;'
            'text-indent:2em;margin:0 0 14px;text-align:justify;">%s</p>'
            % (V["text"], text))


def bl_code(d):
    lines = d.get("lines") or []
    body = []
    for ln in lines:
        indent = len(LINE_RX.match(ln).group(1))
        content = ln[indent:]
        pad = "&nbsp;" * indent
        body.append('  <p style="%s">%s%s</p>' % (CODE_P_STYLE, pad, esc(content) or "&nbsp;"))
    return ('<section style="background:%s;border:1px solid %s;border-radius:8px;'
            'padding:14px 16px;margin:16px 0;overflow-x:auto;">\n%s\n</section>'
            % (V["code_bg"], V["code_border"], "\n".join(body)))


def bl_image(d):
    return ('<section style="text-align:center;margin:0 0 6px;">\n'
            '  <img src="%s" alt="%s" style="max-width:100%%;border-radius:10px;'
            'display:block;margin:0 auto;">\n</section>'
            % (_attr_url(d.get("url")), _attr_text(d.get("alt"))))


def bl_caption(d):
    return ('<p style="font-size:12.5px;color:%s;text-align:center;margin:6px 0 18px;">%s</p>'
            % (V["caption"], _para(d.get("text"))))


def bl_hr(d):
    return ('<p style="border:none;border-top:1px solid %s;margin:22px 0;">&nbsp;</p>'
            % V["divider"])


def bl_card(d):
    """条目卡片（组件 10）：表格的微信安全替代，纯块级布局，微信端稳定。"""
    name = _para(d.get("name"))
    sub = d.get("sub")
    nameline = name
    if sub:
        nameline += ('<span style="color:%s;font-weight:normal;font-size:14px;">　%s</span>'
                     % (V["card_sub"], _para(sub)))
    return ('<section style="margin:0 0 12px;padding:12px 16px;background:%s;'
            'border-left:4px solid %s;border-radius:6px;">\n'
            '  <p style="margin:0 0 6px;font-size:16px;color:%s;font-weight:bold;'
            'line-height:1.6;">%s</p>\n'
            '  <p style="margin:0;font-size:15px;color:%s;line-height:1.7;">%s</p>\n</section>'
            % (V["card_bg"], V["gold"], V["primary"], nameline,
               V["card_desc"], _para(d.get("desc"))))


def bl_inline_code(d):
    return ('<code style="background:%s;color:%s;border-radius:4px;padding:1px 4px;'
            'font-size:14px;">%s</code>'
            % (V["inline_bg"], V["inline_text"], esc(_para(d.get("text")))))


# 组件名 → 生成函数；与 theme-default.md 的组件一一对应
BLOCKS = {
    "h1": bl_h1,
    "rule": bl_rule,
    "h2": bl_h2,
    "para": bl_para,
    "inline_code": bl_inline_code,
    "code": bl_code,
    "image": bl_image,
    "caption": bl_caption,
    "hr": bl_hr,
    "card": bl_card,
}

# theme-default.md 各组件示例里的占位文字（--demo 用，也供一致性测试引用）
DEMO = [
    {"type": "h1", "text": "完整标题"},
    {"type": "rule"},
    {"type": "h2", "text": "一、章节标题"},
    {"type": "para", "text": "正文内容……"},
    {"type": "inline_code", "text": "create_order(oid, customer_id)"},
    {"type": "code", "lines": [
        "    def create_order(oid, customer_id):",
        '        if oid < 0: raise ValueError("invalid id")',
        "",
        "    return order",
    ]},
    {"type": "image", "url": "https://mmbiz.qpic.cn/…", "alt": "图注文字"},
    {"type": "caption", "text": "图 1 说明文字"},
    {"type": "hr"},
    {"type": "card", "name": "条目名", "sub": "副说明", "desc": "条目说明文字"},
]


def _validate(blocks):
    """块参数预检：类型合法 + 各组件必填参数齐全（失败即明确报错，不静默降级）。"""
    for i, b in enumerate(blocks, 1):
        t = b.get("type")
        if t not in BLOCKS:
            raise SystemExit("未知组件 %r（第 %d 块）。可用：%s"
                             % (t, i, "、".join(sorted(BLOCKS))))
        if t == "image" and not str(b.get("url", "")).strip():
            raise SystemExit("第 %d 块 image 缺 url" % i)
        if t == "code" and not b.get("lines"):
            raise SystemExit("第 %d 块 code 缺 lines（空代码块请给 lines:[\"\"]）" % i)
        if t == "card" and not str(b.get("name", "")).strip():
            raise SystemExit("第 %d 块 card 缺 name" % i)
        if t in ("h1", "h2", "caption") and not str(b.get("text", "")).strip():
            raise SystemExit("第 %d 块 %s 缺 text" % (i, t))


def render(blocks):
    _validate(blocks)
    out = [BLOCKS[b.get("type")](b) for b in blocks]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("json_file", nargs="?", help="块定义 JSON（- 读标准输入）")
    ap.add_argument("--demo", action="store_true", help="输出全部组件示例，忽略输入文件")
    ap.add_argument("-o", "--out", help="写入文件；默认标准输出")
    args = ap.parse_args()

    if args.demo:
        src_blocks = DEMO
    else:
        if not args.json_file:
            raise SystemExit("需要 blocks.json 路径，或用 --demo")
        raw = sys.stdin.read() if args.json_file == "-" else open(
            args.json_file, encoding="utf-8").read()
        data = json.loads(raw)
        src_blocks = data.get("blocks") if isinstance(data, dict) else data
        if not isinstance(src_blocks, list) or not src_blocks:
            raise SystemExit("JSON 里 blocks 必须是非空数组")
    html = render(src_blocks)

    if args.out:
        with open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
        print("已写出 %s（%d 字节，%d 个组件块）"
              % (args.out, len(html.encode("utf-8")), len(src_blocks)))
    else:
        sys.stdout.write(html)


if __name__ == "__main__":
    main()
