# -*- coding: utf-8 -*-
"""交付链（B3 验收 / B4 推送 / B5 回读）纯逻辑单测。

只测离线可验证的判据与留痕逻辑：图数计数只认 <img>、验收包三查、人工签字拒空签、
回读清单图数。端到端真推需凭据与 playwright，不在本测范围（那属联调，非常规单测）。
"""
import argparse
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _load(name, relpath):
    path = os.path.join(ROOT, relpath)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(path))
    sys.modules[name] = mod   # 供模块内 dataclass 等查找
    spec.loader.exec_module(mod)
    return mod


def run():
    ap = _load("acceptance_pack", os.path.join("Write", "references", "b3-acceptance",
                                               "scripts", "acceptance_pack.py"))
    pg = _load("push_gate", os.path.join("Write", "references", "b4-push",
                                         "scripts", "push_gate.py"))
    rb = _load("readback_check", os.path.join("Write", "references", "b5-readback",
                                              "scripts", "readback_check.py"))
    ms = _load("manual_signoff", os.path.join("Write", "references", "b3-acceptance",
                                              "scripts", "manual_signoff.py"))

    tmp = tempfile.mkdtemp(prefix="deliver-chain-")
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append("%s%s" % (name, ("（%s）" % detail) if detail else ""))

    # 1) 图数一致性：只数 <img mmbiz> 标签，正文里提到域名不误导
    html_mix = ('<section><img src="https://mmbiz.qpic.cn/a/0">'
                '<p style="font-size:16px;color:#3f3f3f;">正文提到 mmbiz.qpic.cn 域名</p></section>')
    g = ap.gate_figcount(html_mix, None)
    check("图数只算 <img>（正文域名不误导）", g.get("mmbiz_imgs") == 1,
          "got %s" % g.get("mmbiz_imgs"))

    # 2) 验收包三查：overall 非 PASS / 指纹不符 / 通过
    html_ok = '<section><p style="font-size:16px;color:#3f3f3f;">正文。</p></section>'
    f_html = os.path.join(tmp, "a.html")
    io.open(f_html, "w", encoding="utf-8").write(html_ok)
    sha = pg._html_sha256(f_html)
    for overall, want_fail, tag in (("PENDING", True, "PENDING 不放行"),
                                    ("FAIL", True, "FAIL 不放行"),
                                    ("PASS", False, "PASS 放行")):
        f_acc = os.path.join(tmp, "acc_%s.json" % overall)
        json.dump({"overall": overall, "html_sha256": sha},
                  io.open(f_acc, "w", encoding="utf-8"))
        res = pg.check_acceptance(f_html, f_acc)
        check("验收包三查：%s" % tag, bool(res) == want_fail, "fails=%s" % res[:1])
    f_bad = os.path.join(tmp, "acc_badsha.json")
    json.dump({"overall": "PASS", "html_sha256": "deadbeef"},
              io.open(f_bad, "w", encoding="utf-8"))
    res = pg.check_acceptance(f_html, f_bad)
    check("验收包三查：指纹不符拦截", any("指纹" in x for x in res), str(res)[:80])

    # 3) 人工签字拒空签 / 正常留痕
    f_shot = os.path.join(tmp, "shot.png")
    io.open(f_shot, "wb").write(b"\x89PNG\r\n\x1a\n" + b"0" * 100)
    r = ms.cmd_record(argparse.Namespace(html=f_html, qa=f_shot, note="   ",
                                         out=os.path.join(tmp, "s.json")))
    check("人工签字：空 note 拒签", r == 1, "rc=%s" % r)
    r = ms.cmd_record(argparse.Namespace(html=f_html, qa=f_shot, note="看了首屏与代码块",
                                         out=os.path.join(tmp, "s.json")))
    check("人工签字：正常记录", r == 0 and os.path.isfile(os.path.join(tmp, "s.json")))

    # 4) 回读前置：清单正文图数（cover 不计）
    f_man = os.path.join(tmp, "man.json")
    json.dump({"figures": [{"kind": "body", "filename": "a.png"},
                           {"kind": "cover", "filename": "c.png"}]},
              io.open(f_man, "w", encoding="utf-8"))
    check("回读：清单正文图数（cover 不计）", rb.imgs_from_manifest(f_man) == 1)

    if fails:
        print("交付链单测：%d 项失败" % len(fails))
        for f in fails:
            print("   FAIL", f)
        return fails
    print("交付链单测：图数计数 / 验收包三查 / 人工拒空签 / 回读清单图数 全部通过")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
