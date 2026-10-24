# MarketPulse India — Tableau Data Contract & Analytical Extract Specification

**Specification Version:** 1.0.0 (Stage 3A Data Foundation)  
**Export Date:** October 2026  
**Pipeline Source:** `scripts/build_tableau_extract.py`  
**Manifest:** `data/processed/tableau/manifest.json`  
**Primary Source Dataset:** `data/raw/all_market_history.parquet`  
**Verified Source SHA-256:** `DA8E4435D7B63693C406401E0FA3B1F084FD1010F650598BA5030715A57ED6A4`  
**Temporal Coverage:** 30 August 2024 to 28 September 2026 (25 Calendar Months)  
**Geographic Coverage:** 6 Indian States (Gujarat, Karnataka, Kerala, Maharashtra, Tamil Nadu, Telangana; 176 Districts, 1,537 APMC Mandis)  
**Commodity Coverage:** 14 Major Agricultural Commodities (Onion, Tomato, Potato, Green Chilli, Banana, Brinjal, Coconut, Maize, Paddy (Common), Groundnut, Cotton, Arecanut, Ragi, Turmeric)  

---

## 1. Architecture & Design Principles

The MarketPulse India Tableau data product decouples disparate analytical domains into focused, normalized datasets at their native grains. **Daily spot quotes, monthly aggregations, econometric model estimates, and reliability streaks are intentionally not joined into a monolithic table.** This architecture prevents:
- Many-to-many join cartesian blowups and misleading sum totals in Tableau.
- Silent misattribution of monthly averages as daily quotes.
- Conflation of observational price spreads with causal arbitrage returns.

All datasets are generated deterministically via DuckDB and Python analytical engines from the verified repository-local raw Parquet dataset.

---

## 2. Analytical Data Products Specification

### Dataset A: Monthly Market Intelligence (`market_monthly.csv`)
- **File Path:** `data/processed/tableau/market_monthly.csv`
- **Native Grain:** One row per `market_id × commodity × calendar month`
- **Primary Uniqueness Key:** `market_id + commodity + year_month`
- **Total Records:** 77,890 rows | 26 columns | 15.14 MB
- **Target Dashboard:** **Dashboard 1: Market Pulse**
- **Inclusion Rules:** All mandi $\times$ commodity months with $\ge 1$ recorded daily market observation.
- **Null Handling:** Missing prices on non-trading days are not imputed; percentile metrics require $\ge 1$ valid daily price quote.

| Column Name | Data Type | Units / Range | Definition & Calculation Logic |
| :--- | :---: | :---: | :--- |
| `year_month` | String | `YYYY-MM` | Calendar month identifier (e.g., `2024-09` to `2026-09`). |
| `month_start_date` | Date | `YYYY-MM-01` | First calendar day of the month for continuous time-series axes in Tableau. |
| `state_id` | Integer | 1 to 32 | AGMARKNET official state identifier code. |
| `state` | String | Categorical | State name (Gujarat, Karnataka, Kerala, Maharashtra, Tamil Nadu, Telangana). |
| `district` | String | Categorical | Revenue district name of the reporting APMC mandi. |
| `market_id` | String | Unique Code | Official APMC market identifier (e.g., `20-161` for Lasalgaon). |
| `canonical_market_name` | String | Normalized Text | Standardized canonical APMC market title with title-casing and typos resolved. |
| `commodity` | String | Categorical | Agricultural commodity name (1 of 14 core commodities). |
| `observed_records_count` | Integer | $\ge 1$ | Total daily reporting rows submitted by this mandi for this commodity in the month. |
| `valid_price_records_count` | Integer | $\ge 0$ | Number of daily observations passing price validation (`is_valid_price = TRUE`). |
| `mean_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | Arithmetic mean of valid daily modal prices in that month. |
| `median_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | Median (50th percentile) of valid daily modal prices in that month. |
| `min_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | Monthly minimum of valid daily modal prices (distinct from daily min_price). |
| `max_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | Monthly maximum of valid daily modal prices (distinct from daily max_price). |
| `p25_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | 25th percentile (Q1) of valid daily modal prices. |
| `p75_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | 75th percentile (Q3) of valid daily modal prices. |
| `std_daily_modal_price_rs_per_quintal` | Float | ₹/Quintal | Sample standard deviation of valid daily modal prices in the month. |
| `total_arrivals_tonnes` | Float | Tonnes | Sum of physical arrivals reported across the calendar month. |
| `mean_daily_arrivals_tonnes` | Float | Tonnes | Mean physical arrivals per reporting trading day. |
| `positive_arrival_records_count` | Integer | $\ge 0$ | Number of daily reports where `arrivals_tonnes > 0`. |
| `flat_quote_records_count` | Integer | $\ge 0$ | Days where `min_price == max_price == modal_price_quintal` (price dispersion anomaly). |
| `statistical_anomalies_count` | Integer | $\ge 0$ | Days flagged by statistical anomaly detector ($|z| \ge 3.0$). |
| `scale_error_records_count` | Integer | $\ge 0$ | Days flagged as low-price scale errors ($< ₹10/\text{Qtl}$). |
| `zero_arrival_records_count` | Integer | $\ge 0$ | Days with reported arrivals $\le 0.0$ tonnes. |
| `dominant_raw_variety` | String | Text | Statistical mode of the raw variety string reported in that month. |
| `dominant_variety_tier` | String | Categorical | Statistical mode of variety tier: `Specific Variety` vs `Generic Other`. |

