# -*- coding: utf-8 -*-
"""说文解字模式（shuowen.json + scripts/shuowen.py）测试"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

ROOT = os.path.join(os.path.dirname(__file__), "..")
PY = os.path.join(ROOT, ".venv", "bin", "python")


def _run(*args):
    out = subprocess.run([PY, os.path.join(ROOT, "scripts", "shuowen.py"), *args],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


# ---------- 数据层 ----------
def test_data_loadable_and_size():
    from namelib import load_shuowen
    sw = load_shuowen()
    assert len(sw) > 9000  # 全量收录（10874 含异体）


def test_entry_fields_complete():
    from namelib import load_shuowen
    sw = load_shuowen()
    e = sw["信"]
    assert e["gloss"].startswith("诚也")
    assert e["radical"] == "言"
    assert e["fanqie"]
    x = sw["洵"]
    assert "过水中也" in x["gloss"]      # 简体 gloss
    assert "過水中也" in x["original"]    # 繁体原文保留


def test_simplified_keys():
    from namelib import load_shuowen
    sw = load_shuowen()
    assert "风" in sw and sw["风"]["wordhead"] == "風"  # 繁转简生效
    assert all(len(k) == 1 for k in sw)


# ---------- CLI ----------
def test_cli_char_lookup():
    d = _run("--char", "洵")
    e = d["entries"][0]
    assert e["in_lib"] is True
    assert e["wuxing"] == "水"
    assert "过水中也" in e["gloss"]


def test_cli_char_missing():
    d = _run("--char", "𰻝")  # biang，说文未收
    assert "error" in d


def test_cli_sense_recall():
    d = _run("--sense", "清 澄 湛", "--top", "10")
    chars = {e["char"] for e in d["entries"]}
    assert chars & {"清", "淑", "湜", "澄"}  # 清湛义训字能召回
    for e in d["entries"]:
        assert e["gloss"] and e["radical"] and e["fanqie"]


def test_cli_radical():
    d = _run("--radical", "水", "--top", "5")
    assert d["total"] > 400  # 水部字头众多
    assert all(e["radical"] == "水" for e in d["entries"])


def test_cli_pinyin_prefix():
    d = _run("--pinyin", "xun", "--top", "10")
    assert all(e["pinyin"].startswith("xun") for e in d["entries"])
    assert "洵" in {e["char"] for e in d["entries"]}


def test_cli_surname_homophone_flag():
    d = _run("--sense", "风", "--surname", "朱", "--top", "3")
    hits = [e for e in d["entries"] if e["char"] == "风"]
    if hits:
        assert hits[0].get("homo_hits")  # 朱风≈猪疯，谐音命中被标注
