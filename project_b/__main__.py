"""
CLI entry point for Project B NYC 311 Data Quality Engine.
Usage:
  python -m project_b profile
  python -m project_b benchmark
  python -m project_b pipeline --batch 2000
"""

import argparse
from project_b.profiler import profile_raw_data, generate_markdown_profile
from project_b.benchmark import run_project_b_benchmark
from project_b.hybrid_pipeline import HybridDataQualityPipeline
from project_b.data_loader import load_dataset
from project_b.injector import CorruptionInjector


def main():
    parser = argparse.ArgumentParser(description="NYC 311 Data-Quality Engine")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("profile", help="Run raw data profiling on NYC 311 dataset")
    subparsers.add_parser("benchmark", help="Run empirical benchmark of quality detectors")
    
    pipe_p = subparsers.add_parser("pipeline", help="Run the 3-tier hybrid quality pipeline on sample data")
    pipe_p.add_argument("--batch", type=int, default=2000, help="Number of rows to test")
    pipe_p.add_argument("--corrupt", action="store_true", default=True, help="Inject 5% test corruptions")

    args = parser.parse_args()

    if args.command == "profile":
        print("Running NYC 311 Data Profiler...")
        df = load_dataset(sample_size=25_000)
        profile = profile_raw_data(df)
        md_report = generate_markdown_profile(profile)
        print("\n" + md_report)
    elif args.command == "benchmark":
        run_project_b_benchmark(batch_size=5000)
    elif args.command == "pipeline":
        print(f"Loading {args.batch} records and running 3-tiered Hybrid Quality Pipeline...")
        df = load_dataset(args.batch).head(args.batch).copy()
        if args.corrupt:
            injector = CorruptionInjector()
            df, _ = injector.inject_all(df, rate=0.05)
            print(f"Injected 5% corruptions. Testing {len(df)} total rows.")
        
        pipeline = HybridDataQualityPipeline()
        metrics = pipeline.run(df)
        print("\n==================================================")
        print(" HYBRID DATA QUALITY PIPELINE BATCH EXECUTION")
        print("==================================================")
        print(f" Total Rows Evaluated:      {metrics.total_rows:,}")
        print(f" Quarantined Rows:          {len(metrics.quarantined_row_indices):,} ({(len(metrics.quarantined_row_indices)/metrics.total_rows)*100:.1f}%)")
        print(f" Total Execution Time:      {metrics.total_time_seconds:.3f} seconds")
        print(f" Layer 1 (Rules) Flags:     {sum(metrics.layer1_flags.values()):,}")
        for k, v in metrics.layer1_flags.items():
            if v > 0:
                print(f"   - {k}: {v}")
        print(f" Layer 2 (Stats) Flags:     {sum(metrics.layer2_flags.values()):,}")
        for k, v in metrics.layer2_flags.items():
            if v > 0:
                print(f"   - {k}: {v}")
        print(f" Layer 3 (LLM) Confirmed:   {sum(metrics.layer3_confirmations.values()):,}")
        for k, v in metrics.layer3_confirmations.items():
            if v > 0:
                print(f"   - {k}: {v}")
        print(f" LLM Tokens Used:           {metrics.tokens_used:,}")
        print(f" LLM Cost:                  ${metrics.llm_cost_dollars:.4f}")
        print("==================================================")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