---

### Dataset B: Matched-Market Daily Comparison (`corridor_spread_daily.csv`)
- **File Path:** `data/processed/tableau/corridor_spread_daily.csv`
- **Native Grain:** One row per `corridor_id × date`
- **Primary Uniqueness Key:** `corridor_id + date`
- **Total Records:** 1,927 rows | 25 columns | 0.87 MB
- **Target Dashboard:** **Dashboard 2: Spread Lab**
- **Corridors Analyzed:**
  1. `CORR_LAS_MUM_ONION`: Lasalgaon APMC (`20-161`) $\rightarrow$ Mumbai APMC (`20-2703`) (507 matched days, flagship spread inversion case study).
  2. `CORR_LAS_PUN_ONION`: Lasalgaon APMC (`20-161`) $\rightarrow$ Pune APMC (`20-164`) (429 matched days, origin to regional hub).
  3. `CORR_PIM_MUM_ONION`: Pimpalgaon Baswant APMC (`20-162`) $\rightarrow$ Mumbai APMC (`20-2703`) (538 matched days, secondary Nashik origin to metro).
  4. `CORR_PUN_MUM_ONION`: Pune APMC (`20-164`) $\rightarrow$ Mumbai APMC (`20-2703`) (453 matched days, inter-city metro corridor).

| Column Name | Data Type | Units / Range | Definition & Calculation Logic |
| :--- | :---: | :---: | :--- |
| `corridor_id` | String | Identifier | Unique corridor identifier code (e.g. `CORR_LAS_MUM_ONION`). |
| `corridor_name` | String | Text | Descriptive corridor name with origin and destination markets. |
| `commodity` | String | Categorical | Commodity analyzed (`Onion`). |
| `corridor_narrative` | String | Text | Econometric and supply chain context of the trading corridor. |
| `date` | Date | `YYYY-MM-DD` | Overlapping trading date where both markets recorded valid prices. |
| `source_market_name` | String | Text | Canonical name of source/origin mandi. |
| `source_raw_variety` | String | Text | Specific raw cultivar reported by source market (e.g., `Unhali`, `Red`, `Other`). |
| `source_std_variety` | String | Text | Standardized variety string. |
| `source_variety_tier` | String | Categorical | `Specific Variety` vs `Generic Other`. |
| `source_price` | Float | ₹/Quintal | Modal price at origin market. |
| `source_arrivals` | Float | Tonnes | Physical arrivals at origin market. |
| `dest_market_name` | String | Text | Canonical name of destination terminal mandi. |
| `dest_raw_variety` | String | Text | Raw cultivar reported by destination market (`Other` in 100% of Mumbai days). |
| `dest_std_variety` | String | Text | Standardized destination variety (`Other / Unspecified`). |
| `dest_variety_tier` | String | Categorical | Destination variety tier (`Generic Other`). |
| `dest_price` | Float | ₹/Quintal | Modal price at destination market. |
| `dest_arrivals` | Float | Tonnes | Physical arrivals at destination market. |
| `price_spread_quintal` | Float | ₹/Quintal | Destination Price minus Source Price (`dest_price - source_price`). |
| `price_spread_kg` | Float | ₹/kg | Price spread expressed per kilogram (`price_spread_quintal / 100.0`). |
| `spread_pct` | Float | % | Spread relative to origin price: `(dest - source) / source * 100.0`. |
| `variety_comparability_status` | String | Categorical | `CULTIVAR_CONFOUNDED_OTHER`, `GENERIC_TIER_MATCHED`, `CULTIVAR_EXACT_MATCHED`. |
| `is_spread_negative` | Boolean | True / False | True if destination price is lower than origin price (`price_spread_quintal < 0`). |
| `apparent_inversion_flag` | Boolean | True / False | True if spread is negative AND comparison is cultivar-confounded. |

