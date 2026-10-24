"""
MarketPulse India - Configuration & Constants
"""
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SCREENSHOTS_DIR = BASE_DIR / "screenshots" / "runtime"

# Repository-local parquet dataset paths
SOURCE_SAMPLES_DIR = RAW_DATA_DIR
SOURCE_HISTORY_PARQUET = RAW_DATA_DIR / "all_market_history.parquet"
SOURCE_COVERAGE_PARQUET = RAW_DATA_DIR / "all_market_coverage.parquet"
SOURCE_LEDGER_PARQUET = RAW_DATA_DIR / "source_quality_ledger.parquet"

# Unit definitions
QUINTAL_TO_KG = 100.0
TONNE_TO_KG = 1000.0
TONNE_TO_QUINTAL = 10.0

# Quality threshold definitions
MIN_PLAUSIBLE_PRICE = 10.0       # ₹/Quintal - below this is data entry / unit error (e.g. ₹/kg entered as quintal)
MIN_PLAUSIBLE_ARRIVALS = 0.05    # Tonnes (50 kg)
STALE_PRICE_STREAK_DAYS = 7     # Days of unchanged price triggering reliability review
REPORTING_BLACKOUT_DAYS = 30     # Days of missing reports triggering coverage warning

# Core Commodity Definitions & Focus Series
CORE_COMMODITIES = [
    "Onion",
    "Tomato",
    "Potato",
    "Green Chilli",
    "Banana",
    "Brinjal",
    "Coconut",
    "Maize",
    "Paddy (Common)",
    "Groundnut",
    "Cotton",
    "Arecanut",
    "Ragi",
    "Turmeric",
]

# Market Corridor Key Constants
LASALGAON_MAIN_ID = "20-161"
MUMBAI_ONION_POTATO_ID = "20-2703"
LASALGAON_NIPHAD_ID = "20-2139"
LASALGAON_VINCHUR_ID = "20-3448"
PUNE_MAIN_ID = "20-110"
PIMPALGAON_BASWANT_ID = "20-162"

# Road Distances for Decision Simulator (km)
CORRIDOR_DISTANCES_KM = {
    ("20-161", "20-2703"): 225.0,  # Lasalgaon to Vashi, Navi Mumbai
    ("20-2139", "20-2703"): 215.0, # Niphad to Vashi
    ("20-3448", "20-2703"): 235.0, # Vinchur to Vashi
    ("20-162", "20-2703"): 195.0,  # Pimpalgaon to Vashi
    ("20-161", "20-110"): 210.0,   # Lasalgaon to Pune
    ("20-110", "20-2703"): 150.0,  # Pune to Mumbai
}
