"""
Pytest suite for LLM-Compiled Rules (Implementation 2c).
Validates that the pre-generated compiled rules run deterministically and offline.
"""

import json
import pytest
from project_a.models import TaxpayerInput
from project_a.rules_llm_compiled import compute_tax_llm_compiled


@pytest.fixture(scope="module")
def sample_test_cases():
    with open("project_a/tests/test_cases.json", "r") as f:
        cases = json.load(f)
    # Return first 30 cases for rapid regression verification
    return cases[:30]


def test_compiled_rules_deterministic(sample_test_cases):
    """Verifies that compiled rules give identical output across repeated runs."""
    tc = sample_test_cases[5]
    inp = TaxpayerInput(**tc["input"])
    res1 = compute_tax_llm_compiled(inp, "2024-25")
    for _ in range(5):
        res_repeat = compute_tax_llm_compiled(inp, "2024-25")
        assert res1.old_regime.total_tax == res_repeat.old_regime.total_tax
        assert res1.new_regime.total_tax == res_repeat.new_regime.total_tax


def test_compiled_rules_zero_income():
    inp = TaxpayerInput(gross_salary=0, basic_salary=0)
    res = compute_tax_llm_compiled(inp, "2024-25")
    assert res.old_regime.total_tax == 0
    assert res.new_regime.total_tax == 0


def test_compiled_rules_fy25_rebate():
    inp = TaxpayerInput(gross_salary=1200000, basic_salary=600000)
    res = compute_tax_llm_compiled(inp, "2025-26")
    # Under FY25, taxable <= 12L has zero tax in new regime
    assert res.new_regime.total_tax == 0
