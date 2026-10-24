# Source Provenance & Licensing Register — MarketPulse India

## 1. Dataset Provenance & Attribution

- **Source System:** AGMARKNET (Agricultural Marketing Information Network), Directorate of Marketing & Inspection (DMI), Department of Agriculture & Farmers Welfare, Ministry of Agriculture & Farmers Welfare, Government of India.
- **Official Portal:** https://agmarknet.gov.in
- **Data Repository:** National Open Government Data (OGD) Platform India (https://data.gov.in).
- **Snapshot File:** `all_market_history.parquet` (8,190,344 bytes compressed Parquet).
- **Retrieval & Compilation Date:** October 2026 snapshot.
- **Coverage Span:** 30 August 2024 to 28 September 2026.
- **Total Record Count:** **1,481,324 wholesale market-day observations**.

---

## 2. Licensing & Terms of Use

- **License:** National Data Sharing and Accessibility Policy (NDSAP) / Government Open Data License - India (GODL).
- **Redistribution Rights:** Open for public research, educational, analytical, and decision-support applications, provided that official source attribution is maintained.
- **Redistribution Notice:** MarketPulse India utilizes a static, authenticated historical snapshot to ensure reproducible testing, offline stability, and peer review verification without external API outages.

---

## 3. Known Data Limitations & Caveats

1. **Modal Price Definition:**
   AGMARKNET reports a single representative or modal price per market day. It does not provide intraday micro-lot bid distributions, volume-weighted median spreads, or buyer-seller identity.
2. **Terminal Variety Aggregation:**
   Large urban terminal markets (e.g. Mumbai APMC, Pune Pimpri) report aggregate commodity averages under generic labels (e.g. 'Other'), concealing the ratio of high-grade vs cull produce.
3. **Mandi Reporting Frequency:**
   Certain seasonal commodities and smaller rural yards report irregularly during harvest off-seasons.
4. **Unit Convention:**
   All wholesale market prices are quoted in **₹ per Quintal** (100 kg), and arrival quantities are quoted in **Metric Tonnes** (1,000 kg). Scale errors (< ₹10/quintal) originating from manual data entry in local units have been quarantined in the pipeline.
