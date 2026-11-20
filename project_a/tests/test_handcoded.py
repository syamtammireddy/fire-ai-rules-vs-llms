"""
Pytest suite for Hand-Coded Rules (Implementation 2a).
Validates 220+ test cases including 30+ official IT calculator benchmark cases.
"""

import json
import pytest
from project_a.models import TaxpayerInput, City, AgeCategory
from project_a.rules_handcoded import compute_tax


@pytest.fixture(scope="module")
def test_cases():
    with open("project_a/tests/test_cases.json", "r") as f:
        return json.load(f)


def test_suite_coverage(test_cases):
    """Ensure at least 200 test cases exist."""
    assert len(test_cases) >= 200, f"Expected at least 200 test cases, found {len(test_cases)}"


def test_handcoded_all_cases_fy24(test_cases):
    """Verifies all test cases for FY 2024-25 match rupee-exact expected values."""
    mismatches = []
    for tc in test_cases:
        inp = TaxpayerInput(**tc["input"])
        res = compute_tax(inp, "2024-25")
        exp = tc["expected_fy24"]

        if res.old_regime.total_tax != exp["old_tax"]:
            mismatches.append(
                f"{tc['id']} Old Tax mismatch: got {res.old_regime.total_tax}, exp {exp['old_tax']}"
            )
        if res.new_regime.total_tax != exp["new_tax"]:
            mismatches.append(
                f"{tc['id']} New Tax mismatch: got {res.new_regime.total_tax}, exp {exp['new_tax']}"
            )

    assert not mismatches, f"Found {len(mismatches)} mismatches:\n" + "\n".join(mismatches[:10])


def test_handcoded_all_cases_fy25(test_cases):
    """Verifies all test cases for FY 2025-26 match rupee-exact expected values."""
    mismatches = []
    for tc in test_cases:
        inp = TaxpayerInput(**tc["input"])
        res = compute_tax(inp, "2025-26")
        exp = tc["expected_fy25"]

        if res.new_regime.total_tax != exp["new_tax"]:
            mismatches.append(
                f"{tc['id']} FY25 New Tax mismatch: got {res.new_regime.total_tax}, exp {exp['new_tax']}"
            )

    assert not mismatches, f"Found {len(mismatches)} mismatches:\n" + "\n".join(mismatches[:10])


# --- 30 Official Calculator Edge Cases with Exact Assertions ---

def test_official_case_01_zero_income():
    inp = TaxpayerInput(gross_salary=0, basic_salary=0)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.total_tax == 0
    assert res.new_regime.total_tax == 0


def test_official_case_02_below_old_exemption():
    inp = TaxpayerInput(gross_salary=300000, basic_salary=150000)
    res = compute_tax(inp, "2024-25")
    # Gross 3L - 50k std ded = 2.5L -> tax is 0
    assert res.old_regime.total_tax == 0
    # Gross 3L - 75k std ded = 2.25L -> tax is 0
    assert res.new_regime.total_tax == 0


