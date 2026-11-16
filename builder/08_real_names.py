# -*- coding: utf-8 -*-
"""08_real_names.py — 真实人名频次表

语料：data/real_names/Chinese_Names_Corpus_Gender_120W.txt
（来源 wainshine/Chinese-Names-Corpus，公开人物名录收集，格式 `名,性别`，
混合 3 字全名与 2 字纯名；性别 ∈ {男,女,未知}）

处理：
- 3 字条目按 surnames.json 剥姓氏（复姓优先最长匹配），取双字名
- 2 字条目直接视为双字名
- 统计每个双字名的总次数 / 女性次数（n>=2 才收录，过滤孤例噪声）

产出：knowledge/real_name_freq.json  {"名": [总次数, 女性次数], ...}

用法：python builder/08_real_names.py
"""
import json
import os
from collections import defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "real_names", "Chinese_Names_Corpus_Gender_120W.txt")
OUT = os.path.join(BASE, "knowledge", "real_name_freq.json")


def main():
    surnames = json.load(open(os.path.join(BASE, "knowledge", "surnames.json"),
                              encoding="utf-8"))["surnames"]
    sur2 = {r["surname"] for r in surnames if len(r["surname"]) == 2}
    sur1 = {r["surname"] for r in surnames if len(r["surname"]) == 1}

    freq = defaultdict(lambda: [0, 0])  # name -> [n_total, n_female]
    total = used = 0
    for line in open(RAW, encoding="utf-8-sig"):
        total += 1
        parts = line.strip().split(",")
        if len(parts) != 2 or "," in parts[1]:
            continue
        name, sex = parts
        if len(name) == 2:
            given = name
        elif len(name) == 3:
            if name[:2] in sur2:
                given = name[2:]
            elif name[0] in sur1:
                given = name[1:]
            else:
                continue  # 非常规姓氏开头，可能是纯名叠字等，跳过
        else:
            continue
        if len(given) != 2:
            continue
        used += 1
        freq[given][0] += 1
        if sex == "女":
            freq[given][1] += 1

    kept = {k: v for k, v in freq.items() if v[0] >= 2}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"comment": "真实人名双字名频次 [总次数, 女性次数]；"
                              "语料: wainshine/Chinese-Names-Corpus 120W（公开人物名录）",
                   "corpus_lines": total, "given_parsed": used,
                   "names": kept}, f, ensure_ascii=False)
    print(f"语料 {total} 行，解析双字名 {used} 条，"
          f"唯一名 {len(freq)}，收录(n>=2) {len(kept)} -> {OUT}")


if __name__ == "__main__":
    main()
