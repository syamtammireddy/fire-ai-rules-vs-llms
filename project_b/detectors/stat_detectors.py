"""
Task 3b: Statistical & Machine Learning Data Quality Detectors.
Detects near-duplicates, null rate distribution shifts, spatial outliers,
and rare complaint-descriptor co-occurrence anomalies across batches.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Any
from rapidfuzz import fuzz


class StatisticalDetectors:
    def __init__(self, baseline_df: pd.DataFrame | None = None):
        self.baseline_null_rates: Dict[str, Dict[str, float]] = {}  # agency -> {col -> mean_null_rate}
        self.valid_agency_complaints: Set[Tuple[str, str]] = set()
        if baseline_df is not None:
            self.fit_baseline(baseline_df)

    def fit_baseline(self, df: pd.DataFrame):
        """Calculates historical baseline metrics for statistical comparisons."""
        for agency, grp in df.groupby("agency"):
            self.baseline_null_rates[str(agency)] = {
                "incident_zip": float(grp["incident_zip"].isnull().mean()),
                "location_type": float(grp["location_type"].isnull().mean()),
                "latitude": float(grp["latitude"].isnull().mean()),
            }
        # Learn valid Agency -> Complaint Type historical associations
        clean_pairs = df[["agency", "complaint_type"]].dropna().drop_duplicates()
        for _, row in clean_pairs.iterrows():
            ag = str(row["agency"]).strip().upper()
            ct = str(row["complaint_type"]).strip()
            self.valid_agency_complaints.add((ag, ct))

    # 6. Near-Duplicate Detection using Spatio-Temporal Bucketing + Fuzzy String Matching
    def detect_near_duplicates_fuzzy(
        self,
        df: pd.DataFrame,
        similarity_threshold: int = 85,
        max_candidate_window: int = 50,
    ) -> List[Tuple[int, int, float]]:
        """
        Detects near-duplicates using RapidFuzz Levenshtein token similarity.
        Applies Spatio-Temporal Bucketing (Date + ZIP/Spatial Cell + Complaint)
        to prevent O(N^2) combinatorial explosion on large batches.
        Returns: list of (idx1, idx2, similarity_score)
        """
        flagged_pairs = []
        n = len(df)
        if n < 2:
            return []

        # Partition indices into discrete spatio-temporal buckets
        buckets: Dict[str, List[int]] = {}
        for idx in df.index:
            t = str(df.at[idx, "created_date"] or "")[:10]  # day
            c = str(df.at[idx, "complaint_type"] or "").strip().lower()
            z = str(df.at[idx, "incident_zip"] or "").strip()
            b_key = f"{t}_{c}_{z}"
            buckets.setdefault(b_key, []).append(idx)

        # Compare only within candidate buckets
        for bucket_indices in buckets.values():
            b_len = len(bucket_indices)
            if b_len < 2:
                continue
            # Cap comparisons per bucket to bounded constant
            limit = min(b_len, max_candidate_window)
            for i in range(limit):
                idx1 = bucket_indices[i]
                d1 = str(df.at[idx1, "descriptor"] or "")
                for j in range(i + 1, limit):
                    idx2 = bucket_indices[j]
                    d2 = str(df.at[idx2, "descriptor"] or "")
                    score = fuzz.token_sort_ratio(d1, d2)
                    if score >= similarity_threshold:
                        flagged_pairs.append((idx1, idx2, float(score)))

        return flagged_pairs

    # 7. Null Spike Detection via Z-Score
    def detect_null_spikes_zscore(
        self,
        batch_df: pd.DataFrame,
        col_name: str = "incident_zip",
        z_threshold: float = 2.5,
    ) -> List[Dict[str, Any]]:
        """
        Flags agencies whose current batch null rate deviates by > z_threshold from baseline.
        """
        flagged_agencies = []
        for agency, grp in batch_df.groupby("agency"):
            ag_str = str(agency)
            batch_null_rate = float(grp[col_name].isnull().mean())
            
            # Historical reference
            baseline_rate = self.baseline_null_rates.get(ag_str, {}).get(col_name, 0.05)
            # Simple binomial standard error: sqrt(p * (1-p) / n)
            n_samples = len(grp)
            if n_samples < 10:
                continue
            
            se = max(0.01, np.sqrt(baseline_rate * (1 - baseline_rate) / n_samples))
            z_score = (batch_null_rate - baseline_rate) / se

            if z_score > z_threshold and batch_null_rate > 0.20:
                flagged_agencies.append({
                    "agency": ag_str,
                    "column": col_name,
                    "batch_null_rate": round(batch_null_rate, 4),
                    "baseline_rate": round(baseline_rate, 4),
                    "z_score": round(float(z_score), 2),
                    "affected_row_count": int(grp[col_name].isnull().sum()),
                })
        return flagged_agencies

    # 4. Spatial Outliers using Interquartile Range (IQR)
    def detect_spatial_outliers_iqr(self, df: pd.DataFrame) -> List[int]:
        """Flags latitude/longitude points beyond 3 * IQR of the batch distribution."""
        lats = pd.to_numeric(df["latitude"], errors="coerce").dropna()
        lons = pd.to_numeric(df["longitude"], errors="coerce").dropna()
        if len(lats) < 20:
            return []

        q1_lat, q3_lat = np.percentile(lats, [25, 75])
        iqr_lat = q3_lat - q1_lat
        lat_lower, lat_upper = q1_lat - 3 * iqr_lat, q3_lat + 3 * iqr_lat

        q1_lon, q3_lon = np.percentile(lons, [25, 75])
        iqr_lon = q3_lon - q1_lon
        lon_lower, lon_upper = q1_lon - 3 * iqr_lon, q3_lon + 3 * iqr_lon

        flagged = []
        for idx in df.index:
            try:
                lat = float(df.at[idx, "latitude"])
                lon = float(df.at[idx, "longitude"])
                if not (lat_lower <= lat <= lat_upper and lon_lower <= lon <= lon_upper):
                    flagged.append(idx)
            except (ValueError, TypeError):
                continue
        return flagged

    # 5. Multivariate Co-Occurrence Anomaly Detection
    def detect_multivariate_cooccurrence_anomalies(self, df: pd.DataFrame) -> List[int]:
        """
        Flags rows where Agency vs Complaint Type combinations violate learned historical priors
        (e.g., NYPD handling HEAT/HOT WATER or HPD handling Illegal Parking).
        """
        if not self.valid_agency_complaints:
            return []

        flagged = []
        for idx in df.index:
            ag = str(df.at[idx, "agency"] or "").strip().upper()
            ct = str(df.at[idx, "complaint_type"] or "").strip()
            if ag and ct:
                if (ag, ct) not in self.valid_agency_complaints:
                    flagged.append(idx)
        return flagged
