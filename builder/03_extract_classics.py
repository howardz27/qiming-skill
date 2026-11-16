# -*- coding: utf-8 -*-
"""典籍摘名：诗经/楚辞/论语/孟子/大学/中庸/唐诗三百首/千家诗/古文观止/南唐词
→ 繁体语料 OpenCC 转简 → 分句 → 相邻二字组合 → 过滤 → names_classic.jsonl
"""
import json
import os
import re

from opencc import OpenCC

BASE = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(BASE, "data", "raw", "classics")
KNOW = os.path.join(BASE, "knowledge")
T2S = OpenCC("t2s")

# 虚词与不宜入名的字
BAD_CHARS = set("之乎者也矣焉哉而与其且夫兮所者于以因为则若有不无非无毋勿莫")
BAD_CHARS |= set("帝朕皇考曰上下中一二三四五六七八九十百千万亿")
BAD_CHARS |= set("丧哭死尸坟墓棺祭祀鬼神妖魔鬼怪病灾祸殃凶殃")
NEGATIVE_HINT = set("尤怨恨悲愁苦泪涕鲜血亡灭绝断独孤寡哭笑痴狂疯愚蠢")
NEGATIVE_HINT |= set("杳冥黯萧瑟零落凋残颓衰朽腐")
# 句义不祥（涉及死亡/战乱/流放的句子整体跳过）
SENT_SKIP = set("弑崩薨卒囚戮诛屠虐乱贼寇讨伐奔逃亡命逐放流放魂")
# 叙事人称/对话标记（散文中叙述他人的句子不宜摘名）
NARRATIVE_SKIP = set("曰谓汝尔吾乃其人矣耳焉")
# 爵位/称谓后缀，不宜作名末字
BAD_FINAL = set("公侯伯子男爵卿王君后帝")
# 出处优先级（同名多出处时取典雅度更高的）
BOOK_PRIORITY = {"诗经": 0, "楚辞": 1, "论语": 2, "孟子": 3, "中庸": 3, "大学": 3,
                 "唐诗三百首": 4, "千家诗": 5, "南唐词": 5, "古文观止": 6}
# 散文体限句长（诗句 2-14，散文 3-12，避免截取到长句叙事）
MAX_SENT = {"古文观止": 12, "孟子": 12, "大学": 12, "中庸": 12}

def load_chars():
    chars = {}
    with open(os.path.join(KNOW, "chars.jsonl"), encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            chars[r["char"]] = r
    return chars

def _s(t):
    return T2S.convert(t)

def _iter_book(book, fn):
    """yield (title, section, line)；输出统一为简体"""
    data = json.load(open(os.path.join(RAW, fn), encoding="utf-8"))
    if book == "诗经":
        for item in data:
            yield from ((item["title"], f"{item['chapter']}·{item['section']}", l) for l in item["content"])
    elif book == "楚辞":
        for item in data:
            yield from ((item["title"], item["section"], l) for l in item["content"])
    elif book in ("论语", "孟子"):
        for item in data:
            chap = _s(item["chapter"])
            yield from ((chap, "", _s(l)) for l in item["paragraphs"])
    elif book in ("大学", "中庸"):
        for l in data["paragraphs"]:
            yield ("", "", _s(l))
    elif book in ("唐诗三百首", "千家诗"):
        for group in data["content"]:
            gtype = group["type"]
            for item in group["content"]:
                author = _s(re.sub(r"[（）()]", "", item.get("author", "")))
                sec = f"{gtype}·{author}" if author else gtype
                title = _s(item.get("chapter") or item.get("subchapter") or "")
                for l in item["paragraphs"]:
                    if isinstance(l, str):
                        yield (title, sec, _s(l))
    elif book == "古文观止":
        for vol in data["content"]:
            for item in vol["content"]:
                title = _s(item["chapter"])
                sec = f"{_s(vol['title'])}·{_s(item.get('source', ''))}"
                for l in item["paragraphs"]:
                    yield (title, sec, _s(l))
    elif book == "南唐词":
        for item in data:
            title = _s(item.get("rhythmic", ""))
            for l in item.get("paragraphs", []) or item.get("content", []):
                if isinstance(l, list):
                    l = "".join(l)
                yield (title, "李煜", _s(l))

BOOKS = [
    ("诗经", "shijing.json"), ("楚辞", "chuci.json"), ("论语", "lunyu.json"),
    ("孟子", "mengzi.json"), ("大学", "daxue.json"), ("中庸", "zhongyong.json"),
    ("唐诗三百首", "tangshisanbaishou.json"), ("千家诗", "qianjiashi.json"),
    ("古文观止", "guwenguanzhi.json"), ("南唐词", "nantang.json"),
]

def iter_sentences():
    for book, fn in BOOKS:
        maxlen = MAX_SENT.get(book, 14)
        for title, section, line in _iter_book(book, fn):
            for s in re.split(r"[，。！？；：、「」『』“”\"'（）()\u3000]", line):
                s = s.strip()
                if 2 <= len(s) <= maxlen:
                    yield book, title, section, s

def extract():
    chars = load_chars()
    results = {}
    for book, title, section, sent in iter_sentences():
        if SENT_SKIP & set(sent):
            continue
        # 散文体：含叙事人称/对话标记的句子跳过
        if book in MAX_SENT and (NARRATIVE_SKIP & set(sent)):
            continue
        clean = [c for c in sent if not c.isspace()]
        for i in range(len(clean) - 1):
            a, b = clean[i], clean[i + 1]
            if a in BAD_CHARS or b in BAD_CHARS or a in NEGATIVE_HINT or b in NEGATIVE_HINT:
                continue
            if b in BAD_FINAL:
                continue
            if a not in chars or b not in chars:
                continue
            if a == b:
                continue
            name = a + b
            # 性别兼容检查：M+F 组合跳过
            ga, gb = chars[a]["gender"], chars[b]["gender"]
            if {ga, gb} == {"M", "F"}:
                continue
            hint = "M" if "M" in (ga, gb) else ("F" if "F" in (ga, gb) else "N")
            src = {"book": book, "title": title, "section": section, "sentence": sent}
            if name not in results:
                results[name] = {
                    "name": name, "chars": [a, b], "type": "classic",
                    "source": src, "gender_hint": hint,
                    "wuxing_pair": (chars[a]["wuxing"] or "?") + (chars[b]["wuxing"] or "?"),
                    "tone_pair": [chars[a]["tone"], chars[b]["tone"]],
                    "meaning_source": "pending_llm",
                }
            elif BOOK_PRIORITY[book] < BOOK_PRIORITY[results[name]["source"]["book"]]:
                results[name]["source"] = src  # 更典雅出处优先
    out = sorted(results.values(), key=lambda r: (r["source"]["book"], r["source"]["title"]))
    with open(os.path.join(KNOW, "names_classic.jsonl"), "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    from collections import Counter
    c = Counter(r["source"]["book"] for r in out)
    print(f"典籍候选名: {len(out)} {dict(c)}")

if __name__ == "__main__":
    extract()
