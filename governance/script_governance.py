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
MODEL = "claude-sonnet-4-6"
PUBLISHED = {"2026-08-17", "2026-08-18"}
PENDING = "【待記錄】發布後48小時：reach / 非追蹤者觸及 / profile visits / website clicks / DM / saves / shares"
STANDARD_START = "## 【五大型式文案排版輸出標準規範】"
GUIDE_TITLE = "## IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫"
STANDARD_SHA256 = "a5abdb4fa1e799478ee6ec3d1985592d8ce1868723d77ba75a4439587b9f0756"
GUIDE_SHA256 = "a866819e9dbba396ab19ca74ab70e22347055a220f0688bf2abe2c468a976844"
PLAYBOOK_SHA256 = "3d7dffdd926acc037907fd46ce0fffd58a0f964808985e49e496c48afb20d616"
DYNAMIC_RULES_SHA256 = "debc63551ca63fdd527eab0e04ed1562f0c2f9581d0704709d5b99470d227897"
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
MICRO_SCENES = {
    "月台與訊息鏡頭": r"捷運(?:月台|車廂)[^\n]{0,120}(?:手機|對話框|訊息)",
    "咖啡放涼鏡頭": r"咖啡[^\n]{0,80}(?:涼掉|放涼)",
    "訊息反覆操作": r"(?:對話框|訊息)[^\n]{0,100}(?:打開|刪掉|改字|滑開)",
    "廚房動作鏡頭": r"(?:外套|菜|貓|流理台|鍋)[^\n]{0,120}(?:掛上|提在手裡|蹭過|冒小泡)",
}
ANCHOR_PATTERN = r"西北|正北|正東|正西|正南|東北|東南|西南|中央|子時|丑時|寅時|卯時|辰時|巳時|午時|未時|申時|酉時|戌時|亥時|早上|下午|晚上|深夜|肩頸|睡眠"
PRECISE_ANCHOR_PATTERN = r"(?:早上|下午|晚上)\s*\d{1,2}\s*(?:[–—\-至到])\s*\d{1,2}\s*(?:點|時)|\d+\s*(?:步|分鐘|天)"
SOFTENERS = ("可能", "似乎", "正處於", "未必", "隱約", "看似", "有些", "進退兩難", "心有不甘", "若有若無")
# Clockwise geographic ring, derived directly from each palace's direction.
CLOCKWISE_PALACE_RING = (1, 8, 3, 4, 9, 2, 7, 6)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def cjk_count(text: str) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", text))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
        slots.append({"id": f"answer_{label}", "text": match.group(1).strip(), "minimum_cjk": 35, "maximum_cjk": 50, "short_dynamic": True})
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
        slots.append({"id": f"card_{label}", "text": match.group(1).strip(), "minimum_cjk": 300})
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
        if len(lines) != 3:
            raise ValueError(f"Type 2 needs three variable body lines, got {len(lines)}")
        return [{"id": name, "text": value, "minimum_cjk": 0} for name, value in zip(("scene", "reflection", "action"), lines)]
    if kind == "型式三":
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) < 3:
            raise ValueError("Type 3 body incomplete")
        return [{"id": "explain", "text": lines[1], "minimum_cjk": 50}]
    if kind == "型式四":
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) != 3:
            raise ValueError(f"Type 4 needs three body lines, got {len(lines)}")
        return [{"id": name, "text": value, "minimum_cjk": 0} for name, value in zip(("scene", "check", "action"), lines)]
    if kind == "型式五上集":
        scene = re.search(r"(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺", body)
        tip = re.search(r"(?ms)^🔮 C\. .*?\n\n(.*?)\n下一期帶你解鎖更多新的占卜提示～", body)
        if not scene or not tip:
            raise ValueError("Type 5 upper scene or tip missing")
        slots = [
            {"id": "scene", "text": scene.group(1).strip(), "minimum_cjk": 1, "maximum_cjk": 15, "short_window": True},
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


def spirit_placement(rules: dict, value_star: str, dun: str = "陰遁") -> dict[int, str]:
    star = rules["nine_stars_九星"][value_star]
    start_palace = 2 if star["palace"] == 5 else star["palace"]  # A1
    start_index = CLOCKWISE_PALACE_RING.index(start_palace)
    step = 1 if dun == "陽遁" else -1
    placement = {}
    for offset, spirit in enumerate(rules["eight_spirits_八神"]["sequence_order"]):
        palace = CLOCKWISE_PALACE_RING[(start_index + step * offset) % len(CLOCKWISE_PALACE_RING)]
        placement[palace] = spirit
    return placement


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


def derive_combo(rules: dict, star: str, door: str, qi: str, hour: str) -> dict:
    """Recompute every downstream field from the immutable five-tuple under the current rule schema."""
    door_data = rules["eight_doors_八門"][door]
    placement = spirit_placement(rules, star, "陰遁")
    spirit = placement[door_data["palace"]]  # B1
    score, label = auspice(rules, star, door, spirit, qi)
    combo = {
        "star": star, "door": door, "spirit": spirit, "qi": qi, "hour": hour,
        "dun": "陰遁", "value_star": star,
        "value_star_palace": 2 if rules["nine_stars_九星"][star]["palace"] == 5 else rules["nine_stars_九星"][star]["palace"],
        "door_palace": door_data["palace_name"], "direction": door_data["direction"],
        "spirit_placement": {str(key): value for key, value in placement.items()},
        "score": score, "auspice": label,
    }
    combo["key"] = combo_key(combo)
    return combo


def generate_combo(rules: dict, occupied: set[str], used_stars: set[str], used_doors: set[str]) -> dict:
    rng = random.SystemRandom()
    stars = [item for item in rules["nine_stars_九星"] if item not in used_stars]
    doors = [item for item in rules["eight_doors_八門"] if item not in used_doors]
    qi_values = list(rules["three_qi_six_yi_三奇六儀"]["三奇"]) + list(rules["three_qi_six_yi_三奇六儀"]["六儀"])
    hours = rules["time_derivation_rule_時間推導規則"]["shi_chen_十二時辰"]
    for _ in range(500):
        star, door, qi, hour = rng.choice(stars), rng.choice(doors), rng.choice(qi_values), rng.choice(hours)
        combo = derive_combo(rules, star, door, qi, hour)
        if combo["key"] not in occupied:
            return combo
    raise RuntimeError("500 次抽樣後仍無可用盤象組合。")


def pair_map(posts: list[tuple[Path, str, str, str]]) -> dict[str, str]:
    uppers = sorted(date for _, date, header, _ in posts if form(header) == "型式五上集")
    lowers = sorted(date for _, date, header, _ in posts if form(header) == "型式五下集")
    return {lower: upper for upper, lower in zip(uppers, lowers)}


def dynamic_assignments(posts: list[tuple[Path, str, str, str]], registry: dict, rules: dict, persist: bool) -> dict[str, dict[str, dict]]:
    assignments = deepcopy(registry.get("assignments", {}))
    # v1.1 correction safety: preserve the five-tuple, but always recompute all derived fields.
    for date, values in assignments.items():
        for label, combo in list(values.items()):
            values[label] = derive_combo(rules, combo["star"], combo["door"], combo["qi"], combo["hour"])
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
        registry["decision_log"] = {
            "value_star_rule": "九星抽樣值直接視為值符星",
            "tianqin_start_rule": "天禽星抽中為值符星時，以寄坤二宮作八神起點",
            "spirit_selection_rule": "取門的固有宮位所落八神為卡面神值與吉凶計分神",
            "dun_direction_rule": "本輪 22 篇日期使用陰遁逆時針",
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
        slot["must_include"] = combo_terms(combo)
        slot["five_layer"] = kind == "型式五下集"
        slot["short_dynamic"] = kind in {"型式一", "型式五上集"}


def normalize_dynamic_option_heading(slots: list[dict], rewrites: dict[str, str]) -> dict[str, str]:
    """Canonicalize only the required variable first-line emphasis for dynamic options."""
    for slot in slots:
        if not slot.get("five_layer"):
            continue
        label = slot["label"]
        lines = rewrites[slot["id"]].splitlines()
        if not lines:
            continue
        first = lines[0].strip()
        match = re.match(rf"^\*\*選項 {label}(?:\*\*)?[：:](.*?)(?:\*\*)?$|^選項 {label}[：:](.*)$", first)
        if match:
            conclusion = (match.group(1) if match.group(1) is not None else match.group(2)).strip()
            lines[0] = f"**選項 {label}：{conclusion}**"
            rewrites[slot["id"]] = "\n".join(lines).strip()
    return rewrites


def request_rewrite(date: str, kind: str, header: str, slots: list[dict], retry: bool = False) -> dict[str, str]:
    payload_slots = []
    for slot in slots:
        item = {key: slot[key] for key in ("id", "text", "minimum_cjk")}
        if slot.get("maximum_cjk") is not None:
            item["maximum_cjk"] = slot["maximum_cjk"]
        if slot.get("must_include"):
            item["must_include"] = slot["must_include"]
            item["combo"] = slot["combo"]
            item["five_layer"] = bool(slot.get("five_layer"))
            item["short_dynamic"] = bool(slot.get("short_dynamic"))
        payload_slots.append(item)
    system = """你是繁體中文（台灣）IG 文案主筆。只能重寫給定的可變欄位，不得輸出或改動 Hook、Hashtags、CTA、卡片標題、視覺模板、圖騰、日期、型式、色碼與任何固定文字。

用冷靜、權威、透徹的「玄學破局」語氣，全文使用第二人稱「你」。先說核心狀態或可行結論，再寫表面狀態與內在拉扯，最後給低門檻、可觀察且不保證結果的行動。避免心理治癒腔、客服腔、命定論、假深刻、空泛雞湯、術語堆砌、無源歸因、微觀動作與道具鏡頭。不得寫免責、邊界澄清、個人起局說明、資料不足或公開資料等句子。

只要 slot 有 must_include，就必須逐字包含每一項術語。這些是動態盤象已推導結果，不得新增任何其他星、門、神、奇儀、方位、時辰、吉凶、公式或個人結論。只在 slot 標記 five_layer 時，才使用下列五層格式，並以換行分隔：
**選項 X：一句明確但非命定的主軸結論**
【盤象：星｜門｜神｜奇儀】
‧ 表面現象：以概括語句描繪外在或心理狀態。
‧ 盤象真相：內在拉扯；必須立刻說「白話來說」或同義白話轉譯。
【時空與感官錨定】
‧ 只使用已給定的方向、時辰與吉凶；只寫一般錨定，不得寫數字步數、精確時段或身體體感。
【奇門行為改運】
‧ 一至兩項低門檻行動；不得承諾改變他人、化解、招財、吸納吉氣或結果。

型式一與型式五上集置頂解答需約 50 個中文字，範圍 35–50。型式五上集問題聚焦需含「近期」、「本週」、「接下來」或「未來」之一，且 15 字內；貼士 50 字內。型式五下集完整解讀至少 300 個中文字，且每個模組最多兩句。型式二、三、四維持原有欄位數，不得新增模組標題或命理術語。每個可變欄位維持第二人稱「你」，採概括、模糊與投射留白寫法，至少包含「可能、似乎、正處於、未必、隱約、看似、有些、進退兩難、心有不甘、若有若無」之一；不得使用精準時段、步數、分鐘、天數或體感狀態。所有 slot 均需實質重組句法、節奏與狀態描寫，不能原文照抄或只換同義詞。"""
    user = {
        "date": date,
        "form": kind,
        "header_context": header,
        "slots": payload_slots,
        "task": "逐一重寫全部 slot。輸出 JSON，rewrites 必須恰好各含一次 id。" + (" 上次輸出未通過，請特別確認每個動態術語與五層格式都存在。" if retry else ""),
    }
    schema = {
        "type": "object",
        "properties": {"rewrites": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}}, "required": ["id", "text"], "additionalProperties": False}}},
        "required": ["rewrites"], "additionalProperties": False,
    }
    request = {
        "model": MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}],
        "max_tokens": 16000,
        "response_format": {"type": "json_schema", "json_schema": {"name": "slot_rewrites", "strict": True, "schema": schema}},
        "thinking": {"type": "enabled", "budget_tokens": 2048},
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
    if cjk_count(text) < 300:
        issues.append(f"{date} {label} 文字長度不足。")
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
    if not any(word in text for word in SOFTENERS):
        issues.append(f"{date} {label} 缺少模糊化投射留白語氣。")
    return issues


