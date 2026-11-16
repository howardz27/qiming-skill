# -*- coding: utf-8 -*-
"""起名检索统一入口 CLI

用法：
  python search.py --surname 张 --gender M [--birth "2026-03-01 10:23"] \
      [--dims bazi,sancai,zodiac] [--style traditional|balanced|modern] \
      [--exclude 梓,涵] [--style_tag classic|generated|all] [--top 12] [--json]

无 birth 时跳过八字/生肖维度（权重重分配），仍给出五格+音韵+实用性推荐。
"""
import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

import namelib
from bazi import bazi_report
from phonology import homophone_check, phonology_score
from popularity import popularity_score
from realism import realism_info
from sancai import wuge
from scorer import HARD_MIN, bazi_match_score, combine, meaning_score
from zodiac import zodiac_score


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--surname", required=True)
    p.add_argument("--gender", choices=["M", "F", "N"], default="N")
    p.add_argument("--birth", default=None, help="YYYY-MM-DD[ HH:MM]，缺时辰则三柱")
    p.add_argument("--dims", default=None, help="关闭的维度，如 --dims-off bazi,zodiac")
    p.add_argument("--dims-off", default="", help="关闭维度列表（逗号分隔）")
    p.add_argument("--style", default="traditional", choices=["traditional", "balanced", "modern"])
    p.add_argument("--style_tag", default="all", choices=["classic", "modern", "generated", "all"])
    p.add_argument("--vibe", default="", help="风格偏好：清雅/文气/大气/灵动/硬朗/甜美（软性加分惩罚，非硬过滤）")
    p.add_argument("--exclude", default="", help="排除字，逗号分隔")
    p.add_argument("--popularity", default="neutral", choices=["niche", "neutral", "common"],
                   help="重名偏好：niche=小众(爆款强惩罚) neutral=不限 common=大众(爆款不惩罚)")
    p.add_argument("--top", type=int, default=12)
    p.add_argument("--avoid", default="", help="避讳长辈用字，逗号分隔（硬过滤）")
    p.add_argument("--require-real", action="store_true",
                   help="硬过滤：120万真人名库中未出现的名字（剔除古籍断句产物如 果来/家可）")
    p.add_argument("--json", action="store_true")
    return p.parse_args()


def gen_candidates(yongshen=None, gender="N", cap=4000):
    """从字库生成候选：喜用五行优先 + 性别兼容 + 声调相异"""
    chars_lib = namelib.load_chars()
    pool = []
    for c, r in chars_lib.items():
        g = r["gender"]
        if gender in ("M", "F") and g not in (gender, "N"):
            continue
        if not r.get("kangxi"):
            continue
        pool.append(c)
    yong_set = set(yongshen or [])
    out = []
    # 优先两字均命中喜用，其次单字命中
    hit1 = [c for c in pool if chars_lib[c]["wuxing"] in yong_set] if yong_set else pool
    for a in hit1:
        for b in hit1:
            if a >= b:
                continue
            ra, rb = chars_lib[a], chars_lib[b]
            if ra["tone"] == rb["tone"] and ra["tone"] != 0:
                continue
            out.append({"name": a + b, "chars": [a, b], "type": "generated", "source": None,
                        "gender_hint": ra["gender"] if ra["gender"] != "N" else rb["gender"]})
            if len(out) >= cap:
                return out
    return out


# 典籍出句语境贬义模式：句中对名字本身或语境持否定/哀婉态度时弃用
NEG_SENTENCE_PATTERNS = [
    "变而不", "而不芳", "不芳", "彫", "凋", "落尽", "无凭", "憔悴",
    "寂寞", "孤", "寡", "衰", "哭", "泪", "断", "老去", "悲", "怨",
]


def hard_filter(surname, cand, exclude_set, bad_pairs):
    name, chars = cand["name"], cand["chars"]
    if exclude_set & set(chars):
        return None
    if name in bad_pairs:
        return None
    # 典籍名语境检查：出句含贬义/哀婉模式则弃用（如「兰芷变而不芳兮」）
    if cand.get("type") == "classic":
        sent = (cand.get("source") or {}).get("sentence") or ""
        if any(p in sent for p in NEG_SENTENCE_PATTERNS):
            return None
    hits = homophone_check(surname, name)
    if hits:
        return None
    return True


