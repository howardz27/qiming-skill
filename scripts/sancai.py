# -*- coding: utf-8 -*-
"""三才五格 + 81数理

五格（康熙笔画）：
  天格 = 单姓姓+1 / 复姓两字之和
  人格 = 姓氏末字 + 名字首字
  地格 = 双字名两字之和 / 单字名名+1
  外格 = 单姓(1+名末字) / 复姓(姓首字+名末字)；单字名：单姓=2 / 复姓=姓首字+1
  总格 = 姓+名全部之和
三才：天/人/地格尾数定五行（1,2木 3,4火 5,6土 7,8金 9,0水），
吉凶按相邻生克评定：相生或比和为吉、相克为凶（主流三才表口径的程序化实现）。
"""
from namelib import load_chars, load_kangxi_table, load_shuli81, load_surname

DIGIT_WUXING = {1: "木", 2: "木", 3: "火", 4: "火", 5: "土", 6: "土", 7: "金", 8: "金", 9: "水", 0: "水"}
SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
SHENG_PAIRS = {(SHENG[a], a) for a in SHENG}          # (生者, 被生者)
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}
KE_PAIRS = {(KE[a], a) for a in KE}


def name_strokes(chars_lib, kx_table, ch):
    r = chars_lib.get(ch)
    if r and r.get("kangxi"):
        return r["kangxi"]
    return kx_table.get(ch)


def sancai_rating(tian, ren, di):
    """三才五行三项 → 评分0-100与描述。相邻两对（天-人、人-地）生克。"""
    pairs = [(tian, ren), (ren, di)]
    good = bad = 0
    for a, b in pairs:
        if a == b:
            good += 1
        elif (a, b) in SHENG_PAIRS or (b, a) in SHENG_PAIRS:
            good += 1
        elif (a, b) in KE_PAIRS or (b, a) in KE_PAIRS:
            bad += 1
    if good == 2:
        score = 100
    elif good == 1 and bad == 0:
        score = 70
    elif good == 1 and bad == 1:
        score = 45
    elif bad == 2:
        score = 20
    else:
        score = 45
    label = "大吉" if score >= 100 else ("吉" if score >= 70 else ("中" if score >= 45 else "凶"))
    return score, f"{tian}{ren}{di} {'顺生比和' if good == 2 else ('一生一克' if good == 1 and bad == 1 else ('相克' if bad == 2 else '半吉'))}", label


def shuli_score(n):
    """81数理吉凶 → 0-100。余数0按81计。"""
    if n <= 0:
        return 0, "凶", ""
    m = n % 81 or 81
    info = load_shuli81()["numbers"][str(m)]
    scale = load_shuli81()["note_luck_scale"]
    for luck, val in scale.items():
        if info["luck"] == luck:
            return round(val * 100), info["luck"], info.get("summary", "")
    return 50, "中", info.get("summary", "")


def wuge(surname: str, given: str):
    """surname: 姓（含复姓）；given: 双字名（当前仅支持双字名）"""
    sur = load_surname(surname)
    chars_lib = load_chars()
    kx_table = load_kangxi_table()
    if sur["is_compound"]:
        sur_kx = [name_strokes(chars_lib, kx_table, c) or sur["kangxi"] // len(surname) for c in surname]
    else:
        sur_kx = [sur["kangxi"]]
    g_kx = [name_strokes(chars_lib, kx_table, c) for c in given]
    if any(k is None for k in g_kx):
        return {"error": f"名字用字无康熙笔画: {given}"}

    if len(sur_kx) == 1:
        tian = sur_kx[0] + 1
        wai = 2 if len(g_kx) == 1 else 1 + g_kx[-1]
    else:
        tian = sum(sur_kx)
        wai = sur_kx[0] + (1 if len(g_kx) == 1 else g_kx[-1])
    ren = sur_kx[-1] + g_kx[0]
    di = sum(g_kx) if len(g_kx) >= 2 else g_kx[0] + 1
    zong = sum(sur_kx) + sum(g_kx)

    t_wx = DIGIT_WUXING[tian % 10]
    r_wx = DIGIT_WUXING[ren % 10]
    d_wx = DIGIT_WUXING[di % 10]
    sc, desc, label = sancai_rating(t_wx, r_wx, d_wx)

    grids = {"天格": tian, "人格": ren, "地格": di, "外格": wai, "总格": zong}
    shuli = {}
    for g, v in grids.items():
        s, luck, summary = shuli_score(v)
        shuli[g] = {"num": v, "luck": luck, "score": s, "summary": summary}
    # 数理重点：人格/地格/总格
    key_shuli = round((shuli["人格"]["score"] * 0.4 + shuli["地格"]["score"] * 0.3 + shuli["总格"]["score"] * 0.3))
    return {
        "grids": grids, "strokes": {"surname": sur_kx, "given": g_kx},
        "sancai": {"wuxing": f"{t_wx}{r_wx}{d_wx}", "rating": label, "score": sc, "desc": desc},
        "shuli": shuli, "shuli_key_score": key_shuli,
        "score": round(sc * 0.5 + key_shuli * 0.5),
    }


if __name__ == "__main__":
    import sys
    import json
    print(json.dumps(wuge(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
