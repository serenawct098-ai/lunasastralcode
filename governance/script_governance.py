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
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / 'scripts/60day_scripts_W4-W9_20260817-20260925.md',
    ROOT / 'scripts/60day_scripts_W7-W9_20260905-20260926.md',
]
MODEL = 'claude-sonnet-4-6'


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
        reference_map = {
            'A': {'terms': ['乾六宮', '西北', '天心星', '開門', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L014'},
            'B': {'terms': ['坎一宮', '正北', '天蓬星', '休門', '大凶', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L015'},
            'C': {'terms': ['艮八宮', '東北', '天任星', '生門', '大吉'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L013'},
            'D': {'terms': ['兌七宮', '正西', '天柱星', '驚門', '小凶'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L014'},
            'E': {'terms': ['離九宮', '正南', '天英星', '景門', '中平'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L012'},
            'F': {'terms': ['震三宮', '正東', '天沖星', '傷門', '凶'], 'source': 'data/XingMen_WuXing_ShengKe.json / XMWX_L011'},
        }
        for slot in answer_slots(block, 'ABCDEF'):
            label = slot['id'].split('_', 1)[1]
            slot['minimum_cjk'] = 100
            slot['must_include'] = reference_map[label]['terms']
            slot['reference'] = reference_map[label]['source']
            slot['rule_library_type1'] = True
            slots.append(slot)
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
        slots[-1]['requires_short_window'] = True
        add_slot(slots, 'story', story.group(1), minimum_cjk=50)
        slots.extend(answer_slots(block, 'ABC'))
        return slots
    if kind == '型式五下集':
        return card_tail_slots(block)
    raise ValueError(kind)


def request_rewrite(date: str, kind: str, header: str, slots: list[dict], retry: int = 0) -> dict[str, str]:
    slot_payload = [{'id': slot['id'], 'text': slot['text'], 'minimum_cjk': slot['minimum_cjk'], 'must_include': slot.get('must_include', []), 'reference': slot.get('reference', '')} for slot in slots]
    system = '''你是繁體中文（台灣）IG 文案編輯。只改可變散文，保持原本事實、語意強度、主題、時間、圖騰、CTA、專有名詞與不確定性。\n\n依序套用：\n1. humanizer-tw：刪除套話、翻譯腔、黑話、假深刻、金句公式、短句連發戲劇腔與無源權威；不要誤殺合法台灣用語。\n2. good-writing-tw：讓句長與句尾有自然錯落，拆除真正過長或塞太多資訊的句子，但不要把全文修成節拍器。\n3. authentic-voice-editing / speak-human-tw：以可辨識的心理狀態、能量狀態和真實張力取代抽象安慰；不要新增事實、數字、經歷、來源、承諾或命理結論。\n\n這是社群文案。以冷靜、權威、透徹的「玄學破局」語氣寫作：定論明確，但不恐嚇、不命定。全文統一使用第二人稱「你」。可保留適度留白，但不要演戲、不要客服腔、不要空泛雞湯。\n\n描述克制與白描邊界：禁止細寫微觀動作、道具和背景（例如躺在床上看天花板滑手機、咖啡放涼、手拿杯子發呆、在捷運等車時修改訊息、反覆打開對話框）。把這類畫面升維為「表面在運作，心智已抽離」等心理或能量狀態。每一個 slot 最多只保留一至兩個時空／體感對頻點；不可堆疊環境背景。即使規則庫舉例「深夜刷手機」，也要改寫成夜間注意力反覆被抽走等狀態，不輸出操作鏡頭。若 `must_include` 已含一個方位與一個時段，這兩項已用盡配額，禁止再新增任何早晚、深夜、肩頸、睡眠、呼吸、胸口、腳步、手部或其他體感／時間／方位文字。\n\n不要輸出任何固定模板標籤、CTA、Hashtags、Hook 或卡片標題；但型式五下集的可變完整解讀必須輸出下方指定的粗體定論與模組標題。\n\n若內容涉及奇門或紫微：不可新增星曜、門、神、奇儀、方位、時間、吉凶、公式或個人起局結果。只有 slot 提供的 `must_include` 和 `reference` 可新增到該 slot；必須將它們表述為公開奇門資料的「對照示例」，接著立刻白話轉譯，絕不可說成已替讀者起局或確認讀者正處該局。沒有資料就寫生活層面的可觀察情景與行動。

五大型式共同適用的資訊邏輯：每一篇可變正文都要先提出該篇的核心狀態或可執行結論；再呈現讀者表面看見的狀況和底下的心理／能量拉扯；接著只留一至兩個時空或體感對頻點；最後給一項低門檻、可觀察、無結果保證的行動。型式一與型式五可以使用指定的模組標題；型式二、三、四不得自行新增模組標題或奇門術語，應把同一邏輯自然寫進其既有變數欄位。\n\n型式一的 A–F 置頂解答也適用最新版五層輸出邏輯。每個 answer_A 至 answer_F 約 100 至 150 個中文字，必須依序使用：\n**選項 X：［一句明確但非命定的主軸結論］**\n【盤象：［只使用 must_include 已核對的門、星、宮位或奇儀］】\n‧ 表面現象：［具體外在行為］\n‧ 盤象真相：［內在拉扯；立刻以「白話來說」或同義語降維］\n【時空與體感錨定】\n‧ ［已核對的方位／吉凶或可觀察的生活時段、生活感受］\n【奇門行為改運】\n‧ ［一項低門檻、可觀察的整理、溝通、休息或行程行動；不得承諾結果。］\nX 必須等於 A 至 F 對應選項。這些標題是置頂解答的可變內容，不是型式一固定模板。不可使用「注定」「必然」「一定會」「百分之百」。\n\n最新版型式五上集的對應文字是「奇門生活小貼士」，不是故事、故事卡或心理劇；其問題聚焦與 Hook 必須是具體關係／工作／金錢情境加短時間窗，生活貼士至少 50 字。\n\n型式五下集每個 card_A_tail／card_B_tail／card_C_tail 是完整解讀的可變部分，至少 300 字，必須依序、逐字採用以下五層閱讀格式：\n**選項 X：［一句明確但非命定的主軸結論］**\n【盤象：［只使用 must_include 中已核對的門、星、宮位或奇儀；不可自行補造］】\n‧ 表面現象：［具體外在行為或心理狀態］\n‧ 盤象真相：［內在拉扯或局勢本質；把術語立刻白話翻譯，明說「白話來說」或同義語］\n【時空與體感錨定】\n‧ ［只使用 must_include 的方位、時間、吉凶；或可觀察的生活感受。體感不是醫療診斷。］\n【奇門行為改運】\n‧ ［一至兩項低門檻、可觀察的整理、溝通、休息或行程行動；不可保證化解、招財、吸納吉氣或改變他人。］\n\n其中 X 必須等於該 slot 的 A、B 或 C。每一模組最多兩句，模組之間換行。首句要明確，卻不得使用「注定」「必然」「一定會」「百分之百」。不可改動任何固定模板文字。\n\n每個 slot 都必須改寫，不能原封不動回傳。對 minimum_cjk 大於零的 slot，輸出必須至少達該數量的中文字；`must_include` 內的每個字串必須逐字出現。'''
    user = {
        'date': date,
        'form': kind,
        'header_context': header,
        'slots': slot_payload,
        'task': '逐一重寫所有 slot。輸出 JSON，rewrites 內必須剛好有每個 id 一次。本輪為全量重作：每個欄位必須實質重組句法、節奏與狀態描寫，不得只替換同義詞；但不得改變主題、圖騰、時間、CTA、固定模板或可核對命理事實。' + (' 上一稿有欄位原封不動複製、未納入指定術語，或超過時空／體感錨定上限；本次每個欄位必須在不改變事實下改變句法與用字，逐一包含 must_include，且不得出現額外錨定。' if retry else ''),
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
        micro_scenes = ('躺在床上看著天花板', '咖啡放到涼了', '手拿著咖啡杯', '手拿杯子', '坐在辦公室看著螢幕')
        if any(scene in value for scene in micro_scenes):
            raise ValueError(f'Slot {slot["id"]} contains prohibited micro-scene description')
        anchors = r'西北|正北|正東|正西|正南|東北|早上|下午|晚上|深夜|肩頸|睡眠|辰時|巳時|午時|未時|申時|酉時'
        if len(set(re.findall(anchors, value))) > 2:
            raise ValueError(f'Slot {slot["id"]} contains more than two temporal or sensory anchors')
        if slot['id'].startswith('card_') or slot.get('rule_library_type1'):
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
    # 型式五上集的正文與第 2 張問題聚焦卡必須逐字使用同一個情景變數。
    if any(slot.get('requires_short_window') for slot in slots):
        scene = re.search(r'(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺', changed)
        if not scene:
            raise ValueError('Missing rewritten Type 5 upper scene')
        scene_text = scene.group(1).strip()
        if not re.search(r'(?:近|接下來|未來).{0,8}(?:一個月|一週|兩週|七天|30天)|本週|近期', scene_text):
            scene_text = '接下來一個月，' + scene_text
            changed = changed[:scene.start(1)] + scene_text + changed[scene.end(1):]
            scene = re.search(r'(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺', changed)
        changed, count = re.subn(
            r'(（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次\+ 心裡默念：)(?s:.*?)(\+ 憑第一眼直覺)',
            lambda m: m.group(1) + scene_text + m.group(2),
            changed,
            count=1,
        )
        if count != 1:
            raise ValueError('Cannot synchronize Type 5 upper visual scene')
    return changed


def rewrite(args) -> int:
    allowed_forms = {item.strip() for item in args.forms.split(',') if item.strip()}
    allowed_dates = {item.strip() for item in args.dates.split(',') if item.strip()}
    audit = []
    pending: list[tuple[Path, str, str, str, list[dict]]] = []
    for path in FILES:
        source = path.read_text(encoding='utf-8')
        for date, header, block in split_blocks(source):
            if date < '2026-08-20':
                continue
            if allowed_dates and date not in allowed_dates:
                continue
            kind = form(header)
            if allowed_forms and kind not in allowed_forms:
                continue
            slots = slots_for(block, kind)
            pending.append((path, date, header, block, slots))
    if not allowed_forms and not allowed_dates and len(pending) != 22:
        raise ValueError(f'Expected 22 unpublished scripts, got {len(pending)}')
    if (allowed_forms or allowed_dates) and not pending:
        raise ValueError(f'No scripts found for forms/dates: {sorted(allowed_forms)} / {sorted(allowed_dates)}')
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
            'slot_sha256': [
                {
                    'id': slot['id'],
                    'before': hashlib.sha256(slot['text'].encode()).hexdigest(),
                    'after': hashlib.sha256(rewritten[slot['id']].encode()).hexdigest(),
                }
                for slot in slots
            ],
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


# ── Unified governance: Playbook contract, structure, SSOT and style ─────────
STANDARD_START = '## 【五大型式文案排版輸出標準規範】'
GUIDE_TITLE = '# IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫'
STANDARD_SHA256 = 'fecec633611e00cd81ac13dcc1baaa3f28b3c06117f926319b358a09bcbbe957'
GUIDE_SHA256 = 'ad78104d4391b44463f84f6e340c1959d885eb4b685e4f62ace5357b6271eb3c'
PLAYBOOK = ROOT / 'lunas_astral_code_master_playbook.md'
SSOT = Path('/home/ubuntu/ziwei_qimen')
PUBLISHED = {'2026-08-17', '2026-08-18'}
PENDING = '【待記錄】發布後48小時：reach / 非追蹤者觸及 / profile visits / website clicks / DM / saves / shares'
RULE_SCOPE = {
    '型式一': {'mutable': ('scene', 'answer_A–F'), 'fixed': ('A–F 抽籤', '留言 CTA', '閃爍視覺')},
    '型式二': {'mutable': ('scene', 'reflection', 'action'), 'fixed': ('追蹤 CTA', '五張卡')},
    '型式三': {'mutable': ('explain',), 'fixed': ('SSOT 引文', '收藏 CTA', '五張卡')},
    '型式四': {'mutable': ('scene', 'check', 'action'), 'fixed': ('分享 CTA', '五張卡')},
    '型式五上集': {'mutable': ('scene', 'tip', 'answer_A–C'), 'fixed': ('A–C 圖騰', '留言 CTA', '五張卡')},
    '型式五下集': {'mutable': ('card_A–C'), 'fixed': ('上集承接', '圖騰', '收藏／追蹤／DM CTA', '六張卡')},
}
CTA = {
    '型式一': '下方留言 A / B / C / D / E / F 👇🏻\n【解答將於 24 小時後置頂留言區】',
    '型式二': '點擊「追蹤」隨時陪伴在你身邊～',
    '型式三': '點擊「收藏」打開命盤隨時上手\n下一期繼續拆解一個排盤小知識',
    '型式四': '點擊「分享」給朋友一起確認吧～',
    '型式五上集': '「留言」A / B / C 明天置頂留言區公佈解答 ✨\n想看後續「完整解讀」留意下一集',
    '型式五下集': '喜歡這期解讀指引的朋友\n歡迎「收藏 + 追蹤」持續領取你的解讀提示吧～\n\n若想針對個人問題進行深入解析 📩\n歡迎直接 DM 預約一對一的專屬命盤諮詢 🌙',
}
LOWER_REFS = {
    'A': {'terms': ('乾六宮', '西北', '天心星', '開門', '未時', '大吉'), 'sources': (('data/XingMen_WuXing_ShengKe.json', 'XMWX_L014'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00328'))},
    'B': {'terms': ('坎一宮', '正北', '天蓬星', '休門', '申時', '大凶', '大吉'), 'sources': (('data/XingMen_WuXing_ShengKe.json', 'XMWX_L015'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00329'))},
    'C': {'terms': ('艮八宮', '東北', '天任星', '生門', '酉時', '大吉'), 'sources': (('data/XingMen_WuXing_ShengKe.json', 'XMWX_L013'), ('data/QMDJ_ShangJuan_Consolidated.json', 'QMDJ_Auto_00330'))},
}
TYPE1_REFS = {
    'A': ('乾六宮', '西北', '天心星', '開門', '大吉'),
    'B': ('坎一宮', '正北', '天蓬星', '休門', '大凶', '大吉'),
    'C': ('艮八宮', '東北', '天任星', '生門', '大吉'),
    'D': ('兌七宮', '正西', '天柱星', '驚門', '小凶'),
    'E': ('離九宮', '正南', '天英星', '景門', '中平'),
    'F': ('震三宮', '正東', '天沖星', '傷門', '凶'),
}
MICRO_SCENES = {
    '月台與訊息鏡頭': r'捷運(?:月台|車廂)[^\n]{0,120}(?:手機|對話框|訊息)',
    '咖啡放涼鏡頭': r'咖啡[^\n]{0,80}(?:涼掉|放涼)',
    '訊息反覆操作': r'(?:對話框|訊息)[^\n]{0,100}(?:打開|刪掉|改字|滑開)',
    '廚房動作鏡頭': r'(?:外套|菜|貓|流理台|鍋)[^\n]{0,120}(?:掛上|提在手裡|蹭過|冒小泡)',
}
ANCHORS = r'西北|正北|正東|正西|正南|東北|早上|下午|晚上|深夜|肩頸|睡眠|辰時|巳時|午時|未時|申時|酉時'
RETIRED = ('視覺規範核對清單', '【每張固定版面】', '視覺設定：', '上集主題 +', '三個圖騰並排，提醒讀者回到原選項')


def cjk(text: str) -> int:
    return len(re.findall(r'[\u3400-\u9fff]', text))


def post_blocks():
    for path in FILES:
        text = path.read_text(encoding='utf-8')
        starts = list(re.finditer(r'(?m)^## (2026-\d{2}-\d{2}).*$', text))
        for i, marker in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
            yield path, marker.group(1), marker.group(0), text[marker.start():end]


def playbook_contract_issues() -> list[str]:
    text = PLAYBOOK.read_text(encoding='utf-8')
    start, guide = text.find(STANDARD_START), text.find(GUIDE_TITLE)
    issues: list[str] = []
    if start < 0 or guide <= start:
        return ['找不到五大型式固定規範或規則庫。']
    standard, rule_library = text[start:guide], text[guide:]
    if hashlib.sha256(standard.encode()).hexdigest() != STANDARD_SHA256:
        issues.append('五大型式固定規範雜湊與使用者鎖定基線不符。')
    if hashlib.sha256(rule_library.encode()).hexdigest() != GUIDE_SHA256:
        issues.append('規則庫雜湊與使用者鎖定基線不符。')
    if text.count(STANDARD_START) != 1 or text.count(GUIDE_TITLE) != 1:
        issues.append('固定規範或規則庫標題必須且只能出現一次。')
    return issues


def lower_card(block: str, label: str) -> str:
    m = re.search(rf'（[345]）{label} 選項完整解讀卡.*?：(.*?)(?=\n\n（[3456]）|\n（6）|\Z)', block, re.S)
    return m.group(1) if m else ''


def pinned_answer(block: str, label: str, labels: str) -> str:
    anchor = block.find('【置頂留言區解答｜')
    if anchor < 0:
        return ''
    region = block[anchor:]
    m = re.search(rf'(?ms)^{label}：(.*?)(?=\n\n[{'|'.join(labels)}]：|\Z)', region)
    return m.group(1) if m else ''


def five_layer_issues(date: str, text: str, label: str) -> list[str]:
    required = (f'**選項 {label}：', '【盤象：', '‧ 表面現象：', '‧ 盤象真相：', '【時空與體感錨定】', '【奇門行為改運】')
    issues = [f'{date} {label} 缺少五層模組：{item}' for item in required if item not in text]
    if re.search(r'你(?:注定|必然|一定會|百分之百)', text):
        issues.append(f'{date} {label} 使用命定論。')
    if '白話來說' not in text and '簡單說' not in text:
        issues.append(f'{date} {label} 缺少術語白話轉譯。')
    if len(set(re.findall(ANCHORS, text))) > 2:
        issues.append(f'{date} {label} 時空／體感錨定超過兩項。')
    return issues


def script_issues() -> list[str]:
    issues: list[str] = []
    posts: dict[str, tuple[str, str]] = {}
    count = 0
    for path, date, header, block in post_blocks():
        if date in PUBLISHED:
            continue
        if date < '2026-08-20':
            continue
        count += 1
        kind = form(header)
        posts[date] = (kind, block)
        if PENDING not in block:
            issues.append(f'{date} 缺少 48 小時待記錄欄位。')
        if any(token in block for token in RETIRED):
            issues.append(f'{date} 留有已廢止模板文字。')
        tags = re.search(r'(?m)^Hashtags：(.+)$', block)
        if not tags or len(re.findall(r'#[\w\u3400-\u9fff]+', tags.group(1))) != 5 or '#Lunasastralcode' not in tags.group(1):
            issues.append(f'{date} Hashtags 結構錯誤。')
        cta = re.search(r'(?ms)^(?:固定 ?)?CTA：\s*(.*?)(?=\n————————————|\n視覺分鏡描述|\n【待記錄】|\Z)', block)
        if not cta or cta.group(1).strip() != CTA[kind]:
            issues.append(f'{date} CTA 與固定模板不符。')
        for name, pattern in MICRO_SCENES.items():
            if re.search(pattern, block):
                issues.append(f'{date} 有過度微觀描繪：{name}。')
        if kind == '型式一':
            if len(re.findall(r'(?m)^🔮 [A-F]\. ', block)) != 6:
                issues.append(f'{date} 缺少 A–F 圖騰。')
            for label, terms in TYPE1_REFS.items():
                answer = pinned_answer(block, label, 'ABCDEF')
                issues.extend(f'{date} 型式一 {label} 缺少公開奇門對照：{term}。' for term in terms if term not in answer)
                issues.extend(five_layer_issues(date, answer, label))
        elif kind == '型式五上集':
            if len(re.findall(r'(?m)^🔮 [A-C]\. ', block)) != 3:
                issues.append(f'{date} 缺少 A／B／C 圖騰。')
            body_scene = re.search(r'(?ms)^心裡默念：(.*?)\n\n憑第一眼直覺', block)
            visual_scene = re.search(r'（2）問題聚焦卡（3–9 秒）：閉上眼深呼吸三次\+ 心裡默念：(.*?)\+ 憑第一眼直覺', block)
            if not body_scene or not visual_scene or body_scene.group(1).strip() != visual_scene.group(1).strip():
                issues.append(f'{date} 問題聚焦卡與正文情景不一致。')
            elif not re.search(r'(?:近|接下來|未來).{0,8}(?:一個月|一週|兩週|七天|30天)|本週|近期', body_scene.group(1)):
                issues.append(f'{date} 問題聚焦卡缺少短時間窗。')
            if '（4）貼士卡（18–22 秒）' not in block:
                issues.append(f'{date} 缺少貼士卡。')
        elif kind == '型式五下集':
            for label, spec in LOWER_REFS.items():
                card = lower_card(block, label)
                if cjk(card) < 300:
                    issues.append(f'{date} {label} 完整解讀少於 300 字。')
                issues.extend(f'{date} {label} 缺少公開奇門對照：{term}。' for term in spec['terms'] if term not in card)
                issues.extend(five_layer_issues(date, card, label))
                for relpath, line_id in spec['sources']:
                    source = SSOT / relpath
                    if not source.is_file() or line_id not in source.read_text(encoding='utf-8'):
                        issues.append(f'{date} {label} 無法反向定位 SSOT：{relpath} / {line_id}。')
        elif kind == '型式三':
            for relpath, line_id in re.findall(r'`(data/[^`]+)`，`([^`]+)`', block):
                source = SSOT / relpath
                if not source.is_file() or line_id not in source.read_text(encoding='utf-8'):
                    issues.append(f'{date} 無法反向定位 SSOT：{relpath} / {line_id}。')
    if count != 22:
        issues.append(f'未發布腳本數量錯誤：{count}。')
    upper = sorted(d for d, (kind, _) in posts.items() if kind == '型式五上集')
    lower = sorted(d for d, (kind, _) in posts.items() if kind == '型式五下集')
    for up, down in zip(upper[:5], lower):
        utopic = re.search(r'Hook：\s*【大眾奇門占卜｜(.+?)】', posts[up][1])
        normalized_lower = re.sub(r'\s+', '', posts[down][1])
        if not utopic or re.sub(r'\s+', '', utopic.group(1)) not in normalized_lower:
            issues.append(f'{down} 未承接 {up} 的窄題。')
    return issues


def audit() -> int:
    issues = playbook_contract_issues() + script_issues()
    result = {'posts_checked': 22, 'issues': issues, 'pass': not issues}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if issues else 0


def inventory() -> int:
    print(json.dumps({'root': str(ROOT), 'tool': str(Path(__file__).relative_to(ROOT)), 'rule_scope': RULE_SCOPE, 'scripts': [str(p.relative_to(ROOT)) for p in FILES]}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description='Luna scripts unified governance tool')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('audit', help='Validate Playbook contract, scripts, SSOT and cross-post structure.')
    sub.add_parser('inventory', help='Show fixed/mutable mapping and managed script files.')
    rewrite_parser = sub.add_parser('rewrite', help='Rewrite only registered mutable prose slots.')
    rewrite_parser.add_argument('--dry-run', action='store_true')
    rewrite_parser.add_argument('--forms', default='', help='Comma-separated forms; empty means all forms.')
    rewrite_parser.add_argument('--dates', default='', help='Comma-separated ISO dates; empty means all unpublished dates.')
    rewrite_parser.add_argument('--audit', type=Path, default=ROOT / 'governance/rewrite_audit.json')
    args = parser.parse_args()
    if args.command == 'audit':
        return audit()
    if args.command == 'inventory':
        return inventory()
    return rewrite(args)


if __name__ == '__main__':
    raise SystemExit(main())
