#!/usr/bin/env python3
"""Fail closed when user-locked Playbook Parts 5–7 or type-five literals drift.

Part 5, Part 6, and Part 7 are user-authored templates. They are immutable unless
an explicit user request authorizes a new baseline. This script never rewrites files.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / 'lunas_astral_code_master_playbook.md'
SCRIPT_FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]

# This value is filled from the reviewed user-locked baseline immediately after restore.
PARTS_5_TO_7_SHA256 = '2fa4646a5006c55ff878a5982ad2f3ee1a2c7315e8662cb2caa3e2dc812dac70'

UPPER = '問題聚焦卡：「閉上眼深呼吸 3 次」+\n「心裡默念：眼前的情景」+「以第一直覺選擇」'
LOWER = '解答承接卡：上集主題 + 先看上集置頂留言區解答，再回看本集完整解讀'
FORBIDDEN = (
    '問題聚焦卡：「閉上眼，慢慢吸幾口氣」',
    '「心裡想著：',
    '「跟著第一眼的感覺選」',
    '解答承接卡：先看上集置頂留言區解答，再閱讀本集完整解讀',
    '解答承接卡：上集同題',
)


def user_locked_parts(playbook: str) -> str:
    match = re.search(r'(?ms)^## 5\..*?(?=^## 8\.)', playbook)
    if not match:
        raise RuntimeError('找不到 Playbook Part 5–7 的完整範圍。')
    return match.group(0)


def main() -> int:
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    locked = user_locked_parts(playbook)
    actual_hash = hashlib.sha256(locked.encode('utf-8')).hexdigest()
    errors: list[str] = []

    if actual_hash != PARTS_5_TO_7_SHA256:
        errors.append('Part 5–7 區段內容已變更；沒有使用者明確授權，不可覆寫或接受新基線。')

    for phrase in ('閉上眼深呼吸 3 次', '心裡默念：眼前的情景', '以第一直覺選擇'):
        if playbook.count(phrase) < 2:
            errors.append(f'Playbook 固定上集文字缺失：{phrase}')
    if playbook.count(LOWER) < 2:
        errors.append('Playbook 固定下集承接文字缺失。')

    combined = '\n'.join(path.read_text(encoding='utf-8') for path in SCRIPT_FILES)
    if combined.count(UPPER) != 6:
        errors.append(f'型式五上集問題聚焦卡應為 6 張，實際為 {combined.count(UPPER)} 張。')
    if combined.count(LOWER) != 5:
        errors.append(f'型式五下集解答承接卡應為 5 張，實際為 {combined.count(LOWER)} 張。')
    for phrase in FORBIDDEN:
        if phrase in playbook or phrase in combined:
            errors.append(f'發現已禁止的舊模板寫法：{phrase}')

    if errors:
        print('FAIL: 使用者鎖定模板防回歸檢查未通過。')
        print('\n'.join(f'- {error}' for error in errors))
        return 1

    print('PASS: Part 5–7 完整區段與型式五固定字句均保持使用者鎖定基線。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
