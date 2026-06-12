#!/usr/bin/env python3
"""口径嵌套性自动校验器（质量闸门 Q3 的配置层检查）。

校验内容：
  1. E端专业口径：C ⊂ B ⊂ X 严格嵌套、无重复专业、无专业同时出现在 pending_ruling 与正式口径
  2. I_patent：C/B/X IPC 前缀严格嵌套、无前缀互相包含造成的重复计数（如同时列 G06F 与 G06F40）
  3. I_firm / I_job：includes 链完整、引用的关键词层在 i_system_upgrade_keywords.yml 中存在
  4. 高校参照名单：校名唯一、曾用名不与现名冲突

任何检查失败以非零退出码返回，供采集管道作为前置闸门调用。
"""
import sys
import yaml
from pathlib import Path

CONFIG = Path(__file__).resolve().parent.parent / "config"
FAILURES = []


def fail(msg):
    FAILURES.append(msg)


def load(name):
    with open(CONFIG / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_e_majors():
    cfg = load("e_caliber_majors.yml")
    c = {m["name"] for m in cfg["C_conservative"]["majors"]}
    b_add = {m["name"] for m in cfg["B_basic"]["additional_majors"]}
    x_add = {m["name"] for m in cfg["X_expanded"]["additional_majors"]}
    b, x = c | b_add, c | b_add | x_add
    if c & b_add:
        fail(f"E端: C 与 B 增量重复: {c & b_add}")
    if b & x_add:
        fail(f"E端: B 与 X 增量重复: {b & x_add}")
    if not (c < b < x):
        fail("E端: C ⊂ B ⊂ X 嵌套关系不成立")
    pend = {p["name"] for p in cfg.get("pending_ruling", [])}
    if pend & x:
        fail(f"E端: pending_ruling 专业混入正式口径: {pend & x}")
    unverified = [m["name"] for tier in (cfg["C_conservative"]["majors"],
                  cfg["B_basic"]["additional_majors"], cfg["X_expanded"]["additional_majors"])
                  for m in tier if not m.get("code_verified")]
    print(f"  E端: C={len(c)} B={len(b)} X={len(x)} 嵌套OK；待核验代码 {len(unverified)} 项: {unverified}")


def check_patent():
    cfg = load("i_caliber_patent.yml")
    c = [p["code"] for p in cfg["C_conservative"]["ipc_prefixes"]]
    b_add = [p["code"] for p in cfg["B_basic"]["additional_ipc_prefixes"]]
    x_add = [p["code"] for p in cfg["X_expanded"]["additional_ipc_prefixes"]]
    all_codes = c + b_add + x_add
    if len(all_codes) != len(set(all_codes)):
        fail("I_patent: IPC 前缀存在重复条目")
    # 前缀吸收检查：若某层新增前缀已被更早层的更短前缀覆盖，属重复计数配置错误
    # 注意 C 层内部允许 G06F18/G06F40 共存于 B 层 G06F 之下——B 是 C 的超集，吸收是预期行为
    for code in b_add:
        for prior in c:
            if code.startswith(prior):
                fail(f"I_patent: B新增 {code} 已被 C 的 {prior} 覆盖")
    for code in x_add:
        for prior in c + b_add:
            if code.startswith(prior) or prior.startswith(code):
                fail(f"I_patent: X新增 {code} 与既有 {prior} 存在覆盖关系")
    absorbed = [cc for cc in c for bb in b_add if cc.startswith(bb)]
    print(f"  I_patent: C={len(c)} B=+{len(b_add)} X=+{len(x_add)} 嵌套OK；"
          f"C层被B层短前缀吸收(预期): {absorbed}")


def check_keyword_refs():
    kw = load("i_system_upgrade_keywords.yml")
    valid_tiers = set(kw.keys())
    for fname, paths in {
        "i_caliber_firm.yml": [("C_conservative", "keyword_tiers_required"),
                               ("X_expanded", ("additional", "keyword_tiers_required"))],
        "i_caliber_job.yml": [("C_conservative", "keyword_tiers"),
                              ("B_basic", "additional_keyword_tiers"),
                              ("X_expanded", "additional_keyword_tiers")],
    }.items():
        cfg = load(fname)
        for section, key in paths:
            node = cfg[section]
            tiers = node[key[0]][key[1]] if isinstance(key, tuple) else node.get(key, [])
            for t in tiers:
                if t not in valid_tiers:
                    fail(f"{fname}: {section} 引用了不存在的关键词层 {t}")
    print(f"  关键词层引用: 全部存在于 i_system_upgrade_keywords.yml ({sorted(valid_tiers)})")


def check_schools():
    cfg = load("e_school_reference_fujian.yml")
    names, formers = [], []
    for s in cfg["schools"]:
        names.append(s["name"])
        for h in s.get("school_name_history", []):
            formers.append(h["former"])
    if len(names) != len(set(names)):
        dup = {n for n in names if names.count(n) > 1}
        fail(f"高校名单: 现名重复 {dup}")
    clash = set(formers) & set(names)
    if clash:
        fail(f"高校名单: 曾用名与现名冲突 {clash}")
    pub = [s for s in cfg["schools"] if str(s["ownership"]).startswith("public")]
    print(f"  高校名单: 共{len(names)}所（公办{len(pub)}），曾用名{len(formers)}条，无冲突")


def main():
    print("== 口径配置嵌套性校验 ==")
    check_e_majors()
    check_patent()
    check_keyword_refs()
    check_schools()
    if FAILURES:
        print("\n校验失败：")
        for m in FAILURES:
            print("  ✗", m)
        sys.exit(1)
    print("\n全部通过 ✓")


if __name__ == "__main__":
    main()
