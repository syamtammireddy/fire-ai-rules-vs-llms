"""
Compiler script to generate executable Python tax calculation code from rule text using Gemini.
Task 2c: The LLM converts the rule text into executable rules once;
the developer reviews them, and they run without an LLM at query time.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


def compile_rules(fy: str = "2024-25", output_path: str = None) -> str:
    """Invokes Gemini to compile rule text into standalone Python code."""
    from project_a.rules_llm_query import PROMPT_RULE_TEXT_FY2024, PROMPT_RULE_TEXT_FY2025

    rule_text = PROMPT_RULE_TEXT_FY2025 if fy == "2025-26" else PROMPT_RULE_TEXT_FY2024
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options={"api_version": "v1beta"})

    prompt = f"""
You are an expert compiler that translates statutory tax rules into clean, robust, deterministic Python code.
Generate a complete, self-contained Python module that computes Indian income tax for salaried individuals.

RULES FOR FY {fy}:
{rule_text}

REQUIREMENTS:
1. Module must define a function:
   `def compute_tax_compiled(user_input: TaxpayerInput) -> TaxResult:`
   and helper functions for old regime and new regime.
2. Must import `TaxpayerInput`, `TaxResult`, `TaxComputation`, `DeductionBreakdown`, `City`, `AgeCategory` from `project_a.models`.
3. Code must be purely deterministic, have zero external API calls, and accurately compute:
   - Deductions (Standard deduction, 80C, 80CCD(1B), 80D, 24b, HRA exemption)
   - Slabs
   - Section 87A rebate & marginal relief
   - Surcharge & marginal relief
   - 4% Cess
4. Return ONLY the raw Python code (no markdown formatting, no backticks, or inside ```python ... ``` block).
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
        ),
    )

    code = response.text or ""
    # Strip markdown backticks if present
    if code.startswith("```python"):
        code = code[len("```python"):].strip()
    if code.startswith("```"):
        code = code[len("```"):].strip()
    if code.endswith("```"):
        code = code[:-3].strip()

    if output_path:
        with open(output_path, "w") as f:
            f.write(code)
        print(f"Compiled rules for FY {fy} written to {output_path}")

    return code


if __name__ == "__main__":
    compile_rules("2024-25", "project_a/llm_compiled_rules_fy2024.py")
    compile_rules("2025-26", "project_a/llm_compiled_rules_fy2025.py")
