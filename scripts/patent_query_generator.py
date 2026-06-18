#!/usr/bin/env python3
"""产业转化（I_patent）检索式生成器。

读 config/i_caliber_patent.yml 的 C/B/X IPC 口径，生成智慧芽/incoPat 可粘贴的
布尔检索式（省=福建、申请日窗口、发明+实用新型）。口径一改，检索式自动重生成，
不用手改字符串。纯标准库 + pyyaml。

设计要点：
- B 的短前缀 G06F 吸收 C 的 G06F18/G06F40，生成时自动去掉被吸收的长前缀（避免冗余）。
- G06K9 旧码始终纳入（抓全 2019–2021 模式识别专利），去重靠申请号。
- 省级筛选（福建），城市归属留到清洗阶段（平台地址检索易漏）。

用法：
  python3 scripts/patent_query_generator.py                 # 打印 C/B/X 检索式
  python3 scripts/patent_query_generator.py --self-test     # 校验嵌套与吸收逻辑
"""
from __future__ import annotations
import argparse
from pathlib import Path

try:
    import yaml
except ImportError:
    raise SystemExit("需要 pyyaml：pip3 install --user pyyaml")

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "config" / "i_caliber_patent.yml"

YEAR_START, YEAR_END = 2019, 2024
PROVINCE = "福建"
PATENT_TYPES = "发明 OR 实用新型"
LEGACY = "G06K9"   # 旧模式识别码，必纳入


def _prefixes(cfg):
    """返回 {C,B,X: [ipc前缀...]}，严格嵌套展开。"""
    c = [p["code"] for p in cfg["C_conservative"]["ipc_prefixes"]]
    b = c + [p["code"] for p in cfg["B_basic"]["additional_ipc_prefixes"]]
    x = b + [p["code"] for p in cfg["X_expanded"]["additional_ipc_prefixes"]]
    return {"C": c, "B": b, "X": x}


def _absorb(codes):
    """去掉被同集合中更短前缀吸收的码（如 G06F 在场时去掉 G06F18/G06F40）；加 G06K9。"""
    keep = []
    for code in codes:
        if any(code != other and code.startswith(other) for other in codes):
            continue   # 被更短前缀吸收
        keep.append(code)
    if LEGACY not in keep:
        keep.append(LEGACY)
    # 去重保序
    seen, out = set(), []
    for k in keep:
        if k not in seen:
            seen.add(k); out.append(k)
    return out


def build_query(codes):
    ipc = " OR ".join(f"{c}*" for c in codes)
    return (f"IPC=({ipc})\n"
            f"AND 申请人地址=({PROVINCE})\n"
            f"AND 申请日=[{YEAR_START}0101 TO {YEAR_END}1231]\n"
            f"AND 专利类型=({PATENT_TYPES})")


def main():
    ap = argparse.ArgumentParser(description="I_patent 检索式生成器")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    cfg = yaml.safe_load(open(CFG, encoding="utf-8"))
    pref = _prefixes(cfg)
    sets = {k: _absorb(v) for k, v in pref.items()}

    if args.self_test:
        print("== 检索式生成器自检 ==")
        # 语义嵌套：每个小口径前缀须被大口径某前缀覆盖（==或被更短前缀包含），
        # 而非字面子集——因 B 把 C 的 G06F18/G06F40 吸收为 G06F。
        covered = lambda small, big: all(any(s == b or s.startswith(b) for b in big) for s in small)
        okC = covered(sets["C"], sets["B"])
        okB = covered(sets["B"], sets["X"])
        absorbed = "G06F18" not in sets["B"] and "G06F40" not in sets["B"] and "G06F" in sets["B"]
        legacy = all(LEGACY in s for s in sets.values())
        print(f"  C⊆B: {okC}  B⊆X: {okB}  B吸收G06F18/40: {absorbed}  各口径含G06K9: {legacy}")
        print(f"  C={sets['C']}")
        print(f"  B={sets['B']}")
        print(f"  X={sets['X']}")
        ok = okC and okB and absorbed and legacy
        print("自检", "通过 ✓" if ok else "失败 ✗")
        raise SystemExit(0 if ok else 1)

    for cal in ("B", "C", "X"):   # B 主口径先
        label = {"C": "C 保守", "B": "B 基本（主口径）", "X": "X 扩大"}[cal]
        print(f"\n### {label}口径\n```")
        print(build_query(sets[cal]))
        print("```")


if __name__ == "__main__":
    main()
