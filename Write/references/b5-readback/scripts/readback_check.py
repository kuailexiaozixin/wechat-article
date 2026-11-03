#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B5 回读门禁：推送后必须从平台读回来核对，不接受"推送命令成功了"作为交付依据。

本脚本不重新实现任何回读判据。逐项比对（title 字节数 / digest 字数 / thumb /
<pre> / <style> / div 伪表格 / mmbiz 图数 / 本地图片路径 / 正文与源逐字一致）
全部委托根 scripts/check_draft.py --json，规则源只有一份。

在 check_draft 之外，本脚本只补三件它管不到的"留痕"事项：
  1. media_id 不允许人工复制粘贴。默认从 B4 push_gate.py 落盘的 json 读取
     （{"media_id","html","html_sha256"}），也可用 --record 指定；--media-id 仅供排障临时使用。
  2. 排『改了没重推』：推送记录里的 html_sha256 与当前源文件哈希比对，不一致直接 FAIL，
     不再浪费一次接口调用（旧格式记录无哈希时退回 mtime 比较，但复制文件/换机时
     mtime 不可信，属已知局限——新记录一律带哈希）。
  3. --expect-imgs 默认从 B1 图片清单（figure_manifest.json）自动取正文图数
     （kind==cover 不计），避免"少了一张图但回读只看 >0"这种漏检。

用法:
    python readback_check.py --record <B6 push json>
    python readback_check.py --record push.json --manifest manifest.json
    python readback_check.py --media-id MEDIA_ID --source article.html [--json]
退出码: 0 = 全部 PASS; 1 = 有 FAIL（回 B2 改稿重推，不能就地改草稿了事）;
       2 = 前置条件不满足（记录缺失、源码哈希不符、找不到 check_draft.py、凭据缺失）。
"""
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_root_scripts():
    """从本流程目录逐级上溯找仓库根 scripts/，不写死层数（本技能曾因此断链）。"""
    d = HERE
    for _ in range(10):
        cand = os.path.join(d, "scripts", "check_draft.py")
        if os.path.isfile(cand):
            return os.path.join(d, "scripts"), cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    raise SystemExit("ERR 找不到根 scripts/check_draft.py（自 %s 上溯 10 层）"
                     "——回读判据只有一份，本脚本不重新实现。" % HERE)


ROOT_SCRIPTS, CHECK_DRAFT = _find_root_scripts()


def load_record(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            rec = json.load(f)
    except (OSError, ValueError) as e:
        raise SystemExit("ERR 推送记录不可用：%s（%s）" % (path, e))
    mid = rec.get("media_id", "")
    html = rec.get("html", "")
    if not mid:
        raise SystemExit("ERR 推送记录里没有 media_id：%s——请从 B4 push_gate.py "
                         "push 重新生成，不要手填。" % path)
    return mid, html, rec


def imgs_from_manifest(path):
    """清单里有几张正文图，回读就该有几次 mmbiz 引用。kind==cover 不算：
    封面走 media_id，不写进正文，永远不会出现在 mmbiz 计数里。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise SystemExit("ERR 图片清单不可用：%s（%s）" % (path, e))
    figs = data.get("figures") if isinstance(data, dict) else None
    if not isinstance(figs, list) or not figs:
        raise SystemExit("ERR 图片清单里没有非空 figures 数组：%s——清单字段名为 figures，"
                         "用 figure_manifest.py template 生成，不要手编。" % path)
    body = [f for f in figs if f.get("kind", "body") != "cover"]
    if not body:
        raise SystemExit("ERR 清单 %s 里没有正文图（全是 cover）——无正文图时不要传 --manifest，"
                         "由 check_draft 的「有正文图」判据处理。" % path)
    return len(body)


