#!/usr/bin/env python3
"""Fail closed on drift from user-authored Playbook Parts 5–7.

Part 5, Part 6, and Part 7 are user-owned writing-method templates.  They are
immutable unless the user explicitly requests a template amendment.  Scripts may
adapt only variable slots, such as each post's concrete scenario, while retaining
the corresponding fixed wrapper.  This check only reads files; it never rewrites.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / 'lunas_astral_code_master_playbook.md'
SCRIPT_FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]

# Reviewed user-authored Part 5–7 baseline recovered from commit 7498856.
PARTS_5_TO_7_SHA256 = '8a9b5292a3867f0d18494a30df0678a551be5de5514fd6acd834918720f3a1b3'
LOWER = '解答承接卡：上集主題 + 先看上集置頂留言區解答，再回看本集完整解讀'
UPPER_PATTERN = re.compile(
    r'（3–9 秒）問題聚焦卡：「閉上眼深呼吸 3 次」\+\n'
    r'「心裡默念：(?!眼前的情景」\+「以第一直覺選擇」$)(?P<scene>[^\n]+)」\+「以第一直覺選擇」',
    re.MULTILINE,
)


def user_locked_parts(playbook: str) -> str:
    match = re.search(r'(?ms)^## 5\..*?(?=^## 8\.)', playbook)
    if not match:
        raise RuntimeError('找不到 Playbook Part 5–7 的完整範圍。')
    return match.group(0)


def type_five_blocks(text: str) -> list[tuple[str, str]]:
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    return [
        (match.group(1), text[match.start(): starts[index + 1].start() if index + 1 < len(starts) else len(text)])
        for index, match in enumerate(starts)
        if match.group(1) >= '2026-08-20'
    ]


def main() -> int:
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    actual_hash = hashlib.sha256(user_locked_parts(playbook).encode('utf-8')).hexdigest()
    errors: list[str] = []

    if actual_hash != PARTS_5_TO_7_SHA256:
        errors.append('Part 5–7 已偏離使用者手寫基線；未獲明確授權不得覆寫或接受新基線。')

    upper_cards = 0
    lower_cards = 0
    for path in SCRIPT_FILES:
        for date, block in type_five_blocks(path.read_text(encoding='utf-8')):
            if '型式五上集' in block:
                matches = list(UPPER_PATTERN.finditer(block))
                if len(matches) != 1:
                    errors.append(f'{date} 型式五上集須有且僅有一張 Part 7 問題聚焦卡。')
                elif not matches[0].group('scene').strip():
                    errors.append(f'{date} 型式五上集缺少該篇具體情景。')
                upper_cards += len(matches)
            if '型式五下集' in block:
                if LOWER not in block:
                    errors.append(f'{date} 型式五下集缺少 Part 7 固定解答承接卡。')
                else:
                    lower_cards += 1

    if upper_cards != 6:
        errors.append(f'型式五上集問題聚焦卡應為 6 張，實際為 {upper_cards} 張。')
    if lower_cards != 5:
        errors.append(f'型式五下集解答承接卡應為 5 張，實際為 {lower_cards} 張。')

    if errors:
        print('FAIL: 使用者鎖定模板防回歸檢查未通過。')
        print('\n'.join(f'- {error}' for error in errors))
        return 1

    print('PASS: Part 5–7 保持使用者手寫基線；腳本只在允許的具體情景欄位填入各篇內容。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
