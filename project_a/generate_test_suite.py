"""
Generates the comprehensive test suite for Project A:
1. 200+ mathematical test cases (tests/test_cases.json) with exact expected values for FY 2024-25 and FY 2025-26.
2. 50 varied plain-language user descriptions (tests/test_nlp_cases.json).
"""

import json
from project_a.models import TaxpayerInput, City, AgeCategory
from project_a.rules_handcoded import compute_tax


def generate_mathematical_cases():
    cases = []
    tc_id = 1

    # 1. Zero and Sub-Taxable Incomes
    for gross in [0, 100_000, 200_000, 250_000, 300_000, 350_000]:
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "sub_taxable",
            "description": f"Low salary ₹{gross:,} with standard basic",
            "input": TaxpayerInput(gross_salary=gross, basic_salary=gross * 0.5).model_dump(),
        })
        tc_id += 1

    # 2. Slab boundaries and ±₹1 edge cases for Old & New Regimes
    boundaries = [
        250_000, 300_000, 500_000, 700_000, 1_000_000, 1_200_000, 1_500_000,
        2_000_000, 2_400_000, 5_000_000, 10_000_000, 20_000_000, 50_000_000
    ]
    for b in boundaries:
        for offset in [-1, 0, 1]:
            val = b + offset
            if val > 0:
                cases.append({
                    "id": f"TC_{tc_id:03d}",
                    "category": "slab_boundary_offset",
                    "description": f"Boundary boundary ₹{b:,} with offset ₹{offset:+d} = ₹{val:,}",
                    "input": TaxpayerInput(gross_salary=val, basic_salary=val * 0.5).model_dump(),
                })
                tc_id += 1

    # 3. Section 87A Rebate exact boundaries (accounting for standard deductions)
    # Under Old: Taxable 500,000 -> Gross = 550,000
    # Under New: Taxable 700,000 -> Gross = 775,000 (FY 2024-25)
    # Under New: Taxable 1,200,000 -> Gross = 1,275,000 (FY 2025-26)
    for g in [
        549_999, 550_000, 550_001,
        774_999, 775_000, 775_001, 775_100, 780_000, 800_000,
        1_274_999, 1_275_000, 1_275_001, 1_280_000,
    ]:
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "rebate_87a_edge",
            "description": f"Rebate 87A transition around gross ₹{g:,}",
            "input": TaxpayerInput(gross_salary=g, basic_salary=g * 0.5).model_dump(),
        })
        tc_id += 1

    # 4. HRA Exemption edge cases (Metro vs Non-Metro, varied rent)
    hra_scenarios = [
        # (gross, basic, hra_rec, rent_annual, city, desc)
        (800_000, 400_000, 160_000, 240_000, City.METRO, "HRA Metro rent > 10% basic"),
        (800_000, 400_000, 160_000, 240_000, City.NON_METRO, "HRA Non-Metro rent > 10% basic"),
        (1_200_000, 600_000, 240_000, 60_000, City.METRO, "Rent exactly 10% basic (exemption 0)"),
        (1_200_000, 600_000, 240_000, 50_000, City.METRO, "Rent < 10% basic (exemption 0)"),
        (1_500_000, 750_000, 300_000, 600_000, City.METRO, "Very high rent (HRA capped by actual HRA)"),
        (1_500_000, 750_000, 500_000, 600_000, City.NON_METRO, "High HRA capped by 40% basic"),
        (900_000, 450_000, 180_000, 0, City.METRO, "Zero rent paid (no exemption)"),
    ]
    for gross, basic, hra_rec, rent, city, desc in hra_scenarios:
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "hra_exemption",
            "description": desc,
            "input": TaxpayerInput(
                gross_salary=gross,
                basic_salary=basic,
                hra_received=hra_rec,
                rent_paid_annual=rent,
                city=city,
            ).model_dump(),
        })
        tc_id += 1

    # 5. Section 80C, 80CCD(1B), 80D, 24b Deductions combinations
    deduction_tests = [
        (1_000_000, 500_000, 150_000, 0, 0, 0, False, 0, "Full 80C only"),
        (1_000_000, 500_000, 200_000, 0, 0, 0, False, 0, "80C excess (capped at 1.5L)"),
        (1_200_000, 600_000, 150_000, 50_000, 0, 0, False, 0, "Full 80C + 80CCD(1B)"),
        (1_200_000, 600_000, 150_000, 100_000, 0, 0, False, 0, "80CCD(1B) excess (capped at 50k)"),
        (1_500_000, 750_000, 150_000, 50_000, 25_000, 25_000, False, 0, "80C + 80CCD + 80D non-senior parents"),
        (1_500_000, 750_000, 150_000, 50_000, 25_000, 50_000, True, 0, "80D senior citizen parents (50k limit)"),
        (1_500_000, 750_000, 150_000, 50_000, 30_000, 60_000, True, 0, "80D over-claims (capped)"),
        (1_800_000, 900_000, 150_000, 50_000, 25_000, 50_000, True, 200_000, "Max all deductions including 24b"),
        (1_800_000, 900_000, 150_000, 50_000, 25_000, 50_000, True, 300_000, "Home loan interest excess capped at 2L"),
    ]
    for gross, basic, c80, ccd, d_self, d_par, par_sen, hl, desc in deduction_tests:
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "deduction_combinations",
            "description": desc,
            "input": TaxpayerInput(
                gross_salary=gross,
                basic_salary=basic,
                investment_80c=c80,
                investment_80ccd_1b=ccd,
                health_insurance_self=d_self,
                health_insurance_parents=d_par,
                parents_are_senior_citizens=par_sen,
                home_loan_interest=hl,
            ).model_dump(),
        })
        tc_id += 1

    # 6. Age Categories under Old Regime
    for age in [AgeCategory.BELOW_60, AgeCategory.SENIOR_60_TO_80, AgeCategory.SUPER_SENIOR_ABOVE_80]:
        for gross in [280_000, 350_000, 480_000, 550_000, 800_000]:
            cases.append({
                "id": f"TC_{tc_id:03d}",
                "category": "age_exemptions",
                "description": f"Salary ₹{gross:,} for age category {age.value}",
                "input": TaxpayerInput(
                    gross_salary=gross,
                    basic_salary=gross * 0.5,
                    age_category=age,
                ).model_dump(),
            })
            tc_id += 1

    # 7. Surcharge & Marginal Relief Edge Cases
    surch_incomes = [
        # Around 50L (10% surcharge starts)
        5_000_000, 5_050_000, 5_100_000, 5_200_000, 5_500_000, 6_000_000, 7_500_000,
        # Around 1 Cr (15% surcharge starts)
        10_000_000, 10_050_000, 10_100_000, 10_200_000, 11_000_000, 15_000_000,
        # Around 2 Cr (25% surcharge starts)
        20_000_000, 20_050_000, 20_100_000, 20_200_000, 25_000_000, 35_000_000,
        # Around 5 Cr (37% in Old, capped at 25% in New)
        50_000_000, 50_050_000, 50_100_000, 50_200_000, 60_000_000, 100_000_000,
    ]
    for g in surch_incomes:
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "surcharge_and_marginal_relief",
            "description": f"Surcharge test case at gross salary ₹{g:,}",
            "input": TaxpayerInput(gross_salary=g, basic_salary=g * 0.4).model_dump(),
        })
        tc_id += 1

    # 8. Diverse Realistic Salaries across typical salaried brackets
    salaries = [
        450_000, 600_000, 650_000, 720_000, 850_000, 950_000, 1_050_000, 1_150_000,
        1_250_000, 1_350_000, 1_450_000, 1_600_000, 1_750_000, 1_900_000, 2_100_000,
        2_250_000, 2_500_000, 2_800_000, 3_000_000, 3_500_000, 4_000_000, 4_500_000
    ]
    for s in salaries:
        # Without deductions
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "realistic_salaries_zero_deductions",
            "description": f"Standard salaried taxpayer earning ₹{s:,} with no extra deductions",
            "input": TaxpayerInput(gross_salary=s, basic_salary=s * 0.5).model_dump(),
        })
        tc_id += 1

        # With typical deductions (80C 1.5L, health 25k, rent 15-30k/mo)
        rent_mo = min(40_000, int(s * 0.20 / 12))
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "realistic_salaries_with_deductions",
            "description": f"Salaried taxpayer earning ₹{s:,} with typical 80C and rent ₹{rent_mo:,}/mo in Bangalore",
            "input": TaxpayerInput(
                gross_salary=s,
                basic_salary=s * 0.5,
                hra_received=s * 0.20,
                rent_paid_annual=rent_mo * 12,
                city=City.NON_METRO,
                investment_80c=150_000,
                health_insurance_self=25_000,
            ).model_dump(),
        })
        tc_id += 1

    # Ensure total >= 200 cases
    while len(cases) < 220:
        extra_val = 500_000 + len(cases) * 50_000
        cases.append({
            "id": f"TC_{tc_id:03d}",
            "category": "scaled_fill",
            "description": f"Incremental test case ₹{extra_val:,}",
            "input": TaxpayerInput(
                gross_salary=extra_val,
                basic_salary=extra_val * 0.45,
                investment_80c=min(150_000, extra_val * 0.1),
            ).model_dump(),
        })
        tc_id += 1

    # Compute expected results for all cases under FY 2024-25 and FY 2025-26
    for c in cases:
        inp = TaxpayerInput(**c["input"])
        res24 = compute_tax(inp, "2024-25")
        res25 = compute_tax(inp, "2025-26")

        c["expected_fy24"] = {
            "old_tax": res24.old_regime.total_tax,
            "new_tax": res24.new_regime.total_tax,
            "recommended": res24.recommended_regime,
            "savings": res24.savings,
            "old_taxable": res24.old_regime.taxable_income,
            "new_taxable": res24.new_regime.taxable_income,
            "old_marginal_relief": res24.old_regime.marginal_relief,
            "new_marginal_relief": res24.new_regime.marginal_relief,
        }
        c["expected_fy25"] = {
            "old_tax": res25.old_regime.total_tax,
            "new_tax": res25.new_regime.total_tax,
            "recommended": res25.recommended_regime,
            "savings": res25.savings,
            "new_taxable": res25.new_regime.taxable_income,
        }

    return cases


