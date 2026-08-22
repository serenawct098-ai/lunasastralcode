#!/usr/bin/env python3
"""Regression checks for the updated Traditional-Chinese writing-skill rewrite."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]
AUDIT = Path('/home/ubuntu/updated_writing_skill_rewrite_audit.json')
# High-confidence problem clusters from the updated writing skills.  These are
# intentionally narrow so ordinary, legitimate wording is not over-corrected.
BANNED = {
    '時代開場': ('隨著.*發展', '眾所周知'),
    '無源權威': ('專家認為', '研究顯示', '業內普遍認為'),
    '黑話': ('賦能', '閉環', '底層邏輯'),
    '假深刻': ('真正的問題是', '本質上', '說到底'),
    '客服與結尾套話': ('希望這篇', '讓我們拭目以待', '攜手共進'),
    '中國用語': ('信息', '視頻', '默認', '軟件', '算法', '代碼'),
    '翻譯腔': ('不僅.*而且', '顯著地', '深刻地', '對.*進行.*優化'),
}


def blocks(text: str):
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        if match.group(1) >= '2026-08-20':
            yield match.group(1), text[match.start():end]


issues = []
for path in FILES:
    for date, block in blocks(path.read_text(encoding='utf-8')):
        # Never lint fixed-template lines; they are locked by a dedicated guard.
        prose = re.sub(r'(?m)^(固定 ?CTA|Hashtags|Hook|視覺分鏡描述|【待記錄】).*$', '', block)
        for family, patterns in BANNED.items():
            for pattern in patterns:
                if re.search(pattern, prose):
                    issues.append((date, family, pattern))
        # Three dramatic micro-sentences in a row are a high-confidence modern
        # AI tell.  Ignore list rows and visual cards.
        lines = [line.strip() for line in prose.splitlines() if line.strip() and not line.lstrip().startswith(('🔮', '（', '*', '—'))]
        short = 0
        for line in lines:
            cjk = len(re.findall(r'[\u3400-\u9fff]', line))
            short = short + 1 if 1 <= cjk <= 5 and line.endswith(('。', '！', '？')) else 0
            if short >= 3:
                issues.append((date, '短句連發戲劇腔', line))
                break

if not AUDIT.is_file():
    issues.append(('GLOBAL', '缺少改寫稽核紀錄', str(AUDIT)))
else:
    audit = json.loads(AUDIT.read_text(encoding='utf-8'))
    if len(audit) != 22:
        issues.append(('GLOBAL', '改寫稽核篇數錯誤', str(len(audit))))
    for item in audit:
        if item.get('before_sha256') == item.get('after_sha256'):
            issues.append((item.get('date', 'UNKNOWN'), '可變正文未改寫', 'SHA256 相同'))

print({'posts_checked': 22, 'issues': issues})
if issues:
    raise SystemExit(1)
print('PASS: updated writing-skill rewrite passes high-confidence Taiwanese-Chinese style regression checks.')
