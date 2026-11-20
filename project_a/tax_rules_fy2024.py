"""
Tax Rules and Constants for FY 2024-25 (Assessment Year 2025-26).
Official sources: Income-tax Act, 1961, read with Finance Act 2024 (No. 2).
"""

from typing import List, Tuple

# Financial Year
FY_LABEL = "2024-25"
AY_LABEL = "2025-26"

# Standard Deduction under Section 16(ia)
STANDARD_DEDUCTION_OLD = 50_000.0
STANDARD_DEDUCTION_NEW = 75_000.0

# Slabs for Old Regime: (lower_limit, upper_limit, rate)
# Individuals < 60 years
SLABS_OLD_BELOW_60: List[Tuple[float, float, float]] = [
    (0.0, 250_000.0, 0.0),
    (250_000.0, 500_000.0, 0.05),
    (500_000.0, 1_000_000.0, 0.20),
    (1_000_000.0, float("inf"), 0.30),
]

# Senior citizens (60 to 80 years)
SLABS_OLD_SENIOR: List[Tuple[float, float, float]] = [
    (0.0, 300_000.0, 0.0),
    (300_000.0, 500_000.0, 0.05),
    (500_000.0, 1_000_000.0, 0.20),
    (1_000_000.0, float("inf"), 0.30),
]

# Super senior citizens (80+ years)
SLABS_OLD_SUPER_SENIOR: List[Tuple[float, float, float]] = [
    (0.0, 500_000.0, 0.0),
    (500_000.0, 1_000_000.0, 0.20),
    (1_000_000.0, float("inf"), 0.30),
]

# Slabs for New Regime (Section 115BAC(1A) as amended by Finance (No. 2) Act 2024)
SLABS_NEW_FY24: List[Tuple[float, float, float]] = [
    (0.0, 300_000.0, 0.0),
    (300_000.0, 700_000.0, 0.05),
    (700_000.0, 1_000_000.0, 0.10),
    (1_000_000.0, 1_200_000.0, 0.15),
    (1_200_000.0, 1_500_000.0, 0.20),
    (1_500_000.0, float("inf"), 0.30),
]

# Section 87A Rebate Thresholds & Limits
REBATE_87A_THRESHOLD_OLD = 500_000.0
REBATE_87A_MAX_OLD = 12_500.0

REBATE_87A_THRESHOLD_NEW = 700_000.0
REBATE_87A_MAX_NEW = 25_000.0

# Deductions Limits (Old Regime only)
MAX_80C = 150_000.0
MAX_80CCD_1B = 50_000.0
MAX_80D_SELF_NON_SENIOR = 25_000.0
MAX_80D_SELF_SENIOR = 50_000.0
MAX_80D_PARENTS_NON_SENIOR = 25_000.0
MAX_80D_PARENTS_SENIOR = 50_000.0
MAX_HOME_LOAN_INTEREST_24B = 200_000.0  # self-occupied

# HRA Percentages (Rule 2A)
HRA_PERCENTAGE_METRO = 0.50
HRA_PERCENTAGE_NON_METRO = 0.40

# Surcharge Brackets: (threshold, surcharge_rate)
# Note: Marginal relief applies at each threshold transition
SURCHARGE_BRACKETS_OLD: List[Tuple[float, float]] = [
    (5_000_000.0, 0.10),      # > 50 Lakhs up to 1 Crore
    (10_000_000.0, 0.15),     # > 1 Crore up to 2 Crores
    (20_000_000.0, 0.25),     # > 2 Crores up to 5 Crores
    (50_000_000.0, 0.37),     # > 5 Crores
]

SURCHARGE_BRACKETS_NEW: List[Tuple[float, float]] = [
    (5_000_000.0, 0.10),      # > 50 Lakhs up to 1 Crore
    (10_000_000.0, 0.15),     # > 1 Crore up to 2 Crores
    (20_000_000.0, 0.25),     # > 2 Crores (capped at 25%)
]

# Health and Education Cess (Finance Act)
CESS_RATE = 0.04
