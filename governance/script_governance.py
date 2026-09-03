#!/usr/bin/env python3
"""Luna's Astral Code unified script governance.

This tool accepts the current Master Playbook as the contract.  It protects
fixed template literals, derives dynamic type-1/type-5 panxiang combinations
from the user-approved A1+B1 rule set, rewrites only registered variable prose,
and audits all unpublished posts before release.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from copy import deepcopy
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / "lunas_astral_code_master_playbook.md"
RULES_FILE = ROOT / "governance/dynamic_panxiang_rules.json"
REGISTRY_FILE = ROOT / "governance/panxiang_dedup_registry.json"
RULE_MAP_FILE = ROOT / "governance/latest_playbook_rule_map.json"
AUDIT_FILE = ROOT / "governance/rewrite_audit.json"
FILES = (
    ROOT / "scripts/60day_scripts_W4-W9_20260817-20260925.md",
    ROOT / "scripts/60day_scripts_W7-W9_20260905-20260926.md",
)
MODEL = "gpt-5"
PUBLISHED = {"2026-08-17", "2026-08-18"}
THEME_START = "2026-08-20"
TYPE3_SSOT = {
    "2026-08-20": {"data_file": "data/ZWQS_Juan2_Consolidated.json", "source_locator": "ZWQS_Juan2_AnSihua_L002", "intent": "sihua", "palaces": []},
    "2026-09-03": {"data_file": "engines/diagnosis_router_module_v1.json", "source_locator": "routing_rules[4].palace_priority[0] = 福德宮", "intent": "inner_spirit_resilience", "palaces": ["福德宮"]},
    "2026-09-17": {"data_file": "engines/diagnosis_router_module_v1.json", "source_locator": "routing_rules[7].palace_priority[0] = 遷移宮", "intent": "outer_image_mobility", "palaces": ["遷移宮"]},
}
TYPE4_QIMEN_SSOT = {
    "2026-08-27": {
        "topic": "奇門為什麼重視時間", "hook": "奇門不是只看方位，也看你問的是哪個時刻。",
        "data_file": "data/QMDJ_XiaJuan_Consolidated.json", "system_line_id": "QMDJ_Juan30_L011",
        "source_locator": "entries[line_id=QMDJ_Juan30_L011]；《奇門遁甲秘笈大全》下卷·卷30，段落11",
        "original_quote": "此地盤一定不易者也。所謂地主靜也，五日換一元。天盤則時時不同，所謂天主動也。如乙丑時則以休門加天盤坤為值使，以值符天蓬星甲子戊加離九為值符，諸照此例。",
        "source_type": "classical_text", "verification_status": "verified", "school_tag": "source_text_only",
    },
    "2026-09-10": {
        "topic": "奇門八門：門各有本位", "hook": "奇門的八門，不是八種個性。它們各有本來的位置。",
        "data_file": "data/QMDJ_ShangJuan_Consolidated.json", "system_line_id": "QMDJ_Auto_01345",
        "source_locator": "entries[line_id=QMDJ_Auto_01345]；《奇門遁甲秘笈大全》上卷·卷13，段落35",
        "original_quote": "休，坎宅門路。生，艮宅門路。傷，震宅門路。杜，巽宅門路。景，離宅門路。死，坤宅門路。驚，兌宅門路。開，乾宅門路。",
        "source_type": "classical_text", "verification_status": "verified", "school_tag": "source_text_only",
    },
    "2026-09-24": {
        "topic": "值符與值使：一個看星，一個看門", "hook": "看到值符、值使先不用怕，它們不是同一件事。",
        "data_file": "data/QMDJ_XiaJuan_Consolidated.json", "system_line_id": "QMDJ_Juan30_L011",
        "source_locator": "entries[line_id=QMDJ_Juan30_L011]；《奇門遁甲秘笈大全》下卷·卷30，段落11",
        "original_quote": "此地盤一定不易者也。所謂地主靜也，五日換一元。天盤則時時不同，所謂天主動也。如乙丑時則以休門加天盤坤為值使，以值符天蓬星甲子戊加離九為值符，諸照此例。",
        "source_type": "classical_text", "verification_status": "verified", "school_tag": "source_text_only",
    },
}
SERIAL_THEME_FILE = ROOT / "governance/script_theme_arc_v42.json"


def load_theme_plans() -> dict[str, dict]:
    payload = json.loads(SERIAL_THEME_FILE.read_text(encoding="utf-8"))
    if payload.get("version") != "4.2":
        raise ValueError("主題地圖版本必須為 v4.2。")
    plans = {}
    for date, raw in payload["posts"].items():
        plan = {key: value for key, value in raw.items() if key not in {"act", "function", "ssot"}}
        plan["arc_act"] = raw["act"]
        plan["function"] = raw["function"]
        plan["bridge_from"] = raw["bridge_from"]
        plan["bridge_to"] = raw["bridge_to"]
        if raw.get("ssot") == "type3":
            plan["ssot"] = TYPE3_SSOT[date]
        elif raw.get("ssot") == "type4":
            plan["ssot"] = TYPE4_QIMEN_SSOT[date]
        plans[date] = plan
    return plans


THEME_PLANS = load_theme_plans()
TYPE3_SSOT_TERMS = {"2026-08-20": "四化標記", "2026-09-03": "福德宮", "2026-09-17": "遷移宮"}
PENDING = "【待記錄】發布後48小時：reach / 非追蹤者觸及 / profile visits / website clicks / DM / saves / shares"
STANDARD_START = "## 【五大型式文案排版輸出標準規範】"
GUIDE_TITLE = "## 小說式描寫文風（v4.2｜唯一全局文風規範，奇門專用）"
STYLE_MIGRATION_START = "2026-09-01"
STANDARD_SHA256 = "3a91f1d6f23a820fd5e465bda645c80f625d208cefd864c6a79ba9a1d067aa48"
GUIDE_SHA256 = "2e8e8b909ceabd7bd4674207c3e296c6e6adef8ca1785dbf440f5d5bcb25754e"
PLAYBOOK_SHA256 = "915536646086dd1cffd4743e04633acd3f6b72c37c6c8e4129ad8d0feb3b1ad4"
DYNAMIC_RULES_SHA256 = "0c2c78bfbce6054423698de3905bd3b2efbfa5400f542f15728391da1c5956a5"
SERIAL_THEME_SHA256 = "b62693974c0a0ff07721c4947c2a56b4a1996be2880b21051813d29f920c3b30"
CTA = {
    "型式一": "下方留言 A / B / C / D / E / F 👇🏻\n【解答將於 24 小時後置頂留言區】",
    "型式二": "點擊「追蹤」隨時陪伴在你身邊～",
    "型式三": "點擊「收藏」打開命盤隨時上手\n下一期繼續拆解一個排盤小知識",
    "型式四": "點擊「分享」給朋友一起確認吧～",
    "型式五上集": "「留言」A / B / C 明天置頂留言區公佈解答 ✨\n想看後續「完整解讀」留意下一集",
    "型式五下集": "喜歡這期解讀指引的朋友\n歡迎「收藏 + 追蹤」持續領取你的解讀提示吧～\n\n若想針對個人問題進行深入解析 📩\n歡迎直接 DM 預約一對一的專屬命盤諮詢 🌙",
}
RETIRED_DECLARATIONS = (
    "不是替你排出的個人命盤", "沒有你的個人起局資料", "沒有個人起局資料",
    "不替你安門", "不會替你安門", "也不判方位", "不判斷方位",
    "公開奇門資料中的對照示例", "公開奇門資料可對照的示例", "並非替你個人起局後得出的結論",
    "已驗證資料：", "未核實的", "這篇不談未核實", "這篇只看",
    "本篇只教讀取盤面標示。", "本篇只做定位與記錄，不輸出個人關係判定。", "本篇只做盤面讀取與記錄。",
)
RETIRED_TEXT = ("視覺規範核對清單", "【每張固定版面】", "視覺設定：", "上集主題 +", "三個圖騰並排，提醒讀者回到原選項")
ANCHOR_PATTERN = r"西北|正北|正東|正西|正南|東北|東南|西南|中央|子時|丑時|寅時|卯時|辰時|巳時|午時|未時|申時|酉時|戌時|亥時|早上|下午|晚上|深夜|肩頸|睡眠"
PRECISE_ANCHOR_PATTERN = r"(?:早上|下午|晚上)\s*\d{1,2}\s*(?:[–—\-至到])\s*\d{1,2}\s*(?:點|時)|\d+\s*(?:步|分鐘|天)"
SIMPLIFIED_CHARS = "个这时后里么说给动过还"
TYPOGRAPHIC_BLOCKED = ("不子是", "占住")
DANGLING_CONNECTIVES = ("而且", "並且", "以及", "或者", "或", "但是", "所以", "因此", "從而")
RELATIONAL_PAIRS = (("不但", ("而且", "也")), ("不僅", ("也", "還")))
OUTCOME_GUARANTEE_PATTERN = r"你(?:注定|必然|一定會|百分之百)|保證(?:你|會|得到)|只要[^。！？\n]{0,30}就會"
UNSUPPORTED_AUTHORITY_TERMS = ("心理諮商", "療癒技術", "臨床診斷", "投資保證")
AI_STYLE_TELLS = ("真正的問題是", "本質上", "防護機制", "靜默力量", "底層邏輯", "賦能", "生命路徑", "能量消耗", "共振", "典範轉移", "改寫一切")

def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def prose_sentences(text: str) -> list[str]:
    """Return prose sentences while excluding required structural labels and Markdown markers."""
    sentences = []
    for raw_line in text.splitlines():
        line = raw_line.strip().removeprefix("‧ ").replace("**", "")
        if not line or line.startswith(("【盤象：", "【時空與感官錨定】", "【奇門行為改運】", "選項 ")):
            continue
        sentences.extend(piece.strip() for piece in re.split(r"[。！？；]", line) if piece.strip())
    return sentences


def sentence_quality_issues(text: str) -> list[str]:
    """Detect only high-confidence Chinese sentence-quality risks; model review handles semantic judgment."""
    issues = []
    simplified = sorted({char for char in text if char in SIMPLIFIED_CHARS})
    if simplified:
        issues.append(f"含簡體字：{'、'.join(simplified)}")
    issues.extend(f"含錯別字：{word}" for word in TYPOGRAPHIC_BLOCKED if word in text)
    if re.search(r"[，。！？；]{2,}", text):
        issues.append("重複中文標點")
    if re.search(r"[\u3400-\u9fff],[\u3400-\u9fff]", text):
        issues.append("中文句內混用半形逗號")
    if text.count("「") != text.count("」") or text.count("（") != text.count("）"):
        issues.append("引號或括號未成對")
    for sentence in prose_sentences(text):
        if cjk_count(sentence) > 60 and not re.search(r"[，、】【]", sentence):
            issues.append("句子過長且缺少自然停頓")
        if sentence.endswith(DANGLING_CONNECTIVES):
            issues.append("句尾懸空連詞")
        for left, allowed_rights in RELATIONAL_PAIRS:
            if left in sentence and not any(right in sentence for right in allowed_rights):
                issues.append(f"關聯詞未配對：{left}……{'／'.join(allowed_rights)}")
    return sorted(set(issues))


def semantic_boundary_issues(text: str) -> list[str]:
    """Reject result promises and unsupported authority; v4.1 allows track-B scenes when useful."""
    issues = []
    if re.search(OUTCOME_GUARANTEE_PATTERN, text):
        issues.append("含外部結果承諾")
    issues.extend(f"含不支援的專業權威詞：{term}" for term in UNSUPPORTED_AUTHORITY_TERMS if term in text)
    issues.extend(f"含常見 AI 腔：{term}" for term in AI_STYLE_TELLS if term in text)
    return issues


def track_a_issues(text: str, combo: dict) -> list[str]:
    """Require Qimen-bound narration for Track A; reject generic portable divination prose."""
    issues = []
    forbidden = ("塔羅", "牌義", "牌陣", "星座", "宮位", "九型人格")
    issues.extend(f"援引非奇門占卜體系：{term}" for term in forbidden if term in text)
    required_terms = (combo.get("star", ""), combo.get("door", ""), combo.get("spirit", ""), combo.get("qi", ""), combo.get("hour", "") + "時", combo.get("direction", ""), combo.get("auspice", ""))
    if not any(term and term in text for term in required_terms):
        issues.append("軌道 A 未綁定已登錄奇門五元組，敘事可移植至其他占卜工具")
    return issues


def form(header: str) -> str:
    return next(item for item in ("型式五下集", "型式五上集", "型式一", "型式二", "型式三", "型式四") if item in header)


def split_blocks(text: str):
    matches = list(re.finditer(r"(?m)^## (2026-\d{2}-\d{2}).*$", text))
    for index, marker in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield marker.group(1), marker.group(0), text[marker.start():end]


def unpublished_blocks():
    for path in FILES:
        text = path.read_text(encoding="utf-8")
        for date, header, block in split_blocks(text):
            if date >= "2026-08-20" and date not in PUBLISHED:
                yield path, date, header, block


def section(block: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), block, re.S)
    if not match:
        raise ValueError(f"Cannot locate section {start!r}")
    return match.group(1)


def normalize_block(block: str) -> str:
    """Synchronize only changed fixed typography for an unpublished block."""
    changed = block
    for color in ("#0D0D2B", "#F5F5DC", "#B4918F", "#E8E8F0", "#1A1A3A"):
        changed = changed.replace(f"`{color}`", color)
    changed = changed.replace("#B4918F圖騰線稿", "#B4918F 圖騰線稿")
    changed = changed.replace("暖米白底#F5F5DC", "暖米白底 #F5F5DC")
    changed = changed.replace("深海軍藍#0D0D2B", "深海軍藍 #0D0D2B")
    changed = changed.replace("霧玫瑰金#B4918F", "霧玫瑰金 #B4918F")
    changed = changed.replace("約 2–3 幀", "約 23 幀")
    changed = changed.replace("將這 AF 6 張圖騰", "將這 A–F 6 張圖騰")
    changed = changed.replace("固定CTA：", "固定 CTA：")
    changed = changed.replace("視覺分鏡描述（Reels，20 張，4:5，20 秒，底部固定標籤）：", "視覺分鏡描述（Reels，4:5，20 秒，底部固定標籤）：")
    changed = changed.replace("【主體閃爍序列（6張 中央圖騰，0.08 秒/張 無縫硬切循環）】 6 組圖騰：", "【主體閃爍序列（6 張中央圖騰，0.08 秒/張，無縫硬切循環）】6 組圖騰：")
    changed = changed.replace("暖米白  #F5F5DC", "暖米白 #F5F5DC")
    changed = changed.replace("* 大標題：", "- 大標題：")
    changed = changed.replace("* 副標題：", "- 副標題：")
    changed = changed.replace("* 小 CTA：", "- 小 CTA：")
    changed = changed.replace("* 小 CTA 2：", "- 小 CTA 2：")
    changed = changed.replace("* A：", "- A：").replace("* B：", "- B：").replace("* C：", "- C：").replace("* D：", "- D：").replace("* E：", "- E：").replace("* F：", "- F：")
    changed = changed.replace("* 將這 A–F 6 張圖騰", "- 將這 A–F 6 張圖騰")
    changed = changed.replace("* 6 張圖片連續循環閃爍播放 15 秒。", "- 6 張圖片連續循環閃爍播放 15 秒。")
    changed = changed.replace("的速度進行切換\n- 6 張圖片", "的速度進行切換。\n- 6 張圖片")
    changed = re.sub(r"\n已驗證資料：[^\n]+\n", "\n", changed)
    changed = re.sub(r"\+ 已驗證資料：.*?(?=｜(?:深海軍藍|月白銀))", "", changed, flags=re.S)
    changed = changed.replace("本篇只教讀取盤面標示。", "")
    changed = changed.replace("本篇只做定位與記錄，不輸出個人關係判定。", "")
    changed = changed.replace("本篇只做盤面讀取與記錄。", "")
    changed = changed.replace("天沖星", "天冲星").replace(" he ", " 他 ")
    changed = changed.replace("【置頂留言區解答｜24 小時發布後】", "【置頂留言區解答｜24 小時後發布】")
    changed = changed.replace("｜共鳴型｜型式四", "｜資訊型｜型式四")
    changed = re.sub(r"(（3）三選項圖卡.*?暖米白 #F5F5DC)（邊框 \+ 文字）", r"\1（邊框）", changed)
    changed = re.sub(r"(?m)^(- [A-F]：.+?)\s*\+\s*暖米白", lambda match: match.group(1).rstrip() + " + 暖米白", changed)
    changed = re.sub(r"(?m)^(- [A-F]：[^\n]+)\n{2,}", r"\1\n", changed)
    changed = changed.replace("的速度進行切換\n", "的速度進行切換。\n")
    return changed


def synchronize_fixed_typography() -> dict:
    changed_files = []
    for path in FILES:
        source = path.read_text(encoding="utf-8")
        rebuilt = source
        for date, _, block in list(split_blocks(source)):
            if date < "2026-08-20" or date in PUBLISHED:
                continue
            normalized = normalize_block(block)
            if date in TYPE3_SSOT_TERMS:
                normalized = normalized.replace("命盤標記", TYPE3_SSOT_TERMS[date])
            if normalized != block:
                if rebuilt.count(block) != 1:
                    raise ValueError(f"Ambiguous fixed-template migration for {date}")
                rebuilt = rebuilt.replace(block, normalized, 1)
        if rebuilt != source:
            path.write_text(rebuilt, encoding="utf-8")
            changed_files.append(str(path.relative_to(ROOT)))
    return {"changed_files": changed_files}


def answer_slots(block: str, labels: str) -> list[dict]:
    anchor = "【置頂留言區解答｜"
    start = block.find(anchor)
    if start < 0:
        raise ValueError("Pinned-answer section absent")
    end = block.find("————————————", start)
    region = block[start:end if end >= 0 else len(block)]
    slots = []
    for label in labels:
        match = re.search(rf"(?ms)^{label}：(.*?)(?=\n\n[{'|'.join(labels)}]：|\Z)", region)
        if not match:
            raise ValueError(f"Missing pinned answer {label}")
        slots.append({"id": f"answer_{label}", "text": match.group(1).strip(), "minimum_cjk": 20, "maximum_cjk": 60, "short_dynamic": True})
    return slots


def lower_cards(block: str) -> list[dict]:
    slots = []
    for number, label in zip((3, 4, 5), "ABC"):
        match = re.search(
            rf"(?ms)^（{number}）{label} 選項完整解讀卡（[^）]+）：(.*?)(?=｜暖米白底 #F5F5DC、深海軍藍 #0D0D2B（文字）、霧玫瑰金 #B4918F（邊框 \+ 圖騰線稿）。)",
            block,
        )
        if not match:
            raise ValueError(f"Missing latest-template lower card {label}")
        slots.append({"id": f"card_{label}", "text": match.group(1).strip(), "minimum_chars": 300})
    return slots


def hook_slot(block: str) -> dict:
    match = re.search(r"(?m)^Hook： 【(.*?)】$", block)
    if not match:
        raise ValueError("Hook absent")
    return {"id": "hook", "text": match.group(1).strip(), "minimum_cjk": 1}


def themed_slots(block: str, kind: str, date: str) -> list[dict]:
    slots = slots_for(block, kind)
    if kind == "型式五上集" and THEME_PLANS.get(date, {}).get("scene"):
        return [slot for slot in slots if slot["id"] != "scene"]
    return slots


def slots_for(block: str, kind: str) -> list[dict]:
    body = section(block, "正文：\n", "\n\nHashtags：")
    if kind == "型式一":
        scene = body.split("\n長按螢幕 +「留言」領取你的「專屬能量提示」")[0].strip()
        slots = [{"id": "scene", "text": scene, "minimum_cjk": 30}]
        slots.extend(answer_slots(block, "ABCDEF"))
        return slots
    if kind == "型式二":
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) not in {3, 6}:
            raise ValueError(f"Type 2 needs three logical fields, got {len(lines)} prose lines")
        labels = ("scene", "reflection", "action") if len(lines) == 3 else ("scene_1", "scene_2", "reflection_1", "reflection_2", "action_1", "action_2")
        return [hook_slot(block)] + [{"id": name, "text": value, "minimum_cjk": 0} for name, value in zip(labels, lines)]
    if kind == "型式三":
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) < 3:
            raise ValueError("Type 3 body incomplete")
        return [{"id": "explain", "text": lines[1], "minimum_cjk": 50}]
    if kind == "型式四":
        lines = [
            line.strip() for line in body.splitlines()
            if line.strip() and not line.startswith(("【原文層】", "【象義層】", "【創作層】"))
        ]
        if len(lines) not in {3, 6}:
            raise ValueError(f"Type 4 needs three logical fields, got {len(lines)} prose lines")
        labels = ("scene", "check", "action") if len(lines) == 3 else ("scene_1", "scene_2", "check_1", "check_2", "action_1", "action_2")
        return [{"id": name, "text": value, "minimum_cjk": 0} for name, value in zip(labels, lines)]
    if kind == "型式五上集":
        scene = re.search(r"(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺", body)
        tip = re.search(r"(?ms)^🔮 C\. .*?\n\n(.*?)\n下一期帶你解鎖更多新的占卜提示～", body)
        if not scene or not tip:
            raise ValueError("Type 5 upper scene or tip missing")
        slots = [
            {"id": "scene", "text": scene.group(1).strip(), "minimum_cjk": 1, "maximum_cjk": 25, "short_window": True, "hook_context": hook_slot(block)["text"]},
            {"id": "tip", "text": tip.group(1).strip(), "minimum_cjk": 1, "maximum_cjk": 50},
        ]
        slots.extend(answer_slots(block, "ABC"))
        return slots
    if kind == "型式五下集":
        return lower_cards(block)
    raise ValueError(kind)


def load_rules() -> dict:
    if sha(RULES_FILE.read_text(encoding="utf-8")) != DYNAMIC_RULES_SHA256:
        raise ValueError("動態盤象規則來源雜湊不符；須重新確認版本。")
    return load_json(RULES_FILE)


def normalize_star_category(category: str) -> str:
    if category.startswith("吉星"):
        return "吉星"
    if category.startswith("中平星"):
        return "中平星"
    return "凶星"


def qi_category(qi: str) -> str:
    return "三奇" if qi in ("乙", "丙", "丁") else "六儀"


def auspice(rules: dict, star: str, door: str, spirit: str, qi: str) -> tuple[int, str]:
    matrix = rules["auspice_judgment_matrix_吉凶判斷矩陣"]
    score = (
        matrix["star_category_weight"][normalize_star_category(rules["nine_stars_九星"][star]["category"])]
        + matrix["door_category_weight"][rules["eight_doors_八門"][door]["category"]]
        + matrix["spirit_category_weight"][rules["eight_spirits_八神"]["category"][spirit]]
        + matrix["qi_yi_category_weight"][qi_category(qi)]
    )
    if score >= 4:
        label = "大吉"
    elif score >= 1:
        label = "中吉"
    elif score == 0:
        label = "平（吉凶參半）"
    elif score >= -3:
        label = "中凶"
    else:
        label = "大凶"
    return score, label


def combo_key(combo: dict) -> str:
    return "|".join((combo["star"], combo["door"], combo["spirit"], combo["qi"], combo["hour"]))


def derive_combo(rules: dict, star: str, door: str, spirit: str, qi: str, hour: str) -> dict:
    """Recompute derived display fields from an independently sampled five-tuple."""
    door_data = rules["eight_doors_八門"][door]
    score, label = auspice(rules, star, door, spirit, qi)
    combo = {
        "star": star,
        "door": door,
        "spirit": spirit,
        "qi": qi,
        "hour": hour,
        "sampling_model": "independent_v2",
        "door_palace": door_data["palace_name"],
        "direction": door_data["direction"],
        "score": score,
        "auspice": label,
    }
    combo["key"] = combo_key(combo)
    return combo


def generate_combo(rules: dict, occupied: set[str], used_stars: set[str], used_doors: set[str]) -> dict:
    rng = random.SystemRandom()
    stars = [item for item in rules["nine_stars_九星"] if item not in used_stars]
    doors = [item for item in rules["eight_doors_八門"] if item not in used_doors]
    spirits = list(rules["eight_spirits_八神"]["category"])
    qi_values = list(rules["three_qi_six_yi_三奇六儀"]["三奇"]) + list(rules["three_qi_six_yi_三奇六儀"]["六儀"])
    hours = rules["time_derivation_rule_時間推導規則"]["shi_chen_十二時辰"]
    for _ in range(500):
        star = rng.choice(stars)
        door = rng.choice(doors)
        spirit = rng.choice(spirits)
        qi = rng.choice(qi_values)
        hour = rng.choice(hours)
        combo = derive_combo(rules, star, door, spirit, qi, hour)
        if combo["key"] not in occupied:
            return combo
    raise RuntimeError("500 次抽樣後仍無可用盤象組合。")


def pair_map(posts: list[tuple[Path, str, str, str]]) -> dict[str, str]:
    uppers = sorted(date for _, date, header, _ in posts if form(header) == "型式五上集")
    lowers = sorted(date for _, date, header, _ in posts if form(header) == "型式五下集")
    return {lower: upper for upper, lower in zip(uppers, lowers)}


def dynamic_assignments(posts: list[tuple[Path, str, str, str]], registry: dict, rules: dict, persist: bool) -> dict[str, dict[str, dict]]:
    assignments = deepcopy(registry.get("assignments", {}))
    # v2.0 safety: preserve the independently sampled five-tuple, then recompute display fields.
    for date, values in assignments.items():
        for label, combo in list(values.items()):
            values[label] = derive_combo(rules, combo["star"], combo["door"], combo["spirit"], combo["qi"], combo["hour"])
    occupied = {item.get("five_tuple") for item in registry.get("recent_posts", []) if item.get("five_tuple")}
    for values in assignments.values():
        for combo in values.values():
            occupied.add(combo["key"])
    pairs = pair_map(posts)
    for _, date, header, _ in posts:
        kind = form(header)
        if kind not in {"型式一", "型式五上集"}:
            continue
        labels = "ABCDEF" if kind == "型式一" else "ABC"
        current = assignments.setdefault(date, {})
        used_stars = {combo["star"] for combo in current.values()}
        used_doors = {combo["door"] for combo in current.values()}
        for label in labels:
            if label not in current:
                combo = generate_combo(rules, occupied, used_stars, used_doors)
                current[label] = combo
                occupied.add(combo["key"])
                used_stars.add(combo["star"])
                used_doors.add(combo["door"])
    for lower, upper in pairs.items():
        assignments[lower] = deepcopy(assignments[upper])
    if persist:
        records = []
        for _, date, header, _ in posts:
            kind = form(header)
            if kind not in {"型式一", "型式五上集"}:
                continue
            for label, combo in sorted(assignments[date].items()):
                records.append({"date": date, "form": kind, "option": label, "five_tuple": combo["key"], "combo": combo})
        registry["assignments"] = assignments
        registry["recent_posts"] = records[-90:]
        registry["schema_source_sha256"] = DYNAMIC_RULES_SHA256
        registry["schema_version"] = "2.0"
        registry["decision_log"] = {
            "sampling_rule": "九星、八門、八神、奇儀、時辰均為獨立隨機抽樣輸入",
            "direction_rule": "門的固有宮位為卡面主方位",
            "auspice_rule": "以獨立抽樣的星、門、神、奇儀 category 權重加總映射五級吉凶",
            "dedup_rule": "星＋門＋神＋儀＋時辰五元組於近 30 篇內不得重複",
        }
        REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return assignments


def combo_terms(combo: dict) -> list[str]:
    return [combo["star"], combo["door"], combo["spirit"], combo["qi"], f'{combo["hour"]}時', combo["direction"], combo["auspice"]]


def add_dynamic_requirements(slots: list[dict], date: str, kind: str, assignments: dict[str, dict[str, dict]]):
    if kind not in {"型式一", "型式五上集", "型式五下集"}:
        return
    for slot in slots:
        label = slot["id"].rsplit("_", 1)[-1]
        if label not in "ABCDEF":
            continue
        combo = assignments[date][label]
        slot["label"] = label
        slot["combo"] = combo
        slot["five_layer"] = kind == "型式五下集"
        slot["short_dynamic"] = kind in {"型式一", "型式五上集"}
        if slot["five_layer"]:
            slot["must_include"] = combo_terms(combo)


def split_long_sentence(line: str) -> str:
    """Preserve model-chosen sentence rhythm; validation, not mechanical splitting, guards readability."""
    return line


def repair_three_field_boundaries(block: str, kind: str) -> str:
    """Repair only malformed variable prose whose sentence-level line breaks split a fixed three-field body."""
    if kind not in {"型式二", "型式三"}:
        return block
    body = section(block, "正文：\n", "\n\nHashtags：")
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if len(lines) <= 3:
        return block
    changed = block
    if kind == "型式三":
        raw, repaired = "\n".join(lines[1:-1]), "".join(lines[1:-1])
        return changed.replace(raw, repaired)
    if len(lines) % 3:
        raise ValueError(f"{kind} 的正文欄位無法平均修復：{len(lines)} 行。")
    group_size = len(lines) // 3
    for start in range(0, len(lines), group_size):
        group = lines[start:start + group_size]
        raw, repaired = "\n".join(group), "".join(group)
        changed = changed.replace(raw, repaired)
    return changed


def normalize_dynamic_option_heading(slots: list[dict], rewrites: dict[str, str]) -> dict[str, str]:
    """Preserve fixed field boundaries while normalizing sentence layout and required headings."""
    for slot in slots:
        source_lines = [split_long_sentence(line.strip()) for line in rewrites[slot["id"]].strip().splitlines() if line.strip()]
        value = "\n".join(source_lines) if slot.get("five_layer") else "".join(source_lines)
        rewrites[slot["id"]] = value
        if not slot.get("five_layer"):
            continue
        label = slot["label"]
        lines = rewrites[slot["id"]].splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        if slot.get("upper_answer"):
            conclusion = re.sub(rf"^\*\*選項 {label}[：:]\s*|\*\*$", "", slot["upper_answer"]).replace("**", "").strip()
            lines[0] = f"**選項 {label}：{conclusion}**"
            lines = [lines[0]] + [line for line in lines[1:] if not re.match(rf"^\*\*選項 {label}[：:]", line)]
        else:
            match = re.match(rf"^\*\*選項 {label}(?:\*\*)?[：:](.*?)(?:\*\*)?$|^選項 {label}[：:](.*)$", first)
            if match:
                conclusion = (match.group(1) if match.group(1) is not None else match.group(2)).strip()
                conclusion = re.sub(rf"^選項 {label}[：:]\s*", "", conclusion)
                lines[0] = f"**選項 {label}：{conclusion}**"
        rewrites[slot["id"]] = "\n".join(lines).strip()
    return rewrites


def request_rewrite(date: str, kind: str, header: str, slots: list[dict], theme: dict | None = None, retry: bool = False, feedback: str = "") -> dict[str, str]:
    payload_slots = []
    for slot in slots:
        item = {key: slot[key] for key in ("id", "text")}
        if slot.get("minimum_cjk") is not None:
            item["minimum_cjk"] = slot["minimum_cjk"]
        if slot.get("minimum_chars") is not None:
            item["minimum_chars"] = slot["minimum_chars"]
        if slot.get("maximum_cjk") is not None:
            item["maximum_cjk"] = slot["maximum_cjk"]
        if slot.get("combo"):
            item["combo"] = slot["combo"]
        if slot.get("must_include"):
            item["must_include"] = slot["must_include"]
        if slot.get("five_layer") or slot.get("short_dynamic"):
            item["five_layer"] = bool(slot.get("five_layer"))
            item["short_dynamic"] = bool(slot.get("short_dynamic"))
        if slot.get("upper_answer"):
            item["upper_answer"] = slot["upper_answer"]
        if slot.get("hook_context"):
            item["hook_context"] = slot["hook_context"]
        payload_slots.append(item)
    system = """你是繁體中文（臺灣）IG 奇門文案主筆。只能重寫 payload 內的可變欄位；未列入 payload 的 Hashtags、固定 CTA、卡片標題、圖騰、視覺模板、日期、色碼、卡數、盤象、SSOT 術語與固定文字不得輸出或改動。

