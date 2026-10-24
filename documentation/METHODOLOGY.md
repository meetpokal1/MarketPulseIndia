# Methodology & Econometric Design — MarketPulse India

This document details the analytical formulations, mathematical proofs, and econometric models implemented in **MarketPulse India**.

---

## 1. Investigation A: Spatial Market Spreads & Variety Confounding

### Theoretical Formulation
In standard spatial price theory (Enke-Samuelson-Takayama-Judge model), two competitive market yards $i$ (origin / rural hub) and $j$ (destination / urban terminal) trading an identical homogeneous good must satisfy:

$$P_{jt} - P_{it} \le T_{ijt}$$

where $P_{jt}$ is terminal market price, $P_{it}$ is farm-gate price, and $T_{ijt}$ is transport, handling, and transaction cost. If $P_{jt} - P_{it} > T_{ijt}$, trade occurs until spatial arbitrage restores equilibrium.

### The Empirical Paradox in Lasalgaon vs. Mumbai
When computing date-matched daily spreads for Onion:

$$\text{Spread}_t = P_{\text{Mumbai}, t} - P_{\text{Lasalgaon}, t}$$

across all 507 overlapping trading days from August 2024 to September 2026:
- **Mean Spread:** **-₹157.76/quintal**
- **Median Spread:** **-₹100.00/quintal**
- **Negative Spread Proportion:** **74.75% of days** (379 of 507 days)

Reported Mumbai prices were lower than Lasalgaon on three out of four trading days.

### Decomposing Variety Heterogeneity
Auditing variety distributions exposes severe asymmetric reporting:
1. **Mumbai APMC (`20-2703`):** 100% of reported records (507 of 507 days) are aggregated under the single generic string `'Other'`.
2. **Lasalgaon APMC (`20-161`):** Differentiates agricultural cultivars:
   - **Unhali (110 days):** Storable, low-moisture summer crop harvested April-May. Trades at a major quality premium. Mean spread vs Mumbai: **-₹228.36/quintal** (84.5% negative days).
   - **Red (150 days):** Fresh kharif harvest. Mean spread vs Mumbai: **-₹210.58/quintal** (74.7% negative days).
   - **Other (247 days):** Common / lower-grade lots. Mean spread vs Mumbai: **-₹94.25/quintal**.

**Conclusion:** Naive spatial spread comparisons without variety controls compare generic terminal market averages against premium farm-gate lots. This introduces severe composition bias, disproving claims of unadjusted spatial arbitrage.

---

## 2. Investigation B: Price Volatility & Outlier Shocks

### Metrics
1. **Coefficient of Variation (CV):**
   $$\text{CV} = \frac{\sigma_P}{\mu_P}$$
2. **30-Day Rolling Volatility:**
   $$\text{CV}_{30, t} = \frac{\sigma_{P, [t-29, t]}}{\mu_{P, [t-29, t]}}$$
3. **Daily Price Return & Anomaly Shock:**
   $$r_t = \ln(P_t) - \ln(P_{t-1})$$
   $$\text{Shock Flag} \iff |r_t| > \max(0.20, 2.5 \cdot \sigma_r)$$
4. **Shock Persistence (AR(1) Autocorrelation):**
   $$\rho_1 = \frac{\sum (r_t - \bar{r})(r_{t-1} - \bar{r})}{\sum (r_t - \bar{r})^2}$$

In Lasalgaon Onion, $\rho_1 = -0.0146$, indicating fast mean-reversion without persistent speculative momentum, characteristic of physical daily multi-lot auctions.

---

## 3. Investigation C: Econometric Panel Regression (Prices vs. Arrivals)

### The Myth Debunked
Industry folklore often asserts: *"A 10% drop in arrivals causes a 35% to 50% surge in prices"*.

### Econometric Specification
To estimate the empirical elasticity of wholesale prices with respect to arrival quantities without omitted variable bias from mandi-specific unobservables or macroeconomic inflation, we estimate a **Two-Way Fixed Effects (TWFE)** panel model:

