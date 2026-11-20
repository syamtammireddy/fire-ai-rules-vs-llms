"""
Implementation 2b: LLM-at-Query-Time Income Tax Engine.
For every user request, sends rule text and financial facts to Gemini 2.5 Flash,
which performs the tax calculation in its reasoning context and returns structured JSON.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types

from project_a.models import TaxpayerInput, TaxResult, TaxComputation, DeductionBreakdown

load_dotenv()

# Rule text provided in prompt at query time
PROMPT_RULE_TEXT_FY2024 = """
INDIAN INCOME TAX RULES FOR SALARIED INDIVIDUALS - FY 2024-25 (AY 2025-26)

1. OLD TAX REGIME:
- Standard Deduction: ₹50,000 under Section 16(ia).
- HRA Exemption under Section 10(13A): Least of:
    (a) Actual HRA received
    (b) Rent paid minus 10% of basic salary
    (c) 50% of basic salary (if Metro: Mumbai/Delhi/Kolkata/Chennai), or 40% (Non-metro)
- Section 80C: Deductions for PF, ELSS, LIC, etc., capped at maximum ₹1,50,000.
- Section 80CCD(1B): Additional NPS employee contribution capped at maximum ₹50,000.
- Section 80D: Health insurance premium capped at ₹25,000 (self/family; ₹50,000 if senior citizen) + ₹25,000 (parents; ₹50,000 if parents senior citizen).
- Section 24(b): Interest on home loan for self-occupied house capped at ₹2,00,000.
- Tax Slabs (Below 60 years):
    Up to ₹2,50,000: Nil
    ₹2,50,001 to ₹5,00,000: 5%
    ₹5,00,001 to ₹10,00,000: 20%
    Above ₹10,00,000: 30%
- Section 87A Rebate: If taxable income <= ₹5,00,000, 100% tax rebate up to ₹12,500 (tax becomes ₹0).
- Surcharge (on tax):
    ₹50 Lakh to ₹1 Crore: 10%
    ₹1 Crore to ₹2 Crore: 15%
    ₹2 Crore to ₹5 Crore: 25%
    Above ₹5 Crore: 37%
    Marginal relief applies so that total tax + surcharge does not exceed tax at threshold + excess income above threshold.
- Health & Education Cess: 4% on (tax + surcharge).

2. NEW TAX REGIME (Section 115BAC):
- Standard Deduction: ₹75,000 under Section 16(ia).
- No exemptions or deductions allowed for HRA, 80C, 80D, 80CCD(1B), or 24(b).
- Tax Slabs:
    Up to ₹3,00,000: Nil
    ₹3,00,001 to ₹7,00,000: 5%
    ₹7,00,001 to ₹10,00,000: 10%
    ₹10,00,001 to ₹12,00,000: 15%
    ₹12,00,001 to ₹15,00,000: 20%
    Above ₹15,00,000: 30%
- Section 87A Rebate: If taxable income <= ₹7,00,000, rebate of 100% tax up to ₹25,000 (tax becomes ₹0).
- Proviso to Section 87A (Marginal relief): Tax payable cannot exceed excess taxable income over ₹7,00,000.
- Surcharge (on tax): Same as old regime, but capped at 25% above ₹2 Crores. Marginal relief applies.
- Health & Education Cess: 4% on (tax + surcharge).

Rounding: Round all final tax amounts to the nearest rupee.
"""

PROMPT_RULE_TEXT_FY2025 = """
INDIAN INCOME TAX RULES FOR SALARIED INDIVIDUALS - FY 2025-26 (AY 2026-27)
Finance Act 2025 amendments:
1. OLD REGIME: Same as FY 2024-25.
2. NEW REGIME (Finance Act 2025):
- Standard Deduction: ₹75,000.
- Revised Tax Slabs:
    Up to ₹4,00,000: Nil
    ₹4,00,001 to ₹8,00,000: 5%
    ₹8,00,001 to ₹12,00,000: 10%
    ₹12,00,001 to ₹16,00,000: 15%
    ₹16,00,001 to ₹20,00,000: 20%
    ₹20,00,001 to ₹24,00,000: 25%
    Above ₹24,00,000: 30%
