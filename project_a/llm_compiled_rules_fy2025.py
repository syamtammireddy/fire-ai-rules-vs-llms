from dataclasses import dataclass, field
from enum import Enum
import math

# --- Start of project_a.models (as per requirement to import) ---
# Assuming these models are defined in project_a/models.py
# For a self-contained module, these would typically be defined here
# or imported from a common library.
# Since the prompt explicitly states "Must import ... from project_a.models",
# we assume these definitions exist there.
# For the purpose of making this code runnable independently for testing,
# I will include their definitions here, but in a real scenario,
# they would be in project_a/models.py and only imported.

class City(Enum):
    METRO = "METRO"
    NON_METRO = "NON_METRO"

class AgeCategory(Enum):
    BELOW_60 = "BELOW_60"
    BETWEEN_60_AND_80 = "BETWEEN_60_AND_80"
    ABOVE_80 = "ABOVE_80"

@dataclass
class TaxpayerInput:
    gross_salary: float
    basic_salary: float # Used for HRA calculation (Basic + DA + Commission)
    hra_received: float
    rent_paid: float
    city_type: City
    age_category: AgeCategory
    opted_for_new_regime: bool # True if taxpayer explicitly opts for new regime, False to compare and choose lower
    section_80c_investments: float
    section_80ccd1b_nps: float
    section_80d_self_family_non_senior: float # Medical insurance premium for self/family (non-senior)
    section_80d_self_family_senior: float     # Medical insurance premium for self/family (senior)
    section_80d_parents_non_senior: float     # Medical insurance premium for parents (non-senior)
    section_80d_parents_senior: float         # Medical insurance premium for parents (senior)
    section_80d_preventive_health_checkup: float # Total for all, within overall 80D limits
    section_24b_interest_on_housing_loan: float
    other_income: float = 0.0 # Income from other sources, if any

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
    gross_total_income: float = 0.0
    deductions_breakdown: DeductionBreakdown = field(default_factory=DeductionBreakdown)
    total_deductions: float = 0.0
    taxable_income: float = 0.0
    tax_before_rebate: float = 0.0
    rebate_87a: float = 0.0
    tax_after_rebate: float = 0.0
    surcharge: float = 0.0
    tax_after_surcharge: float = 0.0
    health_education_cess: float = 0.0
    total_tax_liability: float = 0.0

@dataclass
class TaxResult:
    old_regime_computation: TaxComputation
    new_regime_computation: TaxComputation
    chosen_regime_computation: TaxComputation
    regime_chosen: str # "OLD" or "NEW"
    tax_saving: float = 0.0

# --- End of project_a.models ---


# --- Constants for FY 2025-26 (AY 2026-27) ---

# Standard Deductions
STANDARD_DEDUCTION_OLD_REGIME = 50_000.0
STANDARD_DEDUCTION_NEW_REGIME = 75_000.0

# Section 80C
SECTION_80C_MAX = 1_50_000.0

# Section 80CCD(1B) - NPS
SECTION_80CCD1B_MAX = 50_000.0

# Section 80D - Medical Insurance
SECTION_80D_SELF_FAMILY_NON_SENIOR_LIMIT = 25_000.0
SECTION_80D_SELF_FAMILY_SENIOR_LIMIT = 50_000.0
SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT = 5_000.0 # Within overall 80D limits

# Section 24b - Interest on Housing Loan
SECTION_24B_MAX = 2_00_000.0

# Section 87A Rebate
REBATE_87A_OLD_REGIME_INCOME_LIMIT = 5_00_000.0
REBATE_87A_OLD_REGIME_MAX_AMOUNT = 12_500.0

REBATE_87A_NEW_REGIME_INCOME_LIMIT = 12_00_000.0 # Full rebate up to this income

# Health and Education Cess
CESS_RATE = 0.04

# Surcharge Thresholds and Rates (Income, Rate)
SURCHARGE_THRESHOLDS = [
    (50_00_000.0, 0.10),
    (1_00_00_000.0, 0.15),
    (2_00_00_000.0, 0.25),
    (5_00_00_000.0, 0.37),
]