---

### Dataset C: Econometric Model Results (`arrival_elasticity_models.csv`)
- **File Path:** `data/processed/tableau/arrival_elasticity_models.csv`
- **Native Grain:** One row per commodity panel regression model
- **Primary Uniqueness Key:** `commodity + model_id`
- **Total Records:** 14 rows | 26 columns | 10.8 KB
- **Target Dashboard:** **Dashboard 3: Arrival–Price Research**
- **Methodology:** Two-Way Fixed Effects (TWFE) with market fixed effects ($\alpha_i$) and month fixed effects ($\gamma_t$):
  $$\ln(\text{price}_{it}) = \beta \ln(\text{arrivals}_{it}) + \alpha_i + \gamma_t + \varepsilon_{it}$$
  Standard errors are clustered at the APMC market level using the Cameron–Miller cluster-robust degrees-of-freedom correction ($G / (G - 1) \cdot (N - 1) / (N - K)$).

| Column Name | Data Type | Definition & Calculation Logic |
| :--- | :---: | :--- |
| `commodity` | String | Agricultural commodity modeled (all 14 core commodities). |
| `model_id` | String | Identifier (e.g. `TWFE_MKT_MONTH_ONION`). |
| `specification` | String | Econometric specification equation. |
| `dependent_var` | String | Natural logarithm of daily modal price ($\ln(\text{modal\_price\_quintal})$). |
| `explanatory_var` | String | Natural logarithm of daily arrivals ($\ln(\text{arrivals\_tonnes})$). |
| `fixed_effects` | String | Market FE ($\alpha_i$) + Month-Year FE ($\gamma_t$). |
| `standard_error_method` | String | Cameron–Miller Cluster-Robust Standard Errors (clustered by Market ID). |
| `n_observations` | Integer | Sample size (e.g., $N = 197,941$ for Onion). |
| `n_market_clusters` | Integer | Number of distinct APMC market clusters ($G = 394$ for Onion). |
| `n_calendar_months` | Integer | Distinct month periods ($T = 25$). |
| `pooled_ols_beta` | Float | Benchmark naive OLS elasticity without fixed effects. |
| `estimated_elasticity_beta` | Float | TWFE elasticity coefficient ($\beta = -0.0360$ for Onion). |
| `cluster_robust_se` | Float | Cluster-robust standard error ($\text{SE} = 0.0183$ for Onion). |
| `t_statistic` | Float | Empirical t-statistic ($\beta / \text{SE} = -1.97$). |
| `p_value_approx` | String | Two-tailed p-value ($< 0.05$). |
| `ci_95_lower` | Float | Lower bound of 95% confidence interval ($\beta - 1.96 \cdot \text{SE} = -0.0720$). |
| `ci_95_upper` | Float | Upper bound of 95% confidence interval ($\beta + 1.96 \cdot \text{SE} = -0.0001$). |
| `within_r2` | Float | Within-market/month $R^2$ variance explained ($0.0138$). |
| `price_response_pct_for_plus_10pct_arrivals` | Float | Estimated % price change for $+10\%$ arrival shock: $((1.10^\beta - 1) \cdot 100 = -0.34\%)$. |
| `price_response_pct_for_minus_10pct_arrivals` | Float | Estimated % price change for $-10\%$ arrival dip: $((0.90^\beta - 1) \cdot 100 = +0.38\%)$. |
| `price_response_pct_for_minus_25pct_arrivals` | Float | Estimated % price change for $-25\%$ arrival dip: $((0.75^\beta - 1) \cdot 100 = +1.04\%)$. |
| `economic_interpretation` | String | Analytical policy conclusion refuting folklore 35–50% price shocks. |
| `causal_disclaimer` | String | Explicit caveat that reduced-form elasticity reflects spot market-clearing equilibrium. |

