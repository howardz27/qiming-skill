# -*- coding: utf-8 -*-
"""真人名感校准：基于 120 万公开人物名录的双字名频次表。

注意口径：语料为已出生世代（成年人物为主），
近年新生儿爆款名可能不在其中——「未见」= 结构存疑，≠ 没人取。
"""
import json
import os

_TABLE = None
PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "knowledge", "real_name_freq.json")


def _load():
    global _TABLE
    if _TABLE is None:
        _TABLE = json.load(open(PATH, encoding="utf-8"))["names"]
    return _TABLE


def realism_info(given, gender="N"):
    """返回 {n, f, level, note}。level: 常用/有人用/罕见/未见"""
    row = _load().get(given)
    if not row:
        return {"n": 0, "f": 0, "level": "未见",
                "note": "120万真人名库未见此名，结构存疑"}
    n, f = row
    if n >= 200:
        level = "常用"
    elif n >= 20:
        level = "有人用"
    else:
        level = "罕见"
    note = f"真人名库出现{n}次（女{f}）"
    if gender == "F" and n >= 20 and f == 0:
        note += "，且均为男性使用"
    if gender == "M" and n >= 20 and f == n:
        note += "，且均为女性使用"
    return {"n": n, "f": f, "level": level, "note": note}
