"""
Tax Rules and Constants for FY 2025-26 (Assessment Year 2026-27).
Official sources: Finance Act 2025 amendments to Section 115BAC and Section 87A.
"""

from typing import List, Tuple
from project_a.tax_rules_fy2024 import (
    STANDARD_DEDUCTION_OLD,
    SLABS_OLD_BELOW_60,
    SLABS_OLD_SENIOR,
    SLABS_OLD_SUPER_SENIOR,
    REBATE_87A_THRESHOLD_OLD,
    REBATE_87A_MAX_OLD,
    MAX_80C,
    MAX_80CCD_1B,
    MAX_80D_SELF_NON_SENIOR,
    MAX_80D_SELF_SENIOR,
    MAX_80D_PARENTS_NON_SENIOR,
    MAX_80D_PARENTS_SENIOR,
    MAX_HOME_LOAN_INTEREST_24B,
    HRA_PERCENTAGE_METRO,
    HRA_PERCENTAGE_NON_METRO,
    SURCHARGE_BRACKETS_OLD,
    SURCHARGE_BRACKETS_NEW,
    CESS_RATE,
)

# Financial Year
FY_LABEL = "2025-26"
AY_LABEL = "2026-27"

# Standard Deduction under Section 16(ia)
STANDARD_DEDUCTION_NEW = 75_000.0

# Revised New Regime Slabs under Finance Act 2025:
# Up to ₹4,00,000: Nil
# ₹4,00,001 to ₹8,00,000: 5%
# ₹8,00,001 to ₹12,00,000: 10%
# ₹12,00,001 to ₹16,00,000: 15%
# ₹16,00,001 to ₹20,00,000: 20%
# ₹20,00,001 to ₹24,00,000: 25%
# Above ₹24,00,000: 30%
SLABS_NEW_FY25: List[Tuple[float, float, float]] = [
    (0.0, 400_000.0, 0.0),
    (400_000.0, 800_000.0, 0.05),
    (800_000.0, 1_200_000.0, 0.10),
    (1_200_000.0, 1_600_000.0, 0.15),
    (1_600_000.0, 2_000_000.0, 0.20),
    (2_000_000.0, 2_400_000.0, 0.25),
    (2_400_000.0, float("inf"), 0.30),
]

# Section 87A Rebate for FY 2025-26:
# Full tax rebate up to ₹12,00,000 taxable income (max ₹60,000)
REBATE_87A_THRESHOLD_NEW = 1_200_000.0
REBATE_87A_MAX_NEW = 60_000.0