def short_dynamic_issues(date: str, text: str, label: str, combo: dict) -> list[str]:
    issues = []
    issues.extend(f"{date} {label} 缺少動態盤象值：{term}" for term in combo_terms(combo) if term not in text)
    if not 35 <= cjk_count(text) <= 50:
        issues.append(f"{date} {label} 短解答未落在 35–50 字。")
    if "你" not in text:
        issues.append(f"{date} {label} 未維持第二人稱。")
    if re.search(PRECISE_ANCHOR_PATTERN, text):
        issues.append(f"{date} {label} 使用精準風格錨定。")
    if not any(word in text for word in SOFTENERS):
        issues.append(f"{date} {label} 缺少模糊化投射留白語氣。")
    return issues


def validate_rewrites(slots: list[dict], rewrites: dict[str, str]) -> None:
    expected = {slot["id"] for slot in slots}
    if set(rewrites) != expected:
        raise ValueError(f"輸出欄位不符：應為 {expected}，實際為 {set(rewrites)}")
    for slot in slots:
        value = rewrites[slot["id"]].strip()
        if not value or value == slot["text"]:
            raise ValueError(f"未實質重寫欄位：{slot['id']}")
        if slot["minimum_cjk"] and cjk_count(value) < slot["minimum_cjk"]:
            raise ValueError(f"欄位字數不足：{slot['id']}（{cjk_count(value)} 字，內容：{value[:160]!r}）")
        if slot.get("maximum_cjk") is not None and cjk_count(value) > slot["maximum_cjk"]:
            raise ValueError(f"欄位超過字數上限：{slot['id']}（{cjk_count(value)} 字，內容：{value[:160]!r}）")
        if slot.get("short_window") and not re.search(r"近|接下來|未來|本週|近期", value):
            raise ValueError(f"欄位缺少短時間窗：{slot['id']}")
        if re.search(PRECISE_ANCHOR_PATTERN, value):
            raise ValueError(f"欄位含精準風格錨定：{slot['id']}")
        retired = next((token for token in RETIRED_DECLARATIONS if token in value), None)
        if retired:
            raise ValueError(f"欄位含已刪除聲明：{slot['id']}（命中：{retired!r}；內容：{value[:180]!r}）")
        if any(re.search(pattern, value) for pattern in MICRO_SCENES.values()):
            raise ValueError(f"欄位含過度微觀描繪：{slot['id']}")
        if slot.get("five_layer"):
            issues = five_layer_issues("重寫輸出", value, slot["label"], slot["combo"], slot["id"].startswith("card_"))
            if issues:
                raise ValueError(" | ".join(issues) + f"；輸出開頭：{value[:180]!r}")
        elif slot.get("short_dynamic") and slot.get("combo"):
            issues = short_dynamic_issues("重寫輸出", value, slot["label"], slot["combo"])
            if issues:
                raise ValueError(" | ".join(issues) + f"；輸出開頭：{value[:180]!r}")


