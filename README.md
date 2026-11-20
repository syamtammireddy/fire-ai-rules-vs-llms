# Rules vs LLMs — Take-Home Assignment

**Candidate**: Syam Tammireddy (`syamtammireddi@gmail.com`)  
**Fire AI · Rules vs LLMs Assignment**

## Quick Start

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd rules-vs-llms

# 2. Set up environment
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY

# 3. Install dependencies and run everything
make all
```

This single command will:
1. Set up the Python virtual environment
2. Install all dependencies
3. Run all Project A tests (200+ tax calculation test cases)
4. Run all Project B tests (injector, detectors, pipeline)
5. Run Project A benchmarks (accuracy, determinism, latency, cost)
6. Run Project B benchmarks (detection rate, false alarm rate, cost)

## Project Structure

```
├── project_a/                 # Income-Tax Engine
│   ├── models.py              # Pydantic data models
│   ├── tax_rules_fy2024.py    # FY 2024-25 tax constants
│   ├── tax_rules_fy2025.py    # FY 2025-26 tax constants (law change)
│   ├── rules_handcoded.py     # Task 2a: Hand-coded rules
│   ├── rules_llm_query.py     # Task 2b: LLM at query time
│   ├── rules_llm_compiled.py  # Task 2c: LLM-compiled rules
│   ├── nlp_parser.py          # Task 3: Plain-language parser
│   ├── benchmark.py           # Task 4: Measurement harness
│   └── tests/                 # 200+ test cases + NLP test cases
├── project_b/                 # Data-Quality Checks
│   ├── data_loader.py         # NYC 311 data download & cache
│   ├── profiler.py            # Task 1: Raw data profiling
│   ├── injector.py            # Task 2: 12-type corruption injector
│   ├── detectors/
│   │   ├── rule_detectors.py  # Task 3a: Declarative rules
│   │   ├── stat_detectors.py  # Task 3b: Statistical/ML detectors
│   │   └── llm_detectors.py   # Task 3c: LLM review
│   ├── hybrid_pipeline.py     # Task 5: Combined pipeline
│   ├── benchmark.py           # Task 4: Measurement harness
│   └── tests/
├── RESULTS_A.md               # Project A comparison & final design
├── RESULTS_B.md               # Project B detection & scale design
├── DECISION_MATRIX.md         # Rule vs LLM justification per component
├── AI_USAGE.md                # AI tool usage log
├── Makefile                   # Single-command reproduction
└── pyproject.toml             # Dependencies
```

## Individual Commands

```bash
make test-a          # Run Project A tests only
make test-b          # Run Project B tests only
make benchmark-a     # Run Project A benchmarks
make benchmark-b     # Run Project B benchmarks
make profile-b       # Profile NYC 311 raw data
make download-data   # Download NYC 311 2023 data
```

## Interactive CLI Usage

### Project A — Income Tax Engine CLI
```bash
# 1. Plain-language input (English / Hinglish):
python -m project_a tax --text "Mera salary 15 LPA hai, Mumbai me rent 30k bharta hu"

# 2. Incomplete input (automatically triggers clarifying questions):
python -m project_a tax --text "I pay 30,000 rent in Mumbai. How much tax do I save?"

# 3. Direct structured calculation (FY 2024-25 or FY 2025-26):
python -m project_a tax --gross 1500000 --rent 360000 --metro --c80 150000 --fy 2024-25
python -m project_a tax --gross 1500000 --rent 360000 --metro --c80 150000 --fy 2025-26
```

### Project B — Data Quality Pipeline CLI
```bash
# Run 3-tier hybrid pipeline (Rules -> Stats -> LLM) on sample batch:
python -m project_b pipeline --batch 1000

# Profile NYC 311 raw dataset:
python -m project_b profile
```

## Requirements

- Python 3.10+
- Gemini API key (free tier)
- ~500MB disk space for NYC 311 data

## Design Philosophy

**Rules dominate where logic is deterministic.** Tax computation is pure arithmetic — it deserves hand-coded rules that are auditable, testable, and instant. The LLM adds value only for natural-language understanding (parsing free-text inputs) and as a one-time code generator (LLM-compiled rules).

**Data quality checks follow the same principle.** Schema validation, date logic, and geographic bounds are cheaper and more reliable as rules. LLMs are reserved for semantic judgment calls that rules can't make: resolution-status contradictions and near-duplicate confirmation.

See [DECISION_MATRIX.md](DECISION_MATRIX.md) for the full breakdown with measurements.
