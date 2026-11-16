# -*- coding: utf-8 -*-
"""知识库加载与缓存（运行时唯一入口）"""
import json
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
KNOW = os.path.join(BASE, "knowledge")

_cache = {}

def _load_json(path):
    if path not in _cache:
        _cache[path] = json.load(open(path, encoding="utf-8"))
    return _cache[path]

def load_chars():
    """返回 {char: 属性dict}"""
    if "chars" not in _cache:
        chars = {}
        with open(os.path.join(KNOW, "chars.jsonl"), encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                chars[r["char"]] = r
        _cache["chars"] = chars
    return _cache["chars"]

def load_surnames():
    return _load_json(os.path.join(KNOW, "surnames.json"))["surnames"]

def load_surname(name):
    for s in load_surnames():
        if s["surname"] == name:
            return s
    return None

def load_classic_names():
    if "classic" not in _cache:
        rows = []
        with open(os.path.join(KNOW, "names_classic.jsonl"), encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
        _cache["classic"] = rows
    return _cache["classic"]

def load_modern_names():
    if "modern" not in _cache:
        rows = []
        with open(os.path.join(KNOW, "names_modern.jsonl"), encoding="utf-8") as f:
            for line in f:
                rows.append(json.loads(line))
        _cache["modern"] = rows
    return _cache["modern"]

def load_zodiac_rules():
    return _load_json(os.path.join(KNOW, "zodiac_rules.json"))

def load_homophone_blocklist():
    return _load_json(os.path.join(KNOW, "homophone_blocklist.json"))

def load_wuxing_rules():
    return _load_json(os.path.join(KNOW, "numerology", "wuxing_rules.json"))

def load_shuli81():
    return _load_json(os.path.join(KNOW, "numerology", "shuli_81.json"))

def load_kangxi_table():
    return _load_json(os.path.join(KNOW, "numerology", "kangxi_strokes.json"))["chars"]

def load_name_blocklist():
    return _load_json(os.path.join(KNOW, "name_blocklist.json"))["bad_pairs"]

def load_name_stats():
    return _load_json(os.path.join(KNOW, "name_stats.json"))
