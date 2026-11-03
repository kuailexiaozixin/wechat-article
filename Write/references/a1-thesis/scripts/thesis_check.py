# -*- coding: utf-8 -*-
"""A1 立意 · 研究性专业文章的立意骨架与形状校验（判不了思想，只判形状）。

子命令：
    init  [-o thesis.json]   写空白立意卡
    check <thesis.json>      六要素齐备性 + 结论具体性 + 边界与意义完整性

为什么要有这一步：研究性专业文章的失败几乎都发生在动笔之前——题目太大、
核心问题不是问题、结论是一句正确的废话。这三个毛病的共同点是「后面四步全靠它派生」，
等到 A5 才发现，A2 的结构、A3 的素材、A4 的逻辑图全部要推翻重做。
本脚本在源头把它们拦下来，判据口径见同目录 thesis-six-elements.md。

退出码：0 = 无 ERROR；1 = 有 ERROR；2 = 用法错误或文件不存在。
"""
import argparse
import io
import json
import os
import re
import sys

CATEGORIES = ("政策解读", "理论分析", "案例分析", "操作指引")
DISCIPLINES = ("财务", "税务", "法律", "金融", "经济")
MUST = ("title", "category", "discipline", "field", "object", "question",
        "purpose", "significance", "claim", "claim_boundary")

# 空洞评价词：没有证据的评价，研究性文章里出现即等于没下判断
HOLLOW = (
    "重要意义", "影响深远", "重要作用", "十分必要", "非常必要", "至关重要",
    "进一步加强", "不断完善", "持续优化", "有效提升", "高质量发展",
    "规范管理", "加强管理", "高度重视", "深入贯彻落实", "深刻影响",
    "具有指导意义", "提供了有益参考", "具有参考价值", "意义重大",
)

# 翻案腔：先立一个读者没有的误解再推翻抬价
PIVOT = (
    "不是", "并非", "不在于", "与其说", "表面", "看似", "你以为",
    "恰恰相反", "说到底", "回头才发现", "真正的问题", "真正的关键",
    "答案恰恰",
)

# 条件/范围标记：结论有边界才会出现这些词
BOUNDARY_WORDS = (
    "当", "时", "满足", "条件", "限于", "不适用", "除外", "区分",
    "前提", "仅", "若", "以下", "属于", "不属于",
)

# 意义里应能认出主体：研究性文章的意义天生是分配性的
SUBJECTS = {
    "企业": ("企业", "纳税人", "上市公司", "公司", "主体", "金融机构", "银行", "事务所"),
    "监管": ("监管", "征管", "税务机关", "主管部门", "执法", "审计", "证监", "银保监"),
    "投资者": ("投资者", "债权人", "股东", "出资人", "市场参与者", "报表使用者"),
    "行业": ("行业", "市场", "交易结构", "竞争", "产业链"),
    "规则": ("准则", "规则", "制度", "法条", "口径", "体系", "国际"),
}

TEMPLATE = {
    "title": "",
    "category": "政策解读",
    "discipline": "财务",
    "field": "写到二级学科或业务条线，如「财务会计领域」「增值税征管」",
    "object": "研究对象：一个可指认的名词短语，能补进「本文研究____」的句式",
    "question": "核心问题：一个问句，带限定条件（行业/交易/时点/主体）",
    "purpose": "读者读完能拿去做什么（写成动作，不写「加深理解」）",
    "significance": {
        "企业/纳税人": "合规成本、税负、报表结果、诉讼风险上得到什么",
        "监管/征管机关": "口径统一、执法一致性、征管效率上得到什么",
    },
    "claim": "研究结论：有区分标准、有科目/权利义务走向、有边界，不少于 40 字",
    "claim_boundary": "适用范围 + 例外情形 + 不确定性",
    "subclaims": [],
    "series": {"name": "", "index": 0},
}


