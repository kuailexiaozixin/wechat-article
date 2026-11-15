# -*- coding: utf-8 -*-
"""B5 回读归一化判据：抵消微信草稿接口的确定性图片改写，但绝不吞掉真实差异。

背景（2026-11-15 第二篇实测）：微信草稿接口把
    <img src="https://mmbiz.qpic.cn/.../0?from=appmsg" alt="..." style="...">
改写成
    <img alt="..." data-src="https://mmbiz.qpic.cn/.../640" style="...">
即：src 改名成 data-src、属性重排、规格尾缀 /0 变成 /640、查询参数被去掉。
旧版 norm_html() 只剥查询参数，B5 因此在归一化位置 1768 误报「正文与源不一致」。

本判据同时守两头，防止把校验修宽成摆设：
  正例 —— 平台标准化改写之后仍须逐字相等；
  反例 —— 正文文字、图片主体、图数、图片说明、样式、标签结构任一处真改动仍须判不等。
只放宽平台改写点，不放宽内容。离线、不联网、不需凭据，变异即报红。
"""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

IMG_SRC = ('<img src="https://mmbiz.qpic.cn/mmbiz_png/QaibgPO7a/0?from=appmsg" '
           'alt="文章标题图" '
           'style="max-width:100%;border-radius:10px;display:block;margin:0 auto;">')
IMG_WX = ('<img alt="文章标题图" '
          'data-src="https://mmbiz.qpic.cn/mmbiz_png/QaibgPO7a/640" '
          'style="max-width:100%;border-radius:10px;display:block;margin:0 auto;">')
HEAD = '<section style="text-align:center;margin:0 0 10px;">'
BODY = '<p style="font-size:16px;color:#3f3f3f;">正文一句话。</p>'
SRC = HEAD + IMG_SRC + '</section>' + BODY
WX = HEAD + IMG_WX + '</section>' + BODY


def _load():
    """加载根 scripts/check_draft.py；它 import 同目录的 wx_api，故先补 sys.path。"""
    path = os.path.join(ROOT, "scripts", "check_draft.py")
    if os.path.dirname(path) not in sys.path:
        sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location("check_draft_norm_t", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_platform_rewrite_equal():
    """平台改写点必须被抵消；缺失任何一条都会让 B5 误报。"""
    cd = _load()
    p = IMG_WX
    cases = [
        ("src 改 data-src + 属性重排 + /0 变 /640", WX),
        ("属性用单引号", HEAD + p.replace('"', "'") + '</section>' + BODY),
        ("标签间空白与 CRLF", HEAD + "\r\n  " + p + "\r\n  </section>\r\n" + BODY),
        ("另一组查询参数", HEAD + IMG_SRC.replace("?from=appmsg", "?wx_fmt=png")
         + '</section>' + BODY),
        ("尾缀换成别的规格数字", HEAD + p.replace("/640", "/0") + '</section>' + BODY),
    ]
    fails = []
    for name, candidate in cases:
        if cd.norm_html(SRC) != cd.norm_html(candidate):
            fails.append("平台改写未抵消：%s" % name)
    return fails


def test_real_diff_still_fail():
    """真实内容差异必须仍判不等，防止归一化把 B5 修成永远通过。"""
    cd = _load()
    cases = [
        ("正文改字", WX.replace("正文一句话", "正文被改过")),
        ("图片主体换掉", WX.replace("/QaibgPO7a/640", "/DIFFERENT/640")),
        ("图片换成站外域名", HEAD + IMG_WX.replace("https://mmbiz.qpic.cn/mmbiz_png/QaibgPO7a/640",
                                              "https://example.com/a.png") + '</section>' + BODY),
        ("少一张图", BODY),
        ("多一张图", WX + HEAD + IMG_WX + '</section>'),
        ("图片说明改字", WX.replace('alt="文章标题图"', 'alt="另一张图"')),
        ("样式改值", WX.replace("border-radius:10px", "border-radius:0")),
        ("外层标签结构变了", WX.replace("</section>", "</p>")),
        ("src 与 data-src 同时存在的畸形标签",
         HEAD + IMG_WX.replace("<img ", "<img src=\"https://mmbiz.qpic.cn/mmbiz_png/QaibgPO7a/0\" ")
         + '</section>' + BODY),
        ("段落被删", HEAD + IMG_WX + '</section>'),
    ]
    fails = []
    for name, candidate in cases:
        if cd.norm_html(SRC) == cd.norm_html(candidate):
            fails.append("真实差异被吞掉：%s" % name)
    return fails


def test_check_end_to_end():
    """在 check() 的真实调用链上锁住行为，而不只测归一化函数本身。"""
    cd = _load()
    fails = []
    old = {k: os.environ.get(k) for k in ("WECHAT_APPID", "WECHAT_SECRET")}
    os.environ["WECHAT_APPID"] = "fake"
    os.environ["WECHAT_SECRET"] = "fake"
    cd.get_token = lambda a, b: {"access_token": "fake"}
    art = {"title": "归一化判据测试", "digest": "摘要",
           "thumb_media_id": "THUMB", "content": WX}
    cd.draft_get = lambda token, mid: {"news_item": [art]}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "article.html")
            with open(src, "w", encoding="utf-8") as f:
                f.write(SRC)
            res = cd.check("MID", source_path=src)
            names = {n: st for n, st, _ in res["checks"]}
            if names.get("正文与源一致") != "PASS":
                fails.append("平台改写后 check() 仍判 FAIL：%s" % names)
            art["content"] = WX.replace("正文一句话", "正文被改过")
            res2 = cd.check("MID", source_path=src)
            names2 = {n: st for n, st, _ in res2["checks"]}
            if names2.get("正文与源一致") != "FAIL":
                fails.append("正文真改了 check() 却判 PASS：%s" % names2)
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    return fails


def run():
    fails = []
    for fn in (test_platform_rewrite_equal, test_real_diff_still_fail,
               test_check_end_to_end):
        sub = fn()
        print("%-32s %s" % (fn.__name__, "OK" if not sub else "FAIL ×%d" % len(sub)))
        fails += ["%s: %s" % (fn.__name__, f) for f in sub]
    for f in fails:
        print("   FAIL", f)
    if not fails:
        print("归一化判据：平台改写全抵消 · 真实差异全拦下 · 端到端调用链一致")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