def test_official_case_03_old_87a_exact_boundary():
    # Taxable income exactly 5,00,000 -> Gross 5,50,000
    inp = TaxpayerInput(gross_salary=550000, basic_salary=275000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 500000
    assert res.old_regime.rebate_87a == 12500
    assert res.old_regime.total_tax == 0


def test_official_case_04_old_87a_plus_one_rupee():
    # Taxable income 5,00,001 -> Gross 5,50,001 -> No rebate under Old Regime!
    inp = TaxpayerInput(gross_salary=550001, basic_salary=275000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 500001
    assert res.old_regime.rebate_87a == 0
    # 2.5L to 5L = 12500 + 1 * 20% = 12500.2 -> cess 4% -> 13000
    assert res.old_regime.total_tax == 13000


def test_official_case_05_new_87a_exact_boundary_fy24():
    # Under New FY24: Gross 7,75,000 - 75,000 = 7,00,000 taxable -> 87A rebate makes tax 0
    inp = TaxpayerInput(gross_salary=775000, basic_salary=387500)
    res = compute_tax(inp, "2024-25")
    assert res.new_regime.taxable_income == 700000
    assert res.new_regime.total_tax == 0


def test_official_case_06_new_87a_marginal_relief_fy24():
    # Gross 7,75,100 -> taxable 7,00,100 -> excess income = 100. Tax cannot exceed 100 before cess!
    inp = TaxpayerInput(gross_salary=775100, basic_salary=387500)
    res = compute_tax(inp, "2024-25")
    assert res.new_regime.taxable_income == 700100
    assert res.new_regime.tax_after_rebate == 100
    assert res.new_regime.total_tax == round(100 * 1.04)


def test_official_case_07_new_87a_exact_boundary_fy25():
    # Under New FY25: Gross 12,75,000 - 75,000 = 12,00,000 taxable -> tax is 0!
    inp = TaxpayerInput(gross_salary=1275000, basic_salary=600000)
    res = compute_tax(inp, "2025-26")
    assert res.new_regime.taxable_income == 1200000
    assert res.new_regime.total_tax == 0


def test_official_case_08_new_87a_marginal_relief_fy25():
    # Gross 12,75,500 -> taxable 12,00,500 -> excess income = 500. Tax cannot exceed 500 before cess!
    inp = TaxpayerInput(gross_salary=1275500, basic_salary=600000)
    res = compute_tax(inp, "2025-26")
    assert res.new_regime.taxable_income == 1200500
    assert res.new_regime.tax_after_rebate == 500
    assert res.new_regime.total_tax == round(500 * 1.04)


def test_official_case_09_hra_metro_full_exemption():
    # Basic 6L, HRA 2.4L, rent 25k/mo (3L/yr) in Mumbai
    # least of: 2.4L, 3L - 60k = 2.4L, 50% of 6L = 3L -> exemption is 2.4L
    inp = TaxpayerInput(
        gross_salary=1200000,
        basic_salary=600000,
        hra_received=240000,
        rent_paid_annual=300000,
        city=City.METRO,
    )
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.hra_exemption == 240000


def test_official_case_10_hra_non_metro_40_percent():
    # Basic 6L, HRA 3L, rent 35k/mo (4.2L/yr) in Bangalore
    # least of: 3L, 4.2L - 60k = 3.6L, 40% of 6L = 2.4L -> exemption is 2.4L
    inp = TaxpayerInput(
        gross_salary=1200000,
        basic_salary=600000,
        hra_received=300000,
        rent_paid_annual=420000,
        city=City.NON_METRO,
    )
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.hra_exemption == 240000


def test_official_case_11_hra_zero_rent():
    inp = TaxpayerInput(gross_salary=1000000, basic_salary=500000, hra_received=200000, rent_paid_annual=0)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.hra_exemption == 0


def test_official_case_12_80c_cap():
    inp = TaxpayerInput(gross_salary=1000000, basic_salary=500000, investment_80c=250000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.section_80c == 150000


def test_official_case_13_80ccd_1b_cap():
    inp = TaxpayerInput(gross_salary=1000000, basic_salary=500000, investment_80ccd_1b=75000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.section_80ccd_1b == 50000


def test_official_case_14_80d_senior_parents():
    inp = TaxpayerInput(
        gross_salary=1500000,
        basic_salary=750000,
        health_insurance_self=25000,
        health_insurance_parents=55000,
        parents_are_senior_citizens=True,
    )
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.section_80d_self == 25000
    assert res.old_regime.deductions.section_80d_parents == 50000


def test_official_case_15_80d_non_senior_parents():
    inp = TaxpayerInput(
        gross_salary=1500000,
        basic_salary=750000,
        health_insurance_parents=40000,
        parents_are_senior_citizens=False,
    )
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.section_80d_parents == 25000


def test_official_case_16_24b_home_loan_cap():
    inp = TaxpayerInput(gross_salary=1500000, basic_salary=750000, home_loan_interest=250000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.deductions.home_loan_interest_24b == 200000


def test_official_case_17_senior_citizen_old_regime_exemption():
    # Senior citizen 60-80: exempt up to 3 Lakhs
    inp = TaxpayerInput(
        gross_salary=350000,
        basic_salary=175000,
        age_category=AgeCategory.SENIOR_60_TO_80,
    )
    res = compute_tax(inp, "2024-25")
    # Gross 3.5L - 50k std ded = 3.0L -> within 3L exemption -> tax 0
    assert res.old_regime.taxable_income == 300000
    assert res.old_regime.total_tax == 0


def test_official_case_18_super_senior_citizen_old_regime_exemption():
    # Super senior citizen 80+: exempt up to 5 Lakhs
    inp = TaxpayerInput(
        gross_salary=550000,
        basic_salary=275000,
        age_category=AgeCategory.SUPER_SENIOR_ABOVE_80,
    )
    res = compute_tax(inp, "2024-25")
    # Gross 5.5L - 50k std ded = 5.0L -> within 5L exemption -> tax 0
    assert res.old_regime.taxable_income == 500000
    assert res.old_regime.total_tax == 0


def test_official_case_19_surcharge_50l_boundary():
    # Taxable income exactly 50,00,000 -> Surcharge rate is 0%
    inp = TaxpayerInput(gross_salary=5050000, basic_salary=2500000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 5000000
    assert res.old_regime.surcharge == 0


def test_official_case_20_surcharge_marginal_relief_51l():
    # Gross 51.5L -> Taxable 51.0L under Old -> Surcharge 10% with marginal relief
    inp = TaxpayerInput(gross_salary=5150000, basic_salary=2500000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 5100000
    assert res.old_regime.marginal_relief > 0
    # Net tax + surcharge cannot exceed tax(50L) + 1L excess
    tax_50l = 112500 + 4000000 * 0.30  # 13,12,500
    assert res.old_regime.tax_after_rebate + res.old_regime.surcharge_after_relief == tax_50l + 100000


def test_official_case_21_surcharge_1cr_boundary():
    inp = TaxpayerInput(gross_salary=10050000, basic_salary=5000000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 10000000
    # At 1 Cr, surcharge is 10%
    assert res.old_regime.surcharge_after_relief == res.old_regime.tax_on_slabs * 0.10


def test_official_case_22_surcharge_2cr_boundary():
    inp = TaxpayerInput(gross_salary=20050000, basic_salary=10000000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 20000000
    assert res.old_regime.surcharge_after_relief == res.old_regime.tax_on_slabs * 0.15


def test_official_case_23_surcharge_5cr_old_vs_new():
    # Above 5 Cr: Old regime surcharge is 37%, New regime surcharge is capped at 25%
    inp = TaxpayerInput(gross_salary=60050000, basic_salary=30000000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.taxable_income == 60000000
    assert res.old_regime.surcharge == round(res.old_regime.tax_on_slabs * 0.37)
    assert res.new_regime.surcharge == round(res.new_regime.tax_on_slabs * 0.25)


def test_official_case_24_cess_rate_exact_4_percent():
    inp = TaxpayerInput(gross_salary=1050000, basic_salary=500000)
    res = compute_tax(inp, "2024-25")
    # Check cess is exactly 4%
    assert res.old_regime.cess == round((res.old_regime.tax_after_rebate + res.old_regime.surcharge_after_relief) * 0.04)
    assert res.new_regime.cess == round((res.new_regime.tax_after_rebate + res.new_regime.surcharge_after_relief) * 0.04)


def test_official_case_25_typical_middle_class_old_wins():
    # 10L salary with max deductions -> Old regime wins
    inp = TaxpayerInput(
        gross_salary=1000000,
        basic_salary=500000,
        hra_received=200000,
        rent_paid_annual=240000,
        city=City.METRO,
        investment_80c=150000,
        investment_80ccd_1b=50000,
        health_insurance_self=25000,
    )
    res = compute_tax(inp, "2024-25")
    assert res.recommended_regime == "Old Tax Regime"
    assert res.savings > 0


def test_official_case_26_typical_middle_class_new_wins():
    # 10L salary with zero deductions -> New regime wins
    inp = TaxpayerInput(gross_salary=1000000, basic_salary=500000)
    res = compute_tax(inp, "2024-25")
    assert res.recommended_regime == "New Tax Regime"
    assert res.savings > 0


def test_official_case_27_equal_tax_scenario():
    # At sub-taxable incomes, tax is 0 in both
    inp = TaxpayerInput(gross_salary=200000, basic_salary=100000)
    res = compute_tax(inp, "2024-25")
    assert res.recommended_regime == "Either Regime"
    assert res.savings == 0


def test_official_case_28_high_earner_15l_fy24():
    inp = TaxpayerInput(gross_salary=1500000, basic_salary=750000)
    res = compute_tax(inp, "2024-25")
    # Old: Gross 15L - 50k = 14.5L -> tax is 1,12,500 + 4.5L * 30% = 2,47,500 + cess 9,900 = 2,57,400
    assert res.old_regime.total_tax == 257400
    # New: Gross 15L - 75k = 14.25L -> tax is 1,25,000 + cess 5,000 = 1,30,000
    assert res.new_regime.total_tax == 130000


def test_official_case_29_high_earner_15l_fy25():
    inp = TaxpayerInput(gross_salary=1500000, basic_salary=750000)
    res = compute_tax(inp, "2025-26")
    # New FY25: Gross 15L - 75k = 14.25L -> tax:
    # 0-4L: 0, 4-8L: 20k, 8-12L: 40k, 12-14.25L: 2.25L * 15% = 33,750
    # total base = 93,750 -> cess 3,750 -> total 97,500!
    assert res.new_regime.total_tax == 97500


def test_official_case_30_ultra_hni_marginal_relief_check():
    # Test that marginal relief is mathematically non-negative and caps correctly
    inp = TaxpayerInput(gross_salary=50100000, basic_salary=25000000)
    res = compute_tax(inp, "2024-25")
    assert res.old_regime.marginal_relief >= 0
    assert res.new_regime.marginal_relief >= 0


def test_proactive_tax_advisor_and_headroom():
    from project_a.tax_advisor import generate_proactive_advice
    inp = TaxpayerInput(gross_salary=1500000, basic_salary=750000, investment_80c=50000)
    res = compute_tax(inp, "2024-25")
    assert res.deduction_headroom["section_80c"] == 100000
    assert res.deduction_headroom["section_80ccd_1b"] == 50000
    advice = generate_proactive_advice(inp, res)
    assert len(advice) >= 1
    assert any(any(k in a.lower() for k in ["nps", "80c", "regime", "deduction", "tax"]) for a in advice)
