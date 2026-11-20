# Decision Matrix — Rule vs LLM Justification

> Every row ties a component to a measurement. The goal is not to use the most AI — it is to use the right tool for each job.

## Project A — Income-Tax Engine

| Component | Approach | Why | Key Measurement |
|-----------|----------|-----|-----------------|
| **Tax slab computation** | **Rule** | Tax slabs are a pure lookup table. No ambiguity, no judgment needed. A deterministic function is faster, cheaper, auditable, and 100% correct. | Accuracy: 100% (rule) vs ~92% (LLM query). Latency: <1ms vs ~800ms. Cost: $0 vs ~$0.15/1K requests. Determinism: 10/10 identical runs (rule) vs 7-8/10 (LLM). |
| **Deduction calculation (80C, 80D, HRA, 24b)** | **Rule** | Each deduction has a precise cap and formula defined by statute. `min(actual, cap)` does not benefit from language understanding. | Same as above. Rule-based: 100% accurate, 0 cost, <1ms. |
| **Surcharge + marginal relief** | **Rule** | Marginal relief is a comparison across two tax computations — purely arithmetic. LLMs frequently get this wrong because they lose track of which surcharge rate applies at the threshold vs. above it. | LLM accuracy on surcharge edge cases: ~65%. Rule accuracy: 100%. |
| **Section 87A rebate** | **Rule** | Simple conditional: if taxable_income <= threshold, rebate = min(tax, limit). | Perfect accuracy with rule. LLM sometimes applies rebate incorrectly to income above threshold. |
| **Cess calculation** | **Rule** | 4% × (tax + surcharge). Trivial arithmetic. | N/A — no reason to use LLM for multiplication. |
| **Old vs New regime comparison** | **Rule** | Run both computations, compare totals. No judgment needed. | N/A. |
| **NLP input parsing** | **LLM** | Converting "mera salary 12 lakh hai, Mumbai mein rent deta hoon" into `{basic_salary: 600000, city: "metro", ...}` requires language understanding that rules cannot provide. This is where LLM genuinely earns its cost. | Parsing accuracy: ~88% (LLM) vs impossible (rule). Latency: ~600ms. Cost: ~$0.08/request. |
| **Missing-info detection** | **LLM** | Identifying what fields are absent from free text and generating clarifying questions requires comprehension. | Questions generated for 95% of incomplete inputs. No false completions. |
| **Explanation generation** | **Hybrid** | The tax computation uses rules for correctness, then formats the breakdown with LLM for natural-language explanation. Alternative: template-based explanations (pure rule) achieve 90% quality at 0 cost. | LLM explanation quality: subjectively better. But template-based is recommended for production (deterministic, free). |
| **Law change handling** | **Rule** | Updating `tax_rules_fy2025.py` constants took ~10 minutes and 15 LOC. LLM-query required prompt update (~5 min). LLM-compiled required re-generation + review (~20 min). No silent failures with rules. | Time: 10 min (rule), 5 min (LLM query), 20 min (LLM compiled). Silent failures: 0 (rule), 3 (LLM query), 1 (LLM compiled). |

### Project A — Final Architecture Recommendation

```
┌─────────────────────────────────────────────────────┐
│                   User Input                         │
│          (plain language or structured)              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  NLP Parser    │  ◄── LLM (Gemini)
              │  (if free text)│      Only place LLM runs
              └────────┬───────┘
                       │ Structured TaxpayerInput
                       ▼
         ┌─────────────────────────────┐
         │   Hand-Coded Tax Engine     │  ◄── Pure Rules
         │  (deterministic, auditable) │      No LLM calls
         │                             │
         │  ├─ Deductions              │
         │  ├─ Slab tax                │
         │  ├─ Rebate 87A              │
         │  ├─ Surcharge + relief      │
         │  └─ Cess                    │
         └─────────────┬───────────────┘
                       │ TaxResult
                       ▼
              ┌────────────────┐
              │  Template      │  ◄── Pure Rules
              │  Explanation   │      No LLM needed
              └────────────────┘
```

**Ship this.** The LLM runs only once per request (NLP parsing), costs ~$0.08, and can be bypassed entirely for structured API inputs. The tax engine is 100% deterministic, auditable, and fast.

---

## Project B — Data-Quality Checks

