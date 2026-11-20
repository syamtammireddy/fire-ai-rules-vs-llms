"""
Task 1: Raw Data Profiler for NYC 311 Service Requests (2023).
Analyzes schema completeness, data distributions, spatial and temporal bounds,
and detects pre-existing quality issues already present in the raw data.
"""

from __future__ import annotations

import re
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from datetime import datetime

# NYC Bounding Box
NYC_LAT_MIN, NYC_LAT_MAX = 40.4774, 40.9176
NYC_LON_MIN, NYC_LON_MAX = -74.2591, -73.7004

# Common regex patterns for PII detection in free text
PHONE_REGEX = re.compile(r"\b(?:\+?1[-.]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")


def profile_raw_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Runs a complete data quality profiling on the 2023 NYC 311 dataset."""
    total_rows = len(df)
    print(f"Profiling {total_rows:,} raw NYC 311 records...")

    # 1. Null / Completeness Analysis
    null_counts = df.isnull().sum()
    null_percentages = (null_counts / total_rows) * 100
    completeness_summary = [
        {"column": col, "null_count": int(null_counts[col]), "null_pct": round(float(null_percentages[col]), 2)}
        for col in df.columns
    ]

    # 2. Date Range and Temporal Validation
    created_dt = pd.to_datetime(df["created_date"], errors="coerce")
    closed_dt = pd.to_datetime(df["closed_date"], errors="coerce")
    
    # Pre-existing Issue: Closed Date Earlier than Created Date
    closed_before_created_mask = (closed_dt < created_dt) & closed_dt.notnull() & created_dt.notnull()
    closed_before_created_count = int(closed_before_created_mask.sum())
    closed_before_created_examples = df[closed_before_created_mask][
        ["unique_key", "created_date", "closed_date", "agency", "complaint_type"]
    ].head(5).to_dict(orient="records")

    # 3. Geolocation & Spatial Bounds Validation
    latitudes = pd.to_numeric(df["latitude"], errors="coerce")
    longitudes = pd.to_numeric(df["longitude"], errors="coerce")

    missing_geo_mask = latitudes.isnull() | longitudes.isnull()
    missing_geo_count = int(missing_geo_mask.sum())

    out_of_bounds_mask = (
        latitudes.notnull() & longitudes.notnull() & (
            (latitudes < NYC_LAT_MIN) | (latitudes > NYC_LAT_MAX) |
            (longitudes < NYC_LON_MIN) | (longitudes > NYC_LON_MAX)
        )
    )
    out_of_bounds_count = int(out_of_bounds_mask.sum())
    out_of_bounds_examples = df[out_of_bounds_mask][
        ["unique_key", "latitude", "longitude", "borough", "complaint_type"]
    ].head(5).to_dict(orient="records")

    # 4. Status vs Resolution Contradictions
    status_counts = df["status"].value_counts().to_dict()
    # Check for requests marked Closed but with empty or 'pending' resolution descriptions
    closed_no_res_mask = (df["status"] == "Closed") & (df["resolution_description"].isnull() | (df["resolution_description"].str.strip() == ""))
    closed_no_res_count = int(closed_no_res_mask.sum())

    closed_but_investigating_mask = (df["status"] == "Closed") & df["resolution_description"].str.contains(
        r"in progress|currently investigating|pending", case=False, na=False
    )
    closed_but_investigating_count = int(closed_but_investigating_mask.sum())
    status_contradiction_examples = df[closed_but_investigating_mask][
        ["unique_key", "status", "resolution_description", "agency"]
    ].head(5).to_dict(orient="records")

    # 5. Exact and Potential Duplicates
    exact_duplicates_count = int(df.duplicated(subset=["unique_key"]).sum())
    potential_duplicates_mask = df.duplicated(
        subset=["created_date", "complaint_type", "incident_zip", "descriptor"],
        keep=False
    )
    potential_duplicates_count = int(potential_duplicates_mask.sum())

    # 6. PII in Free-Text Fields (descriptor, resolution_description)
    text_fields = df["descriptor"].fillna("") + " " + df["resolution_description"].fillna("")
    phone_matches = text_fields.apply(lambda x: bool(PHONE_REGEX.search(str(x))))
    email_matches = text_fields.apply(lambda x: bool(EMAIL_REGEX.search(str(x))))
    pii_count = int((phone_matches | email_matches).sum())
    pii_examples = df[phone_matches | email_matches][
        ["unique_key", "descriptor", "resolution_description"]
    ].head(5).to_dict(orient="records")

    # Top Distributions
    top_complaints = df["complaint_type"].value_counts().head(10).to_dict()
    top_agencies = df["agency"].value_counts().head(10).to_dict()
    borough_counts = df["borough"].value_counts().to_dict()

    return {
        "total_records": total_rows,
        "completeness": completeness_summary,
        "pre_existing_issues": {
            "closed_before_created": {
                "count": closed_before_created_count,
                "pct": round((closed_before_created_count / total_rows) * 100, 4),
                "examples": closed_before_created_examples,
            },
            "missing_or_out_of_bounds_geo": {
                "missing_count": missing_geo_count,
                "out_of_bounds_count": out_of_bounds_count,
                "examples": out_of_bounds_examples,
            },
            "status_resolution_contradictions": {
                "closed_no_resolution": closed_no_res_count,
                "closed_but_pending_text": closed_but_investigating_count,
                "examples": status_contradiction_examples,
            },
            "duplicates": {
                "exact_unique_key_duplicates": exact_duplicates_count,
                "potential_same_event_duplicates": potential_duplicates_count,
            },
            "pii_in_text": {
                "count": pii_count,
                "examples": pii_examples,
            },
        },
        "distributions": {
            "top_complaint_types": top_complaints,
            "top_agencies": top_agencies,
            "boroughs": borough_counts,
            "status": status_counts,
        },
    }


def generate_markdown_profile(profile: Dict[str, Any]) -> str:
    """Formats the profiling results into a professional Markdown document."""
    lines = []
    lines.append("# NYC 311 Service Requests (CY 2023) — Data Quality Profiling Report\n")
    lines.append(f"**Total Records Analyzed**: {profile['total_records']:,}\n")

    lines.append("## 1. Column Completeness & Missing Value Rates\n")
    lines.append("| Column Name | Missing Count | Missing % |")
    lines.append("|---|---|---|")
    for col in profile["completeness"]:
        lines.append(f"| `{col['column']}` | {col['null_count']:,} | {col['null_pct']:.2f}% |")

    lines.append("\n## 2. Pre-Existing Data Quality Problems Found\n")
    issues = profile["pre_existing_issues"]
    lines.append(f"- **Closed Date Earlier than Created Date**: {issues['closed_before_created']['count']:,} records ({issues['closed_before_created']['pct']}%)")
    lines.append(f"- **Missing Geolocation Coordinates**: {issues['missing_or_out_of_bounds_geo']['missing_count']:,} records")
    lines.append(f"- **Coordinates Outside NYC Bounding Box**: {issues['missing_or_out_of_bounds_geo']['out_of_bounds_count']:,} records")
    lines.append(f"- **Closed Status Contradicting Ongoing Text**: {issues['status_resolution_contradictions']['closed_but_pending_text']:,} records")
    lines.append(f"- **Closed Requests with Empty Resolution**: {issues['status_resolution_contradictions']['closed_no_resolution']:,} records")
    lines.append(f"- **Potential Duplicates (Same Event & Location)**: {issues['duplicates']['potential_same_event_duplicates']:,} records")
    lines.append(f"- **Pre-existing PII (Phone/Email) in Free Text**: {issues['pii_in_text']['count']:,} records\n")

    lines.append("## 3. Categorical Distributions\n")
    lines.append("### Top Complaint Types")
    for k, v in profile["distributions"]["top_complaint_types"].items():
        lines.append(f"- **{k}**: {v:,}")

    lines.append("\n### Top Agencies")
    for k, v in profile["distributions"]["top_agencies"].items():
        lines.append(f"- **{k}**: {v:,}")

    return "\n".join(lines)


if __name__ == "__main__":
    from project_b.data_loader import load_dataset
    df = load_dataset(sample_size=25_000)
    profile = profile_raw_data(df)
    md_report = generate_markdown_profile(profile)
    print("\n" + md_report)
    with open("project_b/data_profile_report.md", "w") as f:
        f.write(md_report)
    print("Report written to project_b/data_profile_report.md")
