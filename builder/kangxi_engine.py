# -*- coding: utf-8 -*-
"""康熙笔画引擎（姓名学口径）。

权威数据源（Unicode 官方）：
- CJKRadicals.txt: 214 康熙部首号 → 部首本字 → 全形笔画（水4/玉5/艸6/邑7/金8…）
- Unihan 16.0 kRSUnicode: 字 → 康熙部首号.余部笔画（余部相对部首书写形）
- Unihan 16.0 kTotalStrokes: 简体/本字字形笔画
- Unihan 16.0 kTraditionalVariant: 简体 → 繁体

公式：康熙笔画 = 部首全形笔画 + 余部笔画（繁体字形）
例: 清(繁体同形) = 水4 + 8 = 12；芳 = 艸6 + 4 = 10；郭 = 邑7 + 8 = 15；萬 = 艸6 + 9 = 15
"""
import os
from functools import lru_cache

BASE = os.path.join(os.path.dirname(__file__), "..")
UNIHAN_DIR = os.path.join(BASE, "data", "raw", "unihan16")
CJK_RADICALS = os.path.join(BASE, "data", "raw", "CJKRadicals.txt")

# 人工勘误：姓名学通行口径与机器推算冲突的字
# 依据：姓名学通行"简体对应标准繁体"口径（台湾户政/主流起名平台一致）
OVERRIDES = {
    "王": 4,   # 王作独立字/姓氏计4画；王字旁作偏旁按玉部5画由引擎自动处理
    # 姓氏与常用字中"简体字形本身也是古字/别义字"导致变体映射歧义的
    "刘": 15, "万": 15, "苏": 22, "范": 11, "于": 3,
    "孙": 10, "郑": 19, "罗": 20, "叶": 15, "乔": 12,
    # 常见名字用字（简繁映射取词典义的标准繁体）
    "云": 12, "宁": 14, "丰": 18, "乐": 15, "华": 14, "岚": 12,
    "风": 9, "飞": 9, "广": 15, "书": 10, "义": 13, "凤": 14,
    "龙": 16, "圣": 13, "贤": 15, "聪": 17, "卫": 15, "兰": 23,
    # 本字即标准字（变体为别义）：松(鬆为散义) 秋(鞦为秋千) 冬(鼕为鼓声) 朱(硃)等
    "志": 7, "松": 8, "秋": 9, "冬": 5, "同": 6, "合": 6, "曲": 6,
    "才": 4, "克": 7, "咸": 9, "向": 6, "后": 6,
    "朱": 6, "胡": 11, "余": 7, "沈": 8, "姜": 9,
    # 检索核实：温(水4+昷9)=13 芸(艸6+云4)=10
    "温": 13, "芸": 10,
}

# 部首全形笔画修正（kTotalStrokes 与康熙部首标准笔画不一致的）
RADICAL_FIX = {194: 10}  # 鬼部10画