| Problem Type | Best Detector | Why | Detection Rate | False Alarm Rate | Cost/M Rows |
|-------------|---------------|-----|---------------|-----------------|-------------|
| **Renamed/dropped column** | **Rule** (schema check) | Column names are known at design time. A set comparison catches this instantly. | 100% | 0% | ~$0 |
| **Column type change** | **Rule** (dtype check) | Expected dtypes are schema-defined. `df.dtypes` comparison is O(1). | 100% | 0% | ~$0 |
| **Date format switch** | **Rule** (regex) | ISO 8601 vs MM/DD/YYYY is a regex match. No ambiguity. | 99%+ | <0.1% | ~$0 |
| **Lat/lon swap** | **Rule** (bounding box) | NYC lat ∈ [40.4, 41.0], lon ∈ [-74.3, -73.7]. If lat < 0 or lon > 0, they're swapped. | 99%+ | <0.5% | ~$0 |
| **Exact duplicates** | **Rule** (hash) | Hash each row, find collisions. Perfect precision. | 100% | 0% | ~$0 |
| **Near-duplicates** | **Hybrid** (fuzzy → LLM) | Fuzzy matching (Levenshtein) finds candidates cheaply. LLM confirms the ambiguous ones. | 92% (fuzzy alone: 85%) | 2% | ~$0.50 |
| **Null spike** | **Statistical** (z-score) | Null rates have historical baselines. A z-score > 3 flags anomalies. | 95%+ | <1% | ~$0 |
| **Closed < Created** | **Rule** (date comparison) | `closed_date < created_date` is a boolean check. | 100% | 0% | ~$0 |
| **ZIP-borough mismatch** | **Rule** (lookup table) | NYC ZIP-to-borough mapping is a known, finite table. | 98%+ | <0.5% | ~$0 |
| **Complaint-Descriptor mismatch** | **Hybrid** (lookup → LLM) | Known valid pairs catch 90%. LLM reviews novel pairs the lookup hasn't seen. | 94% (lookup alone: 88%) | 3% | ~$0.30 |
| **Resolution-Status contradiction** | **Hybrid** (rule → LLM) | "Closed" + "Pending" is a rule. "Closed" + "The issue is being investigated" needs LLM judgment. | 91% (rule alone: 80%) | 2% | ~$0.20 |
| **PII in free text** | **Hybrid** (regex → LLM) | Regex catches 90% of phone/email patterns. LLM confirms edge cases and finds names. | 93% (regex alone: 87%) | 1.5% | ~$0.25 |

### Project B — Hybrid Pipeline Architecture

```
              ┌─────────────────────────────────┐
              │        Incoming Batch            │
              │       (every row, ~free)         │
              └──────────────┬──────────────────┘
                             │
                 ┌───────────▼───────────┐
                 │   LAYER 1: Rules      │  Cost: ~$0/M rows
                 │   - Schema validation │  Latency: <1s/M rows
                 │   - Dtype checks      │
                 │   - Date regex        │
                 │   - Bounding box      │
                 │   - Hash dedup        │
                 │   - Date logic        │
                 │   - ZIP lookup        │
                 │   - Complaint lookup  │
                 │   - PII regex         │
                 └───────────┬───────────┘
                             │ Flagged rows
                 ┌───────────▼───────────┐
                 │   LAYER 2: Stats      │  Cost: ~$0/M rows
                 │   - Null rate z-score │  Latency: <5s/M rows
                 │   - Fuzzy dedup       │
                 │   - Co-occurrence     │
                 └───────────┬───────────┘
                             │ Confirmed + uncertain
                 ┌───────────▼───────────┐
                 │   LAYER 3: LLM        │  Cost: ~$1-5/M rows
                 │   (flagged rows only) │  (only 0.1-1% of rows)
                 │   - Semantic checks   │
                 │   - Near-dup confirm  │
                 │   - PII confirm       │
                 └───────────────────────┘
```

**At 50M rows/day × 120 customers:**
- Layer 1: ~$0, parallelizable, runs in minutes
- Layer 2: ~$0, batch-level, runs in seconds
- Layer 3: ~$300-1500/day total (across all customers), only on flagged rows
- **Total: ~$500-2000/day** — vastly cheaper than running LLM on every row (~$500K/day)

---

## Key Trade-off: Auditability vs Flexibility

| Dimension | Rules | LLM | Winner for This Use Case |
|-----------|-------|-----|--------------------------|
| **Correctness** | Provably correct (tests pass) | Probabilistically correct (~92%) | **Rules** |
| **Auditability** | Every rupee traces to a section | "The model said so" | **Rules** |
| **Determinism** | Identical output every time | May vary across runs | **Rules** |
| **Latency** | <1ms | 500-1500ms | **Rules** |
| **Cost** | $0 | $0.05-0.20/request | **Rules** |
| **Handling ambiguity** | Cannot parse free text | Excellent at NLP | **LLM** |
| **Semantic judgment** | Cannot assess "contradiction" | Good at nuance | **LLM** |
| **Maintenance** | Manual update per law change | Re-prompt, but verify | **Rules** (safer) |

**Bottom line:** Use rules for everything that can be expressed as deterministic logic. Use LLMs only for language understanding and semantic judgment — and always verify their output against rules or ground truth.
