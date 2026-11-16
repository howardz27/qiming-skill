# -*- coding: utf-8 -*-
"""04_tag_vibes.py — 给 chars.jsonl 批量加 vibe（风格）与 taste_risk（俗气风险）标签

vibe 分类（多选）：
  清雅  素净、清冷、留白感（月、雪、汀、素）
  文气  书卷气、儒雅（文、翰、彦、辞）
  大气  开阔、宏大（瀚、宇、鹏、岳）
  灵动  活泼、明快、聪慧（欣、悦、灵、曦）
  硬朗  刚毅、力量（刚、毅、锋、峻）
  甜美  柔美、暖甜（嫣、馨、甜系花草柔字）

taste_risk：直白/老派/年代感重，起名易显俗（花、朵、福、贵、舞、菊）
  仅软惩罚：命中一字小扣，两字大扣（在 scorer 内实现）。

用法：python builder/04_tag_vibes.py   （原地写回 knowledge/chars.jsonl，幂等）
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARS_PATH = os.path.join(BASE, "knowledge", "chars.jsonl")

# ---- 手工标注（覆盖全部 594 字；遗漏者默认 ["文气"] 并在 stderr 提示）----
VIBE = {
    "清雅": "清澈澹素简静默深皎皓月星辰汉霄岚烟霞霜璧琦琬琰璟璨璐玥瑗珑泠涓汐湄沂滢漪汀沐冰凝雪露霏黛翠碧青白泠汀渃浣淇潇湘湛?洛洲渚浦滨涯谷溪涧泉畹野旷峦岫?杳渺淼晶莹洁瀛灏濯沧晏?晚夕曈?昙?晗?昀晔旻昱照焕烨煊炜昕晞煦曦"
           .replace("?", ""),
    "文气": "文书雅诗辞章翰彦儒仕修格物智睿哲慧思省观闻见喻言琴瑟棋画绘意歆音韵律咏吟曲谦温良善慈仁义诚正信德恒致远治平承绍继绪纬纶绪?翰?圭?序度?士?君?郎?彦?翰?修?致?格?真璞?简?曲?韶?读?耕?牧?管弦?申?延?公?伯仲季昆?求?克复?喻?"
           .replace("?", ""),
    "大气": "宏宇昊瀚浩洋沛泽涛潮澜鹏骏驰龙麟麒鸿翔腾跃超群伟世泰鼎隆昌盛旺卓岳峰岩磊山川江河海峰?巍嵩崇峨峻?峤?鼎?定?晋登进升?振?鸿?翥翱骐骥?鲸鲲?疆?垂重?境?增?野旷?昭?尧舜禹?世?邦城廷社稷?乾坤震易衍?九?鼎?"
           .replace("?", ""),
    "灵动": "欣悦怡乐舒畅语笑欢暖曦晞昕灵巧伶俐曼妙燕莺鹊鸽鸥鹭雁羽翎?旖旎?曼?漫?妙?姣娉倩窈?盼?歌?舞?跃?潇漾潋滟?奕?飒爽?晴?虹?彩彤?禾年春?苗?芽?new?"
           .replace("?", "").replace("new", ""),
    "硬朗": "刚强健力劲毅勇武军征胜捷凯锋锐剑铖钧铭鉴铸钊铄钰?巍峻崇?石磊?岩?铁?钢?武?威?骁?飒?卓?超?劲?毅恒?振?胜?",
    "甜美": "嫣芝蕊蓓蕾馨芬芳馥郁沁婷娟娥娴婉妍姝妤婕芊茵芸茜菲莉荷莲菱蓉芷蘅萱桃杏梅樱柳栀棠樱?馥?甜?暖?依?侬?妙?姣?娅媛?娜?",
}
# 清理：去掉空格与非汉字
def _clean(s):
    return "".join(ch for ch in s if "\u4e00" <= ch <= "\u9fff")

VIBE = {k: _clean(v) for k, v in VIBE.items()}

TASTE_RISK = _clean("花朵卉福贵旺堂舞菊红彩娟娥娜娇淑美英庆祥凤歌")


def main():
    chars = [json.loads(l) for l in open(CHARS_PATH)]
    untagged = []
    for rec in chars:
        c = rec["char"]
        tags = [v for v, chars_v in VIBE.items() if c in chars_v]
        if not tags:
            tags = ["文气"]
            untagged.append(c)
        rec["vibe"] = tags
        rec["taste_risk"] = c in TASTE_RISK
    with open(CHARS_PATH, "w", encoding="utf-8") as f:
        for rec in chars:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"tagged {len(chars)} chars; taste_risk={len(TASTE_RISK)}字: {TASTE_RISK}")
    if untagged:
        print(f"[WARN] 未显式标注(默认文气) {len(untagged)} 字: {''.join(untagged)}", file=sys.stderr)
    # 分布统计
    from collections import Counter
    cnt = Counter(t for rec in chars for t in rec["vibe"])
    print("分布:", dict(cnt))


if __name__ == "__main__":
    main()
