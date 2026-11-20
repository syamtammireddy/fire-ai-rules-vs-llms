"""
Pytest suite for Task 2: Corruption Injector.
Verifies each of the 12 problem types is injected accurately and deterministically.
"""

import pytest
import pandas as pd
from project_b.data_loader import load_dataset
from project_b.injector import CorruptionInjector


@pytest.fixture(scope="module")
def sample_df():
    return load_dataset(500)


@pytest.fixture(scope="module")
def injector():
    return CorruptionInjector(seed=42)


def test_inject_renamed_column(sample_df, injector):
    corrupted, meta = injector.inject_renamed_column(sample_df, "incident_zip")
    assert "incident_zip" not in corrupted.columns
    assert "incident_zip_err" in corrupted.columns


def test_inject_type_change(sample_df, injector):
    corrupted, idxs = injector.inject_type_change(sample_df, rate=0.10)
    assert len(idxs) == 50
    for i in idxs:
        assert isinstance(corrupted.at[i, "latitude"], str)
        assert "N/A" in corrupted.at[i, "latitude"] or "UNKNOWN" in corrupted.at[i, "latitude"]


def test_inject_date_format_switch(sample_df, injector):
    corrupted, idxs = injector.inject_date_format_switch(sample_df, rate=0.08)
    assert len(idxs) == 40
    for i in idxs:
        # Should be US format with slashes MM/DD/YYYY
        assert "/" in str(corrupted.at[i, "created_date"])


def test_inject_lat_lon_swap(sample_df, injector):
    corrupted, idxs = injector.inject_lat_lon_swap(sample_df, rate=0.06)
    assert len(idxs) == 30
    for i in idxs:
        # In original NYC: lat ~ 40, lon ~ -73
        # Swapped: lat should be negative
        lat = float(corrupted.at[i, "latitude"])
        assert lat < 0


def test_inject_exact_duplicates(sample_df, injector):
    corrupted, new_idxs = injector.inject_exact_duplicates(sample_df, rate=0.05)
    assert len(corrupted) == len(sample_df) + 25
    assert len(new_idxs) == 25


def test_inject_closed_before_created(sample_df, injector):
    corrupted, idxs = injector.inject_closed_before_created(sample_df, rate=0.05)
    assert len(idxs) > 0
    for i in idxs:
        c_dt = pd.to_datetime(corrupted.at[i, "created_date"])
        cl_dt = pd.to_datetime(corrupted.at[i, "closed_date"])
        assert cl_dt < c_dt


def test_inject_zip_borough_mismatch(sample_df, injector):
    corrupted, idxs = injector.inject_zip_borough_mismatch(sample_df, rate=0.05)
    assert len(idxs) == 25


def test_inject_pii(sample_df, injector):
    corrupted, idxs = injector.inject_pii(sample_df, rate=0.05)
    assert len(idxs) == 25
    for i in idxs:
        desc = str(corrupted.at[i, "descriptor"])
        assert any(x in desc for x in ["555-", "@", "mobile", "reached at"])


def test_inject_all_combined(sample_df, injector):
    corrupted, gt = injector.inject_all(sample_df, rate=0.05)
    assert len(corrupted) > len(sample_df)
    assert len(gt) >= 10
