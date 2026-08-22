#!/usr/bin/env python3
"""Validate global application of the user-authored rule library across all five forms."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]

MICRO_SCENE_PATTERNS = {
    '月台與訊息鏡頭': r'捷運(?:月台|車廂)[^\n]{0,120}(?:手機|對話框|訊息)',
    '咖啡放涼鏡頭': r'咖啡[^\n]{0,80}(?:涼掉|放涼)',
    '訊息反覆操作': r'(?:對話框|訊息)[^\n]{0,100}(?:打開|刪掉|改字|滑開)',
    '廚房動作鏡頭': r'(?:外套|菜|貓|流理台|鍋)[^\n]{0,120}(?:掛上|提在手裡|蹭過|冒小泡)',
    '通勤工作鏡頭': r'(?:便當|長椅|通訊錄)[^\n]{0,120}(?:捧著|坐定|打開)',
    '手持物件發呆': r'(?:手拿|拿著).{0,8}(?:咖啡|杯).{0,12}(?:發呆|看著)',
}
ANCHORS = r'西北|正北|正東|正西|正南|東北|早上|下午|晚上|深夜|肩頸|睡眠|辰時|巳時|午時|未時|申時|酉時'


def blocks(text: str):
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        if match.group(1) >= '2026-08-20':
            yield match.group(1), text[match.start():end]


def card_texts(block: str):
    for match in re.finditer(r'(?ms)^（[345]）[ABC] 選項完整解讀卡.*?：(.*?)(?=｜暖米白底)', block):
        yield match.group(1)


issues: list[tuple[str, str]] = []
posts = 0
for path in FILES:
    for date, block in blocks(path.read_text(encoding='utf-8')):
        posts += 1
        for name, pattern in MICRO_SCENE_PATTERNS.items():
            if re.search(pattern, block):
                issues.append((date, f'含過度微觀描繪：{name}'))
        for card in card_texts(block):
            if len(set(re.findall(ANCHORS, card))) > 2:
                issues.append((date, '單張完整解讀的時空／體感錨定超過兩項'))
        header = block.split('\n', 1)[0]
        if not any(kind in header for kind in ('型式一', '型式二', '型式三', '型式四', '型式五上集', '型式五下集')):
            issues.append((date, '缺少型式分類'))

print({'posts_checked': posts, 'issues': issues, 'pass': not issues})
raise SystemExit(1 if issues else 0)
