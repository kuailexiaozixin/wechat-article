# -*- coding: utf-8 -*-
"""搜狗微信公众号文章搜索（type=2 关键词搜文章）——纯标准库实现。

用法:
    python search_wechat.py <关键词> [-n 10] [--pages 1] [-r] [--format text|json|md]
                            [-o out.txt] [--fixture saved.html] [--sleep 1.5]

行为要点（本机实测结论，维护依据见 search/SKILL.md「搜狗参数与反爬实测」）:
  - 只走 type=2 关键词搜文章；type=1（按公众号名）当前返回空结果容器，不进脚本路径。
  - 分页上限 10（page=11 起返回空列表）；翻页采用「命中即停」：凑够 -n 或某页 0 条即止。
  - 参数口径与反爬判定见 search/SKILL.md 第二、四节。
  - 不传 tsn/ft/et 时间筛选参数：实测请求被 302 回首页，等于自己把自己拦在结果页外。
  - 结果页 UTF-8；/link 跳转 wrapper GBK——按响应头 charset 逐层回退解码。
  - 拦截信号两类：正文含 antispider/验证码/环境异常标记；最终 URL 被 302 回首页。
    任一命中立即停止请求并打印处置建议（单 URL 重试不超过 3 次，不循环撞墙）。
  - -r 还原真实 mp.weixin 链接，依次处理三种形态：302 Location、
    <meta http-equiv="refresh" content="0;url=…">、`url += '…'` 片段拼接 + location.replace。
    还原出的 mp.weixin.qq.com/s?src=11&timestamp=…&signature=… 带签名时效，
    隔时再用需重新还原；正文提取交给 read/ 子技能。
  - 实测：连续请求 /link 会被 302 到 weixin.sogou.com/antispider/。脚本遇此停止后续
    还原并打印 NOTE——搜索结果本身可用，不要靠重试硬闯。

搜狗是外部服务，随时可能改版或加验证码。脚本只负责把当前可用的取回来，
失败时按打印的处置建议改路径，不要反复重试同一请求。
"""
import argparse
import html as html_mod
import http.cookiejar
import json
import os
import random
import re
import sys
import time
import urllib.parse
import urllib.request

HOME = "https://weixin.sogou.com/"
SEARCH_TPL = HOME + "weixin?type=2&query=%s&page=%d"
MAX_PAGE = 10          # page=11 起返回空列表（实测）
RETRIES = 3            # 单 URL 重试上限
BLOCK_MARKERS = ("antispider", "wappoc_appmsgcaptcha", "环境异常", "验证码拦截")

# UA 池：请求间轮换，避免单 UA 高频特征
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
]

# ---- 解析用正则（对齐结果页真实结构：li#sogou_vr_*_box_N > h3>a / p.txt-info / span.all-time-y2）----
LIST_RX = re.compile(r'<ul class="news-list"[^>]*>(.*?)</ul>', re.S)
BLOCK_RX = re.compile(r"<li\b[^>]*id=\"sogou_vr_[\w]+_box_\d+\"")
TITLE_RX = re.compile(r"<h3[^>]*>\s*<a\b([^>]*)>(.*?)</a>", re.S)
HREF_RX = re.compile(r'href="([^"]+)"')
SUMMARY_RX = re.compile(r'<p class="txt-info"[^>]*>(.*?)</p>', re.S)
ACCOUNT_RX = re.compile(r'<span class="all-time-y2"[^>]*>(.*?)</span>', re.S)
TS_RX = re.compile(r"timeConvert\('(\d+)'\)")
TAG_RX = re.compile(r"<[^>]+>")
COMMENT_RX = re.compile(r"<!--.*?-->", re.S)
META_REFRESH_RX = re.compile(
    r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]+content=[\"']?\s*0\s*;\s*url=([^\"'\s>]+)",
    re.I)
FRAG_RX = re.compile(r"url\s*\+=\s*'([^']*)'")


def strip_tags(s):
    return html_mod.unescape(TAG_RX.sub("", COMMENT_RX.sub("", s or ""))).strip()


def build_opener():
    cj = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))


