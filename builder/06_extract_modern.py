# -*- coding: utf-8 -*-
"""06_extract_modern.py — 从公版现代诗文语料穷举提取双字名候选

语料：data/modern_texts/*.txt，首行格式 `#作者|篇名`，其后为正文。
作者均为逝世超过50年、作品进入公有领域的现代作家（朱自清/徐志摩/林徽因/
戴望舒/鲁迅/闻一多/郁达夫/萧红/李叔同等）。

提取规则：
- 按标点断句，取长度2-14字的片段
- 片段内所有相邻双字窗口，两字均在 chars.jsonl（保证五行/笔画可算）
- 排除白话虚词参与的组合、纯数字、重复字（如"匆匆"保留？——排除叠字词根）
- 与 names_modern.jsonl 已有条目去重（手工策展优先）；与典籍库重名则跳过
  （古籍来源优先，避免来源混淆）
- 结构分类沿用 07 的分类器

用法：python builder/06_extract_modern.py [--dry]
"""
import glob
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
import namelib

TEXT_DIR = os.path.join(BASE, "data", "modern_texts")
MODERN = os.path.join(BASE, "knowledge", "names_modern.jsonl")
CLASSIC = os.path.join(BASE, "knowledge", "names_classic.jsonl")

BAD_IN_BIGRAM = set("的了吗呢吧啊呀么着是在和与就从被把也都很更太再又便却")

# 提取噪声黑名单：白话虚词对/跨词边界/地名专名/量词短语（人工审核首跑结果归纳）
BAD_BIGRAMS = {
    "正如", "一定", "知道", "可以", "之于", "郁于", "永远", "深晚", "念书", "来信",
    "载一", "香一", "歌一", "树一", "管来", "朵雪", "来花", "道凝", "洲曲", "见风",
    "成红", "一朵", "一树", "一曲", "飞舞", "眠歌", "舟心", "诗歌", "燕子",
    "康桥", "康河", "白山", "长白", "远照", "红公", "成紫", "国之", "之秋",
    "雨一", "一九", "文复", "如果", "果青", "来开", "心来", "光来", "光之",
    "风来", "果子", "见一", "来管", "盼望", "道一", "之蓝", "进来", "悠长", "成一",
}


def fragments(text):
    for seg in text.replace("\n", "。").split("。"):
        seg = seg.strip()
        if not seg:
            continue
        for piece in seg.replace("！", "！").replace("？", "？").split("！"):
            for p in piece.split("？"):
                for q in p.split("；"):
                    q = q.strip()
                    if 2 <= len(q) <= 14:
                        yield q


def classify(a, b):
    XUZI = set("一亦以可若如予于之未知与")
    VERB = set("听望见闻知思念观归沐予乐守")
    if a in XUZI:
        return "虚字组合"
    if a in VERB:
        return "动词开头"
    if b in XUZI:
        return "虚字收尾"
    return "意象并列"


def main():
    dry = "--dry" in sys.argv
    lib = namelib.load_chars()
    modern_names = {json.loads(l)["name"] for l in open(MODERN, encoding="utf-8")}
    classic_names = {json.loads(l)["name"] for l in open(CLASSIC, encoding="utf-8")}

    found = {}  # name -> record
    files = sorted(glob.glob(os.path.join(TEXT_DIR, "*.txt")))
    if not files:
        print("data/modern_texts/ 无文本，先运行收集流程")
        return
    for path in files:
        first = open(path, encoding="utf-8").readline().strip()
        if not first.startswith("#"):
            print(f"[WARN] {os.path.basename(path)} 首行缺 #作者|篇名，跳过")
            continue
        author, title = first[1:].split("|", 1)
        body = open(path, encoding="utf-8").readlines()[1:]
        text = "".join(body)
        for frag in fragments(text):
            for i in range(len(frag) - 1):
                a, b = frag[i], frag[i + 1]
                name = a + b
                if a == b or a in BAD_IN_BIGRAM or b in BAD_IN_BIGRAM or name in BAD_BIGRAMS:
                    continue
                if name in modern_names or name in classic_names or name in found:
                    continue
                ra, rb = lib.get(a), lib.get(b)
                if not (ra and rb):
                    continue
                # 性别兼容
                gh = ra["gender"] if ra["gender"] != "N" else rb["gender"]
                found[name] = {
                    "name": name, "chars": [a, b], "type": "modern",
                    "source": {"book": "现代文学", "title": f"{author}《{title}》",
                               "sentence": frag[:20], "section": f"{author}·{title}"},
                    "gender_hint": gh,
                    "wuxing_pair": [ra["wuxing"], rb["wuxing"]],
                    "tone_pair": [ra["tone"], rb["tone"]],
                    "meaning_source": "pending_llm",
                    "structure": classify(a, b),
                    "extracted": True,
                }
    print(f"提取到 {len(found)} 个候选")
    if dry:
        return
    # 追加写入现代库
    with open(MODERN, "a", encoding="utf-8") as f:
        for r in found.values():
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"追加 {len(found)} 条 -> names_modern.jsonl（后续靠 search.py 质量链过滤）")


if __name__ == "__main__":
    main()
