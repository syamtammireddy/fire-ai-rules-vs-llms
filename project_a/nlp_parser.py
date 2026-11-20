"""
Task 3: Plain-Language Input Parser.
Turns free-text user descriptions (English, Hinglish, casual, incomplete, contradictory)
into structured TaxpayerInput objects.
When information is missing or ambiguous, the system asks clarifying questions instead of guessing.
Includes graceful fallback for rate-limited / offline environments.
"""

from __future__ import annotations

import json
import os
import re
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

from project_a.models import (
    TaxpayerInput,
    ClarifyingQuestion,
    NLPParseResult,
    City,
    AgeCategory,
)

load_dotenv()


def _get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in environment.")
    return genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})


PARSER_SYSTEM_INSTRUCTION = """
You are an expert income-tax assistant that extracts structured financial details from a salaried taxpayer's free-text description.
The taxpayer may write in English, Hindi/Hinglish (e.g. "mera salary 12 lakh hai", "delhi me rehta hu", "rent deta hu"), or casual slang ("15 lpa", "50k pm", "30k rent").

CRITICAL RULES:
1. DO NOT GUESS missing essential numbers. If a critical field is not specified or ambiguous, you MUST generate a clarifying question.
   Essential fields:
   - gross_salary: MUST be known. If absent or ambiguous ("I earn good money"), ask!
   - Bare salary inputs: If the user provides ONLY a salary amount (e.g. "I earn 8 lakhs") without stating whether they live in a rented home or have tax-saving investments (80C, 80D, NPS), ask whether they pay rent or have any deductions under 80C/80D so the best regime can be accurately recommended.
   - Default age_category to 'below_60' unless the user mentions being a senior citizen (60+) or pensioner. Do NOT ask clarifying questions about age unless retirement or senior status is hinted at.
   - Do NOT ask about optional deductions (80D, NPS, home loan) if the user has already specified salary, rent, and 80C. Only ask if essential information needed for the stated facts is missing.
2. Conversion rules:
   - "LPA" / "Lakhs" / "L" = 100,000 (e.g., 12 LPA = 1,200,000).
   - "K" / "thousand" = 1,000 (e.g., 25k = 25,000).
   - "per month" / "pm" for rent: multiply by 12 to get annual rent (e.g. 20k per month = 240,000 annual).
   - Metro cities in India strictly: Mumbai, Delhi, Kolkata, Chennai. All other cities (Bangalore, Hyderabad, Pune, Gurgaon, etc.) are "non_metro".
3. Return ONLY a valid JSON object matching this schema:
{
  "is_complete": boolean,
  "parsed_fields": {
    "gross_salary": number | null,
    "basic_salary": number | null,
    "hra_received": number | null,
    "rent_paid_annual": number | null,
    "city": "metro" | "non_metro" | null,
    "age_category": "below_60" | "senior_60_to_80" | "super_senior_above_80" | null,
    "investment_80c": number | null,
    "investment_80ccd_1b": number | null,
    "health_insurance_self": number | null,
    "health_insurance_parents": number | null,
    "parents_are_senior_citizens": boolean | null,
    "home_loan_interest": number | null,
    "financial_year": string
  },
  "questions": [
    {
      "field": string,
      "question": string,
      "reason": string
    }
  ]
}
"""


