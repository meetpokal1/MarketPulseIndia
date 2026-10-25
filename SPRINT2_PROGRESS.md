# SPRINT 2 PROGRESS — MARKETPULSE INDIA
**Product:** MarketPulse India — Agricultural Market-Price & Supply Intelligence Platform
**Repository:** MarketPulse India
**Execution Date:** 23 October 2026
**Status:** COMPLETED — ALL 7 PHASES COMPLETE & VERIFIED

---

## 1. Verified Discoveries & Empirical Results

### Investigation A: Lasalgaon vs. Mumbai Onion Price Comparison
- **Reproduced 467-Day Text Overlap:** Historical string matching on `'Lasalgaon APMC'` vs `'Mumbai-Onion & Potato Market APMC'` produces exactly 467 days (2024-08-30 to 2026-07-31).
- **Discovered Invariant Market ID Transition:** On August 1, 2026, text labels were modified to `'APMC Lasalgaon'` and `'Mumbai-Onion & Potato Market'`. Using persistent invariant `market_id` (`20-161` vs `20-2703`), the true overlap across the 25-month span is **507 trading days**.
- **Negative Spatial Spread Paradox:** Across all 507 overlapping days, Mumbai reported prices were **lower than Lasalgaon on 74.8% of days** (mean spread **-₹157.76/quintal**).
- **Variety Confounder Proven:** Mumbai reports 100% of arrivals under generic `'Other'`. Lasalgaon segregates export-grade *Unhali* (-₹228 spread) and *Red* onions (-₹210 spread). Unadjusted spread comparisons are fundamentally confounded by variety heterogeneity.

### Investigation B: Price Volatility & Outlier Shocks
- **Volatility Hierarchy:** Tomato (CV = 0.5865) and Onion (CV = 0.5742) exhibit the highest price volatility. Cotton (CV = 0.1111) and Paddy (CV = 0.1844) exhibit the lowest volatility due to MSP floor procurement.
- **Mean-Reversion Dynamics:** Price returns in Lasalgaon Onion exhibit an AR(1) autocorrelation of **-0.0146**, demonstrating rapid auction clearance and low speculative momentum.

### Investigation C: Arrival–Price Panel Econometrics
- **Folklore Claim Rejected:** Debunked the folklore assertion that *"a 10% drop in arrivals causes a 35-50% price surge"*.
- **Empirical Panel Specification:** Two-Way Fixed Effects panel regression with Cameron-Miller cluster-robust standard errors:
  $$\ln(P_{it}) = \beta \ln(Q_{it}) + \alpha_i (\text{Market FE}) + \gamma_t (\text{Month FE}) + \epsilon_{it}$$
- **Estimated Elasticity:** Across 186,681 observations in 360 mandis, **$\beta = -0.0471$ (Cluster SE: $0.0206$, $t = -2.29$)**.
- **Price Response:** A 10% decrease in local reported arrivals is associated with an empirical price change of **+0.50%**. Regional market integration and inter-mandi truck re-routing smooth local daily supply fluctuations.

### Investigation D: Reporting Quality & Mandi Forensics
- **Frozen Price Streaks:** Audited **27,420 instances** of $\ge 7$ consecutive days of frozen prices.
- **Forensic Diagnostics:** Identified administrative price ceilings in Tamil Nadu Uzhavar Sandhai (518 days in Banana) and statutory MSP procurement quotes in Telangana Paddy (373 days at ₹2,320/qtl).
- **Flat Quote Share:** Telangana reports 37.9% flat quotes (min = max = modal), whereas Maharashtra reports only 4.74%.

---

## 2. Technical Stack & Deliverables Built
- **Database Engine:** DuckDB 2.0.0 zero-copy Parquet engine.
- **Pipeline:** `src/cleaning/pipeline.py` with 100% row conservation (1,481,250 valid, 70 scale errors, 4 zero arrivals).
- **Interactive UI:** Streamlit 1.66.1 with 6 fully functional workspaces and Plotly visualizations.
- **Simulator:** Deterministic decision support tool modeling landed capital, transit shrinkage, handling, and breakeven delivered cost.
- **Automated Tests:** 16 Pytest tests passing with 100% pass rate in 5.07 seconds.
- **Playwright Automation:** All 6 workspaces automated and validated with 7 full-page screenshots in `screenshots/runtime/`.

---

## 3. Sprint Checklist & Milestone Sign-Off

- [x] **Milestone 1: Source Data Profiling** (1,481,324 rows verified, 467-day and 507-day overlaps reproduced).
- [x] **Milestone 2: Data Pipeline & Standardized Views** (`vw_clean_market_history`, row conservation ledger).
- [x] **Milestone 3: Analytical Investigations (A, B, C, D)** (Market spreads, volatility CV, panel econometrics, staleness forensics).
- [x] **Milestone 4: Interactive Decision-Support Application** (`dashboard/app.py` with 6 workspaces).
- [x] **Milestone 5: Automated Tests & Playwright UI Validation** (16 pytest passed, 7 screenshots captured).
- [x] **Milestone 6: Comprehensive Documentation** (`README.md`, `DATA_DICTIONARY.md`, `METHODOLOGY.md`, `SOURCE_REGISTER.md`).
- [x] **Milestone 7: Completion Report Published** (`SPRINT2_COMPLETION_REPORT.md`).
