# -*- coding: utf-8 -*-
"""Read/ 元宝换源兜底的离线判据（不联网、不起浏览器、不改真机状态）。

运行: python tests/test_read_yuanbao_fallback.py
全量: python tests/run_all.py     # 本文件按仓库约定暴露 run()

手法：把 read_wechat.py 的四个取页层替换成本地函数，往 sys.modules 注入假的
yuanbao_search 模块（用 patch.dict 自动恢复，不污染后面的元宝解析器判据），
因此全程零网络请求。测的是 read() 的调度与安全门，不测真实站点。

对撞方向（任一判反即报红）：
  默认关闭 → 绝不触发换源；CDP 抛异常 → 仍要能兜底（曾因提前 return 被绕过）；
  命中 → 正文/诊断/合并正确；候选全失败 → 只搜一次不回环；
  搜索异常或空结果 → 干净回退；结果页给的链接不是 mp.weixin → 一律丢弃不发请求。
"""
import importlib.util
import io
import os
import subprocess
import sys
import types
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, os.pardir))
READ_SRC = os.path.join(ROOT, "Read", "scripts", "read_wechat.py")
READ_SKILL = os.path.join(ROOT, "Read", "SKILL.md")
ARTICLE_FIXTURE = os.path.join(HERE, "fixtures", "mp_article_sample.html")

ORIG = "https://mp.weixin.qq.com/s?__biz=ORIG&mid=1&idx=1&sn=dead"
GOOD = "https://mp.weixin.qq.com/s?__biz=GOOD&mid=2&idx=1&sn=alive"
WALL_TITLE = "大模型 &amp; 应用落地"       # og:title 带实体，搜索前应还原成 &
WANT_TITLE = "大模型 & 应用落地"
BODY = "正文内容" * 30


