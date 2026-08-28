#!/usr/bin/env python3
"""Cross-file contract checks for independent dynamic panxiang sampling v2."""
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


class GovernanceContractV2Test(unittest.TestCase):
    def test_rule_map_and_registry_lock_the_independent_five_tuple(self) -> None:
        rule_map = json.loads((ROOT / "governance/latest_playbook_rule_map.json").read_text(encoding="utf-8"))
        registry = json.loads((ROOT / "governance/panxiang_dedup_registry.json").read_text(encoding="utf-8"))

        self.assertEqual(rule_map["playbook_sha256"], GOVERNANCE.PLAYBOOK_SHA256)
        self.assertEqual(rule_map["dynamic_panxiang"]["source_sha256"], GOVERNANCE.DYNAMIC_RULES_SHA256)
        self.assertEqual(rule_map["sentence_quality"]["version"], "3.4")
        self.assertEqual(rule_map["sentence_quality"]["style_source"], "使用者上載的占卜／療癒型社群貼文截圖及其質性分析")
        self.assertIn("第二人稱直接說話", rule_map["sentence_quality"]["style_application"])
        self.assertIn("狀態→接住→轉向→留白", rule_map["sentence_quality"]["style_application"])
        self.assertIn("禁止假共感與過度場景化", rule_map["sentence_quality"]["style_application"])
        self.assertIn("不得捏造精準情景", rule_map["sentence_quality"]["abstraction_boundary"])
        self.assertIn("不加深夜、房間、咖啡", rule_map["sentence_quality"]["abstraction_boundary"])
        self.assertIn("不得替第三人下定論", rule_map["sentence_quality"]["abstraction_boundary"])
        self.assertIn("本質上", rule_map["sentence_quality"]["ai_style_exclusions"])
        self.assertIn("假共感原因改寫", rule_map["sentence_quality"]["ai_style_exclusions"])
        self.assertEqual(
            rule_map["sentence_quality"]["categories"],
            ["成分殘缺", "搭配不當", "用詞不當", "語序混亂", "前後矛盾", "邏輯混亂"],
        )
        self.assertIn("固定模板", rule_map["sentence_quality"]["fixed_template_exclusion"])
        self.assertEqual(rule_map["dynamic_panxiang"]["input"], ["九星", "八門", "八神", "奇儀", "時辰"])
        self.assertIn("八神不由星或門推導", rule_map["dynamic_panxiang"]["sampling_rule"])
        self.assertEqual(registry["schema_version"], "2.0")
        self.assertEqual(registry["schema_source_sha256"], GOVERNANCE.DYNAMIC_RULES_SHA256)
        self.assertIn("八神", registry["decision_log"]["sampling_rule"])
        self.assertIn("不重新抽樣", registry["historical_assignment_policy"])

    def test_playbook_contract_and_direct_spirit_input_are_current(self) -> None:
        rules = GOVERNANCE.load_rules()
        playbook = (ROOT / "lunas_astral_code_master_playbook.md").read_text(encoding="utf-8")
        combo = GOVERNANCE.derive_combo(rules, "天心星", "開門", "白虎", "乙", "子")

        self.assertEqual(GOVERNANCE.current_contract_issues(), [])
        self.assertEqual(GOVERNANCE.STANDARD_SHA256, "16524110c8ce487a0ce2337331341ee12b86db17c5208528ade37ca84aa94bd0")
        self.assertIn(GOVERNANCE.SENTENCE_QUALITY_TITLE, playbook)
        self.assertIn("狀態 → 接住 → 轉向 → 留白", playbook)
        self.assertIn("術語後接白話", playbook)
        self.assertIn("IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫", playbook)
        self.assertIn("共感—重述—賦權—互動", playbook)
        self.assertIn("本次核對的 AI 寫作特徵與繁中寫作技能", playbook)
        self.assertIn("不做假真誠或諮商口吻", playbook)
        self.assertIn("不用怕沒人懂，你可以的！", playbook)
        self.assertIn("病句檢查是底線", playbook)
        self.assertIn("五組，五值均為獨立隨機抽樣輸入", playbook)
        self.assertIn("八神不由九星、八門、宮位或陰陽遁方向推導", playbook)
        self.assertEqual(combo["spirit"], "白虎")
        self.assertEqual(combo["key"], "天心星|開門|白虎|乙|子")
        self.assertNotIn("spirit_placement", combo)

    def test_aug25_theme_plan_covers_every_affected_post_with_traceable_type3_sources(self) -> None:
        posts = list(GOVERNANCE.unpublished_blocks())
        affected = [(date, header, block) for _, date, header, block in posts if date >= "2026-08-25"]
        self.assertEqual(set(GOVERNANCE.THEME_PLANS), {date for date, _, _ in affected})

        by_date = {date: (header, block) for date, header, block in affected}
        for date, header, block in affected:
            plan = GOVERNANCE.THEME_PLANS[date]
            self.assertTrue(plan["topic"])
            self.assertTrue(plan["hook"])
            self.assertEqual(plan["hook"], GOVERNANCE.hook_slot(block)["text"])
            if GOVERNANCE.form(header) == "型式三":
                self.assertIn("data_file", plan["ssot"])
                self.assertIn("source_locator", plan["ssot"])
            if GOVERNANCE.form(header) == "型式五下集":
                upper = GOVERNANCE.pair_map(posts)[date]
                self.assertEqual(plan["topic"], GOVERNANCE.THEME_PLANS[upper]["topic"])

    def test_lower_cards_have_one_option_heading(self) -> None:
        for _, date, header, block in GOVERNANCE.unpublished_blocks():
            if date < "2026-08-25" or GOVERNANCE.form(header) != "型式五下集":
                continue
            for label in "ABC":
                card = GOVERNANCE.lower_card(block, label)
                self.assertEqual(card.count(f"**選項 {label}："), 1, f"{date} {label} has duplicated option headings")

    def test_rewrite_prompt_uses_v34_rules_and_available_bulk_model(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn('MODEL = "gpt-5-mini"', source)
        self.assertIn("狀態 → 接住 → 轉向 → 留白", source)
        self.assertIn("不演場景，不補數字", source)
        self.assertNotIn("它是唯一聲音基準", source)

    def test_normalize_dynamic_option_heading_removes_repeated_label(self) -> None:
        slots = [{"id": "card_A", "label": "A", "five_layer": True}]
        rewrites = {"card_A": "選項 A：選項 A：先把想做的事放回自己手上。\n【盤象：天心星｜開門｜值符｜乙】"}
        normalized = GOVERNANCE.normalize_dynamic_option_heading(slots, rewrites)
        self.assertTrue(normalized["card_A"].startswith("**選項 A：先把想做的事放回自己手上。**"))
        self.assertNotIn("選項 A：選項 A：", normalized["card_A"])

    def test_lower_card_uses_the_approved_220_to_300_cjk_range(self) -> None:
        path, _, _, block = next(item for item in GOVERNANCE.unpublished_blocks() if GOVERNANCE.form(item[2]) == "型式五下集")
        slots = GOVERNANCE.lower_cards(block)
        self.assertEqual(path.name, "60day_scripts_W4-W9_20260817-20260925.md")
        self.assertTrue(all(slot["minimum_cjk"] == 220 for slot in slots))
        self.assertTrue(all(slot["maximum_cjk"] == 300 for slot in slots))

    def test_short_dynamic_answer_accepts_the_approved_30_to_50_cjk_range(self) -> None:
        text = "你還想問下去，但不想把心說滿。先回那個讓你想多問的人，慢慢接著把話聊下去。"
        self.assertEqual(GOVERNANCE.cjk_count(text), 33)
        self.assertEqual(GOVERNANCE.short_dynamic_issues("測試", text, "A", {}), [])

    def test_sentence_quality_detects_high_confidence_grammar_risks(self) -> None:
        self.assertEqual(
            GOVERNANCE.sentence_quality_issues("你先確認資料。再安排下一步。"),
            [],
        )
        self.assertIn("句尾懸空連詞", GOVERNANCE.sentence_quality_issues("你先確認資料，而且"))
        self.assertIn("關聯詞未配對：不但……而且／也", GOVERNANCE.sentence_quality_issues("不但先確認資料。"))
        self.assertIn("中文句內混用半形逗號", GOVERNANCE.sentence_quality_issues("你先確認資料,再安排下一步。"))
        self.assertIn("含外部結果承諾", GOVERNANCE.semantic_boundary_issues("你一定會得到想要的答案。"))
        self.assertIn("含假共感原因改寫", GOVERNANCE.semantic_boundary_issues("你不是不行，只是沒有人懂你。"))
        self.assertIn("含微觀感官場景", GOVERNANCE.semantic_boundary_issues("你深夜躺在床上看著天花板滑手機。"))
        self.assertEqual(GOVERNANCE.semantic_boundary_issues("不用怕沒人懂，你可以的！"), [])


if __name__ == "__main__":
    unittest.main()
