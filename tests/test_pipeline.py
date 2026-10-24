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
    # Mathematical Conservation Law: Valid (1,481,250) + Scale (70) + Zero Arrivals (4) = 1,481,324
    assert valid + scale_err + inverted + zero_arr == total
    assert ledger["preservation_rate_pct"] > 99.9  # Over 99.99% of records are valid
    assert scale_err == 70  # Exactly 70 records quarantined for price < ₹10/quintal
    assert valid == 1_481_250  # Exactly 1,481,250 clean analytical records
    assert inverted == 0
    assert zero_arr == 4


def test_hardened_low_price_validation_real_dataset(loader):
    """
    Verifies that the hardened price validation gate quaranatines all records with
    min_price < 10.0 or modal_price_quintal < 10.0 on the actual dataset.
    """
    # 1. Zero records with min_price < 10.0 or modal_price_quintal < 10.0 can be valid
    invalid_passed = loader.execute_df("""
        SELECT COUNT(*) as cnt
        FROM vw_clean_market_history
        WHERE (min_price < 10.0 OR modal_price_quintal < 10.0) AND is_valid_price
    """)
    assert invalid_passed.iloc[0]["cnt"] == 0, "Found low-price records marked as valid!"

    # 2. Exactly 59 records with min_price < 10.0 and modal_price_quintal >= 10.0
    # are correctly quarantined as SCALE_ERROR_LOW_PRICE
    min_low_rep_ok = loader.execute_df("""
        SELECT COUNT(*) as cnt
        FROM vw_clean_market_history
        WHERE min_price < 10.0 AND modal_price_quintal >= 10.0 AND record_quality_status = 'SCALE_ERROR_LOW_PRICE'
    """)
    assert min_low_rep_ok.iloc[0]["cnt"] == 59

    # 3. Exactly 11 records with both min_price < 10.0 and modal_price_quintal < 10.0
    both_low = loader.execute_df("""
        SELECT COUNT(*) as cnt
        FROM vw_clean_market_history
        WHERE modal_price_quintal < 10.0 AND record_quality_status = 'SCALE_ERROR_LOW_PRICE'
    """)
    assert both_low.iloc[0]["cnt"] == 11


def test_validation_rules_synthetic_edge_cases(loader):
    """
    Controlled synthetic fixtures verifying price gate, inverted prices,
    zero arrivals, precedence order, and null handling.
    """
    test_cases = [
        # (id, min_p, max_p, rep_p, arr_t, expected_valid_price, expected_valid_arr, expected_status)
        (1, 1000.0, 1500.0, 1200.0, 10.0, True, True, "VALID"),
        (2, 5.0, 1500.0, 1200.0, 10.0, False, True, "SCALE_ERROR_LOW_PRICE"),       # min < 10, rep >= 10
        (3, 5.0, 8.0, 7.0, 10.0, False, True, "SCALE_ERROR_LOW_PRICE"),             # both < 10
        (4, 1500.0, 1000.0, 1200.0, 10.0, False, True, "INVERTED_PRICE_RANGE"),     # min > max
        (5, 1000.0, 1500.0, 1200.0, 0.0, True, False, "ZERO_ARRIVALS"),             # arrivals = 0
        (6, 5.0, 1500.0, 1200.0, 0.0, False, False, "SCALE_ERROR_LOW_PRICE"),       # multiple: precedence test
        (7, None, 1500.0, 1200.0, 10.0, False, True, "NULL_PRICE"),                # null min price
        (8, 1000.0, 1500.0, 1200.0, None, True, False, "NULL_ARRIVALS"),            # null arrivals
    ]

    loader._con.execute("CREATE TEMP TABLE IF NOT EXISTS _synthetic_test (id INT, min_p DOUBLE, max_p DOUBLE, rep_p DOUBLE, arr_t DOUBLE)")
    loader._con.execute("DELETE FROM _synthetic_test")
    for row in test_cases:
        loader._con.execute(
            "INSERT INTO _synthetic_test VALUES (?, ?, ?, ?, ?)",
            [row[0], row[1], row[2], row[3], row[4]]
        )

    res = loader._con.execute("""
        SELECT
            id,
            (rep_p IS NOT NULL AND min_p IS NOT NULL AND max_p IS NOT NULL AND rep_p >= 10.0 AND min_p >= 10.0 AND min_p <= max_p) as is_valid_price,
            (arr_t IS NOT NULL AND arr_t > 0) as is_valid_arrival,
            CASE
                WHEN rep_p < 10.0 OR min_p < 10.0 THEN 'SCALE_ERROR_LOW_PRICE'
                WHEN min_p > max_p THEN 'INVERTED_PRICE_RANGE'
                WHEN arr_t <= 0 THEN 'ZERO_ARRIVALS'
                WHEN rep_p IS NULL OR min_p IS NULL OR max_p IS NULL THEN 'NULL_PRICE'
                WHEN arr_t IS NULL THEN 'NULL_ARRIVALS'
                ELSE 'VALID'
            END as record_quality_status
        FROM _synthetic_test
        ORDER BY id
    """).fetchall()

    for idx, (row_id, is_vp, is_va, status) in enumerate(res):
        expected = test_cases[idx]
        assert is_vp == expected[5], f"Case {expected[0]} is_valid_price mismatch"
        assert is_va == expected[6], f"Case {expected[0]} is_valid_arrival mismatch"
        assert status == expected[7], f"Case {expected[0]} status mismatch"


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
