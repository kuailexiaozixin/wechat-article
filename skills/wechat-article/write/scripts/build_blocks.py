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
生成物与 write/references/theme-default.md 逐字一致（tests/test_theme_blocks.py 比对）。

代码块的行内缩进写实空格：每 4 个前导空格转 4 个 &nbsp;，`<` `>` `&` 自动转义，
空行输出 <p>&nbsp;</p>。正文段子里用反引号包裹的行内代码（`xxx`）转组件 5 样式。

`--demo` 输出的是**判据样张**（九个组件各一段，供 tests/test_theme_blocks.py 与 md 逐字比对），
不是文章骨架：写文章时按内容取块，没有代码就不放 code 块，不得为凑组件补写内容。

生成后照旧走闸口（顺序固定）:
    python write/scripts/check_prose.py <稿件.md>        # 第 3 步成文后跑，查硬禁令
    python write/scripts/validate_wx_html.py out.html    # 排版红线，ERROR=0
    python write/scripts/qa_mobile.py out.html           # 390px 渲染验收
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
}

CODE_P_STYLE = ("margin:0;line-height:1.6;font-family:Consolas,Menlo,monospace;"
                "font-size:13.5px;color:%s;text-indent:0;" % V["code_text"])

LINE_RX = re.compile(r"^(\s*)", re.S)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _para(t):
    return t if t is not None else ""


def bl_h1(d):
    return ('<p style="font-size:22px;color:%s;text-align:center;font-weight:bold;'
            'margin:24px 0 10px;line-height:1.6;">%s</p>' % (V["primary"], _para(d.get("text"))))


def bl_rule(d):
    return ('<div style="width:64px;height:3px;background:%s;margin:12px auto 26px;"></div>'
            % V["gold"])


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
            % (_para(d.get("url")), esc(_para(d.get("alt")))))


def bl_caption(d):
    return ('<p style="font-size:12.5px;color:%s;text-align:center;margin:6px 0 18px;">%s</p>'
            % (V["caption"], _para(d.get("text"))))


def bl_hr(d):
    return ('<p style="border:none;border-top:1px solid %s;margin:22px 0;">&nbsp;</p>'
            % V["divider"])


def bl_inline_code(d):
    return ('<code style="background:%s;color:%s;border-radius:4px;padding:1px 4px;'
            'font-size:14px;">%s</code>'
            % (V["inline_bg"], V["inline_text"], esc(_para(d.get("text")))))


# 组件名 → 生成函数；与 theme-default.md 的 9 个组件一一对应
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
    {"type": "image", "url": "http://mmbiz.qpic.cn/…", "alt": "图注文字"},
    {"type": "caption", "text": "图 1 说明文字"},
    {"type": "hr"},
]


def render(blocks):
    out = []
    for i, b in enumerate(blocks):
        t = b.get("type")
        fn = BLOCKS.get(t)
        if fn is None:
            raise SystemExit("未知组件 %r（第 %d 块）。可用：%s"
                             % (t, i + 1, "、".join(sorted(BLOCKS))))
        out.append(fn(b))
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