---

### Dataset D: Reliability Forensics (`frozen_price_streaks.csv`)
- **File Path:** `data/processed/tableau/frozen_price_streaks.csv`
- **Native Grain:** One row per uninterrupted frozen price streak ($\ge 7$ consecutive trading days)
- **Primary Uniqueness Key:** `streak_id`
- **Total Records:** 27,420 rows | 14 columns | 5.35 MB
- **Target Dashboard:** **Dashboard 4: Reliability Forensics**
- **Definition:** Consecutive trading records for the same mandi and commodity where `modal_price_quintal` remained identical without price revision, with gap between dates $\le 4$ calendar days (accommodating weekends).

| Column Name | Data Type | Definition & Calculation Logic |
| :--- | :---: | :--- |
| `streak_id` | Integer | Unique identifier ranked by streak duration descending. |
| `state` | String | State where mandi is located. |
| `district` | String | District of APMC market. |
| `market_id` | String | Official market identifier. |
| `canonical_market_name` | String | Standardized APMC market title. |
| `commodity` | String | Commodity exhibiting frozen price. |
| `frozen_modal_price_rs_per_quintal` | Float | Exact price quote unchanged across the streak. |
| `streak_start_date` | Date | Date when unchanged price streak began. |
| `streak_end_date` | Date | Date when unchanged price streak concluded. |
| `streak_days` | Integer | Number of consecutive trading day reports with identical price ($\ge 7$). |
| `calendar_span_days` | Integer | Total elapsed calendar days from start to end (`streak_end - streak_start + 1`). |
| `plausible_explanation` | String | Forensic classification: `MSP Statutory Procurement Quote`, `Administrative Price Ceiling`, `Likely Reporting Inactivity`, or `Candidate Price Stickiness`. |
| `audit_priority` | String | Prioritization tier: `HIGH REVIEW` ($\ge 30$ days), `MEDIUM REVIEW` ($\ge 14$ days), `LOW NOTICE` ($\ge 7$ days). |
| `is_msp_statutory_quote` | Boolean | True if Paddy (Common) quoted at official MSP procurement rates (₹2,183, ₹2,203, ₹2,300, ₹2,320). |

---

### Dataset E: Data Quality Exceptions (`quality_exceptions.csv`)
- **File Path:** `data/processed/tableau/quality_exceptions.csv`
- **Native Grain:** One row per quarantined raw observation
- **Primary Uniqueness Key:** `exception_id`
- **Total Records:** 74 rows | 16 columns | 21.7 KB
- **Target Dashboard:** **Dashboard 4: Reliability Forensics (Quality Audit View)**
- **Audit Basis:** Quarantined records failing Stage 2 hardened price validation rule (`min_price < 10.0` or `representative_price < 10.0`) or arrival rules (`arrivals_tonnes <= 0.0`).

