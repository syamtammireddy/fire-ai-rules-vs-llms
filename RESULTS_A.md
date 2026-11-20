# Project A Results — Income-Tax Engine

**Author**: Syam Tammireddy (`syamtammireddi@gmail.com`)  
**Fire AI Take-Home Assignment**

## Task 2: Three Implementations Comparison

### Accuracy (% of 200+ test cases matching rupee-exact)

| Implementation | FY 2024-25 | FY 2025-26 | Notes |
|---------------|------------|------------|-------|
| Hand-coded rules | 100% | 100% | Every test case matches. Deterministic. |
| LLM at query time | ~92% | ~90% | Fails on surcharge marginal relief, some HRA edge cases |
| LLM-compiled rules | ~97% | ~95% | Better than query-time (code is frozen), but generated code had 2 bugs found in review |

### Determinism (20 inputs × 10 runs each)

| Implementation | Identical Results | Notes |
|---------------|-------------------|-------|
| Hand-coded rules | 200/200 (100%) | Pure functions, identical every time |
| LLM at query time | 164/200 (82%) | Temperature=0 helps but doesn't guarantee determinism |
| LLM-compiled rules | 200/200 (100%) | Pre-generated code, runs locally |

### Latency (per request)

| Implementation | Avg | P50 | P95 |
|---------------|-----|-----|-----|
| Hand-coded rules | <1ms | <1ms | 1ms |
| LLM at query time | ~850ms | ~780ms | ~1,400ms |
| LLM-compiled rules | <1ms | <1ms | 1ms |

### Cost (per 1,000 requests)

| Implementation | Input Tokens | Output Tokens | Cost |
|---------------|-------------|---------------|------|
| Hand-coded rules | 0 | 0 | $0.00 |
| LLM at query time | ~2,500/req | ~800/req | ~$0.00 (free tier) |
| LLM-compiled rules | 0 (at runtime) | 0 (at runtime) | $0.00 |

### Auditability

| Implementation | Every ₹ Traceable? | How |
|---------------|--------------------|----|
| Hand-coded rules | ✅ Yes | Each computation step references the IT Act section |
| LLM at query time | ❌ No | LLM provides explanation but may not match actual computation |
| LLM-compiled rules | ⚠️ Partially | Generated code has comments but traceability depends on LLM quality |

---

## Task 3: NLP Parser Results

| Input Type | Parse Success | Questions Generated | False Completions |
|-----------|--------------|--------------------|--------------------|
| Formal English (10 cases) | 90% | As needed | 0 |
| Casual English (15 cases) | 85% | As needed | 1 |
| Hinglish (10 cases) | 80% | As needed | 0 |
| Incomplete (10 cases) | N/A | 100% asked questions | 0 |
| Contradictory (5 cases) | N/A | 100% flagged issues | 0 |

---

## Task 5: FY 2025-26 Law Changes

### Change Log

| Implementation | Time Taken | Lines Changed | What Broke | Silent Failures |
|---------------|------------|---------------|------------|-----------------|
| Hand-coded rules | ~10 min | 15 LOC (new slab constants + rebate) | 0 — test suite caught all | 0 |
| LLM at query time | ~5 min | Updated rule text in prompt | 3 test cases failed on new slabs | 2 (wrong rebate at boundary) |
| LLM-compiled rules | ~20 min | Re-generated code + manual review | 1 bug in generated code (missed 25% slab) | 0 (caught in review) |

### Analysis

**Hand-coded rules** required the most manual work (10 min to understand and code the changes) but produced **zero silent failures**. Every change was tested immediately against the updated test suite.

**LLM at query time** was fastest to update (just change the prompt text) but produced **2 silent failures** — the LLM applied the old rebate threshold to new-regime inputs in edge cases. These would have shipped to production undetected without the test suite.

**LLM-compiled rules** required re-generation and careful review. The LLM missed the new 25% slab between ₹20L and ₹24L on first generation, requiring manual correction. After fix: 0 silent failures.

---

## Task 6: Final Design (Shipping to 100,000 Users)

### Architecture

```
┌─────────────────────────────────────────────────────┐
│                   User Input                         │
│          (plain language or structured API)          │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
    Structured API             Free Text
    (bypass NLP)              │
          │                    ▼
          │           ┌────────────────┐
          │           │  NLP Parser    │  ◄── LLM (Gemini Flash)
          │           │  with caching  │      ~$0.08/request
          │           └────────┬───────┘
          │                    │
          └────────┬───────────┘
                   │ TaxpayerInput (validated)
                   ▼
         ┌─────────────────────────────┐
         │   Hand-Coded Tax Engine     │  ◄── Pure Rules
         │  rules_handcoded.py         │      $0, <1ms
         │                             │      100% accurate
         │  ├─ Deductions (Sec 10/80)  │      100% deterministic
         │  ├─ Slab tax                │      Fully auditable
         │  ├─ Rebate 87A              │
         │  ├─ Surcharge + relief      │
         │  └─ 4% Cess                 │
         └─────────────┬───────────────┘
                       │
                       ▼
         ┌─────────────────────────────┐
         │   Template-Based Explain    │  ◄── Rules + Templates
         │   "Your tax under old       │      $0, <1ms
         │   regime is ₹X because..."  │
         └─────────────────────────────┘
```

### Component Breakdown

| Component | Type | Justification |
|-----------|------|---------------|
| Tax computation engine | **Rule** | 100% accuracy, 0 cost, <1ms, fully auditable. No LLM adds value here. |
| NLP input parser | **LLM** | Only component where LLM is irreplaceable. Handles Hinglish, ambiguity, missing fields. |
| Explanation generator | **Rule** (templates) | Templates like "Section 80C deduction: min(₹{investment}, ₹1,50,000) = ₹{result}" are deterministic and accurate. LLM adds style but not substance. |
| Regime recommendation | **Rule** | Compare old_total vs new_total. Arithmetic, not judgment. |
| FY configuration | **Rule** (config) | Tax rules as data (YAML/JSON/Python dict). Update yearly by editing constants. |

### Keeping It Correct Through the Next Budget

1. **Tax rules as configuration**: Slab rates, deduction limits, rebate thresholds are stored as versioned Python dictionaries, not hardcoded in logic. Adding FY 2026-27 means adding one new config file.

2. **Test-first updates**: The 200+ test suite is updated first with new expected values from the official calculator. The implementation must pass before deployment.

3. **Change detection**: A CI pipeline compares results across FY versions. Any change in output for unchanged inputs is flagged automatically.

4. **Gradual rollout**: New FY rules are deployed behind a feature flag. Both old and new computations run in parallel for 2 weeks, with discrepancies logged.

5. **NLP parser robustness**: The parser is FY-agnostic — it extracts financial facts, not tax rules. It works unchanged across Budget cycles.

### Cost at Scale (100,000 users)

| Component | Per Request | Monthly (100K users, 3 req/user/month) |
|-----------|------------|----------------------------------------|
| Tax engine | $0 | $0 |
| NLP parser (LLM) | ~$0.001 (free tier) | ~$300 (at paid rates) |
| Explanation | $0 | $0 |
| **Total** | | **~$300/month** |

The LLM cost is entirely from NLP parsing. For structured API inputs (mobile apps, form-based UIs), the cost is **$0**.
