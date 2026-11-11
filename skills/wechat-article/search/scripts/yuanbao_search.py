# -*- coding: utf-8 -*-
"""元宝搜索（so.qq.com）公众号文章搜索 —— 纯标准库实现。

用法:
    python yuanbao_search.py <关键词> [-n 10] [--account 公众号名]
                            [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                            [--format text|json|md] [-o out.txt]
                            [--fixture saved.html] [--dump DIR] [--sleep 1.5]
                            [--pages N]   # 兼容搜狗 CLI：元宝无翻页，给 N 也只抓一页

与搜狗通道（search_wechat.py）的本质差异（详见 Search/SKILL.md「元宝通道」节）:
  - 入口：https://so.qq.com/isearch?tab=weixin_article&query=<关键词>
    （通用综合搜索不带 tab；tab=weixin_article 才是公众号文章频道；
     其它可用频道：weixin_video 视频号 / xueshu 学术 / media 主流媒体 / gov 政府）
  - 返回服务端渲染的整页 HTML（非 JS 空壳），标准库 urllib 直接可抓，无需浏览器。
  - 结果里给的就是**永久直链** http(s)://mp.weixin.qq.com/s?__biz=...&mid=...&idx=...&sn=...&chksm=...#rd，
    交给 Read/ 直接可读，**不需要像搜狗那样 -r 还原成临时票据**（搜狗的票据会过期）。
  - 每条结果的"时间"是相对时间（如「1天前」「3小时前」），不是搜狗那种 Unix 时间戳；
    --after/--before 按相对时间折算到抓取时刻，粒度较粗。
  - 每次请求只返回约 10 条，page=N 被服务端忽略（元宝为瀑布流加载、无翻页）；
    --pages 大于 1 无意义，脚本只抓一页。
  - 不做跳转还原（-r 在此通道无意义，链接已是真实地址）。

反爬/限流：目前实测无需登录、无验证码；但作为外部站点仍可能限流。
命中非常规页面（空结果 / 结构变更 / 疑似拦截）时，按 NOTE 打印处置建议并停手，不重试撞墙。
"""
import argparse
import html as html_mod
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HOME = "https://so.qq.com/"
SEARCH_TPL = HOME + "isearch?tab=weixin_article&query=%s"
MP_HOSTS = ("mp.weixin.qq.com",)        # 只接受微信文章主机（http/https 均可）
MAX_BODY_BYTES = 4 * 1024 * 1024       # 响应读满即停（正常结果页约 150KB）
TITLE_LIMIT = 10                        # 单页结果上限（page=N 被忽略，超出无意义）

UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ---- 解析用正则（对齐结果页真实结构：每条结果含 linkid:title / linkid:source 两个 <a>）----
# 注意：Next.js 飞行数据里会重复出现容器类名，故不按容器切分，直接按标题锚点配对。
TITLE_BLOCK = re.compile(r'<a\s+([^>]*?linkid&quot;:&quot;title&quot;[^>]*?)>(.*?)</a>', re.S)
SOURCE_BLOCK = re.compile(r'<a\s+([^>]*?linkid&quot;:&quot;source&quot;[^>]*?)>(.*?)</a>', re.S)
HREF_RX = re.compile(r'href="([^"]+)"')
TAG_RX = re.compile(r"<[^>]+>")
# 相对时间所在的 span（结构：<span class="flex-shrink-0">1天前</span>）
SPAN_RX = re.compile(r'<span[^>]*>([^<]+)</span>')
# 摘要（best-effort）：带 sa-text 类的文本块
SUMMARY_RX = re.compile(r'class="[^"]*sa-text[^"]*"[^>]*>(.*?)</div>', re.S)
# 相对/绝对时间字样
DATE_RX = re.compile(
    r"(刚刚|昨天|前天|\d+(?:\.\d+)?\s*(?:分钟|小时|天|周|个月|月|年)前|"
    r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)")
# 疑似拦截标记
BLOCK_MARKERS = ("antispider", "环境异常", "验证码", "请完成验证", "系统检测到")


def strip_tags(s):
    return html_mod.unescape(TAG_RX.sub("", s or "")).strip()


def _urlsplit_safe(u):
    try:
        return urllib.parse.urlsplit(u)
    except ValueError:
        return None


def safe_mp_link(href):
    """只接受 mp.weixin.qq.com（http/https 均可），其余置空并标注。"""
    if not href:
        return ""
    parts = _urlsplit_safe(href.strip())
    if (parts is None or parts.scheme not in ("http", "https")
            or parts.hostname not in MP_HOSTS or parts.port is not None):
        return ""
    return href.strip()


def build_opener():
    import http.cookiejar
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


