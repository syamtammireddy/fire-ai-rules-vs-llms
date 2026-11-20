"""
Hand-coded Indian Income Tax Engine for Salaried Individuals.
Fully auditable, deterministic, and rupee-exact implementation.
Covers FY 2024-25 and FY 2025-26.
"""

from __future__ import annotations

from typing import List, Tuple
from project_a.models import (
    TaxpayerInput,
    TaxComputation,
    TaxResult,
    DeductionBreakdown,
    City,
    AgeCategory,
)
from project_a import tax_rules_fy2024 as r24
from project_a import tax_rules_fy2025 as r25


def compute_hra_exemption(
    basic_salary: float,
    hra_received: float,
    rent_paid: float,
    city: City,
) -> Tuple[float, dict[str, str]]:
    """
    Computes HRA Exemption under Section 10(13A) read with Rule 2A.
    Exemption is the least of:
    1. Actual HRA received
    2. Rent paid - 10% of salary (basic)
    3. 50% of basic (metro: Mumbai/Delhi/Kolkata/Chennai) or 40% (non-metro)
    """
    if rent_paid <= 0 or hra_received <= 0 or basic_salary <= 0:
        return 0.0, {"hra_rule": "Section 10(13A): Rent paid <= 0 or HRA <= 0, exemption is ₹0"}

    cond1 = hra_received
    cond2 = max(0.0, rent_paid - 0.10 * basic_salary)
    percentage = r24.HRA_PERCENTAGE_METRO if city == City.METRO else r24.HRA_PERCENTAGE_NON_METRO
    cond3 = percentage * basic_salary

    exemption = min(cond1, cond2, cond3)
    clause = (
        f"Section 10(13A) read with Rule 2A: Least of "
        f"[Actual HRA: ₹{cond1:,.0f}, "
        f"Rent - 10% Basic: ₹{cond2:,.0f}, "
        f"{int(percentage*100)}% Basic: ₹{cond3:,.0f}] = ₹{exemption:,.0f}"
    )
    return exemption, {"hra_rule": clause}


def compute_slab_tax(taxable_income: float, slabs: List[Tuple[float, float, float]]) -> Tuple[float, List[str]]:
    """Computes basic tax based on progressive slabs."""
    if taxable_income <= 0:
        return 0.0, ["Taxable income <= 0: tax is ₹0"]

    tax = 0.0
    slab_details = []
    for lower, upper, rate in slabs:
        if taxable_income > lower:
            taxable_in_slab = min(taxable_income, upper) - lower
            tax_in_slab = taxable_in_slab * rate
            tax += tax_in_slab
            if rate > 0 and tax_in_slab > 0:
                upper_str = f"₹{upper:,.0f}" if upper != float("inf") else "Above"
                slab_details.append(
                    f"Slab ₹{lower:,.0f} - {upper_str} at {int(rate*100)}%: ₹{tax_in_slab:,.0f}"
                )
    return tax, slab_details


def compute_surcharge_and_marginal_relief(
    taxable_income: float,
    base_tax: float,
    surcharge_brackets: List[Tuple[float, float]],
    slabs: List[Tuple[float, float, float]],
) -> Tuple[float, float, float, str]:
    """
    Computes Surcharge and Marginal Relief under the Finance Act.
    Returns: (nominal_surcharge, marginal_relief, effective_surcharge, explanation)
    """
    if taxable_income <= 5_000_000.0 or base_tax <= 0:
        return 0.0, 0.0, 0.0, "Income <= ₹50 Lakhs: No surcharge"

    # Identify applicable bracket
    applicable_rate = 0.0
    threshold = 0.0
    prev_threshold = 0.0
    prev_rate = 0.0

    for idx, (t, rate) in enumerate(surcharge_brackets):
        if taxable_income > t:
            threshold = t
            applicable_rate = rate
            if idx > 0:
                prev_threshold = surcharge_brackets[idx - 1][0]
                prev_rate = surcharge_brackets[idx - 1][1]
            else:
                prev_threshold = 5_000_000.0
                prev_rate = 0.0

    if applicable_rate == 0.0:
        return 0.0, 0.0, 0.0, "No surcharge applicable"

    nominal_surcharge = base_tax * applicable_rate
    nominal_total = base_tax + nominal_surcharge

    # Marginal Relief Calculation:
    # Benchmark: tax + surcharge at threshold
    tax_at_threshold, _ = compute_slab_tax(threshold, slabs)
    surcharge_at_threshold = tax_at_threshold * prev_rate
    benchmark_total = tax_at_threshold + surcharge_at_threshold

    # Law: Total tax + surcharge cannot exceed (Total at threshold + excess income above threshold)
    max_allowed = benchmark_total + (taxable_income - threshold)

    if nominal_total > max_allowed:
        marginal_relief = nominal_total - max_allowed
        effective_surcharge = nominal_surcharge - marginal_relief
        explanation = (
            f"Marginal Relief under Finance Act: Surcharge capped so total tax+surcharge "
            f"does not exceed tax at ₹{threshold:,.0f} (₹{benchmark_total:,.0f}) + excess income "
            f"(₹{taxable_income - threshold:,.0f}). Relief: ₹{marginal_relief:,.0f}"
        )
    else:
        marginal_relief = 0.0
        effective_surcharge = nominal_surcharge
        explanation = f"Surcharge of {int(applicable_rate*100)}% on tax: ₹{effective_surcharge:,.0f}"

    return nominal_surcharge, marginal_relief, effective_surcharge, explanation