def _decode(raw, content_type):
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    order = ([m.group(1)] if m else []) + ["utf-8", "gbk"]
    for enc in order:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def fetch(opener, url, referer=None, tries=RETRIES):
    """返回 {"html":…, "final_url":…} 或 {"error":…, "final_url":…}。"""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": random.choice(UA_POOL),
            "Referer": referer or HOME,
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        try:
            with opener.open(req, timeout=25) as r:
                return {"html": _decode(r.read(), r.headers.get("Content-Type", "")),
                        "final_url": r.geturl()}
        except Exception as e:  # URLError/HTTPError/timeout 统一退避重试
            last = e
            time.sleep(1.5 * (attempt + 1))
    return {"error": "%s: %s" % (type(last).__name__, last), "final_url": None}


def block_reason(resp):
    """拦截信号：返回原因字符串，未拦截返回 None。"""
    if "error" in resp:
        return None
    body = resp["html"]
    hits = [k for k in BLOCK_MARKERS if k.lower() in body.lower()]
    if hits:
        return "命中反爬标记（%s）" % "、".join(hits)
    final = (resp["final_url"] or "").split("?")[0].rstrip("/")
    if final == HOME.rstrip("/"):
        return "请求被 302 回首页（结果页未渲染，通常是频率或参数触发）"
    return None


def parse_results(page_html):
    """返回 (items, note)。items 为空时用 note 说明是「无结果」还是「结构变更」。"""
    m = LIST_RX.search(page_html)
    scope = m.group(1) if m else page_html
    parts = BLOCK_RX.split(scope)
    items = []
    for blk in parts[1:] if len(parts) > 1 else []:
        tm = TITLE_RX.search(blk)
        if not tm:
            continue
        link = HREF_RX.search(tm.group(1))
        ts = TS_RX.search(blk)
        acct = ACCOUNT_RX.search(blk)
        summ = SUMMARY_RX.search(blk)
        ts_i = int(ts.group(1)) if ts else None
        items.append({
            "title": strip_tags(tm.group(2)),
            "link": urllib.parse.urljoin(HOME, html_mod.unescape(link.group(1))) if link else "",
            "account": strip_tags(acct.group(1)) if acct else "",
            "published": (time.strftime("%Y-%m-%d", time.localtime(ts_i)) if ts_i else ""),
            "timestamp": ts_i,
            "summary": strip_tags(summ.group(1)) if summ else "",
        })
    if items:
        return items, ""
    if "news-list" in page_html or "news-box" in page_html:
        return [], "本页 0 条：该词无更多结果或已到收录末页"
    return [], "未找到 news-list 结果容器：页面结构已变或被拦截"


def resolve_link(opener, link, referer=None):
    """把搜狗 /link wrapper 还原成真实 mp.weixin 链接，覆盖三种形态。"""
    resp = fetch(opener, link, referer=referer or HOME)
    if "error" in resp:
        return None, resp["error"]
    final = resp["final_url"] or ""
    if "/antispider/" in final:
        # 实测：连续请求 /link 会被 302 到 weixin.sogou.com/antispider/，
        # 再撞只会加深风控——调用方据此立即停止后续还原。
        return None, "antispider"
    if "mp.weixin.qq.com" in final and "/link?url=" not in final:
        return final, "302"                      # 形态一：直接 302 落到真实链接
    body = resp["html"]
    reason = block_reason(resp)
    if reason:
        return None, reason
    mr = META_REFRESH_RX.search(body)            # 形态二：meta refresh
    if mr:
        return html_mod.unescape(mr.group(1)), "meta-refresh"
    frags = FRAG_RX.findall(body)                # 形态三：url += '…' 片段拼接
    if frags:
        url = "".join(frags)
        if url.startswith("http"):
            return url, "url-concat"
    return None, "wrapper 页未包含可识别的真实链接（形态变更）"


