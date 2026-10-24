"""
MarketPulse India - Unit Tests: Ingestion, Pipeline, and Row Conservation
"""
import pytest
from src.ingestion.loader import MarketDataLoader, get_loader
from src.cleaning.pipeline import PipelineAuditor, create_standardized_analytical_view


@pytest.fixture(scope="module")
def loader():
    return get_loader()


@pytest.fixture(scope="module")
def auditor(loader):
    return PipelineAuditor(loader)


def test_source_dataset_metadata(loader):
    """Verify total rows, date range, and unique entities in raw dataset."""
    meta = loader.get_metadata()
    assert meta["total_rows"] == 1_481_324
    assert meta["unique_states"] == 6
    assert meta["unique_commodities"] == 14
    assert meta["min_date"] == "2024-08-30"
    assert meta["max_date"] == "2026-09-28"
    assert meta["unique_dates"] == 760


def test_row_conservation_and_data_assurance(auditor):
    """Verify 100% mathematical row conservation across valid and quarantined records."""
    ledger = auditor.get_row_conservation_ledger()
    total = ledger["total_raw_records"]
    valid = ledger["valid_records"]
    scale_err = ledger["scale_errors"]
    inverted = ledger["inverted_prices"]
    zero_arr = ledger["zero_arrivals"]

    assert total == 1_481_324
    # Mathematical Conservation Law
    assert valid + scale_err + inverted + zero_arr == total
    assert ledger["preservation_rate_pct"] > 99.9  # Over 99.9% of records are valid
    assert scale_err == 11  # Exactly 11 scale errors on representative_price (< ₹10/quintal)
    assert inverted == 0
    assert zero_arr == 4


def test_unit_conversions_and_calculated_columns(loader):
    """Verify price per kg and arrivals in quintals conversions."""
    df = loader.execute_df("""
        SELECT modal_price_quintal, modal_price_kg, arrivals_tonnes, arrivals_quintals
        FROM vw_clean_market_history
        WHERE is_valid_price
        LIMIT 100
    """)
    for _, row in df.iterrows():
        assert round(row["modal_price_quintal"] / 100.0, 2) == row["modal_price_kg"]
        assert round(row["arrivals_tonnes"] * 10.0, 2) == row["arrivals_quintals"]


def test_primary_key_grain_uniqueness(loader):
    """Verify that (market_id, commodity, date) has zero duplicate collisions."""
    dups = loader.execute_df("""
        SELECT market_id, commodity, date, COUNT(*) as cnt
        FROM vw_clean_market_history
        GROUP BY market_id, commodity, date
        HAVING COUNT(*) > 1
    """)
    assert len(dups) == 0, f"Found {len(dups)} duplicate primary key collisions!"
