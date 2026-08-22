#!/usr/bin/env python3
"""Rewrite only variable prose in the 22 unpublished scripts.

Fixed Playbook literals, CTAs, headings, cards, citations, hashtags, topics,
totems and publishing metadata are treated as immutable.  The rewriter applies
the updated Traditional-Chinese writing skills only to named prose slots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]
MODEL = 'gpt-5'


def split_blocks(text: str):
    starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        yield match.group(1), match.group(0), text[match.start():end]


def form(header: str) -> str:
    return next(x for x in ('型式五下集', '型式五上集', '型式一', '型式二', '型式三', '型式四') if x in header)


def section(block: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r'(.*?)' + re.escape(end), block, re.S)
    if not match:
        raise ValueError(f'Cannot locate section {start!r}')
    return match.group(1)


def add_slot(slots: list[dict], slot_id: str, text: str, *, minimum_cjk: int = 0, must_include: list[str] | None = None, reference: str = '') -> None:
    text = text.strip()
    if not text:
        raise ValueError(f'Empty variable slot: {slot_id}')
    slots.append({'id': slot_id, 'text': text, 'minimum_cjk': minimum_cjk, 'must_include': must_include or [], 'reference': reference})


def answer_slots(block: str, labels: str) -> list[dict]:
    anchor = '【置頂留言區解答｜'
    start = block.index(anchor)
    region = block[start: block.index('————————————', start)]
    slots: list[dict] = []
    for label in labels:
        match = re.search(rf'(?ms)^{label}：(.*?)(?=\n\n[{'|'.join(labels)}]：|\Z)', region)
        if not match:
            raise ValueError(f'Missing pinned answer {label}')
        add_slot(slots, f'answer_{label}', match.group(1))
    return slots


def card_tail_slots(block: str) -> list[dict]:
    reference_map = {
        'A': {'terms': ['乾六宮', '西北', '天心星', '開門', '未時', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L014；data/QMDJ_ShangJuan_Consolidated.json / QMDJ_Auto_00328'},
        'B': {'terms': ['坎一宮', '正北', '天蓬星', '休門', '申時', '大凶', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L015；data/QMDJ_ShangJuan_Consolidated.json / QMDJ_Auto_00329'},
        'C': {'terms': ['艮八宮', '東北', '天任星', '生門', '酉時', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L013；data/QMDJ_ShangJuan_Consolidated.json / QMDJ_Auto_00330'},
    }
    slots: list[dict] = []
    for index, label in enumerate('ABC', 3):
        match = re.search(
            rf'(?ms)^（{index}）{label} 選項完整解讀卡（[^）]+）：(.*?)(?=｜暖米白底`#F5F5DC`、深海軍藍`#0D0D2B`（文字）、霧玫瑰金`#B4918F`（邊框 \+ 圖騰線稿）。)',
            block,
        )
        if not match:
            raise ValueError(f'Missing Type 5 lower card {label}')
        parts = match.group(1).strip().split('\n\n', 1)
        if len(parts) != 2:
            raise ValueError(f'Missing fixed SSOT boundary / variable tail in card {label}')
        # The first paragraph is a fixed safety boundary. Only rewrite the tail.
        ref = reference_map[label]
        add_slot(slots, f'card_{label}_tail', parts[1], minimum_cjk=300, must_include=ref['terms'], reference=ref['source'])
    return slots


def slots_for(block: str, kind: str) -> list[dict]:
    body = section(block, '正文：\n', '\n\nHashtags：')
    if kind == '型式一':
        scene = body.split('\n長按螢幕 +「留言」領取你的「專屬能量提示」')[0]
        slots: list[dict] = []
        add_slot(slots, 'scene', scene)
        slots.extend(answer_slots(block, 'ABCDEF'))
        return slots
    if kind == '型式二':
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        if len(lines) != 3:
            raise ValueError(f'Type 2 body must contain three variable lines, got {len(lines)}')
        slots = []
        for slot_id, line in zip(('scene', 'reflection', 'action'), lines):
            add_slot(slots, slot_id, line)
        return slots
    if kind == '型式三':
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        if len(lines) < 3:
            raise ValueError('Type 3 body is incomplete')
        slots = []
        add_slot(slots, 'explain', lines[1])
        return slots
    if kind == '型式四':
        lines = [x.strip() for x in body.splitlines() if x.strip()]
        if len(lines) != 4:
            raise ValueError(f'Type 4 body must contain four lines, got {len(lines)}')
        slots = []
        for slot_id, line in zip(('scene', 'check', 'action'), (lines[0], lines[1], lines[3])):
            add_slot(slots, slot_id, line)
        return slots
    if kind == '型式五上集':
        match = re.search(r'(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺', body)
        if not match:
            raise ValueError('Missing Type 5 upper scene')
        story = re.search(r'(?ms)^🔮 C\. .*?\n\n(.*?)\n下一期帶你解鎖更多新的占卜提示～', body)
        if not story:
            raise ValueError('Missing Type 5 upper story')
        slots = []
        add_slot(slots, 'scene', match.group(1))
        add_slot(slots, 'story', story.group(1), minimum_cjk=50)
        slots.extend(answer_slots(block, 'ABC'))
        return slots
    if kind == '型式五下集':
        return card_tail_slots(block)
    raise ValueError(kind)


def request_rewrite(date: str, kind: str, header: str, slots: list[dict], retry: int = 0) -> dict[str, str]:
    slot_payload = [{'id': slot['id'], 'text': slot['text'], 'minimum_cjk': slot['minimum_cjk'], 'must_include': slot.get('must_include', []), 'reference': slot.get('reference', '')} for slot in slots]
    system = '''你是繁體中文（台灣）IG 文案編輯。只改可變散文，保持原本事實、語意強度、主題、時間、圖騰、CTA、專有名詞與不確定性。\n\n依序套用：\n1. humanizer-tw：刪除套話、翻譯腔、黑話、假深刻、金句公式、短句連發戲劇腔與無源權威；不要誤殺合法台灣用語。\n2. good-writing-tw：讓句長與句尾有自然錯落，拆除真正過長或塞太多資訊的句子，但不要把全文修成節拍器。\n3. authentic-voice-editing / speak-human-tw：以具體情景、真主語和真動作取代抽象安慰；不要新增事實、數字、經歷、來源、承諾或命理結論。\n\n這是社群文案。可保留適度猶豫與生活感，但不要演戲、不要客服腔、不要空泛雞湯。用第二人稱「你」。不要輸出任何固定模板標籤、CTA、Hashtags、Hook 或卡片標題；但型式五下集的可變完整解讀必須輸出下方指定的粗體定論與模組標題。\n\n若內容涉及奇門或紫微：不可新增星曜、門、神、奇儀、方位、時間、吉凶、公式或個人起局結果。只有 slot 提供的 `must_include` 和 `reference` 可新增到該 slot；必須將它們表述為公開奇門資料的「對照示例」，接著立刻白話轉譯，絕不可說成已替讀者起局或確認讀者正處該局。沒有資料就寫生活層面的可觀察情景與行動。\n\n最新版型式五上集的對應文字是「奇門生活小貼士」，不是故事、故事卡或心理劇；其生活貼士至少 50 字。\n\n型式五下集每個 card_A_tail／card_B_tail／card_C_tail 是完整解讀的可變部分，至少 300 字，必須依序、逐字採用以下五層閱讀格式：\n**選項 X：［一句明確但非命定的主軸結論］**\n【盤象：［只使用 must_include 中已核對的門、星、宮位或奇儀；不可自行補造］】\n‧ 表面現象：［具體外在行為或心理狀態］\n‧ 盤象真相：［內在拉扯或局勢本質；把術語立刻白話翻譯，明說「白話來說」或同義語］\n【時空與體感錨定】\n‧ ［只使用 must_include 的方位、時間、吉凶；或可觀察的生活感受。體感不是醫療診斷。］\n【奇門行為改運】\n‧ ［一至兩項低門檻、可觀察的整理、溝通、休息或行程行動；不可保證化解、招財、吸納吉氣或改變他人。］\n\n其中 X 必須等於該 slot 的 A、B 或 C。每一模組最多兩句，模組之間換行。首句要明確，卻不得使用「注定」「必然」「一定會」「百分之百」。不可改動任何固定模板文字。\n\n每個 slot 都必須改寫，不能原封不動回傳。對 minimum_cjk 大於零的 slot，輸出必須至少達該數量的中文字；`must_include` 內的每個字串必須逐字出現。'''
    user = {
        'date': date,
        'form': kind,
        'header_context': header,
        'slots': slot_payload,
        'task': '逐一改寫所有 slot。輸出 JSON，rewrites 內必須剛好有每個 id 一次。' + (' 上一稿有欄位原封不動複製或未納入指定術語；本次每個欄位必須在不改變事實下改變句法與用字，並逐一包含 must_include。' if retry else ''),
    }
    schema = {
        'type': 'object',
        'properties': {
            'rewrites': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {'id': {'type': 'string'}, 'text': {'type': 'string'}},
                    'required': ['id', 'text'],
                    'additionalProperties': False,
                },
            },
        },
        'required': ['rewrites'],
        'additionalProperties': False,
    }
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)},
        ],
        'max_completion_tokens': 16000,
        'response_format': {'type': 'json_schema', 'json_schema': {'name': 'script_slot_rewrites', 'strict': True, 'schema': schema}},
    }
    last_error = ''
    for attempt in range(3):
        response = requests.post(
            os.environ['OPENAI_API_BASE'].rstrip('/') + '/chat/completions',
            headers={'Authorization': f"Bearer {os.environ['OPENAI_API_KEY']}", 'Content-Type': 'application/json'},
            json=payload,
            timeout=240,
        )
        try:
            response.raise_for_status()
            body = response.json()
            content = body['choices'][0]['message']['content']
            return {item['id']: item['text'].strip() for item in json.loads(content)['rewrites']}
        except (requests.RequestException, KeyError, ValueError, TypeError) as exc:
            last_error = f'{exc}; response={response.text[:500]}'
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
    raise RuntimeError(f'Model rewrite request failed after retries: {last_error}')


def cjk_count(text: str) -> int:
    return len(re.findall(r'[\u3400-\u9fff]', text))


def validate_output(slots: list[dict], rewritten: dict[str, str]) -> None:
    expected = {slot['id'] for slot in slots}
    if set(rewritten) != expected:
        raise ValueError(f'Rewrite IDs differ: expected {expected}, got {set(rewritten)}')
    forbidden = ('Hook：', 'Hashtags：', '固定CTA', '固定 CTA', '視覺分鏡描述', '【待記錄】')
    for slot in slots:
        value = rewritten[slot['id']].strip()
        if not value or value == slot['text']:
            raise ValueError(f'Slot not rewritten: {slot["id"]}')
        if any(token in value for token in forbidden):
            raise ValueError(f'Fixed template token leaked into {slot["id"]}')
        if slot['minimum_cjk'] and cjk_count(value) < slot['minimum_cjk']:
            raise ValueError(f'Slot {slot["id"]} shorter than {slot["minimum_cjk"]} CJK chars')
        if slot['id'].startswith('card_'):
            label = slot['id'].split('_')[1]
            required_sections = (f'**選項 {label}：', '【盤象：', '‧ 表面現象：', '‧ 盤象真相：', '【時空與體感錨定】', '【奇門行為改運】')
            missing_sections = [section for section in required_sections if section not in value]
            if missing_sections:
                raise ValueError(f'Slot {slot["id"]} missing rule-library sections: {missing_sections}')
            if re.search(r'你(?:注定|必然|一定會|百分之百)', value):
                raise ValueError(f'Slot {slot["id"]} contains fate-determinism language')
        missing = [term for term in slot.get('must_include', []) if term not in value]
        if missing:
            raise ValueError(f'Slot {slot["id"]} missing SSOT-backed terms: {missing}')


def apply_slots(block: str, slots: list[dict], rewritten: dict[str, str]) -> str:
    changed = block
    for slot in sorted(slots, key=lambda item: len(item['text']), reverse=True):
        old, new = slot['text'], rewritten[slot['id']]
        if old not in changed:
            raise ValueError(f'Cannot apply slot {slot["id"]}; original text is absent')
        changed = changed.replace(old, new)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--forms', default='', help='Comma-separated forms to rewrite; empty means all forms.')
    parser.add_argument('--audit', type=Path, default=Path('/home/ubuntu/updated_writing_skill_rewrite_audit.json'))
    args = parser.parse_args()
    allowed_forms = {item.strip() for item in args.forms.split(',') if item.strip()}
    audit = []
    pending: list[tuple[Path, str, str, str, list[dict]]] = []
    for path in FILES:
        source = path.read_text(encoding='utf-8')
        for date, header, block in split_blocks(source):
            if date < '2026-08-20':
                continue
            kind = form(header)
            if allowed_forms and kind not in allowed_forms:
                continue
            slots = slots_for(block, kind)
            pending.append((path, date, header, block, slots))
    if not allowed_forms and len(pending) != 22:
        raise ValueError(f'Expected 22 unpublished scripts, got {len(pending)}')
    if allowed_forms and not pending:
        raise ValueError(f'No scripts found for forms: {sorted(allowed_forms)}')
    if args.dry_run:
        summary = [{'date': date, 'form': form(header), 'slots': [slot['id'] for slot in slots]} for _, date, header, _, slots in pending]
        args.audit.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'posts': len(summary), 'dry_run': True, 'audit': str(args.audit)}, ensure_ascii=False))
        return 0
    by_file: dict[Path, list[tuple[str, str]]] = {path: [] for path in FILES}
    for path, date, header, block, slots in pending:
        last_error: Exception | None = None
        for retry in range(3):
            rewritten = request_rewrite(date, form(header), header, slots, retry)
            try:
                validate_output(slots, rewritten)
                break
            except ValueError as exc:
                last_error = exc
        else:
            raise last_error if last_error else RuntimeError('Unexpected rewrite validation failure')
        revised = apply_slots(block, slots, rewritten)
        by_file[path].append((block, revised))
        audit.append({
            'date': date,
            'form': form(header),
            'changed_slots': [slot['id'] for slot in slots],
            'before_sha256': hashlib.sha256(block.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(revised.encode()).hexdigest(),
        })
    for path, replacements in by_file.items():
        text = path.read_text(encoding='utf-8')
        for old, new in replacements:
            if text.count(old) != 1:
                raise ValueError(f'Ambiguous post replacement in {path.name}')
            text = text.replace(old, new, 1)
        path.write_text(text, encoding='utf-8')
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'posts': len(audit), 'model': MODEL, 'audit': str(args.audit)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