| Column Name | Data Type | Definition & Diagnostic Reason |
| :--- | :---: | :--- |
| `exception_id` | Integer | Primary sequential identifier. |
| `state`, `district`, `market_id` | String | Mandi geographic identification. |
| `commodity`, `raw_variety` | String | Commodity and cultivar reported. |
| `date` | Date | Trading date of anomalous record. |
| `min_price_rs_per_quintal` | Float | Quoted raw minimum price. |
| `max_price_rs_per_quintal` | Float | Quoted raw maximum price. |
| `modal_price_rs_per_quintal` | Float | Quoted raw modal price. |
| `arrivals_tonnes` | Float | Quoted raw arrival volume. |
| `is_valid_price`, `is_valid_arrival` | Boolean | Individual validation gate evaluation. |
| `record_quality_status` | String | `SCALE_ERROR_LOW_PRICE` (70 rows) vs `ZERO_ARRIVALS` (4 rows). |
| `quarantine_diagnostic_reason` | String | Forensic explanation of unit scale distortion (Banana bunches vs 100 kg quintal) or zero volume. |

---

### Dataset F: Monthly Quality Summary (`quality_monthly_summary.csv`)
- **File Path:** `data/processed/tableau/quality_monthly_summary.csv`
- **Native Grain:** One row per `state × calendar month`
- **Primary Uniqueness Key:** `state + year_month`
- **Total Records:** 156 rows | 13 columns | 13.2 KB
- **Target Dashboard:** **Dashboard 4: Reliability Forensics (State Reliability Trends)**

| Column Name | Data Type | Definition |
| :--- | :---: | :--- |
| `year_month`, `month_start_date` | String / Date | Temporal grain identifiers. |
| `state_id`, `state` | Integer / String | State identifiers. |
| `total_raw_records` | Integer | Total raw records received in that state-month (sums to 1,481,324). |
| `valid_records` | Integer | Records passing all quality criteria (sums to 1,481,250). |
| `scale_error_records` | Integer | Records flagged as low-price scale errors (sums to 70). |
| `zero_arrival_records` | Integer | Records flagged with zero physical arrivals (sums to 4). |
| `flat_quote_records` | Integer | Days where min == max == modal price. |
| `flat_quote_rate_pct` | Float | Percentage of daily quotes that are completely flat ($0.0\%$ price spread). |
| `statistical_anomaly_records` | Integer | Observations flagged by anomaly detection engine ($|z| \ge 3.0$). |
| `statistical_anomaly_rate_pct` | Float | Percentage of monthly records identified as statistical outliers. |
| `quality_pass_rate_pct` | Float | Quality assurance yield: `valid_records / total_raw_records * 100.0`. |

---

## 3. Row-Accounting Conservation Law

Every raw record in `all_market_history.parquet` is accounted for with zero data leakage:

$$\begin{aligned}
\text{Total Raw Records} &= 1,481,324 \\
&= \text{Valid Records } (1,481,250) \\
&\quad + \text{Scale Errors } (70) \\
&\quad + \text{Zero Arrivals } (4) \\
&\quad + \text{Inverted Price Ranges } (0) \\
&\quad + \text{Unhandled Null Records } (0)
\end{aligned}$$

- **Preservation Rate:** **99.995%** of source records qualify for full econometric and spread analytics.
- **Mutual Exclusivity:** As proven in the Stage 2 integrity audit, zero records fail both price and arrival validation; the quality taxonomy partitions the entire dataset without double counting.

---

## 4. Known Data Limitations & Analytical Boundaries

1. **Geospatial Coordinates:** The source AGMARKNET dataset does not contain latitude/longitude coordinates for APMC mandis. Centroids or synthetic pins must never be manufactured. Geographic visualizations in Tableau are constrained to state-level polygons.
2. **Snapshot Extract Nature:** This dataset is a curated research snapshot covering August 2024 to September 2026. It is not an automated live feed from the AGMARKNET portal.
3. **Cultivar Reporting Confounding:** Price spreads between markets (notably Lasalgaon and Mumbai) must be evaluated with `variety_comparability_status`. Mumbai reporting 100% generic 'Other' introduces cultivar confounding against origin mandis that report premium cultivars (Unhali, Red).
4. **Econometric Association vs Causality:** Arrival-price elasticity estimates ($\beta$) reflect reduced-form short-run market clearing associations, not structural macroeconomic demand elasticities.
