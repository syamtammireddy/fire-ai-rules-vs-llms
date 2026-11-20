from dataclasses import dataclass
from enum import Enum
import math

# --- Assumed imports from project_a.models ---
# These classes are expected to be defined in project_a/models.py
# and imported into this module.
# For a self-contained module, these would typically be defined here
# or in a separate shared file. As per instructions, we assume they are imported.

class City(Enum):
    METRO = "METRO"
    NON_METRO = "NON_METRO"

class AgeCategory(Enum):
    BELOW_60 = "BELOW_60"
    SENIOR_CITIZEN = "SENIOR_CITIZEN" # 60 to 80 years

@dataclass
class DeductionBreakdown:
    standard_deduction: float = 0.0
    hra_exemption: float = 0.0
    section_80c: float = 0.0
    section_80ccd1b: float = 0.0
    section_80d: float = 0.0
    section_24b: float = 0.0
    total_deductions: float = 0.0

@dataclass
class TaxComputation:
    gross_salary: float = 0.0
    total_deductions: float = 0.0
    taxable_income: float = 0.0
    tax_before_rebate: float = 0.0
    rebate_87a: float = 0.0
    tax_after_rebate: float = 0.0
    surcharge: float = 0.0
    tax_before_cess: float = 0.0
    cess: float = 0.0
    total_tax_payable: float = 0.0

@dataclass
class TaxpayerInput:
    gross_salary: float
    basic_salary: float
    hra_received: float
    rent_paid: float
    city_type: City
    age_category: AgeCategory
    section_80c_investments: float
    section_80ccd1b_nps: float
    section_80d_self_family: float
    section_80d_parents: float
    section_24b_home_loan_interest: float
    opt_for_new_regime: bool

@dataclass
class TaxResult:
    old_regime_computation: TaxComputation
    new_regime_computation: TaxComputation
    old_regime_deductions: DeductionBreakdown
    new_regime_deductions: DeductionBreakdown
    recommended_regime: str
    final_tax_payable: float

# --- End assumed imports ---


# --- Constants for FY 2024-25 (AY 2025-26) ---

# Standard Deductions
STANDARD_DEDUCTION_OLD = 50_000.0
STANDARD_DEDUCTION_NEW = 75_000.0

# HRA Exemption
HRA_METRO_PERCENT = 0.50
HRA_NON_METRO_PERCENT = 0.40

# Section 80C
MAX_80C = 1_50_000.0

# Section 80CCD(1B)
MAX_80CCD1B = 50_000.0

# Section 80D
MAX_80D_BELOW_60 = 25_000.0
MAX_80D_SENIOR = 50_000.0

# Section 24(b)
MAX_24B = 2_00_000.0

# Tax Slabs
OLD_REGIME_SLABS = [
    (2_50_000.0, 0.00),  # Up to 2.5L
    (5_00_000.0, 0.05),  # 2.5L to 5L
    (10_00_000.0, 0.20), # 5L to 10L
    (float('inf'), 0.30) # Above 10L
]

NEW_REGIME_SLABS = [
    (3_00_000.0, 0.00),  # Up to 3L
    (7_00_000.0, 0.05),  # 3L to 7L
    (10_00_000.0, 0.10), # 7L to 10L
    (12_00_000.0, 0.15), # 10L to 12L
    (15_00_000.0, 0.20), # 12L to 15L
    (float('inf'), 0.30) # Above 15L
]

# Section 87A Rebate
REBATE_87A_OLD_MAX_INCOME = 5_00_000.0
REBATE_87A_OLD_MAX_AMOUNT = 12_500.0

REBATE_87A_NEW_MAX_INCOME = 7_00_000.0
REBATE_87A_NEW_MAX_AMOUNT = 25_000.0

