# -*- coding: utf-8 -*-
"""validate_wx_html.py 每条 ERROR 规则各配一个命中 fixture。

设计要点（可证伪）：fixture 表以「规则正则原文」为键。每当校验器新增一条
ERROR 规则而未配 fixture，本测试立即报红——避免"规则存在但从未被验证过"。
WARNING 级规则不在此表内（不阻断推送）。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "write", "scripts", "validate_wx_html.py")

# 规则正则原文 → 只命中该规则的 HTML 片段
TAG_FIXTURES = {
    r"<style[\s>]": '<section><style>p{color:red}</style><p>正文一</p></section>',
    r"<script[\s>]": '<section><script>window.x=1</script><p>正文一</p></section>',
    r"<link[\s>]": '<section><link rel="stylesheet" href="a.css"><p>正文一</p></section>',
    r"<pre[\s>]": '<section><pre>python a.py --help</pre></section>',
    r"<table[\s>]": '<section><table><tr><td>甲</td><td>乙</td></tr></table></section>',
    r"<[a-z][^>]*\sclass\s*=": '<section><p class="lead">正文一</p></section>',
    r"<[a-z][^>]*\sid\s*=": '<section><p id="lead">正文一</p></section>',
}

STYLE_FIXTURES = {
    r"position\s*:\s*(fixed|absolute|sticky)": '<section style="position:absolute;left:0"><p>正文一</p></section>',
    r"float\s*:": '<section style="float:left"><p>正文一</p></section>',
    r"@media": '<section style="@media screen{p{color:red}}"><p>正文一</p></section>',
    r"@keyframes": '<section style="@keyframes fade{from{opacity:0}}"><p>正文一</p></section>',
    r"@import": '<section style="@import url(a.css)"><p>正文一</p></section>',
    r"display\s*:\s*grid": '<section style="display:grid"><p>正文一</p></section>',
    r"display\s*:\s*table(?:-cell|-row|-column)?\b":
        '<section><div style="display:table"><div style="display:table-cell">甲</div></div></section>',
    r"var\s*\(\s*--": '<section style="color:var(--c)"><p>正文一</p></section>',
    r"url\s*\(\s*['\"]?https?://[^)]*\.(woff2?|ttf|otf|eot)":
        '<section style="font-family:url(\'https://f.example.com/a.woff2\')"><p>正文一</p></section>',
}

CLEAN = ('<section style="margin:0 0 12px;">'
         '<p style="font-size:16px;color:#3f3f3f;line-height:1.9;">'
         '草稿推送前要把校验跑完，差异逐条修到零。</p>'
         '<p style="font-family:Consolas,monospace;white-space:pre;">'
         '本文中的代码行不参与禁用词检查</p>'
         '<img src="https://mmbiz.qpic.cn/mmbiz_png/SAMPLE/640?wx_fmt=png">'
         '</section>')

IMG_FIXTURES = [
    ('<section><img src="../assets/cover.png"></section>', "本地路径"),
    ('<section><img src="https://cdn.example.com/a.png"></section>', "非 mmbiz"),
]

BANNED_FIXTURE = '<section><p>本文将介绍草稿推送的六道工序。</p></section>'


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_wx_html", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    v = load_validator()
    fails = []

    declared = [(rx, msg) for rx, lvl, msg in v.FORBIDDEN_TAGS if lvl == "ERROR"] + \
               [(rx, msg) for rx, lvl, msg in v.FORBIDDEN_STYLES if lvl == "ERROR"]
    fixtures = dict(TAG_FIXTURES)
    fixtures.update(STYLE_FIXTURES)
    for rx, msg in declared:
        if rx.pattern not in fixtures:
            fails.append("新增 ERROR 规则未配 fixture：%s" % msg[:40])
    extra = set(fixtures) - {rx.pattern for rx, _ in declared}
    for pat in sorted(extra):
        fails.append("fixture 对应的规则已不存在（规则被删或改写）：%s" % pat)

    for rx, msg in declared:
        html = fixtures.get(rx.pattern)
        if html is None:
            continue          # 缺 fixture 已在前一段记为失败，这里不再重复炸
        errors, _, _ = v.validate(html)
        key = msg[:12]
        if not any(key in e for e in errors):
            fails.append("规则未报红：%s → 期望错误含「%s」，实得 %s"
                         % (rx.pattern, key, errors))

    for html, label in IMG_FIXTURES:
        errors, _, _ = v.validate(html)
        if not any("uploadimg" in e for e in errors):
            fails.append("图片 %s 未报红：%s" % (label, errors))

    errors, _, _ = v.validate(BANNED_FIXTURE)
    if not any("禁用词" in e for e in errors):
        fails.append("禁用词未报红：%s" % errors)

    errors, _, _ = v.validate(CLEAN)
    if errors:
        fails.append("合规样例被误判（ERROR 应清零）：%s" % errors)
    if any("本文" in w for w in errors):
        fails.append("代码区文本误入禁用词检查")

    print("validate_wx_html 规则 fixture：%d 条 ERROR 规则逐条命中，%d 项失败"
          % (len(declared), len(fails)))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
