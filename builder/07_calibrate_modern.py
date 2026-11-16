# -*- coding: utf-8 -*-
"""07_calibrate_modern.py — 用真实姓名数据定义"现代感"

数据源：公安部《二〇二一年全国姓名报告》（knowledge/name_stats.json）
- 2021新生儿50热字、男女Top10名、增速最快字
- 从爆款名反推当代取名结构特征：虚字组合 / 动词开头 / 意象并列

产出：
1. knowledge/modern_calibration.json —— 校准报告（热字集合、结构特征统计）
2. names_modern.jsonl 每条加 structure 字段（虚字组合/动词开头/意象并列/其他）

用法：python builder/07_calibrate_modern.py
"""
import json
import os
import sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))

STATS = os.path.join(BASE, "knowledge", "name_stats.json")
MODERN = os.path.join(BASE, "knowledge", "names_modern.jsonl")
OUT = os.path.join(BASE, "knowledge", "modern_calibration.json")

# 结构分类器（基于2021爆款名的语言特征归纳）
XUZI = set("一亦以可若如予于之未知与")     # 虚字：一诺/若汐/依诺/苡沫
VERB_FIRST = set("听望见闻知思念观归沐予乐守")  # 动词开头：听澜/望山/沐宸


def classify(name):
    a, b = name[0], name[1]
    if a in XUZI and a not in VERB_FIRST:
        return "虚字组合"
    if a in VERB_FIRST:
        return "动词开头"
    if b in XUZI and a not in XUZI:
        return "虚字收尾"
    return "意象并列"


def main():
    stats = json.load(open(STATS, encoding="utf-8"))
    hot50 = set(stats["hot_chars_top50_2021"])
    hot_names = set(stats["hot_given_names_2021"]["M"] + stats["hot_given_names_2021"]["F"])
    rising = set(stats["rising_chars_2021_vs_2020"])

    # 爆款名的结构统计（定义"当代语感"）
    top_struct = Counter(classify(n) for n in hot_names)

    rows = [json.loads(l) for l in open(MODERN, encoding="utf-8")]
    for r in rows:
        r["structure"] = classify(r["name"])
    with open(MODERN, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 我们的库 vs 爆款的对照
    ours_struct = Counter(r["structure"] for r in rows)
    ours_hot = sorted({c for r in rows for c in r["name"] if c in hot50})
    ours_rising = sorted({c for r in rows for c in r["name"] if c in rising})

    calib = {
        "comment": "现代感校准：以公安部2021报告为真实数据锚点",
        "hot_chars_top50_2021": sorted(hot50),
        "rising_chars": sorted(rising),
        "hot_name_structures": {k: v for k, v in top_struct.items()},
        "modern_corpus_structures": {k: v for k, v in ours_struct.items()},
        "modern_corpus_hot_chars": ours_hot,
        "modern_corpus_rising_chars": ours_rising,
        "structure_defs": {
            "虚字组合": f"首字∈{sorted(XUZI)}——爆款名主流（若汐/一诺/苡沫）",
            "动词开头": f"首字∈{sorted(VERB_FIRST)}——白描叙事感（听澜/望山）",
            "虚字收尾": "次字为虚字（知许/南乔）",
            "意象并列": "双实字并列（星河/晚棠）",
        },
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(calib, f, ensure_ascii=False, indent=1)

    print("爆款名结构:", dict(top_struct))
    print("现代库结构:", dict(ours_struct))
    print("现代库含2021热字:", "".join(ours_hot))
    print("现代库含上升字(汐芮霖航):", "".join(ours_rising))
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
