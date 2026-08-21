#!/usr/bin/env python3
"""Strict, read-only validator for the latest user-authored Playbook standard."""
from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]
PUBLISHED = {'2026-08-17', '2026-08-18'}
PENDING = '【待記錄】發布後48小時：reach / 非追蹤者觸及 / profile visits / website clicks / DM / saves / shares'
CTA = {
    '型式一': '下方留言 A / B / C / D / E / F 👇🏻\n【解答將於 24 小時後置頂留言區】',
    '型式二': '點擊「追蹤」隨時陪伴在你身邊～',
    '型式三': '點擊「收藏」打開命盤隨時上手\n下一期繼續拆解一個排盤小知識',
    '型式四': '點擊「分享」給朋友一起確認吧～',
    '型式五上集': '「留言」A / B / C 明天置頂留言區公佈解答 ✨\n想看後續「完整解讀」留意下一集',
    '型式五下集': '喜歡這期解讀指引的朋友\n歡迎「收藏 + 追蹤」持續領取你的解讀提示吧～\n\n若想針對個人問題進行深入解析 📩\n歡迎直接 DM 預約一對一的專屬命盤諮詢 🌙',
}
VISUAL = {
    '型式二': ['（1）封面 Hook 卡：', '（2）情境卡：', '（3）語錄卡：', '（4）行動卡：', '（5）CTA 尾卡：'],
    '型式三': ['（1）封面 Hook 卡：30 秒帶你看懂', '（2）定位卡：打開你的紫微斗數命盤，先找到', '（3）輔助卡：', '（4）補充卡：', '（5）CTA 尾卡：'],
    '型式四': ['（1）封面 Hook 卡：', '（2）事情/情景卡：', '（3）檢查卡：', '（4）解析卡：', '（5）CTA 尾卡：'],
}
RETIRED = ('視覺規範核對清單', '【每張固定版面】', '視覺設定：', '上集主題 +', '三個圖騰並排，提醒讀者回到原選項')


def blocks(path: Path):
    text = path.read_text(encoding='utf-8')
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        date = match.group(1)
        yield date, match.group(0), text[match.start():end]


def form(header: str) -> str | None:
    return next((item for item in ('型式五下集', '型式五上集', '型式一', '型式二', '型式三', '型式四') if item in header), None)


def extract_topic(block: str) -> str | None:
    m = re.search(r'Hook：\n【(?:大眾奇門占卜｜)?(?:完整解讀公佈：)?(.+?)】', block)
    return m.group(1) if m else None


def extract_option_names(block: str, labels='ABC') -> list[str]:
    names = []
    for label in labels:
        m = re.search(rf'(?m)^🔮 {label}\. (.+)$', block)
        if m:
            names.append(m.group(1).strip())
    return names


def cjk_count(text: str) -> int:
    return len(re.findall(r'[\u3400-\u9fff]', text))


def lower_card_text(block: str, label: str) -> str:
    match = re.search(rf'（[345]）{label} 選項完整解讀卡.*?：(.*?)(?=\n\n（[3456]）|\n（6）|\Z)', block, re.S)
    return match.group(1) if match else ''