def compute_old_regime(
    user_input: TaxpayerInput,
    fy: str = "2024-25",
) -> TaxComputation:
    """Calculates tax under the Old Tax Regime."""
    # Deductions
    deductions = DeductionBreakdown()
    clauses: dict[str, str] = {}

    # 1. Standard Deduction (Section 16(ia))
    deductions.standard_deduction = min(user_input.gross_salary, r24.STANDARD_DEDUCTION_OLD)
    clauses["standard_deduction"] = f"Section 16(ia): Standard deduction ₹{deductions.standard_deduction:,.0f}"

    # 2. HRA Exemption (Section 10(13A))
    hra_exemption, hra_clause = compute_hra_exemption(
        basic_salary=user_input.basic_salary,
        hra_received=user_input.hra_received,
        rent_paid=user_input.rent_paid_annual,
        city=user_input.city,
    )
    deductions.hra_exemption = hra_exemption
    clauses.update(hra_clause)

    # 3. Section 80C
    deductions.section_80c = min(user_input.investment_80c, r24.MAX_80C)
    clauses["80C"] = f"Section 80C: Investments capped at ₹{r24.MAX_80C:,.0f} -> ₹{deductions.section_80c:,.0f}"

    # 4. Section 80CCD(1B)
    deductions.section_80ccd_1b = min(user_input.investment_80ccd_1b, r24.MAX_80CCD_1B)
    clauses["80CCD_1B"] = f"Section 80CCD(1B): NPS contribution capped at ₹{r24.MAX_80CCD_1B:,.0f} -> ₹{deductions.section_80ccd_1b:,.0f}"

    # 5. Section 80D - Health Insurance
    limit_self = r24.MAX_80D_SELF_SENIOR if user_input.age_category != AgeCategory.BELOW_60 else r24.MAX_80D_SELF_NON_SENIOR
    deductions.section_80d_self = min(user_input.health_insurance_self, limit_self)

    limit_parents = r24.MAX_80D_PARENTS_SENIOR if user_input.parents_are_senior_citizens else r24.MAX_80D_PARENTS_NON_SENIOR
    deductions.section_80d_parents = min(user_input.health_insurance_parents, limit_parents)
    clauses["80D"] = (
        f"Section 80D: Self/Family (limit ₹{limit_self:,.0f}): ₹{deductions.section_80d_self:,.0f}, "
        f"Parents (limit ₹{limit_parents:,.0f}): ₹{deductions.section_80d_parents:,.0f}"
    )

    # 6. Section 24(b) - Home loan interest
    deductions.home_loan_interest_24b = min(user_input.home_loan_interest, r24.MAX_HOME_LOAN_INTEREST_24B)
    clauses["24b"] = f"Section 24(b): Self-occupied property interest capped at ₹{r24.MAX_HOME_LOAN_INTEREST_24B:,.0f} -> ₹{deductions.home_loan_interest_24b:,.0f}"

    total_deductions = deductions.compute_total()
    taxable_income = max(0.0, user_input.gross_salary - total_deductions)

    # Slabs selection by age
    if user_input.age_category == AgeCategory.SUPER_SENIOR_ABOVE_80:
        slabs = r24.SLABS_OLD_SUPER_SENIOR
        clauses["slabs_category"] = "Super Senior Citizen (80+): Exemption limit ₹5,00,000"
    elif user_input.age_category == AgeCategory.SENIOR_60_TO_80:
        slabs = r24.SLABS_OLD_SENIOR
        clauses["slabs_category"] = "Senior Citizen (60-80): Exemption limit ₹3,00,000"
    else:
        slabs = r24.SLABS_OLD_BELOW_60
        clauses["slabs_category"] = "Individual (<60): Exemption limit ₹2,50,000"

    # Base tax on slabs
    base_tax, slab_desc = compute_slab_tax(taxable_income, slabs)
    clauses["slab_computation"] = "; ".join(slab_desc) if slab_desc else "No slab tax"

    # Section 87A Rebate
    rebate_87a = 0.0
    if taxable_income <= r24.REBATE_87A_THRESHOLD_OLD:
        rebate_87a = min(base_tax, r24.REBATE_87A_MAX_OLD)
        clauses["87A"] = f"Section 87A: Taxable income <= ₹5,00,000, 100% tax rebate up to ₹12,500 = ₹{rebate_87a:,.0f}"
    else:
        clauses["87A"] = "Section 87A: Not eligible (taxable income > ₹5,00,000)"

    tax_after_rebate = max(0.0, base_tax - rebate_87a)

    # Surcharge & Marginal Relief
    nom_surch, marg_relief, eff_surch, surch_exp = compute_surcharge_and_marginal_relief(
        taxable_income=taxable_income,
        base_tax=tax_after_rebate,
        surcharge_brackets=r24.SURCHARGE_BRACKETS_OLD,
        slabs=slabs,
    )
    clauses["surcharge"] = surch_exp

    # Cess 4%
    tax_plus_surcharge = tax_after_rebate + eff_surch
    cess = tax_plus_surcharge * r24.CESS_RATE
    clauses["cess"] = f"Health and Education Cess (4% on ₹{tax_plus_surcharge:,.0f}): ₹{cess:,.0f}"

    total_tax = round(tax_plus_surcharge + cess)

    return TaxComputation(
        gross_salary=user_input.gross_salary,
        deductions=deductions,
        taxable_income=taxable_income,
        tax_on_slabs=round(base_tax),
        rebate_87a=round(rebate_87a),
        tax_after_rebate=round(tax_after_rebate),
        surcharge=round(nom_surch),
        marginal_relief=round(marg_relief),
        surcharge_after_relief=round(eff_surch),
        cess=round(cess),
        total_tax=total_tax,
        clause_references=clauses,
    )


