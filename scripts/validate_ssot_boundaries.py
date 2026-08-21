#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SSOT = Path('/home/ubuntu/ziwei_qimen')
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]

issues = []
posts = 0
for path in FILES:
    text = path.read_text(encoding='utf-8')
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for i, match in enumerate(starts):
        date = match.group(1)
        if date < '2026-08-20':
            continue
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[match.start():end]
        posts += 1
        header = block.split('\n', 1)[0]
        if '型式三' in header:
            for relpath, line_id in re.findall(r'`(data/[^`]+)`，`([^`]+)`', block):
                source = SSOT / relpath
                if not source.is_file():
                    issues.append((date, f'缺少 SSOT 檔案：{relpath}'))
                elif line_id not in source.read_text(encoding='utf-8'):
                    issues.append((date, f'無法反向定位 SSOT 行號：{line_id}'))
        if '型式五上集' in header or '型式五下集' in header:
            required = '不能替你安門、定星、判方位、時間或吉凶'
            if '型式五上集' in header and required not in block:
                issues.append((date, '型式五上集缺少無起局資料不代判邊界'))
            if '型式五下集' in header and '不替你安門、定星、判方位、時間或吉凶' not in block:
                issues.append((date, '型式五下集完整卡缺少無起局資料不代判邊界'))

print({'posts_checked': posts, 'ssot_commit': 'ac8f093f76a6dbcf459eca0075a33828aa47ef7e', 'issues': issues})
if issues:
    raise SystemExit(1)
print('PASS: all Type 3 source locators are reversible and Type 5 scripts do not invent personal Qimen results.')