def apply_slots(block: str, slots: list[dict], rewrites: dict[str, str]) -> str:
    changed = block
    for slot in sorted(slots, key=lambda item: len(item["text"]), reverse=True):
        if slot["text"] not in changed:
            raise ValueError(f"原欄位消失，無法套用：{slot['id']}")
        changed = changed.replace(slot["text"], rewrites[slot["id"]])
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
    if not RULES_FILE.is_file() or sha(RULES_FILE.read_text(encoding="utf-8")) != DYNAMIC_RULES_SHA256:
        issues.append("動態盤象規則檔缺失或來源雜湊不符。")
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
    for name, pattern in MICRO_SCENES.items():
        if re.search(pattern, block):
            issues.append(f"{date} 含過度微觀描繪：{name}。")
    visual_match = re.search(r"視覺分鏡描述（.*?）：\n(.*?)(?=\n【待記錄】)", block, re.S)
    if not visual_match:
        issues.append(f"{date} 缺少視覺分鏡區塊。")
    else:
        visual = visual_match.group(1)
        try:
            variable_slots = slots_for(block, kind)
            if kind in {"型式二", "型式三", "型式四"}:
                for slot in variable_slots:
                    if slot["text"] not in visual:
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
            if re.search(PRECISE_ANCHOR_PATTERN, value):
                issues.append(f"{date} {slot['id']} 使用精準風格錨定。")
    except ValueError as exc:
        issues.append(f"{date} 新版欄位稽核失敗：{exc}")
    body_for_voice = section(block, "正文：\n", "\n\nHashtags：")
    if kind != "型式五下集":
        if "你" not in body_for_voice:
            issues.append(f"{date} 正文未維持第二人稱對話感。")
        if not any(word in body_for_voice for word in SOFTENERS):
            issues.append(f"{date} 正文缺少模糊化投射留白語氣。")
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


