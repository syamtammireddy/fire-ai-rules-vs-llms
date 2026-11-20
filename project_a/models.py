"""
Pydantic models for the Indian income-tax calculator.
Defines the structured input (TaxpayerInput) and output (TaxResult) schemas.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class City(str, Enum):
    """Metro classification for HRA exemption (Sec 10(13A))."""
    METRO = "metro"          # Mumbai, Delhi, Kolkata, Chennai
    NON_METRO = "non_metro"  # All other cities


class AgeCategory(str, Enum):
    """Age classification for old-regime exemption limits."""
    BELOW_60 = "below_60"
    SENIOR_60_TO_80 = "senior_60_to_80"
    SUPER_SENIOR_ABOVE_80 = "super_senior_above_80"


class TaxpayerInput(BaseModel):
    """
    Structured input representing a salaried individual's financial details
    for a given financial year. All amounts in INR (rupees).
    """
    # --- Salary components ---
    gross_salary: float = Field(..., ge=0, description="Total gross salary (CTC or gross)")
    basic_salary: float = Field(..., ge=0, description="Basic salary component")
    hra_received: float = Field(0, ge=0, description="HRA component received from employer")
    
    # --- Personal details ---
    age_category: AgeCategory = Field(
        AgeCategory.BELOW_60,
        description="Age category of the taxpayer"
    )
    city: City = Field(
        City.NON_METRO,
        description="Whether the taxpayer lives in a metro city (Mumbai/Delhi/Kolkata/Chennai)"
    )

    # --- Rent details (for HRA exemption) ---
    rent_paid_annual: float = Field(0, ge=0, description="Total annual rent paid")

    # --- Section 80C investments ---
    investment_80c: float = Field(
        0, ge=0,
        description="Total investments under Sec 80C (PPF, ELSS, EPF employee share, LIC, etc.)"
    )

    # --- Section 80CCD(1B) - Additional NPS ---
    investment_80ccd_1b: float = Field(
        0, ge=0,
        description="Additional NPS contribution under Sec 80CCD(1B)"
    )

    # --- Section 80D - Health Insurance ---
    health_insurance_self: float = Field(
        0, ge=0,
        description="Health insurance premium for self/spouse/children"
    )
    health_insurance_parents: float = Field(
        0, ge=0,
        description="Health insurance premium for parents"
    )
    parents_are_senior_citizens: bool = Field(
        False,
        description="Whether parents are senior citizens (60+) for 80D limit"
    )

    # --- Home Loan Interest (Section 24b) ---
    home_loan_interest: float = Field(
        0, ge=0,
        description="Home loan interest paid for self-occupied property"
    )

    # --- Financial Year ---
    financial_year: str = Field(
        "2024-25",
        description="Financial year for tax computation"
    )

    @field_validator("investment_80c")
    @classmethod
    def cap_80c(cls, v: float) -> float:
        """Section 80C is capped at ₹1,50,000."""
        return min(v, 150000)

    @field_validator("investment_80ccd_1b")
    @classmethod
    def cap_80ccd_1b(cls, v: float) -> float:
        """Section 80CCD(1B) is capped at ₹50,000."""
        return min(v, 50000)


class DeductionBreakdown(BaseModel):
    """Itemized deductions with clause references."""
    standard_deduction: float = 0
    hra_exemption: float = 0
    section_80c: float = 0
    section_80ccd_1b: float = 0
    section_80d_self: float = 0
    section_80d_parents: float = 0
    home_loan_interest_24b: float = 0
    total: float = 0

    def compute_total(self) -> float:
        self.total = (
            self.standard_deduction
            + self.hra_exemption
            + self.section_80c
            + self.section_80ccd_1b
            + self.section_80d_self
            + self.section_80d_parents
            + self.home_loan_interest_24b
        )
        return self.total


class TaxComputation(BaseModel):
    """Step-by-step tax computation with clause references for auditability."""
    gross_salary: float = 0
    deductions: DeductionBreakdown = Field(default_factory=DeductionBreakdown)
    taxable_income: float = 0
    tax_on_slabs: float = 0
    rebate_87a: float = 0
    tax_after_rebate: float = 0
    surcharge: float = 0
    marginal_relief: float = 0
    surcharge_after_relief: float = 0
    cess: float = 0
    total_tax: float = 0
    
    # Audit trail — which clause justifies each line
    clause_references: dict[str, str] = Field(default_factory=dict)


class TaxResult(BaseModel):
    """Complete tax result comparing both regimes."""
    old_regime: TaxComputation = Field(default_factory=TaxComputation)
    new_regime: TaxComputation = Field(default_factory=TaxComputation)
    recommended_regime: str = ""
    savings: float = 0  # positive = new regime saves money
    explanation: str = ""
    deduction_headroom: dict[str, float] = Field(default_factory=dict)
    advisory_notes: list[str] = Field(default_factory=list)
    break_even_deductions: float = 0.0  # Total deductions where Old Regime tax equals New Regime tax
    break_even_gap: float = 0.0         # Additional deductions needed for Old Regime to beat New Regime
    break_even_analysis: str = ""


class ClarifyingQuestion(BaseModel):
    """When NLP parser can't determine a field, it returns questions."""
    field: str
    question: str
    reason: str


class NLPParseResult(BaseModel):
    """Result of parsing a plain-language description."""
    parsed_input: Optional[TaxpayerInput] = None
    questions: list[ClarifyingQuestion] = Field(default_factory=list)
    is_complete: bool = False
    raw_text: str = ""
