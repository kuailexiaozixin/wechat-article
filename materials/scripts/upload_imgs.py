# -*- coding: utf-8 -*-
"""批量上传正文图片换 mmbiz URL（一步到位原则的批量版，替代逐张 uploadimg）。

用法：
  python upload_imgs.py --html <article-wx.html> [--map out.json]   # 扫描 HTML 内本地图片并上传
  python upload_imgs.py --img a.png b.png [--map out.json]          # 直接上传指定图片列表

输出：每张图打印 本地路径 -> mmbiz URL；--map 可选把「本地路径->URL」映射存为 JSON。
凭据从环境变量 WECHAT_APPID / WECHAT_SECRET 读取；依赖同目录 wx_api.py。
"""
import os, re, json, subprocess, sys

WX = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts", "wx_api.py")


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


def main():
    html, imgs, outmap = parse(sys.argv[1:])
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
    env = os.environ.copy()
    mapping = {}
    for p in sorted(need):
        r = subprocess.run([sys.executable, WX, "uploadimg", p], env=env,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        try:
            j = json.loads(out)
            url = j.get("url", "")
            if url:
                mapping[p] = url
                print(os.path.basename(p), "->", url[:80])
            else:
                print("FAIL", os.path.basename(p), out[:200]); sys.exit(1)
        except Exception:
            print("FAIL", os.path.basename(p), out[:300]); sys.exit(1)
    if outmap:
        with open(outmap, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=1)
        print("saved", len(mapping), "urls ->", outmap)
    print("DONE", len(mapping), "images")


if __name__ == "__main__":
    main()
