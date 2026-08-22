#!/usr/bin/env python3
"""Fail closed when user-authored templates or the rule library drift."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / 'lunas_astral_code_master_playbook.md'
STANDARD_START = '## 【五大型式文案排版輸出標準規範】'
GUIDE_TITLE = '# IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫'
STANDARD_SHA256 = '3b233427c76c6750ccf256729453addf76f6adfb0d743c3446e60e4e7970a589'
GUIDE_SHA256 = 'fc941b9971f745d4f66c3aa7baa60cf9381644d8b674ce88730e74c1717f9f09'


def sections(playbook: str) -> tuple[str, str, str]:
    standard_start = playbook.find(STANDARD_START)
    guide_start = playbook.find(GUIDE_TITLE)
    if standard_start < 0 or guide_start < 0 or guide_start <= standard_start:
        raise RuntimeError('找不到或無法排序五大型式固定規範與文案寫作指南與規則庫。')
    return playbook[:standard_start], playbook[standard_start:guide_start], playbook[guide_start:]


def main() -> int:
    playbook = PLAYBOOK.read_text(encoding='utf-8')
    errors: list[str] = []
    prefix, standard, guide = sections(playbook)

    if hashlib.sha256(standard.encode('utf-8')).hexdigest() != STANDARD_SHA256:
        errors.append('五大型式文案排版輸出標準規範已變更；沒有使用者明確授權，不可接受新基線。')
    if hashlib.sha256(guide.encode('utf-8')).hexdigest() != GUIDE_SHA256:
        errors.append('文案寫作指南與規則庫已變更；沒有使用者明確授權，不可接受新基線。')
    if playbook.count(STANDARD_START) != 1:
        errors.append('五大型式文案排版輸出標準規範必須且只能出現一次。')
    if playbook.count(GUIDE_TITLE) != 1:
        errors.append('文案寫作指南與規則庫必須且只能出現一次。')
    for retired in ('## 5.', '## 6.', '## 7.', '### 6.0', '### 7.0'):
        if retired in prefix:
            errors.append(f'發現已廢止的舊 Part 5–7 結構：{retired}')

    if errors:
        print('FAIL: 使用者鎖定的模板或規則庫防回歸檢查未通過。')
        print('\n'.join(f'- {error}' for error in errors))
        return 1

    print('PASS: 五大型式固定規範與文案寫作指南與規則庫保持使用者鎖定基線。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