def run_check_draft(media_id, source, expect_imgs):
    cmd = [sys.executable, CHECK_DRAFT, media_id, "--json"]
    if source:
        cmd += ["--source", source]
    if expect_imgs is not None:
        cmd += ["--expect-imgs", str(expect_imgs)]
    p = subprocess.run(cmd, cwd=ROOT_SCRIPTS, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    raw = (p.stdout or "").strip()
    if not raw:
        return None, p, (p.stderr or "").strip()
    try:
        return json.loads(raw), p, ""
    except ValueError:
        return None, p, raw[:400]


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]

    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default

    def has(name):
        return name in argv

    if not argv:
        print(__doc__)
        raise SystemExit(2)

    record = opt("--record")
    media_id = opt("--media-id")
    source = opt("--source")
    manifest = opt("--manifest")
    expect_raw = opt("--expect-imgs")

    pre = []          # 本脚本自己判的前置项
    notes = []

    if record:
        media_id, rec_html, rec = load_record(record)
        if not source:
            source = rec_html
        if not (source and os.path.isfile(source)):
            pre.append(("源文件存在", "FAIL",
                        "源文件 %s 不存在——推送记录里的路径已失效，无法比哈希也回读不了" % source))
        else:
            cur = hashlib.sha256(open(source, "rb").read()).hexdigest()
            rec_sha = rec.get("html_sha256")
            if rec_sha:
                if cur != rec_sha:
                    pre.append(("源码未重推", "FAIL",
                                "当前源文件 sha256 %s… ≠ 推送记录 %s…——验收/推送后改过稿没重推，"
                                "回读必然不一致。回 B3 重验收、B4 重推。"
                                % (cur[:12], rec_sha[:12])))
                else:
                    pre.append(("源码未重推", "PASS", "sha256 与推送记录一致（%s…）" % cur[:12]))
            else:
                pushed_at = os.path.getmtime(record)
                if os.path.getmtime(source) > pushed_at:
                    pre.append(("源码未重推", "FAIL",
                                "旧格式推送记录无哈希，退回 mtime 判定：源文件晚于推送记录——"
                                "中间改过稿没重推。请用 B4 push_gate.py 重推（新记录带哈希）。"))
                else:
                    pre.append(("源码未重推", "PASS",
                                "旧格式记录退回 mtime（复制文件/换机会失真，建议重推一次以升级记录）"))
    elif not media_id:
        raise SystemExit("ERR 需要 --record <B6 push json>（推荐）或 --media-id（仅排障）。")
    else:
        notes.append("未提供 --record：跳过『改了没重推』检查，media_id 由命令行临时指定。")

    expect_imgs = None
    if expect_raw is not None:
        expect_imgs = int(expect_raw)
    elif manifest:
        expect_imgs = imgs_from_manifest(manifest)
        notes.append("--expect-imgs 取自 B1 清单 %s：%d 张" % (os.path.basename(manifest), expect_imgs))

    fail = [n for n, st, _ in pre if st == "FAIL"]
    if fail:
        result = {"ok": False, "checks": pre, "summary": {"media_id": media_id},
                  "notes": notes, "gate": "前置未过，未调用平台接口"}
        _emit(result, as_json)
        raise SystemExit(2)

    if not (os.environ.get("WECHAT_APPID") and os.environ.get("WECHAT_SECRET")):
        result = {"ok": False,
                  "checks": pre + [("凭据", "FAIL", "WECHAT_APPID / WECHAT_SECRET 未设置")],
                  "summary": {"media_id": media_id}, "notes": notes}
        _emit(result, as_json)
        raise SystemExit(2)

    res, p, err = run_check_draft(media_id, source, expect_imgs)
    if res is None:
        print("ERR check_draft.py 未返回可解析 JSON（exit=%s）：%s" % (p.returncode, err))
        raise SystemExit(2)

    checks = pre + [list(c) for c in res.get("checks", [])]
    ok = bool(res.get("ok")) and not [c for c in pre if c[1] == "FAIL"]
    out = {"ok": ok, "checks": checks,
           "summary": dict(res.get("summary", {}), media_id=media_id),
           "notes": notes, "rule_source": CHECK_DRAFT}
    _emit(out, as_json)
    raise SystemExit(0 if ok else 1)


def _emit(res, as_json):
    if as_json:
        print(json.dumps(res, ensure_ascii=False))
        return
    for name, st, detail in res.get("checks", []):
        print("[%s] %s%s" % (st, name, (" — " + detail) if detail else ""))
    for n in res.get("notes", []):
        print("      note: %s" % n)
    s = res.get("summary", {})
    if s:
        print("摘要: media_id=%s title=%r mmbiz图=%s 本地路径=%s"
              % (s.get("media_id", ""), (s.get("title") or "")[:24],
                 s.get("mmbiz_imgs"), s.get("local_imgs")))
    if res.get("gate"):
        print("[GATE] %s" % res["gate"])
    print("[PASS] 回读一致，可交付" if res.get("ok") else "[FAIL] 回读存在不符项，修复后须重新推送并重跑 B5")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