# Tax Slabs (lower_bound, upper_bound, rate)
# Upper bound is exclusive, lower bound is inclusive.
# Use float('inf') for the highest slab.

# Old Regime Slabs
OLD_REGIME_SLABS_BELOW_60 = [
    (0.0, 2_50_000.0, 0.00),
    (2_50_000.0, 5_00_000.0, 0.05),
    (5_00_000.0, 10_00_000.0, 0.20),
    (10_00_000.0, float('inf'), 0.30),
]

OLD_REGIME_SLABS_60_TO_80 = [
    (0.0, 3_00_000.0, 0.00),
    (3_00_000.0, 5_00_000.0, 0.05),
    (5_00_000.0, 10_00_000.0, 0.20),
    (10_00_000.0, float('inf'), 0.30),
]

OLD_REGIME_SLABS_ABOVE_80 = [
    (0.0, 5_00_000.0, 0.00),
    (5_00_000.0, 10_00_000.0, 0.20),
    (10_00_000.0, float('inf'), 0.30),
]

# New Regime Slabs
NEW_REGIME_SLABS = [
    (0.0, 4_00_000.0, 0.00),
    (4_00_000.0, 8_00_000.0, 0.05),
    (8_00_000.0, 12_00_000.0, 0.10),
    (12_00_000.0, 16_00_000.0, 0.15),
    (16_00_000.0, 20_00_000.0, 0.20),
    (20_00_000.0, 24_00_000.0, 0.25),
    (24_00_000.0, float('inf'), 0.30),
]

# --- Helper Functions ---

def _calculate_hra_exemption(basic_salary: float, hra_received: float, rent_paid: float, city_type: City) -> float:
    """
    Calculates HRA exemption under Section 10(13A).
    """
    if hra_received <= 0 or rent_paid <= 0:
        return 0.0

    # 1. Actual HRA received
    limit1 = hra_received

    # 2. Rent paid minus 10% of Basic Salary
    limit2 = max(0.0, rent_paid - (0.10 * basic_salary))

    # 3. 50% of Basic Salary for metro cities, 40% for non-metro
    if city_type == City.METRO:
        limit3 = 0.50 * basic_salary
    else:
        limit3 = 0.40 * basic_salary
    
    return min(limit1, limit2, limit3)

def _calculate_80d_deduction(
    age_category: AgeCategory,
    self_family_premium_non_senior: float,
    self_family_premium_senior: float,
    parents_premium_non_senior: float,
    parents_premium_senior: float,
    preventive_health_checkup: float
) -> float:
    """
    Calculates deduction under Section 80D for medical insurance and preventive health check-up.
    """
    total_80d = 0.0

    # Self/Family deduction
    self_family_limit = SECTION_80D_SELF_FAMILY_NON_SENIOR_LIMIT
    if age_category in [AgeCategory.BETWEEN_60_AND_80, AgeCategory.ABOVE_80]:
        self_family_limit = SECTION_80D_SELF_FAMILY_SENIOR_LIMIT
    
    # Preventive health check-up is capped and included within the overall limit
    allowed_preventive_self = min(preventive_health_checkup, SECTION_80D_PREVENTIVE_HEALTH_CHECKUP_LIMIT)
    
    total_self_family_premium = self_family_premium_non_senior + self_family_premium_senior
    total_80d += min(total_self_family_premium + allowed_preventive_self, self_family_limit)

    # Parents deduction
    parents_limit = SECTION_80D_SELF_FAMILY_NON_SENIOR_LIMIT # Default if both non-senior
    if parents_premium_senior > 0: # If any senior parent premium is paid, assume at least one parent is senior
        parents_limit = SECTION_80D_SELF_FAMILY_SENIOR_LIMIT
    
    total_parents_premium = parents_premium_non_senior + parents_premium_senior
    total_80d += min(total_parents_premium, parents_limit)

    return total_80d

def _calculate_tax_on_slabs(income: float, slabs: list) -> float:
    """
    Calculates income tax based on provided slabs.
    """
    tax = 0.0
    remaining_income = income
    for lower, upper, rate in slabs:
        if remaining_income <= lower:
            break
        
        taxable_in_slab = min(remaining_income, upper) - lower
        if taxable_in_slab > 0:
            tax += taxable_in_slab * rate
        
        # Update remaining_income for the next iteration
        if upper == float('inf'):
            remaining_income = 0.0 # All remaining income taxed in this slab
        else:
            remaining_income -= (upper - lower)
            
    return max(0.0, tax)

