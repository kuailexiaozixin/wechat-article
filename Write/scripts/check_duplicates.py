# -*- coding: utf-8 -*-
"""跨文章重复段落检测（系列文章防自我抄袭 / 内容冗余）。

用法:
    python check_duplicates.py <dir或文件...> [--min-len 40] [--threshold 0.8] [--fail]

- 输入：目录（递归扫 *.html）或文件列表；正文段提取自 HTML 文本节点（去标签、去代码块）。
- 相似度：字符 4-gram Jaccard；段落长度差 > 20% 跳过。
- 输出：跨文件重复对（文件 A ←→ 文件 B，相似段落片段）。
- 退出码：0 = 正常（默认，重复仅提示）；--fail 时存在重复返回 1。
"""
import argparse
import glob
import os
import re
import sys
from html.parser import HTMLParser


class TextExtractor(HTMLParser):
    """提取非代码区正文文本段（跳过 script/style，代码块按 <p> 等宽样式跳过）。"""

    CODE_STYLE = re.compile(r"monospace|white-space\s*:\s*pre|courier|consolas|menlo", re.I)

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.code_depth = 0
        self.paras = []

    def handle_starttag(self, tag, attrs):
        ad = dict(attrs)
        style = ad.get("style", "") or ""
        is_code = bool(self.CODE_STYLE.search(style)) or tag in ("code", "pre")
        if is_code:
            self.code_depth += 1
        self.stack.append((tag, is_code))

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                for _, was_code in self.stack[i:]:
                    if was_code:
                        self.code_depth -= 1
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.code_depth == 0 and any(t in ("script", "style") for t, _ in self.stack):
            return
        if self.code_depth == 0:
            text = re.sub(r"\s+", "", data.strip())
            if len(text) >= 10:
                self.paras.append(text)


def extract_paras(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except Exception as e:
        print(f"WARN 读取失败 {path}: {e}", file=sys.stderr)
        return []
    ex = TextExtractor()
    try:
        ex.feed(html)
    except Exception:
        pass
    return ex.paras


def ngram_set(text, n=4):
    if len(text) < n:
        return {text}
    return {text[i:i + n] for i in range(len(text) - n + 1)}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def main():
    ap = argparse.ArgumentParser(description="跨文章重复段落检测")
    ap.add_argument("paths", nargs="+", help="目录或 HTML 文件")
    ap.add_argument("--min-len", type=int, default=40, help="参与比较的最小段落字数")
    ap.add_argument("--threshold", type=float, default=0.8, help="相似度阈值（Jaccard）")
    ap.add_argument("--fail", action="store_true", help="存在重复时退出码 1")
    args = ap.parse_args()

    files = []
    for p in args.paths:
        if os.path.isdir(p):
            files.extend(glob.glob(os.path.join(p, "**", "*.html"), recursive=True))
        else:
            files.append(p)
    files = sorted(set(files))
    if not files:
        print("无 HTML 文件"); sys.exit(0)

    # 预提取：段落 -> (file_idx, 段文本)
    paras = []  # (file_idx, text)
    for fi, f in enumerate(files):
        for t in extract_paras(f):
            if len(t) >= args.min_len:
                paras.append((fi, t))
    print(f"扫描 {len(files)} 个文件，段落 {len(paras)} 段（≥{args.min_len} 字）")

    n_paras = len(paras)
    ngrams = [(fi, ngram_set(t)) for fi, t in paras]
    dups = []
    for i in range(n_paras):
        fi_i, gi = ngrams[i]
        for j in range(i + 1, n_paras):
            fi_j, gj = ngrams[j]
            if fi_i == fi_j:
                continue  # 只报跨文件
            li, lj = len(paras[i][1]), len(paras[j][1])
            if abs(li - lj) / max(li, lj) > 0.2:
                continue
            s = jaccard(gi, gj)
            if s >= args.threshold:
                dups.append((fi_i, fi_j, s, paras[i][1], paras[j][1]))

    if not dups:
        print("无跨文件重复段落")
        sys.exit(0)
    print(f"发现 {len(dups)} 对跨文件重复段落（阈值 {args.threshold:.2f}）：")
    for fi_a, fi_b, s, ta, tb in dups[:40]:
        print(f"  [{s:.2f}] {os.path.basename(files[fi_a])} ←→ {os.path.basename(files[fi_b])}")
        print(f"      A: {ta[:50]}…")
        print(f"      B: {tb[:50]}…")
    if len(dups) > 40:
        print(f"  …（仅显示前 40 对，共 {len(dups)} 对）")
    sys.exit(1 if args.fail else 0)


if __name__ == "__main__":
    main()
