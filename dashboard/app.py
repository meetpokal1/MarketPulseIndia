"""
MarketPulse India - Agricultural Market-Price & Supply Intelligence Platform
Streamlit Decision-Support Application
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date

# Core analytical modules
from src.config import (
    CORE_COMMODITIES,
    LASALGAON_MAIN_ID,
    MUMBAI_ONION_POTATO_ID,
    LASALGAON_NIPHAD_ID,
    LASALGAON_VINCHUR_ID,
    PUNE_MAIN_ID,
    PIMPALGAON_BASWANT_ID,
)
from src.ingestion.loader import get_loader
from src.cleaning.pipeline import PipelineAuditor
from src.analytics.market_spreads import MarketSpreadEngine
from src.analytics.volatility import VolatilityAnalyzer
from src.models.econometrics import PanelEconometricEngine
from src.analytics.reliability_audit import ReliabilityAuditor
from src.simulator.decision_simulator import DecisionSimulator

# Page Configuration
st.set_page_config(
    page_title="MarketPulse India — Agri Market Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Styling
st.markdown("""
<style>
    /* Dark Editorial Palette */
    .stApp {
        background-color: #0c1017;
        color: #e2e8f0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Top Banner Badge */
    .mp-banner {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .mp-banner-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f59e0b;
        letter-spacing: 0.5px;
    }
    .mp-badge {
        background-color: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.35);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
    }
    .mp-badge-verified {
        background-color: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.35);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    
    /* KPI Card styling */
    div[data-testid="stMetric"] {
        background: #151d2a;
        border: 1px solid #243144;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.25);
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.85rem !important;
        font-weight: 500;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-size: 1.6rem !important;
        font-weight: 700;
    }
    
    /* Callout & Disclaimer boxes */
    .callout-amber {
        background-color: rgba(245, 158, 11, 0.08);
        border-left: 4px solid #f59e0b;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        margin: 12px 0;
        color: #fde68a;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .callout-rose {
        background-color: rgba(244, 63, 94, 0.08);
        border-left: 4px solid #f43f5e;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        margin: 12px 0;
        color: #fecdd3;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .callout-emerald {
        background-color: rgba(16, 185, 129, 0.08);
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 0 6px 6px 0;
        margin: 12px 0;
        color: #a7f3d0;
        font-size: 0.9rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_singletons():
    loader = get_loader()
    auditor = PipelineAuditor(loader)
    spread_engine = MarketSpreadEngine(loader)
    vol_analyzer = VolatilityAnalyzer(loader)
    econ_engine = PanelEconometricEngine(loader)
    rel_auditor = ReliabilityAuditor(loader)
    return loader, auditor, spread_engine, vol_analyzer, econ_engine, rel_auditor


loader, auditor, spread_engine, vol_analyzer, econ_engine, rel_auditor = load_singletons()
meta = loader.get_metadata()

# Sidebar Navigation
st.sidebar.markdown("## 🌾 MarketPulse India")
st.sidebar.caption("AGRICULTURAL MARKET & SUPPLY INTELLIGENCE")
st.sidebar.markdown(
    '<div class="mp-badge-verified">EVIDENCE-DRIVEN • 1.48M AGMARKNET RECORDS</div>',
    unsafe_allow_html=True,
)
st.sidebar.markdown("---")

nav_choice = st.sidebar.radio(
    "NAVIGATION WORKSPACES",
    [
        "1. Market Explorer",
        "2. Price Intelligence & Volatility",
        "3. Arrival–Price Panel Investigation",
        "4. Data Reliability Lab",
        "5. Market Decision Simulator",
        "6. Research Brief & Export",
    ],
    index=0,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Dataset Scope")
st.sidebar.markdown(f"""
- **Records:** `{meta['total_rows']:,}`
- **Coverage:** `{meta['unique_states']}` States • `{meta['unique_market_ids']:,}` APMCs
- **Commodities:** `{meta['unique_commodities']}` Key Crops
- **Period:** `{meta['min_date']}` to `{meta['max_date']}`
""")

# ==============================================================================
# WORKSPACE 1: MARKET EXPLORER
# ==============================================================================
if nav_choice == "1. Market Explorer":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Market Explorer: APMC Network & Price Levels</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Inspect reported modal prices, arrival volumes, and date coverage across regional agricultural markets.</div>
        </div>
        <div class="mp-badge">EXPLORATORY APMC SCAN</div>
    </div>
    """, unsafe_allow_html=True)

    col_c, col_s = st.columns([1, 1])
    with col_c:
        selected_commodity = st.selectbox("Select Agricultural Commodity", CORE_COMMODITIES, index=0)
    with col_s:
        available_states = ["All States", "Maharashtra", "Tamil Nadu", "Kerala", "Karnataka", "Telangana", "Andhra Pradesh"]
        selected_state = st.selectbox("Filter State", available_states, index=0)

    state_filter = None if selected_state == "All States" else selected_state
    markets_df = loader.get_markets_for_commodity(selected_commodity, state=state_filter)

    # Top KPI Metrics
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    kpi1.metric("Reporting Markets", f"{len(markets_df):,}")
    kpi2.metric("Total Records", f"{markets_df['total_observations'].sum():,}")
    kpi3.metric("Median Modal Price", f"₹{markets_df['median_modal_price'].median():,.1f}/Qtl")
    kpi4.metric("Average Arrivals", f"{markets_df['avg_arrivals_tonnes'].mean():,.1f} MT/day")
    kpi5.metric("Date Span", "25 Months")

    st.markdown("### Top Reporting Mandis by Observation Depth")
    st.dataframe(
        markets_df[[
            "canonical_market_name" if "canonical_market_name" in markets_df.columns else "market_name",
            "state", "district", "trading_days", "avg_modal_price", "median_modal_price", "price_cv", "avg_arrivals_tonnes", "first_reported_date", "last_reported_date"
        ]].rename(columns={
            "canonical_market_name": "Market Name",
            "market_name": "Market Name",
            "state": "State",
            "district": "District",
            "trading_days": "Trading Days",
            "avg_modal_price": "Avg Price (₹/Qtl)",
            "median_modal_price": "Median (₹/Qtl)",
            "price_cv": "Price Volatility (CV)",
            "avg_arrivals_tonnes": "Avg Arrivals (Tonnes)",
            "first_reported_date": "First Date",
            "last_reported_date": "Last Date",
        }).head(25),
        use_container_width=True,
        hide_index=True,
    )

    # Price vs Arrivals Bubble Chart
    st.markdown("### Market Size vs Price Level")
    fig = px.scatter(
        markets_df.head(60),
        x="avg_arrivals_tonnes",
        y="avg_modal_price",
        size="trading_days",
        color="state",
        hover_name="market_name",
        labels={
            "avg_arrivals_tonnes": "Average Daily Arrivals (Metric Tonnes)",
            "avg_modal_price": "Average Modal Price (₹/Quintal)",
            "state": "State",
            "trading_days": "Reported Trading Days",
        },
        title=f"{selected_commodity}: Price vs Arrival Volume across Top APMC Mandis",
        template="plotly_dark",
    )
    fig.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", height=480)
    st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# WORKSPACE 2: PRICE INTELLIGENCE & VOLATILITY
# ==============================================================================
elif nav_choice == "2. Price Intelligence & Volatility":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Price Intelligence: Corridor Spreads & Volatility Dynamics</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Investigations A & B: Spatial price spreads, variety heterogeneity, and price return shocks.</div>
        </div>
        <div class="mp-badge">INVESTIGATIONS A & B</div>
    </div>
    """, unsafe_allow_html=True)

    tab_spread, tab_vol = st.tabs(["Spatial Price Spreads (Investigation A)", "Commodity Volatility & Shocks (Investigation B)"])

    with tab_spread:
        st.markdown("### Corridor Comparison: Producer Hub vs Terminal Urban Mandi")
        st.markdown("""
        <div class="callout-amber">
            <b>Core Empirical Finding (Investigation A):</b> Across <b>507 overlapping trading days</b> between Lasalgaon APMC 
            and Mumbai-Onion APMC, the unadjusted price spread (Mumbai minus Lasalgaon) has a <b>negative mean of -₹157.76/quintal</b>, 
            with Mumbai prices reported as lower than Lasalgaon on <b>74.8% of days</b>. 
            Controlling for variety reveals severe reporting heterogeneity: Mumbai reports 100% of arrivals as generic 'Other', 
            while Lasalgaon trades premium export 'Unhali' (-₹228 spread) and 'Red' (-₹210 spread).
        </div>
        """, unsafe_allow_html=True)

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p1:
            comm_choice = st.selectbox("Commodity", ["Onion", "Tomato", "Potato"], index=0)
        with col_p2:
            corridor_presets = {
                "Lasalgaon APMC (20-161) → Mumbai APMC (20-2703)": (LASALGAON_MAIN_ID, MUMBAI_ONION_POTATO_ID),
                "Lasalgaon Niphad (20-2139) → Mumbai APMC (20-2703)": (LASALGAON_NIPHAD_ID, MUMBAI_ONION_POTATO_ID),
                "Lasalgaon Vinchur (20-3448) → Mumbai APMC (20-2703)": (LASALGAON_VINCHUR_ID, MUMBAI_ONION_POTATO_ID),
                "Pimpalgaon Baswant (20-162) → Mumbai APMC (20-2703)": (PIMPALGAON_BASWANT_ID, MUMBAI_ONION_POTATO_ID),
                "Lasalgaon APMC (20-161) → Pune APMC (20-110)": (LASALGAON_MAIN_ID, PUNE_MAIN_ID),
            }
            corridor_sel = st.selectbox("Corridor Preset", list(corridor_presets.keys()), index=0)
            src_id, dst_id = corridor_presets[corridor_sel]
        with col_p3:
            variety_mode = st.selectbox("Variety Inclusion Rule", ["ALL", "EXACT", "OTHER_ONLY", "Unhali", "Red"], index=0)

        spread_data = spread_engine.compare_markets(
            commodity=comm_choice,
            source_market_id=src_id,
            dest_market_id=dst_id,
            variety_filter_mode=variety_mode,
        )

        if spread_data.get("n_overlapping_days", 0) > 0:
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Overlapping Days", f"{spread_data['n_overlapping_days']}")
            m2.metric("Mean Price Spread", f"₹{spread_data['mean_spread_quintal']:+,.2f}/Qtl")
            m3.metric("Median Spread", f"₹{spread_data['median_spread_quintal']:+,.2f}/Qtl")
            m4.metric("Negative Spread Days", f"{spread_data['negative_spread_pct']}%", delta=f"{spread_data['negative_spread_days']} days", delta_color="inverse")
            m5.metric("Price Correlation", f"{spread_data['price_correlation']:.3f}")

            pair_df = spread_data["df"]

            # Price Time Series Plot
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(
                x=pair_df["date"], y=pair_df["source_price"],
                mode="lines", name=spread_data["source_market_name"],
                line=dict(color="#f59e0b", width=2)
            ))
            fig_p.add_trace(go.Scatter(
                x=pair_df["date"], y=pair_df["dest_price"],
                mode="lines", name=spread_data["dest_market_name"],
                line=dict(color="#38bdf8", width=2)
            ))
            fig_p.update_layout(
                title=f"{comm_choice}: Daily Modal Price Time Series ({spread_data['source_market_name']} vs {spread_data['dest_market_name']})",
                yaxis_title="Modal Price (₹/Quintal)",
                template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=420,
            )
            st.plotly_chart(fig_p, use_container_width=True)

            # Daily Spread Area Chart
            fig_s = go.Figure()
            fig_s.add_trace(go.Scatter(
                x=pair_df["date"], y=pair_df["price_spread_quintal"],
                mode="lines", name="Price Spread (Dest - Source)",
                fill="tozeroy",
                line=dict(color="#f43f5e" if spread_data["mean_spread_quintal"] < 0 else "#10b981", width=1.5)
            ))
            fig_s.add_hline(y=0, line_dash="dash", line_color="#94a3b8")
            fig_s.update_layout(
                title=f"Price Spread: {spread_data['dest_market_name']} minus {spread_data['source_market_name']} (₹/Quintal)",
                yaxis_title="Price Spread (₹/Quintal)",
                template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=340,
            )
            st.plotly_chart(fig_s, use_container_width=True)

            # Export Extract
            csv_data = pair_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Export Corridor Price Spread Dataset (CSV)",
                data=csv_data,
                file_name=f"marketpulse_corridor_spread_{comm_choice}_{src_id}_{dst_id}.csv",
                mime="text/csv",
            )
        else:
            st.warning("No overlapping observations found for the selected criteria.")

    with tab_vol:
        st.markdown("### Cross-Commodity Volatility Rankings (Coefficient of Variation)")
        vol_df = vol_analyzer.get_commodity_volatility_rankings()
        st.dataframe(
            vol_df.rename(columns={
                "commodity": "Commodity",
                "total_observations": "Observations",
                "reporting_markets": "Markets",
                "mean_price": "Mean Price (₹)",
                "median_price": "Median Price (₹)",
                "std_price": "Std Dev (₹)",
                "price_cv": "Price Volatility (CV)",
                "avg_arrivals": "Avg Arrivals (T)",
                "arrivals_cv": "Arrivals Volatility (CV)",
            }),
            use_container_width=True,
            hide_index=True,
        )

        st.markdown("### Single Market Volatility & Return Shocks")
        v_col1, v_col2 = st.columns(2)
        with v_col1:
            v_comm = st.selectbox("Select Commodity for Shock Analysis", CORE_COMMODITIES, index=0)
        with v_col2:
            v_mkt = st.selectbox(
                "Select Focus Mandi",
                [("Lasalgaon APMC", LASALGAON_MAIN_ID), ("Mumbai APMC", MUMBAI_ONION_POTATO_ID), ("Pune APMC", PUNE_MAIN_ID)],
                format_func=lambda x: x[0],
                index=0
            )[1]

        v_res = vol_analyzer.get_market_series_volatility(commodity=v_comm, market_id=v_mkt)
        if "error" not in v_res:
            vk1, vk2, vk3, vk4 = st.columns(4)
            vk1.metric("Overall Price CV", f"{v_res['overall_cv']:.4f}")
            vk2.metric("Mean Daily Price", f"₹{v_res['mean_price']:,.1f}/Qtl")
            vk3.metric("Daily Return AR(1)", f"{v_res['ar1_autocorr']:.4f}", help="Low autocorrelation indicates fast mean reversion in auctions.")
            vk4.metric("Severe Price Shocks (>25%)", f"{v_res['total_shocks_count']}")

            v_ts = v_res["df"]
            fig_vol = go.Figure()
            fig_vol.add_trace(go.Scatter(
                x=v_ts["date"], y=v_ts["rolling_cv"],
                mode="lines", name="30-Day Rolling CV",
                line=dict(color="#ec4899", width=2)
            ))
            fig_vol.update_layout(
                title=f"{v_comm} at {v_res['market_name']}: 30-Day Rolling Price Volatility",
                yaxis_title="Rolling CV (Std / Mean)",
                template="plotly_dark",
                paper_bgcolor="#111827", plot_bgcolor="#111827",
                height=350,
            )
            st.plotly_chart(fig_vol, use_container_width=True)