def _rule_based_nlp_fallback(user_text: str, fy: str = "2024-25") -> Dict[str, Any]:
    """Deterministic fallback NLP extractor when LLM quota is rate-limited."""
    text = user_text.lower()
    clean_text = text.replace(",", "")
    fields: Dict[str, Any] = {"financial_year": fy}
    questions: List[Dict[str, str]] = []

    # 1. Rent extraction
    m_rent = re.search(r"(?:pay(?:ing)?\s*)?(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand|pm|per month)?\s*(?:for\s*|as\s*)?rent", clean_text)
    if not m_rent:
        m_rent = re.search(r"rent\s*(?:is|of|de raha hu|deta hu|bharta hu)?\s*[:=]?\s*(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:k|thousand|pm|per month)?", clean_text)
    if m_rent:
        r_val = float(m_rent.group(1))
        match_str = m_rent.group(0)
        if "k" in match_str or "thousand" in match_str or (r_val < 1000 and r_val > 0):
            r_val *= 1000
        if "pm" in clean_text or "month" in clean_text or "mahina" in clean_text:
            r_val *= 12
        fields["rent_paid_annual"] = r_val

    # 2. Section 80C
    m_80c = re.search(r"(?:80c|ppf|elss|pf|lic|section 80c)[^\d]*(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|l\b|k\b)?", clean_text)
    if not m_80c:
        m_80c = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lakhs|l\b|k\b)?\s*(?:in|into|me|mein)?\s*(?:80c|ppf|elss)", clean_text)
    if m_80c:
        val = float(m_80c.group(1))
        match_str = m_80c.group(0)
        if any(term in match_str for term in ["lakh", "lac", "l"]) or val <= 2.5:
            val *= 100_000
        elif "k" in match_str or val < 1000:
            val *= 1000
        fields["investment_80c"] = min(val, 150_000)

    # 3. City
    if any(c in text for c in ["mumbai", "delhi", "kolkata", "chennai"]):
        fields["city"] = "metro"
    elif any(c in text for c in ["bangalore", "bengaluru", "hyderabad", "pune", "noida", "gurgaon"]):
        fields["city"] = "non_metro"

    # 4. Gross salary extraction (MUST have explicit salary / ctc / earning / package keyword or LPA)
    m_lpa = re.search(r"(\d+(?:\.\d+)?)\s*(?:lpa)\b", clean_text)
    m_sal_lakh = re.search(r"(?:gross|annual|total|ctc|package|salary|compensation|kamata hu|earn(?:s|ing)?|income|pension)\s*[:=]?\s*(?:is|of|hai)?\s*(?:rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l\b)", clean_text)
    m_sal_num = re.search(r"(?:gross|annual|total|ctc|package|salary|compensation|kamata hu|earn(?:s|ing)?|income|pension)\s*[:=]?\s*(?:is|of|hai)?\s*(?:rs\.?|inr)?\s*(\d{5,8})", clean_text)
    m_bare_earn = re.search(r"(?:earn(?:s)?|kamata hu)\s*(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|l\b)", clean_text)

    if m_lpa:
        fields["gross_salary"] = float(m_lpa.group(1)) * 100_000
    elif m_sal_lakh:
        fields["gross_salary"] = float(m_sal_lakh.group(1)) * 100_000
    elif m_bare_earn:
        fields["gross_salary"] = float(m_bare_earn.group(1)) * 100_000
    elif m_sal_num:
        fields["gross_salary"] = float(m_sal_num.group(1))
    else:
        questions.append({
            "field": "gross_salary",
            "question": "What is your total gross annual salary or CTC?",
            "reason": "Gross salary is required to compute income tax.",
        })

    # 5. Incomplete context checks
    if fields.get("gross_salary") is not None:
        if len(text.split()) <= 6 and "rent" not in text and "80c" not in text and "invest" not in text and "deduction" not in text:
            questions.append({
                "field": "deductions",
                "question": "Do you pay rent or have investments under Section 80C / 80D?",
                "reason": "Required to evaluate whether the Old or New Tax Regime is more beneficial.",
            })
        elif fields.get("rent_paid_annual") and "city" not in fields and "hra" not in clean_text:
            questions.append({
                "field": "city_and_hra",
                "question": "Which city do you reside in and what is your HRA allowance?",
                "reason": "Required to calculate HRA exemption under Section 10(13A).",
            })
        elif "parents" in clean_text and ("health" in clean_text or "insurance" in clean_text or "mediclaim" in clean_text) and "senior" not in clean_text and "age" not in clean_text:
            questions.append({
                "field": "parents_age",
                "question": "Are your parents senior citizens (aged 60 or above)?",
                "reason": "Section 80D allows up to Rs 50,000 deduction if parents are senior citizens.",
            })

    is_complete = bool(fields.get("gross_salary") is not None and len(questions) == 0)
    return {"is_complete": is_complete, "parsed_fields": fields, "questions": questions}


def parse_plain_language(
    user_text: str,
    fy: str = "2024-25",
    model: str = "gemini-3.5-flash-lite",
) -> NLPParseResult:
    """
    Parses a plain-language user description into structured fields or clarifying questions.
    """
    client = _get_client()

    prompt = f"""
Financial Year: {fy}
User description:
\"\"\"{user_text}\"\"\"

Analyze the text and extract financial facts or identify what clarification is required.
"""

    data = None
    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=PARSER_SYSTEM_INSTRUCTION,
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )
        raw_text = response.text or "{}"
        data = json.loads(raw_text)
    except Exception as e:
        # Fall back to deterministic NLP extraction if API is rate-limited
        data = _rule_based_nlp_fallback(user_text, fy)

    is_complete = data.get("is_complete", False)
    fields = data.get("parsed_fields", {})
    raw_questions = data.get("questions", [])

    questions = [
        ClarifyingQuestion(
            field=q.get("field", "general"),
            question=q.get("question", ""),
            reason=q.get("reason", ""),
        )
        for q in raw_questions
    ]

    parsed_input: Optional[TaxpayerInput] = None

    if fields.get("gross_salary") is not None and len(questions) == 0:
        basic_sal = fields.get("basic_salary")
        if basic_sal is None:
            basic_sal = float(fields["gross_salary"]) * 0.50

        city_val = City.METRO if fields.get("city") == "metro" else City.NON_METRO
        age_val = AgeCategory.BELOW_60
        if fields.get("age_category") == "senior_60_to_80":
            age_val = AgeCategory.SENIOR_60_TO_80
        elif fields.get("age_category") == "super_senior_above_80":
            age_val = AgeCategory.SUPER_SENIOR_ABOVE_80

        parsed_input = TaxpayerInput(
            gross_salary=float(fields.get("gross_salary", 0)),
            basic_salary=float(basic_sal),
            hra_received=float(fields.get("hra_received") or 0),
            rent_paid_annual=float(fields.get("rent_paid_annual") or 0),
            city=city_val,
            age_category=age_val,
            investment_80c=float(fields.get("investment_80c") or 0),
            investment_80ccd_1b=float(fields.get("investment_80ccd_1b") or 0),
            health_insurance_self=float(fields.get("health_insurance_self") or 0),
            health_insurance_parents=float(fields.get("health_insurance_parents") or 0),
            parents_are_senior_citizens=bool(fields.get("parents_are_senior_citizens") or False),
            home_loan_interest=float(fields.get("home_loan_interest") or 0),
            financial_year=fy,
        )
        is_complete = True
    else:
        is_complete = False

    return NLPParseResult(
        parsed_input=parsed_input,
        questions=questions,
        is_complete=is_complete,
        raw_text=user_text,
    )
