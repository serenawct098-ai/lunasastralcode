#!/usr/bin/env python3
"""Cross-file contract checks for the v4.1 Qimen-only dual-style Playbook."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = Path(__file__).with_name("script_governance.py")
SPEC = importlib.util.spec_from_file_location("script_governance", MODULE_PATH)
assert SPEC and SPEC.loader
GOVERNANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOVERNANCE)


class GovernanceContractV41Test(unittest.TestCase):
    def test_rule_map_locks_v41_dual_track_and_independent_five_tuple(self) -> None:
        rule_map = json.loads((ROOT / "governance/latest_playbook_rule_map.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "governance/panxiang_dedup_registry.json").read_text(encoding="utf-8"))

        self.assertEqual(rule_map["playbook_sha256"], GOVERNANCE.PLAYBOOK_SHA256)
        self.assertEqual(rule_map["writing_tracks"]["version"], "4.1")
        self.assertEqual(rule_map["writing_tracks"]["track_a"]["forms"], ["型式一", "型式五"])
        self.assertIn("盤象先行", rule_map["writing_tracks"]["track_a"]["sequence"])
        self.assertIn("不可套用塔羅", rule_map["writing_tracks"]["track_a"]["anti_portability_gate"])
        self.assertEqual(rule_map["writing_tracks"]["track_b"]["forms"], ["型式二", "型式三", "型式四"])
        self.assertTrue(rule_map["writing_tracks"]["track_b"]["scene_allowed"])
        self.assertEqual(rule_map["dynamic_panxiang"]["input"], ["九星", "八門", "八神", "奇儀", "時辰"])
        self.assertIn("八神不由星或門推導", rule_map["dynamic_panxiang"]["sampling_rule"])
        self.assertEqual(registry["schema_version"], "2.0")
        self.assertEqual(registry["schema_source_sha256"], GOVERNANCE.DYNAMIC_RULES_SHA256)

    def test_playbook_contract_is_v41_and_preserves_fixed_template_boundary(self) -> None:
        rules = GOVERNANCE.load_rules()
        playbook = (ROOT / "lunas_astral_code_master_playbook.md").read_text(encoding="utf-8")
        combo = GOVERNANCE.derive_combo(rules, "天心星", "開門", "白虎", "乙", "子")

        self.assertEqual(GOVERNANCE.current_contract_issues(), [])
        self.assertIn("Master Playbook（v4.1｜奇門專用文風雙軌制", playbook)
        self.assertIn("盤象先行", playbook)
        self.assertIn("不適用塔羅或其他占卜工具", playbook)
        self.assertIn("只可替換 `［］` 內的變數", playbook)
        self.assertIn("共同底線", playbook)
        self.assertEqual(combo["spirit"], "白虎")
        self.assertEqual(combo["key"], "天心星|開門|白虎|乙|子")
        self.assertNotIn("spirit_placement", combo)

    def test_theme_plan_covers_unpublished_posts_and_traceable_type_three_four_sources(self) -> None:
        posts = list(GOVERNANCE.unpublished_blocks())
        affected = [(date, header, block) for _, date, header, block in posts if date >= "2026-08-25"]
        self.assertEqual(set(GOVERNANCE.THEME_PLANS), {date for date, _, _ in affected})

        for date, header, block in affected:
            plan = GOVERNANCE.THEME_PLANS[date]
            self.assertTrue(plan["topic"])
            self.assertTrue(plan["hook"])
            if GOVERNANCE.form(header) != "型式二":
                self.assertEqual(plan["hook"], GOVERNANCE.hook_slot(block)["text"])
            if GOVERNANCE.form(header) == "型式三":
                self.assertIn("data_file", plan["ssot"])
                self.assertIn("source_locator", plan["ssot"])
            if GOVERNANCE.form(header) == "型式四":
                self.assertEqual(plan["ssot"]["verification_status"], "verified")
            if GOVERNANCE.form(header) == "型式五下集":
                upper = GOVERNANCE.pair_map(posts)[date]
                self.assertEqual(plan["topic"], GOVERNANCE.THEME_PLANS[upper]["topic"])

    def test_type4_is_traceable_qimen_knowledge(self) -> None:
        posts = list(GOVERNANCE.unpublished_blocks())
        type4_posts = [(date, header, block) for _, date, header, block in posts if GOVERNANCE.form(header) == "型式四"]
        self.assertEqual({date for date, _, _ in type4_posts}, set(GOVERNANCE.TYPE4_QIMEN_SSOT))
        for date, _, block in type4_posts:
            source = GOVERNANCE.TYPE4_QIMEN_SSOT[date]
            for key in ("data_file", "system_line_id", "source_locator", "original_quote"):
                self.assertIn(source[key], block)

    def test_type4_preprocessing_preserves_three_variable_lines_and_source_layers(self) -> None:
        for _, date, header, block in GOVERNANCE.unpublished_blocks():
            if GOVERNANCE.form(header) != "型式四":
                continue
            repaired = GOVERNANCE.repair_three_field_boundaries(block, "型式四")
            self.assertEqual(repaired, block, date)
            slots = GOVERNANCE.slots_for(repaired, "型式四")
            self.assertEqual([slot["id"] for slot in slots], ["scene", "check", "action"], date)

    def test_lower_cards_have_one_option_heading_and_v41_minimum_length(self) -> None:
        for _, date, header, block in GOVERNANCE.unpublished_blocks():
            if GOVERNANCE.form(header) != "型式五下集":
                continue
            for label in "ABC":
                card = GOVERNANCE.lower_card(block, label)
                self.assertEqual(card.count(f"**選項 {label}："), 1, f"{date} {label} has duplicated option headings")
        path, _, _, block = next(item for item in GOVERNANCE.unpublished_blocks() if GOVERNANCE.form(item[2]) == "型式五下集")
        self.assertTrue(path.name.startswith("60day_scripts"))
        self.assertTrue(all(slot["minimum_chars"] == 300 for slot in GOVERNANCE.lower_cards(block)))
        self.assertTrue(all(slot.get("maximum_cjk") is None for slot in GOVERNANCE.lower_cards(block)))

    def test_rewrite_prompt_uses_v41_tracks_and_keeps_common_safety_boundary(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('MODEL = "gpt-5-mini"', source)
        self.assertIn("軌道 A", source)
        self.assertIn("軌道 B", source)
        self.assertIn("盤象先行", source)
        self.assertIn("不得把一般心理測驗、塔羅牌義、牌陣、星座", source)
        self.assertIn("380–450 個非空白字元為生成目標（硬下限 300 字元）", source)
        self.assertNotIn("必須依 v3.4 文風重寫", source)
        self.assertEqual(GOVERNANCE.semantic_boundary_issues("你一定會得到想要的答案。"), ["含外部結果承諾"])
        self.assertEqual(GOVERNANCE.semantic_boundary_issues("她把門口那封信收進抽屜，沒有立刻回覆。"), [])

    def test_track_a_rejects_portable_or_unanchored_interpretation(self) -> None:
        combo = {"star": "天心星", "door": "開門", "spirit": "值符", "qi": "乙", "hour": "子", "direction": "西北", "auspice": "大吉"}
        portable = "你很敏感，也值得被理解。先相信自己的感覺。"
        anchored = "天心星配開門、值符與乙，先看西北方的安排能否落到實處；再決定要不要答應。"
        self.assertTrue(GOVERNANCE.track_a_issues(portable, combo))
        self.assertEqual(GOVERNANCE.track_a_issues(anchored, combo), [])

    def test_short_dynamic_answer_uses_v41_approximate_fifty_character_window(self) -> None:
        text = "天禽星落死門、值符顯示：先把當下事處理好，其他再等它來決定。"
        self.assertEqual(GOVERNANCE.cjk_count(text), 26)
        self.assertEqual(GOVERNANCE.short_dynamic_issues("測試", text, "A", {}), [])

    def test_normalize_dynamic_option_heading_removes_repeated_label(self) -> None:
        slots = [{"id": "card_A", "label": "A", "five_layer": True}]
        rewrites = {"card_A": "選項 A：選項 A：先把想做的事放回自己手上。\n【盤象：天心星｜開門｜值符｜乙】"}
        normalized = GOVERNANCE.normalize_dynamic_option_heading(slots, rewrites)
        self.assertTrue(normalized["card_A"].startswith("**選項 A：先把想做的事放回自己手上。**"))
        self.assertNotIn("選項 A：選項 A：", normalized["card_A"])


if __name__ == "__main__":
    unittest.main()
