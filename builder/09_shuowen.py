# -*- coding: utf-8 -*-
"""09_shuowen.py — 说文解字字库

语料：data/shuowen/data/*.json（来源 shuowenjiezi/shuowen，Apache-2.0，
shuowen.org 官方整理数据，9833 字条一字一 JSON）

处理：
- 字头（wordhead，繁体）经 OpenCC t2s 转简体作为主键；不同繁体字头映射到
  同一简体时保留首条（按文件名数字序）并记录冲突
- explanation 保留繁体原文（original），另存 t2s 简体（gloss）
- 忽略 seal_character（shuowen.org 私有字体编码，无使用价值）与 duan_notes（过大）

产出：knowledge/shuowen.json
{"comment": ..., "total": N,
 "chars": {"洵": {"radical": "水", "original": "濯洵也。从水旬聲。",
                  "gloss": "…", "pinyin": "xun2", "fanqie": "相伦切",
                  "volume": "11", "wordhead": "洵"}}}

用法：python builder/09_shuowen.py
"""
import json
import os
import re

from opencc import OpenCC

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, "data", "shuowen", "data")
OUT = os.path.join(BASE, "knowledge", "shuowen.json")
T2S = OpenCC("t2s")


def main():
    files = sorted((f for f in os.listdir(RAW_DIR) if f.endswith(".json")),
                   key=lambda x: int(os.path.splitext(x)[0]))
    chars = {}
    conflicts = []
    variants = 0
    for fn in files:
        with open(os.path.join(RAW_DIR, fn), encoding="utf-8") as f:
            d = json.load(f)
        head = (d.get("wordhead") or "").strip()
        expl = (d.get("explanation") or "").strip()
        if not head or not expl:
            continue
        simplified = T2S.convert(head)
        if len(simplified) != 1:  # 字头异常（多字/空），跳过
            continue
        if simplified in chars:
            conflicts.append({"simplified": simplified,
                              "kept": chars[simplified]["wordhead"],
                              "dropped": head})
            continue
        chars[simplified] = {
            "wordhead": head,
            "radical": T2S.convert(d.get("radical") or ""),
            "original": expl,
            "gloss": T2S.convert(expl),
            "pinyin": d.get("pinyin") or "",
            "pinyin_display": d.get("pinyin_full") or "",
            "fanqie": d.get("pronunciation") or "",
            "volume": d.get("volume") or "",
        }
        # 或体/古文异体字：登记到 variants 键下，保证按异体查得到
        for v in d.get("variants") or []:
            vh = (v.get("wordhead") or "").strip()
            if not vh:
                continue
            vs = T2S.convert(vh)
            if len(vs) == 1 and vs not in chars:
                chars[vs] = dict(chars[simplified], variant_of=simplified)
                variants += 1

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"comment": "说文解字训释；来源 shuowenjiezi/shuowen (Apache-2.0)；"
                              "字头经 OpenCC t2s 转简，original 为繁体原文，gloss 为简体；"
                              "variant_of 标记或体/古文异体；忽略 seal_character",
                   "total": len(chars),
                   "conflicts": conflicts,
                   "chars": chars}, f, ensure_ascii=False)
    print(f"读取 {len(files)} 条 → 唯一简体字头 {len(chars)}（含异体 {variants}），"
          f"繁简映射冲突 {len(conflicts)} -> {OUT}")


if __name__ == "__main__":
    main()
