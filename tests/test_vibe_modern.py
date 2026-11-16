# -*- coding: utf-8 -*-
"""风格偏好 / 现代来源 / 俗气惩罚 / 语境贬义过滤 测试"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from namelib import load_chars, load_modern_names
from scorer import meaning_score


def _run(*args):
    root = os.path.join(os.path.dirname(__file__), "..")
    py = os.path.join(root, ".venv", "bin", "python")
    out = subprocess.run(
        [py, os.path.join(root, "scripts", "search.py"), *args],
        capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ---------- 数据层 ----------
def test_chars_have_vibe_and_taste_risk():
    chars = load_chars()
    assert len(chars) >= 610
    assert all("vibe" in r and "taste_risk" in r for r in chars.values())
    assert load_chars()["花"]["taste_risk"] is True
    assert load_chars()["月"]["taste_risk"] is False
    assert "清雅" in load_chars()["月"]["vibe"]


def test_modern_corpus_loadable():
    rows = load_modern_names()
    assert len(rows) >= 130
    assert all(r["type"] == "modern" for r in rows)
    cats = {r["source"]["book"] for r in rows}
    assert cats <= {"自然意象", "现代文学", "品格格言", "新中式", "古典化用"}
    # 结构分类（07 校准）全覆盖
    assert all(r.get("structure") for r in rows)
    # 提取条目必须有真实出处（作者《篇名》格式）
    for r in rows:
        if r.get("extracted"):
            assert "《" in r["source"]["title"] and "》" in r["source"]["title"]


def test_classical_reclassified():
    rows = load_modern_names()
    by_name = {r["name"]: r for r in rows}
    # 望舒/白鹭/知行 出处为古文 → 古典化用降级，不再冒充现代
    for n in ("望舒", "白鹭", "知行"):
        assert by_name[n]["source"]["book"] == "古典化用"
        assert by_name[n].get("origin_classical") is True


# ---------- 俗气惩罚 ----------
def test_taste_risk_penalty():
    clean = meaning_score({"name": "景云", "chars": ["景", "云"], "source": None})
    risky = meaning_score({"name": "花朵", "chars": ["花", "朵"], "source": None})
    assert clean["score"] > risky["score"]
    assert risky["score"] < 60  # 双俗字大扣


# ---------- CLI: vibe / modern / 冲突提示 ----------
def test_vibe_reranks():
    base = _run("--surname", "张", "--gender", "F", "--top", "200")
    vibe = _run("--surname", "张", "--gender", "F", "--vibe", "清雅", "--top", "200")
    base_mean = sum(r["score"] for r in base["top"][:10])
    vibe_mean = sum(r["score"] for r in vibe["top"][:10])
    assert vibe_mean >= base_mean
    assert vibe["query"]["vibe"] == "清雅"


def test_style_tag_modern_only():
    d = _run("--surname", "朱", "--gender", "F", "--birth", "2027-01-15",
             "--style_tag", "modern", "--top", "10")
    assert d["count_total"] > 30
    assert all(r["type"] == "modern" for r in d["top"])


def test_zodiac_water_conflict_note():
    d = _run("--surname", "朱", "--gender", "F", "--birth", "2027-01-15", "--top", "3")
    # 马年喜水生肖忌氵字根 → 应有冲突提示
    assert "note_conflict" in d["bazi"]


def test_negative_context_filtered():
    # 「兰芷变而不芳兮」应被语境贬义过滤，不得出现在任何结果
    d = _run("--surname", "朱", "--gender", "F", "--birth", "2027-01-15", "--top", "100")
    names = {r["name"] for r in d["top"]}
    assert "朱兰芷" not in names
    assert "朱蘅芷" not in names  # 「蘅芷彫兮」
