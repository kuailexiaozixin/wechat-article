# -*- coding: utf-8 -*-
"""公众号封面生成器：纯几何、无文字、深蓝 #1F3864 + 金 #B08D3E。

系列文章每篇换封面：--seed 不传时用随机种子，保证封面唯一；--pattern
可选 layers（装饰器嵌套）/ guard（守卫分支）/ grid（账本网格）/ circuit（订单回路）。

用法:
    python gen_cover.py --out <path.png> [--pattern layers|guard|grid|circuit] [--seed N] [--size WxH]
示例:
    python gen_cover.py --out cover-0066.png --pattern guard --seed 20260901
    python gen_cover.py --out cover-0067.png --pattern layers            # 随机种子
    python gen_cover.py --out cover-0068.png --pattern circuit --size 2048x880

依赖: Pillow（PIL）。
"""
import argparse
import math
import os
import random
import sys

from PIL import Image, ImageDraw

NAVY = (31, 56, 100)      # #1F3864
GOLD = (176, 141, 62)     # #B08D3E
PALE = (226, 214, 189)    # 浅金

PATTERNS = ("layers", "guard", "grid", "circuit")


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _noise(draw, rng, W, H):
    """全幅点状底纹。"""
    for _ in range(140):
        x, y = rng.randint(0, W), rng.randint(0, H)
        r = rng.randint(1, 3)
        c = lerp(NAVY, GOLD, rng.random() * 0.35)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=c)


def _draw_layers(draw, rng, W, H):
    """嵌套方框：装饰器逐层包裹的意象（模块、路由、权限层层嵌套）。"""
    cx, cy = W * 0.5, H * 0.5
    for i in range(80):
        r = int(900 * (i + 1) / 80)
        alpha = int(6 + i * 0.35)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=lerp(NAVY, GOLD, i / 220))
    n = 7
    max_w = 1200
    for i in range(n):
        t = i / (n - 1)
        w = int(max_w * (1 - t * 0.82))
        h = int(w * 0.62)
        x0, y0 = cx - w // 2, cy - h // 2
        off = int(14 + t * 46)
        x0 += rng.randint(-off, off)
        y0 += rng.randint(-off, off)
        color = lerp(GOLD, NAVY, t * 0.75) if i % 2 == 0 else lerp(PALE, GOLD, t * 0.4)
        width = max(2, int(10 - t * 5))
        draw.rectangle([x0, y0, x0 + w, y0 + h], outline=color, width=width)
    r = 26
    draw.rectangle([60, 60, 60 + r * 3, 60 + r * 3], fill=GOLD)
    draw.rectangle([W - 60 - r * 3, H - 60 - r * 3, W - 60, H - 60], fill=GOLD)
    draw.line([0, int(H * 0.5), 120, int(H * 0.5)], fill=GOLD, width=3)
    draw.line([W - 120, int(H * 0.5), W, int(H * 0.5)], fill=GOLD, width=3)


def _draw_guard(draw, rng, W, H):
    """双分支路径：守卫决策分叉（权限校验/状态机分岔）。"""
    cx = W * 0.5
    for i in range(60):
        r = int(950 * (i + 1) / 60)
        draw.ellipse([cx - r, 120 - r, cx + r, H - 120 + r], outline=lerp(NAVY, GOLD, i / 240), width=2)
    d = 260
    draw.polygon([(cx, 300), (cx + d, 440), (cx, 580), (cx - d, 440)], outline=GOLD, width=8)
    for side in (-1, 1):
        x1 = cx + side * d
        y1 = 440
        x2 = cx + side * 520
        draw.line([x1, y1, x2, y1], fill=GOLD, width=6)
        draw.line([x2, y1, x2, y1 + 220], fill=GOLD, width=6)
        draw.ellipse([x2 - 46, y1 + 220 - 46, x2 + 46, y1 + 220 + 46], outline=PALE, width=5)
    draw.rectangle([cx - 16, 140, cx + 16, 172], fill=GOLD)


