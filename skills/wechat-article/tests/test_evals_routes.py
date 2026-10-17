# -*- coding: utf-8 -*-
"""evals/evals.json 路由用例的可证伪核对 + 全树路径引用的大小写核对。

三件事：
  1. 用例里写到的每个仓库路径必须真实存在（文档改名/删文件而 evals 没跟着改 → 报红）。
  2. 用例里写到的每个 `--长选项` 必须出现在同一用例引用的某个脚本里
     （argparse 声明或 docstring 用法行）——评测量到的命令不能是想象出来的 flag。
  3. 全树文本里的顶层目录引用（`write/`…`tests/`、以及 `"read"` 这种引号形式）必须与
     **磁盘上的真实名字逐字符一致**且路径存在。本地是 `write/ read/ search/` 大写布局，
     发布树按 gh skill 的 `skills/<name>/` 结构收成小写；Windows 文件系统大小写不敏感，
     「文件能打开」证明不了这一点，Linux/macOS 克隆后才暴露成 file not found。
     发布仓库根那一层的 `README.md` 一起扫（它写的是 `skills/<技能名>/` 打头的完整式路径，
     剥掉这一段前缀后与子树内引用同一口径比对；本地安装树没有这一层，取不到就跳过）。
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


# ---- 第 3 件事：路径引用与磁盘布局逐字符核对（两种布局共用同一份判据） ----
TOPS = ("write", "read", "search", "draft", "materials", "scripts", "references", "tests", "evals")
REF_RX = re.compile(r"(?<![A-Za-z0-9_./-])((?:%s)/[A-Za-z0-9_./-]*)" % "|".join(TOPS),
                    re.IGNORECASE)
QUOTED_TOP_RX = re.compile(r'"(%s)"' % "|".join(TOPS), re.IGNORECASE)
TEXT_EXT = (".md", ".py", ".json")
LAYOUT_SKIP = {"CHANGELOG.md"}   # 历史条目记的是当时的路径实况，可能指向已删文件，不作断链


def disk_tops():
    """磁盘上真实存在的顶层目录名（跳过 `.git` 这类点开头目录），按小写建索引用于逐字符比对。"""
    return {n.lower(): n for n in os.listdir(ROOT)
            if os.path.isdir(os.path.join(ROOT, n)) and not n.startswith(".")}


def text_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
        for fn in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
            if fn.endswith(TEXT_EXT) and rel not in LAYOUT_SKIP:
                yield rel, None


def repo_meta_files():
    """发布仓库根那一层的 README。它写在技能子树之外，路径却是以 `skills/<技能名>/` 打头的完整式，
    子树内的判据本来看不见——本轮实测就在 README 里写出过一个顶层目录大小写错的引用（磁盘上首字母
    大写、文中写成了小写，Linux 克隆过来就是 file not found）。剥掉 `skills/<本目录名>/` 这一段前缀后，
    它与子树内的引用按同一口径比对；本地安装树没有这一层，取不到就跳过。"""
    up = os.path.normpath(os.path.join(ROOT, os.pardir, os.pardir))
    prefix = "skills/" + os.path.basename(ROOT) + "/"
    out = []
    for fn in ("README.md",):
        p = os.path.join(up, fn)
        if os.path.isfile(p):
            out.append(("../README.md", prefix, p))
    return out


def check_layout():
    """返回 (失败列表, 核对到的引用数)。

    大小写核对对所有命中做（这才是「双轨」的病根：磁盘上的顶层目录是首字母大写，
    文中写成了全小写，Windows 打开得了、Linux 克隆过来就是 file not found）；
    存在性核对只对**像路径**的引用做——末段带点（文件）或原文以 `/` 结尾（目录）。
    `draft/add`、`draft/batchget` 是微信接口名不是文件，三段的顶层目录并列是散文写法，
    都归这条规则之外；两段式并列（第二段本身也是顶层目录）同样不查存在性。
    覆盖面边界：测试脚本用 `os.path.join(HERE, os.pardir, "write", "scripts", ...)` 拼出来的
    加载路径不在本判据里（那不是一个连续的路径字符串），那种点由加载方测试自己炸——文件不在
    就是执行异常，run_all 计为失败。
    """
    fails, tops, n = [], disk_tops(), 0
    sources = [(rel, os.path.join(ROOT, rel.replace("/", os.sep)), None)
               for rel, _ in text_files()]
    sources += [(fn, path, prefix) for fn, prefix, path in repo_meta_files()]
    for rel, path, prefix in sources:
        text = io.open(path, encoding="utf-8", errors="replace").read()
        if prefix:                       # 仓库根 README 用完整式路径，剥前缀后同一口径比对
            text = text.replace(prefix, "")
        for m in REF_RX.finditer(text):
            raw, ref = m.group(1), m.group(1).rstrip("/.-")
            n += 1
            segs = ref.split("/")
            want = tops.get(segs[0].lower())
            if want is None:
                fails.append("%s 引用 %r，磁盘上没有这个顶层目录" % (rel, ref))
                continue
            if segs[0] != want:
                fails.append("%s 里 %r 的顶层目录大小写与磁盘不符（磁盘上是 %r）"
                             % (rel, ref, want))
                continue
            looks_like_path = "." in segs[-1] or raw.endswith("/")
            prose_list = all(s.lower() in tops for s in segs)   # 全是顶层目录名 = 散文并列
            if looks_like_path and not prose_list and not os.path.exists(os.path.join(ROOT, *segs)):
                fails.append("%s 引用 %r，路径不存在（断链）" % (rel, ref))
        for m in QUOTED_TOP_RX.finditer(text):
            tok = m.group(1)
            n += 1
            want = tops.get(tok.lower())
            if want is None:
                fails.append("%s 出现引号目录名 %r，磁盘上没有这个顶层目录" % (rel, tok))
            elif tok != want:
                fails.append("%s 里引号目录名 %r 与磁盘上的 %r 大小写不符" % (rel, tok, want))
    return fails, n


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
    if len(cases) < 8:
        # 只设下界不设上界：用例少说明覆盖面塌了；上界不属于质量判据，
        # 卡住它会让「再加一条用例」变成必须先改判据。
        fails.append("用例数 %d 少于 8 条，覆盖面已缩水" % len(cases))
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

    layout_fails, n_refs = check_layout()
    fails += layout_fails
    print("evals 路由核对：%d 条用例 · 引用路径 %d 个 · 核对长选项 %d 个"
          % (len(cases), len(checked_paths), len(checked_flags)))
    print("路径引用大小写核对：%d 处（顶层目录 %s）"
          % (n_refs, "/".join(sorted(disk_tops().values()))))
    for m in fails:
        print("FAIL", m)
    print("evals 路由判据：%d 项失败" % len(fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(run())
