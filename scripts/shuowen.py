# -*- coding: utf-8 -*-
"""说文解字检索：按字义（义训关键词）/ 部首 / 读音查字，服务「按字义选字起名」。

数据：knowledge/shuowen.json（来源 shuowenjiezi/shuowen，Apache-2.0，10874 简体字头）

用法：
  python scripts/shuowen.py --sense "清 澄 湛" [--top 30] [--surname 朱]
      按义训关键词子串检索（gloss 简体 + original 繁体双字段，多词 OR，
      命中词数多者优先）
  python scripts/shuowen.py --radical 水 [--top N]
  python scripts/shuowen.py --pinyin xun          # 前缀匹配，不带声调
  python scripts/shuowen.py --char 洵             # 单字查询

输出 JSON：每字含 字头/部首/说文原文/简体gloss/拼音/反切/in_lib（653字库内
则附 wuxing+meaning）；--surname 时对每字做谐音检查并附 homo_hits。
本模式不涉及生辰八字；后续验算走 search.py evaluate()（不传 --birth 即免八字）。
"""
import argparse
import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])

from namelib import load_chars, load_shuowen
from phonology import homophone_check
from popularity import popularity_score


def _entry(ch, info, chars_lib, surname=None):
    r = {
        "char": ch,
        "wordhead": info["wordhead"],
        "radical": info["radical"],
        "original": info["original"],
        "gloss": info["gloss"],
        "pinyin": info.get("pinyin") or info.get("pinyin_display") or "",
        "fanqie": info["fanqie"],
        "volume": info["volume"],
        "in_lib": ch in chars_lib,
    }
    if info.get("variant_of"):
        r["variant_of"] = info["variant_of"]
    lib = chars_lib.get(ch)
    if lib:
        r["wuxing"] = lib.get("wuxing")
        r["meaning"] = lib.get("meaning")
    if surname:
        hits = homophone_check(surname, ch)
        if hits:
            r["homo_hits"] = [h if isinstance(h, str) else h.get("word") or str(h)
                              for h in hits]
    pop = popularity_score(ch, "niche")
    if pop["detail"]["rare"]["chars"] or pop["detail"]["hotness"]["hot_char_ranks"]:
        r["pop"] = {"rare_chars": pop["detail"]["rare"]["chars"],
                    "hot_rank": pop["detail"]["hotness"]["hot_char_ranks"].get(ch)}
    return r


def main():
    ap = argparse.ArgumentParser(description="说文解字检索（按字义/部首/读音）")
    ap.add_argument("--sense", help="义训关键词，空格分隔多词（OR），如 '清 澄 湛'")
    ap.add_argument("--radical", help="部首，如 水")
    ap.add_argument("--pinyin", help="读音前缀（不带声调），如 xun")
    ap.add_argument("--char", help="单字查询")
    ap.add_argument("--surname", help="姓氏，用于单字谐音检查")
    ap.add_argument("--top", type=int, default=30, help="最多输出条数，默认30")
    args = ap.parse_args()

    if not any([args.sense, args.radical, args.pinyin, args.char]):
        ap.error("需至少一个检索条件：--sense / --radical / --pinyin / --char")

    chars_lib = load_chars()
    sw = load_shuowen()

    if args.char:
        if args.char not in sw:
            print(json.dumps({"error": f"说文未收字：{args.char}"},
                             ensure_ascii=False))
            return
        out = {"total": 1, "entries": [_entry(args.char, sw[args.char],
                                              chars_lib, args.surname)]}
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return

    kws = args.sense.split() if args.sense else []
    ranked = []
    for ch, info in sw.items():
        if args.radical and info["radical"] != args.radical:
            continue
        if args.pinyin and not info.get("pinyin", "").startswith(args.pinyin):
            continue
        hit = 0
        if kws:
            text = info["gloss"] + info["original"] + ch
            hit = sum(1 for k in kws if k in text)
            if hit == 0:
                continue
        ranked.append((hit, ch, info))
    # 命中词数多者优先；同分时字库内优先，再按部首稳定排序
    ranked.sort(key=lambda t: (-t[0], t[1] not in chars_lib, t[2]["radical"]))
    entries = [_entry(ch, info, chars_lib, args.surname)
               for _, ch, info in ranked[:args.top]]
    print(json.dumps({"total": len(ranked), "returned": len(entries),
                      "entries": entries}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
