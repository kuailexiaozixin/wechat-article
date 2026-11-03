# -*- coding: utf-8 -*-
"""B3 静态 · wx 内联版 HTML 静态合规的批量闸与报告汇总。

**不重新实现校验规则**。规则的唯一实现是同目录的 `validate_wx_html.py`（本目录）
（其 `validate()` 同时被根 `scripts/wx_draft_push.py` 的推送闸加载——两处必须同一套判据）。本脚本只做三件
单文件校验器不管的事：

    1. 批量 —— 一次扫一个目录/多份 HTML，汇总 ERROR/WARNING 计数
    2. 门禁 —— 把「ERROR=0」变成可接进流水线的一条命令（非零即断）
    3. 留痕 —— 输出机器可读 JSON，供 B5 人工自查表与交付说明引用

用法：
    static_check.py <文件或目录> [...] [--json out.json] [--strict]
    --strict : WARNING 也判失败（系列稿件交付、对外发布建议开）

退出码：0 = 全部 ERROR=0；1 = 至少一份有 ERROR（--strict 下含 WARNING）；2 = 用法错误。
"""
import argparse
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def _find_validate():
    """定位 validate_wx_html.py——B3 的单一规则源，与本脚本同目录。

    先查同目录（正常态），再逐级向上兜底（脚本被单独拷走时仍可命中）。
    找不到返回 None，由调用方明确报错，绝不静默降级为「视为通过」。
    """
    d = HERE
    for _ in range(8):
        for cand in (os.path.join(d, "validate_wx_html.py"),
                     os.path.join(d, "scripts", "validate_wx_html.py")):
            if os.path.isfile(cand):
                return cand
        up = os.path.dirname(d)
        if up == d:
            break
        d = up
    return None


def load_validate(explicit=None):
    """按路径加载单文件校验器；找不到就明确报错，绝不静默降级为「视为通过」。"""
    cand = None
    if explicit:
        cand = os.path.join(explicit, "validate_wx_html.py")
        if not os.path.isfile(cand):
            raise SystemExit("ERR --validate-dir %s 下没有 validate_wx_html.py" % explicit)
    cand = cand or _find_validate()
    if cand is None:
        raise SystemExit(
            "ERR 找不到 validate_wx_html.py。已自 %s 起向上逐级查找 8 层。\n"
            "     本脚本只做批量与门禁，规则不在此实现——请先核对目录布局，"
            "或用 --validate-dir 指定 validate_wx_html.py 所在目录。" % HERE)
    sys.path.insert(0, os.path.dirname(cand))
    import validate_wx_html  # noqa: PLC0415
    return validate_wx_html.validate


def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += sorted(glob.glob(os.path.join(p, "**", "*.html"), recursive=True))
        elif os.path.isfile(p):
            out.append(p)
        else:
            # 引用规则文件时的示例路径不存在也算失败：批量闸最怕「扫了个空目录却报全绿」
            out.append(p)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("paths", nargs="+", help="HTML 文件或目录")
    ap.add_argument("--json", dest="json_out", help="机器可读汇总落盘路径")
    ap.add_argument("--strict", action="store_true", help="WARNING 也判失败")
    ap.add_argument("--validate-dir", help="显式指定 validate_wx_html.py 所在目录（默认同目录→逐级上溯）")
    ap.add_argument("--skip-preview", action="store_true",
                    help="跳过 *_预览.html（wrap_preview 产物含 <style>，不是推送件）")
    args = ap.parse_args()

    validate = load_validate(args.validate_dir)
    files = collect(args.paths)
    if not files:
        print("[FAIL] 没有匹配到任何 HTML——空扫不等于全绿")
        return 1
    rows, total_err, total_warn = [], 0, 0
    rc = 0
    print("=== B3 静态合规批量闸（规则源：同目录 validate_wx_html.py）===")
    for f in files:
        if args.skip_preview and f.endswith("_预览.html"):
            print("  [SKIP] %s（预览外壳，非推送产物）" % os.path.basename(f))
            continue
        if not os.path.isfile(f):
            print("  [FAIL] 路径不存在: %s" % f)
            rc = 1
            continue
        html = io.open(f, encoding="utf-8", errors="replace").read()
        errors, warnings, checker = validate(html, f)
        total_err += len(errors)
        total_warn += len(warnings)
        rows.append({"file": f, "errors": errors, "warnings": warnings,
                     "counts": {"img": checker.n_img, "p": checker.n_p,
                                "section": checker.n_section}})
        mark = "FAIL" if errors else ("WARN" if warnings else "PASS")
        print("  [%s] %s  ERROR×%d WARNING×%d · img×%d p×%d section×%d"
              % (mark, os.path.basename(f), len(errors), len(warnings),
                 checker.n_img, checker.n_p, checker.n_section))
        for e in errors[:6]:
            print("        •", e)
        if errors:
            rc = 1
    if args.strict and total_warn:
        rc = 1
        print("  [FAIL] --strict：WARNING 共 %d 条按失败处理" % total_warn)
    if rc == 0:
        print("[PASS] %d 份全部 ERROR=0，可进 B4 渲染验收（WARNING %d 条待人工确认）"
              % (len(rows), total_warn))
    else:
        print("[FAIL] 合计 ERROR×%d · WARNING×%d ——修复后重跑，不带错进下一闸"
              % (total_err, total_warn))
    if args.json_out:
        json.dump({"files": rows, "total_error": total_err,
                   "total_warning": total_warn, "passed": rc == 0},
                  io.open(args.json_out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("saved ->", args.json_out)
    return rc


if __name__ == "__main__":
    sys.exit(main())
