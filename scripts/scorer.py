# -*- coding: utf-8 -*-
"""加权综合评分：维度开关时权重按比例重分配。

维度权重（全开，总100）：八字五行25 / 字义20 / 音韵20 / 实用性15 / 三才五格10 / 生肖10
"""
from namelib import load_chars

WEIGHTS = {
    "bazi": 25, "meaning": 20, "phonology": 20,
    "popularity": 15, "sancai": 10, "zodiac": 10,
}
PRESETS = {
    "traditional": dict(WEIGHTS),  # 全开
    "balanced": {"bazi": 20, "meaning": 20, "phonology": 20, "popularity": 15, "sancai": 15, "zodiac": 10},
    "modern": {"bazi": 0, "meaning": 30, "phonology": 25, "popularity": 35, "sancai": 0, "zodiac": 10},
}
HARD_MIN = {"sancai": 20}  # 三才大凶硬过滤阈值


def bazi_match_score(yongshen, jishen, given):
    """双字对喜用神的命中：双中=100 单中=75 无=40 命中忌神递减"""
    chars_lib = load_chars()
    rs = [chars_lib.get(c) for c in given]
    wux = [r["wuxing"] for r in rs if r]
    score = 40.0
    hits = []
    for w in wux:
        if w in yongshen[:2]:
            score += 30 if len(hits) < 2 else 10
            hits.append(w)
        elif w in yongshen:
            score += 12
            hits.append(w)
    for w in wux:
        if w in jishen:
            score -= 20
    return {"score": max(0, min(100, score)), "hits": hits,
            "wuxing": wux, "yongshen": yongshen[:2]}


# 典籍出处典雅度分级（诗意>经传散文，供寓意分加权）
BOOK_ELEGANCE = {
    "诗经": 28, "楚辞": 26, "南唐词": 22, "唐诗三百首": 22, "千家诗": 20,
    "中庸": 18, "大学": 18, "论语": 18, "孟子": 14, "古文观止": 12,
    # 现代来源（names_modern.jsonl）
    "自然意象": 18, "现代文学": 20, "品格格言": 16, "新中式": 17,
    "古典化用": 14,  # 现代结构但出处为古文，降级
}

def meaning_score(candidate):
    """字义寓意：出处加分 + 种子字义覆盖度 + 俗气字惩罚"""
    chars_lib = load_chars()
    given = candidate["chars"]
    base = 50
    src = candidate.get("source") or {}
    if src.get("book"):
        base += BOOK_ELEGANCE.get(src["book"], 15)
    meanings = [chars_lib[c]["meaning"] for c in given if c in chars_lib and chars_lib[c].get("meaning")]
    base += min(len(meanings), 2) * 8
    # 字义长度粗略代表信息量
    base += min(sum(len(m) for m in meanings) // 10, 6)
    # 俗气字惩罚：直白/老派字（花、朵、福、凤…）命中一字小扣、双字大扣
    risk = sum(1 for c in given if chars_lib.get(c, {}).get("taste_risk"))
    if risk == 1:
        base -= 12
    elif risk >= 2:
        base -= 28
    return {"score": max(0, min(base, 100)), "source": src,
            "meanings": {c: m for c, m in zip(given, meanings)}}


def combine(dim_scores, preset="traditional", off_dims=()):
    """dim_scores: {dim: score}; 返回加权总分与实际权重"""
    weights = dict(PRESETS[preset])
    for d in off_dims:
        if d in weights:
            weights[d] = 0
    total_w = sum(weights.values())
    if total_w == 0:
        return 0, weights
    score = sum(dim_scores.get(d, 0) * w for d, w in weights.items()) / total_w
    return round(score, 1), {d: round(w / total_w * 100, 1) for d, w in weights.items() if w}
