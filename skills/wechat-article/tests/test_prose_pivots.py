# -*- coding: utf-8 -*-
"""check_prose.py 翻案句与翻案腔变形的逐条命中测试（含反向对照）。

翻案句 = 硬禁令（退出码 1）；翻案腔变形 = 提示级（不改退出码）。
两套判据分别取样例：每条正则各一句命中样例，另配若干「不该报」的正常句，
防止变形层把日常陈述也吞掉——只验命中不验误报，判据就是虚的。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, os.pardir, "write", "scripts", "check_prose.py")

# PIVOT_PATTERNS 逐条对应（顺序与脚本内常量一致）
PIVOT_CASES = [
    ("不是…而是", "这不是样式问题，而是结构问题。"),
    ("并非…而是", "这并非工具不足，而是流程缺环。"),
    ("不在于…而在于", "关键不在于好看，而在于能否复核。"),
    ("与其说…不如", "与其说是审美判断，不如说是工程判断。"),
    ("句首而是", "校验已经通过。而是回读没有做。"),
    ("表面…其实", "表面上是标签被吃，其实是属性没有内联。"),
    ("看似…其实", "看似一步到位，其实漏了图数断言。"),
]

# SEMANTIC_PIVOT_PATTERNS 逐条对应
PIVOT_TONE_CASES = [
    ("以为…其实", "我以为校验过了就能发布，其实回读才是最后一道闸。"),
    ("总以为…但", "总以为封面是次要的事，但封面决定读者点不点进来。"),
    ("回头看才发现", "回头看才发现，问题出在图数断言上。"),
    ("不是，是", "这里不是脚本坏了，是归一化没做。"),
    ("从来都与…无关", "这套规矩从来都与审美无关。"),
    ("答案是否定的", "答案是否定的。"),
    ("跨句表面…其实", "表面看是标签被吃。其实是属性没写内联。"),
    ("跨句看似…其实", "看似一步到位。其实漏了图数断言。"),
    ("X不重要，要紧的是", "样式不重要，要紧的是结构能否复核。"),
    ("真正…的是", "真正要防的，是把校验当形式走过场。"),
    ("不只…还", "这不只在推送路径生效，粘贴路径也要照此处理。"),
]

# 反向对照：正常陈述不得被判翻案
NEGATIVE_CASES = [
    "这份稿子里出现了「不是」两个字，后面并没有跟着别的说法。",
    "他把草稿推上去以后才发现图片没有换成微信图床地址。",
    "真实的差异要在草稿箱回读以后才能看到。",
    "校验器会逐条打印命中的规则名称与出现次数。",
    "推送之前需要把归一化后的正文与源文件逐字比较。",
]


def run_case(text):
    p = subprocess.run([sys.executable, SCRIPT, "-"], input=text,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def run():
    fails = []

    for label, text in PIVOT_CASES:
        rc, out = run_case(text)
        if "禁用翻案句" not in out:
            fails.append("硬翻案未报「%s」：%s" % (label, out.strip().replace("\n", " ")[:120]))
        if rc != 1:
            fails.append("硬翻案退出码应为 1（%s）：实得 %d" % (label, rc))

    for label, text in PIVOT_TONE_CASES:
        rc, out = run_case(text)
        if "疑似翻案腔变形" not in out:
            fails.append("翻案腔变形未报「%s」：%s"
                         % (label, out.strip().replace("\n", " ")[:120]))

    for text in NEGATIVE_CASES:
        _, out = run_case(text)
        if "禁用翻案句" in out or "疑似翻案腔变形" in out:
            fails.append("正常陈述被误判翻案：%s → %s"
                         % (text[:20], out.strip().replace("\n", " ")[:140]))

    total = len(PIVOT_CASES) + len(PIVOT_TONE_CASES) + len(NEGATIVE_CASES)
    print("check_prose 翻案判据：%d 例（硬翻案 %d + 变形 %d + 反向 %d），%d 项失败"
          % (total, len(PIVOT_CASES), len(PIVOT_TONE_CASES), len(NEGATIVE_CASES), len(fails)))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
