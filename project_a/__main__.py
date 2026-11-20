"""
CLI entry point for Project A Income Tax Engine.
Usage:
  python -m project_a tax --text "Mera salary 15 LPA hai, Mumbai me rent 30k bharta hu"
  python -m project_a tax --gross 1500000 --basic 750000 --rent 360000 --metro --c80 150000 --fy 2024-25
  python -m project_a benchmark
"""

import argparse
import json
import sys
from project_a.models import TaxpayerInput, City, AgeCategory
from project_a.rules_handcoded import compute_tax
from project_a.nlp_parser import parse_plain_language
from project_a.benchmark import run_benchmark


def main():
    parser = argparse.ArgumentParser(description="Indian Income-Tax Engine (FY 2024-25 & FY 2025-26)")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Tax calculation command
    tax_p = subparsers.add_parser("tax", help="Calculate tax for a profile or text description")
    tax_p.add_argument("--text", type=str, help="Free-text salary/tax description (English/Hinglish)")
    tax_p.add_argument("--gross", type=float, default=0.0, help="Annual gross salary")
    tax_p.add_argument("--basic", type=float, default=0.0, help="Annual basic salary")
    tax_p.add_argument("--hra", type=float, default=0.0, help="Annual HRA received")
    tax_p.add_argument("--rent", type=float, default=0.0, help="Annual rent paid")
    tax_p.add_argument("--metro", action="store_true", help="Set if residing in Metro city (Mumbai, Delhi, Kolkata, Chennai)")
    tax_p.add_argument("--c80", type=float, default=0.0, help="Section 80C investments (PPF/ELSS/EPF)")
    tax_p.add_argument("--nps", type=float, default=0.0, help="Section 80CCD(1B) NPS contribution")
    tax_p.add_argument("--health-self", type=float, default=0.0, help="Section 80D health insurance (self/family)")
    tax_p.add_argument("--health-parents", type=float, default=0.0, help="Section 80D health insurance (parents)")
    tax_p.add_argument("--senior-parents", action="store_true", help="Set if parents are senior citizens (60+)")
    tax_p.add_argument("--home-loan", type=float, default=0.0, help="Section 24(b) home loan interest")
    tax_p.add_argument("--fy", type=str, default="2024-25", choices=["2024-25", "2025-26"], help="Financial Year")

    tax_p.add_argument("--advisor", action="store_true", help="Generate proactive tax optimization recommendations")

    # Benchmark command
    subparsers.add_parser("benchmark", help="Run Project A empirical benchmarks")

    args = parser.parse_args()

    if args.command == "benchmark":
        run_benchmark(sample_size=20, repeats=10)
        return

    if args.command == "tax":
        if args.text:
            print(f"\n--- Parsing Plain-Language Input ---\n\"{args.text}\"\n")
            parse_res = parse_plain_language(args.text, fy=args.fy)
            if not parse_res.is_complete:
                print("⚠️ Incomplete Information. Clarifying questions required:")
                for i, q in enumerate(parse_res.questions, 1):
                    print(f"  {i}. [{q.field}] {q.question}")
                    print(f"     Reason: {q.reason}")
                return
            inp = parse_res.parsed_input
        else:
            if args.gross <= 0:
                print("Error: Please provide --gross salary or --text description.")
                sys.exit(1)
            basic = args.basic if args.basic > 0 else args.gross * 0.5
            city = City.METRO if args.metro else City.NON_METRO
            inp = TaxpayerInput(
                gross_salary=args.gross,
                basic_salary=basic,
                hra_received=args.hra,
                rent_paid_annual=args.rent,
                city=city,
                investment_80c=args.c80,
                investment_80ccd_1b=args.nps,
                health_insurance_self=args.health_self,
                health_insurance_parents=args.health_parents,
                parents_are_senior_citizens=args.senior_parents,
                home_loan_interest=args.home_loan,
                financial_year=args.fy,
            )

        # Compute tax
        res = compute_tax(inp, fy=args.fy)
        print(f"==================================================")
        print(f" TAX COMPUTATION RESULT (FY {args.fy})")
        print(f"==================================================")
        print(f" Gross Salary:        ₹{inp.gross_salary:,.0f}")
        print(f" Basic Salary:        ₹{inp.basic_salary:,.0f}")
        print(f"--------------------------------------------------")
        print(f" OLD REGIME TAX:")
        print(f"   Total Deductions:  ₹{res.old_regime.deductions.total:,.0f}")
        print(f"   Taxable Income:    ₹{res.old_regime.taxable_income:,.0f}")
        print(f"   Tax on Slabs:      ₹{res.old_regime.tax_on_slabs:,.0f}")
        print(f"   Rebate (87A):      ₹{res.old_regime.rebate_87a:,.0f}")
        print(f"   Surcharge:         ₹{res.old_regime.surcharge_after_relief:,.0f}")
        print(f"   Cess (4%):         ₹{res.old_regime.cess:,.0f}")
        print(f"   TOTAL TAX:         ₹{res.old_regime.total_tax:,.0f}")
        print(f"--------------------------------------------------")
        print(f" NEW REGIME TAX:")
        print(f"   Standard Ded:      ₹{res.new_regime.deductions.standard_deduction:,.0f}")
        print(f"   Taxable Income:    ₹{res.new_regime.taxable_income:,.0f}")
        print(f"   Tax on Slabs:      ₹{res.new_regime.tax_on_slabs:,.0f}")
        print(f"   Rebate (87A):      ₹{res.new_regime.rebate_87a:,.0f}")
        print(f"   Surcharge:         ₹{res.new_regime.surcharge_after_relief:,.0f}")
        print(f"   Cess (4%):         ₹{res.new_regime.cess:,.0f}")
        print(f"   TOTAL TAX:         ₹{res.new_regime.total_tax:,.0f}")
        print(f"==================================================")
        print(f" RECOMMENDATION:      {res.recommended_regime}")
        print(f" POTENTIAL SAVINGS:   ₹{res.savings:,.0f}")
        print(f" Summary: {res.explanation}")

        if args.advisor or True:
            from project_a.tax_advisor import generate_proactive_advice
            print("--------------------------------------------------")
            print(" 💡 PROACTIVE TAX OPTIMIZATION ADVICE:")
            advice = generate_proactive_advice(inp, res)
            for idx, pt in enumerate(advice, 1):
                print(f"   {idx}. {pt}")
        print(f"==================================================")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
