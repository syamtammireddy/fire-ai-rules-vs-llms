"""
Task 2: Controlled Corruption Injector for NYC 311 Data.
Injects 12 specific data quality problem types into clean batches at controlled rates,
returning the corrupted dataset alongside exact ground-truth row indices for detection measurement.
"""

from __future__ import annotations

import copy
import random
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Set, Any


class CorruptionInjector:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        random.seed(seed)

    def _get_target_indices(self, total: int, rate: float) -> List[int]:
        k = max(1, int(total * rate))
        return self.rng.choice(total, size=k, replace=False).tolist()

    # 1. Renamed or Dropped Column
    def inject_renamed_column(self, df: pd.DataFrame, target_col: str = "incident_zip") -> Tuple[pd.DataFrame, Dict[str, Any]]:
        corrupted = df.copy()
        new_name = f"{target_col}_err"
        if target_col in corrupted.columns:
            corrupted = corrupted.rename(columns={target_col: new_name})
        return corrupted, {"problem": "renamed_column", "original": target_col, "renamed_to": new_name}

    # 2. Column Type Change (numeric coordinates converted to dirty strings)
    def inject_type_change(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        for i in idx_list:
            orig = corrupted.at[i, "latitude"]
            # Convert to corrupted string like 'approx 40.7' or 'NaN_STR'
            corrupted.at[i, "latitude"] = f"N/A ({orig})" if orig is not None else "UNKNOWN"
        return corrupted, idx_list

    # 3. Date Format Switch partway through batch (ISO -> US MM/DD/YYYY HH:MM:SS)
    def inject_date_format_switch(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        for i in idx_list:
            orig = str(corrupted.at[i, "created_date"])
            try:
                # 2023-12-31T23:59:42.000 -> 12/31/2023 11:59:42 PM
                dt = pd.to_datetime(orig)
                corrupted.at[i, "created_date"] = dt.strftime("%m/%d/%Y %I:%M:%S %p")
            except Exception:
                corrupted.at[i, "created_date"] = "12/31/2023 11:59:42 PM"
        return corrupted, idx_list

    # 4. Latitude and Longitude Swapped
    def inject_lat_lon_swap(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        for i in idx_list:
            lat = corrupted.at[i, "latitude"]
            lon = corrupted.at[i, "longitude"]
            corrupted.at[i, "latitude"] = lon
            corrupted.at[i, "longitude"] = lat
        return corrupted, idx_list

    # 5. Exact Duplicates
    def inject_exact_duplicates(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        k = max(1, int(len(df) * rate))
        src_indices = self.rng.choice(len(df), size=k, replace=False).tolist()
        dup_rows = corrupted.iloc[src_indices].copy()
        # Append duplicate rows to the end
        corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
        new_indices = list(range(len(df), len(corrupted)))
        return corrupted, new_indices

    # 6. Near-Duplicates (same request with slightly altered timestamp or minor typo)
    def inject_near_duplicates(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        k = max(1, int(len(df) * rate))
        src_indices = self.rng.choice(len(df), size=k, replace=False).tolist()
        near_dups = []
        for idx in src_indices:
            row = corrupted.iloc[idx].copy()
            # Alter timestamp by 3 minutes and change unique_key
            row["unique_key"] = f"NEAR_DUP_{row['unique_key']}"
            try:
                dt = pd.to_datetime(row["created_date"]) + timedelta(minutes=3)
                row["created_date"] = dt.strftime("%Y-%m-%dT%H:%M:%S.000")
            except Exception:
                pass
            # Minor typo in descriptor
            if row["descriptor"]:
                row["descriptor"] = str(row["descriptor"]) + " [followup]"
            near_dups.append(row)
        corrupted = pd.concat([corrupted, pd.DataFrame(near_dups)], ignore_index=True)
        new_indices = list(range(len(df), len(corrupted)))
        return corrupted, new_indices

    # 7. Null Spike in One Agency's Records
    def inject_null_spike(self, df: pd.DataFrame, target_agency: str = "NYPD", rate: float = 0.80) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        agency_mask = (corrupted["agency"] == target_agency)
        agency_indices = corrupted[agency_mask].index.tolist()
        k = max(1, int(len(agency_indices) * rate))
        target_idx = self.rng.choice(agency_indices, size=k, replace=False).tolist()
        for i in target_idx:
            corrupted.at[i, "incident_zip"] = None
            corrupted.at[i, "location_type"] = None
        return corrupted, target_idx

    # 8. Closed Date Earlier than Created Date
    def inject_closed_before_created(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        closed_indices = corrupted[corrupted["closed_date"].notnull()].index.tolist()
        k = max(1, int(len(closed_indices) * rate))
        target_idx = self.rng.choice(closed_indices, size=k, replace=False).tolist()
        for i in target_idx:
            try:
                c_dt = pd.to_datetime(corrupted.at[i, "created_date"])
                bad_closed = c_dt - timedelta(days=2, hours=4)
                corrupted.at[i, "closed_date"] = bad_closed.strftime("%Y-%m-%dT%H:%M:%S.000")
            except Exception:
                pass
        return corrupted, target_idx

    # 9. ZIP Code Inconsistent with Borough
    def inject_zip_borough_mismatch(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        # Assign Bronx zip to Manhattan, or Staten Island zip to Brooklyn
        mismatch_zips = {
            "MANHATTAN": "10451",      # Bronx ZIP
            "BROOKLYN": "10314",       # Staten Island ZIP
            "QUEENS": "10001",          # Manhattan ZIP
            "BRONX": "11201",           # Brooklyn ZIP
            "STATEN ISLAND": "11101",   # Queens ZIP
        }
        for i in idx_list:
            b = str(corrupted.at[i, "borough"]).upper()
            corrupted.at[i, "incident_zip"] = mismatch_zips.get(b, "90210")  # California ZIP fallback
        return corrupted, idx_list

    # 10. Complaint Type Inconsistent with Descriptor
    def inject_complaint_descriptor_mismatch(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        absurd_descriptors = [
            "Boiler Malfunction",
            "Double Parked Commercial Truck",
            "Loud Music Party in Backyard",
            "Missed Organic Recycling Collection",
            "Dead Animal on Highway",
        ]
        for i in idx_list:
            # Pair a Noise complaint with Boiler, or Heat with Double Parked
            corrupted.at[i, "descriptor"] = self.rng.choice(absurd_descriptors)
        return corrupted, idx_list

    # 11. Resolution Description Contradicting Status
    def inject_resolution_status_contradiction(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        contradictory_texts = [
            "The service request is still open and currently under active investigation by our team.",
            "Field inspector has been dispatched; work is in progress. Awaiting follow-up.",
            "Case unresolved: inspector unable to access premises, rescheduling required.",
        ]
        for i in idx_list:
            # Keep status as 'Closed' but put active investigation in resolution text
            corrupted.at[i, "status"] = "Closed"
            corrupted.at[i, "resolution_description"] = self.rng.choice(contradictory_texts)
        return corrupted, idx_list

    # 12. Personal Data (PII: Phone numbers, emails, names) Inside Free-Text
    def inject_pii(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, List[int]]:
        corrupted = df.copy()
        idx_list = self._get_target_indices(len(df), rate)
        fake_pii_snippets = [
            " Caller John Doe requested callback at 212-555-0199.",
            " Contact complainant Jane Smith directly at jane.smith@gmail.com for building access.",
            " Resident mobile: (917) 555-0143, prefers WhatsApp notifications.",
            " Superintendent Mike Patel reached at 646-555-0182 regarding apartment leak.",
        ]
        for i in idx_list:
            orig = str(corrupted.at[i, "descriptor"] or "General complaint")
            corrupted.at[i, "descriptor"] = orig + self.rng.choice(fake_pii_snippets)
        return corrupted, idx_list

    def inject_all(self, df: pd.DataFrame, rate: float = 0.05) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """Applies all 12 corruptions and returns ground truth mapping."""
        corrupted = df.copy()
        ground_truth: Dict[str, Any] = {}

        # Row-level corruptions
        corrupted, gt_type = self.inject_type_change(corrupted, rate)
        ground_truth["type_change"] = gt_type

        corrupted, gt_date = self.inject_date_format_switch(corrupted, rate)
        ground_truth["date_format_switch"] = gt_date

        corrupted, gt_geo = self.inject_lat_lon_swap(corrupted, rate)
        ground_truth["lat_lon_swap"] = gt_geo

        corrupted, gt_closed = self.inject_closed_before_created(corrupted, rate)
        ground_truth["closed_before_created"] = gt_closed

        corrupted, gt_zip = self.inject_zip_borough_mismatch(corrupted, rate)
        ground_truth["zip_borough_mismatch"] = gt_zip

        corrupted, gt_desc = self.inject_complaint_descriptor_mismatch(corrupted, rate)
        ground_truth["complaint_descriptor_mismatch"] = gt_desc

        corrupted, gt_res = self.inject_resolution_status_contradiction(corrupted, rate)
        ground_truth["resolution_status_contradiction"] = gt_res

        corrupted, gt_pii = self.inject_pii(corrupted, rate)
        ground_truth["pii"] = gt_pii

        corrupted, gt_null = self.inject_null_spike(corrupted, "NYPD", rate=0.70)
        ground_truth["null_spike"] = gt_null

        # Duplicates appended
        corrupted, gt_exact = self.inject_exact_duplicates(corrupted, rate)
        ground_truth["exact_duplicates"] = gt_exact

        corrupted, gt_near = self.inject_near_duplicates(corrupted, rate)
        ground_truth["near_duplicates"] = gt_near

        return corrupted, ground_truth
