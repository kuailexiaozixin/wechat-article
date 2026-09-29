#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wx 内联版 HTML 合规校验器（API 推送路径版）。

把 write/SKILL.md 的「微信兼容硬规范」从模型自觉变成确定性兜底。
BANNED_WORDS / AI_FLAVOR_PHRASES 词表与改写手法维护见 `write/references/de-ai-measures.md`
（与 check_prose.py 的硬禁词表须同一轮更新）。
推送草稿前必跑：检查禁用标签/属性/样式、代码块结构、图片域名、
转义、禁用词与半角标点，并核对产物是否为纯 <section> 片段。

用法:
    validate_wx_html.py <file.html>
    validate_wx_html.py --stdin < file.html

退出码: 1 = 有 ERROR（会被微信过滤或显示异常，必须修复）; 0 = 通过
（WARNING 建议人工确认）。

与 gzh-design-skill 的 validate_gzh_html.py（AGPL-3.0，作者 甲木 × 摸鱼小李）
差异：本校验面向「draft/add API 直接推送」路径，不要求 <span leaf=""> 包裹
（API 保留内联样式，实测样式正常）；但要求图片必须 mmbiz 域名、
代码块必须 <section>+逐行 <p>、产物为纯正文片段。
检查项清单借鉴自该技能；实现为本文件独立编写。依 AGPL-3.0 保留来源声明。
"""
import argparse
import os
import re
import sys
from html.parser import HTMLParser

# (正则, 级别, 说明) —— 标签级检查全文（代码块内标签已转义为 &lt;，不会误报；
# class/id 属性检查限定「真实标签内」：代码块文本中的 `WHERE id=?`、`cls=` 等
# 字样经 &nbsp; 转义后仍带 `id=`/`class=`，宽松正则会误报，故要求以 `<标签名` 开头）
FORBIDDEN_TAGS = [
    (re.compile(r"<style[\s>]", re.I), "ERROR", "<style> 标签会被过滤，样式必须内联"),
    (re.compile(r"<script[\s>]", re.I), "ERROR", "<script> 标签会被过滤"),
    (re.compile(r"<link[\s>]", re.I), "ERROR", "外部 <link>（CSS/字体）会被过滤"),
    (re.compile(r"<pre[\s>]", re.I), "ERROR",
     "<pre> 代码块会被微信剥离并折叠空格/换行——代码块必须用 <section>+逐行 <p>"),
    (re.compile(r"<table[\s>]", re.I), "ERROR",
     "<table> 在微信端不渲染（手机端整表丢失）——表格用条目卡片 <section> 结构，或渲染成图片"),
    (re.compile(r"<[a-z][^>]*\sclass\s*=", re.I), "ERROR", "class 属性会被剥离，请用内联 style"),
    (re.compile(r"<[a-z][^>]*\sid\s*=", re.I), "ERROR", "id 属性会被剥离"),
    (re.compile(r"<div[\s>]", re.I), "WARN",
     "<div> 标签：API 推送路径实测不清洗、样式保留（板块五已发布文章在用）；"
     "但编辑器粘贴路径会被改写，官方红线不建议——能用 <section> 就用 <section>"),
]

# 样式级红线 —— 只检查元素 style 属性值（代码块文本里的 CSS 示例不算违规）
FORBIDDEN_STYLES = [
    (re.compile(r"position\s*:\s*(fixed|absolute|sticky)", re.I), "ERROR",
     "position fixed/absolute/sticky 不被支持"),
    (re.compile(r"float\s*:", re.I), "ERROR", "float 不被支持"),
    (re.compile(r"@media", re.I), "ERROR", "@media 媒体查询不被支持"),
    (re.compile(r"@keyframes", re.I), "ERROR", "@keyframes 动画不被支持"),
    (re.compile(r"@import", re.I), "ERROR", "@import 不被支持"),
    (re.compile(r"display\s*:\s*grid", re.I), "ERROR", "display:grid 不被支持，多列布局用条目卡片或渲染成图片"),
    (re.compile(r"display\s*:\s*flex", re.I), "WARN",
     "display:flex 微信端支持不稳定（部分机型换行/对齐异常）——多列布局优先用条目卡片或渲染成图片"),
    (re.compile(r"display\s*:\s*table(?:-cell|-row|-column)?\b", re.I), "ERROR",
     "div 伪表格（display:table/table-cell）微信端堆叠成纯文本（实测教训 0088）——表格用条目卡片 <section> 结构，或渲染成图片"),
    (re.compile(r"var\s*\(\s*--", re.I), "ERROR", "CSS 变量 var(--x) 不被支持，请写死值"),
    (re.compile(r"url\s*\(\s*['\"]?https?://[^)]*\.(woff2?|ttf|otf|eot)", re.I),
     "ERROR", "外部字体不被支持"),
]

# 图片本地路径 / 非法域名：正文图必须 mmbiz.qpic.cn（API 推送否则不显示）
IMG_LOCAL = re.compile(r'<img[^>]*\bsrc\s*=\s*["\'](?!https?://)(?!//)[^"\']*["\']', re.I)
IMG_NON_MMBIZ = re.compile(r'<img[^>]*\bsrc\s*=\s*["\'](?:https?://)?(?!mmbiz\.qpic\.cn)[^"\']*["\']', re.I)

CJK = re.compile(r"[一-鿿㐀-䶿]")
# 中文字后紧跟半角逗号/分号/叹号/问号（应改全角）；只查"中文在前"避免中英混排误伤
HALF_PUNCT = re.compile(r"[一-鿿㐀-䶿][,;!?]")
ASCII_QUOTE = re.compile(r"[\"']")
# 英文词内撇号（Owner's / don't / 2000's）——合法英文，检测直引号时豁免
APOSTROPHE_WORD = re.compile(r"[A-Za-z]'\w|\w+'")
# 代码区特征：等宽字体或 white-space:pre —— 其内半角符号/直引号是正常的
CODE_STYLE = re.compile(r"monospace|white-space\s*:\s*pre|courier|consolas|menlo", re.I)
CODE_TAGS = {"code", "pre", "tt"}

# 禁用词/套话（写作纪律，项目内清零；按需增删）
BANNED_WORDS = [
    "本文", "读者", "总而言之", "综上所述", "首先", "其次", "最后，",
    "众所周知", "不难发现", "值得注意的是", "通过以上", "我们可以看到",
]

# AI 味启发式短语（WARNING 级：空洞修辞，命中提示改写为具体表述）
AI_FLAVOR_PHRASES = [
    "功能强大", "强大的功能", "十分强大", "非常强大", "非常简单", "一目了然",
    "显而易见", "不言而喻", "事半功倍", "锦上添花", "赋能", "助力",
    "闭环", "抓手", "值得一提的是", "不难看出", "事实上", "实际上",
    "换句话说", "换言之", "也就是说", "从这个角度", "从这个意义上",
    # —— 4.2.1 扩充：万能开头/结尾与权威腔 ——
    "深入探讨", "深入解析", "全面解析", "一文读懂", "不可否认", "毋庸置疑",
    "毫无疑问", "与此同时", "更重要的是", "不仅仅是", "为我们提供了",
    "带来了前所未有的", "保驾护航", "添砖加瓦", "雨后春笋", "日新月异",
    "画上句号", "揭开了序幕", "新的篇章", "里程碑式", "淋漓尽致",
    "娓娓道来", "跃然纸上", "可见一斑", "概括来说", "由此可见",
    "拭目以待", "迈上新台阶", "提供了有力的", "日益增长", "日趋完善",
]

SKIP_TAGS = {"head", "title", "style", "script"}


class InlineChecker(HTMLParser):
    """统计图片/段落/代码区，检测未转义文本与半角标点。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.code_depth = 0
        self.n_img = 0
        self.n_p = 0
        self.n_section = 0
        self.bad_img = []       # 本地路径/非 mmbiz 图片的 src 片段
        self.half_punct = []    # 正文疑似半角标点片段
        self.style_hits = []    # (style值片段, 说明) —— 元素 style 属性里的红线命中
        self.texts = []         # 非代码区正文文本段（AI 味/长句检查用）

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        style = ad.get("style", "") or ""
        if tag == "img":
            self.n_img += 1
            src = ad.get("src", "")
            if src:
                if not src.startswith(("http://", "https://", "//")):
                    self.bad_img.append((src, "本地路径"))
                elif "mmbiz.qpic.cn" not in src:
                    self.bad_img.append((src, "非 mmbiz 域名"))
        if tag == "p":
            self.n_p += 1
        if tag == "section":
            self.n_section += 1
        # 样式级红线只查真实 style 属性（代码块文本里的 CSS 示例不算）
        if style:
            for rx, level, msg in FORBIDDEN_STYLES:
                if rx.search(style):
                    self.style_hits.append((msg, style[:80]))
        is_code = bool(CODE_STYLE.search(style)) or tag in CODE_TAGS
        if is_code:
            self.code_depth += 1
        self.stack.append((tag, is_code))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, was_code in self.stack[i:]:
                    if was_code:
                        self.code_depth -= 1
                del self.stack[i:]
                break

    def handle_data(self, data):
        text = data.strip()
        if not text or not CJK.search(text):
            return
        if any(t in SKIP_TAGS for t, _, in self.stack):
            return
        if self.code_depth == 0:
            self.texts.append(text)
            # 英文词内撇号（Owner's 等）是合法英文，先剔除再查直引号
            text_naked = APOSTROPHE_WORD.sub("", text)
            if HALF_PUNCT.search(text) or ASCII_QUOTE.search(text_naked):
                snippet = text[:24] + ("…" if len(text) > 24 else "")
                self.half_punct.append(snippet)


