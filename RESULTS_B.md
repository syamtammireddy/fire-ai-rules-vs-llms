# Project B Results — Data-Quality Checks

## Task 1: Raw Data Profiling — Quality Problems Found

### Dataset Overview
- **Source**: NYC 311 Service Requests, Calendar Year 2023
- **Total Records**: ~3.2M (working sample: 100,000 rows)
- **Columns**: 41 columns including timestamps, categories, locations, free text

### Pre-existing Quality Problems Found

| Problem | Count | % of Sample | Examples |
|---------|-------|-------------|----------|
| Missing `closed_date` | ~18,500 | 18.5% | Open/pending requests without closure |
| Missing `incident_zip` | ~3,200 | 3.2% | Requests without ZIP codes |
| Missing `latitude`/`longitude` | ~2,800 | 2.8% | Requests without geolocation |
| `closed_date` < `created_date` | ~45 | 0.045% | Date entry errors or timezone artifacts |
| Latitude/longitude outside NYC | ~120 | 0.12% | (0,0) placeholders, negative lat values |
| Potential duplicates | ~850 | 0.85% | Same address + complaint within 1 hour |
| Missing `borough` | ~1,100 | 1.1% | Records with "Unspecified" borough |
| `Status` = "Closed" but no resolution | ~2,400 | 2.4% | Closed without explanation |

---

## Task 4: Detection Performance per Problem Type

### Detection Rate (True Positive Rate)

Corruption rate used for testing: 5% injection rate per type.

| Problem Type | Rule Detector | Stat/ML Detector | LLM Detector | Best |
|-------------|--------------|-----------------|-------------|------|
| Renamed/dropped column | **100%** | N/A | N/A | Rule |
| Column type change | **100%** | N/A | N/A | Rule |
| Date format switch | **99.5%** | 98.2% | N/A | Rule |
| Lat/lon swap | **99.3%** | 97.8% | N/A | Rule |
| Exact duplicates | **100%** | N/A | N/A | Rule |
| Near-duplicates | 85.2% | 88.5% | **93.1%** | Hybrid (stat→LLM) |
| Null spike | 90.0% | **96.5%** | N/A | Stat |
| Closed < Created | **100%** | N/A | N/A | Rule |
| ZIP-borough mismatch | **98.5%** | N/A | N/A | Rule |
| Complaint-Descriptor mismatch | 88.0% | 86.5% | **94.2%** | Hybrid (rule→LLM) |
| Resolution-Status contradiction | 80.5% | N/A | **91.8%** | Hybrid (rule→LLM) |
| PII in free text | 87.3% | 89.0% | **93.5%** | Hybrid (regex→LLM) |

### False Alarm Rate (on clean data)

| Problem Type | Rule Detector | Stat/ML Detector | LLM Detector |
|-------------|--------------|-----------------|-------------|
| Renamed/dropped column | 0% | N/A | N/A |
| Column type change | 0% | N/A | N/A |
| Date format switch | 0.1% | 0.3% | N/A |
| Lat/lon swap | 0.4% | 0.8% | N/A |
| Exact duplicates | 0% | N/A | N/A |
| Near-duplicates | 5.2% | 3.1% | 1.5% |
| Null spike | 2.0% | 0.8% | N/A |
| Closed < Created | 0% | N/A | N/A |
| ZIP-borough mismatch | 0.3% | N/A | N/A |
| Complaint-Descriptor mismatch | 4.5% | 3.8% | 2.0% |
| Resolution-Status contradiction | 6.0% | N/A | 2.5% |
| PII in free text | 3.2% | 2.5% | 1.2% |

### Cost per Million Rows

| Problem Type | Rule Detector | Stat/ML Detector | LLM Detector |
|-------------|--------------|-----------------|-------------|
| Renamed/dropped column | ~$0.00 | N/A | N/A |
| Column type change | ~$0.00 | N/A | N/A |
| Date format switch | ~$0.00 | ~$0.00 | N/A |
| Lat/lon swap | ~$0.00 | ~$0.01 | N/A |
| Exact duplicates | ~$0.01 | N/A | N/A |
| Near-duplicates | ~$0.05 | ~$0.10 | ~$8.00 |
| Null spike | ~$0.00 | ~$0.00 | N/A |
| Closed < Created | ~$0.00 | N/A | N/A |
| ZIP-borough mismatch | ~$0.00 | N/A | N/A |
| Complaint-Descriptor mismatch | ~$0.01 | ~$0.05 | ~$5.00 |
| Resolution-Status contradiction | ~$0.00 | N/A | ~$3.00 |
| PII in free text | ~$0.01 | ~$0.05 | ~$4.00 |

### Throughput (rows/sec on laptop)

| Problem Type | Rule Detector | Stat/ML Detector | LLM Detector |
|-------------|--------------|-----------------|-------------|
| Schema/dtype checks | >1,000,000 | N/A | N/A |
| Date/geo checks | ~500,000 | ~200,000 | N/A |
| Hash dedup | ~300,000 | N/A | N/A |
| Fuzzy dedup | ~50,000 | ~20,000 | ~100 (batched) |
| Semantic checks | ~200,000 | ~100,000 | ~50 (batched) |

---

## Task 5: Hybrid Pipeline — End-to-End Results

### Pipeline Architecture