def _calculate_87a_rebate(taxable_income: float, tax_before_rebate: float, regime_type: str) -> float:
    """
    Calculates Section 87A rebate, including marginal relief for the new regime.
    """
    rebate = 0.0
    if regime_type == "OLD":
        if taxable_income <= REBATE_87A_OLD_REGIME_INCOME_LIMIT:
            rebate = min(tax_before_rebate, REBATE_87A_OLD_REGIME_MAX_AMOUNT)
    elif regime_type == "NEW":
        if taxable_income <= REBATE_87A_NEW_REGIME_INCOME_LIMIT:
            rebate = tax_before_rebate # Full rebate
        else:
            # Marginal relief for new regime 87A:
            # Tax payable should not exceed (taxable_income - REBATE_87A_NEW_REGIME_INCOME_LIMIT)
            # because tax at REBATE_87A_NEW_REGIME_INCOME_LIMIT is 0 due to full rebate.
            tax_after_marginal_relief = min(tax_before_rebate, taxable_income - REBATE_87A_NEW_REGIME_INCOME_LIMIT)
            rebate = tax_before_rebate - tax_after_marginal_relief
            
    return max(0.0, rebate)

def _calculate_surcharge(taxable_income: float, tax_after_rebate: float, regime_type: str, age_category: AgeCategory) -> float:
    """
    Calculates surcharge on income tax, including marginal relief.
    """
    surcharge = 0.0
    if taxable_income <= SURCHARGE_THRESHOLDS[0][0]: # 50 Lakhs
        return 0.0

    applicable_surcharge_rate = 0.0
    applicable_threshold = 0.0
    
    # Determine the applicable surcharge rate and threshold
    for threshold, rate in SURCHARGE_THRESHOLDS:
        if taxable_income > threshold:
            applicable_surcharge_rate = rate
            applicable_threshold = threshold
        else:
            break # Found the highest applicable threshold

    if applicable_surcharge_rate > 0:
        surcharge_calculated = tax_after_rebate * applicable_surcharge_rate

        # Marginal Relief for Surcharge
        # The total tax (tax_after_rebate + surcharge) should not exceed
        # (Tax on income up to threshold + (taxable_income - threshold_income)).
        
        # Get slabs for the specific regime to calculate tax at threshold
        if regime_type == "OLD":
            if age_category == AgeCategory.BELOW_60:
                slabs_at_threshold = OLD_REGIME_SLABS_BELOW_60
            elif age_category == AgeCategory.BETWEEN_60_AND_80:
                slabs_at_threshold = OLD_REGIME_SLABS_60_TO_80
            else: # ABOVE_80
                slabs_at_threshold = OLD_REGIME_SLABS_ABOVE_80
        else: # NEW
            slabs_at_threshold = NEW_REGIME_SLABS

        # Calculate tax at the threshold income (before surcharge, after 87A rebate)
        tax_at_threshold_before_rebate = _calculate_tax_on_slabs(applicable_threshold, slabs_at_threshold)
        tax_at_threshold_after_rebate = tax_at_threshold_before_rebate - _calculate_87a_rebate(applicable_threshold, tax_at_threshold_before_rebate, regime_type)
        
        # Marginal relief limit
        marginal_relief_limit = (taxable_income - applicable_threshold) + tax_at_threshold_after_rebate
        
        if (tax_after_rebate + surcharge_calculated) > marginal_relief_limit:
            surcharge = marginal_relief_limit - tax_after_rebate
        else:
            surcharge = surcharge_calculated
            
    return max(0.0, surcharge)

