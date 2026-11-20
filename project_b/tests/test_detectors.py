"""
Pytest suite for Project B Detectors (Rule & Statistical).
"""

import pytest
import pandas as pd
from project_b.data_loader import load_dataset
from project_b.injector import CorruptionInjector
from project_b.detectors.rule_detectors import RuleDetectors
from project_b.detectors.stat_detectors import StatisticalDetectors


@pytest.fixture(scope="module")
def sample_data():
    df = load_dataset(1000)
    return df


@pytest.fixture(scope="module")
def rules(sample_data):
    return RuleDetectors(reference_df=sample_data)


@pytest.fixture(scope="module")
def stats(sample_data):
    return StatisticalDetectors(baseline_df=sample_data)


@pytest.fixture(scope="module")
def injector():
    return CorruptionInjector(seed=123)


def test_rule_detect_type_change(sample_data, rules, injector):
    corrupted, gt = injector.inject_type_change(sample_data, rate=0.05)
    flagged = rules.detect_type_anomalies(corrupted)
    assert len(flagged) > 0
    # True positives intersection
    tp = set(flagged).intersection(set(gt))
    assert len(tp) / len(gt) >= 0.90


def test_rule_detect_date_format_switch(sample_data, rules, injector):
    corrupted, gt = injector.inject_date_format_switch(sample_data, rate=0.05)
    flagged = rules.detect_date_format_switch(corrupted)
    assert len(flagged) == len(gt)
    assert set(flagged) == set(gt)


def test_rule_detect_lat_lon_swap(sample_data, rules, injector):
    corrupted, gt = injector.inject_lat_lon_swap(sample_data, rate=0.05)
    flagged = rules.detect_lat_lon_swap(corrupted)
    assert len(flagged) > 0
    tp = set(flagged).intersection(set(gt))
    assert len(tp) / len(gt) >= 0.85


def test_rule_detect_closed_before_created(sample_data, rules, injector):
    corrupted, gt = injector.inject_closed_before_created(sample_data, rate=0.05)
    flagged = rules.detect_closed_before_created(corrupted)
    tp = set(flagged).intersection(set(gt))
    assert len(tp) == len(gt)


def test_rule_detect_exact_duplicates(sample_data, rules, injector):
    corrupted, gt = injector.inject_exact_duplicates(sample_data, rate=0.05)
    flagged = rules.detect_exact_duplicates(corrupted)
    assert len(flagged) == len(gt)


def test_stat_detect_null_spike(sample_data, stats, injector):
    corrupted, gt = injector.inject_null_spike(sample_data, target_agency="NYPD", rate=0.80)
    spikes = stats.detect_null_spikes_zscore(corrupted, col_name="incident_zip")
    assert any(s["agency"] == "NYPD" for s in spikes)


def test_stat_detect_cooccurrence_anomaly(sample_data, stats):
    corrupted = sample_data.copy()
    # Inject impossible agency-complaint pairing
    corrupted.at[0, "agency"] = "NYPD"
    corrupted.at[0, "complaint_type"] = "HEAT/HOT WATER"  # HPD's complaint
    anomalies = stats.detect_multivariate_cooccurrence_anomalies(corrupted)
    assert 0 in anomalies


def test_stat_spatiotemporal_fuzzy_dedup(sample_data, stats, injector):
    corrupted, gt = injector.inject_near_duplicates(sample_data.head(500), rate=0.05)
    pairs = stats.detect_near_duplicates_fuzzy(corrupted, similarity_threshold=80)
    assert isinstance(pairs, list)