def search(keyword, want=10, pages=1, resolve=False, sleep=1.5, log=print):
    opener = build_opener()
    bootstrap = fetch(opener, HOME)               # cookie 引导：拿 ABTEST/SNUID/SUID 种子
    if "error" in bootstrap:
        log("WARN 首页 cookie 引导失败（%s），继续直接请求搜索页" % bootstrap["error"])
    quoted = urllib.parse.quote(keyword)
    items, notes, search_url = [], [], None
    for page in range(1, max(1, pages) + 1):
        if len(items) >= want:
            break
        if page > MAX_PAGE:
            notes.append("搜狗分页上限 %d 页，page=%d 起不再请求" % (MAX_PAGE, page))
            break
        search_url = SEARCH_TPL % (quoted, page)
        resp = fetch(opener, search_url, referer=HOME + "weixin?type=2&query=" + quoted)
        reason = block_reason(resp)
        if reason:
            notes.append("page=%d 被拦截：%s" % (page, reason))
            break
        got, note = parse_results(resp["html"])
        if not got:
            notes.append("page=%d %s" % (page, note))
            break
        items.extend(got)
        if len(items) < want and page < MAX_PAGE:
            time.sleep(sleep)

    items = items[:want]          # 先截断：跳转还原只做真正交付的条数。
    # 一页固定返回 10 条，若按整页还原，-n 1 也会打光 10 个 /link 请求并撞 antispider。
    if resolve and items:
        for idx, it in enumerate(items, 1):
            real, how = resolve_link(opener, it["link"], referer=search_url)
            it["resolved"] = real or ""
            it["resolve_via"] = how if real else ""
            if not real:
                it["resolve_error"] = how
                if how == "antispider" or "反爬" in how or "302 回首页" in how:
                    notes.append("跳转还原在 item#%d 被拦截（%s），已停止后续还原"
                                 "——搜索结果本身可用，真实链接请隔时再还原或"
                                 "直接向用户确认链接" % (idx, how))
                    break
            if idx < len(items):
                time.sleep(sleep)                 # /link 连续请求会触发 antispider
    return items, notes


def render(items, fmt="text", keyword=""):
    if fmt == "json":
        return json.dumps({"keyword": keyword, "count": len(items), "items": items},
                          ensure_ascii=False, indent=2)
    lines = []
    if fmt == "md":
        lines.append("# 搜狗微信搜索结果：%s（%d 条）\n" % (keyword, len(items)))
        for i, it in enumerate(items, 1):
            lines.append("%d. [%s](%s) — %s · %s" % (
                i, it["title"], it.get("resolved") or it["link"],
                it["account"] or "公众号未知", it["published"] or "日期未知"))
            if it["summary"]:
                lines.append("   > %s" % it["summary"])
            lines.append("")
        return "\n".join(lines)
    for i, it in enumerate(items, 1):
        lines.append("[%d] %s" % (i, it["title"]))
        lines.append("    公众号: %s | 发布时间: %s" % (
            it["account"] or "-", it["published"] or "-"))
        lines.append("    链接: %s" % (it.get("resolved") or it["link"]))
        if it.get("resolve_via"):
            lines.append("    还原方式: %s" % it["resolve_via"])
        if it.get("resolve_error"):
            lines.append("    还原失败: %s" % it["resolve_error"])
        if it["summary"]:
            lines.append("    摘要: %s" % it["summary"][:120])
    if not items:
        lines.append("(无结果)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("keyword", nargs="?", help="搜索关键词")
    ap.add_argument("-n", type=int, default=10, help="返回条数（默认 10）")
    ap.add_argument("--pages", type=int, default=1, help="最多翻几页（每页 10 条，上限 10 页）")
    ap.add_argument("-r", "--resolve", action="store_true",
                    help="把搜狗跳转链接还原为真实 mp.weixin 链接（每条多一次请求）")
    ap.add_argument("--format", choices=("text", "json", "md"), default="text")
    ap.add_argument("-o", "--out", help="结果写入文件（UTF-8）")
    ap.add_argument("--fixture", help="解析本地已保存的结果页（离线，不联网）")
    ap.add_argument("--sleep", type=float, default=1.5, help="翻页间隔秒数")
    args = ap.parse_args()

    if args.fixture:
        if not os.path.exists(args.fixture):
            print("ERR fixture 文件不存在: %s" % args.fixture, file=sys.stderr)
            sys.exit(1)
        with open(args.fixture, encoding="utf-8", errors="replace") as f:
            items, note = parse_results(f.read())
        items = items[:args.n]
        print(render(items, args.format, args.keyword or os.path.basename(args.fixture)))
        if note:
            print("NOTE", note, file=sys.stderr)
        sys.exit(0 if items else 1)

    if not args.keyword:
        print("ERR 需要关键词（或 --fixture 离线解析）", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    items, notes = search(args.keyword, args.n, args.pages, args.resolve, args.sleep)
    out = render(items, args.format, args.keyword)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("已写入 %s（%d 条）" % (args.out, len(items)))
    else:
        print(out)
    for n in notes:
        print("NOTE", n, file=sys.stderr)
    if not items:
        print("处置建议：换关键词或减少 pages；若 NOTE 显示被拦截，"
              "停止重试，改用已知链接走 read/，或向用户确认来源。", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
