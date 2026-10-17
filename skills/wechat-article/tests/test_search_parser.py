# -*- coding: utf-8 -*-
"""search/scripts/search_wechat.py 解析与还原测试（全程离线，不联网）。

fixture 来源：tests/fixtures/sogou_type2_sample.html（真实结果页结构切片，10 条）、
sogou_two_items_sample.html（两条，字段值可逐字断言）、sogou_empty_page.html（0 条）、
sogou_antispider_sample.html（拦截页）、sogou_link_wrapper_sample.html（url += 拼接形态）。
"""
import importlib.util
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")
sys.path.insert(0, os.path.join(HERE, os.pardir, "search", "scripts"))


def _load():
    path = os.path.join(HERE, os.pardir, "search", "scripts", "search_wechat.py")
    spec = importlib.util.spec_from_file_location("search_wechat", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read(name):
    with open(os.path.join(FIX, name), encoding="utf-8") as f:
        return f.read()


def run():
    S = _load()
    fails = []

    # 1) 真实结果页切片：10 条，字段齐备
    items, note = S.parse_results(read("sogou_type2_sample.html"))
    if len(items) != 10:
        fails.append("真实切片应解析出 10 条，实得 %d（note=%s）" % (len(items), note))
    if not items:
        fails.append("真实切片解析为空，后续断言无法进行")
        return fails
    first = items[0]
    if not first["title"] or "<" in first["title"]:
        fails.append("标题未去标签或为空：%r" % first["title"])
    if not first["account"]:
        fails.append("公众号名未解析：%r" % first)
    if first["timestamp"] is None or not re.match(r"^\d{4}-\d{2}-\d{2}$", first["published"]):
        fails.append("timeConvert Unix 时间戳未转日期：%r" % first["published"])
    if first["published"] != time.strftime("%Y-%m-%d", time.localtime(first["timestamp"])):
        fails.append("日期换算与时间戳不符：%s vs %s" % (first["published"], first["timestamp"]))
    if not first["link"].startswith("https://weixin.sogou.com/link?url="):
        fails.append("跳转链接未补成绝对地址：%s" % first["link"][:60])
    if "&amp;" in first["link"]:
        fails.append("链接未反转义（&amp; 残留会让 /link 请求失败）")
    if not first["summary"]:
        fails.append("摘要未解析")

    # 2) 小样本：逐字段断言具体值
    two, _ = S.parse_results(read("sogou_two_items_sample.html"))
    if len(two) != 2:
        fails.append("小样本应 2 条，实得 %d" % len(two))
    else:
        if two[0]["title"] != "微信公众号排版的六个步骤":
            fails.append("标题（含 <em> 高亮剥离后）不符：%r" % two[0]["title"])
        if two[0]["account"] != "样例公众号":
            fails.append("公众号名不符：%r" % two[0]["account"])
        if two[0]["timestamp"] != 1700000000:
            fails.append("时间戳不符：%r" % two[0]["timestamp"])

    # 3) 空页与拦截页的判据方向
    empty, note_e = S.parse_results(read("sogou_empty_page.html"))
    if empty or "0 条" not in note_e:
        fails.append("空列表页应判「本页 0 条」，实得 %r / %r" % (len(empty), note_e))
    junk, note_j = S.parse_results("<html><body>Nothing</body></html>")
    if junk or "结构" not in note_j:
        fails.append("无结果容器页应判「结构已变/被拦截」，实得 %r / %r" % (junk, note_j))
    reason = S.block_reason({"html": read("sogou_antispider_sample.html"),
                             "final_url": "https://weixin.sogou.com/weixin?type=2"})
    if not reason:
        fails.append("拦截页未被 block_reason 认出（会被当正常页继续解析）")
    reason2 = S.block_reason({"html": "<html>ok</html>",
                              "final_url": "https://weixin.sogou.com/"})
    if not reason2 or "302" not in reason2:
        fails.append("302 回首页未被识别为拦截：%r" % reason2)
    if S.block_reason({"html": "<html>正常结果页</html>",
                       "final_url": "https://weixin.sogou.com/weixin?type=2&query=x"}):
        fails.append("正常页被误判为拦截")

    # 4) 搜索 URL 纪律：不带 tsn/ft/et（实测这些参数会把请求 302 回首页）
    url = S.SEARCH_TPL % (requote("公众号排版"), 3)
    for bad in ("tsn=", "ft=", "et="):
        if bad in url:
            fails.append("搜索 URL 含已失效时间筛选参数 %s" % bad)
    if "page=3" not in url or "type=2" not in url:
        fails.append("搜索 URL 缺少分页或类型参数：%s" % url)
    if S.MAX_PAGE != 10:
        fails.append("分页上限常量应为 10（实测 page=11 起空列表）")

    # 5) 跳转还原三形态（用打桩 fetch 直接驱动 resolve_link，不联网）
    wrapper = read("sogou_link_wrapper_sample.html")
    S302 = _load()
    S302.fetch = lambda opener, url, referer=None, tries=3: {
        "html": "<html></html>", "final_url": "https://mp.weixin.qq.com/s?src=11&x=1"}
    u, how = S302.resolve_link(None, "https://weixin.sogou.com/link?url=x")
    if how != "302" or not (u or "").startswith("https://mp.weixin.qq.com"):
        fails.append("形态一（302 Location）判定失败：%r %r" % (u, how))

    Sconcat = _load()
    Sconcat.fetch = lambda opener, url, referer=None, tries=3: {
        "html": wrapper, "final_url": "https://weixin.sogou.com/link?url=x"}
    u, how = Sconcat.resolve_link(None, "https://weixin.sogou.com/link?url=x")
    expect = "https://mp.weixin.qq.com/s?src=11&timestamp=1792213530&ver=7031&signature=SAMPLESIGNATURETAIL&new=1"
    if how != "url-concat" or u != expect:
        fails.append("形态三（url += 片段拼接）还原不符：%r %r" % (u, how))

    Smeta = _load()
    Smeta.fetch = lambda opener, url, referer=None, tries=3: {
        "html": '<meta http-equiv="refresh" content="0;url=https://mp.weixin.qq.com/s?abc=1">',
        "final_url": "https://weixin.sogou.com/link?url=x"}
    u, how = Smeta.resolve_link(None, "https://weixin.sogou.com/link?url=x")
    if how != "meta-refresh" or u != "https://mp.weixin.qq.com/s?abc=1":
        fails.append("形态二（meta refresh）还原不符：%r %r" % (u, how))

    Sasp = _load()
    Sasp.fetch = lambda opener, url, referer=None, tries=3: {
        "html": read("sogou_antispider_sample.html"),
        "final_url": "https://weixin.sogou.com/antispider/?from=%2Flink"}
    u, how = Sasp.resolve_link(None, "https://weixin.sogou.com/link?url=x")
    if u is not None or how != "antispider":
        fails.append("还原遇 antispider 未返回可停止的信号：%r %r" % (u, how))

    # 6) -n 决定网络请求数（还原只针对交付条数，不整页还原）
    S.fetch = lambda opener, url, referer=None, tries=3: {
        "html": read("sogou_type2_sample.html"), "final_url": url}
    S.time.sleep = lambda *a: None
    calls = []
    S.resolve_link = lambda opener, link, referer=None: (
        calls.append(link) or "https://mp.weixin.qq.com/s?ok", "url-concat")
    for want in (1, 3):
        del calls[:]
        got, _ = S.search("公众号排版", want=want, pages=1, resolve=True)
        if len(got) != want or len(calls) != want:
            fails.append("-n %d：交付 %d 条却发起 %d 次还原请求"
                         % (want, len(got), len(calls)))

    # 7) 还原遇 antispider 立即停止（不再撞剩余条目）
    def flaky(opener, link, referer=None):
        calls.append(link)
        if len(calls) == 1:
            return "https://mp.weixin.qq.com/s?ok", "url-concat"
        return None, "antispider"
    S.resolve_link = flaky
    del calls[:]
    got, notes = S.search("公众号排版", want=5, pages=1, resolve=True)
    if len(calls) != 2:
        fails.append("遇 antispider 后仍继续还原（请求 %d 次，应为 2 次）" % len(calls))
    if not any("antispider" in n for n in notes):
        fails.append("遇 antispider 未打印 NOTE：%s" % notes)
    if len(got) != 5:
        fails.append("还原失败不应影响交付条数：%d" % len(got))

    # 8) --after/--before：客户端按时间戳筛，闭区间，边界含当天首末秒
    lo17 = S.date_bound("2026-10-17")
    hi17 = S.date_bound("2026-10-17", end_of_day=True)
    if time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(lo17)) != "2026-10-17 00:00:00":
        fails.append("--after 端点不是当日 00:00:00：%s" % time.localtime(lo17))
    if time.strftime("%H:%M:%S", time.localtime(hi17)) != "23:59:59":
        fails.append("--before 端点不是当日 23:59:59（漏掉当天白天就等于把当天筛没了）")
    if not (abs(S.date_bound("2026-10-18") - lo17 - 86400) <= 3600):
        fails.append("相邻两天的端点差不是 86400 秒")
    for bad in ("2026-13-45", "2026/10/17", "10-17", "2026-10", "", "abc"):
        try:
            S.date_bound(bad)
            fails.append("非法日期未被拒绝：%r" % bad)
        except ValueError:
            pass

    def art(ts, title="t"):
        return {"title": title, "link": "", "account": "", "published": "",
                "timestamp": ts, "summary": ""}
    keep, no_ts, out = S.filter_window([art(1760000000), art(lo17), art(hi17), art(None)],
                                       lo17, hi17)
    if len(keep) != 2 or out != 1 or no_ts != 1:
        fails.append("时间窗闭区间/无时间戳判定不符：keep=%d 窗口外=%d 无时间戳=%d"
                     % (len(keep), out, no_ts))
    if keep and keep[0]["timestamp"] != lo17:
        fails.append("窗口内保序失败：%r" % keep)

    # 9) search() 带窗口：过滤靠多翻页保证覆盖，且不把时间参数交给搜狗
    real = read("sogou_type2_sample.html")          # 10 条，全部 2026-10-17
    def make_stub(urls):
        def _f(opener, url, referer=None, tries=3):
            urls.append(url)
            return {"html": real, "final_url": url}
        return _f
    S9 = _load()
    S9.time.sleep = lambda *a: None
    urls = []
    S9.fetch = make_stub(urls)
    got, notes = S9.search("税务", want=3, pages=10, window=(S9.date_bound("2026-10-17"),
                                                             S9.date_bound("2026-10-17", True)))
    page_calls = [u for u in urls if "weixin?" in u]
    if len(got) != 3:
        fails.append("窗口内应有 3 条交付，实得 %d" % len(got))
    if len(page_calls) != 1:
        fails.append("凑够 -n 后没有停页（搜索页请求 %d 次，应 1 次）" % len(page_calls))
    del urls[:]
    got, notes = S9.search("税务", want=5, pages=10, window=(S9.date_bound("2020-01-01"),
                                                             S9.date_bound("2020-01-02", True)))
    page_calls = [u for u in urls if "weixin?" in u]
    if got:
        fails.append("窗口外仍交付了 %d 条" % len(got))
    if len(page_calls) != 10:
        fails.append("空窗口应翻满 10 页再下结论（实翻 %d 页）——只翻 1 页就报没结果是"
                     "把覆盖不足当成搜狗没收录" % len(page_calls))
    if not any("时间窗口过滤" in n for n in notes):
        fails.append("带窗口没打印覆盖说明：%s" % notes)
    if any(("tsn=" in u) or ("ft=" in u) or ("et=" in u) or ("ss_st=" in u) for u in urls):
        fails.append("窗口过滤把时间参数交给搜狗了（实测这些参数会 302 回首页）")
    if not any("非严格倒序" in n for n in notes):
        fails.append("覆盖说明缺「同页日期非严格倒序」提醒")

    # 10) resolved_at：还原成功即落本机时刻
    S10 = _load()
    S10.time.sleep = lambda *a: None
    S10.fetch = lambda opener, url, referer=None, tries=3: {"html": real, "final_url": url}
    S10.resolve_link = lambda opener, link, referer=None: ("https://mp.weixin.qq.com/s?x=1", "302")
    got, _ = S10.search("税务", want=2, pages=1, resolve=True)
    if not all(isinstance(it.get("resolved_at"), int) for it in got):
        fails.append("还原成功未写 resolved_at（票据时效变成只能口头提醒）：%s" % got[:1])
    if "还原时刻" not in S10.render(got, "text", "税务"):
        fails.append("text 输出未打印还原时刻")
    if "resolved_at" not in S10.render(got, "json", "税务"):
        fails.append("json 输出未带 resolved_at")

    # 11) 结构哨兵：真实切片四类节点齐备（10/10/10/10，链接却有 20 条——不能拿链接数判定）
    items, note = S.parse_results(real)
    if note:
        fails.append("真实结果页被误报结构漂移：%s" % note)
    if len(re.findall(r'/link\?url=', real)) < 20:
        fails.append("切片里每条结果的第二跳链接不见了，哨兵的连接数豁免失去依据")
    one = real.replace("timeConvert('", "xx('", 1)
    its, note = S.parse_results(one)
    if len(its) != 10 or "时间戳" not in note:
        fails.append("抽掉 1 个 timeConvert 未报字段命中率下降（its=%d note=%r）" % (len(its), note))
    b0 = re.search(r'<li\b[^>]*id="sogou_vr_[\w]+_box_0".*?<h3>', real, re.S).group(0)
    two = real.replace(b0, b0.replace("<h3>", "<div>"), 1)   # box_0 标题标签改掉：TITLE_RX 失配
    its, note = S.parse_results(two)
    if len(its) != 9 or "结构漂移" not in note:
        fails.append("拆掉 box_0 的 h3 标题未报结构漂移（its=%d note=%r）" % (len(its), note))
    box = re.search(r'<li\b[^>]*id="sogou_vr_[\w]+_box_0"', real).group(0)
    its, note = S.parse_results(real.replace(box, "<li id=\"other\">", 1))
    if "结构漂移" not in note:
        fails.append("box id 改名后未报结构漂移（its=%d note=%r）" % (len(its), note))
    S11 = _load()
    S11.time.sleep = lambda *a: None
    urls11 = []
    S11.fetch = make_stub(urls11)
    got, notes = S11.search("税务", want=3, pages=1, resolve=False)
    if not got:
        fails.append("哨兵误报会连带影响交付（本例页面已被改动？）")

    # 12) 传输层异常：既不崩溃，也不冒充「被拦」或「本页 0 条」
    S12 = _load()
    S12.time.sleep = lambda *a: None
    calls12 = []

    def err_fetch(opener, url, referer=None, tries=3):
        calls12.append(url)
        return {"error": "URLError: timed out", "final_url": None}
    S12.fetch = err_fetch
    try:
        got, notes = S12.search("税务", want=3, pages=5, resolve=False, log=lambda *a: None)
        crashed = None
    except Exception as e:
        got, notes, crashed = [], [], "%s: %s" % (type(e).__name__, e)
    if crashed:
        fails.append("搜索页一次超时就把脚本打崩（%s）——传输异常该是一条 NOTE，不是一条回溯" % crashed)
    else:
        if got:
            fails.append("传输异常却交付了 %d 条" % len(got))
        if not any("传输层异常" in n for n in notes):
            fails.append("传输异常没打印可区分的 NOTE：%s" % notes)
        for word in ("被拦截", "本页 0 条"):
            if any(word in n for n in notes):
                fails.append("传输异常被说成了「%s」，三态混淆：%s" % (word, notes))
        pages12 = [u for u in calls12 if "weixin?" in u]
        if len(pages12) != 1:
            fails.append("传输异常后仍在翻页（搜索页请求 %d 次，应停在第 1 页）" % len(pages12))

    S12b = _load()
    S12b.time.sleep = lambda *a: None
    S12b.fetch = lambda opener, url, referer=None, tries=3: {
        "html": read("sogou_antispider_sample.html"), "final_url": url}
    _, notes_b = S12b.search("税务", want=3, pages=3, resolve=False, log=lambda *a: None)
    if not any("被拦截" in n for n in notes_b) or any("传输层异常" in n for n in notes_b):
        fails.append("拦截态与传输态的文案没有互斥：%s" % notes_b)
    # 拦截标记的两侧：只有 anti.min.css 的拦截页要判成拦截，真结果页绝不能误判
    only_css = ('<html><head><link rel="stylesheet" href="static/css/anti.min.css?v=1"/>'
                '</head><body><div class="anti-wrap">完成验证后即可继续访问</div></body></html>')
    why = S.block_reason({"html": only_css, "final_url": "https://weixin.sogou.com/weixin?type=2"})
    if not why or "anti.min.css" not in why:
        fails.append("仅带 anti.min.css 的拦截页没判成拦截（%r）——该标记在仓库样本里实存，"
                     "去掉它这条判据就失效" % why)
    if S.block_reason({"html": real, "final_url": "https://weixin.sogou.com/weixin?type=2"}):
        fails.append("真实结果页被误判成拦截：标记集在好页面上命中了")

    # 13) 结果页 href 验域：外域链接不交付、也不为它发请求
    # 只改标题锚点的 href——每条结果另有 img 锚点也指 /link（一页 20 条链接），
    # 用「第一次出现的 href="/link」下手会 poison 到 img，解析器根本读不到。
    m13 = re.search(r'(<h3[^>]*>\s*<a\b[^>]*?href=")([^"]*)(")', real, re.S)
    if not m13:
        fails.append("切片里找不到标题锚点的 href，验域判据无法构造（fixture 变了要同步这里）")
        bad = real
    else:
        bad = real[:m13.start(2)] + "//evil.example.com/pwn?x=1" + real[m13.end(2):]
    if bad != real:
        its, note13 = S.parse_results(bad)
        hit = [it for it in its if it.get("link_error")]
        if len(hit) != 1:
            fails.append("协议相对外链未被拦下（拦下 %d 条）" % len(hit))
        elif hit[0]["link"]:
            fails.append("外域链接仍然交付：%s" % hit[0]["link"][:60])
        elif "weixin.sogou.com" not in hit[0]["link_error"]:
            fails.append("拦下却没说明原因：%r" % hit[0]["link_error"])
        if len(its) != 10 or "结构漂移" in (note13 or ""):
            fails.append("验域丢链接被误报成结构漂移（its=%d note=%r）——条目数没变，不该报"
                         % (len(its), note13))
    for h in ("http://weixin.sogou.com/link?url=a",
              "https://weixin.sogou.com:8443/link?url=a",
              "https://weixin.sogou.com.evil.example/x",
              "//evil.example.com/x"):
        if S.safe_link(h):
            fails.append("safe_link 放过了 %s" % h)
    if not S.safe_link("/link?url=abc"):
        fails.append("safe_link 把正常的相对 /link 也拦了，整页结果会全成空链接")
    S13 = _load()
    S13.time.sleep = lambda *a: None
    reqs = []

    def stub13(opener, url, referer=None, tries=3):
        reqs.append(url)
        return {"html": bad, "final_url": url}
    S13.fetch = stub13
    got13, _ = S13.search("税务", want=1, pages=1, resolve=True, log=lambda *a: None)
    if any("evil" in u for u in reqs):
        fails.append("-r 拿外域链接发了请求（%s）——等于用本机会话去访问结果页里的陌生主机"
                     % [u for u in reqs if "evil" in u][:1])
    if len(reqs) != 2:
        # 首页 cookie 引导 + 1 页搜索页 = 2 次；链接已被拦下就一次都不许多发
        fails.append("空链接条目仍触发了还原请求（共 %d 次请求，应 2 次）" % len(reqs))
    if bad != real and got13 and got13[0].get("resolve_error") and \
            "weixin.sogou.com" not in got13[0]["resolve_error"]:
        fails.append("被拦条目没带原因：%s" % got13[0].get("resolve_error"))

    # 14) 状态码分家：403/429/503 是服务端明确拒绝，归「被拦截」；其余仍归「传输层异常」
    import urllib.error as _uerr

    class _Resp14(object):
        def __init__(self, body, url):
            self._b = body.encode("utf-8")
            self._u = url
            self.headers = {"Content-Type": "text/html; charset=utf-8"}

        def read(self, n=-1):
            return self._b

        def geturl(self):
            return self._u

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Op14(object):
        """只换 opener，让真实 fetch 跑完整条异常路径（打桩 fetch 证不出状态码有没有带出来）。"""

        def __init__(self, exc=None, body="<html>ok</html>", final=None):
            self.exc, self.body, self.final = exc, body, final
            self.n = 0

        def open(self, req, timeout=None):
            self.n += 1
            if self.exc is not None:
                raise self.exc
            return _Resp14(self.body, self.final or req.get_full_url())

    S14 = _load()
    S14.time.sleep = lambda *a: None

    def _httperr(code):
        return _uerr.HTTPError("https://weixin.sogou.com/weixin?type=2", code,
                               "Server Error", {}, None)

    r = S14.fetch(_Op14(_httperr(429)), "https://weixin.sogou.com/weixin?type=2")
    if r.get("http_status") != 429:
        fails.append("fetch 没把 HTTPError 的状态码带出来：%r——只剩字符串时 429 会被下游当成"
                     "网络抖动继续撞" % r)
    r = S14.fetch(_Op14(_httperr(500)), "https://weixin.sogou.com/weixin?type=2")
    if r.get("http_status") != 500:
        fails.append("非限流状态码也该带出来（分家要靠它，不是靠猜）：%r" % r)
    r = S14.fetch(_Op14(_uerr.URLError("timed out")), "https://weixin.sogou.com/weixin?type=2")
    if "http_status" in r:
        fails.append("网络抖动被安上了 http_status（会被误判成服务端拒绝）：%r" % r)
    op14 = _Op14(_httperr(429))
    S14.fetch(op14, "https://weixin.sogou.com/weixin?type=2")
    if op14.n != S14.RETRIES:
        fails.append("状态码失败的重试次数应受 RETRIES 约束（实发 %d 次，RETRIES=%d）"
                     % (op14.n, S14.RETRIES))

    for code, is_block in ((429, True), (403, True), (503, True), (500, False)):
        S14b = _load()
        S14b.time.sleep = lambda *a: None

        def _f14b(opener, url, referer=None, tries=3, _c=code):
            if "weixin?" in url:
                return {"error": "HTTPError: HTTP Error %d: Server Error" % _c,
                        "final_url": None, "http_status": _c}
            return {"html": "<html>seed</html>", "final_url": url}
        S14b.fetch = _f14b
        got14, notes14 = S14b.search("税务", want=3, pages=1, log=lambda *a: None)
        j = " | ".join(notes14)
        blocked = "被拦截" in j and "服务端按状态码拒绝" in j
        transport = "传输层异常" in j
        if is_block and not (blocked and not transport):
            fails.append("HTTP %d 应归「被拦截」且不得同时报传输层异常（blocked=%s transport=%s）：%s"
                         % (code, blocked, transport, j[:140]))
        if not is_block and not (transport and not blocked):
            fails.append("HTTP %d 被误报成服务端拒绝（transport=%s blocked=%s）：%s"
                         % (code, transport, blocked, j[:140]))
        if got14:
            fails.append("HTTP %d 失败仍交付了 %d 条" % (code, len(got14)))

    # 14b) -r 期间撞 429 必须熔断：限流时继续逐条撞 /link 正是「加深风控」的动作
    S14c = _load()
    S14c.time.sleep = lambda *a: None
    calls14 = []

    def _f14c(opener, url, referer=None, tries=3):
        calls14.append(url)
        if "/link?" in url:
            return {"error": "HTTPError: HTTP Error 429: Server Error",
                    "final_url": None, "http_status": 429}
        return {"html": real, "final_url": url}
    S14c.fetch = _f14c
    got14c, notes14c = S14c.search("税务", want=5, pages=1, resolve=True, log=lambda *a: None)
    link_urls = {u for u in calls14 if "/link?" in u}
    if len(link_urls) != 1:
        fails.append("还原期撞 429 没有熔断（请求了 %d 个不同的 /link，应 1 个）" % len(link_urls))
    if not any("item#" in n and "429" in n for n in notes14c):
        fails.append("还原期 429 未打印熔断 NOTE：%s" % [n[:70] for n in notes14c])
    if not any("服务端按状态码拒绝" in (it.get("resolve_error") or "") for it in got14c):
        fails.append("429 未落进 resolve_error（调用方看不出是被限流还是页面变了）：%s"
                     % [it.get("resolve_error") for it in got14c][:1])

    # 15) 还原结果按主机判定：/link 壳页同样是不可信输入
    S15 = _load()
    WRAP15 = "https://weixin.sogou.com/link?url=abc&type=2&query=x&token=t"
    for label, body, final in (
            ("302 落到子串伪装域", "<html>n</html>", "https://mp.weixin.qq.com.evil.example/s?x=1"),
            ("302 落到完全外域", "<html>n</html>", "https://evil.example/pwn"),
            ("meta refresh 指外域",
             '<meta http-equiv="refresh" content="0;url=https://evil.example/p?a=1&amp;b=2">', WRAP15),
            ("url += 拼出外域",
             "<script>var url='';url += 'https://evil';url += '.example/p';</script>", WRAP15)):
        S15.fetch = lambda opener, url, referer=None, tries=3, _b=body, _f=final: {
            "html": _b, "final_url": _f}
        u15, how15 = S15.resolve_link(None, WRAP15)
        if u15 is not None:
            fails.append("外域还原目标被当成真实链接交付（%s）：%r" % (label, u15))
        if "不是 https://mp.weixin.qq.com" not in (how15 or ""):
            fails.append("外域还原没写明主机判定原因（%s），会被读成「页面改版」：%r" % (label, how15))

    for label, body, final, via in (
            ("302 合法", "<html>n</html>", "https://mp.weixin.qq.com/s?src=11&x=1", "302"),
            ("meta refresh 合法",
             '<meta http-equiv="refresh" content="0;url=https://mp.weixin.qq.com/s?abc=1">',
             WRAP15, "meta-refresh"),
            ("url += 合法", wrapper, WRAP15, "url-concat")):
        S15.fetch = lambda opener, url, referer=None, tries=3, _b=body, _f=final: {
            "html": _b, "final_url": _f}
        u15, how15 = S15.resolve_link(None, WRAP15)
        if not (u15 or "").startswith("https://mp.weixin.qq.com/"):
            fails.append("合法还原被误杀（%s）：%r" % (label, u15))
        if how15 != via:
            fails.append("合法还原形态标注变了（%s）：%r，应 %r" % (label, how15, via))

    for bad_mp in ("http://mp.weixin.qq.com/s?x", "https://mp.weixin.qq.com:8443/s?x",
                   "https://mp.weixin.qq.com.evil.example/s", "https://evil.example/s",
                   "/s?relative=1", ""):
        if S15.safe_mp_link(bad_mp):
            fails.append("safe_mp_link 放过了 %r" % bad_mp)
    if not S15.safe_mp_link("https://mp.weixin.qq.com/s?a=1&signature=x#rd"):
        fails.append("safe_mp_link 把带锚点的合法链接拦了")

    # 15b) 丢弃外域结果后，交付面要保持可用：链接退回搜狗跳转、原因可见、条目数不变
    S15e = _load()
    S15e.time.sleep = lambda *a: None
    S15e.fetch = lambda opener, url, referer=None, tries=3: (
        {"html": "<html>n</html>", "final_url": "https://evil.example/x"} if "/link?" in url
        else {"html": real, "final_url": url})
    got15e, _ = S15e.search("税务", want=2, pages=1, resolve=True, log=lambda *a: None)
    if any(it.get("resolved") for it in got15e):
        fails.append("外域还原结果落进了 resolved：%s" % [it.get("resolved") for it in got15e])
    if len(got15e) != 2 or not all(it["link"].startswith("https://weixin.sogou.com/") for it in got15e):
        fails.append("还原被丢弃后条目数或搜狗链接兜底不对：%s" % got15e[:1])
    if "evil" in S15e.render(got15e, "md", "税务"):
        fails.append("md 交付里出现了外域链接——调用方会照着它交给 read/")
    if "还原失败" not in S15e.render(got15e, "text", "税务"):
        fails.append("text 交付没打印还原失败原因，用户只看到一条没还原的跳转链接")
    ctrl = "<script>var url='';url += 'https://\x1b[31mLEAK\x1b[0m.example/p';</script>"
    S15.fetch = lambda opener, url, referer=None, tries=3: {"html": ctrl, "final_url": WRAP15}
    _u, how15 = S15.resolve_link(None, WRAP15)
    if "\x1b" in (how15 or ""):
        fails.append("页面可控文本里的控制字符原样进了打印原因（可伪造终端输出）：%r" % how15[:60])

    # 15c) 非法 URL 不能弄崩解析：主机位置出现不配对的 `[` 时 urlsplit 抛 ValueError('Invalid IPv6 URL')
    m15 = re.search(r'(<h3[^>]*>\s*<a\b[^>]*?href=")([^"]*)(")', real, re.S)
    broken = real[:m15.start(2)] + "https://weixin.sogou.com[b/x" + real[m15.end(2):]
    its15, note15 = S.parse_results(broken)
    if len(its15) != 10:
        fails.append("一条非法 href 弄丢了条目（%d 条，应 10 条）：%s" % (len(its15), note15))
    bad15 = [it for it in its15 if not it["link"]]
    if len(bad15) != 1 or "URL 非法" not in (bad15[0].get("link_error") or ""):
        fails.append("非法 href 没有被单独标注（拦下 %d 条）：%s"
                     % (len(bad15), bad15 and bad15[0].get("link_error")))
    if S.safe_link("https://weixin.sogou.com[b/x") or S.safe_mp_link("https://[bad"):
        fails.append("safe_link/safe_mp_link 把非法 URL 放过去了（应当抛的话上面已经崩在这里）")
    if S.safe_link("https://weixin.sogou.com/link?url=a[b") != "https://weixin.sogou.com/link?url=a[b":
        fails.append("safe_link 把主机合法、只是 query 里有 `[` 的正常链接也拦了")

    # 16) 响应字节上限：读满 MAX_BODY_BYTES 即停并标注截断（超时管不住「慢但不断」的响应）
    class _Resp16(object):
        """按 n 诚实返回的假响应；step 非空时模拟短读（一次拿不满请求的块数）。"""

        def __init__(self, body, url, step=None):
            self._b, self._u, self._i, self._step = body, url, 0, step
            self.headers = {"Content-Type": "text/html; charset=utf-8"}

        def read(self, n=-1):
            if n is None or n < 0:
                n = len(self._b) - self._i
            if self._step:
                n = min(n, self._step)
            chunk = self._b[self._i:self._i + n]
            self._i += len(chunk)
            return chunk

        def geturl(self):
            return self._u

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Op16(object):
        def __init__(self, body, step=None):
            self.body, self.step = body, step

        def open(self, req, timeout=None):
            return _Resp16(self.body, req.get_full_url(), self.step)

    S16 = _load()
    S16.time.sleep = lambda *a: None
    CAP16 = S16.MAX_BODY_BYTES
    if not isinstance(CAP16, int) or CAP16 < 1024 * 1024:
        fails.append("MAX_BODY_BYTES 应是不小于 1MB 的整数（当前 %r）" % CAP16)
    r = S16.fetch(_Op16(b"<html>" + b"A" * (CAP16 + 4096) + b"</html>"),
                  "https://weixin.sogou.com/weixin?type=2")
    if r.get("truncated") is not True:
        fails.append("超出上限的响应没标截断（truncated=%r）：读到底就是把内存交给对方决定"
                     % r.get("truncated"))
    if len(r["html"]) != CAP16:
        fails.append("截断后长度应正好是上限（实得 %d，上限 %d）" % (len(r["html"]), CAP16))
    small16 = "<html><body>正常页</body></html>"
    r = S16.fetch(_Op16(small16.encode("utf-8")), "https://weixin.sogou.com/weixin?type=2")
    if r.get("truncated") or r["html"] != small16:
        fails.append("正常大小的页面被动了（truncated=%r，长度 %d）"
                     % (r.get("truncated"), len(r["html"])))
    r = S16.fetch(_Op16(b"<html>ok</html>", step=3), "https://weixin.sogou.com/weixin?type=2")
    if r.get("truncated") or r["html"] != "<html>ok</html>":
        fails.append("短读被当成读完（truncated=%r，html=%r）" % (r.get("truncated"), r["html"][:24]))
    r = S16.fetch(_Op16(b"B" * CAP16), "https://weixin.sogou.com/weixin?type=2")
    if r.get("truncated"):
        fails.append("正文正好等于上限时报了截断——后面真的没有字节，这是假警报")

    S16b = _load()
    S16b.time.sleep = lambda *a: None
    S16b.fetch = lambda opener, url, referer=None, tries=3: {
        "html": real, "final_url": url, "truncated": "/link?" not in url}
    got16, notes16 = S16b.search("税务", want=3, pages=1, log=lambda *a: None)
    if not any("截断" in n for n in notes16):
        fails.append("fetch 报了截断，search() 没写进 NOTE：%s" % " | ".join(notes16)[:120])
    if len(got16) != 3:
        fails.append("截断页仍应照常解析交付（实得 %d 条）" % len(got16))

    # 17) NOTE 进 json：只用 -o 落盘的调用方原本看不到拦截与哨兵判定
    S17 = _load()
    it17, _ = S17.parse_results(real)
    d17 = S17.json.loads(S17.render(it17[:2], "json", "税务",
                                    ["page=1 被拦截：antispider", "结构漂移（box=10）"]))
    if d17.get("notes") != ["page=1 被拦截：antispider", "结构漂移（box=10）"]:
        fails.append("json 顶层 notes 键没带上原样 NOTE：%r" % (d17.get("notes"),))
    if d17.get("count") != 2 or len(d17.get("items", [])) != 2:
        fails.append("notes 的加入动摇了 count/items：%r" % {k: len(str(v)) for k, v in d17.items()})
    d17b = S17.json.loads(S17.render(it17[:1], "json", "税务"))
    if d17b.get("notes") != []:
        fails.append("不传 notes 时该是空表而不是缺键：%r" % (d17b.get("notes"),))
    if "notes" in S17.render(it17[:1], "text", "税务", ["不该出现"]):
        fails.append("text 输出里混进了 notes 字样（三种格式的交付面不该互相污染）")

    # 18) 熔断后未发起请求的条目要留下自己的状态
    S18 = _load()
    S18.time.sleep = lambda *a: None
    S18.fetch = lambda opener, url, referer=None, tries=3: (
        {"error": "HTTPError: HTTP Error 429: Server Error", "final_url": None, "http_status": 429}
        if "/link?" in url else {"html": real, "final_url": url})
    got18, notes18 = S18.search("税务", want=5, pages=1, resolve=True, log=lambda *a: None)
    if len(got18) != 5:
        fails.append("熔断不该动条目数（实得 %d，应 5）" % len(got18))
    tried18 = [it for it in got18[:1] if it.get("resolve_error")]
    skipped18 = [it for it in got18[1:] if it.get("resolve_skipped")]
    if len(tried18) != 1:
        fails.append("item#1 没带上失败原因：%r" % got18[0].get("resolve_error"))
    if len(skipped18) != 4:
        fails.append("熔断后 %d 条里没有一条标出「未尝试」（json 里它们和「还原出来正好是空」同形）"
                     % len(got18[1:]))
    if any("resolve_error" in it for it in got18[1:]):
        fails.append("未发起请求的条目被写上了 resolve_error（会把没试过的说成试过的）")
    if "还原未尝试" not in S18.render(got18, "text", "税务"):
        fails.append("text 交付没露出「还原未尝试」这行")
    if "resolve_skipped" not in S18.render(got18, "json", "税务", notes18):
        fails.append("json 交付没有 resolve_skipped 字段")
    if "还原未尝试" not in S18.render(got18, "md", "税务"):
        fails.append("md 交付没有还原未尝试的说明")

    # 19) 拦截类 NOTE 带本机时刻：处置是「隔时再跑」，没起点就没法比对
    S19 = _load()
    S19.time.sleep = lambda *a: None
    TS_RX_NOTE = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
    S19.fetch = lambda opener, url, referer=None, tries=3: {
        "html": '<html>antispider 环境异常</html>', "final_url": "https://weixin.sogou.com/x"}
    _, notes19 = S19.search("税务", want=3, pages=1, log=lambda *a: None)
    blk19 = [n for n in notes19 if "被拦截" in n]
    if not blk19 or not TS_RX_NOTE.search(blk19[0]):
        fails.append("搜索页被拦的 NOTE 没有本机时刻：%s" % (blk19 and blk19[0][:100]))
    else:
        time.strptime(TS_RX_NOTE.search(blk19[0]).group(0), "%Y-%m-%d %H:%M:%S")
    S19b = _load()
    S19b.time.sleep = lambda *a: None
    S19b.fetch = lambda opener, url, referer=None, tries=3: (
        {"error": "HTTPError: HTTP Error 503: Slow Down", "final_url": None, "http_status": 503}
        if "/link?" in url else {"html": real, "final_url": url})
    _, notes19b = S19b.search("税务", want=3, pages=1, resolve=True, log=lambda *a: None)
    cut19 = [n for n in notes19b if "已停止后续还原" in n]
    if not cut19 or not TS_RX_NOTE.search(cut19[0]):
        fails.append("还原熔断 NOTE 没有本机时刻：%s" % (cut19 and cut19[0][:100]))

    # 20) 按公众号后置筛选：type=1 实测空容器，账号名只能从 type=2 的字段里筛
    S20 = _load()
    pool, _ = S20.parse_results(real)
    hit, dropped = S20.filter_account(pool, "挥墨叙流年")
    if len(hit) != 1 or dropped != len(pool) - 1 or hit[0]["account"] != "挥墨叙流年":
        fails.append("filter_account 精确命中数不对（命中 %d、筛掉 %d）" % (len(hit), dropped))
    hit_up, _ = S20.filter_account(pool, "3QPD")
    if len(hit_up) != len(S20.filter_account(pool, "3qpd")[0]):
        fails.append("公众号名筛选没做到大小写不敏感")
    hit_none, dropped_none = S20.filter_account(pool, "根本没有这个号")
    if hit_none or dropped_none != len(pool):
        fails.append("不存在的账号名筛出了条目（命中 %d、筛掉 %d）" % (len(hit_none), dropped_none))
    if S20.filter_account(pool, "")[0] != pool:
        fails.append("空账号名应当原样返回而不是筛空")

    S20b = _load()
    S20b.time.sleep = lambda *a: None
    pages_fetched = []

    def _f20b(opener, url, referer=None, tries=3):
        if "weixin?" in url:
            pages_fetched.append(url)
        return {"html": real, "final_url": url}
    S20b.fetch = _f20b
    got20, notes20 = S20b.search("税务", want=2, pages=5, account="挥墨叙流年",
                                 log=lambda *a: None)
    # 一页 10 条里只有 1 条属于该号：停止条件若还按原始条数判，翻 1 页就停、筛完只剩 1 条
    if len(pages_fetched) < 2:
        fails.append("带 --account 时翻页停止条件没跟着筛后的条数走（只翻了 %d 页）"
                     % len(pages_fetched))
    if len(got20) != 2 or any("挥墨叙流年" not in it["account"] for it in got20):
        fails.append("--account 交付条数或归属不对：%s" % [it["account"] for it in got20])
    acct_note = [n for n in notes20 if "按公众号筛选" in n]
    if not acct_note or "本次读到过的公众号" not in acct_note[0]:
        fails.append("--account 没打印筛条计数与读到的账号名：%s" % (acct_note and acct_note[0][:100]))

    S20c = _load()
    S20c.time.sleep = lambda *a: None
    S20c.fetch = lambda opener, url, referer=None, tries=3: {"html": real, "final_url": url}
    got20c, notes20c = S20c.search("税务", want=3, pages=1, account="根本没有这个号",
                                   log=lambda *a: None)
    if got20c:
        fails.append("不存在的账号名仍有交付（%d 条）" % len(got20c))
    if not any("命中 0 条" in n for n in notes20c):
        fails.append("筛到 0 条时 NOTE 没写明命中 0：%s" % [n[:60] for n in notes20c])

    # 21) --dump：结构哨兵报漂移时，样本必须来自出问题的那一次请求
    import tempfile
    tmp21 = tempfile.mkdtemp(prefix="wx_dump_")
    S21 = _load()
    S21.time.sleep = lambda *a: None
    S21.fetch = lambda opener, url, referer=None, tries=3: {"html": real, "final_url": url}
    got21, notes21 = S21.search("税务", want=3, pages=1, dump_dir=tmp21, log=lambda *a: None)
    files21 = [f for f in os.listdir(tmp21) if f.startswith("page1_")]
    if len(files21) != 1:
        fails.append("--dump 没把结果页写下来（目录里是 %s）" % os.listdir(tmp21))
    else:
        saved = open(os.path.join(tmp21, files21[0]), encoding="utf-8").read()
        if saved != real:
            fails.append("--dump 写下的页面与本次抓到的不一致（%d 字符 vs %d 字符）"
                         % (len(saved), len(real)))
    if not any("结果页已存" in n for n in notes21):
        fails.append("--dump 没在 NOTE 里报出落盘路径：%s" % [n[:60] for n in notes21])

    S21b = _load()
    S21b.time.sleep = lambda *a: None
    S21b.fetch = lambda opener, url, referer=None, tries=3: {
        "html": '<html>antispider 环境异常</html>', "final_url": "https://weixin.sogou.com/x"}
    _, notes21b = S21b.search("税务", want=3, pages=1, dump_dir=tmp21, log=lambda *a: None)
    blocked21 = [f for f in os.listdir(tmp21) if f.startswith("blocked_page")]
    if not blocked21:
        fails.append("被拦页没有单独命名落盘（改版/风控现场最容易丢）")

    bad_dir = os.path.join(tmp21, files21[0] if files21 else "x", "sub")
    p, err = S21.dump_page(bad_dir, 1, "<html>x</html>")
    if p is not None or not err:
        fails.append("dump_page 写失败时没把错误交回调用方（%r, %r）" % (p, err))
    import shutil
    shutil.rmtree(tmp21, ignore_errors=True)

    # 22) CLI 出口：--account、--format json 的 notes、空 --account
    import json as _json22
    import subprocess
    SCRIPT22 = os.path.join(HERE, os.pardir, "search", "scripts", "search_wechat.py")
    FX22 = os.path.join(FIX, "sogou_type2_sample.html")

    def _cli22(*extra):
        p = subprocess.run([sys.executable, "-X", "utf8", SCRIPT22, "--fixture", FX22] + list(extra),
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode, (p.stdout or ""), (p.stderr or "")

    rc, so, se = _cli22("-n", "10", "--account", "挥墨叙流年")
    if rc != 0 or "挥墨叙流年" not in so or "[2]" in so:
        fails.append("CLI --account 交付不对（rc=%d）：%s" % (rc, so[:160]))
    if "按公众号筛选" not in se:
        fails.append("CLI --account 没把筛条计数打到 NOTE：%s" % se[:120])
    rc, so, se = _cli22("--account", "根本没有这个号")
    if rc != 1 or "处置建议" not in se or "公众号筛选" not in se:
        fails.append("CLI 筛到 0 条没有退 1 并给处置建议（rc=%d）：%s" % (rc, se[:160]))
    rc, so, se = _cli22("--account", "   ")
    if rc != 2:
        fails.append("--account 传空白应退 2，实得 %d：%s" % (rc, se[:80]))
    rc, so, se = _cli22("--format", "json", "-n", "1")
    if rc != 0:
        fails.append("--format json 路径退 %d" % rc)
    else:
        d22 = _json22.loads(so)
        if "notes" not in d22 or not isinstance(d22["notes"], list):
            fails.append("CLI 的 json 里没有 notes 数组：%s" % list(d22.keys()))
        if d22.get("count") != len(d22.get("items", [])):
            fails.append("json 的 count 与 items 不一致")

    print("search_wechat 解析/还原测试：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


def requote(s):
    import urllib.parse
    return urllib.parse.quote(s)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
