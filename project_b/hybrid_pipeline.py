"""
Task 5: End-to-End Hybrid Data Quality Pipeline.
Combines:
- Layer 1: Cheap declarative rules on EVERY row ($0 cost, microsecond latency)
- Layer 2: Statistical & fuzzy detectors across the batch ($0 cost, millisecond latency)
- Layer 3: Targeted LLM semantic review ONLY on pre-filtered rows (<1% of rows)
"""

from __future__ import annotations

import time
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Set, Any, Tuple

from project_b.detectors.rule_detectors import RuleDetectors
from project_b.detectors.stat_detectors import StatisticalDetectors
from project_b.detectors.llm_detectors import LLMDetectors


@dataclass
class PipelineMetrics:
    total_rows: int = 0
    layer1_flags: Dict[str, int] = field(default_factory=dict)
    layer2_flags: Dict[str, int] = field(default_factory=dict)
    layer3_confirmations: Dict[str, int] = field(default_factory=dict)
    quarantined_row_indices: Set[int] = field(default_factory=set)
    total_time_seconds: float = 0.0
    llm_cost_dollars: float = 0.0
    tokens_used: int = 0


class HybridDataQualityPipeline:
    def __init__(self, reference_df: pd.DataFrame | None = None, enable_llm: bool = True):
        self.rules = RuleDetectors(reference_df)
        self.stats = StatisticalDetectors(reference_df)
        self.llm = LLMDetectors() if enable_llm else None
        self.enable_llm = enable_llm

    def run(self, df: pd.DataFrame, sample_llm_limit: int = 20) -> PipelineMetrics:
        """Runs the 3-tiered data quality pipeline over an incoming batch."""
        t_start = time.perf_counter()
        metrics = PipelineMetrics(total_rows=len(df))

        # =========================================================================
        # LAYER 1: Pure Rule-Based Screening (Every Row, $0 Cost)
        # =========================================================================
        # 1. Schema Check
        schema_res = self.rules.detect_schema_issues(df)
        if schema_res["has_error"]:
            metrics.layer1_flags["schema_mismatch"] = len(df)

        # 2. Type anomalies
        type_flags = self.rules.detect_type_anomalies(df)
        metrics.layer1_flags["type_anomalies"] = len(type_flags)
        metrics.quarantined_row_indices.update(type_flags)

        # 3. Date format switch
        date_flags = self.rules.detect_date_format_switch(df)
        metrics.layer1_flags["date_format_switch"] = len(date_flags)
        metrics.quarantined_row_indices.update(date_flags)

        # 4. Lat/Lon swap
        geo_flags = self.rules.detect_lat_lon_swap(df)
        metrics.layer1_flags["lat_lon_swap"] = len(geo_flags)
        metrics.quarantined_row_indices.update(geo_flags)

        # 5. Exact duplicates
        dup_flags = self.rules.detect_exact_duplicates(df)
        metrics.layer1_flags["exact_duplicates"] = len(dup_flags)
        metrics.quarantined_row_indices.update(dup_flags)

        # 6. Closed < Created
        closed_flags = self.rules.detect_closed_before_created(df)
        metrics.layer1_flags["closed_before_created"] = len(closed_flags)
        metrics.quarantined_row_indices.update(closed_flags)

        # 7. Zip-Borough mismatch
        zip_flags = self.rules.detect_zip_borough_mismatch(df)
        metrics.layer1_flags["zip_borough_mismatch"] = len(zip_flags)
        metrics.quarantined_row_indices.update(zip_flags)

        # 8. Preliminary Resolution-Status keywords
        status_rule_flags = self.rules.detect_resolution_status_rule(df)
        metrics.layer1_flags["status_contradiction_candidates"] = len(status_rule_flags)

        # 9. PII regex candidates
        pii_regex_flags = self.rules.detect_pii_regex(df)
        metrics.layer1_flags["pii_regex_candidates"] = len(pii_regex_flags)

        # =========================================================================
        # LAYER 2: Statistical Batch Analysis ($0 Cost)
        # =========================================================================
        # 1. Null rate z-score spikes
        null_spikes = self.stats.detect_null_spikes_zscore(df, col_name="incident_zip")
        metrics.layer2_flags["null_spike_agencies"] = len(null_spikes)

        # 2. Near-duplicate fuzzy candidates (with spatio-temporal bucketing)
        fuzzy_pairs = self.stats.detect_near_duplicates_fuzzy(df, similarity_threshold=85)
        metrics.layer2_flags["near_duplicate_candidate_pairs"] = len(fuzzy_pairs)

        # 3. Multivariate co-occurrence anomalies (Agency vs Complaint Type priors)
        cooc_flags = self.stats.detect_multivariate_cooccurrence_anomalies(df)
        metrics.layer2_flags["cooccurrence_anomalies"] = len(cooc_flags)
        metrics.quarantined_row_indices.update(cooc_flags)

        # =========================================================================
        # LAYER 3: Targeted LLM Semantic Review (Flagged Rows Only, Controlled Cost)
        # =========================================================================
        if self.enable_llm and self.llm is not None:
            # A. Review resolution status contradictions (capped to sample_llm_limit)
            if status_rule_flags:
                sample_status_idx = status_rule_flags[:sample_llm_limit]
                status_candidates = [
                    {
                        "unique_key": str(df.at[i, "unique_key"]),
                        "status": str(df.at[i, "status"]),
                        "resolution_description": str(df.at[i, "resolution_description"]),
                    }
                    for i in sample_status_idx
                ]
                status_reviewed, meta1 = self.llm.review_resolution_status_batch(status_candidates)
                confirmed_contra = sum(1 for r in status_reviewed if r.get("is_contradiction"))
                metrics.layer3_confirmations["confirmed_resolution_contradictions"] = confirmed_contra
                # Add confirmed to quarantine
                for r, orig_idx in zip(status_reviewed, sample_status_idx):
                    if r.get("is_contradiction"):
                        metrics.quarantined_row_indices.add(orig_idx)

            # B. Review near-duplicate pairs
            if fuzzy_pairs:
                sample_pairs = fuzzy_pairs[:sample_llm_limit]
                pair_candidates = [
                    {
                        "pair_id": f"{p[0]}_{p[1]}",
                        "req_1": {
                            "created": str(df.at[p[0], "created_date"]),
                            "complaint": str(df.at[p[0], "complaint_type"]),
                            "descriptor": str(df.at[p[0], "descriptor"]),
                        },
                        "req_2": {
                            "created": str(df.at[p[1], "created_date"]),
                            "complaint": str(df.at[p[1], "complaint_type"]),
                            "descriptor": str(df.at[p[1], "descriptor"]),
                        },
                    }
                    for p in sample_pairs
                ]
                pairs_reviewed, meta2 = self.llm.review_near_duplicates_batch(pair_candidates)
                confirmed_dups = sum(1 for r in pairs_reviewed if r.get("is_duplicate"))
                metrics.layer3_confirmations["confirmed_near_duplicates"] = confirmed_dups
                for r, p in zip(pairs_reviewed, sample_pairs):
                    if r.get("is_duplicate"):
                        metrics.quarantined_row_indices.add(p[1])

            # C. Review PII candidates
            if pii_regex_flags:
                sample_pii_idx = pii_regex_flags[:sample_llm_limit]
                pii_candidates = [
                    {
                        "id": str(i),
                        "text": f"{df.at[i, 'descriptor']} | {df.at[i, 'resolution_description']}"[:150],
                    }
                    for i in sample_pii_idx
                ]
                pii_reviewed, meta3 = self.llm.review_pii_batch(pii_candidates)
                confirmed_pii = sum(1 for r in pii_reviewed if r.get("contains_pii"))
                metrics.layer3_confirmations["confirmed_pii_records"] = confirmed_pii
                for r, orig_idx in zip(pii_reviewed, sample_pii_idx):
                    if r.get("contains_pii"):
                        metrics.quarantined_row_indices.add(orig_idx)

            metrics.tokens_used = self.llm.total_tokens_in + self.llm.total_tokens_out
            # Calculate cost at Gemini 2.5 Flash pricing
            metrics.llm_cost_dollars = (self.llm.total_tokens_in / 1_000_000 * 0.075) + (self.llm.total_tokens_out / 1_000_000 * 0.30)

        metrics.total_time_seconds = time.perf_counter() - t_start
        return metrics