class KangxiEngine:
    def __init__(self):
        self.radical_strokes = {}  # 部首号 -> 全形笔画
        self.rs = {}               # char -> (radical, residual)
        self.total = {}            # char -> 本字字形笔画
        self.traditional = {}      # 简体 -> [繁体候选]
        self._load()

    def _load(self):
        for line in open(CJK_RADICALS, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "'" in line.split(";")[0]:
                continue
            parts = [p.strip() for p in line.split(";")]
            if len(parts) != 3:
                continue
            try:
                num = int(parts[0])
                uni = chr(int(parts[2], 16))
            except ValueError:
                continue
            self.radical_strokes[num] = None
            self._radical_chars = getattr(self, "_radical_chars", {})
            self._radical_chars[num] = uni

        files = {
            "Unihan_IRGSources.txt": self._h_irg,
            "Unihan_DictionaryLikeData.txt": self._h_dict,
            "Unihan_Variants.txt": self._h_var,
        }
        for fn, handler in files.items():
            path = os.path.join(UNIHAN_DIR, fn)
            with open(path, encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("U+"):
                        continue
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) < 3:
                        continue
                    handler(chr(int(parts[0][2:], 16)), parts[1], parts[2])

        # 部首全形笔画 = 部首本字的 kRSUnicode residual0 + ? —— 部首本字：canonical = residual(=0时)用 kTotalStrokes
        # 部首本字如 水=85.0：全形笔画 = 4 = kTotalStrokes(水)。直接用 kTotalStrokes。
        for num, uni in self._radical_chars.items():
            if num in RADICAL_FIX:
                self.radical_strokes[num] = RADICAL_FIX[num]
            elif uni in self.total:
                self.radical_strokes[num] = self.total[uni]

    def _h_irg(self, ch, field, val):
        if field == "kRSUnicode":
            first = val.split()[0].split(".")
            if len(first) >= 2 and first[0].isdigit() and first[1].rstrip("'").isdigit():
                r = int(first[0])
                res = int(first[1].rstrip("'"))
                if 1 <= r <= 214:
                    self.rs.setdefault(ch, (r, res))
        elif field == "kTotalStrokes":
            v = val.split()[0]
            if v.isdigit():
                self.total.setdefault(ch, int(v))

    def _h_dict(self, ch, field, val):
        if field == "kTotalStrokes":
            v = val.split()[0]
            if v.isdigit():
                self.total.setdefault(ch, int(v))

    def _h_var(self, ch, field, val):
        if field not in ("kTraditionalVariant",):
            return
        chars = []
        for v in val.split():
            v = v.split("<")[0].split("(")[0]
            if v.startswith("U+") and len(v) >= 6:
                try:
                    chars.append(chr(int(v[2:], 16)))
                except ValueError:
                    pass
        if chars:
            self.traditional.setdefault(ch, chars)

    def traditional_form(self, ch):
        """姓名学口径取繁体：候选含自身（该字简繁同形语境）时取首个非自身候选
        （如 涛→濤、远→遠、万→萬）；无候选或全为自身则用自身。"""
        cands = self.traditional.get(ch, [])
        if not cands:
            return ch
        if cands[0] == ch:
            for c in cands[1:]:
                if c != ch:
                    return c
            return ch
        return cands[0]

    def _calc(self, ch):
        if ch in self.rs:
            r, res = self.rs[ch]
            base = self.radical_strokes.get(r)
            if base is not None:
                return base + res
        return None

    def kangxi(self, ch):
        """返回 (康熙笔画, confidence)。A=权威推算 D=无数据"""
        if ch in OVERRIDES:
            return OVERRIDES[ch], "A"
        trad = self.traditional_form(ch)
        for target in (trad, ch):
            v = self._calc(target)
            if v is not None:
                return v, "A"
        # 兜底：繁体总笔画近似
        for target in (trad, ch):
            if target in self.total and target != ch:
                return self.total[target], "B"
        return None, "D"

    def simplified_strokes(self, ch):
        return self.total.get(ch)


@lru_cache(maxsize=1)
def get_engine():
    return KangxiEngine()


if __name__ == "__main__":
    e = get_engine()
    print("radicals loaded:", sum(1 for v in e.radical_strokes.values() if v))
    known = {"张": 11, "李": 7, "清": 12, "钱": 16, "陈": 16, "杨": 13, "黄": 12,
             "赵": 14, "刘": 15, "孙": 10, "马": 10, "郑": 19, "王": 4,
             "吴": 7, "郭": 15, "胡": 11, "泽": 17, "东": 8, "伟": 11, "芳": 10,
             "罗": 20, "周": 8, "林": 8, "何": 7, "高": 10, "朱": 6, "徐": 10,
             "谢": 17, "宋": 7, "唐": 10, "许": 11, "韩": 17, "冯": 12, "邓": 19,
             "曹": 11, "彭": 12, "曾": 12, "肖": 9, "田": 5, "董": 15, "潘": 16,
             "袁": 10, "蔡": 17, "蒋": 17, "余": 7, "杜": 7, "叶": 15, "程": 12,
             "苏": 22, "魏": 18, "吕": 7, "丁": 2, "任": 6, "沈": 8, "姚": 9,
             "卢": 16, "姜": 9, "崔": 11, "钟": 17, "谭": 19, "陆": 16, "汪": 8,
             "范": 11, "金": 8, "石": 5, "廖": 14, "贾": 13, "夏": 10, "韦": 9,
             "傅": 12, "方": 4, "白": 5, "邹": 17, "熊": 14, "孟": 8, "秦": 10,
             "邱": 12, "江": 7, "尹": 4, "薛": 19, "段": 9, "雷": 13, "侯": 9,
             "龙": 16, "史": 5, "陶": 16, "黎": 15, "贺": 12, "顾": 21, "毛": 4,
             "郝": 14, "龚": 22, "邵": 12, "万": 15, "严": 20, "覃": 12,
             "洪": 10, "武": 8, "莫": 13, "乔": 12, "汤": 13, "殷": 10, "樊": 15,
             "泽": 17, "铭": 14, "淑": 12, "轩": 10, "涵": 12, "瑞": 14, "睿": 14}
    bad = []
    for ch, expect in known.items():
        got, conf = e.kangxi(ch)
        if got != expect:
            bad.append((ch, expect, got, conf))
    if bad:
        print(f"MISMATCH {len(bad)}/{len(known)}:")
        for ch, ex, got, conf in bad:
            print(f"  {ch}: expect={ex} got={got} conf={conf}")
    else:
        print(f"ALL {len(known)} regression cases PASSED")
