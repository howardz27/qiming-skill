# -*- coding: utf-8 -*-
"""核心回归测试：八字排盘节气边界 / 三才五格已知姓名 / 康熙笔画 / 谐音检测"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import pytest


# ---------- 八字排盘（节气边界金标准） ----------
from bazi import paipan

CASES = [
    # (birth, 年柱, 月柱, 日柱)  权威口径：年界立春、月界节气（日柱经 2000-01-01=戊午 锚点独立核验）
    ("2026-03-01 10:23", "丙午", "庚寅", "甲戌"),   # 惊蛰(3/5)前 → 庚寅月
    ("2024-02-04 08:00", "甲辰", "丙寅", "戊戌"),   # 立春日当日 → 甲辰年（sxtwl按日切换）
    ("2024-02-03 12:00", "癸卯", "乙丑", "丁酉"),   # 立春前一日 → 仍癸卯年乙丑月
    ("2023-12-31 23:59", "癸卯", "甲子", "癸亥"),   # 大雪后 → 甲子月
    ("1990-05-15 12:00", "庚午", "辛巳", "庚辰"),
    ("2000-01-01 00:30", "己卯", "丙子", "戊午"),   # 立春前 → 己卯年
]

@pytest.mark.parametrize("birth,y,m,d", CASES)
def test_paipan(birth, y, m, d):
    pillars, _ = paipan(birth)
    assert pillars["year"] == tuple(y)
    assert pillars["month"] == tuple(m)
    assert pillars["day"] == tuple(d)


def test_three_pillar_when_no_hour():
    pillars, has_hour = paipan("2026-03-01")
    assert not has_hour and "hour" not in pillars


# ---------- 三才五格（公开可查已知姓名） ----------
from sancai import wuge

def test_wuge_wangzihan():
    """王梓涵：王4 梓11 涵12 → 天5 人15 地23 外13 总27"""
    r = wuge("王", "梓涵")
    assert r["grids"] == {"天格": 5, "人格": 15, "地格": 23, "外格": 13, "总格": 27}

def test_wuge_zhangwei():
    """张伟：张11 伟(偉)11 → 天12 人22 地12 外2 总22"""
    r = wuge("张", "伟")
    assert r["grids"] == {"天格": 12, "人格": 22, "地格": 12, "外格": 2, "总格": 22}

def test_wuge_compound():
    """欧阳修型复姓：复姓天格=两字和"""
    r = wuge("欧阳", "文修")
    assert r["grids"]["天格"] == r["strokes"]["surname"][0] + r["strokes"]["surname"][1]
    assert r["grids"]["外格"] == r["strokes"]["surname"][0] + r["strokes"]["given"][1]


# ---------- 康熙笔画折算规则（直接对引擎断言：引擎是知识库唯一来源） ----------
KANGXI_CASES = {
    "清": 12, "泽": 17, "汉": 15, "淑": 12,      # 氵→水4
    "华": 14, "蓉": 16, "莉": 13,                 # 艹→艸6
    "阳": 17, "阵": 15,                           # 左阝→阜8 右阝→邑7
    "志": 7, "情": 12,                            # 忄→心4
    "琛": 13, "瑾": 16,                           # 王→玉5
    "进": 15, "远": 17,                           # 辶→辵7
    "张": 11, "刘": 15, "李": 7, "陈": 16, "郭": 15,
    "邓": 19, "万": 15, "孙": 10, "叶": 15,
    "伟": 11, "梓": 11, "涵": 12, "轩": 10, "萱": 15,
    "涛": 18, "琳": 13, "珊": 10, "丽": 19,
    "边": 22, "达": 16, "俊": 9, "建": 9,
    "郁": 29, "滨": 18, "权": 22, "静": 16,
    "松": 8, "秋": 9, "冬": 5, "温": 13, "芸": 10,  # 本字即标准字
}

def test_kangxi_strokes():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "builder"))
    from kangxi_engine import get_engine
    e = get_engine()
    bad = []
    for ch, expect in KANGXI_CASES.items():
        got, conf = e.kangxi(ch)
        if got != expect:
            bad.append(f"{ch}: got {got}({conf}), expect {expect}")
    assert not bad, "; ".join(bad)


# ---------- 谐音检测 ----------
from phonology import homophone_check, phonology_score

def test_homophone_fanjian():
    hits = homophone_check("范", "建")
    assert any(h["word"] == "犯贱" for h in hits)

def test_homophone_duxiaoman():
    hits = homophone_check("杜", "子腾")
    assert any("肚子" in h["word"] or h["word"] == "肚子疼" for h in hits)

def test_homophone_clean():
    assert homophone_check("王", "梓涵") == []
    assert homophone_check("李", "思睿") == []

def test_phonology_pingze():
    r = phonology_score("王", "梓涵")   # 仄平
    assert r["detail"]["pingze"]["pattern"] == "仄平"


# ---------- 生肖宜忌 ----------
from zodiac import zodiac_score

def test_zodiac_horse():
    r = zodiac_score("马", "泽林")   # 氵忌、木喜 混合
    assert "泽" in r["bad_hits"]
    assert "林" in r["good_hits"]

def test_zodiac_neutral():
    r = zodiac_score("马", "言信")
    assert r["score"] == 70


# ---------- 重名偏好（公安部2021姓名报告数据驱动） ----------
from popularity import popularity_score

def test_popularity_neutral():
    r = popularity_score("梓涵")  # 2021女名Top10 精确命中
    assert r["detail"]["hotness"]["exact_top10_hit"]
    assert r["score"] <= 60
    assert popularity_score("景云")["score"] >= 85  # 双字均不在TOP50

def test_popularity_niche_pref():
    neutral = popularity_score("泽宇")["score"]  # 双热字但非Top10名
    niche = popularity_score("泽宇", "niche")["score"]
    common = popularity_score("泽宇", "common")["score"]
    assert niche < neutral < common

def test_popularity_stock_names():
    r = popularity_score("秀英")  # 存量双字名Top1（216.9万）
    assert r["detail"]["hotness"]["exact_top10_hit"]

def test_popularity_niche_level():
    assert "小众" in popularity_score("景云")["detail"]["hotness"]["niche_level"]
    assert "高频" in popularity_score("泽宇")["detail"]["hotness"]["niche_level"]


# ---------- 评分与检索 ----------
def test_search_e2e():
    import json
    import subprocess
    root = os.path.join(os.path.dirname(__file__), "..")
    py = os.path.join(root, ".venv", "bin", "python")
    out = subprocess.run(
        [py, os.path.join(root, "scripts", "search.py"),
         "--surname", "张", "--gender", "M", "--birth", "2026-03-01 10:23", "--top", "5"],
        capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    d = json.loads(out.stdout)
    assert d["bazi"]["pillars"]["year"] == "丙午"
    assert len(d["top"]) == 5
    for r in d["top"]:
        assert 0 <= r["score"] <= 100
        assert r["dims"]["phonology"] > 0
