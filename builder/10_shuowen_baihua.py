# -*- coding: utf-8 -*-
"""10_shuowen_baihua.py — 汉字白话释义库（维基词典）

语料：data/wiktionary/raw-wiktextract-data.jsonl.gz
（来源 kaikki.org 对中文维基词典 dump 的 wiktextract 提取版，
许可 CC BY-SA 4.0 + GFDL，与维基词典一致；约 1.9GB 解压后逐行 JSON）

处理：
- 只取 lang=漢語 的单字条目，按 OpenCC t2s 转简后建立字索引
  （word 本身可能是繁体页标题；另收录 forms 中 Simplified-Chinese 单字形式）
- 每个 senses[].glosses 为白话释义（繁体）→ 转简；跳过 no-gloss
- 保留至多 1 条带白话译文的例句（例句原文 + 译文 + 出处）
- 只输出说文字头 ∪ 起名字库的字，控制体积

产出：knowledge/char_baihua.json
{"comment": ..., "total": N, "chars": {"洵": {"glosses": ["诚然，实在…"],
  "example": {"text": "…洵美且仁。", "trans": "确实俊美又仁慈。", "ref": "《诗经》…"}}}}

用法：python builder/10_shuowen_baihua.py
"""
import gzip
import json
import os

from opencc import OpenCC

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "wiktionary", "raw-wiktextract-data.jsonl.gz")
XINHUA = os.path.join(BASE, "data", "wiktionary", "xinhua-word.json")
OUT = os.path.join(BASE, "knowledge", "char_baihua.json")
T2S = OpenCC("t2s")

MAX_GLOSSES = 4
XINHUA_MAX = 300  # 新华释义清洗后截断长度


def _extract_senses(entry):
    """返回 (glosses, best_example)；glosses 转简、去重"""
    glosses, seen = [], set()
    example = None
    for s in entry.get("senses") or []:
        if "no-gloss" in (s.get("tags") or []):
            continue
        for g in s.get("glosses") or []:
            g = T2S.convert(g).strip()
            if any(mk in g for mk in ("^", "‡", "†", "{", "}", "[")):
                continue  # wikitext 残留标记
            if g and g not in seen and len(g) <= 60:
                seen.add(g)
                glosses.append(g)
        if example is None:
            for e in s.get("examples") or []:
                trans = e.get("translation")
                if trans:  # 只要带白话译文的例句
                    example = {
                        "text": T2S.convert(e.get("text") or ""),
                        "trans": T2S.convert(trans),
                        "ref": T2S.convert(e.get("ref") or ""),
                    }
                    break
    return glosses, example


def main():
    # 目标字集：说文字头 ∪ 起名字库
    with open(os.path.join(BASE, "knowledge", "shuowen.json"), encoding="utf-8") as f:
        targets = set(json.load(f)["chars"])
    with open(os.path.join(BASE, "knowledge", "chars.jsonl"), encoding="utf-8") as f:
        targets |= {json.loads(line)["char"] for line in f}
    targets = {t for t in targets if len(t) == 1}

    chars = {}
    with gzip.open(RAW, "rt", encoding="utf-8") as f:
        for line in f:
            if '"lang": "漢語"' not in line:
                continue
            d = json.loads(line)
            word = d.get("word") or ""
            if len(word) != 1:
                continue
            heads = {T2S.convert(word)}
            for fm in d.get("forms") or []:
                form = fm.get("form") or ""
                if len(form) == 1 and "Simplified-Chinese" in (fm.get("tags") or []):
                    heads.add(T2S.convert(form))
            heads &= targets
            if not heads:
                continue
            glosses, example = _extract_senses(d)
            if not glosses:
                continue
            for h in heads:
                cur = chars.setdefault(h, {"glosses": [], "example": None})
                for g in glosses:
                    if g not in cur["glosses"] and len(cur["glosses"]) < MAX_GLOSSES * 2:
                        cur["glosses"].append(g)
                if example and not cur["example"]:
                    cur["example"] = example

    for v in chars.values():
        v["glosses"] = v["glosses"][:MAX_GLOSSES]

    # 第二层：新华字典释义（pwxcoo/chinese-xinhua）补维基词典未覆盖的字。
    # 数据本体为汉典/新华字典汇编，权属存疑——只作本地查询参考。
    xinhua_hit = 0
    if os.path.exists(XINHUA):
        import re
        with open(XINHUA, encoding="utf-8") as f:
            for x in json.load(f):
                w = x.get("word") or ""
                if len(w) != 1 or w in chars or w not in targets:
                    continue
                expl = x.get("explanation") or ""
                # 清洗：去字头重复、合并空白
                expl = re.sub(rf"^{re.escape(w)}\s*", "", expl.strip())
                expl = re.sub(r"\s*\n\s*", " ", expl)
                expl = re.sub(r"\s{2,}", " ", expl).strip()
                if not expl:
                    continue
                chars[w] = {"glosses": [expl[:XINHUA_MAX]], "xinhua": True}
                xinhua_hit += 1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"comment": "汉字白话释义与例句；来源：中文维基词典（经 kaikki.org "
                              "wiktextract 提取，dump 2026-11-01）；许可 CC BY-SA 4.0 + GFDL，"
                              "https://creativecommons.org/licenses/by-sa/4.0/；"
                              "xinhua=true 的条目来自 pwxcoo/chinese-xinhua（新华字典/汉典汇编，"
                              "权属存疑，仅本地参考）；释义由繁体转简，覆盖说文字头∪起名字库",
                   "total": len(chars), "chars": chars}, f, ensure_ascii=False)
    print(f"目标字 {len(targets)}，白话释义 {len(chars)}（维基 {len(chars)-xinhua_hit} + "
          f"新华补 {xinhua_hit}，覆盖率 {len(chars) / len(targets):.0%}）-> {OUT}")


if __name__ == "__main__":
    main()
