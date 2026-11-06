# -*- coding: utf-8 -*-
"""B1 figure_plan.py 判据测试：分层配图需求校验 + from-ledger 展开。

只覆盖确定性判据（脚本能拦的），不覆盖 AI 读台账的判断本身。
"""
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
SCRIPT = os.path.join(ROOT, "Write", "references", "b1-images", "scripts", "figure_plan.py")


def run_script(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "")


def dump(path, obj):
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=1))


def good_reqs():
    return {"topic": "护盘式回购", "requirements": [
        {"id": "r1", "layer": "L1架构", "figure_type": "架构总览图",
         "trigger": "6 章分论点交叉支撑，架构复杂需总览", "tool": "mermaid",
         "filename": "arch_overview.png"},
        {"id": "r2", "layer": "L4法条", "figure_type": "法条拆解卡",
         "trigger": "论证边引用公司法142条，拆解要件", "tool": "screenshot",
         "filename": "statute_142.png", "text_in_image": "第142条 6 款",
         "labels_traceable": True,
         "source_basis": "台账 L4 论证边 backing=公司法142"},
        {"id": "r3", "layer": "封面", "figure_type": "封面",
         "trigger": "每篇必配", "tool": "cover", "filename": "cover.png"},
    ]}


def run():
    fails = []
    tmp = tempfile.mkdtemp(prefix="wxfigplan-")

    # 正向：合法需求清单 → check 0
    fp = os.path.join(tmp, "req.json")
    dump(fp, good_reqs())
    code, out = run_script("check", fp)
    if code != 0:
        fails.append("合法需求清单应 check 通过（exit 0），实际 %d：%s" % (code, out[:200]))

    # 正向：from-ledger 展开成 manifest（3 条）
    mp = os.path.join(tmp, "manifest.json")
    code, out = run_script("from-ledger", fp, "-o", mp)
    if code != 0 or not os.path.isfile(mp):
        fails.append("from-ledger 应生成 manifest（exit 0），实际 %d：%s" % (code, out[:200]))
    else:
        m = json.load(io.open(mp, encoding="utf-8"))
        if len(m.get("figures") or []) != 3:
            fails.append("from-ledger 应展开 3 条目，实际 %d" % len(m.get("figures") or []))
        tools = {f["_from_layer"]: f["tool"] for f in m.get("figures") or []}
        if tools.get("L4法条") != "screenshot":
            fails.append("L4法条层 tool 应为 screenshot（法条走 gen_table），实际 %s"
                         % tools.get("L4法条"))

    # 反向：层级↔图形式错配（法条层配 mermaid 思维导图）应被拦
    bad = good_reqs()
    bad["requirements"][1]["tool"] = "mermaid"  # L4法条 允许 screenshot/mermaid，改个更硬的
    bad["requirements"][1]["layer"] = "数据"      # 数据层只许 screenshot，配 mermaid → 错配
    badp = os.path.join(tmp, "req-bad.json")
    dump(badp, bad)
    code, out = run_script("check", badp)
    if code != 1 or "错配" not in out:
        fails.append("数据层配 mermaid 应判层级错配 FAIL，实际 %d：%s" % (code, out[:200]))

    # 反向：trigger 写「更直观」应被拦
    lazy = good_reqs()
    lazy["requirements"][0]["trigger"] = "更直观"
    lazy2 = os.path.join(tmp, "req-lazy.json")
    dump(lazy2, lazy)
    code, out = run_script("check", lazy2)
    if code != 1 or "判据" not in out:
        fails.append("trigger 写『更直观』应被拦（说不清为何配），实际 %d：%s" % (code, out[:200]))

    if fails:
        print("B1 分层配图需求判据：%d 项失败" % len(fails))
        for f in fails:
            print("FAIL", f)
        return 1
    print("B1 分层配图需求判据（figure_plan）：全部通过（正向 check/from-ledger + 反向错配/懒判据）")
    return 0


if __name__ == "__main__":
    sys.exit(run())
