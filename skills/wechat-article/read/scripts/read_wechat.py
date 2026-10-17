# -*- coding: utf-8 -*-
"""读取 mp.weixin.qq.com 文章 → Markdown（四层渐进式 + 质量门，脚本化落地）。

用法:
    python read_wechat.py <文章URL> [-o out.md] [--json] [--min-chars 800]
                          [--no-cdp] [--layer 1|2|3|4] [--timeout 25]
    python read_wechat.py <URL> --fixture saved.html   # 离线解析，不联网（回归测试）

四层渐进（逐层降级，以「非空正文」为唯一成功判据）:
    1 Mobile UA 直连        2 Desktop UA + Cookie Session
    3 完整浏览器 Headers    4 CDP 本机 Edge（验证墙场景，连接细节见 read/references/cdp-edge.md）

质量门（判成功的硬条件，缺任一项即判该层失败继续降级）:
    - 正文节点存在（#js_content / .rich_media_content）
    - 未命中验证墙标记（wappoc_appmsgcaptcha、"环境异常"、"完成验证后即可继续访问"）
    - 正文长度 ≥ --min-chars（默认 800）
    短文豁免：长度不足但同时拿到「标题 + 发布时间 + 正文节点」时判通过，
    打 NOTE 说明按短文放行——公众号确有短文的真实存在，一刀切会误杀。

重试纪律（上限由代码里的 LAYER_TRIES / HTTP_MAX_PER_URL 给出，不是口头约定）：
    第 1–3 层每层最多 2 次网络请求（1 次正常 + 1 次连接类异常补发），内容不合格不在同层重试、
    直接换层，三层合计最多 6 次；第 4 层是浏览器导航，不在这 6 次之内。
    四层走完仍失败就输出诊断并停止，不循环撞墙（实测反复请求会加深风控）。

输出：Markdown + YAML frontmatter（source_url / title / author / account /
published / cover / digest / layer / chars）。依赖优先级：
bs4+lxml（正文结构化）→ 标准库 HTMLParser（退化取文本，标注 degraded）；
requests 缺失自动用 urllib；第 4 层需要 websocket-client（缺失则明确报不可用，不静默跳过）。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

MIN_FULLTEXT_CHARS = 800          # 正文长度参考阈值（经验值，可 --min-chars 覆盖）；短文豁免见 __doc__
LAYER_TRIES = 2                   # 单层最多请求次数：1 次正常 + 1 次连接类异常补发
HTTP_MAX_PER_URL = 3 * LAYER_TRIES   # 第 1–3 层对同一个 URL 的请求上限；第 4 层走浏览器导航，不计入
CAPTCHA_MARKERS = ("wappoc_appmsgcaptcha", "环境异常", "完成验证后即可继续访问", "验证码拦截")
CONTENT_RX = re.compile(r'id="js_content"', re.I)

MOBILE_UA = ("Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
DESKTOP_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _decode(raw, content_type=""):
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    order = ([m.group(1)] if m else []) + ["utf-8", "gbk"]
    for enc in order:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


def http_get(url, ua, extra=None, referer=None, timeout=25, tries=LAYER_TRIES, cookie_jar=None):
    """单层取页：连接类异常补 1 次，内容问题不在此重试。"""
    headers = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,"
                                         "application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "zh-CN,zh;q=0.9"}
    if referer:
        headers["Referer"] = referer
    headers.update(extra or {})
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)) if cookie_jar is not None \
        else urllib.request.build_opener()
    err = None
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with opener.open(req, timeout=timeout) as r:
                return {"html": _decode(r.read(), r.headers.get("Content-Type", "")),
                        "final_url": r.geturl(), "layer_ua": ua[:24]}
        except Exception as e:  # URLError / HTTPError / timeout
            err = e
            time.sleep(1.5)
    return {"error": "%s: %s" % (type(err).__name__, err)}


def layer1(url):
    return http_get(url, MOBILE_UA)


def layer2(url):
    import http.cookiejar
    jar = http.cookiejar.CookieJar()
    return http_get(url, DESKTOP_UA, cookie_jar=jar)      # Session 语义：cookie 随请求带


def layer3(url):
    return http_get(url, DESKTOP_UA, extra={
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                  "image/webp,*/*;q=0.8",
        "Accept-Encoding": "identity",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1",
        "Referer": "https://mp.weixin.qq.com/",
    })


# ---------------- 第 4 层：CDP（按 read/references/cdp-edge.md 固化的连接序列） ----------------

DEVTOOLS_ENV = "WX_EDGE_DEVTOOLS_PORT_FILE"


def devtools_port_candidates():
    """DevToolsActivePort 的默认位置按平台给出；win32 那条是本机实测，其余两条按
    Edge 的 profile 目录惯例给出且未跨平台实测，取不到时一律用 DEVTOOLS_ENV 指定。"""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        return [os.path.join(local, "Microsoft", "Edge", "User Data", "DevToolsActivePort")]
    if sys.platform == "darwin":
        return [os.path.join(home, "Library", "Application Support",
                             "Microsoft Edge", "DevToolsActivePort")]
    cfg = os.environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return [os.path.join(cfg, "microsoft-edge", "DevToolsActivePort")]


def devtools_port_file():
    override = (os.environ.get(DEVTOOLS_ENV) or "").strip()
    if override:
        if not os.path.exists(override):
            raise RuntimeError("%s 指向的文件不存在: %s" % (DEVTOOLS_ENV, override))
        return override
    tried = devtools_port_candidates()
    for path in tried:
        if os.path.exists(path):
            return path
    raise RuntimeError("DevToolsActivePort 不存在（Edge 未运行或未开远程调试），已试: %s；"
                       "profile 不在默认位置时设 %s 指向该文件"
                       % (" | ".join(tried), DEVTOOLS_ENV))


def devtools_ws_url():
    port_file = devtools_port_file()
    with open(port_file, encoding="utf-8") as f:
        port = f.readline().strip()
        ws_path = f.readline().strip()      # 两行都要；只用端口连不上，UUID 每次重启都变
    if not port or not ws_path:
        raise RuntimeError("DevToolsActivePort 内容不完整（需两行：端口 + WebSocket 路径）")
    return "ws://127.0.0.1:%s%s" % (port, ws_path)


def cdp_get_html(url, timeout=40):
    try:
        import websocket
    except ImportError:
        raise RuntimeError("第 4 层需要 websocket-client（pip install websocket-client）")
    ws = websocket.create_connection(devtools_ws_url(), suppress_origin=True, timeout=timeout)
    try:
        state = {"id": 0}

        def cdp(method, params=None, session=None):
            state["id"] += 1
            mid = state["id"]
            msg = {"id": mid, "method": method, "params": params or {}}
            if session:
                msg["sessionId"] = session
            ws.send(json.dumps(msg))
            deadline = time.time() + timeout
            while time.time() < deadline:      # 关键坑：CDP 夹带事件消息，必须按 id 循环匹配
                got = json.loads(ws.recv())
                if got.get("id") == mid:
                    if got.get("error"):
                        raise RuntimeError("%s → %s" % (method, got["error"]))
                    return got.get("result", {})
            raise RuntimeError("CDP 响应超时（id=%d, method=%s）" % (mid, method))

        tid = cdp("Target.createTarget", {"url": url})["targetId"]
        cdp("Target.activateTarget", {"targetId": tid})
        sid = cdp("Target.attachToTarget", {"targetId": tid, "flatten": True})["sessionId"]

        def evaluate(expr):
            return cdp("Runtime.evaluate",
                       {"expression": expr, "returnByValue": True, "awaitPromise": True},
                       session=sid).get("result", {}).get("value")

        deadline = time.time() + timeout
        ready = ""
        while time.time() < deadline:
            ready = evaluate("document.readyState") or ""
            if ready == "complete" and CONTENT_RX.search(evaluate(
                    "document.documentElement.outerHTML") or ""):
                break
            time.sleep(1.0)
        html = evaluate("document.documentElement.outerHTML") or ""
        cdp("Target.closeTarget", {"targetId": tid})
        return {"html": html, "final_url": url, "ready_state": ready}
    finally:
        ws.close()


# ---------------- 解析与质量门 ----------------

def _meta(html, prop, fallback_rx):
    m = re.search(r'<meta[^>]+property="%s"[^>]+content="([^"]*)"' % re.escape(prop), html)
    if not m:
        m = re.search(r'<meta[^>]+content="([^"]*)"[^>]+property="%s"' % re.escape(prop), html)
    if m:
        return m.group(1).strip()
    m = re.search(fallback_rx, html, re.S) if fallback_rx else None
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""


def parse_meta(html, url):
    return {
        "source_url": url,
        "title": _meta(html, "og:title", r'<h1[^>]*id="activity-name"[^>]*>(.*?)</h1>'),
        "author": _meta(html, "og:article:author", r'<span[^>]*id="js_author_name"[^>]*>(.*?)</span>'),
        "account": _meta(html, "og:account_name", r'<strong[^>]*id="js_name"[^>]*>(.*?)</strong>'),
        "published": _meta(html, "article:published_time",
                           r'<em[^>]*id="js_publish_time"[^>]*>(.*?)</em>'),
        "cover": _meta(html, "og:image", ""),
        "digest": _meta(html, "og:description", ""),
    }


def extract_content(html):
    """返回 (content_html, mode)。bs4(html.parser) 优先；缺 bs4 时退化到标准库正则截取。"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        BeautifulSoup = None
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        node = soup.find(id="js_content") or soup.find(class_="rich_media_content")
        if node is None:
            return "", "bs4-no-node"
        return str(node), "bs4"
    m = re.search(r'id="js_content"', html)
    if not m:
        return "", "no-node"
    tail = html[m.start():]
    cut = re.search(r'<div[^>]+class="(?:rich_media_tool|pay_tip|qr_code_pc)', tail)
    return (tail[:cut.start()] if cut else tail[:200000]), "regex-degraded"