# Surcharge Thresholds and Rates
SURCHARGE_THRESHOLDS = [50_00_000.0, 1_00_00_000.0, 2_00_00_000.0, 5_00_00_000.0]
SURCHARGE_RATES_OLD = [0.10, 0.15, 0.25, 0.37]
SURCHARGE_RATES_NEW = [0.10, 0.15, 0.25, 0.25] # New regime capped at 25%

# Health & Education Cess
CESS_RATE = 0.04

# --- Helper functions ---

def _round_to_nearest_rupee(amount: float) -> int:
    """Rounds a float amount to the nearest integer rupee."""
    return int(round(amount))

def _calculate_tax_on_slabs(income: float, slabs: list) -> float:
    """Calculates tax based on provided slab rates."""
    tax = 0.0
    remaining_income = income
    previous_slab_limit = 0.0

    for slab_limit, rate in slabs:
        if remaining_income <= previous_slab_limit:
            break
        
        taxable_in_slab = min(remaining_income, slab_limit) - previous_slab_limit
        tax += taxable_in_slab * rate
        
        if remaining_income <= slab_limit:
            break
        
        previous_slab_limit = slab_limit
    
    return tax

def _calculate_surcharge(tax_after_rebate: float, taxable_income: float, regime: str) -> float:
    """Calculates surcharge with marginal relief."""
    surcharge_rate = 0.0
    current_surcharge_threshold_idx = -1

    if taxable_income > SURCHARGE_THRESHOLDS[3]: # > 5 Crore
        current_surcharge_threshold_idx = 3
    elif taxable_income > SURCHARGE_THRESHOLDS[2]: # > 2 Crore to 5 Crore
        current_surcharge_threshold_idx = 2
    elif taxable_income > SURCHARGE_THRESHOLDS[1]: # > 1 Crore to 2 Crore
        current_surcharge_threshold_idx = 1
    elif taxable_income > SURCHARGE_THRESHOLDS[0]: # > 50 Lakh to 1 Crore
        current_surcharge_threshold_idx = 0
    else:
        return 0.0 # No surcharge

    if regime == "OLD":
        surcharge_rate = SURCHARGE_RATES_OLD[current_surcharge_threshold_idx]
        slabs = OLD_REGIME_SLABS
        rebate_max_income = REBATE_87A_OLD_MAX_INCOME
        rebate_max_amount = REBATE_87A_OLD_MAX_AMOUNT
    else: # NEW regime
        surcharge_rate = SURCHARGE_RATES_NEW[current_surcharge_threshold_idx]
        slabs = NEW_REGIME_SLABS
        rebate_max_income = REBATE_87A_NEW_MAX_INCOME
        rebate_max_amount = REBATE_87A_NEW_MAX_AMOUNT

    surcharge_amount_before_marginal_relief = tax_after_rebate * surcharge_rate
    total_tax_before_marginal_relief = tax_after_rebate + surcharge_amount_before_marginal_relief

    # Marginal relief calculation
    threshold_income = SURCHARGE_THRESHOLDS[current_surcharge_threshold_idx]
    
    # Calculate tax at the lower threshold of the current surcharge slab (before 87A rebate)
    tax_at_threshold_before_rebate = _calculate_tax_on_slabs(threshold_income, slabs)
    
    # Apply 87A rebate for the threshold income.
    # For surcharge thresholds (50L, 1Cr, etc.), the income is always > 7L/5L, so 87A rebate is 0.
    rebate_at_threshold = 0.0
    
    tax_at_threshold_after_rebate = tax_at_threshold_before_rebate - rebate_at_threshold

    # The marginal relief is applied such that the total tax (tax_after_rebate + actual_surcharge)
    # does not exceed (tax_at_threshold_after_rebate + (taxable_income - threshold_income)).
    max_allowed_total_tax = tax_at_threshold_after_rebate + (taxable_income - threshold_income)

    if total_tax_before_marginal_relief > max_allowed_total_tax:
        actual_total_tax = max_allowed_total_tax
        actual_surcharge = actual_total_tax - tax_after_rebate
        return max(0.0, actual_surcharge) # Surcharge cannot be negative
    else:
        return surcharge_amount_before_marginal_relief