def compute_new_regime(
    user_input: TaxpayerInput,
    fy: str = "2024-25",
) -> TaxComputation:
    """Calculates tax under the New Tax Regime (Section 115BAC)."""
    deductions = DeductionBreakdown()
    clauses: dict[str, str] = {}

    is_fy25 = (fy == "2025-26")
    std_ded = r25.STANDARD_DEDUCTION_NEW if is_fy25 else r24.STANDARD_DEDUCTION_NEW
    slabs = r25.SLABS_NEW_FY25 if is_fy25 else r24.SLABS_NEW_FY24
    rebate_threshold = r25.REBATE_87A_THRESHOLD_NEW if is_fy25 else r24.REBATE_87A_THRESHOLD_NEW
    rebate_max = r25.REBATE_87A_MAX_NEW if is_fy25 else r24.REBATE_87A_MAX_NEW

    # Standard deduction only (no 80C, 80D, HRA, 24b allowed under 115BAC)
    deductions.standard_deduction = min(user_input.gross_salary, std_ded)
    clauses["standard_deduction"] = f"Section 16(ia) read with 115BAC: Standard deduction ₹{deductions.standard_deduction:,.0f}"
    clauses["other_deductions"] = "Section 115BAC(2): Deductions under 80C, 80D, 80CCD(1B), 24(b), and HRA are not allowed"
    
    total_deductions = deductions.compute_total()
    taxable_income = max(0.0, user_input.gross_salary - total_deductions)

    # Base tax on slabs
    base_tax, slab_desc = compute_slab_tax(taxable_income, slabs)
    clauses["slab_computation"] = "; ".join(slab_desc) if slab_desc else "No slab tax"

    # Section 87A Rebate with Marginal Relief for 115BAC
    rebate_87a = 0.0
    if taxable_income <= rebate_threshold:
        rebate_87a = min(base_tax, rebate_max)
        clauses["87A"] = (
            f"Section 87A (New Regime): Taxable income <= ₹{rebate_threshold:,.0f}, "
            f"full rebate up to ₹{rebate_max:,.0f} = ₹{rebate_87a:,.0f} (Net tax: ₹0)"
        )
    else:
        # Marginal relief under proviso to Section 87A:
        # Tax payable cannot exceed excess income over rebate threshold
        excess_income = taxable_income - rebate_threshold
        if base_tax > excess_income:
            rebate_87a = base_tax - excess_income
            clauses["87A"] = (
                f"Section 87A Proviso: Tax on ₹{taxable_income:,.0f} (₹{base_tax:,.0f}) exceeds "
                f"income above ₹{rebate_threshold:,.0f} (₹{excess_income:,.0f}). "
                f"Marginal relief rebate: ₹{rebate_87a:,.0f}"
            )
        else:
            clauses["87A"] = f"Section 87A: Taxable income > ₹{rebate_threshold:,.0f}, no rebate required"

    tax_after_rebate = max(0.0, base_tax - rebate_87a)

    # Surcharge & Marginal Relief
    nom_surch, marg_relief, eff_surch, surch_exp = compute_surcharge_and_marginal_relief(
        taxable_income=taxable_income,
        base_tax=tax_after_rebate,
        surcharge_brackets=r24.SURCHARGE_BRACKETS_NEW,
        slabs=slabs,
    )
    clauses["surcharge"] = surch_exp

    # Cess 4%
    tax_plus_surcharge = tax_after_rebate + eff_surch
    cess = tax_plus_surcharge * r24.CESS_RATE
    clauses["cess"] = f"Health and Education Cess (4% on ₹{tax_plus_surcharge:,.0f}): ₹{cess:,.0f}"

    total_tax = round(tax_plus_surcharge + cess)

    return TaxComputation(
        gross_salary=user_input.gross_salary,
        deductions=deductions,
        taxable_income=taxable_income,
        tax_on_slabs=round(base_tax),
        rebate_87a=round(rebate_87a),
        tax_after_rebate=round(tax_after_rebate),
        surcharge=round(nom_surch),
        marginal_relief=round(marg_relief),
        surcharge_after_relief=round(eff_surch),
        cess=round(cess),
        total_tax=total_tax,
        clause_references=clauses,
    )


