# -*- coding: utf-8 -*-
"""四柱排盘 + 日主强弱 + 喜用神（扶抑法为主口径）

年柱以立春为界（sxtwl getYearGZ(True)），月柱按节气。
藏干权重：本气1.0 中气0.5 余气0.3；天干1.0。
"""
from datetime import datetime

import sxtwl

from namelib import load_wuxing_rules

TIANGAN = "甲乙丙丁戊己庚辛壬癸"
DIZHI = "子丑寅卯辰巳午未申酉戌亥"
# 十二地支序 → 生肖
DIZHI_SHENGXIAO = dict(zip(DIZHI, "鼠牛虎兔龙蛇马羊猴鸡狗猪"))

# 藏干权重: 支 -> [(干, 本气1.0/中气0.5/余气0.3)]
CANGGAN = {
    "子": [("癸", 1.0)],
    "丑": [("己", 1.0), ("癸", 0.5), ("辛", 0.3)],
    "寅": [("甲", 1.0), ("丙", 0.5), ("戊", 0.3)],
    "卯": [("乙", 1.0)],
    "辰": [("戊", 1.0), ("乙", 0.5), ("癸", 0.3)],
    "巳": [("丙", 1.0), ("庚", 0.5), ("戊", 0.3)],
    "午": [("丁", 1.0), ("己", 0.5)],
    "未": [("己", 1.0), ("丁", 0.5), ("乙", 0.3)],
    "申": [("庚", 1.0), ("壬", 0.5), ("戊", 0.3)],
    "酉": [("辛", 1.0)],
    "戌": [("戊", 1.0), ("辛", 0.5), ("丁", 0.3)],
    "亥": [("壬", 1.0), ("甲", 0.5)],
}

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # 我生者
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}     # 我克者
SHENG_BY = {v: k for k, v in SHENG.items()}                            # 生我者
KE_BY = {v: k for k, v in KE.items()}                                  # 克我者


def paipan(birth: str):
    """birth: 'YYYY-MM-DD HH:MM' 或 'YYYY-MM-DD'（缺时辰则三柱）"""
    dt = datetime.strptime(birth.replace("/", "-").strip(), "%Y-%m-%d %H:%M" if len(birth.strip()) > 10 else "%Y-%m-%d")
    day = sxtwl.fromSolar(dt.year, dt.month, dt.day)
    y = day.getYearGZ(False)  # False = 以立春为年界（True 为正月初一界）
    m = day.getMonthGZ()
    d = day.getDayGZ()
    pillars = {
        "year": (TIANGAN[y.tg], DIZHI[y.dz]),
        "month": (TIANGAN[m.tg], DIZHI[m.dz]),
        "day": (TIANGAN[d.tg], DIZHI[d.dz]),
    }
    has_hour = len(birth.strip()) > 10
    if has_hour:
        h = day.getHourGZ(dt.hour)
        pillars["hour"] = (TIANGAN[h.tg], DIZHI[h.dz])
    return pillars, has_hour


def wuxing_count(pillars):
    """五行加权计数（含藏干）"""
    rules = load_wuxing_rules()
    tg_wx, dz_wx = rules["tiangan"], {k: v[0] for k, v in rules["dizhi_wuxing_yinyang"].items()}
    cnt = {"金": 0.0, "木": 0.0, "水": 0.0, "火": 0.0, "土": 0.0}
    for pillar in pillars.values():
        tg, dz = pillar
        cnt[tg_wx[tg]] += 1.0
        for gan, w in CANGGAN[dz]:
            cnt[tg_wx[gan]] += w
    return cnt


def day_master_strength(pillars):
    """日主强弱：同党(比劫+印) vs 异党(克泄耗) 占比"""
    rules = load_wuxing_rules()
    tg_wx = rules["tiangan"]
    dm_wx = tg_wx[pillars["day"][0]]
    tong = yi = 0.0
    for pillar in pillars.values():
        tg, dz = pillar
        for gan, w in [(tg, 1.0)] + CANGGAN[dz]:
            wx = tg_wx[gan]
            if wx == dm_wx or wx == SHENG_BY[dm_wx]:   # 同我 or 生我
                tong += w
            else:
                yi += w
    ratio = tong / (tong + yi)
    if ratio >= 0.60:
        level = "偏强"
    elif ratio >= 0.40:
        level = "中和"
    else:
        level = "偏弱"
    return level, round(ratio, 3)


def xiyongshen(pillars):
    """喜用神（扶抑法）：偏强→克(官杀)泄(食伤)耗(财)；偏弱→生(印)扶(比劫)；中和→以日主五行帮扶为主"""
    rules = load_wuxing_rules()
    dm_wx = rules["tiangan"][pillars["day"][0]]
    level, ratio = day_master_strength(pillars)
    if level == "偏强":
        primary = [KE[dm_wx], SHENG[dm_wx], KE_BY[dm_wx]]      # 克我、我生、我克
        reason = "日主偏强，宜克泄耗（官杀/食伤/财）"
    elif level == "偏弱":
        primary = [SHENG_BY[dm_wx], dm_wx]                      # 生我、同我
        reason = "日主偏弱，宜生扶（印/比劫）"
    else:
        primary = [dm_wx, SHENG_BY[dm_wx]]
        reason = "日主中和，以帮扶日主为主"
    # 忌神：与喜用对立方向（弱者忌克泄、强者忌生扶），取前两类
    if level == "偏弱":
        ji = [KE_BY[dm_wx], SHENG[dm_wx], KE[dm_wx]]
    else:
        ji = [SHENG_BY[dm_wx], dm_wx]
    return {
        "day_master": pillars["day"][0], "day_master_wuxing": dm_wx,
        "strength": level, "strength_ratio": ratio,
        "yongshen": primary, "jishen": ji, "method": "扶抑法", "reason": reason,
    }


def bazi_report(birth: str):
    pillars, has_hour = paipan(birth)
    cnt = wuxing_count(pillars)
    xys = xiyongshen(pillars)
    year_dz = pillars["year"][1]
    return {
        "birth": birth.strip(),
        "has_hour": has_hour,
        "pillars": {k: "".join(v) for k, v in pillars.items()},
        "wuxing_count": {k: round(v, 1) for k, v in cnt.items()},
        "wuxing_missing": [k for k, v in cnt.items() if v < 0.3],
        "wuxing_weak": sorted(cnt, key=lambda k: cnt[k])[:2],
        "zodiac": DIZHI_SHENGXIAO[year_dz],
        "zodiac_note": "属相按立春口径" ,
        **xys,
    }


if __name__ == "__main__":
    import sys
    import json
    print(json.dumps(bazi_report(sys.argv[1]), ensure_ascii=False, indent=2))
