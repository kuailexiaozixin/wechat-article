# -*- coding: utf-8 -*-
"""qa_mobile.py 渲染验收判据测试（起真实浏览器，无浏览器时跳过并说明）。

方向性断言：伪表格样本必须报红（display:table* 在微信手机端堆叠成纯文本，
与宽度无关）；条目卡片样本必须通过；超宽样本必须报横向溢出。
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


def _load():
    path = os.path.join(HERE, os.pardir, "write", "scripts", "qa_mobile.py")
    sys.path.insert(0, os.path.join(HERE, os.pardir, "write", "scripts"))
    spec = importlib.util.spec_from_file_location("qa_mobile", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    try:
        import playwright  # noqa: F401
    except ImportError:
        print("qa_mobile 渲染验收：跳过（未安装 playwright，pip install playwright）")
        return []
    Q = _load()
    fails = []

    r = Q.qa(os.path.join(FIX, "wx_pseudo_table.html"), 390,
             screenshot=os.path.join(FIX, "_tmp_pseudo.png"), image_check=False)
    if r["ok"]:
        fails.append("div+display:table 伪表格样本被判通过（这杆旗失效）：%s" % r["errors"])
    elif not any("display:table" in e for e in r["errors"]):
        fails.append("伪表格样本报红但未指出伪表格：%s" % r["errors"])

    r2 = Q.qa(os.path.join(FIX, "wx_card_layout.html"), 390,
              screenshot=os.path.join(FIX, "_tmp_card.png"), image_check=False)
    if not r2["ok"]:
        fails.append("条目卡片样本被误判：%s" % r2["errors"])

    r3 = Q.qa(os.path.join(FIX, "wx_overflow.html"), 390,
              screenshot=os.path.join(FIX, "_tmp_over.png"), image_check=False)
    if r3["ok"] or "横向溢出" not in " ".join(r3["errors"]):
        fails.append("760px 固定宽元素未报横向溢出：%s" % r3["errors"])

    for name in ("_tmp_pseudo.png", "_tmp_card.png", "_tmp_over.png"):
        p = os.path.join(FIX, name)
        if os.path.exists(p):
            os.remove(p)

    print("qa_mobile 渲染验收：%d 项失败（浏览器: %s）" % (len(fails), r.get("browser", "-")))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