def compute_break_even_deductions(
    gross_salary: float,
    fy: str = "2024-25",
    age_category: AgeCategory = AgeCategory.BELOW_60,
) -> float:
    """
    Computes the mathematical Indifference Point (Break-Even Deduction Threshold).
    Finds the exact total deductions D* such that:
        Tax_Old(gross_salary - D*) == Tax_New(gross_salary - std_ded)
    """
    if gross_salary <= 0:
        return 0.0

    dummy_input = TaxpayerInput(
        gross_salary=gross_salary,
        basic_salary=gross_salary * 0.5,
        age_category=age_category,
        financial_year=fy,
    )
    new_res = compute_new_regime(dummy_input, fy=fy)
    target_tax = new_res.total_tax

    if age_category == AgeCategory.SUPER_SENIOR_ABOVE_80:
        slabs = r24.SLABS_OLD_SUPER_SENIOR
    elif age_category == AgeCategory.SENIOR_60_TO_80:
        slabs = r24.SLABS_OLD_SENIOR
    else:
        slabs = r24.SLABS_OLD_BELOW_60

    low, high = 0.0, float(gross_salary)
    for _ in range(40):
        mid = (low + high) / 2.0
        tax, _ = compute_slab_tax(mid, slabs)
        if mid <= r24.REBATE_87A_THRESHOLD_OLD:
            tax = max(0.0, tax - min(tax, r24.REBATE_87A_MAX_OLD))
        tot = round(tax * 1.04)
        if tot > target_tax:
            high = mid
        else:
            low = mid

    target_taxable = (low + high) / 2.0
    return max(0.0, float(round(gross_salary - target_taxable)))