def generate_nlp_cases():
    return [
        # --- Formal English (10 cases) ---
        {
            "id": "NLP_01",
            "style": "formal_english",
            "text": "My gross annual salary is Rs 12,00,000. Basic salary is Rs 6,00,000, and I receive Rs 2,40,000 as HRA. I live in Mumbai and pay Rs 25,000 per month as rent. I have invested Rs 1,50,000 in PPF and ELSS under Section 80C.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1200000, "city": "metro", "investment_80c": 150000},
            "should_clarify": False,
        },
        {
            "id": "NLP_02",
            "style": "formal_english",
            "text": "I am a salaried employee in Delhi with a total CTC of 18,00,000 INR. My basic is 9,00,000 INR and HRA is 3,60,000 INR. Annual rent paid is 3,00,000 INR. I contribute 50,000 to NPS under 80CCD(1B) and pay 25,000 for health insurance for myself.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1800000, "investment_80ccd_1b": 50000},
            "should_clarify": False,
        },
        {
            "id": "NLP_03",
            "style": "formal_english",
            "text": "Gross compensation is 24 Lakhs per annum. Basic salary is 12 Lakhs. I do not stay in rented accommodation. I have a home loan for a self-occupied flat and paid Rs 2,00,000 interest this year. Also invested 1.5 Lakhs in Section 80C.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 2400000, "home_loan_interest": 200000},
            "should_clarify": False,
        },
        {
            "id": "NLP_04",
            "style": "formal_english",
            "text": "Annual salary is 7,50,000 INR. I have no investments or rent expenses. Age is 32 years.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 750000, "investment_80c": 0},
            "should_clarify": False,
        },
        {
            "id": "NLP_05",
            "style": "formal_english",
            "text": "My CTC is 35 Lakhs. Basic pay is 14 Lakhs. I stay in Kolkata paying 35,000 monthly rent. HRA is 4.5 Lakhs. I invest 1.5 Lakhs in 80C and pay 25,000 health insurance for my parents who are senior citizens aged 65.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 3500000, "parents_are_senior_citizens": True},
            "should_clarify": False,
        },
        {
            "id": "NLP_06",
            "style": "formal_english",
            "text": "I am a retired senior citizen, age 68, receiving pension salary of Rs 6,50,000. No rent, 80C investments of Rs 80,000.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 650000, "age_category": "senior_60_to_80"},
            "should_clarify": False,
        },
        {
            "id": "NLP_07",
            "style": "formal_english",
            "text": "Gross salary is 52,00,000 per annum, basic is 26,00,000. Residing in Chennai with rent paid 40,000/month, HRA 6,00,000. 80C is 1,50,000.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 5200000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_08",
            "style": "formal_english",
            "text": "Gross pay 4,80,000 per annum. No rent, no investments. Below 60 years old.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 480000},
            "should_clarify": False,
        },
        {
            "id": "NLP_09",
            "style": "formal_english",
            "text": "Total remuneration: Rs 15,00,000. Basic: Rs 7,50,000. Paying 1,80,000 rent in Pune. HRA component: 2,00,000. Health insurance premium paid: 20,000 for self.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1500000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_10",
            "style": "formal_english",
            "text": "Total gross income from salary is Rs 9,00,000. Basic is 4,50,000. HRA is 1,50,000. Paying rent 15,000 per month in Hyderabad. Section 80C is 1,20,000.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 900000, "city": "non_metro"},
            "should_clarify": False,
        },

        # --- Casual English (10 cases) ---
        {
            "id": "NLP_11",
            "style": "casual_english",
            "text": "Hey, earning 10 lpa in Bengaluru. Basic is 5L, HRA 2L, paying 18k rent pm. Put 1.5L in ELSS.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1000000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_12",
            "style": "casual_english",
            "text": "package is 16 LPA, basic 8L, HRA 2.4L. Renting in Gurgaon for 22k a month. Maxed out 80c and put 50k in nps.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1600000, "investment_80c": 150000},
            "should_clarify": False,
        },
        {
            "id": "NLP_13",
            "style": "casual_english",
            "text": "make around 22 lakhs, basic is 11L, living in mumbai paying 30k rent. HRA is 3.5L. Health insurance 20k self.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 2200000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_14",
            "style": "casual_english",
            "text": "Salary 8.5 lakhs gross. Basic is 4.25L. No rent, living with parents. 80c is 1.5 lakhs.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 850000, "rent_paid_annual": 0},
            "should_clarify": False,
        },
        {
            "id": "NLP_15",
            "style": "casual_english",
            "text": "Just got an offer of 14 LPA. Basic 7L, HRA 2L, rent 20k pm in Noida. Also pay 25k health insurance.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1400000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_16",
            "style": "casual_english",
            "text": "making 30 lakhs ctc, basic 15L, hra 4L. Paying 40k rent in Delhi. Home loan interest 1.8L.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 3000000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_17",
            "style": "casual_english",
            "text": "Earning 6.5 lakhs, single, no rent, no investments. What tax do I pay?",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 650000},
            "should_clarify": False,
        },
        {
            "id": "NLP_18",
            "style": "casual_english",
            "text": "Salary 40 LPA, basic 20 LPA, HRA 6 LPA. Paying rent 60k/month in Mumbai. 80c 1.5L, 80d 25k self.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 4000000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_19",
            "style": "casual_english",
            "text": "Earning 11 LPA in Ahmedabad. Basic 5.5L, HRA 1.8L. Rent 15k pm. 80C 1.5L, NPS 50k.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1100000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_20",
            "style": "casual_english",
            "text": "CTC 7 lakhs. Basic 3.5L. No rent. 80C investments 1 lakh. How much tax?",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 700000, "investment_80c": 100000},
            "should_clarify": False,
        },

        # --- Hinglish (10 cases) ---
        {
            "id": "NLP_21",
            "style": "hinglish",
            "text": "Mera salary 12 lakh hai saal ka, basic salary 6 lakh hai, aur Mumbai me rehta hu jaha 25000 per month rent deta hu. HRA 2 lakh milta hai. 80C me 1.5 lakh invest kiya hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1200000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_22",
            "style": "hinglish",
            "text": "Bhai CTC 15 LPA hai, basic 7.5L. Bangalore me hu, rent 20k per month deta hu, HRA 2.2L hai. 80c pura 1.5 lakh kiya hai aur NPS me 50k dala hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1500000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_23",
            "style": "hinglish",
            "text": "Meri annual income 8 lakh hai. Basic 4 lakh. Rent nahi deta, ghar apna hai. PPF me 1 lakh dala hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 800000, "rent_paid_annual": 0},
            "should_clarify": False,
        },
        {
            "id": "NLP_24",
            "style": "hinglish",
            "text": "Mera package 20 lakh hai, basic 10 lakh. Delhi me rehta hu aur rent 30k pm deta hu. HRA 3 lakh milta hai. Mediclaim 25k khud ka.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 2000000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_25",
            "style": "hinglish",
            "text": "Annual package 9.5 lakh, basic 4.75 lakh, Pune me rent 16000 pm deta hu, HRA 1.5 lakh. 80C me 1.5 lakh aur health insurance 20000.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 950000, "city": "non_metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_26",
            "style": "hinglish",
            "text": "Saal ka 18 lakh kamata hu, basic 9L. Hyderabad me rent 22000 per month, HRA 2.5L. Papa mummy senior citizen hain unka health insurance 45000 bhara.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1800000, "parents_are_senior_citizens": True},
            "should_clarify": False,
        },
        {
            "id": "NLP_27",
            "style": "hinglish",
            "text": "Gross salary 5 lakh 50 thousand hai. Basic 2.75 lakh. Koi rent nahi deta, 80c me kuch nahi hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 550000},
            "should_clarify": False,
        },
        {
            "id": "NLP_28",
            "style": "hinglish",
            "text": "Mera 25 LPA package hai, basic 12.5 lakh, Chennai me rent 28k pm, HRA 3L. Home loan interest 2 lakh bharta hu.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 2500000, "city": "metro"},
            "should_clarify": False,
        },
        {
            "id": "NLP_29",
            "style": "hinglish",
            "text": "Main 7.2 lakh kamata hu. Basic 3.6 lakh. Koi investment nahi hai aur rent bhi nahi hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 720000},
            "should_clarify": False,
        },
        {
            "id": "NLP_30",
            "style": "hinglish",
            "text": "Salary 14 lakh hai. Basic 7 lakh, HRA 2.5 lakh. Kolkata me rent 20k deta hu. 80C me 1.5L invest kiya hai.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1400000, "city": "metro"},
            "should_clarify": False,
        },

        # --- Incomplete Cases (10 cases) - MUST trigger clarifying questions ---
        {
            "id": "NLP_31",
            "style": "incomplete",
            "text": "I earn 8 lakhs.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 800000},
            "should_clarify": True,
            "clarify_topic": "basic_salary_or_deductions",
        },
        {
            "id": "NLP_32",
            "style": "incomplete",
            "text": "My salary is 15 LPA and I pay 25k rent per month.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 1500000},
            "should_clarify": True,
            "clarify_topic": "city_and_hra_missing_for_rent",
        },
        {
            "id": "NLP_33",
            "style": "incomplete",
            "text": "I pay 30,000 rent in Mumbai. How much tax do I save?",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "gross_salary_missing",
        },
        {
            "id": "NLP_34",
            "style": "incomplete",
            "text": "Mera rent 20000 hai aur 80C me 1.5 lakh lagaya hai.",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "gross_salary_missing",
        },
        {
            "id": "NLP_35",
            "style": "incomplete",
            "text": "Gross salary is 12 lakhs. I pay health insurance for my parents of 40,000.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 1200000},
            "should_clarify": True,
            "clarify_topic": "parents_age_for_80d",
        },
        {
            "id": "NLP_36",
            "style": "incomplete",
            "text": "I earn good money in Bangalore, around 20 LPA, what should I choose?",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 2000000},
            "should_clarify": True,
            "clarify_topic": "rent_or_deduction_details",
        },
        {
            "id": "NLP_37",
            "style": "incomplete",
            "text": "Paying rent in Delhi and have home loan.",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "all_amounts_missing",
        },
        {
            "id": "NLP_38",
            "style": "incomplete",
            "text": "Salary 10 LPA. HRA is 2 LPA.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 1000000},
            "should_clarify": True,
            "clarify_topic": "rent_paid_and_city",
        },
        {
            "id": "NLP_39",
            "style": "incomplete",
            "text": "Retired senior citizen with pension. Paid 50k medical bills.",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "gross_pension_salary_missing",
        },
        {
            "id": "NLP_40",
            "style": "incomplete",
            "text": "CTC 50 LPA.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 5000000},
            "should_clarify": True,
            "clarify_topic": "breakdown_and_investments_missing",
        },

        # --- Contradictory / Edge Cases (10 cases) ---
        {
            "id": "NLP_41",
            "style": "contradictory_or_edge",
            "text": "I earn 12 Lakhs and I have invested Rs 3,00,000 under Section 80C in various mutual funds.",
            "expected_complete": True,  # Parser caps 80C at 1.5L and warns
            "expected_fields": {"gross_salary": 1200000, "investment_80c": 150000},
            "should_clarify": True,
            "clarify_topic": "80c_cap_exceeded",
        },
        {
            "id": "NLP_42",
            "style": "contradictory_or_edge",
            "text": "Gross salary is 10 lakhs but my basic salary is 12 lakhs.",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "basic_cannot_exceed_gross",
        },
        {
            "id": "NLP_43",
            "style": "contradictory_or_edge",
            "text": "My CTC is -500,000 and I pay rent.",
            "expected_complete": False,
            "expected_fields": {},
            "should_clarify": True,
            "clarify_topic": "negative_salary_invalid",
        },
        {
            "id": "NLP_44",
            "style": "contradictory_or_edge",
            "text": "I make 15 LPA. I put 1 Lakh in NPS under 80CCD(1B).",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1500000, "investment_80ccd_1b": 50000},
            "should_clarify": True,
            "clarify_topic": "nps_capped_at_50k",
        },
        {
            "id": "NLP_45",
            "style": "contradictory_or_edge",
            "text": "Earning 20 LPA, basic 10 LPA. Paying 30k rent in Bangalore which is a metro city.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 2000000, "city": "non_metro"},
            "should_clarify": True,
            "clarify_topic": "bangalore_is_legally_non_metro",
        },
        {
            "id": "NLP_46",
            "style": "contradictory_or_edge",
            "text": "Gross salary 18 LPA. Home loan interest paid for self-occupied flat is Rs 4,50,000.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1800000, "home_loan_interest": 200000},
            "should_clarify": True,
            "clarify_topic": "24b_capped_at_200k",
        },
        {
            "id": "NLP_47",
            "style": "contradictory_or_edge",
            "text": "My salary is 6 LPA and my 80C is 1.5L, 80D is 50k, HRA is 2L, total deductions 8 Lakhs exceeding my salary.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 600000},
            "should_clarify": False,
        },
        {
            "id": "NLP_48",
            "style": "contradictory_or_edge",
            "text": "I am 105 years old and earn 12 LPA pension.",
            "expected_complete": True,
            "expected_fields": {"gross_salary": 1200000, "age_category": "super_senior_above_80"},
            "should_clarify": False,
        },
        {
            "id": "NLP_49",
            "style": "contradictory_or_edge",
            "text": "I live in Mumbai and pay rent 25k/month, but my employer gives 0 HRA.",
            "expected_complete": True,
            "expected_fields": {"hra_received": 0, "rent_paid_annual": 300000},
            "should_clarify": False,
        },
        {
            "id": "NLP_50",
            "style": "contradictory_or_edge",
            "text": "Gross salary 14 LPA, basic 7 LPA. Rent paid in London £2000/month.",
            "expected_complete": False,
            "expected_fields": {"gross_salary": 1400000},
            "should_clarify": True,
            "clarify_topic": "foreign_rent_ineligible_under_indian_it_act",
        },
    ]


if __name__ == "__main__":
    math_cases = generate_mathematical_cases()
    with open("project_a/tests/test_cases.json", "w") as f:
        json.dump(math_cases, f, indent=2)
    print(f"Generated {len(math_cases)} mathematical test cases in project_a/tests/test_cases.json")

    nlp_cases = generate_nlp_cases()
    with open("project_a/tests/test_nlp_cases.json", "w") as f:
        json.dump(nlp_cases, f, indent=2)
    print(f"Generated {len(nlp_cases)} plain-language cases in project_a/tests/test_nlp_cases.json")
