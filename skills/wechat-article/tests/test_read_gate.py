# -*- coding: utf-8 -*-
"""read_wechat.py 质量门、降级判据与 Markdown 转换测试（离线，不联网）。

判定方向逐条对撞：正文缺失要 FAIL、验证墙要 FAIL、短文有标题+发布时间要放行、
短文缺发布时间要 FAIL。只测「取到了就算过」等于没测——四例里任何一例判反即报红。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


def _load():
    path = os.path.join(HERE, os.pardir, "read", "scripts", "read_wechat.py")
    spec = importlib.util.spec_from_file_location("read_wechat", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def page(content_inner, title="测试标题", published="2026-04-18 09:30"):
    head = '<meta property="og:title" content="%s">' % title
    if published:
        head += '<meta property="article:published_time" content="%s">' % published
    return ('<html><head>%s</head><body><div id="js_content" style="visibility: hidden;">'
            '%s</div></body></html>' % (head, content_inner))


LONG = "<p>%s</p>" % ("排版是工程问题，不是审美问题。" * 60)     # 840 字 > 800 阈值
SHORT = "<p>只有一段话的短文。</p>"


def run():
    R = _load()
    fails = []
    url = "https://mp.weixin.qq.com/s/SAMPLE"

    # 1) 真实结构样本：应通过，且转成 Markdown 保留结构
    with open(os.path.join(FIX, "mp_article_sample.html"), encoding="utf-8") as f:
        sample = f.read()
    r = R.read_from_html(sample, url)
    if not r["ok"]:
        fails.append("合格样本被判失败：%s" % r["diag"])
    else:
        if r["chars"] < 800:
            fails.append("样本字数统计异常：%d" % r["chars"])
        md = r["markdown"]
        for token, why in (("## 第一道：结构先于样式", "二级标题"),
                           ("- 每段一个论点", "无序列表"),
                           ("1. 先通读一遍", "有序列表"),
                           ("**验收标准**", "加粗"),
                           ("```\npython read/scripts", "代码块围栏"),
                           ("> 引用的官方文档", "引用块"),
                           ("![微信配图](https://mmbiz.qpic.cn/mmbiz_png/IMGSAMPLE/640?wx_fmt=png)",
                            "图片地址")):
            if token not in md:
                fails.append("Markdown 缺少%s（未命中 %r）" % (why, token[:40]))
        if "wx_lazy" in md:
            fails.append("图片地址未清掉 wx_lazy 懒加载参数")
        if "script" in md.lower() and "window." in md:
            fails.append("脚本内容混进正文")
        fm = R.frontmatter(r["meta"], r["layer"], r["chars"], r["note"])
        for k in ("source_url", "title", "author", "account", "published", "cover",
                  "digest", "extract_layer", "content_chars"):
            if ("%s:" % k) not in fm:
                fails.append("frontmatter 缺字段 %s" % k)
        if 'title: "公众号排版' not in fm:
            fails.append("frontmatter 标题取值错误：%s" % fm[:120])

    # 2) 正文节点缺失 → FAIL
    r2 = R.read_from_html(page(LONG).replace('id="js_content"', 'id="other_content"'), url)
    if r2["ok"] or "正文节点缺失" not in " ".join(r2["diag"]):
        fails.append("正文节点缺失未判 FAIL：%s" % r2["diag"])

    # 3) 验证墙标记 → FAIL（即便页面很长）
    r3 = R.read_from_html(page(LONG + "<p>当前环境异常，完成验证后即可继续访问。</p>"), url)
    if r3["ok"] or "验证墙" not in " ".join(r3["diag"]):
        fails.append("验证墙标记未判 FAIL：%s" % r3["diag"])

    # 4) 短文 + 标题 + 发布时间 → 豁免放行
    r4 = R.read_from_html(page(SHORT), url)
    if not r4["ok"] or "短文豁免" not in r4["note"]:
        fails.append("短文豁免未生效：%s / %s" % (r4["ok"], r4["note"]))

    # 5) 短文 + 无发布时间 → FAIL（豁免不能变成无条件放行）
    r5 = R.read_from_html(page(SHORT, published=""), url)
    if r5["ok"]:
        fails.append("短文缺发布时间仍被判通过，豁免条件失效")

    # 6) 图片地址清洗：去 wx_lazy、留 wx_fmt/wx_co
    cleaned = R.clean_img_src("https://mmbiz.qpic.cn/a/640?wx_fmt=jpeg&wx_lazy=1&wx_co=1")
    if "wx_lazy" in cleaned or "wx_fmt=jpeg" not in cleaned or "wx_co=1" not in cleaned:
        fails.append("clean_img_src 清洗结果不符：%s" % cleaned)

    # 7) 阈值常量与文档一致（阈值漂移会让短文豁免悄悄改变语义）
    if R.MIN_FULLTEXT_CHARS != 800:
        fails.append("MIN_FULLTEXT_CHARS 已变为 %d，需同步脚本说明与测试"
                     % R.MIN_FULLTEXT_CHARS)

    # 8) CDP 前置检查在没有端口文件时给出明确原因（不是静默跳过）
    if os.path.exists(os.path.expanduser(
            r"~\AppData\Local\Microsoft\Edge\User Data\DevToolsActivePort")):
        try:
            ws = R.devtools_ws_url()
            if not ws.startswith("ws://127.0.0.1:"):
                fails.append("devtools_ws_url 返回值异常：%s" % ws)
        except Exception as e:
            fails.append("端口文件存在却取不到 ws 地址：%s" % e)
    else:
        try:
            R.devtools_ws_url()
            fails.append("无端口文件时 devtools_ws_url 未报错")
        except Exception as e:
            if "Edge" not in str(e) and "DevToolsActivePort" not in str(e):
                fails.append("报错未说明缺哪个前提：%s" % e)

    print("read_wechat 质量门/转换测试：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