先做三個隱性編輯步驟：第一，依 chinese-webnovel-studio 先讀 payload 的 topic、bridge_from 與 bridge_to，決定一個由前篇帶來、又能留給下篇的微型情境；只用一至兩個準確細節（物件、動作、停頓或對話前的空白），讓狀態自己說話。第二，依 good-writing-tw 刪掉空泛升華、同義重複與無用修辭，調整長短句與停頓，但不可把文字磨成節拍器。第三，依 direct-chinese-writing 使用直接、精準、臺灣讀者一眼懂的中文。保留原主題、事實、盤象、卡片用途與讀者可採取的行動。

v4.2 小說式描寫。型式一、二、三、四、五都使用玄學小說式描寫：依 payload 的 topic、bridge_from 與 bridge_to，先寫一個能投射的微型情境，再讓命理白話、知識或行動自然推進。每篇只用一至兩個準確細節（物件、動作、停頓或對話前的空白），讓狀態自己說話；不要替讀者編造真實經歷、精確日期、次數、金額、職業或對話紀錄，也不要堆砌感官畫面。

型式一、型式五上集、型式五下集仍須盤象先行：先依 payload 的五元組寫星、門、神、奇儀、方位、時辰與吉凶的白話，再把微型情境扣回盤象，最後給一個讀者能自行決定的低風險下一步。不得把一般心理測驗、塔羅牌義、牌陣、星座或其他占卜術語移植進來。型式五上下集必須同題、同圖騰、同五元組；下集第一行仍逐字保留 upper_answer 的主軸。

