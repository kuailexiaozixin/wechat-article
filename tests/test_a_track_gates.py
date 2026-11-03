# -*- coding: utf-8 -*-
"""A 轨道五阶段判据的逐条命中测试（正向通过 + 反向拦截），以及三处词表一致性核对。

为什么单独成一支：A1-A4 是「形状校验」，它的价值全在「该拦的拦得住、该放的行得过」。
只测正向等于没测——一个永远返回 PASS 的脚本也能通过正向用例。

运行：python tests/test_a_track_gates.py
返回：失败说明列表（空 = 通过）。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))

A1 = os.path.join(ROOT, "Write", "references", "a1-thesis", "scripts", "thesis_check.py")
A2 = os.path.join(ROOT, "Write", "references", "a2-structure", "scripts", "outline_check.py")
A3 = os.path.join(ROOT, "Write", "references", "a3-materials", "scripts", "material_ledger.py")
A4 = os.path.join(ROOT, "Write", "references", "a4-logic", "scripts", "logic_graph.py")

THESIS = {
    "title": "研发过程形成产品对外销售的会计处理",
    "category": "政策解读",
    "discipline": "财务",
    "field": "财务会计领域",
    "object": "研发过程中形成产品对外销售的会计处理",
    "question": "研发过程中形成的样品、样机对外销售时，相关支出应如何确认与结转？",
    "purpose": "让财务人员按阶段划分与资本化条件，把研发支出记进正确科目并完成结转",
    "significance": {
        "企业/纳税人": "弄清费用化与资本化的分界，避免报表错报与纳税调整风险",
        "监管/征管机关": "统一口径，减少同类交易的处理分歧与稽查争议",
    },
    "claim": ("研究开发项目支出须区分研究阶段与开发阶段：研究阶段支出于发生时计入研发支出费用化支出；"
              "开发阶段支出不满足资本化条件的计入费用化支出，满足资本化条件的计入研发支出资本化支出。"
              "期末费用化支出转入研发费用，资本化支出转入开发支出；形成无形资产的从开发支出结转无形资产。"),
    "claim_boundary": "适用于执行企业会计准则的一般工商企业；不适用于政府补助为主的研发项目；样机是否满足资产确认条件存在判断空间",
    "subclaims": [
        {"id": "s1", "text": "阶段划分决定费用化与资本化的起点"},
        {"id": "s2", "text": "样机样品满足资产确认条件时按对应支出结转"},
        {"id": "s3", "text": "期末科目结转路径固定"},
    ],
    "series": {"name": "", "index": 0},
}

OUTLINE = {
    "thesis_ref": "thesis.json",
    "method": "problem-solution",
    "flow": "递进式",
    "word_budget": 1200,
    "sections": [
        {"id": "s1", "heading": "准则把研发过程切成研究与开发两段", "claim_ref": "s1",
         "role": "条文及适用范围", "words": 400, "evidence_kinds": ["准则原文"]},
        {"id": "s2", "heading": "样机样品结转资产的三道门槛", "claim_ref": "s2",
         "role": "分析", "words": 500, "evidence_kinds": ["准则原文"]},
        {"id": "s3", "heading": "期末科目结转与报表列示", "claim_ref": "s3",
         "role": "结论", "words": 300, "evidence_kinds": ["应用指南"]},
    ],
    "relations": [
        {"from": "s1", "to": "s2", "type": "递进", "note": "定了阶段才谈得上资本化"},
        {"from": "s2", "to": "s3", "type": "回扣主线", "note": "回到核心问题：怎么结转"},
    ],
}


def exec_script(script, *args):
    p = subprocess.run([sys.executable, script] + list(args),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def dump(path, obj):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(obj, ensure_ascii=False, indent=2))


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def build_materials(target=1200):
    items = []
    srcs = [("s1", "研究阶段支出费用化", "《企业会计准则第6号》第八条", "一手事实",
             "研究阶段的支出，于发生时计入当期损益"),
            ("s1", "开发阶段支出区分资本化", "《企业会计准则第6号》第九条", "一手事实",
             "开发阶段的支出同时满足条件的才能确认为无形资产"),
            ("s2", "样机满足资产确认条件", "《企业会计准则第1号》第四条", "一手事实", ""),
            ("s2", "样机转固的判断", "《企业会计准则第4号》第三条", "一手事实", ""),
            ("s3", "期末结转路径", "《应用指南》会计科目", "一手事实", ""),
            ("s3", "报表列示位置", "《企业会计准则第30号》", "一手事实", "")]
    for i, (sec, claim, src, st, quote) in enumerate(srcs, 1):
        items.append({"id": "m%02d" % i, "section": sec, "claim": claim, "quote": quote,
                      "source": src, "source_type": st, "locator": "",
                      "verified_at": "2026-11-03", "status": "done", "note": ""})
    return {"thesis_ref": "thesis.json", "outline_ref": "outline.json",
            "target_words": target, "items": items}


def build_logic(mat):
    nodes, edges = [], []
    for s in OUTLINE["sections"]:
        nodes.append({"id": "n_%s" % s["id"], "kind": "section", "ref": s["id"],
                      "text": s["heading"]})
    for sc in THESIS["subclaims"]:
        nodes.append({"id": "n_c_%s" % sc["id"], "kind": "claim", "ref": sc["id"],
                      "text": sc["text"]})
    sec_claim = {s["id"]: s["claim_ref"] for s in OUTLINE["sections"]}
    for m in mat["items"]:
        nodes.append({"id": "n_%s" % m["id"], "kind": "evidence", "ref": m["id"],
                      "text": m["claim"]})
        edges.append({"from": "n_%s" % m["id"], "to": "n_c_%s" % sec_claim[m["section"]],
                      "type": "论证", "rel": "证据",
                      "warrant": "条文的适用范围与本节主张逐项对应，故主张成立",
                      "backing": "", "rebuttal": ""})
    for s in OUTLINE["sections"]:
        edges.append({"from": "n_c_%s" % s["claim_ref"], "to": "n_%s" % s["id"],
                      "type": "结构", "rel": "依赖", "note": "分论点靠这一节立住"})
    return {
        "thesis_ref": "thesis.json", "outline_ref": "outline.json",
        "materials_ref": "materials.json", "series": {"name": "", "index": 0},
        "terms": [{"term": "开发支出", "canonical": "开发支出", "aliases_ok": [],
                   "banned": ["开发费用"], "definition": "开发阶段资本化支出的归集科目"}],
        "nodes": nodes, "edges": edges,
        "statements": ["研发阶段的支出于发生时计入当期损益。",
                       "样机满足资产确认条件的按对应支出结转。",
                       "期末开发支出在资产负债表单独列示。"],
        "series_links": [],
    }


def main():
    fails = []
    tmp = tempfile.mkdtemp(prefix="a-track-")
    try:
        f_thesis = os.path.join(tmp, "thesis.json")
        f_outline = os.path.join(tmp, "outline.json")
        f_mat = os.path.join(tmp, "materials.json")
        f_logic = os.path.join(tmp, "logic.json")
        dump(f_thesis, THESIS)
        dump(f_outline, OUTLINE)
        mat = build_materials()
        dump(f_mat, mat)
        dump(f_logic, build_logic(mat))

        # ---------- 正向：四个阶段全过 ----------
        for name, script, args in [
            ("A1 正向", A1, ["check", f_thesis]),
            ("A2 正向", A2, ["check", f_outline, "--thesis", f_thesis]),
            ("A3 正向", A3, ["check", f_mat, "--outline", f_outline]),
            ("A4 正向", A4, ["check", f_logic, "--materials", f_mat]),
        ]:
            code, out = exec_script(script, *args)
            if code != 0:
                fails.append("%s 应通过却退出码 %d：%s" % (name, code, out.strip()[:300]))

        # ---------- 反向：A1 空模板 / 空泛结论 ----------
        code, _ = exec_script(A1, "init", "-o", f_thesis + ".empty")
        if code != 0:
            fails.append("A1 init 应成功")
        code, _ = exec_script(A1, "check", f_thesis + ".empty")
        if code != 1:
            fails.append("A1 空模板应报 ERROR（退出码 1），实际 %d" % code)

        bad = dict(THESIS)
        bad["claim"] = "企业应当进一步加强研发支出的规范管理与监督"
        dump(f_thesis + ".bad", bad)
        code, out = exec_script(A1, "check", f_thesis + ".bad")
        if code != 1 or "空洞评价词" not in out:
            fails.append("A1 空泛结论（规范管理/加强）应被拦，实际 %d" % code)

        bad = dict(THESIS)
        bad["claim"] = "真正的问题不是条文，而是执行条文的人，这是一句足够长但是翻案的结论表述"
        dump(f_thesis + ".pivot", bad)
        code, out = exec_script(A1, "check", f_thesis + ".pivot")
        if code != 1 or "翻案腔" not in out:
            fails.append("A1 翻案腔结论应被拦，实际 %d" % code)

        bad = dict(THESIS)
        bad["question"] = "研发支出的会计处理"
        dump(f_thesis + ".q", bad)
        code, _ = exec_script(A1, "check", f_thesis + ".q")
        if code != 1:
            fails.append("A1 核心问题写成陈述句应被拦，实际 %d" % code)

        # ---------- 反向：A2 结构 ----------
        bad = dict(OUTLINE)
        bad["sections"] = [dict(x) for x in OUTLINE["sections"]]
        bad["sections"][0]["claim_ref"] = "s9"
        dump(f_outline + ".ref", bad)
        code, out = exec_script(A2, "check", f_outline + ".ref", "--thesis", f_thesis)
        if code != 1 or "subclaims" not in out:
            fails.append("A2 claim_ref 指空应被拦，实际 %d" % code)

        bad = dict(OUTLINE)
        bad["sections"] = [dict(x) for x in OUTLINE["sections"]]
        bad["sections"][1]["heading"] = "抽丝剥茧之道"
        dump(f_outline + ".h", bad)
        code, out = exec_script(A2, "check", f_outline + ".h")
        if code != 1 or "对仗" not in out:
            fails.append("A2 对仗小标题应被拦，实际 %d" % code)

        bad = dict(OUTLINE)
        bad["relations"] = [{"from": "s1", "to": "s2", "type": "递进", "note": ""}]
        dump(f_outline + ".n", bad)
        code, out = exec_script(A2, "check", f_outline + ".n")
        if code != 1 or "note" not in out:
            fails.append("A2 空的交接说明应被拦，实际 %d" % code)

        bad = dict(OUTLINE)
        bad["sections"] = [dict(x) for x in OUTLINE["sections"]]
        bad["sections"][0]["words"] = 5000
        dump(f_outline + ".w", bad)
        code, out = exec_script(A2, "check", f_outline + ".w")
        if code != 1 or "偏差" not in out:
            fails.append("A2 字数预算失配应被拦，实际 %d" % code)

        # ---------- 反向：A3 素材 ----------
        bad = build_materials()
        bad["items"][0]["status"] = "pending"
        dump(f_mat + ".p", bad)
        code, out = exec_script(A3, "check", f_mat + ".p", "--outline", f_outline)
        if code != 1 or "pending" not in out:
            fails.append("A3 pending 台账应被拦，实际 %d" % code)

        bad = build_materials()
        bad["items"][0]["source_type"] = "未核实"
        dump(f_mat + ".u", bad)
        code, _ = exec_script(A3, "check", f_mat + ".u", "--outline", f_outline)
        if code != 1:
            fails.append("A3 未核实材料应被拦，实际 %d" % code)

        bad = build_materials()
        for it in bad["items"]:
            it["source_type"] = "作者推断"
        dump(f_mat + ".i", bad)
        code, out = exec_script(A3, "check", f_mat + ".i", "--outline", f_outline)
        if code != 1 or "一手事实" not in out:
            fails.append("A3 全篇无一手事实应被拦，实际 %d" % code)

        bad = build_materials(target=3000)   # 6 条 < 3000/240=13 条
        dump(f_mat + ".short", bad)
        code, out = exec_script(A3, "check", f_mat + ".short", "--outline", f_outline)
        if code != 1 or "材料" not in out:
            fails.append("A3 材料数不足门槛应被拦，实际 %d" % code)

        # ---------- 反向：A4 四类查询 ----------
        bad = build_logic(mat)
        bad["edges"][0]["warrant"] = ""
        dump(f_logic + ".w", bad)
        code, out = exec_script(A4, "check", f_logic + ".w", "--materials", f_mat)
        if code != 1 or "warrant" not in out:
            fails.append("A4 空 warrant 应被拦，实际 %d" % code)

        bad = build_logic(mat)
        bad["statements"][0] = "研发阶段的开发费用应当资本化。"
        dump(f_logic + ".t", bad)
        code, out = exec_script(A4, "check", f_logic + ".t", "--materials", f_mat)
        if code != 1 or "术语" not in out:
            fails.append("A4 术语漂移应被拦，实际 %d" % code)

        bad = build_logic(mat)
        bad["series"] = {"name": "研发支出会计处理", "index": 2}
        bad["series_links"] = [{"target": "资本化时点", "type": "支撑", "conflict": True}]
        dump(f_logic + ".s", bad)
        code, out = exec_script(A4, "check", f_logic + ".s", "--materials", f_mat)
        if code != 1 or "支撑" not in out:
            fails.append("A4 系列冲突未标 rebuttal 应被拦，实际 %d" % code)

        # 孤证章节：把 s2 的材料边全删掉
        bad = build_logic(mat)
        s2_ids = {"n_%s" % m["id"] for m in mat["items"] if m["section"] == "s2"}
        bad["edges"] = [e for e in bad["edges"] if e["from"] not in s2_ids]
        dump(f_logic + ".o", bad)
        code, out = exec_script(A4, "check", f_logic + ".o", "--materials", f_mat)
        if code != 1 or "n_s2" not in out:
            fails.append("A4 孤证章节（本节材料未进图）应被拦，实际 %d" % code)

        # ---------- 词表一致性：三处关键条目必须一致 ----------
        probe = os.path.join(ROOT, "Write", "references", "a5-draft", "scripts",
                             "check_prose.py")
        vwx = os.path.join(ROOT, "Write", "references", "b3-acceptance", "scripts",
                           "validate_wx_html.py")
        s1 = io.open(probe, encoding="utf-8").read()
        s2 = io.open(vwx, encoding="utf-8").read()
        # 两处词表是分层而非同一份：check_prose 管散文硬禁令（含黑话全集），
        # validate 管微信侧禁用词 + AI 味启发式。真正的要求是「重叠部分必须一致、
        # 且都存在」，不是逐词相同——否则两处会被强行绑成一份，反而失去分层。
        for word in ("赋能", "抓手", "闭环"):
            if word not in s1:
                fails.append("check_prose.py 词表缺 %r（该词在两处都应存在）" % word)
            if word not in s2:
                fails.append("validate_wx_html.py 词表缺 %r（该词在两处都应存在）" % word)

        # 文档与脚本的词表维护指针必须指向真实文件
        for doc in ("Write/references/a5-draft/revision-protocol.md",
                    "Write/references/a5-draft/de-ai-playbook.md"):
            text = io.open(os.path.join(ROOT, doc), encoding="utf-8").read()
            if "词表" not in text:
                fails.append("%s 缺词表维护段落" % doc)

        # 旧文档与旧目录不得再被引用（CHANGELOG 的历史条目除外）
        stale = ("writing-discipline.md", "human-writing-nonfiction.md",
                 "de-ai-measures.md", "b3-validate/", "b4-render/", "b5-manual/",
                 "b6-push/", "b7-readback/")
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__", "node_modules")]
            for fn in filenames:
                if not fn.endswith((".md", ".py", ".json")):
                    continue
                rel = os.path.relpath(os.path.join(dirpath, fn), ROOT).replace(os.sep, "/")
                if rel in ("CHANGELOG.md", "tests/test_a_track_gates.py"):
                    continue   # 历史条目记当时的路径；本文件是判据本身，词表字符串是数据
                body = io.open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
                for token in stale:
                    if token in body:
                        fails.append("%s 仍引用已废弃的 %s" % (rel, token))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run():
    """run_all.py 的入口：返回失败说明列表（空 = 通过）。"""
    return main()


if __name__ == "__main__":
    f = run()
    if f:
        print("A 轨道判据：%d 项失败" % len(f))
        for x in f:
            print("  -", x)
        sys.exit(1)
    print("A 轨道判据：全部通过（A1-A4 正向 4 例 + 反向 15 例 + 词表与废弃引用核对）")