$$\ln(P_{it}) = \beta \ln(Q_{it}) + \alpha_i + \gamma_t + \epsilon_{it}$$

where:
- $P_{it}$ is the modal price in APMC market $i$ on date $t$.
- $Q_{it}$ is total arrivals in tonnes in market $i$ on date $t$.
- $\alpha_i$ is the unobserved time-invariant APMC market fixed effect (absorbing geography, baseline infrastructure, road connectivity).
- $\gamma_t$ is the monthly time fixed effect (absorbing seasonal production cycles, national diesel price shocks, central export bans).
- $\beta$ is the within-market arrival elasticity of price.

### High-Performance Estimation via Frisch-Waugh-Lovell Demeaning
Rather than inverting a $450 \times 450$ dummy variable matrix across 186,000 rows, variables are transformed via two-way demeaning:

$$\tilde{y}_{it} = y_{it} - \bar{y}_{i\cdot} - \bar{y}_{\cdot t} + \bar{y}$$
$$\tilde{x}_{it} = x_{it} - \bar{x}_{i\cdot} - \bar{x}_{\cdot t} + \bar{x}$$
$$\hat{\beta}_{\text{TWFE}} = \frac{\sum_{i,t} \tilde{x}_{it} \tilde{y}_{it}}{\sum_{i,t} \tilde{x}_{it}^2}$$

### Cameron-Miller Cluster-Robust Standard Errors
Because price shocks within a market are autocorrelated over time, standard OLS standard errors underestimate variance. We apply cluster-robust sandwich covariance clustered at the market level ($i$):

$$\widehat{\text{Var}}(\hat{\beta}) = \frac{N-1}{N-K} \frac{G}{G-1} \cdot \frac{\sum_{i=1}^G \left(\sum_{t} \tilde{x}_{it} \hat{\epsilon}_{it}\right)^2}{\left(\sum_{i,t} \tilde{x}_{it}^2\right)^2}$$

### Empirical Estimation Results (Onion National Panel)
- **Observations ($N$):** **186,681**
- **APMC Mandis ($G$):** **360**
- **Time Periods ($T$):** **26 Months**
- **Estimated Elasticity ($\hat{\beta}$):** **-0.0471**
- **Cluster-Robust SE:** **0.0206**
- **$t$-statistic:** **-2.29** ($p < 0.05$)
- **95% Confidence Interval:** **[-0.0875, -0.0067]**

### Economic Interpretation
A **+10% increase** in arrivals is associated with a **-0.45% change** in modal price.  
A **-10% decrease** in arrivals is associated with a **+0.50% change** in modal price.

**Why is daily wholesale price so inelastic to local arrivals?**  
Indian agricultural wholesale markets are spatially integrated. When arrivals dip in a single mandi on a given Tuesday, buyers do not bid up prices by 40%; they redirect trucks from neighboring mandis within 50 km, draw from cold storage stock, or postpone purchases to Wednesday's auction.

---

## 4. Investigation D: Reporting Quality & Mandi Staleness Forensics

### Diagnostic Classification Rules
1. **Frozen Price Streak:**
   A sequence of consecutive reported trading dates $\Delta t \le 4$ calendar days where:
   $$P_t = P_{t-1} \quad \text{for } k \ge 7 \text{ trading days}$$
2. **Forensic Attribution:**
   - **MSP Statutory Pegging:** Identified in crops with central procurement (e.g. Telangana Paddy at ₹2,320/qtl for 373 days).
   - **Administrative Price Ceilings:** Identified in state-administered direct farmer bazaars (e.g. Tamil Nadu Uzhavar Sandhai Banana for 518 days).
   - **Stale Administrative Inertia:** Repeated quotes during auction recesses or reporting neglect.
3. **Flat Quotes:**
   Identified where $\text{Min Price} = \text{Max Price} = \text{Modal Price}$. Indicates lack of multi-lot auction grade dispersion.
