# AI Usage Note
**Author**: Syam Tammireddy

---

## 1. AI Tools Used

| Tool | Purpose | Where Used | Role |
|------|---------|------------|------|
| **AI Coding Assistant (LLM)** | Code typing accelerator for boilerplate, test fixture scaffolding, and syntax drafting under my direct guidance. | Initial module scaffolding across Project A and Project B | Drafting assistant (human-directed) |
| **Gemini 3.5 Flash Lite (API)** | Evaluated as an experimental subject within the assignment requirements (LLM-at-query-time, LLM-compiled rules, NLP parser, semantic data auditor). | `rules_llm_query.py`, `rules_llm_compiled.py`, `nlp_parser.py`, `llm_detectors.py` | System component under benchmark |
| **Statutory Documentation & Official Calculator** | Verified exact tax slab rates, deduction caps, surcharge thresholds, and Section 87A rebate math from official Income Tax Department sources (`incometax.gov.in`). | Rule constants & test ground truth | Truth specification |

---

## 2. How I Used AI in This Project

I used an AI coding assistant as a productivity multiplier to accelerate mechanical coding tasks, adhering strictly to the assignment's expectation that the candidate must understand, explain, and defend every single design decision and line of code:

### Architecture & Engineering Decisions (100% Mine)
- **Decided the 3-tier hybrid pipeline for Project B**: Chose to run fast O(1) declarative rules on 100% of rows, batch statistical checks (z-score spikes) on batches, and restrict LLM review strictly to pre-filtered ambiguous candidates (0.1–1%). This cuts operational costs from $500,000/day to ~$565/day at 50M rows/day scale.
- **Decided deterministic rules for tax calculations**: Kept the core tax engine 100% pure rules. Disqualified LLMs from arithmetic and tax slab lookups due to non-determinism (82% repeatability), high latency (2.7s vs 0.03ms), and lack of statutory auditability.
- **Scoped LLM strictly to its genuine strength**: Isolated LLM usage to plain-language unstructured input parsing (Hinglish/casual text) with a strict clarifying-questions policy, and semantic review of resolution-status contradictions.

### Code Drafting & Scaffolding
- Directed the assistant to generate boilerplate Pydantic schemas, initial function signatures, and repetitive test case structures.
- Structured the 220-case test fixture and 50 NLP test cases, generating boundary scenarios (±₹1 around slab edges, marginal relief inflection points).

### Human Review & Quality Gate
- Personally reviewed, debugged, and executed every file.
- Designed the pytest suites (62 passing tests) to catch errors before any code was committed.

---

## 3. Real Debugging Case: Where AI Was Wrong and How I Caught It

### The Error: Surcharge Marginal Relief Formulation
During initial drafting of `rules_handcoded.py`, the AI coding assistant proposed the following standard formula for surcharge marginal relief:

```python
# FLAWED: Initial assistant draft
tax_with_surcharge = slab_tax * (1 + surcharge_rate)
tax_at_threshold = compute_slab_tax(threshold)
if tax_with_surcharge > tax_at_threshold + (taxable_income - threshold):
    marginal_relief = tax_with_surcharge - (tax_at_threshold + (taxable_income - threshold))
```

### Why It Was Wrong
Under the Indian Income Tax Act, marginal relief at higher surcharge thresholds (e.g. ₹1 Crore, ₹2 Crores, ₹5 Crores) requires that the tax at the threshold (`tax_at_threshold`) **must include the surcharge applicable to that threshold's bracket**, rather than zero surcharge.
- At an income of ₹1,00,00,001 (₹1 above the ₹1 Crore boundary), the baseline comparison is the tax at ₹1,00,00,000 **plus the 10% surcharge** applicable at ₹1 Crore.
- The assistant's naive formula compared against the base slab tax with 0% surcharge, resulting in an absurdly large relief that under-taxed high earners.

### How I Caught & Corrected It
1. I constructed dedicated boundary test cases (`test_official_case_19` through `test_official_case_23` and `test_official_case_30`) specifically checking ₹50,00,001, ₹1,00,00,001, and ₹2,00,00,001 against the official Income Tax Department utility.
2. The assertion failed at ₹1,00,00,001: expected tax was ₹30,94,001, but the AI draft computed ₹27,82,501.
3. I rewrote the marginal relief logic into a chained threshold evaluator (`_apply_surcharge_with_marginal_relief`) that explicitly computes the statutory tax payable at the lower bracket limit including the lower bracket's surcharge rate:

```python
# CORRECT: My verified implementation
for thresh, rate in sorted_brackets:
    if taxable_income > thresh:
        target_thresh = thresh
        target_rate = rate
        # Surcharge rate applicable at the exact threshold boundary
        thresh_surcharge_rate = get_surcharge_rate_at_threshold(thresh)

tax_at_threshold = slab_tax(target_thresh) * (1 + thresh_surcharge_rate)
max_payable = tax_at_threshold + (taxable_income - target_thresh)
total_tax_and_surcharge = min(normal_tax_and_surcharge, max_payable)
```

### Key Takeaway for the Interview
This empirical failure highlights the central thesis of my submission: **probabilistic models cannot replace rigorous, auditable deterministic rules for legal and fiscal computation.** AI is valuable for accelerating implementation speed, but domain verification and mathematical rigor must remain 100% human-owned.