def _compute_old_regime_tax(user_input: TaxpayerInput) -> TaxComputation:
    """
    Computes income tax under the Old Regime.
    """
    computation = TaxComputation()
    computation.gross_total_income = user_input.gross_salary + user_input.other_income

    deductions = DeductionBreakdown()

    # Standard Deduction
    deductions.standard_deduction = STANDARD_DEDUCTION_OLD_REGIME

    # HRA Exemption
    deductions.hra_exemption = _calculate_hra_exemption(
        user_input.basic_salary,
        user_input.hra_received,
        user_input.rent_paid,
        user_input.city_type
    )

    # Section 80C
    deductions.section_80c = min(user_input.section_80c_investments, SECTION_80C_MAX)

    # Section 80CCD(1B)
    deductions.section_80ccd1b = min(user_input.section_80ccd1b_nps, SECTION_80CCD1B_MAX)

    # Section 80D
    deductions.section_80d = _calculate_80d_deduction(
        user_input.age_category,
        user_input.section_80d_self_family_non_senior,
        user_input.section_80d_self_family_senior,
        user_input.section_80d_parents_non_senior,
        user_input.section_80d_parents_senior,
        user_input.section_80d_preventive_health_checkup
    )

    # Section 24b
    deductions.section_24b = min(user_input.section_24b_interest_on_housing_loan, SECTION_24B_MAX)

    # Total Deductions
    deductions.total_deductions = sum([
        deductions.standard_deduction,
        deductions.hra_exemption,
        deductions.section_80c,
        deductions.section_80ccd1b,
        deductions.section_80d,
        deductions.section_24b,
    ])
    
    computation.deductions_breakdown = deductions
    computation.total_deductions = deductions.total_deductions

    # Taxable Income
    computation.taxable_income = max(0.0, computation.gross_total_income - computation.total_deductions)

    # Determine slabs based on age category for Old Regime
    if user_input.age_category == AgeCategory.BELOW_60:
        slabs = OLD_REGIME_SLABS_BELOW_60
    elif user_input.age_category == AgeCategory.BETWEEN_60_AND_80:
        slabs = OLD_REGIME_SLABS_60_TO_80
    else: # ABOVE_80
        slabs = OLD_REGIME_SLABS_ABOVE_80

    # Tax before rebate
    computation.tax_before_rebate = _calculate_tax_on_slabs(computation.taxable_income, slabs)

    # Section 87A Rebate
    computation.rebate_87a = _calculate_87a_rebate(computation.taxable_income, computation.tax_before_rebate, "OLD")
    computation.tax_after_rebate = computation.tax_before_rebate - computation.rebate_87a

    # Surcharge
    computation.surcharge = _calculate_surcharge(computation.taxable_income, computation.tax_after_rebate, "OLD", user_input.age_category)
    computation.tax_after_surcharge = computation.tax_after_rebate + computation.surcharge

    # Health and Education Cess
    computation.health_education_cess = computation.tax_after_surcharge * CESS_RATE

    # Total Tax Liability
    computation.total_tax_liability = computation.tax_after_surcharge + computation.health_education_cess
    
    # Round all final monetary values to nearest rupee
    computation.gross_total_income = round(computation.gross_total_income)
    computation.deductions_breakdown.standard_deduction = round(computation.deductions_breakdown.standard_deduction)
    computation.deductions_breakdown.hra_exemption = round(computation.deductions_breakdown.hra_exemption)
    computation.deductions_breakdown.section_80c = round(computation.deductions_breakdown.section_80c)
    computation.deductions_breakdown.section_80ccd1b = round(computation.deductions_breakdown.section_80ccd1b)
    computation.deductions_breakdown.section_80d = round(computation.deductions_breakdown.section_80d)
    computation.deductions_breakdown.section_24b = round(computation.deductions_breakdown.section_24b)
    computation.deductions_breakdown.total_deductions = round(computation.deductions_breakdown.total_deductions)
    computation.total_deductions = round(computation.total_deductions)
    computation.taxable_income = round(computation.taxable_income)
    computation.tax_before_rebate = round(computation.tax_before_rebate)
    computation.rebate_87a = round(computation.rebate_87a)
    computation.tax_after_rebate = round(computation.tax_after_rebate)
    computation.surcharge = round(computation.surcharge)
    computation.tax_after_surcharge = round(computation.tax_after_surcharge)
    computation.health_education_cess = round(computation.health_education_cess)
    computation.total_tax_liability = round(computation.total_tax_liability)

    return computation

