# -*- coding: utf-8 -*-
"""批量上传正文图片换 mmbiz URL（一步到位原则的批量版，替代逐张 uploadimg）。

用法：
  python upload_imgs.py --html <article-wx.html> [--map out.json]   # 扫描 HTML 内本地图片并上传
  python upload_imgs.py --img a.png b.png [--map out.json]          # 直接上传指定图片列表

输出：每张图打印 本地路径 -> mmbiz URL；--map 可选把「图片 basename -> URL」映射存为 JSON（键统一为 basename，供写作排版按图名查 URL）。
凭据从环境变量 WECHAT_APPID / WECHAT_SECRET 读取。

实现要点（3.4.0 起）：
  - 一次取 token 循环上传全部图片（不再逐张 subprocess 现取 token）。
  - 遇 45009（接口频率超限）自动退避重试：3s/6s/9s，最多 3 次；仍失败则 FAIL 退出。
  - 复用 wx_api.py 的 get_token / multipart_upload / http_json（直接 import，不重复实现）。
"""
import importlib.util
import os
import re
import json
import sys
import time

WX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                  "scripts", "wx_api.py")

# 加载 wx_api.py 模块（复用其函数，避免重复实现与凭据不一致）
_spec = importlib.util.spec_from_file_location("wx_api", WX)
wx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wx)


def parse(argv):
    html, imgs, outmap = None, [], None
    i = 0
    while i < len(argv):
        if argv[i] == "--html" and i + 1 < len(argv):
            html = argv[i + 1]; i += 2
        elif argv[i] == "--map" and i + 1 < len(argv):
            outmap = argv[i + 1]; i += 2
        elif argv[i] == "--img":
            i += 1
        else:
            imgs.append(argv[i]); i += 1
    return html, imgs, outmap


def upload_with_retry(token, path):
    """multipart_upload + 45009 退避重试（3s/6s/9s，最多 3 次）。"""
    last = None
    for attempt in range(3):
        j = wx.multipart_upload(token, path, "media/uploadimg")
        if j.get("errcode") == 45009 and attempt < 2:
            wait = 3 * (attempt + 1)
            print("WARN 45009 频率超限，%ss 后重试 (%s/3) ..." % (wait, attempt + 2),
                  file=sys.stderr)
            time.sleep(wait)
            last = j
            continue
        return j
    return last


def main():
    argv = sys.argv[1:]
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return
    html, imgs, outmap = parse(argv)
    if not html and not imgs:
        print(__doc__); sys.exit(1)
    need = set(imgs)
    if html:
        src = open(html, encoding="utf-8").read()
        base = os.path.dirname(os.path.abspath(html))
        for m in re.finditer(r'src="([^"]+)"', src):
            url = m.group(1)
            if url.startswith(("http://", "https://")):
                continue  # 已是 mmbiz 或外链，跳过
            full = os.path.normpath(os.path.join(base, url))
            if os.path.exists(full):
                need.add(full)
            else:
                print("WARN 本地路径不存在(跳过):", url)
    if not need:
        print("无可上传图片"); return

    appid = os.environ.get("WECHAT_APPID")
    secret = os.environ.get("WECHAT_SECRET")
    if not appid or not secret:
        print("ERR: WECHAT_APPID / WECHAT_SECRET 未设置", file=sys.stderr)
        sys.exit(1)
    tok = wx.get_token(appid, secret)
    if "access_token" not in tok:
        print("ERR token:", json.dumps(tok, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    token = tok["access_token"]  # 一次取 token，循环上传

    mapping = {}
    if outmap and os.path.exists(outmap):
        try:
            mapping = json.load(open(outmap, encoding="utf-8"))
        except Exception:
            mapping = {}
    for p in sorted(need):
        j = upload_with_retry(token, p)
        url = (j or {}).get("url", "")
        if url:
            mapping[os.path.basename(p)] = url  # 键统一为 basename，写作排版按图名命中即换 URL
            print(os.path.basename(p), "->", url[:80])
        else:
            print("FAIL", os.path.basename(p), json.dumps(j, ensure_ascii=False)[:300])
            sys.exit(1)
    if outmap:
        with open(outmap, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=1)
        print("saved", len(mapping), "urls ->", outmap)
    print("DONE", len(mapping), "images")


if __name__ == "__main__":
    main()
