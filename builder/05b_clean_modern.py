# -*- coding: utf-8 -*-
"""05b_clean_modern.py — 清洗 names_modern.jsonl

问题：现代库初创时混入了出处为古文的条目（望舒出自《离骚》、白鹭出自杜甫、
汀洲出自《楚辞》…），导致"现代风"名不副实。

规则：出处引用了古籍/古代作家的条目 → 类别改为「古典化用」，保留条目但降级
（BOOK_ELEGANCE 由 16-20 降至 14，scorer 中配置）。
真正的现代来源保持原类别：自然意象/现代文学/品格格言/新中式。

用法：python builder/05b_clean_modern.py
"""
import json
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(BASE, "knowledge", "names_modern.jsonl")

# 古文出处信号（出现在 title 或 sentence 中即判定）
CLASSICAL_MARKS = [
    "诗经", "楚辞", "离骚", "论语", "大学", "中庸", "老子", "孟子",
    "诫子书", "王阳明", "陶渊明", "诸葛亮",
    "李白", "杜甫", "崔颢", "白居易", "李清照", "贺铸", "王维", "柳如是",
    "唐诗", "宋词", "古诗", "《离骚》", "《诗经》", "《楚辞》", "《孟子》", "《老子》",
    "《大学》", "《中庸》", "《论语》",
]


def is_classical(src):
    text = (src.get("title") or "") + " " + (src.get("sentence") or "")
    return any(m in text for m in CLASSICAL_MARKS)


def main():
    rows = [json.loads(l) for l in open(PATH, encoding="utf-8")]
    moved = []
    for r in rows:
        if is_classical(r["source"]):
            old = r["source"]["book"]
            r["source"]["book"] = "古典化用"
            r["origin_classical"] = True
            moved.append((r["name"], old))
    with open(PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"total {len(rows)}, 重分类为古典化用 {len(moved)} 条:")
    for n, old in moved:
        print(f"  {n}  ({old})")
    from collections import Counter
    cnt = Counter(r["source"]["book"] for r in rows)
    print("类别分布:", dict(cnt))


if __name__ == "__main__":
    main()