- Section 87A Rebate: Full rebate for taxable income up to ₹12,00,000 (tax becomes ₹0).
- Marginal relief applies for incomes slightly above ₹12,00,000.
- Surcharge & 4% Cess same as FY 2024-25.
"""


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})


def compute_tax_llm_query(
    user_input: TaxpayerInput,
    fy: str = "2024-25",
    model: str = "gemini-3.5-flash-lite",
) -> Tuple[TaxResult, dict]:
    """
    Computes tax using Gemini at query time.
    Returns: (TaxResult, metadata_dict_with_tokens_and_latency)
    """
    client = _get_client()
    rule_text = PROMPT_RULE_TEXT_FY2025 if fy == "2025-26" else PROMPT_RULE_TEXT_FY2024

    system_instruction = (
        "You are an expert Indian income tax computation engine. "
        "Compute the exact income tax for both Old and New regimes strictly following the rules provided. "
        "Perform exact mathematical calculations step-by-step to the rupee. "
        "Return ONLY a valid JSON object matching the requested schema."
    )

    prompt = f"""
{rule_text}

TAXPAYER FINANCIAL DETAILS:
- Gross Salary: ₹{user_input.gross_salary:,.0f}
- Basic Salary: ₹{user_input.basic_salary:,.0f}
- HRA Received: ₹{user_input.hra_received:,.0f}
- Annual Rent Paid: ₹{user_input.rent_paid_annual:,.0f}
- City: {user_input.city.value}
- Age Category: {user_input.age_category.value}
- Section 80C Investment: ₹{user_input.investment_80c:,.0f}
- Section 80CCD(1B) NPS: ₹{user_input.investment_80ccd_1b:,.0f}
- Health Insurance (Self): ₹{user_input.health_insurance_self:,.0f}
- Health Insurance (Parents): ₹{user_input.health_insurance_parents:,.0f}
- Parents are Senior Citizens: {user_input.parents_are_senior_citizens}
- Home Loan Interest (24b): ₹{user_input.home_loan_interest:,.0f}

Calculate the exact tax step-by-step for both regimes and return JSON with this structure:
{{
  "old_regime": {{
    "gross_salary": number,
    "deductions": {{
      "standard_deduction": number,
      "hra_exemption": number,
      "section_80c": number,
      "section_80ccd_1b": number,
      "section_80d_self": number,
      "section_80d_parents": number,
      "home_loan_interest_24b": number,
      "total": number
    }},
    "taxable_income": number,
    "tax_on_slabs": number,
    "rebate_87a": number,
    "tax_after_rebate": number,
    "surcharge": number,
    "marginal_relief": number,
    "surcharge_after_relief": number,
    "cess": number,
    "total_tax": number
  }},
  "new_regime": {{
    "gross_salary": number,
    "deductions": {{
      "standard_deduction": number,
      "hra_exemption": 0,
      "section_80c": 0,
      "section_80ccd_1b": 0,
      "section_80d_self": 0,
      "section_80d_parents": 0,
      "home_loan_interest_24b": 0,
      "total": number
    }},
    "taxable_income": number,
    "tax_on_slabs": number,
    "rebate_87a": number,
    "tax_after_rebate": number,
    "surcharge": number,
    "marginal_relief": number,
    "surcharge_after_relief": number,
    "cess": number,
    "total_tax": number
  }},
  "recommended_regime": "Old Tax Regime" | "New Tax Regime" | "Either Regime",
  "savings": number,
  "explanation": string
}}
"""

    start_time = time.perf_counter()
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.0,
            response_mime_type="application/json",
        ),
    )
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    raw_text = response.text or "{}"
    data = json.loads(raw_text)

    # Convert to TaxResult object
    old_c = TaxComputation(**data.get("old_regime", {}))
    new_c = TaxComputation(**data.get("new_regime", {}))
    res = TaxResult(
        old_regime=old_c,
        new_regime=new_c,
        recommended_regime=data.get("recommended_regime", ""),
        savings=float(data.get("savings", 0)),
        explanation=data.get("explanation", ""),
    )

    metadata = {
        "latency_ms": elapsed_ms,
        "input_tokens": response.usage_metadata.prompt_token_count if response.usage_metadata else 0,
        "output_tokens": response.usage_metadata.candidates_token_count if response.usage_metadata else 0,
        "model": model,
    }

    return res, metadata
