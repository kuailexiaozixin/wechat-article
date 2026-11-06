# -*- coding: utf-8 -*-
"""把正文 HTML 里的 `__MMP__:<filename>` 图位占位回填为 mmbiz URL，是 A3→B1 的交接闸。

A3 逻辑的 L5 `html` 子命令直出的正文里，图是 `src="__MMP__:<filename>"` 占位（filename 与 B1
清单 manifest 的 `filename` 字段一致，也即 upload_imgs 映射表的键）。本脚本按映射表把占位
整体替换为 mmbiz URL 并回写 HTML，然后自检无残留占位。上传与回填职责分离：先
`upload_imgs.py` 拿映射，再本脚本回填，最后 `check_urls.py`（--html）复核残留清零。

用法:
    python fill_placeholders.py --html article-wx.html --map mmbiz_map.json [--dry-run]

判据:
    占位的 key 不在 map 里  -> FAIL（列出所有对不上的 key，不静默跳过）
    回填后 HTML 仍残留 __MMP__ -> FAIL
    全部回填且无残留        -> PASS，退出码 0；有 FAIL 退出码 1

退出码：0 = 全部回填成功；1 = 有 key 缺失或残留占位；2 = 用法错误（缺参/文件不存在/非法 JSON）。
纯本地字符串替换，不涉及凭据与网络。
"""
import argparse
import io
import json
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
PLACE_RX = re.compile(r'src="__MMP__:([^"]+)"')  # 捕获 filename（不含 __MMP__: 前缀）

def main():
    ap = argparse.ArgumentParser(description="A3→B1 占位回填：__MMP__:filename -> mmbiz URL")
    ap.add_argument("--html", required=True, help="A3 逻辑直出的正文 HTML（含 __MMP__ 占位）")
    ap.add_argument("--map", required=True, help="upload_imgs.py 产出的 mmbiz_map.json（{filename: url}）")
    ap.add_argument("--dry-run", action="store_true", help="只报告不写回，核对 key 是否都在 map 里")
    args = ap.parse_args()

    for p in (args.html, args.map):
        if not os.path.isfile(p):
            print("ERR 文件不存在：%s" % p, file=sys.stderr)
            return 2
    try:
        mapping = json.loads(io.open(args.map, encoding="utf-8-sig").read())
    except Exception as e:  # noqa: BLE001
        print("ERR map 不是合法 JSON：%s" % e, file=sys.stderr)
        return 2
    if not isinstance(mapping, dict):
        print("ERR map 应为 {filename: url} 对象", file=sys.stderr)
        return 2

    html = io.open(args.html, encoding="utf-8-sig").read()
    keys = sorted(set(PLACE_RX.findall(html)))
    bad = [k for k in keys if k not in mapping]
    for b in bad:
        print("FAIL 占位 key 不在 map 里：%s（upload_imgs 未覆盖或文件名对不上）" % b, file=sys.stderr)

    filled = {k: mapping[k] for k in keys if k in mapping}
    for k, url in filled.items():
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            print("FAIL key %s 的映射值不是 URL：%r" % (k, url), file=sys.stderr)
            return 1

    if args.dry_run:
        print("dry-run：%d 个占位，%d 个可回填，%d 个缺失" % (len(keys), len(filled), len(bad)))
        return 1 if bad else 0

    new_html = html
    for k, url in filled.items():
        new_html = new_html.replace('src="__MMP__:%s"' % k, 'src="%s"' % url, 1)

    remaining = ["__MMP__:" + k for k in sorted(set(PLACE_RX.findall(new_html)))]
    if not args.dry_run:
        with open(args.html, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_html)
        print("已回填 %d 个占位 -> %s" % (len(filled), os.path.basename(args.html)))
    if remaining:
        for r in remaining:
            print("FAIL 回填后仍残留占位：%s（key 不在 map 或映射值非 URL）" % r, file=sys.stderr)
        return 1
    if not bad and not filled:
        print("HTML 无 __MMP__ 占位，无需回填")
    print("PASS 占位清零" if not bad else "FAIL %d 个 key 缺失" % len(bad))
    return 1 if bad else 0

if __name__ == "__main__":
    sys.exit(main())
