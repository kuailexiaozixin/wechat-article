# -*- coding: utf-8 -*-
"""evals/evals.json 路由用例的可证伪核对。

两件事：
  1. 用例里写到的每个仓库路径必须真实存在（文档改名/删文件而 evals 没跟着改 → 报红）。
  2. 用例里写到的每个 `--长选项` 必须出现在同一用例引用的某个脚本里
     （argparse 声明或 docstring 用法行）——评测量到的命令不能是想象出来的 flag。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
EVALS = os.path.join(ROOT, "evals", "evals.json")

PATH_RX = re.compile(r"(?:write|read|search|draft|materials|scripts|references|tests)/[A-Za-z0-9_./-]+")
BARE_RX = re.compile(r"\b[A-Za-z0-9_-]+\.py\b")   # 只解析脚本名；命令里的输出文件名（article.md/imgs.json）不是仓库引用
FLAG_RX = re.compile(r"--([a-z][a-z0-9-]*)")
IGNORED_FLAGS = {"help"}       # -h/--help 由 docstring 短路与 argparse 提供，不逐一核对


def script_index():
    """脚本 basename → 仓库内相对路径列表；用于解析用例里不带目录的脚本名。"""
    idx = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in filenames:
            if fn.endswith(".py") and not fn.startswith("test_"):
                idx.setdefault(fn, []).append(
                    os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/"))
    return idx


def blob(case):
    return " ".join([case.get("prompt", ""), case.get("expected_output", "")]
                    + list(case.get("expectations", [])))


def flags_of(script_rel):
    p = os.path.join(ROOT, script_rel.replace("/", os.sep))
    src = io.open(p, encoding="utf-8").read()
    return set(FLAG_RX.findall(src))


def run():
    fails = []
    if not os.path.exists(EVALS):
        print("FAIL evals/evals.json 不存在")
        return 1
    with io.open(EVALS, encoding="utf-8") as f:
        data = json.load(f)
    cases = data.get("evals", [])
    if data.get("skill_name") != "wechat-article":
        fails.append("skill_name 应为 wechat-article，实为 %r" % data.get("skill_name"))
    if not 8 <= len(cases) <= 10:
        fails.append("用例数 %d 不在 8–10 区间" % len(cases))
    ids = [c.get("id") for c in cases]
    if ids != list(range(1, len(cases) + 1)):
        fails.append("id 不连续/重复：%s" % ids)

    checked_paths, checked_flags, idx = set(), set(), script_index()
    for c in cases:
        b = blob(c)
        if not c.get("prompt") or not c.get("expected_output") or not c.get("expectations"):
            fails.append("用例 #%s 字段不全（prompt/expected_output/expectations 均必填）" % c.get("id"))
        refs = {r.rstrip(".") for r in PATH_RX.findall(b)}
        for r in sorted(refs):
            checked_paths.add(r)
            if not os.path.exists(os.path.join(ROOT, r.replace("/", os.sep))):
                fails.append("用例 #%s 引用路径不存在：%s" % (c.get("id"), r))
        # 不带目录的脚本名（如 check_draft.py）也要能落到唯一文件上
        bare = {t for t in BARE_RX.findall(b)
                if t not in {os.path.basename(x) for x in refs}}
        for t in sorted(bare):
            hits = idx.get(t, [])
            if not hits:
                fails.append("用例 #%s 引用文件仓库内不存在：%s" % (c.get("id"), t))
                continue
            checked_paths.update(hits)
        scripts = sorted(refs | {h for t in bare for h in idx.get(t, [])})
        scripts = [s for s in scripts if s.endswith(".py")]
        pool = set()
        for s in scripts:
            if not os.path.exists(os.path.join(ROOT, s.replace("/", os.sep))):
                continue      # 文件缺失已由上面的存在性判据报红，此处不重复炸
            pool |= flags_of(s)
        for flag in sorted(set(FLAG_RX.findall(b))):
            checked_flags.add(flag)
            if flag in IGNORED_FLAGS or flag in pool:
                continue
            fails.append("用例 #%s 用到 --%s，但所引脚本 %s 中无此选项声明"
                         % (c.get("id"), flag, scripts or "（未引用任何 .py）"))

    print("evals 路由核对：%d 条用例 · 引用路径 %d 个 · 核对长选项 %d 个"
          % (len(cases), len(checked_paths), len(checked_flags)))
    for m in fails:
        print("FAIL", m)
    print("evals 路由判据：%d 项失败" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