def _compute_new_regime_tax(user_input: TaxpayerInput) -> TaxComputation:
    """
    Computes income tax under the New Regime.
    """
    computation = TaxComputation()
    computation.gross_total_income = user_input.gross_salary + user_input.other_income

    deductions = DeductionBreakdown()

    # Standard Deduction (New Regime)
    deductions.standard_deduction = STANDARD_DEDUCTION_NEW_REGIME
    
    # Other specified deductions (80C, 80CCD(1B), 80D, 24b, HRA) are NOT allowed in the new regime
    # They remain 0 in the breakdown.

    deductions.total_deductions = deductions.standard_deduction
    
    computation.deductions_breakdown = deductions
    computation.total_deductions = deductions.total_deductions

    # Taxable Income
    computation.taxable_income = max(0.0, computation.gross_total_income - computation.total_deductions)

    # Tax before rebate (New Regime Slabs)
    computation.tax_before_rebate = _calculate_tax_on_slabs(computation.taxable_income, NEW_REGIME_SLABS)

    # Section 87A Rebate (New Regime)
    computation.rebate_87a = _calculate_87a_rebate(computation.taxable_income, computation.tax_before_rebate, "NEW")
    computation.tax_after_rebate = computation.tax_before_rebate - computation.rebate_87a

    # Surcharge
    computation.surcharge = _calculate_surcharge(computation.taxable_income, computation.tax_after_rebate, "NEW", user_input.age_category)
    computation.tax_after_surcharge = computation.tax_after_rebate + computation.surcharge

    # Health and Education Cess
    computation.health_education_cess = computation.tax_after_surcharge * CESS_RATE

    # Total Tax Liability
    computation.total_tax_liability = computation.tax_after_surcharge + computation.health_education_cess

    # Round all final monetary values to nearest rupee
    computation.gross_total_income = round(computation.gross_total_income)
    computation.deductions_breakdown.standard_deduction = round(computation.deductions_breakdown.standard_deduction)
    computation.deductions_breakdown.total_deductions = round(computation.deductions_breakdown.total_deductions)
    computation.total_deductions = round(computation.total_deductions)
    computation.taxable_income = round(computation.taxable_income)
    computation.tax_before_rebate = round(computation.tax_before_rebate)
    computation.rebate_87a = round(computation.rebate_87a)
    computation.tax_after_rebate = round(computation.tax_after_rebate)
    computation.surcharge = round(computation.surcharge)
    computation.tax_after_surcharge = round(computation.tax_after_surcharge)
    computation.health_education_cess = round(computation.health_education_cess)
    computation.total_tax_liability = round(computation.total_tax_liability)

    return computation

def compute_tax_compiled(user_input: TaxpayerInput) -> TaxResult:
    """
    Main function to compute Indian income tax for salaried individuals for FY 2025-26.
    It computes tax under both Old and New Regimes and returns the result
    based on user's choice or the lower tax liability.
    """
    old_regime_comp = _compute_old_regime_tax(user_input)
    new_regime_comp = _compute_new_regime_tax(user_input)

    chosen_regime_comp: TaxComputation
    regime_chosen: str
    tax_saving: float = 0.0

    if user_input.opted_for_new_regime:
        chosen_regime_comp = new_regime_comp
        regime_chosen = "NEW"
        tax_saving = old_regime_comp.total_tax_liability - new_regime_comp.total_tax_liability
    else:
        # If not explicitly opted for new, compare and choose the lower tax
        if old_regime_comp.total_tax_liability <= new_regime_comp.total_tax_liability:
            chosen_regime_comp = old_regime_comp
            regime_chosen = "OLD"
            tax_saving = new_regime_comp.total_tax_liability - old_regime_comp.total_tax_liability
        else:
            chosen_regime_comp = new_regime_comp
            regime_chosen = "NEW"
            tax_saving = old_regime_comp.total_tax_liability - new_regime_comp.total_tax_liability
            
    return TaxResult(
        old_regime_computation=old_regime_comp,
        new_regime_computation=new_regime_comp,
        chosen_regime_computation=chosen_regime_comp,
        regime_chosen=regime_chosen,
        tax_saving=round(tax_saving)
    )