型式二、型式三、型式四同樣使用小說式片段，但型式三／四只可依 payload 已有 SSOT 術語與來源寫白話說明。型式四的【原文層】、【象義層】、【創作層】逐字受保護，不得產生、刪除或改寫。不得把古籍內容延伸成個人斷語、醫療建議、法律建議、財務建議或結果保證。

依序使用三個寫作 skill：先用 chinese-webnovel-studio 決定承接、情境與留白；再用 good-writing-tw 刪冗、調整節奏，不把句子磨成同一拍；最後用 direct-chinese-writing 改為直接、自然、臺灣讀者易懂的中文。所有型式都不用「你不是……只是……」這類假共感，不扮演心理師，不替讀者編原因；不寫命定論、療效或外部結果保證。不要堆「真正的問題是」「本質上」「防護機制」「靜默力量」「底層邏輯」「賦能」「生命路徑」「能量消耗」「共振」等 AI 腔。每句維持合理主語、動詞、對象與因果。

five_layer=true 時，保留原有五層格式與換行：
**選項 X：逐字沿用 upper_answer 的主軸結論**
【盤象：星｜門｜神｜奇儀】
‧ 表面現象：由盤象推導的具體狀態。
‧ 盤象真相：先寫盤象術語，再以「白話來說，」自然轉譯。
【時空與感官錨定】
‧ 只使用 payload 已給定的方向、時辰與吉凶；可用與主題相關的輕量場景，不得另加未授權時間、數字或事件。
【奇門行為改運】
‧ 提出一至兩項低風險、讀者可自行決定的行動；不承諾他人反應或外部結果。

