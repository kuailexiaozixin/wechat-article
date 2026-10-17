# -*- coding: utf-8 -*-
"""read_wechat.py 质量门、降级判据与 Markdown 转换测试（离线，不联网）。

判定方向逐条对撞：正文缺失要 FAIL、验证墙要 FAIL、短文有标题+发布时间要放行、
短文缺发布时间要 FAIL。只测「取到了就算过」等于没测——四例里任何一例判反即报红。
"""
import importlib.util
import io
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


def _read_rel(*parts):
    """按磁盘真实名字读技能内文件（发布树把 write/read/Search 收成小写，此处两种布局都要能跑）。"""
    cur = os.path.normpath(os.path.join(HERE, os.pardir))
    for p in parts:
        hit = [n for n in os.listdir(cur) if n.lower() == p.lower()]
        if not hit:
            return ""
        cur = os.path.join(cur, hit[0])
    if not os.path.isfile(cur):
        return ""
    with io.open(cur, encoding="utf-8", errors="replace") as f:
        return f.read()


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

    # 8) CDP 前置检查：端口文件路径不写死单一平台，且取不到时给出明确原因
    saved = os.environ.pop(R.DEVTOOLS_ENV, None)
    try:
        # 8a) 环境变量指定路径优先于任何平台默认候选（跨平台可分发的唯一出口）
        tmp_port = os.path.join(os.environ.get("TEMP") or "/tmp",
                                "wx_test_devtools_port_%d.txt" % os.getpid())
        with io.open(tmp_port, "w", encoding="utf-8", newline="") as f:
            f.write("9222\n/devtools/browser/test-uuid\n")
        os.environ[R.DEVTOOLS_ENV] = tmp_port
        if R.devtools_port_file() != tmp_port:
            fails.append("%s 指向的文件未被优先采用" % R.DEVTOOLS_ENV)
        ws = R.devtools_ws_url()
        if ws != "ws://127.0.0.1:9222/devtools/browser/test-uuid":
            fails.append("devtools_ws_url 两行拼接结果不符：%s" % ws)
        os.remove(tmp_port)
        # 8b) 指定的文件不存在 → 报错要点名环境变量与路径，不能只报候选目录
        os.environ[R.DEVTOOLS_ENV] = tmp_port
        try:
            R.devtools_port_file()
            fails.append("指定的端口文件不存在时未报错")
        except Exception as e:
            if R.DEVTOOLS_ENV not in str(e) or tmp_port not in str(e):
                fails.append("报错未点名 %s 与路径：%s" % (R.DEVTOOLS_ENV, e))
        # 8c) 端口文件只有一行 → 必须报「内容不完整」，不能拼出一个缺路径的 ws 地址
        with io.open(tmp_port, "w", encoding="utf-8", newline="") as f:
            f.write("9222\n")
        os.environ[R.DEVTOOLS_ENV] = tmp_port
        try:
            ws = R.devtools_ws_url()
            fails.append("端口文件缺一行却返回了地址：%s" % ws)
        except Exception as e:
            if "内容不完整" not in str(e):
                fails.append("缺一行时的报错没说明是内容不完整：%s" % e)
        os.remove(tmp_port)
        # 8d) 未指定时按当前平台的候选找；候选全不存在 → 报错说明缺哪个前提
        os.environ.pop(R.DEVTOOLS_ENV)
        real_cands = R.devtools_port_candidates()
        if not any(os.path.exists(p) for p in real_cands):
            try:
                R.devtools_ws_url()
                fails.append("无端口文件时 devtools_ws_url 未报错")
            except Exception as e:
                if "Edge" not in str(e) and "DevToolsActivePort" not in str(e):
                    fails.append("报错未说明缺哪个前提：%s" % e)
        # 8e) 候选路径必须跟着当前平台走：非 win32 不得给出 AppData 那一条
        #     （按 sys.platform 现取现判，所以同一份判据在三种平台上都跑得动）
        saved_platform, R.sys.platform = R.sys.platform, "win32"
        try:
            win = R.devtools_port_candidates()
            R.sys.platform = "darwin"
            mac = R.devtools_port_candidates()
            R.sys.platform = "linux"
            lnx = R.devtools_port_candidates()
        finally:
            R.sys.platform = saved_platform
        if not any("User Data" in p for p in win):
            fails.append("win32 候选里没有 Edge 的 User Data 路径：%s" % win)
        for label, cands in (("darwin", mac), ("linux", lnx)):
            if any("AppData" in p or "User Data" in p for p in cands):
                fails.append("%s 平台给出了 Windows 路径：%s" % (label, cands))
            if not cands:
                fails.append("%s 平台没有候选路径" % label)
        # 三个平台必须给出三种形状：某一家的分支塌了（`if False`，或 win32 判据恒真）会让其中
        # 两行变相同，靠「两两不同」把它们揪出来
        if len({tuple(win), tuple(mac), tuple(lnx)}) != 3:
            fails.append("三个平台的候选路径没有两两不同，平台分支已塌：win32=%s darwin=%s linux=%s"
                         % (win, mac, lnx))
        if not any("Library" in p for p in mac):
            fails.append("darwin 候选里没有 macOS 的 Library 目录：%s" % mac)
        if not any("microsoft-edge" in p for p in lnx):
            fails.append("linux 候选里没有 Edge 的配置目录名：%s" % lnx)
    finally:
        os.environ.pop(R.DEVTOOLS_ENV, None)
        if saved is not None:
            os.environ[R.DEVTOOLS_ENV] = saved

    # 9) 重试上限三处口径同值：常量、脚本 docstring、两份文档必须写同一个数
    import inspect
    default_tries = inspect.signature(R.http_get).parameters["tries"].default
    if default_tries != R.LAYER_TRIES:
        fails.append("http_get 默认 tries=%s 与常量 LAYER_TRIES=%s 不一致，上限改了行为没跟"
                     % (default_tries, R.LAYER_TRIES))
    if R.HTTP_MAX_PER_URL != 3 * R.LAYER_TRIES:
        fails.append("HTTP_MAX_PER_URL=%s 不等于三层 × 每层 %s 次"
                     % (R.HTTP_MAX_PER_URL, R.LAYER_TRIES))
    want = "%d 次" % R.HTTP_MAX_PER_URL
    for label, text in (("read_wechat docstring", R.__doc__ or ""),
                        ("read/SKILL.md", _read_rel("read", "SKILL.md")),
                        ("read/references/cdp-edge.md", _read_rel("read", "references", "cdp-edge.md"))):
        if want not in text:
            fails.append("%s 没写出合计上限 %s（常量已改或口径漏同步）" % (label, want))

    print("read_wechat 质量门/转换测试：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
