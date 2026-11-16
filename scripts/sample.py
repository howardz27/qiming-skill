# -*- coding: utf-8 -*-
"""口味快选（taste calibration）：先给样例名让用户勾选，反推风格偏好。

两种用法：
  python scripts/sample.py --surname 朱 --gender F [--pick 12] [--seed 1]
    → 输出横跨风格桶的样例名列表（JSON），供用户勾选

  python scripts/sample.py --infer "朱云帆,朱令仪" 或 "云帆,令仪"
    → 输出 vibe/来源 统计与推荐检索参数（JSON）
"""
import argparse
import json
import random
import sys
from collections import Counter

from namelib import load_chars, load_classic_names, load_modern_names
from phonology import homophone_check
from realism import realism_info

# 风格桶：覆盖 vibe 六系 + 古典/现代来源，保证样例多样性
BUCKETS = [
    ("古籍·清雅", "classic", ("清雅",)),
    ("古籍·文气", "classic", ("文气",)),
    ("古籍·大气", "classic", ("大气",)),
    ("古籍·灵动甜美", "classic", ("灵动", "甜美")),
    ("现代·自然意象", "book:自然意象", ()),
    ("现代·新中式", "book:新中式", ()),
    ("现代·文学品格", "book:现代文学/品格格言", ()),
    ("中性·硬朗", None, ("硬朗",)),
]


def _candidates(gender):
    rows = []
    for r in load_classic_names():
        r = dict(r)
        r["_origin"] = "classic"
        rows.append(r)
    for r in load_modern_names():
        if r.get("origin_classical"):
            continue  # 古典化用不放样例，来源标签会误导
        r = dict(r)
        r["_origin"] = "modern"
        rows.append(r)
    return [r for r in rows if r.get("gender_hint") in (gender, "N")]


def _bucket_rows(rows, bucket):
    _, spec, vibes = bucket
    chars = load_chars()
    out = []
    for r in rows:
        name = r["name"]
        if len(name) != 2:
            continue
        if any(chars.get(c, {}).get("taste_risk") for c in name):
            continue  # 样例不用俗气字，避免误导口味信号
        if spec == "classic" and r["_origin"] != "classic":
            continue
        if spec and spec.startswith("book:"):
            if r["source"]["book"] not in spec[5:].split("/"):
                continue
        cv = [v for c in name for v in (chars.get(c, {}).get("vibe") or [])]
        if vibes:
            hit = sum(1 for v in vibes if v in cv)
            if hit == 0:
                continue
            r["_rank"] = hit
        else:
            r["_rank"] = 1
        out.append(r)
    return out


def cmd_pick(args):
    rows = _candidates(args.gender)
    chars = load_chars()
    rng = random.Random(args.seed)
    picked, used_chars = [], set()
    extra = max(0, args.pick - len(BUCKETS))
    for bi, bucket in enumerate(BUCKETS):
        pool = _bucket_rows(rows, bucket)
        rng.shuffle(pool)
        pool.sort(key=lambda r: -r["_rank"])
        took = 0
        want = 1 + (1 if bi < extra else 0)
        for r in pool:
            if took >= want:
                break
            if any(c in used_chars for c in r["name"]):
                continue  # 样例间不共用字，信号更干净
            if homophone_check(args.surname, r["name"]):
                continue
            if realism_info(r["name"], args.gender)["n"] == 0:
                continue  # 样例必须是真人名库中出现过的名字
            used_chars.update(r["name"])
            src = r["source"]
            picked.append({
                "name": args.surname + r["name"], "given": r["name"],
                "bucket": bucket[0], "origin": r["_origin"],
                "source": {"book": src["book"], "title": src.get("title", ""),
                           "sentence": src.get("sentence", "")[:24]},
                "vibes": sorted({v for c in r["name"]
                                 for v in (chars.get(c, {}).get("vibe") or [])}),
            })
            took += 1
    print(json.dumps({"count": len(picked), "samples": picked},
                     ensure_ascii=False, indent=1))


def cmd_infer(args):
    chars = load_chars()
    corpus = {r["name"]: r["source"]["book"]
              for rows in (load_classic_names(), load_modern_names())
              for r in rows}
    vibe_tally, src_tally, per_name = Counter(), Counter(), []
    for raw in args.names.split(","):
        given = raw.strip().replace(args.surname, "")
        if not given:
            continue
        vibes = sorted({v for c in given
                        for v in (chars.get(c, {}).get("vibe") or [])})
        book = corpus.get(given)
        per_name.append({"given": given, "vibes": vibes, "book": book})
        vibe_tally.update(vibes)
        if book:
            src_tally["modern" if book in
                      ("自然意象", "现代文学", "品格格言", "新中式") else "classic"] += 1
    vibe = vibe_tally.most_common(1)[0][0] if vibe_tally else ""
    style_tag = ("all" if not src_tally else
                 src_tally.most_common(1)[0][0] if len(src_tally) == 1 else "all")
    print(json.dumps({
        "per_name": per_name,
        "vibe_tally": dict(vibe_tally),
        "source_tally": dict(src_tally),
        "suggest": {"vibe": vibe, "style_tag": style_tag},
    }, ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surname", default="朱")
    ap.add_argument("--gender", default="N", choices=["M", "F", "N"])
    ap.add_argument("--pick", type=int, default=12)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--infer", dest="names", help="用户勾选的名字，逗号分隔")
    args = ap.parse_args()
    if args.names:
        cmd_infer(args)
    else:
        cmd_pick(args)


if __name__ == "__main__":
    main()