def load(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return json.load(f), None
    except OSError:
        return None, "读不到文件：%s" % path
    except ValueError as e:
        return None, "不是合法 JSON：%s（%s）" % (path, e)


def cmd_init(args):
    text = json.dumps(TEMPLATE, ensure_ascii=False, indent=2)
    if args.out:
        with io.open(args.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
        print("模板已写入 %s" % args.out)
    else:
        print(text)
    return 0


def _sig_text(sig):
    """significance 允许写字符串或 {主体: 说明} 字典，统一成一段文本。"""
    if isinstance(sig, dict):
        return "\n".join("%s：%s" % (k, v) for k, v in sig.items())
    return sig if isinstance(sig, str) else ""


def check_card(d):
    fails, warns = [], []

    for k in MUST:
        v = d.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            fails.append("缺字段或为空：%s" % k)

    if d.get("category") and d["category"] not in CATEGORIES:
        fails.append("category 取值 %r 不在 %s 内" % (d["category"], "/".join(CATEGORIES)))
    if d.get("discipline") and d["discipline"] not in DISCIPLINES:
        fails.append("discipline 取值 %r 不在 %s 内" % (d["discipline"], "/".join(DISCIPLINES)))

    q = (d.get("question") or "").strip()
    if q and not re.search(r"(如何|怎么|怎样|是否|能否|应当|应由|应该|何以|为何|为什么|"
                           r"哪些|哪个|多少|哪一|几何)", q):
        fails.append("question 读不出问句形态：%s" % q)
    if q and q == (d.get("claim") or "").strip():
        fails.append("question 与 claim 逐字相同——问题与结论不能是一句话")

    claim = (d.get("claim") or "").strip()
    if claim:
        if len(claim) < 40:
            fails.append("claim 只有 %d 字——研究性文章的结论不能是一句话口号" % len(claim))
        hit = [w for w in HOLLOW if w in claim]
        if hit:
            fails.append("claim 命中空洞评价词：%s（换成区分标准、科目走向或后果）" % "、".join(hit))
        piv = [w for w in PIVOT if w in claim]
        if piv:
            fails.append("claim 命中翻案腔：%s（判断从正面下，依据放旁边）" % "、".join(piv))
        if not any(w in claim for w in BOUNDARY_WORDS):
            warns.append("claim 里看不到条件/范围标记——检查结论是不是漏了适用前提")

    obj = (d.get("object") or "").strip()
    if obj and len(obj) > 30:
        warns.append("object 有 %d 字——多半把一句话塞进了研究对象" % len(obj))

    cb = (d.get("claim_boundary") or "").strip()
    if cb and len(cb) < 15:
        fails.append("claim_boundary 太短（%d 字）：要写适用范围、例外、不确定性" % len(cb))

    sig = _sig_text(d.get("significance"))
    if sig:
        kinds = [k for k, words in SUBJECTS.items() if any(w in sig for w in words)]
        if len(kinds) < 2:
            fails.append("significance 只认出 %d 类主体（%s）——研究性文章的意义要落到至少两类主体"
                         % (len(kinds), "、".join(kinds) or "无"))

    subs = d.get("subclaims") or []
    if isinstance(subs, list) and len(subs) < 2:
        warns.append("subclaims 少于 2 个——分论点拆不开通常说明结论还不够具体")

    return fails, warns


def cmd_check(args):
    d, err = load(args.card)
    if err:
        print("ERR", err)
        return 2
    if not isinstance(d, dict):
        print("ERR 顶层必须是对象")
        return 2

    fails, warns = check_card(d)
    print("=== A1 立意核验：%s ===" % os.path.basename(args.card))
    for x in warns:
        print("  [WARN]", x)
    for x in fails:
        print("  [FAIL]", x)
    if fails:
        print("[FAIL] %d 项——立意没立住，不要进 A2：后面的结构、素材、逻辑图全从这里派生"
              % len(fails))
        return 1
    if warns:
        print("[PASS] 无 ERROR，但有 %d 项 WARNING 需要人工确认后再进 A2" % len(warns))
    else:
        print("[PASS] 六要素齐备，结论带判断与边界，可进 A2")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="A1 立意：研究性专业文章的立意卡骨架与形状校验",
        epilog="判据口径见同目录 thesis-six-elements.md")
    sub = ap.add_subparsers(dest="cmd")
    i = sub.add_parser("init", help="写空白立意卡")
    i.add_argument("-o", "--out", help="输出路径；省略则打印到标准输出")
    c = sub.add_parser("check", help="校验立意卡")
    c.add_argument("card", help="thesis.json 路径")
    args = ap.parse_args()
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "check":
        return cmd_check(args)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