def ai_taste_warnings(texts):
    """AI 味启发式检查（WARNING 级，不阻断推送，但逐项人工确认）。
    空洞修辞、感叹号密度、长段节奏、编号排比——命中即提示改写。"""
    warns = []
    joined = "\n".join(texts)
    hits = [w for w in AI_FLAVOR_PHRASES if w in joined]
    if hits:
        warns.append(f"疑似空洞修辞 {len(hits)} 处（{'、'.join(hits[:6])}）"
                     f"——如非必要请改为具体表述")
    n_bang = joined.count("！")
    if n_bang > 3:
        warns.append(f"正文感叹号 {n_bang} 个——技术文宜 ≤3，多用陈述句")
    lens = [len(t) for t in texts if len(t) > 0]
    if lens:
        avg = sum(lens) / len(lens)
        longest = max(lens)
        if longest > 120:
            warns.append(f"最长段落 {longest} 字——长段是 AI 味高发点，建议拆分")
        if avg > 80 and len(lens) >= 3:
            warns.append(f"段落平均 {avg:.0f} 字——节奏偏平，建议长短句交错")
    for trio in (("其一", "其二", "其三"), ("一是", "二是", "三是")):
        if all(t in joined for t in trio):
            warns.append("检测到「%s/%s/%s」编号排比——如为机械罗列，建议改为有层次的论证"
                         % trio)
    return warns


