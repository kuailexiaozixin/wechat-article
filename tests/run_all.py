# -*- coding: utf-8 -*-
"""一次跑完 tests/ 下全部判据脚本，汇总失败项。

用法（Windows 控制台需 UTF-8）：
    set PYTHONUTF8=1 && python tests/run_all.py
    python tests/run_all.py -k qa          # 只跑文件名含 qa 的判据

约定：每个 test_*.py 暴露 run() → 失败说明列表（空表 = 通过），或返回失败条数（int）。
跳过不是通过：判据脚本因缺依赖等原因没跑起来时，把原因写进模块全局 `SKIP` 再返回空表，
本文件把它计入「跳过」并在汇总行单列，汇总里的通过数不包含它。
本文件不做任何判定，只做发现、聚合与非零退出，便于交付前一条命令过全闸。
"""
import argparse
import importlib.util
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))


def discover(keyword):
    names = sorted(f for f in os.listdir(HERE)
                   if f.startswith("test_") and f.endswith(".py"))
    if keyword:
        names = [f for f in names if keyword in f]
    return names


def load(fname):
    spec = importlib.util.spec_from_file_location(fname[:-3], os.path.join(HERE, fname))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-k", "--keyword", help="只跑文件名含此串的判据")
    args = ap.parse_args()

    files = discover(args.keyword)
    if not files:
        print("tests/ 下没有匹配的 test_*.py（关键词 %r）" % args.keyword)
        return 1

    total, failed, skipped, bad = [], [], [], set()
    for fname in files:
        print("\n===== %s =====" % fname)
        try:
            mod = load(fname)
            if not hasattr(mod, "run"):
                bad.add(fname)
                failed.append("%s: 缺 run()，约定见 tests/run_all.py 文档" % fname)
                print("   FAIL 缺 run()")
                continue
            result = mod.run()
            if isinstance(result, int):   # 约定二：run() 返回失败计数也接受，0 通过
                fails = ["run() 返回 %d 项失败（详见上方输出）" % result] if result else []
            else:
                fails = result or []
        except SystemExit as e:            # 判据脚本内部 sys.exit 不当崩溃
            bad.add(fname)
            failed.append("%s: 内部 SystemExit(%s)" % (fname, e.code))
            print("   FAIL 内部 SystemExit(%s)" % e.code)
            continue
        except Exception:
            bad.add(fname)
            total.append(fname)
            failed.append("%s: 执行异常\n%s" % (fname, traceback.format_exc()))
            print("   FAIL 执行异常")
            print(traceback.format_exc())
            continue
        total.append(fname)
        reason = getattr(mod, "SKIP", None)
        if reason:
            skipped.append("%s: %s" % (fname, reason))
        elif fails:
            bad.add(fname)
            failed += ["%s: %s" % (fname, f) for f in fails]

    passed = [f for f in total if f not in bad and f not in
              {s.split(":")[0] for s in skipped}]
    print("\n" + "=" * 56)
    print("判据文件 %d 个：通过 %d · 跳过 %d · 失败 %d 项"
          % (len(total), len(passed), len(skipped), len(failed)))
    for s in skipped:
        print(" - SKIP %s" % s)
    for f in failed:
        print(" - %s" % f)
    if not failed and not skipped:
        print("全部通过。")
    elif not failed:
        print("无失败，但有判据未真正跑起来——上面的 SKIP 就是缺口，不能当通过引用。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
