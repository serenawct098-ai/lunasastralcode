#!/usr/bin/env python3
"""Regression checks for independent dynamic panxiang sampling."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("script_governance.py")
SPEC = importlib.util.spec_from_file_location("script_governance", MODULE_PATH)
assert SPEC and SPEC.loader
GOVERNANCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOVERNANCE)


class FixedRandom:
    def __init__(self, values: list[str]) -> None:
        self._values = iter(values)

    def choice(self, options: list[str]) -> str:
        value = next(self._values)
        if value not in options:
            raise AssertionError(f"{value!r} is not an allowed independent draw")
        return value


class IndependentSamplingTest(unittest.TestCase):
    def test_all_five_values_are_independent_draws(self) -> None:
        rules = GOVERNANCE.load_rules()
        rng = FixedRandom(["天心星", "開門", "白虎", "乙", "子"])

        with patch.object(GOVERNANCE.random, "SystemRandom", return_value=rng):
            combo = GOVERNANCE.generate_combo(rules, set(), set(), set())

        self.assertEqual(combo["star"], "天心星")
        self.assertEqual(combo["door"], "開門")
        self.assertEqual(combo["spirit"], "白虎")
        self.assertEqual(combo["qi"], "乙")
        self.assertEqual(combo["hour"], "子")
        self.assertNotIn("spirit_placement", combo)
        self.assertEqual(combo["key"], "天心星|開門|白虎|乙|子")


if __name__ == "__main__":
    unittest.main()
