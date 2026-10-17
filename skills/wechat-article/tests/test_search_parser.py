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

    print("search_wechat 解析/还原测试：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


def requote(s):
    import urllib.parse
    return urllib.parse.quote(s)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