def validate(html, name="<input>"):
    errors, warnings = [], []

    for rx, level, msg in FORBIDDEN_TAGS:
        hits = len(rx.findall(html))
        if hits:
            (errors if level == "ERROR" else warnings).append(
                f"{msg}（命中 {hits} 处）")

    checker = InlineChecker()
    try:
        checker.feed(html)
    except Exception as e:
        warnings.append(f"HTML 解析中断: {e}")

    # 样式级红线（来自真实 style 属性）
    for msg, snippet in checker.style_hits[:6]:
        errors.append(f"{msg}（style 属性片段: {snippet!r}…）")

    # 图片域名
    for src, why in checker.bad_img[:6]:
        errors.append(f"图片 src={src[:60]!r}（{why}）——必须 uploadimg 换成 "
                      f"mmbiz.qpic.cn URL，否则微信端不显示")
    n_local = len(IMG_LOCAL.findall(html))
    n_nonm = len(IMG_NON_MMBIZ.findall(html))
    if n_local:
        errors.append(f"{n_local} 处图片为本地路径（本地路径必不显示）")

    # 纯 section 片段（不包文档外壳）
    head = html.lstrip()[:400]
    if head.lower().startswith("<!doctype") or "<html" in head.lower():
        warnings.append("产物以 <!DOCTYPE>/<html> 开头——应交付纯 <section> 正文片段"
                        "（公众号只认正文片段，文档外壳会被丢弃）")
    if checker.n_img and checker.n_section == 0 and not re.search(r"<section", html):
        warnings.append("全文无 <section> 容器——代码块/卡片请用 <section> 包裹")

    # 禁用词（只查非代码区正文文本，代码块内注释/字符串中的字样不误报）
    body_text = "\n".join(checker.texts)
    found = [w for w in BANNED_WORDS if w in body_text]
    if found:
        errors.append("写作纪律禁用词命中：" + "、".join(found))

    # 半角标点
    if checker.half_punct:
        sample = "；".join(f"「{s}」" for s in checker.half_punct[:5])
        warnings.append(f"{len(checker.half_punct)} 处正文疑似半角标点/英文引号，"
                        f"应改中文全角（代码块内不计）。例：{sample}")

    # AI 味启发式（WARNING，逐项人工确认）
    warnings.extend(ai_taste_warnings(checker.texts))

    # 无图片提示
    if checker.n_img == 0:
        warnings.append("全文无 <img> —— 若本应配图请确认")

    return errors, warnings, checker


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", help="HTML 文件路径")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读取")
    args = ap.parse_args()

    if args.stdin or not args.file:
        html = sys.stdin.read()
        name = "<stdin>"
    else:
        with open(args.file, encoding="utf-8", errors="replace") as f:
            html = f.read()
        name = args.file

    errors, warnings, checker = validate(html, name)

    print(f"📋 wx 内联版 HTML 合规校验: {name}")
    print(f"   img ×{checker.n_img} · p ×{checker.n_p} · section ×{checker.n_section}")
    if errors:
        print(f"\n❌ ERROR ×{len(errors)}（必须修复，否则推送后显示异常）:")
        for e in errors:
            print(f"   • {e}")
    if warnings:
        print(f"\n⚠️  WARNING ×{len(warnings)}（建议检查）:")
        for w in warnings:
            print(f"   • {w}")
    if not errors and not warnings:
        print("\n✅ 完全合规，可推送草稿")
    elif not errors:
        print("\n✅ 无致命问题，可推送草稿（warning 请人工确认）")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