# ==============================================================================
# WORKSPACE 3: ARRIVAL-PRICE INVESTIGATION
# ==============================================================================
elif nav_choice == "3. Arrival–Price Panel Investigation":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Arrival–Price Panel Investigation: Econometric Demand Response</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Investigation C: Two-Way Fixed Effects Panel Regression with Cluster-Robust Standard Errors.</div>
        </div>
        <div class="mp-badge">INVESTIGATION C</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="callout-emerald">
        <b>Empirical Reality vs Folklore Claim:</b> An unverified claim previously asserted that <i>"a 10% drop in arrivals causes a 35-50% price surge"</i>.
        <br><b>The Data Proves Otherwise:</b> Estimating a rigorous Two-Way Fixed Effects panel model:
        <br><code>log(price<sub>it</sub>) = β · log(arrivals<sub>it</sub>) + α<sub>i</sub> (Market FE) + γ<sub>t</sub> (Month FE) + ε<sub>it</sub></code>
        <br>reveals that across <b>186,681 observations</b> for Onion, the elasticity is <b>β = -0.0471 (SE = 0.0206)</b>.
        A 10% drop in reported arrivals is associated with a modest <b>+0.50% price increase</b>. 
        Local daily arrival variation is smoothed by inter-mandi trade, storage drawdowns, and regional supply substitution.
    </div>
    """, unsafe_allow_html=True)

    col_e1, col_e2 = st.columns([1, 1])
    with col_e1:
        econ_comm = st.selectbox("Select Commodity for Econometric Panel", ["Onion", "Tomato", "Potato", "Green Chilli", "Banana", "Brinjal"], index=0)
    with col_e2:
        econ_scope = st.selectbox("Geographic Scope", ["All States (National Panel)", "Maharashtra", "Tamil Nadu", "Kerala"], index=0)

    state_arg = None if econ_scope == "All States (National Panel)" else econ_scope
    model_res = econ_engine.fit_panel_model(commodity=econ_comm, state=state_arg)

    if "error" not in model_res:
        ek1, ek2, ek3, ek4, ek5 = st.columns(5)
        ek1.metric("Sample Size (N)", f"{model_res['n_observations']:,}")
        ek2.metric("APMC Markets (G)", f"{model_res['n_markets']:,}")
        ek3.metric("Elasticity (β)", f"{model_res['twfe_elasticity_beta']:.4f}")
        ek4.metric("Cluster-Robust SE", f"{model_res['cluster_robust_se']:.4f}")
        ek5.metric("Price Response to -10% Arrivals", f"{model_res['price_response_minus_10pct_arrivals']:+.2f}%")

        # Econometric Specification Table
        st.markdown("### Econometric Model Specification & Diagnostics")
        spec_df = pd.DataFrame([
            {"Parameter / Metric": "Dependent Variable", "Value": "log(representative_price)"},
            {"Parameter / Metric": "Independent Variable", "Value": "log(arrivals_tonnes)"},
            {"Parameter / Metric": "Naive Pooled OLS Elasticity", "Value": f"{model_res['pooled_ols_beta']:.4f}"},
            {"Parameter / Metric": "Two-Way Fixed Effects Elasticity (β)", "Value": f"{model_res['twfe_elasticity_beta']:.4f}"},
            {"Parameter / Metric": "Cluster-Robust Standard Error", "Value": f"{model_res['cluster_robust_se']:.4f}"},
            {"Parameter / Metric": "t-statistic", "Value": f"{model_res['t_statistic']:.2f}"},
            {"Parameter / Metric": "p-value", "Value": f"{model_res['p_value_approx']}"},
            {"Parameter / Metric": "95% Confidence Interval", "Value": f"[{model_res['ci_95_lower']:.4f}, {model_res['ci_95_upper']:.4f}]"},
            {"Parameter / Metric": "Within R²", "Value": f"{model_res['within_r2']:.4f}"},
            {"Parameter / Metric": "Market Fixed Effects", "Value": f"Included ({model_res['n_markets']} markets absorbed)"},
            {"Parameter / Metric": "Time Fixed Effects", "Value": f"Included ({model_res['n_months']} months absorbed)"},
        ])
        st.dataframe(spec_df, use_container_width=True, hide_index=True)

        # Log-Log Scatter & Fitted Line Plot
        st.markdown("### Log-Log Scatter Plot & Fitted Slope")
        sample_df = model_res["sample_df"]
        fig_scatter = px.scatter(
            sample_df,
            x="x",
            y="y",
            color="canonical_market_name",
            labels={
                "x": "log(Arrivals in Tonnes)",
                "y": "log(Modal Price in ₹/Quintal)",
                "canonical_market_name": "Market",
            },
            title=f"{econ_comm}: Empirical Association between Log Arrivals and Log Prices (N={len(sample_df)} Sampled Points)",
            template="plotly_dark",
            opacity=0.6,
        )
        # Add fitted line
        x_vals = np.linspace(sample_df["x"].min(), sample_df["x"].max(), 100)
        y_vals = sample_df["y"].mean() + model_res["twfe_elasticity_beta"] * (x_vals - sample_df["x"].mean())
        fig_scatter.add_trace(go.Scatter(
            x=x_vals, y=y_vals,
            mode="lines",
            name=f"Fitted Slope (β = {model_res['twfe_elasticity_beta']:.4f})",
            line=dict(color="#f59e0b", width=3, dash="dash")
        ))
        fig_scatter.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", height=450)
        st.plotly_chart(fig_scatter, use_container_width=True)

        st.caption("Note: Results represent observational associations within markets over time, not structural consumer demand curves.")
    else:
        st.warning(model_res["error"])

# ==============================================================================
# WORKSPACE 4: DATA RELIABILITY LAB
# ==============================================================================
elif nav_choice == "4. Data Reliability Lab":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Data Reliability Lab: Mandi Reporting Forensics</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Investigation D: Transparent candidate anomaly detection, frozen price streaks, and reporting blackouts.</div>
        </div>
        <div class="mp-badge">INVESTIGATION D</div>
    </div>
    """, unsafe_allow_html=True)

    rel_tab1, rel_tab2, rel_tab3 = st.tabs([
        "Frozen Price Streaks Review Queue",
        "Reporting Blackouts & Hiatuses",
        "State Flat Quote Summary",
    ])

    with rel_tab1:
        st.markdown("### Frozen Price Streaks (Unchanged Price for Consecutive Days)")
        st.markdown("""
        <div class="callout-amber">
            <b>Reporting Quality Forensics:</b> Unchanged price quotes for extended periods do not automatically indicate fraudulent reporting.
            In <b>Telangana</b>, Paddy is frozen at exactly <b>₹2,320/quintal</b> for 373 days because mandis quote the statutory <b>MSP procurement floor</b>.
            In <b>Tamil Nadu Uzhavar Sandhai</b>, Banana is frozen for 518 days due to <b>administrative price ceiling boards</b>.
        </div>
        """, unsafe_allow_html=True)

        col_rf1, col_rf2 = st.columns(2)
        with col_rf1:
            streak_comm = st.selectbox("Filter Commodity", ["All Commodities"] + CORE_COMMODITIES, index=0)
        with col_rf2:
            min_days_filter = st.slider("Minimum Consecutive Frozen Days", min_value=7, max_value=60, value=14, step=7)

        comm_arg = None if streak_comm == "All Commodities" else streak_comm
        frozen_df = rel_auditor.get_frozen_price_streaks(min_streak_days=min_days_filter, commodity=comm_arg, limit=100)

        st.dataframe(
            frozen_df[[
                "state", "district", "canonical_market_name", "commodity", "frozen_price",
                "streak_start", "streak_end", "streak_days", "audit_priority", "plausible_explanation"
            ]].rename(columns={
                "state": "State",
                "district": "District",
                "canonical_market_name": "Market Name",
                "commodity": "Commodity",
                "frozen_price": "Frozen Price (₹/Qtl)",
                "streak_start": "Start Date",
                "streak_end": "End Date",
                "streak_days": "Frozen Days",
                "audit_priority": "Priority",
                "plausible_explanation": "Forensic Diagnostic / Plausible Explanation",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with rel_tab2:
        st.markdown("### Extended Reporting Blackouts (≥ 30-Day Gap Between Quotes)")
        blackout_df = rel_auditor.get_reporting_blackouts(min_gap_days=30, limit=100)
        st.dataframe(
            blackout_df.rename(columns={
                "state": "State",
                "canonical_market_name": "Market Name",
                "commodity": "Commodity",
                "blackout_start": "Last Report Before Gap",
                "blackout_end": "First Report After Gap",
                "blackout_days": "Blackout Duration (Days)",
                "diagnostic_category": "Diagnostic Category",
            }),
            use_container_width=True,
            hide_index=True,
        )

    with rel_tab3:
        st.markdown("### State Flat Quote Rate (Min Price == Max Price == Modal Price)")
        st.markdown("""
        When an APMC reports identical values for min, max, and modal price, it indicates either a single uniform lot,
        statutory pegging, or lack of reporting grade dispersion.
        """)
        flat_df = rel_auditor.get_state_flat_quote_summary()
        st.dataframe(
            flat_df.rename(columns={
                "state": "State",
                "total_records": "Total Records",
                "flat_quote_records": "Flat Quote Records",
                "flat_quote_pct": "Flat Quote Share (%)",
                "avg_price": "Average Modal Price (₹)",
                "total_markets": "APMC Mandis",
            }),
            use_container_width=True,
            hide_index=True,
        )

# ==============================================================================
# WORKSPACE 5: MARKET DECISION SIMULATOR
# ==============================================================================
elif nav_choice == "5. Market Decision Simulator":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Market Decision Simulator: Procurement & Spatial Logistics</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Hypothetical scenario tool comparing procurement costs, transport freight, transit loss, and delivered breakeven.</div>
        </div>
        <div class="mp-badge">DECISION SUPPORT SCENARIO</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="callout-rose">
        <b>MANDATORY DISCLAIMER:</b> This simulator models <b>hypothetical user-specified logistics scenarios</b>. 
        It does NOT represent guaranteed commercial profit, proven arbitrage, or live truck dispatching advice. 
        Actual freight rates, moisture shrinkage, loading charges, and terminal market clearance prices vary daily.
    </div>
    """, unsafe_allow_html=True)

    col_sim_l, col_sim_r = st.columns([1, 1])

    with col_sim_l:
        st.markdown("#### 1. Corridor & Physical Parameters")
        sim_corridor = st.selectbox(
            "Select Origin & Destination Corridor",
            [
                "Lasalgaon APMC (20-161) → Mumbai APMC (20-2703) [~225 km]",
                "Lasalgaon Niphad (20-2139) → Mumbai APMC (20-2703) [~215 km]",
                "Pimpalgaon Baswant (20-162) → Mumbai APMC (20-2703) [~195 km]",
                "Lasalgaon APMC (20-161) → Pune APMC (20-110) [~210 km]",
            ],
            index=0,
        )
        sim_comm = st.selectbox("Commodity", ["Onion", "Tomato", "Potato"], index=0)
        sim_qty_tonnes = st.slider("Procurement Volume (Metric Tonnes)", min_value=1.0, max_value=25.0, value=10.0, step=1.0)
        
        st.markdown("#### 2. Pricing Benchmarks")
        sim_p_purchase = st.number_input("Source Mandi Purchase Price (₹/Quintal)", min_value=500.0, max_value=10000.0, value=1950.0, step=50.0)
        sim_p_dest = st.number_input("Destination Reference Price (₹/Quintal)", min_value=500.0, max_value=10000.0, value=2250.0, step=50.0)

    with col_sim_r:
        st.markdown("#### 3. Transport & Operational Assumptions")
        sim_freight = st.number_input("Freight Rate (₹/Quintal)", min_value=20.0, max_value=500.0, value=120.0, step=10.0, help="Approx ₹1,200/Tonne for ~200 km.")
        sim_handling = st.number_input("Handling & Packaging (₹/Quintal)", min_value=10.0, max_value=150.0, value=35.0, step=5.0, help="Loading, unloading, gunny bags.")
        sim_cess = st.number_input("APMC Cess / Market Fee (%)", min_value=0.0, max_value=5.0, value=1.05, step=0.05, help="Standard Maharashtra APMC cess (1.05%).")
        sim_shrinkage = st.slider("Transit Shrinkage & Loss (%)", min_value=0.0, max_value=8.0, value=2.0, step=0.5, help="Moisture loss and transit damage.")

    # Run Simulation
    sim_res = DecisionSimulator.simulate_procurement_and_transit(
        source_market_name="Origin Mandi",
        dest_market_name="Destination Mandi",
        commodity=sim_comm,
        purchase_price_quintal=sim_p_purchase,
        dest_reference_price_quintal=sim_p_dest,
        quantity_tonnes=sim_qty_tonnes,
        freight_cost_per_quintal=sim_freight,
        handling_cost_per_quintal=sim_handling,
        mandi_cess_pct=sim_cess,
        transit_shrinkage_pct=sim_shrinkage,
    )

    costs = sim_res["costs"]
    delivered = sim_res["delivered"]

    st.markdown("---")
    st.markdown("### Scenario Economics & Breakeven Analysis")

    sk1, sk2, sk3, sk4, sk5 = st.columns(5)
    sk1.metric("Total Landed Outlay", f"₹{costs['total_landed_capital']:,.2f}")
    sk2.metric("Delivered Saleable Volume", f"{delivered['saleable_quantity_quintals']:,.1f} Qtl", delta=f"-{sim_qty_tonnes * 10 - delivered['saleable_quantity_quintals']:.1f} Qtl loss", delta_color="inverse")
    sk3.metric("Breakeven Cost", f"₹{delivered['breakeven_cost_per_quintal']:,.2f}/Qtl", help="Minimum destination sale price to avoid cash loss.")
    sk4.metric("Breakeven Cost per kg", f"₹{delivered['breakeven_cost_per_kg']:.2f}/kg")
    
    diff = delivered["hypothetical_net_differential"]
    sk5.metric(
        "Hypothetical Margin",
        f"₹{diff:+,.2f}",
        delta=f"{delivered['scenario_margin_pct']:+.1f}% Return on Outlay",
        delta_color="normal" if diff > 0 else "inverse",
    )

    # Cost Breakdown Waterfall
    waterfall_df = pd.DataFrame([
        {"Category": "Procurement", "Amount": costs["gross_procurement_cost"]},
        {"Category": "APMC Cess", "Amount": costs["mandi_cess_cost"]},
        {"Category": "Freight", "Amount": costs["total_freight_cost"]},
        {"Category": "Handling & Bags", "Amount": costs["total_handling_cost"]},
    ])
    fig_w = px.bar(
        waterfall_df,
        x="Category",
        y="Amount",
        color="Category",
        title="Capital Outlay Composition by Cost Category",
        template="plotly_dark",
        text_auto=",.0f",
    )
    fig_w.update_layout(paper_bgcolor="#111827", plot_bgcolor="#111827", height=320)
    st.plotly_chart(fig_w, use_container_width=True)

    # Sensitivity Matrix: Freight Rate vs Transit Loss
    st.markdown("### Sensitivity Matrix: Freight Rate vs Transit Loss")
    sens_df = sim_res.get("sensitivity_matrix")
    if sens_df is None or sens_df.empty:
        st.info("Sensitivity matrix unavailable for current scenario parameters.")
    else:
        pivot_sens = sens_df.pivot(index="freight_per_quintal", columns="shrinkage_pct", values="scenario_differential")
        pivot_be = sens_df.pivot(index="freight_per_quintal", columns="shrinkage_pct", values="breakeven_cost_quintal")

        x_labels = [f"{col:.1f}% Shrinkage" for col in pivot_sens.columns]
        y_labels = [f"₹{idx:.0f}/Qtl Freight" for idx in pivot_sens.index]
        z_vals = pivot_sens.values
        text_vals = [[f"₹{val:+,.0f}" for val in row] for row in z_vals]
        max_abs = max(abs(float(z_vals.min())), abs(float(z_vals.max())), 1.0)

        customdata = []
        for i, f_idx in enumerate(pivot_sens.index):
            row_data = []
            for j, s_col in enumerate(pivot_sens.columns):
                be_val = pivot_be.loc[f_idx, s_col]
                row_data.append([be_val, f"₹{be_val:,.2f}/Qtl", "Viable (+)" if z_vals[i][j] > 0 else "Loss (-)"])
            customdata.append(row_data)

        fig_heat = go.Figure(data=go.Heatmap(
            z=z_vals,
            x=x_labels,
            y=y_labels,
            text=text_vals,
            texttemplate="%{text}",
            textfont={"size": 13, "color": "#f8fafc", "family": "Inter, sans-serif"},
            colorscale="RdYlGn",
            zmid=0,
            zmin=-max_abs,
            zmax=max_abs,
            colorbar=dict(
                title=dict(text="Net Diff (₹)", font=dict(color="#94a3b8", size=12)),
                tickprefix="₹",
                tickfont=dict(color="#94a3b8"),
                len=0.9,
            ),
            customdata=customdata,
            hovertemplate=(
                "<b>Scenario Stress Point</b><br>"
                "Freight Rate: <b>%{y}</b><br>"
                "Transit Shrinkage: <b>%{x}</b><br>"
                "Delivered Breakeven: <b>%{customdata[1]}</b><br>"
                "Hypothetical Net Differential: <b>%{text}</b> (%{customdata[2]})"
                "<extra></extra>"
            ),
        ))
        fig_heat.update_layout(
            title=dict(
                text="Hypothetical Net Scenario Differential Across Freight & Transit Shrinkage Variations",
                font=dict(size=14, color="#e2e8f0"),
            ),
            xaxis=dict(title="Transit Shrinkage Loss (%)", tickfont=dict(color="#cbd5e1")),
            yaxis=dict(title="Freight Cost (₹/Quintal)", tickfont=dict(color="#cbd5e1")),
            template="plotly_dark",
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            height=340,
            margin=dict(l=50, r=40, t=50, b=50),
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        with st.expander("View Tabular Sensitivity Metrics", expanded=False):
            table_display = sens_df.copy()
            table_display["freight_per_quintal"] = table_display["freight_per_quintal"].map("₹{:,.1f}/Qtl".format)
            table_display["shrinkage_pct"] = table_display["shrinkage_pct"].map("{:.1f}%".format)
            table_display["breakeven_cost_quintal"] = table_display["breakeven_cost_quintal"].map("₹{:,.2f}".format)
            table_display["scenario_differential"] = table_display["scenario_differential"].map("₹{:,.2f}".format)
            table_display["viability_status"] = table_display["is_viable"].map(lambda v: "✅ Economically Viable" if v else "❌ Deficit / Loss")
            table_display = table_display.rename(columns={
                "freight_per_quintal": "Freight Rate",
                "shrinkage_pct": "Transit Loss",
                "breakeven_cost_quintal": "Breakeven Cost",
                "scenario_differential": "Scenario Net Differential",
                "viability_status": "Status",
            })[["Freight Rate", "Transit Loss", "Breakeven Cost", "Scenario Net Differential", "Status"]]
            st.dataframe(table_display, use_container_width=True, hide_index=True)

# ==============================================================================
# WORKSPACE 6: RESEARCH BRIEF & EXPORT
# ==============================================================================
elif nav_choice == "6. Research Brief & Export":
    st.markdown("""
    <div class="mp-banner">
        <div>
            <div class="mp-banner-title">Executive Research Brief: Lasalgaon–Mumbai Corridor Investigation</div>
            <div style="color: #94a3b8; font-size: 0.85rem;">Peer-reviewed analytical summary of empirical findings, methodology, and limitations.</div>
        </div>
        <div class="mp-badge">RESEARCH MEMORANDUM</div>
    </div>
    """, unsafe_allow_html=True)

    brief_markdown = """
# EXECUTIVE RESEARCH BRIEF
**Project:** MarketPulse India — Agricultural Market & Supply Intelligence  
**Candidate:** Meet Pokal  
**Investigation Topic:** The Lasalgaon–Mumbai Onion Supply Corridor & National APMC Market Integration  
**Date:** October 2026  

---

### 1. Research Question
Do wholesale agricultural market prices in terminal metropolitan consuming centres (e.g., Mumbai APMC) reflect positive spatial transport spreads over primary rural production hubs (e.g., Lasalgaon APMC), and do daily shifts in reported arrivals drive major price swings?

### 2. Empirical Findings & Discoveries
1. **The Negative Spatial Spread Paradox:**
   Across 507 date-aligned trading days between Lasalgaon and Mumbai, reported Mumbai modal prices are **lower than Lasalgaon on 74.8% of days**, yielding a mean spread of **-₹157.76/quintal**.
2. **Variety Heterogeneity as the Explanatory Confounder:**
   Mumbai APMC classifies 100% of reported onion records as generic 'Other'. Lasalgaon segregates premium export-grade *Unhali* (-₹228 spread) and fresh *Red* onions (-₹210 spread). Comparing generic terminal market averages against premium rural farm-gate lots introduces extreme variety bias.
3. **Rejection of the Arrival-Price Inelasticity Myth:**
   A two-way fixed effects panel regression across 186,681 observations disproves the folklore claim that a 10% drop in arrivals triggers a 35–50% price surge. The true empirical elasticity is **β = -0.0471 (SE = 0.0206)**, yielding a modest **+0.50% price response** because inter-mandi trade smooths local supply shocks.
4. **Mandi Reporting Reliability:**
   Over 27,000 extended frozen price streaks exist in AGMARKNET, including 518 consecutive days in Tamil Nadu Uzhavar Sandhai (administrative price boards) and 373 days in Telangana Paddy (MSP procurement quotes).

### 3. Methodology & Econometric Design
- **Analytical Engine:** DuckDB zero-copy queries over 1.48M row AGMARKNET Parquet database.
- **Model Specification:** `log(price_it) = β · log(arrivals_it) + α_i (Market FE) + γ_t (Month FE) + ε_it`
- **Standard Errors:** Cameron-Miller cluster-robust standard errors clustered at the APMC market level.

### 4. Project Limitations
- **Lack of Intraday Auction Micro-Data:** AGMARKNET reports a single daily modal price; intraday bid-ask dispersions are unobservable.
- **Retail vs Wholesale Gap:** Terminal wholesale prices do not capture final consumer retail margins.
- **Freight Volatility:** Fuel price shocks and return-trip backhaul loads dynamically alter actual transport economics.
"""
    st.markdown(brief_markdown)

    st.download_button(
        label="📥 Download Complete Research Brief (Markdown)",
        data=brief_markdown.encode('utf-8'),
        file_name="MARKETPULSE_RESEARCH_BRIEF_OCT2026.md",
        mime="text/markdown",
    )
