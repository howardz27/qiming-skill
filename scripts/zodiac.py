# -*- coding: utf-8 -*-
"""生肖宜忌评分：字根规则（chars.jsonl 构建期已打标 zodiac_good/zodiac_bad）"""
from namelib import load_chars


def zodiac_score(zodiac: str, given: str):
    """given: 名字（不含姓）。0-100"""
    chars_lib = load_chars()
    rs = [chars_lib.get(c) for c in given]
    hits_good, hits_bad = [], []
    for ch, r in zip(given, rs):
        if not r:
            continue
        if zodiac in (r.get("zodiac_good") or []):
            hits_good.append(ch)
        if zodiac in (r.get("zodiac_bad") or []):
            hits_bad.append(ch)
    n = len(given)
    score = 70  # 无命中基准分
    score += min(len(hits_good), n) * 15
    score -= min(len(hits_bad), n) * 35
    score = max(0, min(100, score))
    return {
        "score": score, "zodiac": zodiac,
        "good_hits": hits_good, "bad_hits": hits_bad,
        "note": "字根宜忌按传统生肖规则，仅作参考维度",
    }