型式一與型式五上集短解答以約 50 個中文字為準，可落在 20–60 字；型式五上集問題聚焦保留既有 Hook 的時間窗且 15 字內；貼士 50 字內。型式五下集每張完整解讀以 380–450 個非空白字元為生成目標（硬下限 300 字元）；輸出前逐張自行計算，未達 380 字元時，只能補入與該盤象、方位、時辰或低風險行動直接相關的解讀，不得用空話湊字。若有 upper_answer，下集第一行必須逐字沿用其主軸。型式二、三、四維持原有欄位數及正文與視覺卡同步。所有句子要複核成分、搭配、用詞、語序、前後一致與因果；不確定時保留原意，不自行補造結論。"""
    user = {
        "date": date,
        "form": kind,
        "header_context": header,
        "target_theme": theme or {},
        "slots": payload_slots,
        "task": "逐一重寫全部 slot。輸出 JSON，rewrites 必須恰好各含一次 id。" + (f" 上次輸出未通過，請只修正以下驗收問題，其他欄位仍需完整輸出：{feedback}" if retry else ""),
    }
    schema = {
        "type": "object",
        "properties": {"rewrites": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}}, "required": ["id", "text"], "additionalProperties": False}}},
        "required": ["rewrites"], "additionalProperties": False,
    }
    request = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
        "max_completion_tokens": 4096,
        "response_format": {"type": "json_schema", "json_schema": {"name": "slot_rewrites", "strict": True, "schema": schema}},
    }
    errors = []
    for attempt in range(3):
        response = requests.post(os.environ["OPENAI_API_BASE"].rstrip("/") + "/chat/completions", headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}", "Content-Type": "application/json"}, json=request, timeout=300)
        try:
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            rewrites = {item["id"]: item["text"].strip() for item in json.loads(content)["rewrites"]}
            return normalize_dynamic_option_heading(slots, rewrites)
        except (requests.RequestException, KeyError, TypeError, ValueError) as exc:
            errors.append(str(exc))
            time.sleep(4 * (attempt + 1))
    raise RuntimeError("模型重寫請求失敗：" + " | ".join(errors))


def five_layer_issues(date: str, text: str, label: str, combo: dict, lower: bool) -> list[str]:
    required = (f"**選項 {label}：", "【盤象：", "‧ 表面現象：", "‧ 盤象真相：", "【時空與感官錨定】", "【奇門行為改運】")
    issues = [f"{date} {label} 缺少五層模組：{value}" for value in required if value not in text]
    issues.extend(f"{date} {label} 缺少動態盤象值：{term}" for term in combo_terms(combo) if term not in text)
    minimum = 300 if date >= STYLE_MIGRATION_START else 220
    count = len(re.sub(r"\s", "", text)) if date >= STYLE_MIGRATION_START else cjk_count(text)
    if count < minimum:
        unit = "非空白字元" if date >= STYLE_MIGRATION_START else "中文字"
        issues.append(f"{date} {label} 文字長度不足 {minimum} {unit}。")
    if "白話來說" not in text and "簡單說" not in text:
        issues.append(f"{date} {label} 缺少術語白話轉譯。")
    if "你" not in text:
        issues.append(f"{date} {label} 未維持第二人稱。")
    if re.search(r"你(?:注定|必然|一定會|百分之百)", text):
        issues.append(f"{date} {label} 使用命定論。")
    anchors = set(re.findall(ANCHOR_PATTERN, text))
    allowed = {combo["direction"], f'{combo["hour"]}時'}
    if any(anchor not in allowed for anchor in anchors):
        issues.append(f"{date} {label} 使用了未獲授權的時空或體感錨定：{sorted(anchors - allowed)}。")
    if len(anchors) > 2:
        issues.append(f"{date} {label} 時空／體感錨定超過兩項。")
    if re.search(PRECISE_ANCHOR_PATTERN, text):
        issues.append(f"{date} {label} 使用精準風格錨定。")
    issues.extend(f"{date} {label} 軌道 A 問題：{issue}" for issue in track_a_issues(text, combo))
    issues.extend(f"{date} {label} 句法品質問題：{issue}" for issue in sentence_quality_issues(text))
    issues.extend(f"{date} {label} 語意邊界問題：{issue}" for issue in semantic_boundary_issues(text))
    return issues


def short_dynamic_issues(date: str, text: str, label: str, combo: dict) -> list[str]:
    issues = []
    if not 20 <= cjk_count(text) <= 60:
        issues.append(f"{date} {label} 短解答未落在 20–60 字（約 50 字）。")
    issues.extend(f"{date} {label} 句法品質問題：{issue}" for issue in sentence_quality_issues(text))
    issues.extend(f"{date} {label} 語意邊界問題：{issue}" for issue in semantic_boundary_issues(text))
    return issues


def validate_rewrites(slots: list[dict], rewrites: dict[str, str]) -> None:
    expected = {slot["id"] for slot in slots}
    if set(rewrites) != expected:
        raise ValueError(f"輸出欄位不符：應為 {expected}，實際為 {set(rewrites)}")
    for slot in slots:
        value = rewrites[slot["id"]].strip()
        if not value or value == slot["text"]:
            raise ValueError(f"未實質重寫欄位：{slot['id']}")
        if slot.get("minimum_cjk") and cjk_count(value) < slot["minimum_cjk"]:
            raise ValueError(f"欄位字數不足：{slot['id']}（{cjk_count(value)} 個中文字，內容：{value[:160]!r}）")
        if slot.get("minimum_chars") and len(re.sub(r"\s", "", value)) < slot["minimum_chars"]:
            raise ValueError(f"欄位字數不足：{slot['id']}（{len(re.sub(r'\s', '', value))} 個非空白字元，內容：{value[:160]!r}）")
        if slot.get("maximum_cjk") is not None and cjk_count(value) > slot["maximum_cjk"]:
            raise ValueError(f"欄位超過字數上限：{slot['id']}（{cjk_count(value)} 字，內容：{value[:160]!r}）")
        if slot.get("short_window") and not re.search(r"近|接下來|未來|本週|近期", value):
            raise ValueError(f"欄位缺少短時間窗：{slot['id']}")
        retired = next((token for token in RETIRED_DECLARATIONS if token in value), None)
        if retired:
            raise ValueError(f"欄位含已刪除聲明：{slot['id']}（命中：{retired!r}；內容：{value[:180]!r}）")
        quality_issues = sentence_quality_issues(value)
        if quality_issues:
            raise ValueError(f"欄位有病句風險：{slot['id']}（{'；'.join(quality_issues)}）")
        boundary_issues = semantic_boundary_issues(value)
        if boundary_issues:
            raise ValueError(f"欄位超出語意邊界：{slot['id']}（{'；'.join(boundary_issues)}）")
        if slot.get("five_layer"):
            issues = five_layer_issues("重寫輸出", value, slot["label"], slot["combo"], slot["id"].startswith("card_"))
            if issues:
                raise ValueError(" | ".join(issues) + f"；輸出開頭：{value[:180]!r}")
        elif slot.get("short_dynamic") and slot.get("combo"):
            issues = short_dynamic_issues("重寫輸出", value, slot["label"], slot["combo"])
            if issues:
                raise ValueError(" | ".join(issues) + f"；輸出開頭：{value[:180]!r}")


def apply_theme_metadata(block: str, date: str, kind: str) -> str:
    plan = THEME_PLANS.get(date)
    if not plan:
        return block
    changed = block
    old_hook = hook_slot(block)["text"]
    if kind != "型式二":
        changed = changed.replace(old_hook, plan["hook"])
        if "｜" in old_hook and "｜" in plan["hook"]:
            old_question, new_question = old_hook.rsplit("：", 1)[-1].split("｜", 1)[-1], plan["hook"].rsplit("：", 1)[-1].split("｜", 1)[-1]
            changed = changed.replace(old_question, new_question)
    totems = plan.get("totems", {})
    if kind in {"型式一", "型式五上集"}:
        for label, totem in totems.items():
            changed = re.sub(rf"(?m)^🔮 {label}\. [^\n]+$", f"🔮 {label}. {totem}", changed)
    if kind == "型式一" and totems:
        colors = {"A": "霧玫瑰金", "B": "月白銀", "C": "霧玫瑰金", "D": "月白銀", "E": "霧玫瑰金", "F": "月白銀"}
        for label, totem in totems.items():
            changed = re.sub(rf"(?m)^- {label}：.*$", f"- {label}：{colors[label]}{totem} + 暖米白{totem}", changed)
    if kind == "型式五上集" and plan.get("scene"):
        scene = plan["scene"]
        changed, body_count = re.subn(r"(?ms)(^心裡默念：).*?(\n\n憑第一眼直覺)", lambda match: match.group(1) + scene + match.group(2), changed, count=1)
        changed, visual_count = re.subn(r"(（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次\+ 心裡默念：)(?s:.*?)(\+ 憑第一眼直覺)", lambda match: match.group(1) + scene + match.group(2), changed, count=1)
        if body_count != 1 or visual_count != 1:
            raise ValueError(f"{date} 型式五上集問題聚焦無法同步")
    if kind == "型式五上集" and totems:
        visual = "／".join(f"{label}{totem}" for label, totem in totems.items())
        changed, count = re.subn(r"(（3）三選項圖卡（9–18 秒）：).*?(｜深海軍藍)", lambda match: match.group(1) + visual + match.group(2), changed, count=1)
        if count != 1:
            raise ValueError(f"{date} 型式五上集圖騰視覺卡無法同步")
    if kind == "型式五下集" and totems:
        for label, totem in totems.items():
            changed = re.sub(rf"({label} 選項完整解讀卡（)[^）]+(）)", rf"\1{totem}\2", changed)
    if kind == "型式三":
        ssot = plan.get("ssot")
        if not ssot:
            raise ValueError(f"{date} 型式三缺少 SSOT 題材來源")
        citation = f"已驗證補充資料：SSOT 定位：`{ssot['data_file']}`，`{ssot['source_locator']}`。"
        changed, count = re.subn(r"已驗證補充資料：[^\n｜]+", citation, changed)
        if count != 2:
            raise ValueError(f"{date} 型式三 SSOT 引文無法同步")
    return changed


def apply_slots(block: str, slots: list[dict], rewrites: dict[str, str]) -> str:
    changed = block
    tokens: dict[str, str] = {}
    for index, slot in enumerate(sorted(slots, key=lambda item: len(item["text"]), reverse=True)):
        if slot["text"] not in changed:
            raise ValueError(f"原欄位消失，無法套用：{slot['id']}")
        token = f"__LUNA_REWRITE_SLOT_{index}__"
        changed = changed.replace(slot["text"], token)
        tokens[token] = rewrites[slot["id"]]
    for token, value in tokens.items():
        changed = changed.replace(token, value)
    scene_slot = next((slot for slot in slots if slot.get("short_window")), None)
    if scene_slot:
        scene = rewrites[scene_slot["id"]]
        if cjk_count(scene) > 15:
            raise ValueError("型式五上集問題聚焦超過 15 字。")
        if not re.search(r"近|接下來|未來|本週|近期", scene):
            raise ValueError("型式五上集問題聚焦缺少短時間窗。")
        changed, count = re.subn(
            r"(（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次\+ 心裡默念：)(?s:.*?)(\+ 憑第一眼直覺)",
            lambda match: match.group(1) + scene + match.group(2), changed, count=1,
        )
        if count != 1:
            raise ValueError("型式五上集視覺問題聚焦卡無法同步")
    return changed


def current_contract_issues() -> list[str]:
    text = PLAYBOOK.read_text(encoding="utf-8")
    issues = []
    if sha(text) != PLAYBOOK_SHA256:
        issues.append("完整 Playbook 雜湊與本次鎖定基線不符。")
    start, guide = text.find(STANDARD_START), text.find(GUIDE_TITLE)
    if start < 0 or guide <= start:
        return issues + ["找不到固定模板或規則庫標題。"]
    if sha(text[start:guide]) != STANDARD_SHA256:
        issues.append("固定模板合約雜湊不符。")
    if sha(text[guide:]) != GUIDE_SHA256:
        issues.append("規則庫合約雜湊不符。")
    required_v42 = (
        "小說式描寫文風（v4.2｜唯一全局文風規範，奇門專用）",
        "型式一、二、三、四、五都使用**玄學小說式描寫**",
        "一至兩個可感知細節",
        "盤象先行，不可調換",
        "不得援引塔羅牌義、牌陣、星座宮位",
        "`chinese-webnovel-studio`",
        "`good-writing-tw`",
        "`direct-chinese-writing`",
    )
    missing = [marker for marker in required_v42 if marker not in text[guide:]]
    if missing:
        issues.append("v4.2 小說式描寫規範缺少：" + "、".join(missing))
    if not RULES_FILE.is_file() or sha(RULES_FILE.read_text(encoding="utf-8")) != DYNAMIC_RULES_SHA256:
        issues.append("動態盤象規則檔缺失或來源雜湊不符。")
    if not SERIAL_THEME_FILE.is_file() or sha(SERIAL_THEME_FILE.read_text(encoding="utf-8")) != SERIAL_THEME_SHA256:
        issues.append("v4.2 主題地圖缺失或來源雜湊不符。")
    return issues


def pinned_answer(block: str, label: str, labels: str) -> str:
    anchor = block.find("【置頂留言區解答｜")
    if anchor < 0:
        return ""
    end = block.find("————————————", anchor)
    region = block[anchor:end if end >= 0 else len(block)]
    match = re.search(rf"(?ms)^{label}：(.*?)(?=\n\n[{'|'.join(labels)}]：|\Z)", region)
    return match.group(1).strip() if match else ""


def lower_card(block: str, label: str) -> str:
    number = {"A": 3, "B": 4, "C": 5}[label]
    match = re.search(rf"(?ms)^（{number}）{label} 選項完整解讀卡（[^）]+）：(.*?)(?=｜暖米白底 #F5F5DC、深海軍藍 #0D0D2B（文字）、霧玫瑰金 #B4918F（邊框 \+ 圖騰線稿）。)", block)
    return match.group(1).strip() if match else ''


def block_issues(date: str, kind: str, block: str, assignments: dict[str, dict[str, dict]]) -> list[str]:
    issues = []
    if PENDING not in block:
        issues.append(f"{date} 缺少 48 小時待記錄欄位。")
    if any(token in block for token in RETIRED_DECLARATIONS):
        issues.append(f"{date} 留有已刪除免責或邊界澄清。")
    if any(token in block for token in RETIRED_TEXT):
        issues.append(f"{date} 留有已廢止模板文字。")
    if "`#" in block:
        issues.append(f"{date} 色碼仍使用已淘汰反引號格式。")
    tags = re.search(r"(?m)^Hashtags：(.+)$", block)
    if not tags or len(re.findall(r"#[\w\u3400-\u9fff]+", tags.group(1))) != 5 or "#Lunasastralcode" not in tags.group(1):
        issues.append(f"{date} Hashtags 結構錯誤。")
    cta = re.search(r"(?ms)^固定 CTA：\s*(.*?)(?=\n————————————|\n視覺分鏡描述|\n【待記錄】|\Z)", block)
    if not cta or cta.group(1).strip() != CTA[kind]:
        issues.append(f"{date} CTA 與固定模板不符。")
    visual_match = re.search(r"視覺分鏡描述（.*?）：\n(.*?)(?=\n【待記錄】)", block, re.S)
    if not visual_match:
        issues.append(f"{date} 缺少視覺分鏡區塊。")
    else:
        visual = visual_match.group(1)
        try:
            variable_slots = slots_for(block, kind)
            if kind in {"型式二", "型式三", "型式四"}:
                for slot in variable_slots:
                    required_lines = [line for line in slot["text"].splitlines() if line]
                    if any(line not in visual for line in required_lines):
                        issues.append(f"{date} 正文欄位 {slot['id']} 未同步至視覺卡。")
            elif kind == "型式五上集":
                for slot in variable_slots:
                    if slot["id"] in {"scene", "tip"} and slot["text"] not in visual:
                        issues.append(f"{date} 正文欄位 {slot['id']} 未同步至視覺卡。")
        except ValueError as exc:
            issues.append(f"{date} 欄位解析失敗：{exc}")
    try:
        for slot in slots_for(block, kind):
            value = slot["text"]
            if slot.get("maximum_cjk") is not None and cjk_count(value) > slot["maximum_cjk"]:
                issues.append(f"{date} {slot['id']} 超過 {slot['maximum_cjk']} 字。")
            issues.extend(f"{date} {slot['id']} 句法品質問題：{issue}" for issue in sentence_quality_issues(value))
            issues.extend(f"{date} {slot['id']} 語意邊界問題：{issue}" for issue in semantic_boundary_issues(value))
    except ValueError as exc:
        issues.append(f"{date} 新版欄位稽核失敗：{exc}")
    if kind == "型式一":
        if len(re.findall(r"(?m)^🔮 [A-F]\. ", block)) != 6:
            issues.append(f"{date} 缺少 A–F 圖騰。")
        scene = section(block, "正文：\n", "\n\nHashtags：").split("\n長按螢幕")[0]
        if cjk_count(scene) < 30:
            issues.append(f"{date} 型式一情節少於 30 字。")
        for label in "ABCDEF":
            issues.extend(short_dynamic_issues(date, pinned_answer(block, label, "ABCDEF"), label, assignments[date][label]))
    if kind == "型式五上集":
        if len(re.findall(r"(?m)^🔮 [A-C]\. ", block)) != 3:
            issues.append(f"{date} 缺少 A／B／C 圖騰。")
        body_scene = re.search(r"(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺", block)
        visual_scene = re.search(r"(?s)（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次\+ 心裡默念：(.*?)\+ 憑第一眼直覺", block)
        if not body_scene or not visual_scene or body_scene.group(1).strip() != visual_scene.group(1).strip():
            issues.append(f"{date} 正文與視覺問題聚焦情景不一致。")
        elif not re.search(r"近|接下來|未來|本週|近期", body_scene.group(1)):
            issues.append(f"{date} 缺少短時間窗。")
        for label in "ABC":
            issues.extend(short_dynamic_issues(date, pinned_answer(block, label, "ABC"), label, assignments[date][label]))
    if kind == "型式五下集":
        for label in "ABC":
            issues.extend(five_layer_issues(date, lower_card(block, label), label, assignments[date][label], True))
    if date >= THEME_START:
        plan = THEME_PLANS.get(date)
        if not plan:
            issues.append(f"{date} 缺少新題材計畫。")
        else:
            try:
                if kind != "型式二" and hook_slot(block)["text"] != plan["hook"]:
                    issues.append(f"{date} Hook 未套用題材計畫。")
            except ValueError as exc:
                issues.append(f"{date} Hook 驗證失敗：{exc}")
            for label, totem in plan.get("totems", {}).items():
                if kind in {"型式一", "型式五上集"} and f"🔮 {label}. {totem}" not in block:
                    issues.append(f"{date} {label} 圖騰未套用題材計畫。")
                if kind == "型式五下集" and f"{label} 選項完整解讀卡（{totem}）" not in block:
                    issues.append(f"{date} {label} 下集圖騰未承接題材計畫。")
            if kind == "型式三":
                ssot = plan.get("ssot", {})
                if not ssot or ssot["data_file"] not in block or ssot["source_locator"] not in block:
                    issues.append(f"{date} 型式三 SSOT 引文未套用題材計畫。")
            if kind == "型式四":
                ssot = plan.get("ssot", {})
                required = ("data_file", "system_line_id", "source_locator", "original_quote", "source_type", "verification_status")
                if not ssot or any(ssot[key] not in block for key in required):
                    issues.append(f"{date} 型式四奇門 SSOT 引文未套用題材計畫。")
    return issues


def cross_post_issues(posts: list[tuple[Path, str, str, str]], assignments: dict[str, dict[str, dict]]) -> list[str]:
    issues = []
    by_date = {date: (form(header), block) for _, date, header, block in posts}
    pairs = pair_map(posts)
    for lower, upper in pairs.items():
        _, upper_block = by_date[upper]
        _, lower_block = by_date[lower]
        upper_topic = re.search(r"Hook： 【大眾奇門占卜｜(.+?)】", upper_block)
        if not upper_topic or re.sub(r"\s+", "", upper_topic.group(1)) not in re.sub(r"\s+", "", lower_block):
            issues.append(f"{lower} 未承接 {upper} 的窄題。")
        for label in "ABC":
            upper_totem = re.search(rf"(?m)^🔮 {label}\. (.+)$", upper_block)
            lower_totem = re.search(rf"{label} 選項完整解讀卡（([^）]+)）", lower_block)
            if not upper_totem or not lower_totem or upper_totem.group(1).strip() != lower_totem.group(1).strip():
                issues.append(f"{lower} {label} 圖騰未承接 {upper}。")
            if assignments.get(lower, {}).get(label, {}).get("key") != assignments.get(upper, {}).get(label, {}).get("key"):
                issues.append(f"{lower} {label} 動態盤象未承接 {upper}。")
    return issues


def serial_arc_issues(posts: list[tuple[Path, str, str, str]]) -> list[str]:
    issues = []
    ordered = [date for _, date, _, _ in posts]
    if len(ordered) != 23:
        return [f"v4.2 主題地圖預期 23 篇，實際為 {len(ordered)}。"]
    for index, date in enumerate(ordered):
        plan = THEME_PLANS.get(date)
        if not plan:
            issues.append(f"{date} 缺少 v4.2 主題地圖。")
            continue
        if not plan.get("bridge_from") or not plan.get("bridge_to"):
            issues.append(f"{date} 缺少主題承接或後續鉤子。")
        if index and plan.get("bridge_from") == "無":
            issues.append(f"{date} 不可在主題中段斷開承接。")
    if pair_map(posts).get("2026-09-28") != "2026-09-26":
        issues.append("2026-09-28 未承接 2026-09-26 型式五上集。")
    return issues


def audit() -> int:
    issues = current_contract_issues()
    posts = list(unpublished_blocks())
    try:
        rules, registry = load_rules(), load_json(REGISTRY_FILE)
        assignments = dynamic_assignments(posts, registry, rules, persist=False)
        for stored_date, values in registry.get("assignments", {}).items():
            for stored_label, stored_combo in values.items():
                derived = derive_combo(rules, stored_combo["star"], stored_combo["door"], stored_combo["spirit"], stored_combo["qi"], stored_combo["hour"])
                fields = ("star", "door", "spirit", "qi", "hour", "door_palace", "direction", "score", "auspice", "key")
                if any(stored_combo.get(field) != derived[field] for field in fields):
                    issues.append(f"{stored_date} {stored_label} 五元組或顯示欄位未與 v2.0 規則一致。")
    except Exception as exc:
        print(json.dumps({"posts_checked": 23, "pass": False, "issues": issues + [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    if len(posts) != 23:
        issues.append(f"未發布腳本數量錯誤：{len(posts)}。")
    primary_keys = []
    for _, date, header, block in posts:
        kind = form(header)
        issues.extend(block_issues(date, kind, block, assignments))
        if kind in {"型式一", "型式五上集"}:
            primary_keys.extend(combo["key"] for combo in assignments[date].values())
    if len(primary_keys) != len(set(primary_keys)):
        issues.append("型式一／五上集近 30 篇動態盤象五元組重複。")
    if len(primary_keys) != 36:
        issues.append(f"動態盤象主選項數量錯誤：{len(primary_keys)}，預期 36。")
    issues.extend(cross_post_issues(posts, assignments))
    issues.extend(serial_arc_issues(posts))
    print(json.dumps({"posts_checked": len(posts), "pass": not issues, "issues": issues}, ensure_ascii=False, indent=2))
    return 0 if not issues else 1


def write_rule_map() -> None:
    rule_map = {
        "playbook_source": "lunas_astral_code_master_playbook.md",
        "playbook_sha256": PLAYBOOK_SHA256,
        "fixed_template_policy": "Only [ ] or ［］ variables may change. Fixed wording, punctuation, CTA, cards, media, seconds, colors, visual structure and order are immutable.",
        "dynamic_panxiang": {
            "source": "governance/dynamic_panxiang_rules.json",
            "source_sha256": DYNAMIC_RULES_SHA256,
            "input": ["九星", "八門", "八神", "奇儀", "時辰"],
            "sampling_rule": "九星、八門、八神、奇儀、時辰均為獨立隨機抽樣輸入；八神不由星或門推導。",
            "direction_rule": "門的固有宮位為主方位。",
            "auspice_rule": "以星、門、神、奇儀 category 權重加總映射大吉／中吉／平／中凶／大凶。",
            "dedup_rule": "星＋門＋神＋儀＋時辰五元組於近 30 篇內不得重複。",
        },
        "ssot_references": {
            "repository": "https://github.com/serenawct098-ai/ziwei_qimen",
            "verified_commit": "ac8f093f76a6dbcf459eca0075a33828aa47ef7e",
            "type3": {
                "2026-08-20": {"data_file": "data/ZWQS_Juan2_Consolidated.json", "line_id": "ZWQS_Juan2_AnSihua_L002"},
                "2026-09-03": TYPE3_SSOT["2026-09-03"],
                "2026-09-17": TYPE3_SSOT["2026-09-17"],
            },
            "type4": TYPE4_QIMEN_SSOT,
        },
        "serial_theme_map": {
            "source": "governance/script_theme_arc_v42.json",
            "source_sha256": SERIAL_THEME_SHA256,
            "posts": 23,
            "arc": ["看見", "清出空位", "把話說到門口", "在決定前停一拍", "留一盞燈給下一步"],
            "pairing": "每組型式五上／下集同題、同圖騰、同五元組；2026-09-28 承接 2026-09-26。"
        },
        "writing_tracks": {
            "version": "4.2",
            "scope": "只適用 Hook、正文、置頂解答、完整解讀與視覺卡中註冊的可變文案；固定模板、CTA、盤象、SSOT 與視覺規格不適用。",
            "style": "玄學小說式描寫：狀態／鏡頭→動作或停頓→命理白話或知識→可掌握的下一步→留白。",
            "skill_routing": ["chinese-webnovel-studio：承接、微型情境與留白", "good-writing-tw：刪冗與自然節奏", "direct-chinese-writing：直接、精準的臺灣中文"],
            "all_forms": ["型式一", "型式二", "型式三", "型式四", "型式五上集", "型式五下集"],
            "qimen_gate": "型式一／五盤象先行；情境必須緊扣已登錄五元組，不可移植塔羅、星座或其他占卜工具。",
            "ssot_gate": "型式三／四先依 SSOT；型式四固定保存原文層、象義層、創作層。",
            "narrative_gate": "每篇承接前一篇的問題、物件或狀態，並為下一篇留下可回答的問題；每篇僅一至兩個準確細節，不虛構未提供的個人事實。",
            "common_boundary": "禁止醫療、法律、財務專業建議、命定論、療效或外部結果保證；不得以假共感替讀者編造人生原因。",
            "sentence_categories": ["成分殘缺", "搭配不當", "用詞不當", "語序混亂", "前後矛盾", "邏輯混亂"],
            "review_order": ["受保護內容", "主題承接", "盤象或 SSOT 可追溯性", "小說式微型情境", "單一重點與語域", "句法與標點", "搭配用詞", "前後一致與因果"],
            "fixed_template_exclusion": "五大型式文案排版輸出標準規範的固定模板及其固定字句、CTA、卡數、順序、媒介、秒數、色碼與視覺結構不得修改。"
        },
        "forms": {
            "型式一": {"dynamic_options": "A–F", "option_format": "約 50 字（20–60 字）動態盤象短解答"},
            "型式五上集": {"dynamic_options": "A–C", "option_format": "問題聚焦 15 字內、貼士 50 字內、約 50 字（20–60 字）短解答"},
            "型式五下集": {"pairing": "承接上集同題、同圖騰、同五元組", "option_format": "五層完整解讀；2026-09-01 起每卡至少 300 字，先盤象白話降維再延伸奇門敘事"},
            "型式三": {"data_boundary": "涉及紫微命理資料必須先查 SSOT；不得套用動態盤象。"},
            "型式四": {"content_type": "奇門遁甲小知識", "data_boundary": "固定附原文層、象義層、創作層；概念必須可反向定位至已驗證 SSOT，不作個人論斷。"},
        },
        "acceptance": [
            "23 篇未發布腳本的每個註冊可變欄位在重寫前後均有不同 SHA-256。",
            "五大型式固定模板、CTA、Hashtags、日期、型式、媒介、卡數、色碼與已發布內容不變。",
            "型式一／五各選項盤象與視覺、正文、置頂解答、上下集完全一致。",
            "治理稽核、發布節奏、卡片視覺與 Git 格式檢查全部通過。",
            "型式一／五短解答以約 50 字（20–60 字）為準；型式五問題聚焦維持 15 字內；貼士維持 50 字內；2026-09-01 起型式五下集完整解讀每卡至少 300 字。",
            "所有可變文案均遵循 v4.2 玄學小說式描寫：承接前後主題、以一至兩個準確細節推進；型式一／五盤象先行且不可移植至其他占卜工具；型式三／四先依 SSOT；均通過網文敘事、好寫作、直接中文、句法與邏輯複核。",
            "型式四固定為奇門遁甲小知識；每篇含原文層、象義層與創作層，並可反向定位至已驗證 SSOT。",
            "五大型式文案排版輸出標準規範的區段 SHA-256 維持 3a91f1d6f23a820fd5e465bda645c80f625d208cefd864c6a79ba9a1d067aa48。",
        ],
    }
    RULE_MAP_FILE.write_text(json.dumps(rule_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def migrate_registry(args) -> int:
    load_rules()
    registry = load_json(REGISTRY_FILE)
    assignment_count = sum(len(values) for values in registry.get("assignments", {}).values())
    recent_post_count = len(registry.get("recent_posts", []))
    registry["schema_version"] = "2.0"
    registry["schema_source_sha256"] = DYNAMIC_RULES_SHA256
    registry["decision_log"] = {
        "sampling_rule": "九星、八門、八神、奇儀、時辰均為獨立隨機抽樣輸入",
        "direction_rule": "門的固有宮位為卡面主方位",
        "auspice_rule": "以獨立抽樣的星、門、神、奇儀 category 權重加總映射五級吉凶",
        "dedup_rule": "星＋門＋神＋儀＋時辰五元組於近 30 篇內不得重複",
    }
    registry["historical_assignment_policy"] = "既有五元組保持原值與原有衍生欄位；只更新 schema 治理中繼資料，不重新抽樣或覆寫未發布腳本內容。"
    if not args.dry_run:
        REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"dry_run": args.dry_run, "assignments_preserved": assignment_count, "recent_posts_preserved": recent_post_count}, ensure_ascii=False))
    return 0


def sync(args) -> int:
    if args.dry_run:
        print(json.dumps({"playbook_contract": {"playbook": PLAYBOOK_SHA256, "standard": STANDARD_SHA256, "guide": GUIDE_SHA256}, "writing_tracks": "v4.1 奇門專用雙軌：盤象先行／玄學小說敘事（可變文案專用）", "dynamic_rules_sha256": DYNAMIC_RULES_SHA256, "posts": len(list(unpublished_blocks()))}, ensure_ascii=False))
        return 0
    write_rule_map()
    print(json.dumps({"synced": True, "changed_files": [str(RULE_MAP_FILE.relative_to(ROOT))], "fixed_template_mutation": False}, ensure_ascii=False))
    return 0


def rewrite(args) -> int:
    if args.dry_run:
        posts = list(unpublished_blocks())
        summary = []
        for _, date, header, block in posts:
            summary.append({"date": date, "form": form(header), "slots": [slot["id"] for slot in slots_for(normalize_block(block), form(header))]})
        args.audit.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"posts": len(summary), "dry_run": True, "audit": str(args.audit)}, ensure_ascii=False))
        return 0
    write_rule_map()
    posts = list(unpublished_blocks())
    if len(posts) != 23:
        raise ValueError(f"Expected 23 unpublished posts, got {len(posts)}")
    rules, registry = load_rules(), load_json(REGISTRY_FILE)
    assignments = dynamic_assignments(posts, registry, rules, persist=False)
    blocks_by_date = {date: block for _, date, _, block in posts}
    lower_to_upper = pair_map(posts)
    replacements: dict[Path, list[tuple[str, str]]] = {path: [] for path in FILES}
    audit_rows = []
    for path, date, header, original_block in posts:
        kind = form(header)
        print(json.dumps({"stage": "rewrite", "date": date, "form": kind}, ensure_ascii=False), flush=True)
        block = repair_three_field_boundaries(original_block, kind)
        if date < args.from_date:
            continue
        slots = themed_slots(block, kind, date)
        add_dynamic_requirements(slots, date, kind, assignments)
        if kind == "型式五下集":
            upper_block = blocks_by_date[lower_to_upper[date]]
            for slot in slots:
                label = slot["id"].rsplit("_", 1)[-1]
                slot["upper_answer"] = pinned_answer(upper_block, label, "ABC")
        error = None
        feedback = ""
        for attempt in range(3):
            print(json.dumps({"stage": "request", "date": date, "attempt": attempt + 1, "slot_count": len(slots)}, ensure_ascii=False), flush=True)
            rewrites = request_rewrite(date, kind, header, slots, THEME_PLANS.get(date), retry=attempt > 0, feedback=feedback)
            try:
                validate_rewrites(slots, rewrites)
                error = None
                break
            except ValueError as exc:
                error = exc
                feedback = str(exc)
        if error:
            raise error
        revised = apply_theme_metadata(apply_slots(block, slots, rewrites), date, kind)
        blocks_by_date[date] = revised
        replacements[path].append((original_block, revised))
        audit_rows.append({
            "date": date, "form": kind, "theme": THEME_PLANS.get(date), "dynamic_panxiang": {label: assignments[date][label] for label in assignments.get(date, {})},
            "changed_slots": [slot["id"] for slot in slots],
            "slot_sha256": [{"id": slot["id"], "before": sha(slot["text"]), "after": sha(rewrites[slot["id"]])} for slot in slots],
            "before_sha256": sha(original_block), "after_sha256": sha(revised),
        })
    for path, items in replacements.items():
        text = path.read_text(encoding="utf-8")
        for old, new in items:
            if text.count(old) != 1:
                raise ValueError(f"Ambiguous replacement in {path.name}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
    prior = load_json(args.audit) if args.audit.is_file() else {}
    preserved = {item["date"]: item for item in prior.get("posts", []) if item.get("date") < args.from_date}
    preserved.update({item["date"]: item for item in audit_rows})
    args.audit.write_text(json.dumps({"playbook_sha256": PLAYBOOK_SHA256, "dynamic_rules_sha256": DYNAMIC_RULES_SHA256, "theme_rewrite_from": args.from_date, "posts": [preserved[date] for date in sorted(preserved)]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"posts": len(audit_rows), "model": MODEL, "audit": str(args.audit)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Luna unified Playbook governance")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="Synchronize governance map and latest fixed typography.")
    sync_parser.add_argument("--dry-run", action="store_true")
    migrate_parser = sub.add_parser("migrate-registry", help="Migrate stored five-tuples to the independent sampling schema.")
    migrate_parser.add_argument("--dry-run", action="store_true")
    rewrite_parser = sub.add_parser("rewrite", help="Rewrite registered variable prose for every unpublished post.")
    rewrite_parser.add_argument("--dry-run", action="store_true")
    rewrite_parser.add_argument("--audit", type=Path, default=AUDIT_FILE)
    rewrite_parser.add_argument("--from-date", default=THEME_START)
    sub.add_parser("audit", help="Audit Playbook contract, dynamic panxiang and 22 scripts.")
    args = parser.parse_args()
    if args.command == "sync":
        return sync(args)
    if args.command == "migrate-registry":
        return migrate_registry(args)
    if args.command == "rewrite":
        return rewrite(args)
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
