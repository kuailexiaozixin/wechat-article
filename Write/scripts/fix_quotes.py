# -*- coding: utf-8 -*-
"""正文引号全角化（跳过代码块）。"""
import re
import sys

p = sys.argv[1]
lines = open(p, encoding="utf-8").read().split("\n")
out, in_code = [], False
for ln in lines:
    if ln.startswith("```"):
        in_code = not in_code
    elif not in_code:
        ln = re.sub(r'"([^"]*)"', "\u201c\\1\u201d", ln)
    out.append(ln)
open(p, "w", encoding="utf-8").write("\n".join(out))
print("done:", p)