def evaluate(surname, cand, args, bazi_r):
    dims, reasons = {}, {}
    given = cand["chars"]
    if bazi_r:
        bm = bazi_match_score(bazi_r["yongshen"], bazi_r["jishen"], given)
        dims["bazi"] = bm["score"]
        reasons["bazi"] = f"喜用{bm['yongshen']}，名局五行{bm['wuxing']}，命中{bm['hits'] or '无'}"
    dims["meaning"] = meaning_score(cand)["score"]
    if (cand.get("source") or {}).get("book"):
        src = cand["source"]
        reasons["meaning"] = f"出自{src['book']}·{src['title']}：「{src['sentence']}」"
    ph = phonology_score(surname, cand["name"])
    ri = realism_info(cand["name"], args.gender if hasattr(args, "gender") else "N")
    reasons["realism"] = ri["note"]
    if getattr(args, "require_real", False) and ri["n"] == 0:
        return None
    dims["phonology"] = ph["score"]
    pop = popularity_score(cand["name"], args.popularity)
    dims["popularity"] = pop["score"]
    reasons["popularity"] = pop["detail"]["hotness"]["niche_level"]
    wg = wuge(surname, cand["name"])
    if "error" in wg:
        return None
    dims["sancai"] = wg["score"]
    if dims["sancai"] < HARD_MIN["sancai"]:
        return None  # 三才大凶硬过滤
    if bazi_r:
        zs = zodiac_score(bazi_r["zodiac"], cand["name"])
        dims["zodiac"] = zs["score"]
        if zs["good_hits"] or zs["bad_hits"]:
            reasons["zodiac"] = f"生肖{zs['zodiac']}：喜字根{zs['good_hits'] or '无'} 忌字根{zs['bad_hits'] or '无'}"
    total, weights = combine(dims, preset=args.style, off_dims=args.off_dims)
    # 风格偏好（--vibe）：软性加分惩罚。双字合风格+5，单字0，全不合-8
    if getattr(args, "vibe", ""):
        chars_lib = namelib.load_chars()
        match = sum(1 for c in given if args.vibe in (chars_lib.get(c, {}).get("vibe") or []))
        if match == len(given):
            total = min(100.0, total + 5)
            reasons["vibe"] = f"风格{args.vibe}：双字契合"
        elif match == 0:
            total = max(0.0, total - 8)
        else:
            reasons["vibe"] = f"风格{args.vibe}：{match}/{len(given)}字契合"
    result = {
        "name": surname + cand["name"], "given": cand["name"],
        "gender_hint": cand.get("gender_hint", "N"),
        "type": cand["type"], "score": total,
        "dims": dims, "reasons": {k: v for k, v in reasons.items() if v},
        "wuge": {"grids": wg["grids"], "sancai": wg["sancai"]["wuxing"] + f"({wg['sancai']['rating']})"},
        "pinyin": " ".join(namelib_full_pinyin(surname, cand["name"])),
    }
    if cand.get("source"):
        result["source"] = cand["source"]
    return result


def namelib_full_pinyin(surname, given):
    from phonology import full_pinyin
    return full_pinyin(surname, given)


def main():
    args = parse_args()
    sur = namelib.load_surname(args.surname)
    if not sur:
        print(json.dumps({"error": f"姓氏 {args.surname} 不在库中"}, ensure_ascii=False))
        return
    args.off_dims = {d.strip() for d in args.dims_off.split(",") if d.strip()}
    exclude_set = {c.strip() for c in (args.exclude + "," + args.avoid).split(",") if c.strip()}

    bazi_r = None
    if args.birth:
        bazi_r = bazi_report(args.birth)
        if args.style_tag in ("all",):
            args.off_dims.discard("bazi")
    else:
        args.off_dims |= {"bazi", "zodiac"}

    candidates = []
    if args.style_tag in ("classic", "all"):
        for r in namelib.load_classic_names():
            if args.gender in ("M", "F") and r["gender_hint"] not in (args.gender, "N"):
                continue
            candidates.append(r)
    if args.style_tag in ("modern", "all"):
        for r in namelib.load_modern_names():
            if args.gender in ("M", "F") and r["gender_hint"] not in (args.gender, "N"):
                continue
            candidates.append(r)
    if args.style_tag in ("generated", "all"):
        yong = bazi_r["yongshen"] if bazi_r else None
        candidates += gen_candidates(yong, args.gender)

    seen, results = set(), []
    bad_pairs = set(namelib.load_name_blocklist())
    for cand in candidates:
        if cand["name"] in seen:
            continue
        seen.add(cand["name"])
        if hard_filter(args.surname, cand, exclude_set, bad_pairs) is None:
            continue
        r = evaluate(args.surname, cand, args, bazi_r)
        if r:
            results.append(r)
    results.sort(key=lambda r: -r["score"])
    # 八字喜水 vs 生肖忌氵字根的体系冲突提示
    if bazi_r and "水" in (bazi_r.get("yongshen") or []):
        chars_lib = namelib.load_chars()
        conflict = [c for c, r in chars_lib.items()
                    if r.get("wuxing") == "水" and bazi_r["zodiac"] in (r.get("zodiac_bad") or [])]
        if conflict:
            bazi_r = dict(bazi_r)
            bazi_r["note_conflict"] = (
                f"八字喜水，但生肖{bazi_r['zodiac']}民俗忌部分氵字根（如{''.join(conflict[:6])}）。"
                "两套体系口径不同，可选不带氵而五行属水的字（如月/白/雨/云）两全。"
            )
    out = {
        "query": {
            "surname": args.surname, "gender": args.gender,
            "birth": args.birth, "style": args.style,
            "vibe": args.vibe or None,
            "popularity_pref": args.popularity,
            "excluded_chars": sorted(exclude_set),
        },
        "bazi": bazi_r,
        "count_total": len(results),
        "top": results[: args.top],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