def _compute_old_regime_tax(user_input: TaxpayerInput) -> tuple[TaxComputation, DeductionBreakdown]:
    """Computes tax under the Old Tax Regime."""
    deductions = DeductionBreakdown()
    computation = TaxComputation()
    
    computation.gross_salary = user_input.gross_salary

    # 1. Standard Deduction
    deductions.standard_deduction = STANDARD_DEDUCTION_OLD
    
    # 2. HRA Exemption (Section 10(13A))
    hra_exemption_a = user_input.hra_received
    hra_exemption_b = max(0.0, user_input.rent_paid - (0.10 * user_input.basic_salary))
    hra_exemption_c_percent = HRA_METRO_PERCENT if user_input.city_type == City.METRO else HRA_NON_METRO_PERCENT
    hra_exemption_c = hra_exemption_c_percent * user_input.basic_salary
    
    deductions.hra_exemption = min(hra_exemption_a, hra_exemption_b, hra_exemption_c)
    deductions.hra_exemption = max(0.0, deductions.hra_exemption) # Ensure HRA exemption is not negative

    # Gross Total Income (before Chapter VI-A deductions)
    # Note: Standard deduction and HRA are deducted from Gross Salary to arrive at Gross Total Income for Chapter VI-A deductions.
    # However, for simplicity and direct calculation of taxable income, we sum all deductions.
    
    # 3. Section 80C
    deductions.section_80c = min(user_input.section_80c_investments, MAX_80C)
    
    # 4. Section 80CCD(1B)
    deductions.section_80ccd1b = min(user_input.section_80ccd1b_nps, MAX_80CCD1B)
    
    # 5. Section 80D
    # Self/Family limit
    limit_self_family = MAX_80D_SENIOR if user_input.age_category == AgeCategory.SENIOR_CITIZEN else MAX_80D_BELOW_60
    deductions_80d_self_family = min(user_input.section_80d_self_family, limit_self_family)

    # Parents limit (assuming parents are senior citizens if the primary assessee is, for lack of separate input)
    limit_parents = MAX_80D_SENIOR if user_input.age_category == AgeCategory.SENIOR_CITIZEN else MAX_80D_BELOW_60
    deductions_80d_parents = min(user_input.section_80d_parents, limit_parents)
    
    deductions.section_80d = deductions_80d_self_family + deductions_80d_parents

    # 6. Section 24(b)
    deductions.section_24b = min(user_input.section_24b_home_loan_interest, MAX_24B)

    deductions.total_deductions = (
        deductions.standard_deduction +
        deductions.hra_exemption +
        deductions.section_80c +
        deductions.section_80ccd1b +
        deductions.section_80d +
        deductions.section_24b
    )

    computation.total_deductions = deductions.total_deductions
    computation.taxable_income = max(0.0, user_input.gross_salary - computation.total_deductions)

    # Tax Calculation
    computation.tax_before_rebate = _calculate_tax_on_slabs(computation.taxable_income, OLD_REGIME_SLABS)

    # Section 87A Rebate
    if computation.taxable_income <= REBATE_87A_OLD_MAX_INCOME:
        computation.rebate_87a = min(computation.tax_before_rebate, REBATE_87A_OLD_MAX_AMOUNT)
    else:
        computation.rebate_87a = 0.0
    
    computation.tax_after_rebate = computation.tax_before_rebate - computation.rebate_87a
    computation.tax_after_rebate = max(0.0, computation.tax_after_rebate) # Tax cannot be negative

    # Surcharge
    computation.surcharge = _calculate_surcharge(computation.tax_after_rebate, computation.taxable_income, "OLD")
    
    computation.tax_before_cess = computation.tax_after_rebate + computation.surcharge

    # Health & Education Cess
    computation.cess = computation.tax_before_cess * CESS_RATE

    computation.total_tax_payable = computation.tax_before_cess + computation.cess
    
    return computation, deductions