def _read_capped(r, cap=MAX_BODY_BYTES):
    chunks, total = [], 0
    while total < cap:
        chunk = r.read(min(65536, cap - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    truncated = bool(r.read(1)) if total >= cap else False
    return b"".join(chunks), truncated


def fetch(opener, url, referer=None, tries=2):
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": UA_POOL[attempt % len(UA_POOL)],
            "Referer": referer or HOME,
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        try:
            with opener.open(req, timeout=25) as r:
                body, truncated = _read_capped(r)
                return {"html": _decode(body, r.headers.get("Content-Type", "")),
                        "final_url": r.geturl(), "truncated": truncated}
        except Exception as e:  # URLError/HTTPError/timeout
            last = e
            time.sleep(1.5 * (attempt + 1))
    out = {"error": "%s: %s" % (type(last).__name__, last), "final_url": None}
    if isinstance(last, urllib.error.HTTPError):
        out["http_status"] = last.code
    return out


def block_reason(resp):
    if "error" in resp:
        return None  # 传输层异常归另一类处置
    body = resp["html"]
    hits = [k for k in BLOCK_MARKERS if k.lower() in body.lower()]
    if hits:
        return "疑似命中拦截标记（%s）" % "、".join(hits)
    return None


def parse_date_text(seg):
    """从卡片片段里挑出时间文字（相对或绝对）。"""
    for txt in SPAN_RX.findall(seg):
        t = txt.strip()
        if DATE_RX.search(t):
            return t
    return ""


def extract_account(inner):
    """从账号链接内部取账号名：第一个「既非网址、也非日期」的 span 文本。"""
    for txt in SPAN_RX.findall(inner or ""):
        t = txt.strip()
        if t and not t.startswith("http") and not DATE_RX.search(t):
            return t
    return ""


def to_epoch(date_text, now=None):
    """相对/绝对时间 → Unix 秒（相对时间按 now 折算，粒度粗）。返回 None 表示无法判定。"""
    if not date_text:
        return None
    now = now or time.time()
    s = date_text.strip()
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(分钟|小时|天|周|个月|月|年)前$", s)
    if m:
        n = float(m.group(1))
        unit = m.group(2)
        mult = {"分钟": 60, "小时": 3600, "天": 86400, "周": 604800,
                "个月": 2592000, "月": 2592000, "年": 31536000}[unit]
        return int(now - n * mult)
    if s == "刚刚":
        return int(now)
    if s == "昨天":
        return int(now - 86400)
    if s == "前天":
        return int(now - 2 * 86400)
    # 绝对日期 YYYY-MM-DD / YYYY年MM月DD日
    am = re.match(r"^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$", s)
    if am:
        try:
            return int(time.mktime((int(am.group(1)), int(am.group(2)),
                                    int(am.group(3)), 0, 0, 0, 0, 0, -1)))
        except Exception:
            return None
    return None


def parse_results(page_html):
    """返回 (items, note)。无 linkid:title 锚点时说明无结果或结构变更。

    不依赖外层容器类名（Next.js 飞行数据里也会重复出现类名，按容器切分不可靠）：
    直接在全页找所有标题锚点（linkid:title），再以「上一条标题末尾 ~ 下一条标题开头」
    的区间配对本卡的公众号名（标题前）与发布时间（标题后）。
    """
    titles = list(TITLE_BLOCK.finditer(page_html))
    n = len(titles)
    items = []
    for i, tm in enumerate(titles):
        # 本卡公众号名：位于上一条标题末尾与本条标题之间（每张卡 account 在 title 之前）
        acc_region = page_html[(titles[i - 1].end() if i > 0 else 0):tm.start()]
        # 本卡发布时间：位于本条标题末尾与下一条标题之间
        date_region = page_html[tm.end():(titles[i + 1].start() if i + 1 < n else len(page_html))]
        href = HREF_RX.search(tm.group(1))
        raw_link = html_mod.unescape(href.group(1)) if href else ""
        link = safe_mp_link(raw_link)
        title = strip_tags(tm.group(2))
        sm = SOURCE_BLOCK.search(acc_region)
        # 账号链接内包着三个 span：账号名 / 域名(http://mp.weixin.qq.com) / 相对时间。
        # 账号名是第一个「既非网址、也非日期」的 span 文本。
        account = extract_account(sm.group(2)) if sm else ""
        date_text = parse_date_text(date_region)
        smm = SUMMARY_RX.search(date_region)
        summary = strip_tags(smm.group(1)) if smm else ""
        if not title:
            continue
        epoch = to_epoch(date_text)
        item = {
            "title": title,
            "account": account,
            "summary": summary,
            "published": (time.strftime("%Y-%m-%d", time.localtime(epoch))
                          if epoch else ""),
            "timestamp": epoch,
            "link": link,
            "resolved": link,                 # 已是永久直链，无需还原
            "resolve_via": "yuanbao-permanent" if link else "",
            "resolved_at": int(time.time()) if link else None,
        }
        if not link:
            item["link_error"] = ("结果链接不是 mp.weixin.qq.com（%s），已丢弃不交付"
                                  % (raw_link[:80] if raw_link else "空"))
        items.append(item)
    if items:
        n_ok = sum(1 for it in items if it["link"])
        note = ("解析到 %d 条，其中 %d 条含有效 mp.weixin 直链" % (len(items), n_ok))
        if n_ok != len(items):
            note += "（其余链接非微信主机，已置 link_error）"
        return items, note
    if "js-results" in page_html or "result-card" in page_html:
        return [], "本页 0 条：该词在公众号频道无结果"
    return [], "未找到 linkid:title 锚点：页面结构已变或被拦截"


def date_bound(text, end_of_day=False):
    try:
        y, mo, d = (int(x) for x in text.strip().split("-"))
    except Exception:
        raise ValueError("日期格式应为 YYYY-MM-DD，收到 %r" % text)
    epoch = time.mktime((y, mo, d, 0, 0, 0, 0, 0, -1))
    got = time.localtime(epoch)[:3]
    if got != (y, mo, d):
        raise ValueError("日期不合法：%s 被换算成 %d-%02d-%02d" % (text, got[0], got[1], got[2]))
    return epoch + (86399 if end_of_day else 0)


def filter_window(items, lo=None, hi=None):
    keep, no_ts, out = [], 0, 0
    for it in items:
        ts = it.get("timestamp")
        if not ts:
            no_ts += 1
        elif (lo is not None and ts < lo) or (hi is not None and ts > hi):
            out += 1
        else:
            keep.append(it)
    return keep, no_ts, out


def filter_account(items, account):
    needle = (account or "").strip().lower()
    if not needle:
        return list(items), 0
    keep = [it for it in items if needle in (it.get("account") or "").strip().lower()]
    return keep, len(items) - len(keep)


def _stamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def pages_note(pages):
    """--pages 只为与搜狗 CLI 形状对齐而保留；给了非 1 的值要显式说明被忽略，
    免得调用方以为自己翻了页、把覆盖不足当成「元宝没收录」。"""
    if pages is not None and pages != 1:
        return ["--pages %d 已忽略：元宝无翻页（page=N 被服务端忽略），单页最多约 %d 条"
                % (pages, TITLE_LIMIT)]
    return []


def dump_page(dump_dir, html_text, tag="page"):
    path = os.path.join(dump_dir, "%s_%d.html" % (tag, int(time.time())))
    try:
        if not os.path.isdir(dump_dir):
            os.makedirs(dump_dir)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(html_text or "")
        return path, ""
    except OSError as e:
        return None, "%s: %s" % (type(e).__name__, e)


def search(keyword, want=10, resolve=False, sleep=1.5, log=print, window=None,
           account=None, dump_dir=None):
    """resolve 参数在本通道无意义（链接已是永久直链），保留仅为 CLI 兼容。"""
    opener = build_opener()
    quoted = urllib.parse.quote(keyword)
    url = SEARCH_TPL % quoted
    resp = fetch(opener, url, referer=HOME)
    if dump_dir:
        saved, derr = dump_page(dump_dir, resp.get("html", ""), "page")
        if derr:
            log("WARN 结果页未能写盘（%s）" % derr)
        else:
            log("NOTE page 已存 %s" % saved)
    reason = block_reason(resp)
    if reason:
        return [], ["page 疑似被拦截：%s（本机时刻 %s，隔时重跑以这个时刻为起点）"
                    % (reason, _stamp())]
    if "error" in resp:
        return [], ["请求失败：%s（传输层异常，既不是拦截也不是无结果）" % resp["error"]]
    if resp.get("truncated"):
        return [], ["响应读满 %d 字节上限后截断（拿到的可能不是预期页面）" % MAX_BODY_BYTES]
    got, note = parse_results(resp["html"])
    notes = [note] if note else []
    if not got:
        notes.append(got and note or (note or "本页 0 条或无结果"))
        return [], notes
    if window:
        got, no_ts, out = filter_window(got, window[0], window[1])
        notes.append("时间窗口过滤：窗内 %d 条（窗口外 %d、无时间戳 %d）；"
                     "元宝时间为相对时间，折算粒度较粗" % (len(got), out, no_ts))
    if account:
        got, acct_out = filter_account(got, account)
        notes.append("按公众号筛选「%s」：命中 %d 条（筛掉 %d）" % (account, len(got), acct_out))
    got = got[:want]
    return got, notes


def render(items, fmt="text", keyword="", notes=None):
    if fmt == "json":
        return json.dumps({"keyword": keyword, "count": len(items),
                           "notes": list(notes or []), "items": items},
                          ensure_ascii=False, indent=2)
    lines = []
    if fmt == "md":
        lines.append("# 元宝搜索（公众号）结果：%s（%d 条）\n" % (keyword, len(items)))
        for i, it in enumerate(items, 1):
            url = it.get("resolved") or it["link"]
            lines.append("%d. [%s](%s) — %s · %s" % (
                i, it["title"], url or "无可用链接",
                it["account"] or "公众号未知", it["published"] or "日期未知"))
            if it.get("link_error"):
                lines.append("   > 链接： %s" % it["link_error"])
            if it["summary"]:
                lines.append("   > %s" % it["summary"])
            lines.append("")
        return "\n".join(lines)
    for i, it in enumerate(items, 1):
        lines.append("[%d] %s" % (i, it["title"]))
        lines.append("    公众号: %s | 发布时间: %s" % (
            it["account"] or "-", it["published"] or "-"))
        lines.append("    链接: %s" % (it.get("resolved") or it["link"] or "-"))
        if it.get("resolve_via"):
            lines.append("    链接性质: %s（永久直链，可直接交 Read/，无需 -r 还原）" % it["resolve_via"])
        if it.get("link_error"):
            lines.append("    链接问题: %s" % it["link_error"])
        if it["summary"]:
            lines.append("    摘要: %s" % it["summary"][:120])
    if not items:
        lines.append("(无结果)")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("keyword", nargs="?", help="搜索关键词")
    ap.add_argument("-n", type=int, default=TITLE_LIMIT,
                    help="返回条数（默认 10；元宝单页上限约 10 条，给更大也不会多给）")
    ap.add_argument("--pages", type=int, default=None,
                    help="兼容搜狗 CLI 的参数：元宝无翻页，给 N 也只抓一页")
    ap.add_argument("-r", "--resolve", action="store_true",
                    help="兼容参数（本通道链接已是永久直链，无需还原）")
    ap.add_argument("--after", metavar="YYYY-MM-DD", help="只保留该日（含）之后发布")
    ap.add_argument("--before", metavar="YYYY-MM-DD", help="只保留该日（含）之前发布")
    ap.add_argument("--account", metavar="公众号名", help="只保留该公众号发的条目（后置筛）")
    ap.add_argument("--dump", metavar="DIR", help="把抓到的结果页原样写入该目录")
    ap.add_argument("--format", choices=("text", "json", "md"), default="text")
    ap.add_argument("-o", "--out", help="结果写入文件（UTF-8）")
    ap.add_argument("--fixture", help="解析本地已保存的结果页（离线，不联网）")
    ap.add_argument("--sleep", type=float, default=1.5, help="保留参数（本通道单页，无实际翻页）")
    args = ap.parse_args()

    window = None
    if args.after or args.before:
        try:
            lo = date_bound(args.after) if args.after else None
            hi = date_bound(args.before, end_of_day=True) if args.before else None
        except ValueError as e:
            print("ERR %s" % e, file=sys.stderr)
            sys.exit(2)
        if lo is not None and hi is not None and lo > hi:
            print("ERR --after %s 晚于 --before %s，区间为空" % (args.after, args.before),
                  file=sys.stderr)
            sys.exit(2)
        window = (lo, hi)
    account = args.account.strip() if args.account else ""
    if args.account and not account:
        print("ERR --account 给了空名字", file=sys.stderr)
        sys.exit(2)

    if args.fixture:
        if not os.path.exists(args.fixture):
            print("ERR fixture 文件不存在: %s" % args.fixture, file=sys.stderr)
            sys.exit(1)
        with open(args.fixture, encoding="utf-8", errors="replace") as f:
            items, note = parse_results(f.read())
        notes = [note] if note else []
        if window:
            items, no_ts, n_out = filter_window(items, window[0], window[1])
            notes.append("时间窗口过滤：窗内 %d 条（窗口外 %d、无时间戳 %d）"
                         % (len(items), n_out, no_ts))
        if account:
            n_in = len(items)
            items, n_drop = filter_account(items, account)
            notes.append("按公众号筛选「%s」：命中 %d 条（筛掉 %d）" % (account, len(items), n_drop))
        items = items[:args.n]
        notes += pages_note(args.pages)
        print(render(items, args.format, args.keyword or os.path.basename(args.fixture), notes))
        for n in notes:
            print("NOTE", n, file=sys.stderr)
        sys.exit(0 if items else 1)

    if not args.keyword:
        print("ERR 需要关键词（或 --fixture 离线解析）", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    items, notes = search(args.keyword, args.n, args.resolve, args.sleep,
                          window=window, account=account or None, dump_dir=args.dump)
    notes += pages_note(args.pages)
    out = render(items, args.format, args.keyword, notes)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("已写入 %s（%d 条）" % (args.out, len(items)))
    else:
        print(out)
    for n in notes:
        print("NOTE", n, file=sys.stderr)
    sys.exit(0 if items else 1)


if __name__ == "__main__":
    main()
