# -*- coding: utf-8 -*-
"""现代实用性：爆款重名惩罚 / 生僻字 / 多音字 / 书写复杂度

爆款数据驱动：knowledge/name_stats.json（公安部《二〇二一年全国姓名报告》，
最新一期官方数据）。字热度 = 95 - (排名-1)，排名1-50。
"""
from namelib import load_chars, load_name_stats

_HOT_CHARS = None
_HOT_NAMES = None
_STOCK_NAMES = None
_TOP50 = None


def _hot_data():
    global _HOT_CHARS, _HOT_NAMES, _STOCK_NAMES, _TOP50
    if _HOT_CHARS is None:
        stats = load_name_stats()
        # 第1名热度95，线性递减，第50名热度46
        _TOP50 = stats["hot_chars_top50_2021"]
        _HOT_CHARS = {c: 95 - i for i, c in enumerate(_TOP50)}
        _HOT_NAMES = set(stats["hot_given_names_2021"]["M"] + stats["hot_given_names_2021"]["F"])
        _STOCK_NAMES = set(stats["stock_double_names"])
    return _HOT_CHARS, _HOT_NAMES, _STOCK_NAMES, _TOP50


def popularity_score(given: str, pref: str = "neutral"):
    """pref: niche=小众（爆款强惩罚）/ neutral=中性 / common=大众（爆款不惩罚）"""
    chars_lib = load_chars()
    hot_chars, hot_names, stock_names, top50 = _hot_data()
    rs = [chars_lib.get(c) for c in given]
    detail = {}
    # 爆款惩罚 40：整名命中当年Top10或存量重名Top10 → 最低档；否则按最热单字分档
    hot_char = max((hot_chars.get(c, 0) for c in given), default=0)
    exact_hot = given in hot_names or given in stock_names
    hot = 100 if exact_hot else hot_char
    if pref == "niche":
        # 小众模式：上榜字（热度≥85即Top11-）几乎不给分，爆款名直接0
        hot_score = 40 if hot < 50 else (25 if hot < 70 else (8 if hot < 85 else 0))
    elif pref == "common":
        # 大众模式：重名不敏感，仅整名爆款轻微提示
        hot_score = 40 if not exact_hot else 25
    else:
        hot_score = 40 if hot < 50 else (28 if hot < 70 else (15 if hot < 85 else (5 if hot < 96 else 0)))
    # 小众程度标签（供解读）：取双字中最高排名
    ranks = [top50.index(c) + 1 for c in given if c in top50]
    if exact_hot:
        niche_level = "爆款名（2021年全国Top10/存量Top10）"
    elif not ranks:
        niche_level = "小众（双字均不在2021年TOP50热字）"
    elif max(ranks) > 25:
        niche_level = "偏低频（热字榜26-50名）"
    elif max(ranks) > 10:
        niche_level = "常见（热字榜11-25名）"
    else:
        niche_level = "高频（热字榜Top10）"
    detail["hotness"] = {
        "max_char_hot": hot_char, "exact_top10_hit": exact_hot,
        "hot_char_ranks": {c: top50.index(c) + 1 for c in given if c in top50},
        "niche_level": niche_level, "pref": pref,
        "score": hot_score, "max": 40,
        "basis": "公安部2021年全国姓名报告",
    }
    # 生僻/户籍风险 35：康熙笔画>25 或 simplified>20 风险
    rare = 35
    rare_chars = []
    for ch, r in zip(given, rs):
        if not r:
            rare_chars.append(ch)
            rare -= 18
        else:
            simp = r.get("simplified") or 0
            if simp > 20 or (r.get("kangxi") or 0) > 25:
                rare_chars.append(ch)
                rare -= 15
    detail["rare"] = {"score": max(rare, 0), "max": 35, "chars": rare_chars}
    # 多音字/书写 25
    poly = 25
    poly_chars = []
    for ch, r in zip(given, rs):
        if r and r.get("is_polyphone"):
            poly_chars.append(ch)
            poly -= 8
    detail["polyphone"] = {"score": max(poly, 0), "max": 25, "chars": poly_chars}
    score = hot_score + max(rare, 0) + max(poly, 0)
    return {"score": min(score, 100), "detail": detail}