def _compute_new_regime_tax(user_input: TaxpayerInput) -> tuple[TaxComputation, DeductionBreakdown]:
    """Computes tax under the New Tax Regime."""
    deductions = DeductionBreakdown()
    computation = TaxComputation()

    computation.gross_salary = user_input.gross_salary

    # 1. Standard Deduction
    deductions.standard_deduction = STANDARD_DEDUCTION_NEW
    
    # No other deductions allowed in new regime
    deductions.total_deductions = deductions.standard_deduction

    computation.total_deductions = deductions.total_deductions
    computation.taxable_income = max(0.0, user_input.gross_salary - computation.total_deductions)

    # Tax Calculation
    computation.tax_before_rebate = _calculate_tax_on_slabs(computation.taxable_income, NEW_REGIME_SLABS)

    # Section 87A Rebate and Proviso
    if computation.taxable_income <= REBATE_87A_NEW_MAX_INCOME:
        computation.rebate_87a = min(computation.tax_before_rebate, REBATE_87A_NEW_MAX_AMOUNT)
        computation.tax_after_rebate = computation.tax_before_rebate - computation.rebate_87a
        computation.tax_after_rebate = max(0.0, computation.tax_after_rebate) # Tax cannot be negative
    else:
        # If taxable income > 7,00,000, no 87A rebate.
        computation.rebate_87a = 0.0
        computation.tax_after_rebate = computation.tax_before_rebate
        
        # Proviso to Section 87A (Marginal relief for income just above 7L)
        # "Tax payable cannot exceed excess taxable income over ₹7,00,000."
        # This applies if taxable_income > 7,00,000.
        # The tax payable (without surcharge/cess) should be min(normal_tax, taxable_income - 7,00,000)
        if computation.taxable_income > REBATE_87A_NEW_MAX_INCOME:
            max_tax_due_to_marginal_relief = max(0.0, computation.taxable_income - REBATE_87A_NEW_MAX_INCOME)
            computation.tax_after_rebate = min(computation.tax_after_rebate, max_tax_due_to_marginal_relief)

    # Surcharge
    computation.surcharge = _calculate_surcharge(computation.tax_after_rebate, computation.taxable_income, "NEW")
    
    computation.tax_before_cess = computation.tax_after_rebate + computation.surcharge

    # Health & Education Cess
    computation.cess = computation.tax_before_cess * CESS_RATE

    computation.total_tax_payable = computation.tax_before_cess + computation.cess

    return computation, deductions

def compute_tax_compiled(user_input: TaxpayerInput) -> TaxResult:
    """
    Computes Indian income tax for salaried individuals for FY 2024-25 (AY 2025-26)
    under both Old and New Tax Regimes and recommends the better option.
    """
    old_regime_comp, old_regime_deductions = _compute_old_regime_tax(user_input)
    new_regime_comp, new_regime_deductions = _compute_new_regime_tax(user_input)

    recommended_regime = "OLD"
    final_tax_payable = old_regime_comp.total_tax_payable

    if new_regime_comp.total_tax_payable < old_regime_comp.total_tax_payable:
        recommended_regime = "NEW"
        final_tax_payable = new_regime_comp.total_tax_payable
    
    # If user explicitly opted for new regime, use its tax, regardless of recommendation
    if user_input.opt_for_new_regime:
        final_tax_payable = new_regime_comp.total_tax_payable
        recommended_regime = "NEW (User Opted)" # Indicate user choice

    return TaxResult(
        old_regime_computation=old_regime_comp,
        new_regime_computation=new_regime_comp,
        old_regime_deductions=old_regime_deductions,
        new_regime_deductions=new_regime_deductions,
        recommended_regime=recommended_regime,
        final_tax_payable=_round_to_nearest_rupee(final_tax_payable)
    )