def audit() -> int:
    issues = current_contract_issues()
    posts = list(unpublished_blocks())
    try:
        rules, registry = load_rules(), load_json(REGISTRY_FILE)
        assignments = dynamic_assignments(posts, registry, rules, persist=False)
        for stored_date, values in registry.get("assignments", {}).items():
            for stored_label, stored_combo in values.items():
                derived = derive_combo(rules, stored_combo["star"], stored_combo["door"], stored_combo["qi"], stored_combo["hour"])
                if stored_combo != derived:
                    issues.append(f"{stored_date} {stored_label} 去重紀錄衍生欄位未依 v1.1 五元組重算。")
    except Exception as exc:
        print(json.dumps({"posts_checked": 22, "pass": False, "issues": issues + [str(exc)]}, ensure_ascii=False, indent=2))
        return 1
    if len(posts) != 22:
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
            "input": ["九星", "八門", "奇儀", "時辰"],
            "value_star_rule": "九星抽樣值直接視為值符星；天禽星以寄坤二宮作八神起點。",
            "spirit_rule": "陰遁逆時針排列八神，取門之固有宮位所落八神為卡面神值與吉凶計分神。",
            "direction_rule": "門的固有宮位為主方位。",
            "auspice_rule": "以星、門、神、奇儀 category 權重加總映射大吉／中吉／平／中凶／大凶。",
            "dedup_rule": "星＋門＋神＋儀＋時辰五元組於近 30 篇內不得重複。",
        },
        "ssot_references": {
            "repository": "https://github.com/serenawct098-ai/ziwei_qimen",
            "verified_commit": "ac8f093f76a6dbcf459eca0075a33828aa47ef7e",
            "type3": {
                "2026-08-20": {"data_file": "data/ZWQS_Juan2_Consolidated.json", "line_id": "ZWQS_Juan2_AnSihua_L002"},
                "2026-09-03": {"data_file": "engines/diagnosis_router_module_v1.json", "intent": "relationship", "palaces": ["夫妻宮", "交友宮"]},
                "2026-09-17": {"data_file": "engines/diagnosis_router_module_v1.json", "intent": "career", "palaces": ["官祿宮", "財帛宮"]},
            },
        },
        "forms": {
            "型式一": {"dynamic_options": "A–F", "option_format": "約 50 字動態盤象短解答（35–50 字）"},
            "型式五上集": {"dynamic_options": "A–C", "option_format": "問題聚焦 15 字內、貼士 50 字內、約 50 字短解答（35–50 字）"},
            "型式五下集": {"pairing": "承接上集同題、同圖騰、同五元組", "option_format": "五層完整解讀，每卡至少 300 字；使用感官錨定與概括描繪"},
            "型式三四": {"data_boundary": "涉及命理資料必須先查 SSOT；不得套用動態盤象。"},
        },
        "acceptance": [
            "22 篇未發布腳本的每個註冊可變欄位在重寫前後均有不同 SHA-256。",
            "五大型式固定模板、CTA、Hashtags、日期、型式、媒介、卡數、色碼與已發布內容不變。",
            "型式一／五各選項盤象與視覺、正文、置頂解答、上下集完全一致。",
            "治理稽核、發布節奏、卡片視覺與 Git 格式檢查全部通過。",
            "保留第二人稱；型式一／五短解答 35–50 字、型式五問題聚焦 15 字內、貼士 50 字內，且可變解讀使用概括與投射留白。",
        ],
    }
    RULE_MAP_FILE.write_text(json.dumps(rule_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sync(args) -> int:
    if args.dry_run:
        print(json.dumps({"playbook_contract": {"playbook": PLAYBOOK_SHA256, "standard": STANDARD_SHA256, "guide": GUIDE_SHA256}, "dynamic_rules_sha256": DYNAMIC_RULES_SHA256, "posts": len(list(unpublished_blocks()))}, ensure_ascii=False))
        return 0
    write_rule_map()
    result = synchronize_fixed_typography()
    print(json.dumps({"synced": True, **result}, ensure_ascii=False))
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
    synchronize_fixed_typography()
    posts = list(unpublished_blocks())
    if len(posts) != 22:
        raise ValueError(f"Expected 22 unpublished posts, got {len(posts)}")
    rules, registry = load_rules(), load_json(REGISTRY_FILE)
    assignments = dynamic_assignments(posts, registry, rules, persist=True)
    replacements: dict[Path, list[tuple[str, str]]] = {path: [] for path in FILES}
    audit_rows = []
    for path, date, header, block in posts:
        kind = form(header)
        slots = slots_for(block, kind)
        add_dynamic_requirements(slots, date, kind, assignments)
        error = None
        for retry in (False, True, True):
            rewrites = request_rewrite(date, kind, header, slots, retry)
            try:
                validate_rewrites(slots, rewrites)
                error = None
                break
            except ValueError as exc:
                error = exc
        if error:
            raise error
        revised = apply_slots(block, slots, rewrites)
        replacements[path].append((block, revised))
        audit_rows.append({
            "date": date, "form": kind, "dynamic_panxiang": {label: assignments[date][label] for label in assignments.get(date, {})},
            "changed_slots": [slot["id"] for slot in slots],
            "slot_sha256": [{"id": slot["id"], "before": sha(slot["text"]), "after": sha(rewrites[slot["id"]])} for slot in slots],
            "before_sha256": sha(block), "after_sha256": sha(revised),
        })
    for path, items in replacements.items():
        text = path.read_text(encoding="utf-8")
        for old, new in items:
            if text.count(old) != 1:
                raise ValueError(f"Ambiguous replacement in {path.name}")
            text = text.replace(old, new, 1)
        path.write_text(text, encoding="utf-8")
    args.audit.write_text(json.dumps({"playbook_sha256": PLAYBOOK_SHA256, "dynamic_rules_sha256": DYNAMIC_RULES_SHA256, "posts": audit_rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"posts": len(audit_rows), "model": MODEL, "audit": str(args.audit)}, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Luna unified Playbook governance")
    sub = parser.add_subparsers(dest="command", required=True)
    sync_parser = sub.add_parser("sync", help="Synchronize governance map and latest fixed typography.")
    sync_parser.add_argument("--dry-run", action="store_true")
    rewrite_parser = sub.add_parser("rewrite", help="Rewrite registered variable prose for every unpublished post.")
    rewrite_parser.add_argument("--dry-run", action="store_true")
    rewrite_parser.add_argument("--audit", type=Path, default=AUDIT_FILE)
    sub.add_parser("audit", help="Audit Playbook contract, dynamic panxiang and 22 scripts.")
    args = parser.parse_args()
    if args.command == "sync":
        return sync(args)
    if args.command == "rewrite":
        return rewrite(args)
    return audit()


if __name__ == "__main__":
    raise SystemExit(main())