def main() -> int:
    issues: list[tuple[str, str]] = []
    posts: dict[str, tuple[str, str, str]] = {}
    actual = 0
    for path in FILES:
        current_text = path.read_text(encoding='utf-8')
        if path.name.startswith('60day_scripts_W4'):
            baseline = subprocess.check_output(['git', '-C', str(ROOT), 'show', f'HEAD:{path.relative_to(ROOT)}'], text=True)
            current_prefix = current_text[:current_text.index('## 2026-08-20')]
            baseline_prefix = baseline[:baseline.index('## 2026-08-20')]
            if current_prefix != baseline_prefix:
                issues.append(('PUBLISHED', '2026-08-17、2026-08-18 已發布內容被修改'))
        for date, header, block in blocks(path):
            if date in PUBLISHED:
                continue
            if date < '2026-08-20':
                continue
            actual += 1
            kind = form(header)
            posts[date] = (kind or '', header, block)
            if not kind:
                issues.append((date, '無法判定型式'))
                continue
            if PENDING not in block:
                issues.append((date, '缺少發布後 48 小時待記錄欄位'))
            if any(item in block for item in RETIRED):
                issues.append((date, '保留舊版視覺／承接文字'))
            tags = re.search(r'(?m)^Hashtags：(.+)$', block)
            if not tags or len(re.findall(r'#[\w\u3400-\u9fff]+', tags.group(1))) != 5 or '#Lunasastralcode' not in tags.group(1):
                issues.append((date, 'Hashtags 必須為四個主題／拉新標籤加 #Lunasastralcode'))
            expected_cta = CTA[kind]
            cta = re.search(r'(?ms)^(?:固定 ?)?CTA：\s*(.*?)(?=\n————————————|\n視覺分鏡描述|\n【待記錄】|\Z)', block)
            if not cta or cta.group(1).strip() != expected_cta:
                issues.append((date, f'CTA 未逐字符合最新模板：{repr(cta.group(1).strip() if cta else None)}'))
            if kind == '型式一':
                if not re.search(r'(?m)^Hook： 【.+｜.+】$', block):
                    issues.append((date, '型式一 Hook 格式錯誤'))
                if '長按螢幕 +「留言」領取你的「專屬能量提示」' not in block:
                    issues.append((date, '型式一缺少固定正文引導'))
                if len(extract_option_names(block, 'ABCDEF')) != 6:
                    issues.append((date, '型式一缺少 A–F 圖騰'))
                for item in ('【固定文字圖層】', '(1) 上方區域（透明底欄背景）：', '(2) 下方區域：', '【主體閃爍序列（6張 中央圖騰，0.08 秒/張 無縫硬切循環）】 6 組圖騰：', '【動畫與渲染邏輯】'):
                    if item not in block:
                        issues.append((date, f'型式一缺少固定視覺文字：{item}'))
            elif kind in VISUAL:
                for item in VISUAL[kind]:
                    if item not in block:
                        issues.append((date, f'{kind}缺少固定視覺卡：{item}'))
            elif kind == '型式五上集':
                for item in ('閉上眼，深呼吸三次', '心裡默念：', '憑第一眼直覺，選出一張最吸引你的圖騰：', '下一期帶你解鎖更多新的占卜提示～', '【置頂留言區解答｜24 小時發布後】'):
                    if item not in block:
                        issues.append((date, f'型式五上集缺少固定文字：{item}'))
                for item in ('（1）Hook 卡（0–3 秒）', '（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次+ 心裡默念：', '（3）三選項圖卡（9–18 秒）', '（4）故事卡（18–22 秒）', '（5）CTA 卡（22–30 秒）'):
                    if item not in block:
                        issues.append((date, f'型式五上集缺少固定視覺卡：{item}'))
                if len(extract_option_names(block, 'ABC')) != 3:
                    issues.append((date, '型式五上集缺少 A／B／C 圖騰'))
            elif kind == '型式五下集':
                for item in ('上集選好答案的朋友，\n要先看上集置頂留言區的解答，\n再回來看這一集的「完整解讀」。', '【在貼文中領取「完整解讀」喔～】', '（1）固定封面 Hook 卡：大標題「大眾奇門占卜」＋副標「完整解讀公佈」', '（2）解答承接卡：'):
                    if item not in block:
                        issues.append((date, f'型式五下集缺少固定文字：{item}'))
                for label in 'ABC':
                    body = lower_card_text(block, label)
                    if cjk_count(body) < 500:
                        issues.append((date, f'型式五下集 {label} 完整解讀少於 500 字：{cjk_count(body)}'))
    if actual != 22:
        issues.append(('GLOBAL', f'未發布腳本數量錯誤：{actual}'))

    upper_dates = sorted(date for date, (kind, _, _) in posts.items() if kind == '型式五上集')
    lower_dates = sorted(date for date, (kind, _, _) in posts.items() if kind == '型式五下集')
    for upper, lower in zip(upper_dates[:5], lower_dates):
        utopic = extract_topic(posts[upper][2])
        ltopic = extract_topic(posts[lower][2])
        if utopic != ltopic:
            issues.append((lower, '型式五下集 Hook 未逐字承接上集窄題'))
        if utopic and f'{utopic} + 先看上集置頂留言區解答，再回看本集完整解讀' not in posts[lower][2]:
            issues.append((lower, '型式五下集解答承接卡未代入上集實際窄題'))
        upper_options = extract_option_names(posts[upper][2])
        expected_cards = [f'（{index}）{label} 選項完整解讀卡（{name}）：' for index, (label, name) in enumerate(zip('ABC', upper_options), 3)]
        if not all(card in posts[lower][2] for card in expected_cards):
            issues.append((lower, '型式五上下集圖騰未一一對應'))

    print({'posts_checked': actual, 'issues': issues, 'pass': not issues})
    return 1 if issues else 0


if __name__ == '__main__':
    raise SystemExit(main())
