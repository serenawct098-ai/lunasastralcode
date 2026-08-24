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
        self.assertEqual(rule_map["sentence_quality"]["version"], "3.2")
        self.assertEqual(rule_map["sentence_quality"]["style_source"], "使用者上載文章的語氣、用詞、句長與節奏")
        self.assertIn("第二人稱直呼", rule_map["sentence_quality"]["style_application"])
        self.assertIn("不得捏造精準情景", rule_map["sentence_quality"]["abstraction_boundary"])
        self.assertIn("本質上", rule_map["sentence_quality"]["ai_style_exclusions"])
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
        self.assertIn("IG 爆款奇門遁甲大眾占卜：文案寫作指南與規則庫", playbook)
        self.assertIn("共感—重述—賦權—互動", playbook)
        self.assertIn("使用者上載文章是可變文案的唯一聲音基準", playbook)
        self.assertIn("常見 AI 口頭禪", playbook)
        self.assertIn("病句檢查是底線", playbook)
        self.assertIn("五組，五值均為獨立隨機抽樣輸入", playbook)
        self.assertIn("八神不由九星、八門、宮位或陰陽遁方向推導", playbook)
        self.assertEqual(combo["spirit"], "白虎")
        self.assertEqual(combo["key"], "天心星|開門|白虎|乙|子")
        self.assertNotIn("spirit_placement", combo)

    def test_sentence_quality_detects_high_confidence_grammar_risks(self) -> None:
        self.assertEqual(
            GOVERNANCE.sentence_quality_issues("你先確認資料。再安排下一步。"),
            [],
        )
        self.assertIn("句尾懸空連詞", GOVERNANCE.sentence_quality_issues("你先確認資料，而且"))
        self.assertIn("關聯詞未配對：不但……而且／也", GOVERNANCE.sentence_quality_issues("不但先確認資料。"))
        self.assertIn("中文句內混用半形逗號", GOVERNANCE.sentence_quality_issues("你先確認資料,再安排下一步。"))
        self.assertIn("含外部結果承諾", GOVERNANCE.semantic_boundary_issues("你一定會得到想要的答案。"))


if __name__ == "__main__":
    unittest.main()
