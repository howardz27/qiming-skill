# -*- coding: utf-8 -*-
"""构建汉字属性库 knowledge/chars.jsonl + kangxi_strokes.json + surnames.json

字段全部程序化生成：拼音(pypinyin) + 康熙笔画(Unihan引擎) + 五行(种子覆盖>部首映射) + 生肖宜忌(字根规则)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pypinyin import pinyin, Style
from kangxi_engine import get_engine
from seed_chars import SEED

# 补充五行（部首无法判定的少量字）
SEED.setdefault("安", {})["w"] = "土"
SEED.setdefault("和", {})["w"] = "木"
SEED.setdefault("毅", {})["w"] = "木"

BASE = os.path.join(os.path.dirname(__file__), "..")
KNOW = os.path.join(BASE, "knowledge")

e = get_engine()

# ---------- 五行：康熙部首号 → 五行（部首号已用 Unihan 权威映射核实） ----------
RADICAL_WUXING = {
    75: "木", 118: "木", 115: "木", 140: "木",              # 木竹禾艸
    86: "火", 72: "火", 73: "火", 117: "火",                # 火日曰立
    32: "土", 33: "土", 46: "土", 102: "土", 170: "土", 163: "土",  # 土士山田阜邑
    167: "金", 96: "金", 154: "金", 112: "金", 149: "金", 164: "金", 18: "金",  # 金玉贝石言酉刀
    85: "水", 15: "水", 173: "水", 38: "水", 39: "水",      # 水冫雨女子
}

def infer_wuxing(ch, override):
    if override in ("金", "木", "水", "火", "土"):
        return override, "seed"
    trad = e.traditional_form(ch)
    for target in (trad, ch):
        if target in e.rs:
            r, _ = e.rs[target]
            if r in RADICAL_WUXING:
                return RADICAL_WUXING[r], "radical"
    return None, "none"

# ---------- 生肖宜忌 ----------
ZOD = json.load(open(os.path.join(KNOW, "zodiac_rules.json"), encoding="utf-8"))
# 部首符号别名 → 生肖字根可匹配集合
RAD_SYMBOL = {  # 康熙部首号 → 部首书写形符号列表
    85: ["氵", "水", "冫"], 86: ["火", "灬"], 72: ["月"], 130: ["月", "心", "忄"],
    61: ["心", "忄"], 9: ["人", "亻"], 96: ["王", "玉"], 140: ["艹", "艸"],
    163: ["阝"], 170: ["阝"], 167: ["钅", "金"], 30: ["土"], 46: ["山"],
    32: ["口"], 38: ["宀", "宀"], 149: ["言", "讠"], 75: ["木"], 112: ["禾"],
    152: ["米"], 151: ["豆"], 118: ["米"], 195: ["鸟", "鳥"], 172: ["隹"],
    196: ["鸟", "鳥"], 142: ["衣", "衤"], 113: ["示", "礻"], 162: ["辶"],
}

def zodiac_match(ch):
    """返回 {生肖: 'good'/'bad'}"""
    out = {}
    if ch not in e.rs:
        return out
    r, _ = e.rs[ch]
    symbols = set(RAD_SYMBOL.get(r, []))
    trad_char = e._radical_chars.get(r, "")
    if trad_char:
        symbols.add(trad_char)
    for z, info in ZOD["zodiacs"].items():
        hit = None
        for root in info["bad_roots"]:
            if root in symbols or (len(root) <= 2 and root and root in ch):
                hit = "bad"; break
        if hit is None:
            for root in info["good_roots"]:
                if root in symbols or (len(root) <= 2 and root and root in ch):
                    hit = "good"; break
        if hit:
            out[z] = hit
    return out

# ---------- 生成 chars.jsonl ----------
KAIMOU = ("a", "o", "e", "ai", "ao", "ou", "ang", "eng", "ong", "an", "en")  # 开口呼韵母起头

def build():
    rows = []
    for ch, meta in SEED.items():
        py = pinyin(ch, style=Style.TONE3, heteronym=False)[0][0]  # 如 "qing1"
        py_all = [p.strip() for p in pinyin(ch, style=Style.TONE3, heteronym=True)[0]]
        base = py.rstrip("1234")
        tone = int(py[-1]) if py[-1].isdigit() else 0
        # 声母/韵母
        sm = pinyin(ch, style=Style.INITIALS, strict=False)[0][0]
        fina = pinyin(ch, style=Style.FINALS, strict=False)[0][0]
        wx, wx_src = infer_wuxing(ch, meta.get("w"))
        kx, conf = e.kangxi(ch)
        simp = e.simplified_strokes(ch)
        zm = zodiac_match(ch)
        good = [z for z, v in zm.items() if v == "good"]
        bad = [z for z, v in zm.items() if v == "bad"]
        rows.append({
            "char": ch,
            "pinyin": base,
            "pinyins_all": list(set(py_all)),
            "tone": tone,
            "shengmu": sm or "",
            "yunmu": fina,
            "kaimou": any(base.startswith(k) for k in KAIMOU),
            "kangxi": kx,
            "kangxi_conf": conf,
            "simplified": simp,
            "wuxing": wx,
            "wuxing_src": wx_src,
            "zodiac_good": good,
            "zodiac_bad": bad,
            "gender": meta.get("g", "N"),
            "meaning": meta.get("m", ""),
            "is_polyphone": len(set(py_all)) > 1,
            "meaning_source": "curated",
        })
    os.makedirs(KNOW, exist_ok=True)
    with open(os.path.join(KNOW, "chars.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 康熙笔画全量表（姓氏等扩展用）
    with open(os.path.join(KNOW, "numerology", "kangxi_strokes.json"), "w", encoding="utf-8") as f:
        json.dump({"comment": "ch -> kangxi strokes (由 Unihan kRSUnicode 引擎计算)",
                   "chars": {r["char"]: r["kangxi"] for r in rows if r["kangxi"]}}, f, ensure_ascii=False, indent=0)
    no_wx = [r["char"] for r in rows if not r["wuxing"]]
    no_kx = [r["char"] for r in rows if not r["kangxi"]]
    print(f"chars: {len(rows)}, 无五行: {len(no_wx)} {no_wx[:20]}")
    print(f"无康熙笔画: {len(no_kx)} {no_kx[:20]}")

if __name__ == "__main__":
    build()
