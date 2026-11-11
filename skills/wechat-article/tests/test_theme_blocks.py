# -*- coding: utf-8 -*-
"""theme-default 组件样张与 build_blocks 模板的逐字一致性测试。

两件事：
1. 全组件通过样张：把 Write/references/b2-typeset/theme-default.md 里每个 ```html 代码块
   逐字拼起来送 validate_wx_html.validate()，ERROR 必须为零——参考文档自身
   写进不合规样式时，这里立刻报红。
2. 模板一致：build_blocks.DEMO 每个组件渲染结果必须与 md 对应代码块逐字节相等。
   改 md 不改脚本会红，改脚本不改 md 也会红（样式单一来源不因生成器漂移）。
"""
import importlib.util
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MD = os.path.join(ROOT, "Write", "references", "b2-typeset", "theme-default.md")


def _load(name, relpath):
    path = os.path.join(ROOT, relpath)
    sys.path.insert(0, os.path.dirname(path))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SECTION_RX = re.compile(r"^### (\d+)\. (.+)$", re.M)
BLOCK_RX = re.compile(r"```html\n(.*?)```", re.S)


def md_sections():
    """→ [(序号, 标题, 代码块内容)]，代码块取该小节内第一个 ```html 围栏。"""
    text = open(MD, encoding="utf-8").read()
    heads = [(int(m.group(1)), m.group(2), m.start()) for m in SECTION_RX.finditer(text)]
    out = []
    for i, (num, title, start) in enumerate(heads):
        end = heads[i + 1][2] if i + 1 < len(heads) else len(text)
        body = text[start:end]
        m = BLOCK_RX.search(body)
        out.append((num, title, m.group(1).rstrip("\n") if m else None))
    return out


def run():
    v = _load("validate_wx_html", os.path.join("Write", "references", "b3-acceptance",
                                             "scripts", "validate_wx_html.py"))
    B = _load("build_blocks", os.path.join("Write", "references", "b2-typeset",
                                         "scripts", "build_blocks.py"))
    fails = []

    secs = md_sections()
    if not secs:
        fails.append("b2-typeset/theme-default.md 未解析到「### N. 组件名」小节：文档结构已变，本测试需同步")
        print("theme-default 一致性：%d 项失败" % len(fails))
        for f in fails:
            print("   FAIL", f)
        return fails

    missing = ["%d. %s" % (n, t) for n, t, blk in secs if blk is None]
    if missing:
        fails.append("组件小节缺 ```html 代码块：%s" % "、".join(missing))

    with_blocks = [(n, t, blk) for n, t, blk in secs if blk]
    if len(with_blocks) != len(B.DEMO):
        fails.append("md 组件数 %d 与 build_blocks.DEMO 组件数 %d 不等（新增/删除组件须同步）"
                     % (len(with_blocks), len(B.DEMO)))

    joined = "\n".join(blk for _, _, blk in with_blocks) + "\n"
    errors, warnings, checker = v.validate(joined)
    if errors:
        fails.append("theme-default 全组件样张被判定不合规（ERROR 应清零）：%s" % errors)
    print("全组件样张: %d 个组件 · img×%d p×%d section×%d · ERROR×%d WARNING×%d"
          % (len(with_blocks), checker.n_img, checker.n_p, checker.n_section,
             len(errors), len(warnings)))
    for w in warnings:
        print("   WARN", w)

    for (num, title, blk), demo in zip(with_blocks, B.DEMO):
        got = B.render([demo]).rstrip("\n")
        if got != blk:
            fails.append("组件 %d「%s」(type=%s) 与脚本模板不一致：\n     md  = %r\n     脚本 = %r"
                         % (num, title, demo["type"], blk, got))

    # 生成器不接受自定义样式：漂移只能发生在 md 或模板两处，二者都已被上面拦住
    if "style" in json_keys(B.DEMO):
        fails.append("DEMO 块里出现了 style 参数，样式应由脚本单一持有")

    # 设计变量表（色值）与 build_blocks.V 一致性（表漂移也能被抓住）
    fv = check_design_vars(B)
    if fv:
        print("设计变量一致性：%d 项失败" % len(fv))
    else:
        print("设计变量一致性：表色值与 build_blocks.V 一致（%d 个变量）" % len(B.V))
    fails += fv

    print("theme-default 一致性：%d 个组件逐字比对，%d 项失败" % (len(with_blocks), len(fails)))
    for f in fails:
        print("   FAIL", f)
    return fails


def json_keys(demo_list):
    keys = set()
    for d in demo_list:
        keys.update(d)
    return keys


def check_design_vars(B):
    """设计变量表（theme-default.md「设计变量」节）的色值须与 build_blocks.V 一一对应。

    组件样张的逐字比对间接覆盖了用到的颜色，但「表里写了、组件没用」或「V 里改了、表没更新」
    这类漂移抓不到——本项把表本身也纳入一致性核对。
    """
    text = open(MD, encoding="utf-8").read()
    m = re.search(r"## 设计变量[^\n]*\n(.*?)(?=\n## |\Z)", text, re.S)
    if not m:
        return ["theme-default.md 未解析到「## 设计变量」节（表结构已变，本检查需同步）"]
    table_hex = set(re.findall(r"#[0-9A-Fa-f]{6}", m.group(1)))
    v_hex = set()
    for v in B.V.values():
        v_hex |= set(re.findall(r"#[0-9A-Fa-f]{6}", str(v)))
    fails = []
    if table_hex - v_hex:
        fails.append("设计变量表有 build_blocks.V 没有的色值：%s" % sorted(table_hex - v_hex))
    if v_hex - table_hex:
        fails.append("build_blocks.V 有色值未在设计变量表登记：%s" % sorted(v_hex - table_hex))
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
