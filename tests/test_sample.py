# -*- coding: utf-8 -*-
"""口味快选（sample.py）测试"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

ROOT = os.path.join(os.path.dirname(__file__), "..")
PY = os.path.join(ROOT, ".venv", "bin", "python")


def _run(*args):
    out = subprocess.run([PY, os.path.join(ROOT, "scripts", "sample.py"), *args],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_pick_diverse_and_safe():
    d = _run("--surname", "朱", "--gender", "F", "--pick", "12", "--seed", "3")
    assert 8 <= d["count"] <= 14
    buckets = {s["bucket"] for s in d["samples"]}
    assert len(buckets) >= 7  # 8 桶基本全覆盖
    # 样例间不共用字（口味信号干净）
    chars = [c for s in d["samples"] for c in s["given"]]
    assert len(chars) == len(set(chars))
    # 无俗气字
    from namelib import load_chars
    lib = load_chars()
    assert not any(lib[c].get("taste_risk") for s in d["samples"] for c in s["given"])


def test_infer_vibe_and_source():
    d = _run("--infer", "朱晚晴,朱竹露,朱望宁")
    assert d["suggest"]["vibe"] == "清雅"  # 3/3 名字带清雅
    assert d["source_tally"]["modern"] == 2
    assert {p["given"] for p in d["per_name"]} == {"晚晴", "竹露", "望宁"}


def test_infer_handles_full_and_given():
    # 带姓/不带姓均可
    d1 = _run("--infer", "云帆")
    d2 = _run("--infer", "朱云帆")
    assert d1["per_name"][0]["given"] == "云帆"
    assert d2["per_name"][0]["given"] == "云帆"
    assert d2["per_name"][0]["book"] == "唐诗三百首"


# ---------- 真实人名校准 ----------
def test_realism_levels():
    from realism import realism_info
    assert realism_info("一诺")["level"] == "有人用"
    assert realism_info("婕妤", "F")["n"] == 41
    assert realism_info("果来")["level"] == "未见"
    assert realism_info("云帆", "F")["note"].endswith("且均为男性使用")


def test_require_real_filters_junk():
    d = _run2("--surname", "朱", "--gender", "F", "--birth", "2027-01-15",
              "--style_tag", "classic", "--require-real", "--top", "100")
    names = {r["given"] for r in d["top"]}
    assert "果来" not in names and "来孝" not in names and "家可" not in names
    assert all("realism" in r["reasons"] for r in d["top"])


def _run2(*args):
    import subprocess
    out = subprocess.run([PY, os.path.join(ROOT, "scripts", "search.py"), *args],
                         capture_output=True, text=True, timeout=180)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)
