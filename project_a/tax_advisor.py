"""
Proactive Tax Advisor Engine.
Uses Gemini to formulate actionable, personalized tax optimization strategies
based on the exact mathematical deduction headroom computed by the rule engine.
Includes deterministic rule-based fallback for offline mode.
"""

from __future__ import annotations

import os
from typing import Dict, Any, List
from dotenv import load_dotenv
from google import genai
from google.genai import types

from project_a.models import TaxpayerInput, TaxResult

load_dotenv()


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})


def generate_proactive_advice(
    user_input: TaxpayerInput,
    tax_result: TaxResult,
    model: str = "gemini-3.5-flash-lite",
) -> List[str]:
    """
    Synthesizes proactive financial recommendations on how the user can legally minimize
    their tax liability before the end of the financial year.
    """
    headroom = tax_result.deduction_headroom
    has_headroom = any(v > 0 for v in headroom.values())

    if not has_headroom:
        return ["Your deductions are already fully optimized under statutory limits."]

    # Fallback advisory generation
    fallback_advice = []
    if headroom.get("section_80ccd_1b", 0) > 0:
        nps_room = headroom["section_80ccd_1b"]
        fallback_advice.append(
            f"Invest up to ₹{nps_room:,.0f} in National Pension System (NPS) under Section 80CCD(1B) "
            f"to claim an exclusive deduction outside Section 80C."
        )
    if headroom.get("section_80c", 0) > 0:
        c_room = headroom["section_80c"]
        fallback_advice.append(
            f"Utilize your remaining ₹{c_room:,.0f} headroom under Section 80C via PPF, ELSS mutual funds, or tax-saving FDs."
        )
    if headroom.get("section_80d_self", 0) > 0 or headroom.get("section_80d_parents", 0):
        tot_d = headroom.get("section_80d_self", 0) + headroom.get("section_80d_parents", 0)
        fallback_advice.append(
            f"Take advantage of ₹{tot_d:,.0f} remaining headroom under Section 80D for preventive health checkups and health insurance."
        )

    # Attempt LLM generation for rich narrative advice
    try:
        client = _get_client()
        prompt = f"""
You are a senior Indian Chartered Accountant.
Review the following taxpayer computation:
- Gross Salary: ₹{user_input.gross_salary:,.0f}
- Current Recommendation: {tax_result.recommended_regime}
- Old Regime Tax: ₹{tax_result.old_regime.total_tax:,.0f}
- New Regime Tax: ₹{tax_result.new_regime.total_tax:,.0f}
- Unused Deduction Headroom:
  * Section 80C: ₹{headroom.get('section_80c', 0):,.0f}
  * Section 80CCD(1B) NPS: ₹{headroom.get('section_80ccd_1b', 0):,.0f}
  * Section 80D (Health): ₹{(headroom.get('section_80d_self', 0) + headroom.get('section_80d_parents', 0)):,.0f}
  * Section 24(b) Home Loan: ₹{headroom.get('home_loan_interest_24b', 0):,.0f}

Provide 2 to 3 concise, highly actionable bullet points on how this taxpayer can strategically invest before March 31 to legally reduce tax or switch to a better regime.
Keep advice grounded in statutory facts. Do not make up non-existent deductions.
"""
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                system_instruction="You provide concise, high-impact Indian tax advisory points. Return clean bullet points without markdown formatting symbols.",
            ),
        )
        if resp.text:
            lines = [line.strip("- *•").strip() for line in resp.text.strip().split("\n") if line.strip()]
            return lines[:3] if lines else fallback_advice
    except Exception:
        pass

    return fallback_advice