def _draw_grid(draw, rng, W, H):
    """账本网格：数据库表/账簿的行列结构。"""
    step = 92
    for x in range(0, W, step):
        draw.line([x, 0, x, H], fill=lerp(NAVY, GOLD, 0.22), width=1)
    for y in range(0, H, step):
        draw.line([0, y, W, y], fill=lerp(NAVY, GOLD, 0.22), width=1)
    # 表头行高亮 + 若干高亮单元格（数据点）
    draw.rectangle([0, 0, W, 68], fill=GOLD)
    for _ in range(9):
        cx = rng.randint(1, W // step - 1) * step
        cy = rng.randint(1, H // step - 1) * step
        draw.rectangle([cx, cy, cx + step, cy + step], outline=PALE, width=2)
        draw.ellipse([cx + step // 2 - 8, cy + step // 2 - 8,
                      cx + step // 2 + 8, cy + step // 2 + 8], fill=PALE)
    # 对角主线
    draw.line([0, H, W, 0], fill=GOLD, width=4)


def _draw_circuit(draw, rng, W, H):
    """订单回路：订单到收款的环形流转。"""
    cx, cy = W * 0.5, H * 0.5
    R = int(H * 0.34)
    for i in range(72):
        a0 = math.pi * 2 * i / 72
        a1 = math.pi * 2 * (i + 1) / 72
        x0, y0 = cx + R * math.cos(a0), cy + R * math.sin(a0)
        x1, y1 = cx + R * math.cos(a1), cy + R * math.sin(a1)
        draw.line([x0, y0, x1, y1], fill=lerp(NAVY, GOLD, i / 72), width=2)
    # 环上四个节点（Draft→Deliver→Invoice→Pay）
    for i in range(4):
        a = math.pi * 2 * i / 4 - math.pi / 2
        nx, ny = cx + R * math.cos(a), cy + R * math.sin(a)
        draw.ellipse([nx - 42, ny - 42, nx + 42, ny + 42], outline=GOLD, width=6)
        draw.ellipse([nx - 14, ny - 14, nx + 14, ny + 14], fill=GOLD)
    # 中心记账符号意象（+ / -）
    draw.line([cx - 90, cy, cx + 90, cy], fill=PALE, width=8)
    draw.line([cx, cy - 90, cx, cy + 90], fill=PALE, width=8)


def make_cover(path, pattern, seed, size):
    W, H = size
    img = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)
    rng = random.Random(seed)
    _noise(draw, rng, W, H)
    if pattern == "layers":
        _draw_layers(draw, rng, W, H)
    elif pattern == "guard":
        _draw_guard(draw, rng, W, H)
    elif pattern == "grid":
        _draw_grid(draw, rng, W, H)
    else:
        _draw_circuit(draw, rng, W, H)
    img.save(path, "PNG")
    print(f"cover: {path}  pattern={pattern}  seed={seed}  {W}x{H}")


def main():
    ap = argparse.ArgumentParser(description="公众号封面生成器（纯几何无文字）")
    ap.add_argument("--out", required=True, help="输出 PNG 路径")
    ap.add_argument("--pattern", choices=PATTERNS, default="layers", help="几何图案")
    ap.add_argument("--seed", type=int, default=None, help="随机种子（缺省随机，保证每篇不同）")
    ap.add_argument("--size", default="2048x880", help="尺寸 WxH（默认 2048x880，接近 2.35:1）")
    args = ap.parse_args()

    try:
        W, H = (int(x) for x in args.size.lower().split("x"))
    except Exception:
        print("ERR: --size 格式应为 WxH，如 2048x880", file=sys.stderr)
        sys.exit(1)
    seed = args.seed if args.seed is not None else random.randint(1, 99999999)
    make_cover(args.out, args.pattern, seed, (W, H))


if __name__ == "__main__":
    main()
