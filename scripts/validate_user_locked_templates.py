#!/usr/bin/env python3
"""Fail closed when the user-authored unique writing standard drifts.

The Playbook's user-owned fixed source is the complete section beginning with
「五大型式文案排版輸出標準規範」.  It replaces the retired Part 5–7 model.
This check only reads files; it never rewrites them.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / 'lunas_astral_code_master_playbook.md'
STANDARD_SHA256 = '1163b7e2c8a787bd486f438cfa096a995a30413f57c2a527ba36430fe3fa1f35'
STANDARD_START = '## 【五大型式文案排版輸出標準規範】'
GUIDE_TITLE = '**「IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫」**：'


def standard_section(playbook: str) -> str:
    start = playbook.find(STANDARD_START)
    if start < 0:
        raise RuntimeError('找不到使用者鎖定的五大型式文案排版輸出標準規範。')
    return playbook[start:]


def main() -> int:
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    errors: list[str] = []
    section = standard_section(playbook)

    actual_hash = hashlib.sha256(section.encode('utf-8')).hexdigest()
    if actual_hash != STANDARD_SHA256:
        errors.append('五大型式文案排版輸出標準規範已變更；沒有使用者明確授權，不可接受新基線。')
    if playbook.count(STANDARD_START) != 1:
        errors.append('五大型式文案排版輸出標準規範必須且只能出現一次。')
    if playbook.count(GUIDE_TITLE) != 1:
        errors.append('文案寫作指南與規則庫必須且只能出現一次。')
    for retired in ('## 5.', '## 6.', '## 7.', '### 6.0', '### 7.0'):
        if retired in playbook:
            errors.append(f'發現已廢止的舊 Part 5–7 結構：{retired}')

    if errors:
        print('FAIL: 使用者鎖定的唯一文案標準防回歸檢查未通過。')
        print('\n'.join(f'- {error}' for error in errors))
        return 1

    print('PASS: 五大型式文案排版輸出標準規範與文案寫作指南與規則庫保持使用者鎖定基線。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
