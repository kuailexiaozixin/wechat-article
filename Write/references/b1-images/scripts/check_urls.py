# -*- coding: utf-8 -*-
"""mmbiz 图片 URL 批量体检：上传的图会不会掉，换会话动手前先抽查一轮。

背景：`media/uploadimg` 返回的 mmbiz.qpic.cn URL 官方页未写有效期，本技能按「长期可用 +
定期抽查」处理（见 image-upload-interfaces.md「URL 失效处理」）。此前抽查靠人工，本脚本把
它固化：逐条 HTTP GET map 里的 URL，报状态码；--html 模式额外核「HTML 用到的 URL 是否都在
map 里」（防漏传）。

用法:
    python check_urls.py --map mmbiz_map.json [--html article-wx.html]
                         [--timeout 10] [--json]

判据:
    http 200        -> OK
    其他状态码/网络错误 -> FAIL（HTML 若引用该 URL，需重新 uploadimg 换新 URL 后 draft-update 重推）
    --html 且某 mmbiz URL 不在 map 的值里 -> FAIL（漏传：正文引用了未登记的图）
仅本地/网络只读，需凭据无关。退出码：0 = 全部 OK；1 = 有 FAIL。
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

UA = "Mozilla/5.0 (compatible; wechat-article-url-check/1.0)"


def http_status(url, timeout):
    """返回 (status_or_None, err)。只读 1 字节即断，不下载整图。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            r.read(1)
            return r.getcode(), None
    except urllib.error.HTTPError as e:
        return e.code, "HTTP %d" % e.code
    except Exception as e:  # noqa: BLE001
        return None, str(e)


def main():
    ap = argparse.ArgumentParser(description="mmbiz 图片 URL 批量体检")
    ap.add_argument("--map", required=True, help="mmbiz_map.json 路径")
    ap.add_argument("--html", default=None, help="可选：正文 HTML，核 URL 是否都在 map 里")
    ap.add_argument("--timeout", type=int, default=10, help="单条超时秒数（默认 10）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    args = ap.parse_args()

    if not os.path.isfile(args.map):
        print("ERR map 不存在：%s" % args.map, file=sys.stderr)
        return 1
    try:
        mapping = json.loads(io.open(args.map, encoding="utf-8-sig").read())
    except Exception as e:  # noqa: BLE001
        print("ERR map 不是合法 JSON：%s" % e, file=sys.stderr)
        return 1
    if not isinstance(mapping, dict) or not mapping:
        print("ERR map 为空或不是对象", file=sys.stderr)
        return 1

    fails = []
    results = {}
    for name, url in mapping.items():
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            results[name] = {"status": None, "err": "非 URL"}
            fails.append((name, url, "非 URL"))
            continue
        status, err = http_status(url, args.timeout)
        results[name] = {"status": status, "err": err, "url": url}
        if status != 200:
            fails.append((name, url, err or ("HTTP %s" % status)))

    # --html：核查正文引用的 mmbiz URL 是否都在 map 里
    missing = []
    if args.html:
        if not os.path.isfile(args.html):
            print("ERR html 不存在：%s" % args.html, file=sys.stderr)
            return 1
        html = io.open(args.html, encoding="utf-8-sig").read()
        used = set(re.findall(r'src="(https?://mmbiz\.qpic\.cn/[^"]+)"', html))
        known = set(v for v in mapping.values() if isinstance(v, str))
        missing = sorted(u for u in used if u not in known)
        for u in missing:
            fails.append(("<html>", u, "正文引用但不在 map 中（漏传）"))

    if args.json:
        print(json.dumps({"fail": [{"name": n, "url": u, "err": e} for n, u, e in fails],
                          "checked": len(mapping), "results": results,
                          "html_missing": missing}, ensure_ascii=False))
        return 1 if fails else 0

    print("=== mmbiz URL 体检：%s（%d 条）===" % (args.map, len(mapping)))
    for name, r in results.items():
        if r["status"] == 200:
            print("  [OK]   %s" % name)
        else:
            print("  [FAIL] %s  %s" % (name, r["err"]))
    if args.html:
        print("  -- 正文核验 %s：引用 %d 个 mmbiz URL"
              % (os.path.basename(args.html),
                 len(set(re.findall(r'src="(https?://mmbiz\.qpic\.cn/[^"]+)"',
                                    io.open(args.html, encoding="utf-8-sig").read())))))
        for u in missing:
            print("  [FAIL] 正文引用但不在 map 中：%s" % u[:90])
    if fails:
        print("[FAIL] %d 项不通过——失效图需重新 uploadimg 换新 URL 后 draft-update 重推。"
              % len(fails))
        return 1
    print("[PASS] %d 条全部可达。" % len(mapping))
    return 0


if __name__ == "__main__":
    sys.exit(main())
