# -*- coding: utf-8 -*-
"""图片压缩器：把正文图压到 1MB 以下（media/uploadimg 的硬上限），封面另按 10MB 口径。

为什么需要它：正文图超 1MB 上传必报 `40009 invalid image size`，是 B1 阶段最常见的失败点。
`upload_imgs.py` / `figure_manifest.py check` 都会在超限时 FAIL，但都不负责压——本脚本补这一环。

用法:
    python compress_img.py <img> [img2 ...] [--max-kb 950] [--max-width 1080]
                           [--quality 85] [--out-dir <dir>] [--in-place]

参数:
    --max-kb     目标上限（KB，默认 950，给 1MB 留余量；封面可传 --max-kb 9800）
    --max-width  像素宽度上限（默认 1080，超宽先缩放；0 表示不缩放）
    --quality    JPEG 起始质量（默认 85，不够再逐级降）
    --out-dir    输出目录（缺省与原图同目录）
    --in-place   就地把压缩结果覆盖原文件（缺省另存为 <stem>_min<ext>，不破坏原图）

策略（按顺序尝试，命中即停）:
    JPEG：质量 85→80→70→60→50；仍超则逐级降分辨率（×0.85/0.70/0.55）再降质量。
    PNG ：先 optimize；再量化到 256 色；再逐级降分辨率。
输出：逐张打印「原大小 -> 新大小（压缩比）」，全部达标退出 0；仍有超限者退出 1。

依赖：Pillow（PIL）。
"""
import argparse
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

try:
    from PIL import Image
except ImportError:
    print("ERR 未安装 Pillow，无法压缩——请先 pip install Pillow。", file=sys.stderr)
    sys.exit(2)


def _save_bytes(im, fmt, quality):
    buf = io.BytesIO()
    if fmt == "JPEG":
        im.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
    else:
        im.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def _scale(im, factor):
    if factor >= 1.0:
        return im
    w = max(1, int(im.width * factor))
    h = max(1, int(im.height * factor))
    return im.resize((w, h), Image.LANCZOS)


def _attempts(fmt, quality):
    """产出 (scale, quality_or_None, quantize) 尝试序列。"""
    if fmt == "JPEG":
        seq = [(1.0, q, False) for q in (quality, 80, 70, 60, 50)]
        for s in (0.85, 0.70, 0.55):
            seq += [(s, q, False) for q in (quality, 70, 55)]
        return seq
    # PNG / 其他：optimize → 量化 → 降分辨率
    seq = [(1.0, None, False), (1.0, None, True)]
    for s in (0.85, 0.70, 0.55):
        seq += [(s, None, False), (s, None, True)]
    return seq


def compress_one(path, max_bytes, max_width, quality, out_dir, in_place):
    orig = os.path.getsize(path)
    with Image.open(path) as im:
        fmt = (im.format or "PNG").upper()
        if fmt in ("JPG", "JPEG"):
            fmt = "JPEG"
        work = im.copy()
    # 先按 --max-width 缩放（若原图超宽）
    if max_width and work.width > max_width:
        work = _scale(work, max_width / float(work.width))

    if orig <= max_bytes:
        print("OK   %s  %d 字节，已在 %d KB 以内，无需压缩"
              % (os.path.basename(path), orig, max_bytes // 1024))
        return True

    best = None  # (bytes, scale, quality, quantize)
    for scale, q, quant in _attempts(fmt, quality):
        im2 = _scale(work, scale)
        if quant:
            im2 = im2.convert("P", palette=Image.ADAPTIVE, colors=256)
        data = _save_bytes(im2, fmt, q)
        if best is None or len(data) < len(best[0]):
            best = (data, scale, q, quant)
        if len(data) <= max_bytes:
            break

    data, scale, q, quant = best
    ext = ".jpg" if fmt == "JPEG" else ".png"
    stem = os.path.splitext(os.path.basename(path))[0]
    if in_place:
        out = path
    else:
        out = os.path.join(out_dir or os.path.dirname(os.path.abspath(path)), stem + "_min" + ext)
    with open(out, "wb") as f:
        f.write(data)
    ratio = (1 - len(data) / float(orig)) * 100 if orig else 0
    tag = "OK  " if len(data) <= max_bytes else "WARN"
    detail = "scale=%.2f" % scale + (", q=%d" % q if q else "") + (", quant" if quant else "")
    print("%s %s  %d -> %d 字节（降 %.0f%%，%s）%s"
          % (tag, os.path.basename(path), orig, len(data), ratio, detail,
             "" if len(data) <= max_bytes else "  仍超限，请降 --max-width 或换更小源图"))
    return len(data) <= max_bytes


def main():
    ap = argparse.ArgumentParser(description="图片压缩器（正文图压到 1MB 以下）")
    ap.add_argument("imgs", nargs="+", help="一个或多个图片路径")
    ap.add_argument("--max-kb", type=int, default=950, help="目标上限 KB（默认 950）")
    ap.add_argument("--max-width", type=int, default=1080, help="像素宽度上限（默认 1080，0=不缩放）")
    ap.add_argument("--quality", type=int, default=85, help="JPEG 起始质量（默认 85）")
    ap.add_argument("--out-dir", default=None, help="输出目录（缺省与原图同目录）")
    ap.add_argument("--in-place", action="store_true", help="就地覆盖原文件")
    args = ap.parse_args()

    max_bytes = args.max_kb * 1024
    all_ok = True
    for p in args.imgs:
        if not os.path.isfile(p):
            print("FAIL 文件不存在：%s" % p, file=sys.stderr)
            all_ok = False
            continue
        try:
            ok = compress_one(p, max_bytes, args.max_width, args.quality,
                              args.out_dir, args.in_place)
        except Exception as e:  # noqa: BLE001
            print("FAIL 处理失败 %s：%s" % (p, e), file=sys.stderr)
            ok = False
        all_ok = all_ok and ok
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
