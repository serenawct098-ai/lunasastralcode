#!/usr/bin/env python3
"""Read-only validator for the user-authored Qimen public-divination rule library v2."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]


def blocks(text: str):
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        if match.group(1) >= '2026-08-20':
            yield match.group(1), text[match.start():end]


def card(block: str, label: str) -> str:
    match = re.search(
        rf'(?ms)（[345]）{label} 選項完整解讀卡.*?：(.*?)(?=｜暖米白底)',
        block,
    )
    return match.group(1).strip() if match else ''


def cjk_count(text: str) -> int:
    return len(re.findall(r'[\u3400-\u9fff]', text))


issues: list[tuple[str, str]] = []
checked_cards = 0
for path in FILES:
    for date, block in blocks(path.read_text(encoding='utf-8')):
        if '型式五下集' not in block.split('\n', 1)[0]:
            continue
        for label in 'ABC':
            text = card(block, label)
            checked_cards += 1
            if cjk_count(text) < 300:
                issues.append((date, f'{label} 少於 300 字'))
            required = {
                '明確定論': rf'(?m)^\*\*選項 {label}[：:]',
                '術語亮牌': '【盤象：',
                '表面現象': '‧ 表面現象：',
                '盤象真相': '‧ 盤象真相：',
                '時空與體感錨定': '【時空與體感錨定】',
                '奇門行為改運': '【奇門行為改運】',
            }
            for name, pattern in required.items():
                if not re.search(pattern, text):
                    issues.append((date, f'{label} 缺少 {name}'))
            if re.search(r'你(?:注定|一定會|必然)', text):
                issues.append((date, f'{label} 含命定論'))
            if '【盤象：' in text and not re.search(r'白話|換成日常|意思是|也就是說', text):
                issues.append((date, f'{label} 術語後缺少明示白話降維'))

print({'checked_type5_lower_cards': checked_cards, 'issues': issues, 'pass': not issues})
raise SystemExit(1 if issues else 0)