def clean_img_src(src):
    """去 wx_lazy 懒加载标记，保留 wx_fmt/wx_co/tp 等参数（动了会 403 或丢格式）。"""
    if not src:
        return src
    try:
        parts = urllib.parse.urlsplit(src)
        q = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query) if k != "wx_lazy"]
        return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(q)))
    except Exception:
        return src


def html_to_md(content_html):
    try:
        from bs4 import BeautifulSoup, NavigableString, Tag
    except ImportError:
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", content_html, flags=re.S | re.I)
        text = re.sub(r"<[^>]+>", "\n", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"
    soup = BeautifulSoup(content_html, "html.parser")

    def conv(el):
        if isinstance(el, NavigableString):
            return str(el)
        if not isinstance(el, Tag):
            return ""
        tag = el.name
        if tag in ("script", "style", "noscript", "svg", "mp-style-type"):
            return ""
        kids = "".join(conv(c) for c in el.children)
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            t = kids.strip()
            return ("\n%s %s\n" % ("#" * int(tag[1]), t)) if t else ""
        if tag in ("strong", "b"):
            return "**%s**" % kids.strip() if kids.strip() else ""
        if tag in ("em", "i"):
            return "*%s*" % kids.strip() if kids.strip() else ""
        if tag == "a":
            href, t = el.get("href", ""), kids.strip()
            return "[%s](%s)" % (t, href) if href and t else t
        if tag == "img":
            src = clean_img_src(el.get("data-src") or el.get("src") or "")
            return "\n![微信配图](%s)\n" % src if src and not src.startswith("data:") else ""
        if tag == "br":
            return "\n"
        if tag == "hr":
            return "\n---\n"
        if tag == "pre":
            code = el.get_text().strip("\n")
            return "\n```\n%s\n```\n" % code if code else ""
        if tag == "code":
            return "`%s`" % el.get_text() if el.get_text().strip() else ""
        if tag == "li":
            t = kids.strip().replace("\n", " ")
            return "- %s\n" % t if t else ""
        if tag in ("ul", "ol"):
            n = 0
            out = []
            for li in el.find_all("li", recursive=False):
                if tag == "ol":
                    n += 1
                    out.append("%d. %s" % (n, conv(li).strip().lstrip("- ")))
                else:
                    out.append(conv(li).rstrip("\n"))
            return "\n" + "\n".join(x for x in out if x.strip()) + "\n"
        if tag == "blockquote":
            inner = kids.strip()
            return "\n" + "\n".join("> " + ln for ln in inner.splitlines()) + "\n" if inner else ""
        if tag in ("p", "section", "div", "figure", "span", "td", "th", "tr", "table"):
            if tag in ("p", "section", "div", "figure"):
                t = kids.strip()
                return ("\n%s\n" % t) if t else ""
            return kids
        return kids

    md = conv(soup)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def judge(meta, content_html, mode, min_chars):
    """质量门：返回 (ok, reason, chars)。"""
    if not content_html:
        return False, "正文节点缺失（可能命中验证墙或页面结构变更）", 0
    blob = content_html
    hits = [k for k in CAPTCHA_MARKERS if k in blob]
    if hits:
        return False, "命中验证墙标记：" + "、".join(hits), 0
    text = re.sub(r"<[^>]+>", "", blob)
    chars = len(re.sub(r"\s", "", text))
    if chars < min_chars:
        if meta["title"] and meta["published"]:
            return True, "短文豁免：%d 字 < %d，但标题/发布时间/正文节点齐备" % (
                chars, min_chars), chars
        return False, "正文仅 %d 字且缺标题或发布时间，判为未取到全文" % chars, chars
    return True, "", chars


def frontmatter(meta, layer, chars, note):
    lines = ["---"]
    for k in ("source_url", "title", "author", "account", "published", "cover", "digest"):
        v = (meta.get(k) or "").replace('"', "'")
        lines.append('%s: "%s"' % (k, v))
    lines.append('extract_layer: "%s"' % layer)
    lines.append('content_chars: %d' % chars)
    if note:
        lines.append('note: "%s"' % note.replace('"', "'"))
    lines.append('fetched_at: "%s"' % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("---\n")
    return "\n".join(lines)


def read(url, min_chars=MIN_FULLTEXT_CHARS, use_cdp=True, max_layer=4, timeout=25):
    attempts, diag = [], []
    layers = [("1-mobile-ua", layer1), ("2-desktop-session", layer2),
              ("3-full-headers", layer3)]
    for i, (name, fn) in enumerate(layers, 1):
        if i > max_layer:
            break
        resp = fn(url)
        if "error" in resp:
            attempts.append("%s: 网络失败 %s" % (name, resp["error"]))
            diag.append("[%s] 网络失败：%s" % (name, resp["error"]))
            continue
        attempts.append("%s: %d 字符页" % (name, len(resp["html"])))
        meta = parse_meta(resp["html"], url)
        content_html, mode = extract_content(resp["html"])
        ok, reason, chars = judge(meta, content_html, mode, min_chars)
        if ok:
            md = html_to_md(content_html)
            return {"ok": True, "meta": meta, "layer": name, "parse_mode": mode,
                    "chars": chars, "note": reason, "markdown": md,
                    "attempts": attempts, "diag": diag}
        diag.append("[%s] 未过质量门：%s" % (name, reason))
    if use_cdp and max_layer >= 4:
        try:
            resp = cdp_get_html(url, timeout=timeout)
        except Exception as e:
            diag.append("[4-cdp] 不可用：%s" % e)
            return {"ok": False, "layer": "4-cdp", "attempts": attempts, "diag": diag,
                    "markdown": "", "note": "CDP 层失败"}
        attempts.append("4-cdp: %d 字符页 (readyState=%s)" % (len(resp["html"]),
                                                              resp.get("ready_state")))
        meta = parse_meta(resp["html"], url)
        content_html, mode = extract_content(resp["html"])
        ok, reason, chars = judge(meta, content_html, mode, min_chars)
        if ok:
            return {"ok": True, "meta": meta, "layer": "4-cdp", "parse_mode": mode,
                    "chars": chars, "note": reason, "markdown": html_to_md(content_html),
                    "attempts": attempts, "diag": diag}
        diag.append("[4-cdp] 未过质量门：%s" % reason)
    return {"ok": False, "layer": None, "attempts": attempts, "diag": diag,
            "markdown": "", "note": "四层均未取到合格正文"}


def read_from_html(html, url, min_chars=MIN_FULLTEXT_CHARS):
    """离线解析入口（--fixture 与回归测试）：跳过网络层，只做解析 + 质量门。"""
    meta = parse_meta(html, url)
    content_html, mode = extract_content(html)
    ok, reason, chars = judge(meta, content_html, mode, min_chars)
    attempts = ["fixture: 本地页 %d 字符" % len(html)]
    if not ok:
        return {"ok": False, "layer": "fixture", "parse_mode": mode, "attempts": attempts,
                "diag": ["[fixture] 未过质量门：%s" % reason], "markdown": "", "note": reason}
    return {"ok": True, "meta": meta, "layer": "fixture", "parse_mode": mode,
            "chars": chars, "note": reason, "markdown": html_to_md(content_html),
            "attempts": attempts, "diag": []}


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.splitlines()[0])
    ap.add_argument("url")
    ap.add_argument("-o", "--out", help="Markdown 输出路径（缺省打印到 stdout）")
    ap.add_argument("--json", action="store_true", help="输出结构化结果（含正文 Markdown）")
    ap.add_argument("--min-chars", type=int, default=MIN_FULLTEXT_CHARS)
    ap.add_argument("--no-cdp", action="store_true", help="跳过第 4 层 CDP")
    ap.add_argument("--layer", type=int, choices=(1, 2, 3, 4), default=4,
                    help="最多降到第几层（默认 4）")
    ap.add_argument("--timeout", type=int, default=25)
    ap.add_argument("--fixture", help="离线解析本地已保存的文章页（不联网，回归测试用）")
    args = ap.parse_args()

    if args.fixture:
        with open(args.fixture, encoding="utf-8", errors="replace") as f:
            r = read_from_html(f.read(), args.url, args.min_chars)
    else:
        r = read(args.url, args.min_chars, not args.no_cdp, args.layer, args.timeout)
    if r["ok"]:
        doc = frontmatter(r["meta"], r["layer"], r["chars"], r["note"]) + \
            "# %s\n\n%s" % (r["meta"]["title"] or "(无标题)", r["markdown"])
    else:
        doc = ""
    if args.json:
        out = dict(r)
        out["markdown"] = doc
        print(json.dumps(out, ensure_ascii=False, indent=2))
    elif args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(doc if r["ok"] else "读取失败\n" + "\n".join(r["diag"]) + "\n")
        print("%s → %s" % ("OK" if r["ok"] else "FAIL", args.out))
    else:
        if r["ok"]:
            print(doc)
        for line in r["attempts"]:
            print("ATTEMPT", line, file=sys.stderr)
        for line in r["diag"]:
            print("DIAG", line, file=sys.stderr)
        if r["ok"]:
            if r["note"]:
                print("NOTE", r["note"], file=sys.stderr)
            print("LAYER %s · 正文 %d 字 · 解析 %s" % (r["layer"], r["chars"], r["parse_mode"]),
                  file=sys.stderr)
        else:
            print("FAIL 四层均未取到合格正文——按 read/references/cdp-edge.md 确认 Edge 调试端口，"
                  "或改用 search/ 换来源；勿对本 URL 继续重试。", file=sys.stderr)
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
