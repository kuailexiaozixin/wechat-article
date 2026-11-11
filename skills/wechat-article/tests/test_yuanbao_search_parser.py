# -*- coding: utf-8 -*-
"""元宝搜索（so.qq.com 公众号频道）解析器的离线判据（不联网，用真实页面样本）。

运行: python tests/test_yuanbao_search_parser.py
全量: python tests/run_all.py     # 本文件按仓库约定暴露 run()

样本: tests/fixtures/yuanbao_weixin_article_sample.html
      （来自 https://so.qq.com/isearch?tab=weixin_article&query=微信 的真实返回，2026-11-11）

除解析结果外还守两条「代码/文档不漂移」的契约：
  1. Search/SKILL.md 元宝通道示例里出现的每个长参数，脚本必须真的定义了
     （曾出现文档写 --pages 2 而脚本没定义、实跑 argparse 直接报错的事）；
  2. --pages 被忽略时必须给出 NOTE，且 -n 口径与单页上限一致。
"""
import io
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
sys.path.insert(0, os.path.join(ROOT, "Search", "scripts"))

import yuanbao_search as yb  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "yuanbao_weixin_article_sample.html")
YB_SRC = os.path.join(ROOT, "Search", "scripts", "yuanbao_search.py")
SEARCH_SKILL = os.path.join(ROOT, "Search", "SKILL.md")


def _read(path):
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _yuanbao_doc_section(text):
    """只取「零、元宝搜索通道」那一节，避免把下面搜狗通道的参数混进来。"""
    start = text.find("## 零、元宝搜索通道")
    if start < 0:
        return ""
    nxt = text.find("\n## ", start + 5)
    return text[start:(nxt if nxt > 0 else len(text))]


def run():
    fails = []

    def ck(name, cond, detail=""):
        if cond:
            print("  [PASS] %s" % name)
        else:
            fails.append("%s %s" % (name, detail))
            print("  [FAIL] %s  %s" % (name, detail))

    # ---------- 一、真实页面样本解析 ----------
    html_text = _read(FIXTURE)
    items, note = yb.parse_results(html_text)
    print("解析注记: %s" % note)
    print("解析到条目数: %d" % len(items))

    ck("解析到至少 1 条结果", len(items) >= 1, "实际 %d" % len(items))
    ck("解析到接近单页上限(>=8)", len(items) >= 8, "实际 %d" % len(items))

    with_link = [it for it in items if it.get("resolved")]
    ck("多数条目含永久 mp.weixin 直链", len(with_link) >= 8,
       "含直链 %d / 共 %d" % (len(with_link), len(items)))

    for it in with_link[:3]:
        ck("直链主机为 mp.weixin.qq.com", "mp.weixin.qq.com" in it["resolved"],
           it.get("resolved"))
        ck("直链含 __biz（永久文章标识）", "__biz=" in it["resolved"], it.get("resolved"))
        ck("标题非空", bool(it["title"]), repr(it.get("title")))
        ck("resolve_via 标记为 yuanbao-permanent",
           it["resolve_via"] == "yuanbao-permanent", it.get("resolve_via"))
        ck("link 与 resolved 相同（免 -r 还原）", it["link"] == it["resolved"],
           "%s vs %s" % (it["link"], it["resolved"]))

    with_account = [it for it in items if it.get("account")]
    ck("多数条目能抽到公众号名", len(with_account) >= 5,
       "含公众号名 %d / 共 %d" % (len(with_account), len(items)))

    # 相对时间解析（用固定 now 做确定性断言）
    now = time.mktime((2026, 11, 11, 18, 0, 0, 0, 0, -1))
    ck("「1天前」可折算为时间戳", yb.to_epoch("1天前", now) is not None)
    ck("「3小时前」可折算为时间戳", yb.to_epoch("3小时前", now) is not None)
    ck("绝对日期 2026-11-01 可解析", yb.to_epoch("2026-11-01", now) is not None)
    ck("「刚刚」折算为当前时刻附近",
       abs((yb.to_epoch("刚刚", now) or 0) - now) < 5)
    ck("「1天前」比「1小时前」更旧",
       yb.to_epoch("1天前", now) < yb.to_epoch("1小时前", now))
    ck("无法识别的时间返回 None", yb.to_epoch("不是时间", now) is None)

    # 链接主机白名单：非 mp.weixin 的链接必须被丢弃
    ck("safe_mp_link 拒绝外域链接", yb.safe_mp_link("https://evil.example/x") == "")
    ck("safe_mp_link 拒绝子串伪装 mp.weixin.qq.com.evil.example",
       yb.safe_mp_link("https://mp.weixin.qq.com.evil.example/s?x=1") == "")
    ck("safe_mp_link 放行 mp.weixin 直链",
       yb.safe_mp_link("http://mp.weixin.qq.com/s?__biz=1") != "")
    ck("safe_mp_link 拒绝带端口的 mp.weixin",
       yb.safe_mp_link("https://mp.weixin.qq.com:8080/s?x=1") == "")

    # ---------- 二、--pages 兼容契约 ----------
    ck("pages_note(None) 不产生 NOTE", yb.pages_note(None) == [])
    ck("pages_note(1) 不产生 NOTE", yb.pages_note(1) == [])
    pnote = yb.pages_note(3)
    ck("pages_note(3) 明确写出被忽略", len(pnote) == 1 and "已忽略" in pnote[0],
       repr(pnote))
    ck("pages_note(3) 说明无翻页", len(pnote) == 1 and "无翻页" in pnote[0], repr(pnote))

    # ---------- 三、文档示例里的长参数必须在脚本里真实定义 ----------
    src = _read(YB_SRC)
    doc = _yuanbao_doc_section(_read(SEARCH_SKILL))
    ck("Search/SKILL.md 存在元宝通道节", bool(doc))
    defined = set(re.findall(r'add_argument\(\s*"(--[a-z][a-z-]*)"', src))
    # 只扫代码块里的示例命令：本节散文会提到别的子技能参数（如 Read 的 --yuanbao），
    # 那些不是本脚本的参数，混进 used 会误报缺定义。
    code = "\n".join(re.findall(r"```[a-z]*\s*\n(.*?)```", doc, re.S))
    ck("元宝通道节含可执行的命令示例", bool(code.strip()))
    used = set(re.findall(r"(--[a-z][a-z-]*)", code))
    missing = sorted(used - defined)
    ck("文档示例里的长参数脚本均已定义", not missing, "缺: %s" % missing)
    ck("--pages 在脚本里已定义（文档示例会用到）", "--pages" in defined,
       "已定义: %s" % sorted(defined))

    # ---------- 四、render 三形态都能出结果 ----------
    for fmt in ("text", "json", "md"):
        out = yb.render(items[:2], fmt, "微信", ["note-a"])
        ck("render(%s) 产出非空文本" % fmt, bool(out.strip()))
    ck("render(json) 的 notes 与 stderr 同源",
       '"note-a"' in yb.render(items[:2], "json", "微信", ["note-a"]))

    print("\n元宝解析器判据：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