def _load():
    spec = importlib.util.spec_from_file_location("read_wechat_fallback_probe", READ_SRC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read(path):
    with io.open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def _good_html(title="换源后的真实文章"):
    return ('<html><head><meta property="og:title" content="%s">'
            '<meta property="article:published_time" content="2026-11-01">'
            '</head><body><div id="js_content"><p>%s</p></div></body></html>'
            % (title, BODY))


def _wall_html(title=WALL_TITLE):
    # 有 og:title（供换源用），但正文命中验证墙标记 → 四层都判 FAIL
    return ('<html><head><meta property="og:title" content="%s">'
            '</head><body><div id="js_content">环境异常，请完成验证后即可继续访问</div>'
            '</body></html>' % title)


class Harness(object):
    """一次用例的环境：替换四层 + 注入假元宝模块，记录所有请求。"""

    def __init__(self, R, items, notes=None, raise_search=None, pages=None):
        self.R = R
        self.calls = []          # HTTP 三层收到的 URL
        self.cdp_calls = []      # 第 4 层收到的 URL
        self.queries = []        # 假元宝收到的 (关键词, want)
        self.items = items
        self.notes = notes if notes is not None else ["元宝：解析到 N 条"]
        self.raise_search = raise_search
        self.pages = pages or {}

        def fake_layer(url):
            self.calls.append(url)
            return {"html": self.pages.get(url, _wall_html()),
                    "final_url": url, "layer_ua": "fake"}

        def fake_cdp(url, timeout=40):
            self.cdp_calls.append(url)
            # 模拟最常见的真机前提：Edge 没开远程调试端口
            raise RuntimeError("DevToolsActivePort 不存在（模拟）")

        self._orig = (R.layer1, R.layer2, R.layer3, R.cdp_get_html)
        R.layer1 = R.layer2 = R.layer3 = fake_layer
        R.cdp_get_html = fake_cdp

        fake = types.ModuleType("yuanbao_search")

        def search(keyword, want=10, **kwargs):
            self.queries.append((keyword, want))
            if self.raise_search:
                raise self.raise_search
            return self.items, self.notes

        fake.search = search
        self.fake = fake

    def __enter__(self):
        # sys.modules 与 sys.path 都进上下文：退出自动恢复，不污染同批次其它判据
        self._stack = mock.patch.dict(sys.modules, {"yuanbao_search": self.fake})
        self._stack.start()
        self._pathbak = list(sys.path)
        return self

    def __exit__(self, *exc):
        R = self.R
        R.layer1, R.layer2, R.layer3, R.cdp_get_html = self._orig
        self._stack.stop()
        sys.path[:] = self._pathbak
        return False


def run():
    fails = []

    def ck(name, cond, detail=""):
        if cond:
            print("  [PASS] %s" % name)
        else:
            fails.append("%s %s" % (name, detail))
            print("  [FAIL] %s  %s" % (name, detail))

    R = _load()
    kw = dict(min_chars=20, use_cdp=True, max_layer=4, timeout=5)

    # ---------- 一、安全门单元断言 ----------
    print("\n[一] 换源链接主机白名单")
    ck("放行 mp.weixin 永久直链", R.safe_article_url(GOOD) == GOOD)
    ck("拒绝空链接", R.safe_article_url("") == "")
    ck("拒绝外域链接", R.safe_article_url("https://evil.example/x") == "")
    ck("拒绝子串伪装 mp.weixin.qq.com.evil.example",
       R.safe_article_url("https://mp.weixin.qq.com.evil.example/s?x=1") == "")
    ck("拒绝带端口的 mp.weixin",
       R.safe_article_url("https://mp.weixin.qq.com:8080/s?x=1") == "")
    ck("拒绝非法 IPv6 主机（urlsplit 会抛）",
       R.safe_article_url("https://[mp.weixin.qq.com/s?x=1") == "")
    ck("拒绝非 http(s) 协议", R.safe_article_url("javascript:alert(1)") == "")

    # ---------- 二、默认关闭，绝不触发 ----------
    print("\n[二] 默认关闭")
    items = [{"resolved": GOOD, "link": GOOD, "title": "同款"}]
    with Harness(R, items, pages={GOOD: _good_html()}) as h:
        r = R.read(ORIG, yuanbao_fallback=False, **kw)
        ck("四层失败时结果 ok=False", r["ok"] is False)
        ck("未调用元宝搜索", h.queries == [], repr(h.queries))
        ck("未对换源链接发过请求", GOOD not in h.calls, repr(h.calls))
        ck("CDP 异常被记进诊断",
           any("[4-cdp] 不可用" in d for d in r["diag"]), repr(r["diag"]))
        ck("CDP 异常不再提前 return（能走到统一失败出口）",
           r.get("layer") is None and r.get("note") == "四层均未取到合格正文",
           repr((r.get("layer"), r.get("note"))))

    # ---------- 三、CDP 异常仍能兜底命中 ----------
    print("\n[三] CDP 异常 → 换源命中（本轮修复的核心）")
    with Harness(R, items, pages={GOOD: _good_html()}) as h:
        r = R.read(ORIG, yuanbao_fallback=True, **kw)
        ck("结果 ok=True", r["ok"] is True, repr(r["diag"]))
        ck("元宝被查询 1 次", len(h.queries) == 1, repr(h.queries))
        ck("标题实体已还原成正常文字", h.queries[0][0] == WANT_TITLE, repr(h.queries))
        ck("只取 3 个候选", h.queries[0][1] == R.FALLBACK_CANDIDATES, repr(h.queries))
        ck("正文来自换源后的链接", r.get("meta", {}).get("source_url") == GOOD,
           repr(r.get("meta", {}).get("source_url")))
        ck("正文非空且过质量门", r.get("chars", 0) >= 20, repr(r.get("chars")))
        ck("note 标注元宝换源命中并留原链接",
           "元宝换源命中" in (r.get("note") or "") and ORIG in (r.get("note") or ""),
           repr(r.get("note")))
        ck("attempts 保留原四层 + 新读取记录",
           len(r.get("attempts", [])) >= 4, repr(r.get("attempts")))
        ck("diag 含 CDP 不可用与换源过程",
           any("[4-cdp] 不可用" in d for d in r["diag"]) and
           any("[yuanbao]" in d for d in r["diag"]), repr(r["diag"]))
        ck("元宝 NOTE 也进了 diag",
           any("元宝：解析到" in d for d in r["diag"]), repr(r["diag"]))
        ck("换源链接确实被请求过", GOOD in h.calls, repr(h.calls))

    # ---------- 四、候选全失败：只搜一次，不回环 ----------
    print("\n[四] 候选全失败 → 不回环")
    bad_items = [{"resolved": "https://mp.weixin.qq.com/s?__biz=BAD%d" % i,
                  "link": "", "title": "同款%d" % i} for i in range(1, 6)]
    with Harness(R, bad_items) as h:
        r = R.read(ORIG, yuanbao_fallback=True, **kw)
        ck("结果 ok=False", r["ok"] is False)
        ck("元宝只被查询 1 次（递归不再搜）", len(h.queries) == 1, repr(h.queries))
        ck("候选数被截到 3", h.queries[0][1] == 3 and
           sum(1 for d in r["diag"] if d.startswith("[yuanbao] 候选 ")) <= 6,
           repr(h.queries))
        ck("诊断给出回到原失败结论",
           any("回到原失败结论" in d for d in r["diag"]), repr(r["diag"]))
        ck("CDP 异常仍记录在案",
           sum(1 for d in r["diag"] if "[4-cdp] 不可用" in d) >= 1)

    # ---------- 五、空结果 / 搜索异常 → 干净回退 ----------
    print("\n[五] 换源不可用 → 干净回退")
    with Harness(R, []) as h:
        r = R.read(ORIG, yuanbao_fallback=True, **kw)
        ck("空结果时 ok=False", r["ok"] is False)
        ck("空结果时不发换源请求", GOOD not in h.calls)
        ck("诊断里保留了元宝 NOTE",
           any("元宝：解析到" in d for d in r["diag"]), repr(r["diag"]))
    with Harness(R, items, raise_search=RuntimeError("antispider 拦截")) as h:
        r = R.read(ORIG, yuanbao_fallback=True, **kw)
        ck("搜索抛异常时 ok=False 而非崩溃", r["ok"] is False)
        ck("异常原因写进 diag",
           any("换源搜索异常" in d and "antispider" in d for d in r["diag"]),
           repr(r["diag"]))

    # ---------- 六、结果页注入的恶意链接一律不发请求 ----------
    print("\n[六] 不可信链接安全门")
    evil = [
        {"resolved": "https://mp.weixin.qq.com.evil.example/s?x=1", "link": ""},
        {"resolved": "", "link": "https://evil.example/x"},
        {"resolved": "https://mp.weixin.qq.com:8080/s?x=1", "link": ""},
    ]
    with Harness(R, evil, pages={GOOD: _good_html()}) as h:
        r = R.read(ORIG, yuanbao_fallback=True, **kw)
        ck("结果 ok=False", r["ok"] is False)
        ck("三条恶意链接均被丢弃",
           sum(1 for d in r["diag"] if "已丢弃" in d) == 3, repr(r["diag"]))
        ck("没有任何一次请求发往非原 URL",
           all(u == ORIG for u in h.calls), repr(h.calls))
        ck("CDP 也只收到原 URL",
           all(u == ORIG for u in h.cdp_calls), repr(h.cdp_calls))

    # ---------- 七、CLI 接线与文档一致性 ----------
    print("\n[七] CLI 接线")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, READ_SRC, "--help"],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       env=env, timeout=30)
    help_text = p.stdout.decode("utf-8", "replace")
    ck("--help 退出码 0", p.returncode == 0, str(p.returncode))
    ck("--help 列出 --yuanbao", "--yuanbao" in help_text)

    p2 = subprocess.run([sys.executable, READ_SRC, ORIG, "--fixture", ARTICLE_FIXTURE,
                         "--yuanbao"],
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=env, timeout=30)
    err2 = p2.stderr.decode("utf-8", "replace")
    ck("--fixture + --yuanbao 明确提示已忽略（离线不联网）",
       "已忽略" in err2, repr(err2[:300]))
    ck("--fixture 路径不触发真实网络请求",
       "ATTEMPT fixture" in err2 or "fixture" in err2, repr(err2[:300]))

    src = _read(READ_SRC)
    ck("read() 定义了 yuanbao_fallback 形参",
       "yuanbao_fallback=False" in src)
    ck("main() 把 --yuanbao 传给了 read()",
       "yuanbao_fallback=args.yuanbao" in src)
    ck("递归调用显式关闭兜底（不回环）",
       "yuanbao_fallback=False)" in src or "yuanbao_fallback=False\n" in src)
    ck("Read/SKILL.md 写到了 --yuanbao",
       "--yuanbao" in _read(READ_SKILL))

    print("\nRead 元宝兜底判据：%d 项失败" % len(fails))
    for f in fails:
        print("   FAIL", f)
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
