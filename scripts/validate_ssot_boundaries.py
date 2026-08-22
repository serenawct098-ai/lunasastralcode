#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SSOT = Path('/home/ubuntu/ziwei_qimen')
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]
LOWER_REFERENCES = {
    'A': {'terms': ['乾六宮', '西北', '天心星', '開門', '未時', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L014'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00328')]},
    'B': {'terms': ['坎一宮', '正北', '天蓬星', '休門', '申時', '大凶', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L015'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00329')]},
    'C': {'terms': ['艮八宮', '東北', '天任星', '生門', '酉時', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L013'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00330')]},
}
TYPE1_REFERENCES = {
    'A': {'terms': ['乾六宮', '西北', '天心星', '開門', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L014')]},
    'B': {'terms': ['坎一宮', '正北', '天蓬星', '休門', '大凶', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L015')]},
    'C': {'terms': ['艮八宮', '東北', '天任星', '生門', '大吉'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L013')]},
    'D': {'terms': ['兌七宮', '正西', '天柱星', '驚門', '小凶'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L014')]},
    'E': {'terms': ['離九宮', '正南', '天英星', '景門', '中平'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L012')]},
    'F': {'terms': ['震三宮', '正東', '天沖星', '傷門', '凶'], 'checks': [('data/XingMen_WuXing_ShengKe.json', 'XMWX_L011')]},
}

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
        if '型式一' in header:
            anchor = '【置頂留言區解答｜'
            region = block[block.index(anchor):] if anchor in block else ''
            for label, spec in TYPE1_REFERENCES.items():
                answer = re.search(rf'(?ms)^{label}：(.*?)(?=\n\n[ABCDEF]：|\Z)', region)
                if not answer:
                    issues.append((date, f'型式一缺少 {label} 置頂解答'))
                    continue
                missing = [term for term in spec['terms'] if term not in answer.group(1)]
                if missing:
                    issues.append((date, f'型式一 {label} 缺少公開奇門對照：{missing}'))
                for relpath, line_id in spec['checks']:
                    source = SSOT / relpath
                    if not source.is_file() or line_id not in source.read_text(encoding='utf-8'):
                        issues.append((date, f'型式一 {label} 無法反向定位 SSOT：{relpath} / {line_id}'))
        if '型式五上集' in header or '型式五下集' in header:
            no_personal_reading = re.search(r'(?:不會(?:、?也不能)?|不能|不)替你安門、定星(?:，或|、)判方位、時間(?:或|、)吉凶', block)
            if '型式五上集' in header and not no_personal_reading:
                issues.append((date, '型式五上集缺少無起局資料不代判邊界'))
            if '型式五下集' in header:
                if '不替你安門、定星、判方位、時間或吉凶' not in block:
                    issues.append((date, '型式五下集完整卡缺少無起局資料不代判邊界'))
                for label, spec in LOWER_REFERENCES.items():
                    card = re.search(rf'(?ms)（[345]）{label} 選項完整解讀卡.*?：(.*?)(?=｜暖米白底)', block)
                    if not card:
                        issues.append((date, f'型式五下集缺少 {label} 完整解讀卡'))
                        continue
                    missing = [term for term in spec['terms'] if term not in card.group(1)]
                    if missing:
                        issues.append((date, f'型式五下集 {label} 缺少公開奇門對照：{missing}'))
                    for relpath, line_id in spec['checks']:
                        source = SSOT / relpath
                        if not source.is_file() or line_id not in source.read_text(encoding='utf-8'):
                            issues.append((date, f'型式五下集 {label} 無法反向定位 SSOT：{relpath} / {line_id}'))

print({'posts_checked': posts, 'ssot_commit': 'ac8f093f76a6dbcf459eca0075a33828aa47ef7e', 'issues': issues})
if issues:
    raise SystemExit(1)
print('PASS: Type 1 and Type 5 public Qimen terms are SSOT-verifiable; Type 3 locators are reversible; no public script claims a personal Qimen reading.')