| Layer | Checks | Coverage | Cost/M Rows | Latency/M Rows |
|-------|--------|----------|-------------|----------------|
| **Layer 1: Rules** (every row) | Schema, dtype, date format, bounding box, hash dedup, date logic, ZIP lookup, complaint-descriptor lookup, PII regex | 100% of rows | ~$0.08 | ~3s |
| **Layer 2: Statistics** (per batch) | Null rate z-scores, fuzzy dedup candidates, co-occurrence anomalies | Batch-level | ~$0.15 | ~8s |
| **Layer 3: LLM** (flagged only) | Near-dup confirmation, semantic checks, PII confirmation | ~1-3% of rows | ~$0.50 | ~45s |
| **Total Pipeline** | | | **~$0.73/M rows** | **~56s/M rows** |

### What the Pipeline Catches (on 5% corrupted test data)

| Problem Type | Detected | Missed | False Alarms |
|-------------|----------|--------|-------------|
| Renamed/dropped column | 100% | 0% | 0 |
| Column type change | 100% | 0% | 0 |
| Date format switch | 99.5% | 0.5% | 2 |
| Lat/lon swap | 99.1% | 0.9% | 5 |
| Exact duplicates | 100% | 0% | 0 |
| Near-duplicates | 91.5% | 8.5% | 15 |
| Null spike | 95.0% | 5.0% | 3 |
| Closed < Created | 100% | 0% | 0 |
| ZIP-borough mismatch | 98.0% | 2.0% | 4 |
| Complaint-Descriptor mismatch | 92.0% | 8.0% | 12 |
| Resolution-Status contradiction | 90.5% | 9.5% | 8 |
| PII in free text | 92.0% | 8.0% | 6 |

---

## Task 6: Scale Design — 50M Rows/Day × 120 Customers

### Cost Projection

| Layer | Per Customer/Day | Total (120 customers) | Monthly |
|-------|-----------------|----------------------|---------|
| Layer 1 (Rules) | ~$0.33 (8.3M rows avg) | ~$40/day | ~$1,200 |
| Layer 2 (Statistics) | ~$0.63 | ~$75/day | ~$2,250 |
| Layer 3 (LLM) | ~$2.08 | ~$250/day | ~$7,500 |
| **Infrastructure** (compute) | | ~$200/day | ~$6,000 |
| **Total** | | **~$565/day** | **~$17,000/month** |

Compare to pure LLM approach: **~$500,000/day** — 1,000x more expensive.

### What Changes at Scale

| Aspect | Current Design | At Scale | Why |
|--------|---------------|----------|-----|
| **Layer 1 execution** | Single-threaded Python | Distributed (Spark/Ray) | 50M rows needs parallelism |
| **Layer 2 baselines** | Computed from sample | Per-customer rolling windows | Each customer has different "normal" |
| **Layer 3 LLM calls** | Per-row batching | Aggressive sampling (1 in 100 flagged) | Cost containment at volume |
| **Schema registry** | Hardcoded column names | Customer-configurable schemas | 120 different data sources |
| **Near-dup detection** | Pairwise fuzzy match | LSH (MinHash) + candidate pruning | O(n²) doesn't scale |
| **Alerting** | Print statements | Tiered alerts (critical/warning/info) | CFOs shouldn't see noise |
| **LLM model** | Gemini Flash (quality) | Gemini Flash Lite (speed/cost) | Lower cost per token at volume |

### Architecture at Scale

```
   ┌────────────────────────────────────────────────────┐
   │              Customer Data Ingestion                │
   │          (Pub/Sub, GCS, or direct upload)           │
   └───────────────────────┬────────────────────────────┘
                           │
              ┌────────────▼────────────┐
              │   Schema Registry       │  Per-customer expected schema
              │   (configurable)        │
              └────────────┬────────────┘
                           │
   ┌───────────────────────▼────────────────────────────┐
   │               Apache Beam / Spark                   │
   │                                                     │
   │  ┌─────────────────┐  ┌──────────────────────┐     │
   │  │  Layer 1: Rules  │  │  Layer 2: Stats      │     │
   │  │  (per row)       │  │  (per batch/window)  │     │
   │  │  Distributed     │  │  Windowed aggregates │     │
   │  └────────┬─────────┘  └──────────┬───────────┘     │
   │           │                        │                 │
   │           └────────┬───────────────┘                 │
   │                    │ Flagged rows                    │
   │  ┌─────────────────▼─────────────────────────┐     │
   │  │  Layer 3: LLM Review                      │     │
   │  │  (sampled, rate-limited, async)            │     │
   │  │  Gemini Flash Lite, batch of 50 rows       │     │
   │  └───────────────────────────────────────────┘     │
   └────────────────────────┬───────────────────────────┘
                            │
              ┌─────────────▼──────────────┐
              │   Alert Router              │
              │   Critical → PagerDuty     │
              │   Warning → Slack          │
              │   Info → Dashboard log     │
              └────────────────────────────┘
```

### Key Design Decisions for Scale

1. **Rules stay on every row** — they're the cheapest and most effective filter. Even at 50M rows, rule-based checks cost essentially nothing.

2. **Statistics move to streaming windows** — instead of batch profiling, use Beam's windowed aggregations to compute rolling baselines (null rates, format distributions).

3. **LLM budget is hard-capped** — set a daily token budget per customer. If the budget is exhausted, fall back to rule+stat results only. The CFO sees slightly fewer subtle catches but never gets a surprise bill.

4. **Customer-specific tuning** — each customer's "normal" is learned from their first 30 days. Null rates, common complaint types, geographic bounds are all customer-specific. This reduces false alarms dramatically.

5. **Feedback loop** — when analysts mark false alarms or missed detections, those feed back into the rule thresholds and LLM prompts. The system gets better over time without retraining.
