"""
Pytest suite for Project B: Hybrid Data Quality Pipeline.
Verifies end-to-end multi-layer execution on clean and corrupted data.
"""

import pytest
from project_b.data_loader import load_dataset
from project_b.injector import CorruptionInjector
from project_b.hybrid_pipeline import HybridDataQualityPipeline


@pytest.fixture(scope="module")
def sample_data():
    return load_dataset(500)


def test_hybrid_pipeline_clean_data(sample_data):
    pipeline = HybridDataQualityPipeline(reference_df=sample_data, enable_llm=False)
    metrics = pipeline.run(sample_data)
    assert metrics.total_rows == len(sample_data)
    # Minimal false alarms on clean data
    assert metrics.layer1_flags.get("type_anomalies", 0) == 0
    assert metrics.layer1_flags.get("date_format_switch", 0) == 0


def test_hybrid_pipeline_corrupted_data(sample_data):
    injector = CorruptionInjector(seed=99)
    corrupted, gt = injector.inject_all(sample_data, rate=0.05)
    pipeline = HybridDataQualityPipeline(reference_df=sample_data, enable_llm=False)
    metrics = pipeline.run(corrupted)

    assert metrics.total_rows == len(corrupted)
    # Ensure all layer 1 detectors flagged corruptions
    assert metrics.layer1_flags["type_anomalies"] > 0
    assert metrics.layer1_flags["date_format_switch"] > 0
    assert metrics.layer1_flags["lat_lon_swap"] > 0
    assert metrics.layer1_flags["exact_duplicates"] > 0
    assert len(metrics.quarantined_row_indices) > 0
