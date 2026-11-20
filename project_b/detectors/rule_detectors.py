"""
Task 3a: Declarative Rules & Schema-Based Data Quality Detectors.
Ultra high-speed, zero-cost, deterministic detectors that run on every row.
"""

from __future__ import annotations

import re
import pandas as pd
import numpy as np
from typing import Dict, List, Set, Tuple, Any

# NYC Bounding Box
NYC_LAT_MIN, NYC_LAT_MAX = 40.4774, 40.9176
NYC_LON_MIN, NYC_LON_MAX = -74.2591, -73.7004

# ISO 8601 Timestamp Regex (e.g., 2023-12-31T23:59:42.000)
ISO_TIMESTAMP_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

# Regex for PII detection
PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


class RuleDetectors:
    def __init__(self, reference_df: pd.DataFrame | None = None):
        self.expected_columns = [
            "unique_key", "created_date", "closed_date", "agency", "agency_name",
            "complaint_type", "descriptor", "location_type", "incident_zip",
            "city", "borough", "latitude", "longitude", "status",
            "resolution_description", "open_data_channel_type"
        ]
        # Build reference lookup tables
        self.valid_zip_borough: Dict[str, Set[str]] = {}
        self.valid_complaint_descriptors: Dict[str, Set[str]] = {}

        if reference_df is not None:
            self._build_reference_lookups(reference_df)

    def _build_reference_lookups(self, df: pd.DataFrame):
        """Extracts valid domain constraints from reference data."""
        # Zip to Borough mapping
        clean_zip_b = df[df["incident_zip"].notnull() & df["borough"].notnull()][["incident_zip", "borough"]]
        for _, row in clean_zip_b.iterrows():
            z = str(row["incident_zip"]).strip()[:5]
            b = str(row["borough"]).strip().upper()
            if b != "UNSPECIFIED":
                if z not in self.valid_zip_borough:
                    self.valid_zip_borough[z] = set()
                self.valid_zip_borough[z].add(b)

        # Complaint type to Descriptor mapping
        clean_cd = df[df["complaint_type"].notnull() & df["descriptor"].notnull()][["complaint_type", "descriptor"]]
        for _, row in clean_cd.iterrows():
            c = str(row["complaint_type"]).strip()
            d = str(row["descriptor"]).strip()
            if c not in self.valid_complaint_descriptors:
                self.valid_complaint_descriptors[c] = set()
            self.valid_complaint_descriptors[c].add(d)

    # 1. Schema Validation
    def detect_schema_issues(self, df: pd.DataFrame) -> Dict[str, Any]:
        actual_cols = set(df.columns)
        expected_cols = set(self.expected_columns)
        missing = expected_cols - actual_cols
        unexpected = actual_cols - expected_cols
        return {
            "has_error": bool(missing or unexpected),
            "missing_columns": list(missing),
            "unexpected_columns": list(unexpected),
            "explanation": f"Missing expected columns: {missing}; Unexpected: {unexpected}" if (missing or unexpected) else "Schema intact",
        }

    # 2. Type Anomalies in Numeric Columns
    def detect_type_anomalies(self, df: pd.DataFrame) -> List[int]:
        if "latitude" not in df.columns:
            return []
        
        # Check if values in latitude cannot be parsed as floats
        flagged = []
        for idx, val in df["latitude"].items():
            if pd.notnull(val):
                try:
                    float(val)
                except ValueError:
                    flagged.append(idx)
        return flagged

    # 3. Date Format Switch (Regex check)
    def detect_date_format_switch(self, df: pd.DataFrame) -> List[int]:
        if "created_date" not in df.columns:
            return []
        flagged = []
        for idx, val in df["created_date"].items():
            if pd.notnull(val) and not ISO_TIMESTAMP_REGEX.match(str(val).strip()):
                flagged.append(idx)
        return flagged

    # 4. Lat/Lon Swap (Bounding box check)
    def detect_lat_lon_swap(self, df: pd.DataFrame) -> List[int]:
        if "latitude" not in df.columns or "longitude" not in df.columns:
            return []
        flagged = []
        for idx in df.index:
            lat_raw = df.at[idx, "latitude"]
            lon_raw = df.at[idx, "longitude"]
            try:
                lat = float(lat_raw)
                lon = float(lon_raw)
                # In NYC: lat is positive (~40.7), lon is negative (~ -73.9)
                # If lat < 0 and lon > 0: definitely swapped!
                if lat < 0 < lon:
                    flagged.append(idx)
                elif not (NYC_LAT_MIN <= lat <= NYC_LAT_MAX) and (NYC_LON_MIN <= lon <= NYC_LON_MAX):
                    # Out of bounds or flipped
                    if NYC_LON_MIN <= lat <= NYC_LON_MAX and NYC_LAT_MIN <= lon <= NYC_LAT_MAX:
                        flagged.append(idx)
            except (ValueError, TypeError):
                continue
        return flagged

    # 5. Exact Duplicates
    def detect_exact_duplicates(self, df: pd.DataFrame) -> List[int]:
        if "unique_key" not in df.columns:
            return []
        dups = df[df.duplicated(subset=["unique_key"], keep="first")].index.tolist()
        return dups

    # 8. Closed Date Earlier Than Created Date
    def detect_closed_before_created(self, df: pd.DataFrame) -> List[int]:
        if "created_date" not in df.columns or "closed_date" not in df.columns:
            return []
        c_dt = pd.to_datetime(df["created_date"], errors="coerce")
        cl_dt = pd.to_datetime(df["closed_date"], errors="coerce")
        bad_mask = (cl_dt < c_dt) & cl_dt.notnull() & c_dt.notnull()
        return df[bad_mask].index.tolist()

    # 9. ZIP Code Inconsistent with Borough
    def detect_zip_borough_mismatch(self, df: pd.DataFrame) -> List[int]:
        if "incident_zip" not in df.columns or "borough" not in df.columns:
            return []
        flagged = []
        for idx in df.index:
            z_raw = df.at[idx, "incident_zip"]
            b_raw = df.at[idx, "borough"]
            if pd.notnull(z_raw) and pd.notnull(b_raw):
                z = str(z_raw).strip()[:5]
                b = str(b_raw).strip().upper()
                if b in ["UNSPECIFIED", ""]:
                    continue
                valid_boroughs = self.valid_zip_borough.get(z)
                if valid_boroughs and b not in valid_boroughs:
                    flagged.append(idx)
        return flagged

    # 10. Complaint Type Inconsistent with Descriptor (Rule-based lookup)
    def detect_complaint_descriptor_mismatch(self, df: pd.DataFrame) -> List[int]:
        if "complaint_type" not in df.columns or "descriptor" not in df.columns:
            return []
        flagged = []
        for idx in df.index:
            c = str(df.at[idx, "complaint_type"]).strip()
            d = str(df.at[idx, "descriptor"]).strip()
            if c and d and c in self.valid_complaint_descriptors:
                valid_descs = self.valid_complaint_descriptors[c]
                # If descriptor has never been seen with this complaint type in historical data
                if d not in valid_descs:
                    flagged.append(idx)
        return flagged

    # 11. Resolution Description Contradicting Status (Rule-based keywords)
    def detect_resolution_status_rule(self, df: pd.DataFrame) -> List[int]:
        if "status" not in df.columns or "resolution_description" not in df.columns:
            return []
        # Flag if marked Closed, but resolution explicitly says 'under investigation', 'in progress', 'unresolved'
        pattern = re.compile(r"\b(under investigation|work is in progress|case unresolved|still open|currently investigating)\b", re.IGNORECASE)
        flagged = []
        closed_mask = (df["status"] == "Closed") & df["resolution_description"].notnull()
        for idx in df[closed_mask].index:
            res_text = str(df.at[idx, "resolution_description"])
            if pattern.search(res_text):
                flagged.append(idx)
        return flagged

    # 12. PII Regex Detector
    def detect_pii_regex(self, df: pd.DataFrame) -> List[int]:
        flagged = []
        for idx in df.index:
            text = str(df.at[idx, "descriptor"] or "") + " " + str(df.at[idx, "resolution_description"] or "")
            if PHONE_REGEX.search(text) or EMAIL_REGEX.search(text):
                flagged.append(idx)
        return flagged
