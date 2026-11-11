# -*- coding: utf-8 -*-
"""B1 图注闸 + 禁词表单点维护的可证伪核对。

A 轨的 references 三个目录（a1-thesis / a2-materials / a3-logic）已移除：写作纪律的机器可验证部分
单点收归 `Write/references/b3-acceptance/scripts/validate_wx_html.py` 的 BANNED_WORDS /
AI_FLAVOR_PHRASES / PROCESS_TRACE_RULES（全仓唯一一份）。本文件因此只核两件事：

  - validate_wx_html 仍持有制作痕迹与 AI 味词表，且 check_captions 侧的同名词仍在
    （两侧一起被削掉 = 写作纪律与图注纪律同时失效，这里报红）；
  - check_captions 对内部坐标图注 FAIL、对内容性图注 PASS（B1 出口闸既不漏拦也不误伤）。

只测正向等于没测：内部坐标那一组是负例，内容性图注那一组是反向对照。
"""
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
W = os.path.join(ROOT, "Write", "references")
VALIDATE = os.path.join(W, "b3-acceptance", "scripts", "validate_wx_html.py")
CAPTIONS = os.path.join(W, "b1-images", "scripts", "check_captions.py")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _run(script, args):
    return subprocess.run([sys.executable, script] + args,
                          capture_output=True, text=True, encoding="utf-8",
                          env=dict(os.environ, PYTHONUTF8="1"))


def run():
    fails = []

    # 1. 词表仍在（制作痕迹核心词 + AI 味词表 + 被动/过程规则）
    if not os.path.isfile(VALIDATE):
        return ["validate_wx_html.py 不存在：%s" % VALIDATE]
    vw = _load("_vw_gate", VALIDATE)
    core = ("全文", "稿件", "对应台账", "结尾交代", "下面按", "标注推断")
    for word in core:
        if word not in vw.BANNED_WORDS:
            fails.append("validate_wx_html.BANNED_WORDS 缺制作痕迹词 %r" % word)
    if not getattr(vw, "AI_FLAVOR_PHRASES", ()):
        fails.append("validate_wx_html 缺 AI_FLAVOR_PHRASES（空洞修辞无判据）")
    if not getattr(vw, "PROCESS_TRACE_RULES", ()):
        fails.append("validate_wx_html 缺 PROCESS_TRACE_RULES")

    # 2. check_captions：内部坐标 FAIL，内容性图注 PASS
    if not os.path.isfile(CAPTIONS):
        return fails + ["check_captions.py 不存在：%s" % CAPTIONS]
    d = tempfile.mkdtemp(prefix="cap_gate_")
    bad_manifest = os.path.join(d, "manifest.json")
    io.open(bad_manifest, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"figures": [{"id": "f1", "caption": "图 1 三次操作对照（对应第二节段4）"}]},
                   ensure_ascii=False))
    r = _run(CAPTIONS, ["--manifest", bad_manifest])
    if r.returncode == 0:
        fails.append("图注含内部坐标未判 FAIL")
    good_manifest = os.path.join(d, "good.json")
    io.open(good_manifest, "w", encoding="utf-8", newline="\n").write(
        json.dumps({"figures": [{"id": "f1", "caption": "图 1 三次操作金额与中标费率对照"}]},
                   ensure_ascii=False))
    r = _run(CAPTIONS, ["--manifest", good_manifest])
    if r.returncode != 0:
        fails.append("内容性图注被误判：%s" % (r.stdout or "")[:200])

    print("B1 图注闸 + 禁词表单点：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
