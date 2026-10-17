# -*- coding: utf-8 -*-
"""搜狗微信公众号文章搜索（type=2 关键词搜文章）——纯标准库实现。

用法:
    python search_wechat.py <关键词> [-n 10] [--pages 1] [-r] [--format text|json|md]
                            [-o out.txt] [--fixture saved.html] [--sleep 1.5]
                            [--after YYYY-MM-DD] [--before YYYY-MM-DD]
                            [--account 公众号名] [--dump DIR]

行为要点（本机实测结论，维护依据见 search/SKILL.md「搜狗参数与反爬实测」）:
  - 只走 type=2 关键词搜文章；type=1（按公众号名）当前返回空结果容器，不进脚本路径。
    要按公众号取文用 --account：在 type=2 已解析出的账号名上做子串筛，是后置过滤，
    少翻页会漏——筛出 0 条时先看 NOTE 列出的「本次读到过的公众号」。
  - 分页上限 10（page=11 起返回空结果容器）；翻页采用「命中即停」：凑够 -n 或某页 0 条即止。
  - 参数口径与反爬判定见 search/SKILL.md 第二、四节。
  - 时间过滤走客户端：不传 tsn/ft/et（实测 302 回首页，等于自己把自己拦在结果页外），
    --after/--before 直接按结果页的 timeConvert 时间戳筛。同页时间戳不是严格倒序
    （两例实测：10 条里 4 处与 3 处倒序，单页跨度从 0.3 天到 3.3 年），所以过滤后靠多翻页保证
    覆盖，不靠「本页变旧就停」；反过来说，早停阈值现在也没有样本可定，只能翻满。
  - cookie 引导只打 weixin.sogou.com 首页（拿 ABTEST/SUID 种子）。实测 v.sogou.com/v?p=40030600
    预热只落下视频频道 cookie（VIDEO_DEBUG/wuid），不带搜索页种子 cookie，不换。
  - 结果页 UTF-8；/link 跳转 wrapper GBK——按响应头 charset 逐层回退解码。
  - 拦截信号三类：正文含 antispider/验证码/环境异常/anti.min.css 标记；最终 URL 被 302 回首页；
    HTTP 状态码 403/429/503（服务端明确拒绝/限流）。任一命中立即停止请求并打印处置建议
    （单 URL 重试不超过 3 次，不循环撞墙）。
    /antispider/ 是「按顺序点汉字」的点选验证，脚本层没有可自动化的填写动作——停手转人工。
  - 失败分三态，不把任何一种伪装成「搜索没结果」：被拦（NOTE 写「被拦截」，含 403/429/503）、
    传输层异常（NOTE 写「传输层异常」，指超时/DNS/连接重置这类服务端没表态的失败，
    立即停止翻页，与 fetch 的 3 次退避重试是两回事）、真的 0 条（NOTE 写「本页 0 条」）。
    三态都退 1，但 NOTE 文案互斥，调用方按文案选处置：限流要冷却，网络抖动才值得马上重试。
    两类拦截 NOTE（搜索页被拦、还原期熔断）都带本机时刻——处置建议是「隔时再跑」，
    没有起点就没有可比对的数；冷却时长本身仍未实测，所以只记时刻不承诺几点恢复。
  - 单次响应读满 4MB 即停（MAX_BODY_BYTES）并打截断 NOTE。实测正常结果页在几十 KB 量级
    （切片约 3 万字符），到上限说明拿到的不是预期页面；25 秒超时管不住「慢但不断」的响应。
  - 结果页是不可信输入：每条 href 过 safe_link 验域，只接受 https://weixin.sogou.com（无端口）。
    `//evil.com/x` 这类协议相对链接会被 urljoin 拼成合法外域，直接交给 -r 或 read/ 就是拿本机
    会话去请求陌生主机；这类条目保留标题与日期、link 置空并落 link_error，且 -r 不为它发请求。
  - 结构哨兵：parse_results 对每条结果页核对 box/h3>a/timeConvert/公众号 四类节点数量，
    数量与条目数背离时打印「结构漂移」NOTE（结果仍交付），改版当天即可从输出看出，不用联网巡检。
  - -r 还原真实 mp.weixin 链接，依次处理三种形态：302 Location、
    <meta http-equiv="refresh" content="0;url=…">、`url += '…'` 片段拼接 + location.replace。
    三种形态的目标都由页面对象说了算，产物一律过 safe_mp_link 按主机判定，只接受
    https://mp.weixin.qq.com（无端口）；`mp.weixin.qq.com.evil.example` 这种子串伪装与外域
    meta refresh 都丢弃不落 resolved，原因写进 resolve_error，条目继续交付搜狗跳转链接。
    还原出的 mp.weixin.qq.com/s?src=11&timestamp=…&signature=… 是当次票据，隔时或换 IP 会失效，
    技能不重试旧票据：JSON 里落 resolved_at（本机还原时刻），据此判断该重新还原还是直接走 read/。
  - 实测：连续请求 /link 会被 302 到 weixin.sogou.com/antispider/。脚本遇拦截类失败
    （antispider、反爬标记、302 回首页、HTTP 403/429/503）立即停止后续还原并打印 NOTE——
    搜索结果本身可用，不要靠重试硬闯。熔断后剩下未发起请求的条目落 resolve_skipped，
    免得在 json 里和「还原出来正好是空」长成一样；text/md 各多一行「还原未尝试」。
  - 交付面自述：--format json 顶层带 notes（拦截、结构漂移、窗口跨度、筛条计数都在里面），
    stderr 上的 NOTE 不再是从判定到处置的唯一通道；只用 -o 落盘 JSON 的调用方也能看到判定。
  - --dump DIR 把每一次抓到的结果页（被拦页文件名带 blocked_page）写到该目录。
    结构哨兵报漂移时，样本要来自出问题的那一次请求：事后重跑可能已经是另一个页面。

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
import urllib.error
import urllib.parse
import urllib.request

HOME = "https://weixin.sogou.com/"
SEARCH_TPL = HOME + "weixin?type=2&query=%s&page=%d"
MAX_PAGE = 10          # page=11 起返回空列表（实测）
RETRIES = 3            # 单 URL 重试上限
BLOCK_MARKERS = ("antispider", "wappoc_appmsgcaptcha", "环境异常", "验证码拦截", "anti.min.css")
LINK_HOST = "weixin.sogou.com"   # 结果页 href 只认这一台主机，其余一律不交付
MP_HOST = "mp.weixin.qq.com"     # /link 还原结果只认这一台主机，其余按形态异常丢弃
# 服务端按状态码明确拒绝/限流。与传输层抖动（超时、DNS）处置相反：
# 前者继续撞只会延长风控，后者可以直接重试，所以必须分家。
BLOCKING_STATUSES = (403, 429, 503)
# 单次响应读取上限。真实结果页量级是几十 KB（实测切片约 3 万字符），
# 到 4MB 说明拿到的根本不是结果页；读到底会把内存和挂钟都交给对方决定。
MAX_BODY_BYTES = 4 * 1024 * 1024

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


def _url_parts(u):
    """安全 urlsplit。页面可控的字符串未必是合法 URL——`[` 不配对时 urllib 直接抛
    ValueError('Invalid IPv6 URL')，一条坏 href 不该把整次搜索弄崩，解析不了就按不可信处理。"""
    try:
        return urllib.parse.urlsplit(u)
    except ValueError:
        return None


def safe_link(href):
    """把结果页 href 绝对化并验域。结果页是不可信输入：`//evil.com/x` 会被 urljoin
    拼成合法的外域链接，交给 -r 或 read/ 就是拿本机会话去请求陌生主机。
    只接受 https + weixin.sogou.com 且不带端口，其余返回空串由调用方标注。"""
    if not href:
        return ""
    try:
        # urljoin 内部也会 urlsplit：非法 href 在这里抛，不是在后面才抛
        joined = urllib.parse.urljoin(HOME, html_mod.unescape(href))
    except ValueError:
        return ""
    parts = _url_parts(joined)
    if (parts is None or parts.scheme != "https" or parts.hostname != LINK_HOST
            or parts.port is not None):
        return ""
    return joined


def safe_mp_link(url):
    """还原结果验主机。/link 壳页同样是不可信输入：三种形态（302 Location、meta refresh、
    `url += '…'` 片段拼接）拿到的目标都由页面说了算，只判「字符串里含不含 mp.weixin.qq.com」
    的话，mp.weixin.qq.com.evil.example 也算含。只接受 https + mp.weixin.qq.com（无端口）。"""
    if not url:
        return ""
    parts = _url_parts(url.strip())
    if (parts is None or parts.scheme != "https" or parts.hostname != MP_HOST
            or parts.port is not None):
        return ""
    return url.strip()


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


def _read_capped(r, cap=MAX_BODY_BYTES):
    """分块读到 cap 即停，返回 (字节, 是否截断)。

    短读（一次拿不满请求的块数）继续读，只有空块才算读完；读满 cap 后再探一字节，
    用来区分「正文正好是 cap」和「后面还有」——后者才是截断。"""
    chunks, total = [], 0
    while total < cap:
        chunk = r.read(min(65536, cap - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    truncated = bool(r.read(1)) if total >= cap else False
    return b"".join(chunks), truncated


def fetch(opener, url, referer=None, tries=RETRIES):
    """返回 {"html":…, "final_url":…, "truncated":…} 或 {"error":…, "final_url":…}；
    失败源于 HTTP 状态码时多带一个 http_status 整数，供调用方分家处置。"""
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={
            "User-Agent": random.choice(UA_POOL),
            "Referer": referer or HOME,
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        try:
            with opener.open(req, timeout=25) as r:
                body, truncated = _read_capped(r)
                return {"html": _decode(body, r.headers.get("Content-Type", "")),
                        "final_url": r.geturl(), "truncated": truncated}
        except Exception as e:  # URLError/HTTPError/timeout 统一退避重试
            last = e
            time.sleep(1.5 * (attempt + 1))
    out = {"error": "%s: %s" % (type(last).__name__, last), "final_url": None}
    if isinstance(last, urllib.error.HTTPError):
        # 状态码要单独带出来：只剩 error 字符串的话，429 会被下游当成网络抖动继续撞。
        out["http_status"] = last.code
    return out


def status_reason(resp):
    """服务端按状态码拒绝（403/429/503）时给出拦截类原因，其余失败返回 None。

    这三个码是搜狗明确告诉我们「现在不给」，和超时/DNS 那种「不知道给不给」是两回事：
    前者继续请求只会延长风控，所以必须落到「被拦截」这条文案上，不能报成传输层异常。"""
    code = resp.get("http_status") if resp else None
    if code in BLOCKING_STATUSES:
        return ("服务端按状态码拒绝（HTTP %d）：这是限流/拒绝，不是网络抖动——"
                "停止后续请求，冷却后再跑；重试同一 URL 只会延长风控" % code)
    return None


# 还原/拦截原因字符串里出现这些键，就按「继续撞只会加深风控」处置（熔断，停后续还原）。
BLOCK_WHY_KEYS = ("antispider", "反爬", "302 回首页", "服务端按状态码拒绝")


def is_block_why(how):
    return any(k in (how or "") for k in BLOCK_WHY_KEYS)


def block_reason(resp):
    """拦截信号：返回原因字符串，未拦截返回 None。"""
    if "error" in resp:
        return status_reason(resp)
    body = resp["html"]
    hits = [k for k in BLOCK_MARKERS if k.lower() in body.lower()]
    if hits:
        why = "命中反爬标记（%s）" % "、".join(hits)
        if "antispider" in hits or "wappoc_appmsgcaptcha" in hits:
            why += "：点选式验证码（按顺序点汉字），脚本层没有可自动化的填写动作——" \
                   "停止重试，人工过一次验证后再跑；重试只会加深风控"
        return why
    final = (resp["final_url"] or "").split("?")[0].rstrip("/")
    if final == HOME.rstrip("/"):
        return "请求被 302 回首页（结果页未渲染，通常是频率或参数触发）"
    return None


def structure_drift(scope_html, items):
    """结构哨兵：真实结果页每条结果同时有 box id、h3>a、timeConvert、公众号 span
    四类节点，数量都等于条目数（实测切片 10/10/10/10/10）。任一背离即改版或降级信号。
    链接数不参与判定——每条结果的 h3 之外还有第二跳 /link，实测一页 20 条链接。"""
    n_box = len(BLOCK_RX.split(scope_html)) - 1
    if n_box <= 0:
        return ""
    n_title = len(TITLE_RX.findall(scope_html))
    n_ts = len(TS_RX.findall(scope_html))
    n_acct = len(ACCOUNT_RX.findall(scope_html))
    counts = "box=%d 标题=%d 时间戳=%d 公众号=%d 已解析=%d" % (
        n_box, n_title, n_ts, n_acct, len(items))
    if len(items) != n_box or n_title != n_box:
        return "结构漂移（%s）：条目缺 h3>a 或 box 判定失效，解析器需要跟进改版" % counts
    if n_ts < n_box or n_acct < n_box:
        return "结构变更提示（%s）：时间戳/公众号字段命中率下降，日期与账号可能缺失" % counts
    return ""


def parse_results(page_html):
    """返回 (items, note)。items 非空时 note 只放结构哨兵结论；为空时说明是「无结果」还是「结构变更」。"""
    m = LIST_RX.search(page_html)
    scope = m.group(1) if m else page_html
    parts = BLOCK_RX.split(scope)
    items = []
    for blk in parts[1:] if len(parts) > 1 else []:
        tm = TITLE_RX.search(blk)
        if not tm:
            continue
        hm = HREF_RX.search(tm.group(1))
        raw_href = hm.group(1) if hm else ""
        link_ok = safe_link(raw_href)
        ts = TS_RX.search(blk)
        acct = ACCOUNT_RX.search(blk)
        summ = SUMMARY_RX.search(blk)
        ts_i = int(ts.group(1)) if ts else None
        item = {
            "title": strip_tags(tm.group(2)),
            "link": link_ok,
            "account": strip_tags(acct.group(1)) if acct else "",
            "published": (time.strftime("%Y-%m-%d", time.localtime(ts_i)) if ts_i else ""),
            "timestamp": ts_i,
            "summary": strip_tags(summ.group(1)) if summ else "",
        }
        if not link_ok:
            item["link_error"] = ("链接主机不是 %s 或 URL 非法，已丢弃不交付（结果页内容不可信）"
                                  % LINK_HOST if raw_href else "结果条目没有可用的 href")
        items.append(item)
    if items:
        return items, structure_drift(scope, items)
    if "news-list" in page_html or "news-box" in page_html:
        return [], "本页 0 条：该词无更多结果或已到收录末页"
    return [], "未找到 news-list 结果容器：页面结构已变或被拦截"


def date_bound(text, end_of_day=False):
    """YYYY-MM-DD → 本机时区 epoch 秒。--before 取当日 23:59:59，保证「含当天」。
    回读年月日核对，挡住 2026-13-45 这类被 mktime 静默进位的输入。"""
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
    """按结果页 timeConvert 的 Unix 时间戳筛发布日期。无时间戳的条目无法证明在窗内，丢弃并计数。"""
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
    """按公众号名筛。type=1（搜公众号）实测返回空容器，所以只能在 type=2 已解析出的
    account 字段上做后置过滤；大小写不敏感的子串匹配，公众号名常带「某某工作室」这类后缀。"""
    needle = (account or "").strip().lower()
    if not needle:
        return list(items), 0
    keep = [it for it in items if needle in (it.get("account") or "").strip().lower()]
    return keep, len(items) - len(keep)


def _stamp():
    """拦截类 NOTE 带本机时刻：处置建议是「冷却后再跑」，没有起点就无从比对。
    冷却时长本身仍未实测，所以只落时刻，不承诺几点恢复。"""
    return time.strftime("%Y-%m-%d %H:%M:%S")


def dump_page(dump_dir, page, html_text, tag="page"):
    """把这一次抓到的结果页原样落盘，返回 (路径, 错误)。

    结构哨兵报漂移或改版当天需要样本，而样本必须来自出问题的那一次请求：事后重跑
    拿到的可能是另一个页面，比对就没有意义。写失败不影响交付，只打一行 WARN。"""
    path = os.path.join(dump_dir, "%s%d_%d.html" % (tag, page, int(time.time())))
    try:
        if not os.path.isdir(dump_dir):
            os.makedirs(dump_dir)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(html_text or "")
        return path, ""
    except OSError as e:
        return None, "%s: %s" % (type(e).__name__, e)


def _brief(u):
    """把页面可控的字符串压成一行短文本，只用于打印原因，不作为链接交付。
    控制字符要一起去掉：这段文字会直接打到终端，页面上塞 \\x1b 序列就能伪造输出。"""
    return " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", u or "").split())[:120]


def resolve_link(opener, link, referer=None):
    """把搜狗 /link wrapper 还原成真实 mp.weixin 链接，覆盖三种形态；
    三种形态的产物一律过 safe_mp_link 验主机，外域结果丢弃不落 resolved。"""
    resp = fetch(opener, link, referer=referer or HOME)
    if "error" in resp:
        return None, status_reason(resp) or resp["error"]
    final = resp["final_url"] or ""
    if "/antispider/" in final:
        # 实测：连续请求 /link 会被 302 到 weixin.sogou.com/antispider/，
        # 再撞只会加深风控——调用方据此立即停止后续还原。
        return None, "antispider"
    real = safe_mp_link(final)
    if real:
        return real, "302"                       # 形态一：直接 302 落到真实链接
    parts = _url_parts(final)
    if final and (parts is None or parts.hostname != LINK_HOST):
        # 跳转确实离开了搜狗、又没落到微信：还原目标被改写，不能退回页内解析去凑一个能用的 URL
        return None, "302 目标主机不是 https://%s（已丢弃不交付）：%s" % (MP_HOST, _brief(final))
    body = resp["html"]                          # 仍停在 wrapper：真实链接在页内形态二/三
    reason = block_reason(resp)
    if reason:
        return None, reason
    mr = META_REFRESH_RX.search(body)            # 形态二：meta refresh
    if mr:
        cand = html_mod.unescape(mr.group(1))
        real = safe_mp_link(cand)
        if real:
            return real, "meta-refresh"
        return None, "还原目标不是 https://%s（已丢弃不交付）：%s" % (MP_HOST, _brief(cand))
    frags = FRAG_RX.findall(body)                # 形态三：url += '…' 片段拼接
    if frags:
        url = "".join(frags)
        real = safe_mp_link(url)
        if real:
            return real, "url-concat"
        return None, "还原目标不是 https://%s（已丢弃不交付）：%s" % (MP_HOST, _brief(url))
    return None, "wrapper 页未包含可识别的真实链接（形态变更）"


def search(keyword, want=10, pages=1, resolve=False, sleep=1.5, log=print, window=None,
           account=None, dump_dir=None):
    """window=(lo,hi) 为 Unix 秒闭区间，None 端点不限制；account 为公众号名后置过滤；
    dump_dir 非空时把每一次抓到的结果页（含被拦页）原样落盘。"""
    opener = build_opener()
    bootstrap = fetch(opener, HOME)               # cookie 引导：拿 ABTEST/SNUID/SUID 种子
    if "error" in bootstrap:
        log("WARN 首页 cookie 引导失败（%s），继续直接请求搜索页" % bootstrap["error"])
    quoted = urllib.parse.quote(keyword)
    lo, hi = window if window else (None, None)
    raw, notes = [], []
    items, search_url = [], None
    for page in range(1, max(1, pages) + 1):
        if len(items) >= want:
            break
        if page > MAX_PAGE:
            notes.append("搜狗分页上限 %d 页，page=%d 起不再请求" % (MAX_PAGE, page))
            break
        search_url = SEARCH_TPL % (quoted, page)
        resp = fetch(opener, search_url, referer=HOME + "weixin?type=2&query=" + quoted)
        reason = block_reason(resp)               # 含 HTTP 403/429/503：那是服务端拒绝，先归这里
        if dump_dir:
            saved, derr = dump_page(dump_dir, page, resp.get("html", ""),
                                    "blocked_page" if reason else "page")
            if derr:
                log("WARN page=%d 结果页未能写盘（%s）" % (page, derr))
            else:
                notes.append("page=%d 结果页已存 %s" % (page, saved))
        if reason:
            notes.append("page=%d 被拦截：%s（本机时刻 %s，隔时重跑以这个时刻为起点）"
                         % (page, reason, _stamp()))
            break
        if "error" in resp:
            # 超时/DNS/连接重置这类「不知道给不给」的失败：不能报成搜狗拦我，也不能当成「这页没结果」；
            # 立即停止翻页并把原因带出，调用方据此决定是重试整条链路还是换来源。
            notes.append("page=%d 请求失败：%s（传输层异常，既不是拦截也不是无结果）"
                         % (page, resp["error"]))
            break
        if resp.get("truncated"):
            notes.append("page=%d 响应读满 %d 字节上限后截断（正常结果页几十 KB 量级，"
                         "这说明拿到的不是预期页面，解析结果不可信）"
                         % (page, MAX_BODY_BYTES))
        got, note = parse_results(resp["html"])
        if not got:
            notes.append("page=%d %s" % (page, note))
            break
        if note:                                    # 结构哨兵：有结果但节点数量背离
            notes.append("page=%d %s" % (page, note))
        raw.extend(got)
        items = raw if not window else filter_window(raw, lo, hi)[0]
        if account:                                 # 停止条件按筛完的条数判，否则翻一页就停、命中 0 条
            items = filter_account(items, account)[0]
        if len(items) < want and page < MAX_PAGE:
            time.sleep(sleep)

    if window:
        items, no_ts, out = filter_window(raw, lo, hi)
        span = sorted({it["published"] for it in raw if it["published"]})
        notes.append("时间窗口过滤：读到 %d 条、窗内 %d 条（窗口外 %d、无时间戳 %d）；"
                     "已翻 %d 页，观测日期跨度 %s。同页日期非严格倒序（两例实测：10 条里 4 处与 "
                     "3 处倒序，单页跨度从 0.3 天到 3.3 年），"
                     "覆盖不到的更早日期要加大 --pages（上限 %d），不能据此断定搜狗没收录"
                     % (len(raw), len(items), out, no_ts, min(max(1, pages), MAX_PAGE),
                        "%s~%s" % (span[0], span[-1]) if span else "无日期", MAX_PAGE))
    else:
        items = raw
    if account:
        items, acct_out = filter_account(items, account)
        seen = sorted({it["account"] for it in raw if it["account"]})
        notes.append("按公众号筛选「%s」：读到 %d 条、命中 %d 条（筛掉 %d）。本次读到过的公众号：%s"
                     % (account, len(raw), len(items), acct_out,
                        "、".join(seen) if seen else "无账号字段"))
    items = items[:want]          # 先截断：跳转还原只做真正交付的条数。
    # 一页固定返回 10 条，若按整页还原，-n 1 也会打光 10 个 /link 请求并撞 antispider。
    if resolve and items:
        for idx, it in enumerate(items, 1):
            if not it["link"]:
                # 链接被验域拦掉或本来就没有 href：不发请求，直接把原因标在条目上
                it["resolved"] = ""
                it["resolve_error"] = it.get("link_error") or "无可还原的搜狗链接"
                continue
            real, how = resolve_link(opener, it["link"], referer=search_url)
            it["resolved"] = real or ""
            it["resolve_via"] = how if real else ""
            if real:
                # 票据是当次的：记下本机还原时刻，隔时/换 IP 后要不要重取由调用方按它判
                it["resolved_at"] = int(time.time())
            if not real:
                it["resolve_error"] = how
                if is_block_why(how):
                    notes.append("跳转还原在 item#%d 被拦截（%s），已停止后续还原"
                                 "——搜索结果本身可用，真实链接请隔时再还原或"
                                 "直接向用户确认链接（本机时刻 %s）" % (idx, how, _stamp()))
                    # 熔断后剩下的条目既不成功也不失败，是「没发起请求」。
                    # 不给这个状态留字段，json 里它们和「还原出来正好是空」长得一样。
                    for rest in items[idx:]:
                        rest["resolve_skipped"] = ("还原已熔断（item#%d 被拦截），本条未发起请求；"
                                                   "隔时后可单独再试" % idx)
                    break
            if idx < len(items):
                time.sleep(sleep)                 # /link 连续请求会触发 antispider
    return items, notes


def render(items, fmt="text", keyword="", notes=None):
    if fmt == "json":
        # notes 也要进 json：拦截判定、结构漂移、窗口跨度原本只打到 stderr，
        # 用 -o 落盘的调用方拿到的是「结果 + 无说明」，三态区分在这条路径上就断了。
        return json.dumps({"keyword": keyword, "count": len(items),
                           "notes": list(notes or []), "items": items},
                          ensure_ascii=False, indent=2)
    lines = []
    if fmt == "md":
        lines.append("# 搜狗微信搜索结果：%s（%d 条）\n" % (keyword, len(items)))
        for i, it in enumerate(items, 1):
            url = it.get("resolved") or it["link"]
            lines.append("%d. [%s](%s) — %s · %s" % (
                i, it["title"], url or "无可用链接",
                it["account"] or "公众号未知", it["published"] or "日期未知"))
            if it.get("link_error"):
                lines.append("   > 链接： %s" % it["link_error"])
            if it.get("resolve_skipped"):
                lines.append("   > 还原未尝试：%s" % it["resolve_skipped"])
            if it["summary"]:
                lines.append("   > %s" % it["summary"])
            lines.append("")
        return "\n".join(lines)
    for i, it in enumerate(items, 1):
        lines.append("[%d] %s" % (i, it["title"]))
        lines.append("    公众号: %s | 发布时间: %s" % (
            it["account"] or "-", it["published"] or "-"))
        lines.append("    链接: %s" % (it.get("resolved") or it["link"] or "-"))
        if it.get("link_error"):
            lines.append("    链接问题: %s" % it["link_error"])
        if it.get("resolve_via"):
            lines.append("    还原方式: %s" % it["resolve_via"])
        if it.get("resolved_at"):
            lines.append("    还原时刻: %s（票据当次有效，隔时或换 IP 需重新还原）"
                         % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(it["resolved_at"])))
        if it.get("resolve_error"):
            lines.append("    还原失败: %s" % it["resolve_error"])
        if it.get("resolve_skipped"):
            lines.append("    还原未尝试: %s" % it["resolve_skipped"])
        if it["summary"]:
            lines.append("    摘要: %s" % it["summary"][:120])
    if not items:
        lines.append("(无结果)")
    return "\n".join(lines)


def advice(window, account):
    """交付 0 条时给的一句处置。--fixture 与在线两条路都要有：离线复现拿去比对的
    也是同一个「为什么是空」，只有一边打印会让复现出来的结论和实跑不一样。"""
    if account:
        return ("处置建议：按公众号筛选「%s」后 0 条。看上面 NOTE 列出的「本次读到过的公众号」"
                "——搜狗的账号名常带工作室/小站这类后缀，先用实际出现的名字重试；"
                "该词下确实没这篇号的文章，就加大 --pages 或换关键词。" % account)
    if window:
        return ("处置建议：窗口内没读到。先看上面「观测日期跨度」——翻页没覆盖到该日期"
                "不等于搜狗没收录，加大 --pages 再试；确认覆盖后再换关键词。")
    return ("处置建议：换关键词或减少 pages；若 NOTE 显示被拦截，"
            "停止重试，改用已知链接走 read/，或向用户确认来源。")


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("keyword", nargs="?", help="搜索关键词")
    ap.add_argument("-n", type=int, default=10, help="返回条数（默认 10）")
    ap.add_argument("--pages", type=int, default=None,
                    help="最多翻几页（每页 10 条，上限 10 页）。不带时间筛选默认 1 页；"
                         "带 --after/--before 时默认翻满 10 页，否则窗口外的日期根本没读到")
    ap.add_argument("-r", "--resolve", action="store_true",
                    help="把搜狗跳转链接还原为真实 mp.weixin 链接（每条多一次请求）")
    ap.add_argument("--after", metavar="YYYY-MM-DD",
                    help="只保留该日（含）之后发布的文章：客户端按结果页时间戳筛，不传搜狗时间参数")
    ap.add_argument("--before", metavar="YYYY-MM-DD",
                    help="只保留该日（含）之前发布的文章，与 --after 同用即为闭区间")
    ap.add_argument("--account", metavar="公众号名",
                    help="只保留该公众号发的条目：在结果页解析出的公众号名上做不区分大小写的"
                         "子串匹配（type=1 搜公众号实测返回空容器，本脚本未封装）")
    ap.add_argument("--dump", metavar="DIR",
                    help="把每一次抓到的结果页（含被拦页）原样写入该目录，供改版比对与夹具更新")
    ap.add_argument("--format", choices=("text", "json", "md"), default="text")
    ap.add_argument("-o", "--out", help="结果写入文件（UTF-8）")
    ap.add_argument("--fixture", help="解析本地已保存的结果页（离线，不联网）")
    ap.add_argument("--sleep", type=float, default=1.5, help="翻页间隔秒数")
    args = ap.parse_args()

    window = None
    lo = hi = None
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
        print("ERR --account 给了空名字，无法按公众号筛选", file=sys.stderr)
        sys.exit(2)
    pages = args.pages if args.pages is not None else (MAX_PAGE if window else 1)
    if window and args.pages is None:
        print("NOTE 未显式给 --pages，时间窗口下默认翻满 %d 页（多 %d 次搜索页请求）；"
              "想少发请求就显式指定" % (MAX_PAGE, MAX_PAGE - 1), file=sys.stderr)

    if args.fixture:
        if not os.path.exists(args.fixture):
            print("ERR fixture 文件不存在: %s" % args.fixture, file=sys.stderr)
            sys.exit(1)
        with open(args.fixture, encoding="utf-8", errors="replace") as f:
            items, note = parse_results(f.read())
        notes = [note] if note else []          # 结构哨兵：离线复现同样会报漂移
        if window:
            items, no_ts, n_out = filter_window(items, lo, hi)
            notes.append("时间窗口过滤：读到 %d 条、窗内 %d 条（窗口外 %d、无时间戳 %d）"
                         % (len(items) + no_ts + n_out, len(items), n_out, no_ts))
        if account:
            n_in = len(items)
            items, n_drop = filter_account(items, account)
            notes.append("按公众号筛选「%s」：读到 %d 条、命中 %d 条（筛掉 %d）"
                         % (account, n_in, len(items), n_drop))
        items = items[:args.n]
        print(render(items, args.format, args.keyword or os.path.basename(args.fixture), notes))
        for n in notes:
            print("NOTE", n, file=sys.stderr)
        if not items:
            print(advice(window, account), file=sys.stderr)
        sys.exit(0 if items else 1)

    if not args.keyword:
        print("ERR 需要关键词（或 --fixture 离线解析）", file=sys.stderr)
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    items, notes = search(args.keyword, args.n, pages, args.resolve, args.sleep,
                          window=window, account=account or None, dump_dir=args.dump)
    out = render(items, args.format, args.keyword, notes)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        print("已写入 %s（%d 条）" % (args.out, len(items)))
    else:
        print(out)
    for n in notes:
        print("NOTE", n, file=sys.stderr)
    if not items:
        print(advice(window, account), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