def compute_tax(user_input: TaxpayerInput, fy: str = "2024-25") -> TaxResult:
    """
    Computes tax under both Old and New regimes, identifies the recommended
    regime with highest savings, and produces an auditable breakdown.
    """
    old_comp = compute_old_regime(user_input, fy=fy)
    new_comp = compute_new_regime(user_input, fy=fy)

    if new_comp.total_tax < old_comp.total_tax:
        rec = "New Tax Regime"
        savings = old_comp.total_tax - new_comp.total_tax
        reason = (
            f"The New Tax Regime is more beneficial, saving you ₹{savings:,.0f}. "
            f"Under the New Regime your tax liability is ₹{new_comp.total_tax:,.0f} "
            f"compared to ₹{old_comp.total_tax:,.0f} under the Old Regime."
        )
    elif old_comp.total_tax < new_comp.total_tax:
        rec = "Old Tax Regime"
        savings = new_comp.total_tax - old_comp.total_tax
        reason = (
            f"The Old Tax Regime is more beneficial, saving you ₹{savings:,.0f}. "
            f"Your deductions of ₹{old_comp.deductions.total:,.0f} (80C, 80D, HRA, etc.) "
            f"significantly reduce your taxable income from ₹{user_input.gross_salary:,.0f} "
            f"to ₹{old_comp.taxable_income:,.0f}."
        )
    else:
        rec = "Either Regime"
        savings = 0.0
        reason = (
            f"Both regimes yield an identical tax liability of ₹{new_comp.total_tax:,.0f}. "
            f"You may choose either regime."
        )

    # Calculate deduction headroom & proactive advisory notes
    headroom = {
        "section_80c": max(0.0, 150_000.0 - user_input.investment_80c),
        "section_80ccd_1b": max(0.0, 50_000.0 - user_input.investment_80ccd_1b),
        "section_80d_self": max(0.0, (50_000.0 if user_input.age_category != AgeCategory.BELOW_60 else 25_000.0) - user_input.health_insurance_self),
        "section_80d_parents": max(0.0, (50_000.0 if user_input.parents_are_senior_citizens else 25_000.0) - user_input.health_insurance_parents),
        "home_loan_interest_24b": max(0.0, 200_000.0 - user_input.home_loan_interest),
    }

    advisory_notes = []
    if headroom["section_80c"] > 0:
        advisory_notes.append(f"You have ₹{headroom['section_80c']:,.0f} unused headroom under Section 80C (PPF/ELSS/EPF).")
    if headroom["section_80ccd_1b"] > 0:
        advisory_notes.append(f"You have ₹{headroom['section_80ccd_1b']:,.0f} unused headroom under Section 80CCD(1B) for NPS.")
    if headroom["section_80d_self"] > 0 or headroom["section_80d_parents"] > 0:
        tot_80d = headroom["section_80d_self"] + headroom["section_80d_parents"]
        advisory_notes.append(f"You have ₹{tot_80d:,.0f} additional headroom for health insurance under Section 80D.")

    # Calculate break-even indifference deduction threshold
    break_even_d = compute_break_even_deductions(
        gross_salary=user_input.gross_salary,
        fy=fy,
        age_category=user_input.age_category,
    )
    current_deductions = old_comp.deductions.total
    break_even_gap = max(0.0, break_even_d - current_deductions)

    if current_deductions >= break_even_d:
        be_analysis = (
            f"Your current total deductions of ₹{current_deductions:,.0f} exceed the break-even "
            f"threshold of ₹{break_even_d:,.0f}. The Old Regime is mathematically optimal."
        )
    else:
        be_analysis = (
            f"The break-even deduction threshold is ₹{break_even_d:,.0f}. With your current deductions "
            f"of ₹{current_deductions:,.0f}, you need an additional ₹{break_even_gap:,.0f} in eligible "
            f"deductions (HRA, 80C, 80D, NPS) for the Old Regime to match or beat the New Regime."
        )

    return TaxResult(
        old_regime=old_comp,
        new_regime=new_comp,
        recommended_regime=rec,
        savings=savings,
        explanation=reason,
        deduction_headroom=headroom,
        advisory_notes=advisory_notes,
        break_even_deductions=break_even_d,
        break_even_gap=break_even_gap,
        break_even_analysis=be_analysis,
    )
