# -*- coding: utf-8 -*-
"""音韵学评分：平仄/声韵/开口呼/谐音检测"""
from pypinyin import pinyin, Style

from namelib import load_chars, load_homophone_blocklist, load_surname

PINGZE = {1: "平", 2: "平", 3: "仄", 4: "仄", 0: "仄"}


def full_pinyin(surname, given, tone3=False):
    sur = load_surname(surname)
    chars_lib = load_chars()
    parts = []
    if sur:
        for p in sur["pinyin_tone3"].split():
            parts.append(p if tone3 else p.rstrip("12345"))
    else:
        for c in surname:
            r = chars_lib.get(c)
            if r:
                parts.append(r["pinyin"])
    for c in given:
        r = chars_lib.get(c)
        if r:
            parts.append(r["pinyin"] if not tone3 else f"{r['pinyin']}{r['tone']}")
        else:
            parts.append(pinyin(c, style=Style.TONE3, heteronym=False)[0][0].rstrip("12345"))
    return parts


_blocklist_flat = None

def _get_blocklist_flat():
    global _blocklist_flat
    if _blocklist_flat is None:
        bl = load_homophone_blocklist()
        flat = []
        for word in bl["multi_char_words"]:
            wpy = "".join(p[0].rstrip("12345") for p in pinyin(word, style=Style.TONE3, heteronym=False))
            flat.append((word, wpy))
        singles = []
        for ch in bl["single_char_with_tone"]:
            # 只取主读音：heteronym 会带出生僻古音（如屎的xī），造成误拦
            singles.append((ch, pinyin(ch, style=Style.TONE3, heteronym=False)[0][0]))
        _blocklist_flat = (flat, singles)
    return _blocklist_flat


def homophone_check(surname, given):
    """全名谐音检测：多字词无声调匹配 + 单字词带声调匹配。返回命中列表。"""
    bl = load_homophone_blocklist()
    py_no_tone = "".join(full_pinyin(surname, given))
    py_tone = "".join(full_pinyin(surname, given, tone3=True))
    flat, singles = _get_blocklist_flat()
    hits = []
    for word, wpy in flat:
        if wpy in py_no_tone:
            hits.append({"word": word, "mode": "multi"})
            if len(hits) >= 3:
                break
    for ch, t3 in singles:
        if t3 in py_tone:
            hits.append({"word": ch, "mode": "single_tone", "pinyin": t3})
            break
    return hits


def phonology_score(surname, given):
    """音韵评分 0-100 与明细"""
    chars_lib = load_chars()
    rs = [chars_lib.get(c) for c in given]
    detail = {}
    # 平仄 40
    pz = [PINGZE.get(r["tone"], "仄") if r else "仄" for r in rs]
    if len(pz) == 2:
        pz_score = 40 if pz[0] != pz[1] else 28
    else:
        pz_score = 35
    detail["pingze"] = {"pattern": "".join(pz), "score": pz_score, "max": 40}
    # 声韵多样 30：声母相同扣、韵母相同(叠韵)扣、整体读音同音扣
    sm = [r["shengmu"] for r in rs if r]
    ym = [r["yunmu"] for r in rs if r]
    var = 30
    if len(sm) == 2 and sm[0] and sm[0] == sm[1]:
        var -= 8
    if len(ym) == 2 and ym[0] == ym[1]:
        var -= 10
    # 姓与名首字声母相同（拗口）
    sur = load_surname(surname)
    if sur and not sur["is_compound"] and rs and rs[0] and rs[0]["shengmu"]:
        sur_py = sur["pinyin_tone3"].rstrip("12345")
        if sur_py and sur_py[0] == rs[0]["shengmu"][0]:
            var -= 5
    detail["variety"] = {"score": max(var, 0), "max": 30}
    # 开口呼结尾 15：末字韵母开口呼更响亮
    open_end = bool(rs[-1]["kaimou"]) if rs and rs[-1] else False
    detail["open_ending"] = {"score": 15 if open_end else 8, "max": 15, "hit": open_end}
    # 谐音 15
    hits = homophone_check(surname, given)
    detail["homophone"] = {"score": 0 if hits else 15, "max": 15, "hits": hits}
    score = pz_score + max(var, 0) + detail["open_ending"]["score"] + detail["homophone"]["score"]
    return {"score": score, "detail": detail}


if __name__ == "__main__":
    import sys
    import json
    print(json.dumps(phonology_score(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
