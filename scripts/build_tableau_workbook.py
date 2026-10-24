#!/usr/bin/env python3
"""
MarketPulse India - Tableau Workbook Generator (Stage 3B)

Generates:
  1. tableau/marketpulse_india.twb   (Editable Tableau XML workbook)
  2. tableau/marketpulse_india.twbx  (Self-contained packaged workbook with bundled data)

Dashboards Built:
  - Dashboard 1: Market Pulse (Monthly Mandi Intelligence)
  - Dashboard 2: Spread Lab (Spatial Price Disparities & Variety Confounding)
  - Dashboard 3: Arrival-Price Research (Econometric Elasticity & TWFE Panel)
  - Dashboard 4: Reliability Forensics (Reporting Behavior & Data Assurance)
"""

import os
import sys
import zipfile
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET
from xml.dom import minidom

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed" / "tableau"
TABLEAU_DIR = BASE_DIR / "tableau"


def create_workbook_xml(is_packaged: bool = False) -> str:
    """Generate professional, fully structured Tableau Public XML workbook."""
    
    # Path prefix for data sources
    # In .twbx, data files are located in Data/ relative to the workbook
    # In .twb, data files are located in ../data/processed/tableau/
    data_dir_rel = "Data" if is_packaged else "../data/processed/tableau"

    xml_lines = [
        "<?xml version='1.0' encoding='utf-8' ?>",
        "<workbook original-version='18.1' source-build='2026.2.26.0912.1023' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>",
        "  <document-format-change-manifest>",
        "    <AccessibleZoneTabOrder />",
        "    <IntuitiveSorting />",
        "    <MapboxVectorStylesAndLayers />",
        "    <SheetIdentifierTracking />",
        "    <WindowsPersistSimpleIdentifiers />",
        "  </document-format-change-manifest>",
        "  <preferences>",
        "    <color-palette name='MarketPulse Divergent' type='ordered-diverging'>",
        "      <color>#e11d48</color>",  # Crimson / Negative Spread
        "      <color>#fca5a5</color>",
        "      <color>#e2e8f0</color>",  # Neutral Zero
        "      <color>#6ee7b7</color>",
        "      <color>#059669</color>",  # Emerald / Positive Spread
        "    </color-palette>",
        "    <color-palette name='MarketPulse Slate' type='regular'>",
        "      <color>#0f172a</color>",
        "      <color>#0284c7</color>",
        "      <color>#0d9488</color>",
        "      <color>#f59e0b</color>",
        "      <color>#e11d48</color>",
        "    </color-palette>",
        "  </preferences>",
        "  <datasources>",
    ]

    # --------------------------------------------------------------------------
    # Datasource 1: Market Monthly
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "    <datasource caption='Market Monthly Intelligence' inline='true' name='ds_market_monthly' version='18.1'>",
        "      <connection class='federated'>",
        "        <named-connections>",
        "          <named-connection caption='market_monthly' name='conn_market_monthly'>",
        f"            <connection class='textscan' directory='{data_dir_rel}' filename='market_monthly.csv' />",
        "          </named-connection>",
        "        </named-connections>",
        "        <relation connection='conn_market_monthly' name='market_monthly.csv' table='[market_monthly#csv]' type='table'>",
        "          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>",
        "            <column datatype='string' name='year_month' ordinal='0' />",
        "            <column datatype='date' name='month_start_date' ordinal='1' />",
        "            <column datatype='integer' name='state_id' ordinal='2' />",
        "            <column datatype='string' name='state' ordinal='3' />",
        "            <column datatype='string' name='district' ordinal='4' />",
        "            <column datatype='string' name='market_id' ordinal='5' />",
        "            <column datatype='string' name='canonical_market_name' ordinal='6' />",
        "            <column datatype='string' name='commodity' ordinal='7' />",
        "            <column datatype='integer' name='observed_records_count' ordinal='8' />",
        "            <column datatype='integer' name='valid_price_records_count' ordinal='9' />",
        "            <column datatype='real' name='mean_daily_modal_price_rs_per_quintal' ordinal='10' />",
        "            <column datatype='real' name='median_daily_modal_price_rs_per_quintal' ordinal='11' />",
        "            <column datatype='real' name='min_daily_modal_price_rs_per_quintal' ordinal='12' />",
        "            <column datatype='real' name='max_daily_modal_price_rs_per_quintal' ordinal='13' />",
        "            <column datatype='real' name='p25_daily_modal_price_rs_per_quintal' ordinal='14' />",
        "            <column datatype='real' name='p75_daily_modal_price_rs_per_quintal' ordinal='15' />",
        "            <column datatype='real' name='std_daily_modal_price_rs_per_quintal' ordinal='16' />",
        "            <column datatype='real' name='total_arrivals_tonnes' ordinal='17' />",
        "            <column datatype='real' name='mean_daily_arrivals_tonnes' ordinal='18' />",
        "            <column datatype='integer' name='positive_arrival_records_count' ordinal='19' />",
        "            <column datatype='integer' name='flat_quote_records_count' ordinal='20' />",
        "            <column datatype='integer' name='statistical_anomalies_count' ordinal='21' />",
        "            <column datatype='integer' name='scale_error_records_count' ordinal='22' />",
        "            <column datatype='integer' name='zero_arrival_records_count' ordinal='23' />",
        "            <column datatype='string' name='dominant_raw_variety' ordinal='24' />",
        "            <column datatype='string' name='dominant_variety_tier' ordinal='25' />",
        "          </columns>",
        "        </relation>",
        "        <metadata-records>",
        "          <metadata-record class='column'>",
        "            <remote-name>commodity</remote-name>",
        "            <remote-type>129</remote-type>",
        "            <local-name>[commodity]</local-name>",
        "            <parent-name>[market_monthly.csv]</parent-name>",
        "            <remote-alias>commodity</remote-alias>",
        "            <ordinal>7</ordinal>",
        "            <local-type>string</local-type>",
        "            <aggregation>Count</aggregation>",
        "            <contains-null>true</contains-null>",
        "          </metadata-record>",
        "          <metadata-record class='column'>",
        "            <remote-name>mean_daily_modal_price_rs_per_quintal</remote-name>",
        "            <remote-type>5</remote-type>",
        "            <local-name>[mean_daily_modal_price_rs_per_quintal]</local-name>",
        "            <parent-name>[market_monthly.csv]</parent-name>",
        "            <remote-alias>mean_daily_modal_price_rs_per_quintal</remote-alias>",
        "            <ordinal>10</ordinal>",
        "            <local-type>real</local-type>",
        "            <aggregation>Avg</aggregation>",
        "            <contains-null>true</contains-null>",
        "          </metadata-record>",
        "        </metadata-records>",
        "      </connection>",
        "      <aliases enabled='yes' />",
        "      <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "      <column caption='APMC Mandi' datatype='string' name='[canonical_market_name]' role='dimension' type='nominal' />",
        "      <column caption='Month Start' datatype='date' name='[month_start_date]' role='dimension' type='ordinal' />",
        "      <column caption='Mean Modal Price (₹/Qtl)' datatype='real' name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='Median Price (₹/Qtl)' datatype='real' name='[median_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='IQR 25th Pct (₹/Qtl)' datatype='real' name='[p25_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='IQR 75th Pct (₹/Qtl)' datatype='real' name='[p75_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='Total Arrivals (MT)' datatype='real' name='[total_arrivals_tonnes]' role='measure' type='quantitative' />",
        "      <column caption='Observed Records' datatype='integer' name='[observed_records_count]' role='measure' type='quantitative' />",
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 2: Corridor Spread Daily
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "    <datasource caption='Corridor Spread Daily' inline='true' name='ds_corridor_spread' version='18.1'>",
        "      <connection class='federated'>",
        "        <named-connections>",
        "          <named-connection caption='corridor_spread_daily' name='conn_corridor_spread'>",
        f"            <connection class='textscan' directory='{data_dir_rel}' filename='corridor_spread_daily.csv' />",
        "          </named-connection>",
        "        </named-connections>",
        "        <relation connection='conn_corridor_spread' name='corridor_spread_daily.csv' table='[corridor_spread_daily#csv]' type='table'>",
        "          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>",
        "            <column datatype='string' name='corridor_id' ordinal='0' />",
        "            <column datatype='string' name='corridor_name' ordinal='1' />",
        "            <column datatype='string' name='commodity' ordinal='2' />",
        "            <column datatype='string' name='corridor_narrative' ordinal='3' />",
        "            <column datatype='date' name='date' ordinal='4' />",
        "            <column datatype='string' name='source_market_name' ordinal='5' />",
        "            <column datatype='string' name='source_raw_name' ordinal='6' />",
        "            <column datatype='string' name='source_raw_variety' ordinal='7' />",
        "            <column datatype='string' name='source_std_variety' ordinal='8' />",
        "            <column datatype='string' name='source_variety_tier' ordinal='9' />",
        "            <column datatype='real' name='source_price' ordinal='10' />",
        "            <column datatype='real' name='source_arrivals' ordinal='11' />",
        "            <column datatype='string' name='dest_market_name' ordinal='12' />",
        "            <column datatype='string' name='dest_raw_name' ordinal='13' />",
        "            <column datatype='string' name='dest_raw_variety' ordinal='14' />",
        "            <column datatype='string' name='dest_std_variety' ordinal='15' />",
        "            <column datatype='string' name='dest_variety_tier' ordinal='16' />",
        "            <column datatype='real' name='dest_price' ordinal='17' />",
        "            <column datatype='real' name='dest_arrivals' ordinal='18' />",
        "            <column datatype='real' name='price_spread_quintal' ordinal='19' />",
        "            <column datatype='real' name='price_spread_kg' ordinal='20' />",
        "            <column datatype='real' name='spread_pct' ordinal='21' />",
        "            <column datatype='string' name='variety_comparability_status' ordinal='22' />",
        "            <column datatype='boolean' name='is_spread_negative' ordinal='23' />",
        "            <column datatype='boolean' name='apparent_inversion_flag' ordinal='24' />",
        "          </columns>",
        "        </relation>",
        "      </connection>",
        "      <aliases enabled='yes' />",
        "      <column caption='Corridor Name' datatype='string' name='[corridor_name]' role='dimension' type='nominal' />",
        "      <column caption='Observation Date' datatype='date' name='[date]' role='dimension' type='ordinal' />",
        "      <column caption='Price Spread (₹/Qtl)' datatype='real' name='[price_spread_quintal]' role='measure' type='quantitative' />",
        "      <column caption='Spread Pct (%)' datatype='real' name='[spread_pct]' role='measure' type='quantitative' />",
        "      <column caption='Origin Price (₹/Qtl)' datatype='real' name='[source_price]' role='measure' type='quantitative' />",
        "      <column caption='Destination Price (₹/Qtl)' datatype='real' name='[dest_price]' role='measure' type='quantitative' />",
        "      <column caption='Variety Comparability' datatype='string' name='[variety_comparability_status]' role='dimension' type='nominal' />",
        "      <column caption='Apparent Inversion' datatype='boolean' name='[apparent_inversion_flag]' role='dimension' type='nominal' />",
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 3: Arrival Elasticity Models
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "    <datasource caption='Arrival Elasticity Models' inline='true' name='ds_elasticity_models' version='18.1'>",
        "      <connection class='federated'>",
        "        <named-connections>",
        "          <named-connection caption='arrival_elasticity_models' name='conn_elasticity_models'>",
        f"            <connection class='textscan' directory='{data_dir_rel}' filename='arrival_elasticity_models.csv' />",
        "          </named-connection>",
        "        </named-connections>",
        "        <relation connection='conn_elasticity_models' name='arrival_elasticity_models.csv' table='[arrival_elasticity_models#csv]' type='table'>",
        "          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>",
        "            <column datatype='string' name='commodity' ordinal='0' />",
        "            <column datatype='string' name='model_id' ordinal='1' />",
        "            <column datatype='string' name='specification' ordinal='2' />",
        "            <column datatype='string' name='dependent_var' ordinal='3' />",
        "            <column datatype='string' name='explanatory_var' ordinal='4' />",
        "            <column datatype='string' name='fixed_effects' ordinal='5' />",
        "            <column datatype='string' name='standard_error_method' ordinal='6' />",
        "            <column datatype='string' name='state_scope' ordinal='7' />",
        "            <column datatype='integer' name='n_observations' ordinal='8' />",
        "            <column datatype='integer' name='n_market_clusters' ordinal='9' />",
        "            <column datatype='integer' name='n_calendar_months' ordinal='10' />",
        "            <column datatype='string' name='min_date' ordinal='11' />",
        "            <column datatype='string' name='max_date' ordinal='12' />",
        "            <column datatype='real' name='pooled_ols_beta' ordinal='13' />",
        "            <column datatype='real' name='estimated_elasticity_beta' ordinal='14' />",
        "            <column datatype='real' name='cluster_robust_se' ordinal='15' />",
        "            <column datatype='real' name='t_statistic' ordinal='16' />",
        "            <column datatype='string' name='p_value_approx' ordinal='17' />",
        "            <column datatype='real' name='ci_95_lower' ordinal='18' />",
        "            <column datatype='real' name='ci_95_upper' ordinal='19' />",
        "            <column datatype='real' name='within_r2' ordinal='20' />",
        "            <column datatype='real' name='price_response_pct_for_plus_10pct_arrivals' ordinal='21' />",
        "            <column datatype='real' name='price_response_pct_for_minus_10pct_arrivals' ordinal='22' />",
        "            <column datatype='real' name='price_response_pct_for_minus_25pct_arrivals' ordinal='23' />",
        "            <column datatype='string' name='economic_interpretation' ordinal='24' />",
        "            <column datatype='string' name='causal_disclaimer' ordinal='25' />",
        "          </columns>",
        "        </relation>",
        "      </connection>",
        "      <aliases enabled='yes' />",
        "      <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      <column caption='Estimated Elasticity (β)' datatype='real' name='[estimated_elasticity_beta]' role='measure' type='quantitative' />",
        "      <column caption='95% CI Lower' datatype='real' name='[ci_95_lower]' role='measure' type='quantitative' />",
        "      <column caption='95% CI Upper' datatype='real' name='[ci_95_upper]' role='measure' type='quantitative' />",
        "      <column caption='Cluster-Robust SE' datatype='real' name='[cluster_robust_se]' role='measure' type='quantitative' />",
        "      <column caption='Price Impact (-10% Arrivals)' datatype='real' name='[price_response_pct_for_minus_10pct_arrivals]' role='measure' type='quantitative' />",
        "      <column caption='Observations (N)' datatype='integer' name='[n_observations]' role='measure' type='quantitative' />",
        "      <column caption='Market Clusters (G)' datatype='integer' name='[n_market_clusters]' role='measure' type='quantitative' />",
        "      <column caption='Within R²' datatype='real' name='[within_r2]' role='measure' type='quantitative' />",
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 4: Frozen Price Streaks & Reliability Forensics
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "    <datasource caption='Frozen Price Streaks' inline='true' name='ds_frozen_streaks' version='18.1'>",
        "      <connection class='federated'>",
        "        <named-connections>",
        "          <named-connection caption='frozen_price_streaks' name='conn_frozen_streaks'>",
        f"            <connection class='textscan' directory='{data_dir_rel}' filename='frozen_price_streaks.csv' />",
        "          </named-connection>",
        "        </named-connections>",
        "        <relation connection='conn_frozen_streaks' name='frozen_price_streaks.csv' table='[frozen_price_streaks#csv]' type='table'>",
        "          <columns character-set='UTF-8' header='yes' locale='en_US' separator=','>",
        "            <column datatype='integer' name='streak_id' ordinal='0' />",
        "            <column datatype='string' name='state' ordinal='1' />",
        "            <column datatype='string' name='district' ordinal='2' />",
        "            <column datatype='string' name='market_id' ordinal='3' />",
        "            <column datatype='string' name='canonical_market_name' ordinal='4' />",
        "            <column datatype='string' name='commodity' ordinal='5' />",
        "            <column datatype='real' name='frozen_modal_price_rs_per_quintal' ordinal='6' />",
        "            <column datatype='date' name='streak_start_date' ordinal='7' />",
        "            <column datatype='date' name='streak_end_date' ordinal='8' />",
        "            <column datatype='integer' name='streak_days' ordinal='9' />",
        "            <column datatype='integer' name='calendar_span_days' ordinal='10' />",
        "            <column datatype='string' name='plausible_explanation' ordinal='11' />",
        "            <column datatype='string' name='audit_priority' ordinal='12' />",
        "            <column datatype='boolean' name='is_msp_statutory_quote' ordinal='13' />",
        "          </columns>",
        "        </relation>",
        "      </connection>",
        "      <aliases enabled='yes' />",
        "      <column caption='Streak Days' datatype='integer' name='[streak_days]' role='measure' type='quantitative' />",
        "      <column caption='Plausible Explanation' datatype='string' name='[plausible_explanation]' role='dimension' type='nominal' />",
        "      <column caption='Audit Priority' datatype='string' name='[audit_priority]' role='dimension' type='nominal' />",
        "      <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "      <column caption='Mandi' datatype='string' name='[canonical_market_name]' role='dimension' type='nominal' />",
        "      <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      <column caption='Frozen Price (₹/Qtl)' datatype='real' name='[frozen_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "    </datasource>",
    ])

    xml_lines.append("  </datasources>")

    # --------------------------------------------------------------------------
    # Worksheets Definition
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "  <worksheets>",
        "    <worksheet name='w_price_trends'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_market_monthly' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_market_monthly'>",
        "            <column name='[commodity]' role='dimension' type='nominal' />",
        "            <column name='[month_start_date]' role='dimension' type='ordinal' />",
        "            <column name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Line' />",
        "            <encodings>",
        "              <color column='[ds_market_monthly].[commodity]' />",
        "            </encodings>",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_market_monthly].[mean_daily_modal_price_rs_per_quintal]</rows>",
        "        <cols>[ds_market_monthly].[month_start_date]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_state_comparison'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_market_monthly' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_market_monthly'>",
        "            <column name='[state]' role='dimension' type='nominal' />",
        "            <column name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_market_monthly].[state]</rows>",
        "        <cols>[ds_market_monthly].[mean_daily_modal_price_rs_per_quintal]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_corridor_spread_timeline'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_corridor_spread' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_corridor_spread'>",
        "            <column name='[date]' role='dimension' type='ordinal' />",
        "            <column name='[price_spread_quintal]' role='measure' type='quantitative' />",
        "            <column name='[variety_comparability_status]' role='dimension' type='nominal' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Line' />",
        "            <encodings>",
        "              <color column='[ds_corridor_spread].[variety_comparability_status]' />",
        "            </encodings>",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_corridor_spread].[price_spread_quintal]</rows>",
        "        <cols>[ds_corridor_spread].[date]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_corridor_spread_hist'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_corridor_spread' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_corridor_spread'>",
        "            <column name='[corridor_name]' role='dimension' type='nominal' />",
        "            <column name='[price_spread_quintal]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_corridor_spread].[corridor_name]</rows>",
        "        <cols>[ds_corridor_spread].[price_spread_quintal]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_elasticity_forest_plot'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_elasticity_models' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_elasticity_models'>",
        "            <column name='[commodity]' role='dimension' type='nominal' />",
        "            <column name='[estimated_elasticity_beta]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Circle' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_elasticity_models].[commodity]</rows>",
        "        <cols>[ds_elasticity_models].[estimated_elasticity_beta]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_elasticity_shock_response'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_elasticity_models' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_elasticity_models'>",
        "            <column name='[commodity]' role='dimension' type='nominal' />",
        "            <column name='[price_response_pct_for_minus_10pct_arrivals]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_elasticity_models].[commodity]</rows>",
        "        <cols>[ds_elasticity_models].[price_response_pct_for_minus_10pct_arrivals]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_frozen_streak_distribution'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_frozen_streaks' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_frozen_streaks'>",
        "            <column name='[audit_priority]' role='dimension' type='nominal' />",
        "            <column name='[streak_days]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_frozen_streaks].[audit_priority]</rows>",
        "        <cols>[ds_frozen_streaks].[streak_days]</cols>",
        "      </table>",
        "    </worksheet>",

        "    <worksheet name='w_frozen_explanation_pie'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource name='ds_frozen_streaks' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_frozen_streaks'>",
        "            <column name='[plausible_explanation]' role='dimension' type='nominal' />",
        "            <column name='[streak_days]' role='measure' type='quantitative' />",
        "          </datasource-dependencies>",
        "        </view>",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_frozen_streaks].[plausible_explanation]</rows>",
        "        <cols>[ds_frozen_streaks].[streak_days]</cols>",
        "      </table>",
        "    </worksheet>",
        "  </worksheets>",
    ])

    # --------------------------------------------------------------------------
    # Dashboards Definition (4 Full Dashboards)
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "  <dashboards>",
        # Dashboard 1: Market Pulse
        "    <dashboard name='Dashboard 1 - Market Pulse'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <zones>",
        "        <zone h='100000' id='1' type='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='2' param='vert' type='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='3' type='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 1. Monthly Mandi Intelligence</run>",
        "                <run fontcolor='#64748b' fontsize='10'>\nWholesale price trends and inter-mandi price dispersion across 6 Indian states (Aug 2024 – Sep 2026 snapshot). Units: ₹/Quintal.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='4' param='horz' type='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='5' name='w_price_trends' w='60000' x='1000' y='12000' />",
        "              <zone h='86000' id='6' name='w_state_comparison' w='38000' x='61000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
        "    </dashboard>",

        # Dashboard 2: Spread Lab
        "    <dashboard name='Dashboard 2 - Spread Lab'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <zones>",
        "        <zone h='100000' id='11' type='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='12' param='vert' type='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='13' type='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 2. Spatial Arbitrage &amp; Variety Confounding</run>",
        "                <run fontcolor='#64748b' fontsize='10'>\nLasalgaon vs Mumbai Onion spread inversion case study: Mumbai lower on 74.75% of 507 matched days (mean -₹157.76/Qtl) due to cultivar reporting heterogeneity.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='14' param='horz' type='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='15' name='w_corridor_spread_timeline' w='65000' x='1000' y='12000' />",
        "              <zone h='86000' id='16' name='w_corridor_spread_hist' w='33000' x='66000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
        "    </dashboard>",

        # Dashboard 3: Arrival-Price Research
        "    <dashboard name='Dashboard 3 - Arrival-Price Research'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <zones>",
        "        <zone h='100000' id='21' type='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='22' param='vert' type='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='23' type='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 3. Econometric Elasticity Panel (TWFE)</run>",
        "                <run fontcolor='#64748b' fontsize='10'>\nTwo-Way Fixed Effects panel regression with Cameron-Miller cluster-robust standard errors. Onion β = -0.0360 (95% CI [-0.072, -0.0001]); refutes 35-50% price surge folklore.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='24' param='horz' type='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='25' name='w_elasticity_forest_plot' w='55000' x='1000' y='12000' />",
        "              <zone h='86000' id='26' name='w_elasticity_shock_response' w='43000' x='56000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
        "    </dashboard>",

        # Dashboard 4: Reliability Forensics
        "    <dashboard name='Dashboard 4 - Reliability Forensics'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <zones>",
        "        <zone h='100000' id='31' type='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='32' param='vert' type='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='33' type='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 4. Mandi Reliability &amp; Quality Assurance</run>",
        "                <run fontcolor='#64748b' fontsize='10'>\nForensic audit of 27,420 frozen price streaks (≥7 days). MSP statutory quotes vs administrative ceilings vs stale reporting. 100% row conservation (1,481,250 valid + 70 scale errors + 4 zero arrivals).</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='34' param='horz' type='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='35' name='w_frozen_streak_distribution' w='50000' x='1000' y='12000' />",
        "              <zone h='86000' id='36' name='w_frozen_explanation_pie' w='48000' x='51000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
        "    </dashboard>",
        "  </dashboards>",
    ])

    # --------------------------------------------------------------------------
    # Windows & Layout Navigation
    # --------------------------------------------------------------------------
    xml_lines.extend([
        "  <windows>",
        "    <window class='dashboard' maximized='true' name='Dashboard 1 - Market Pulse'>",
        "      <viewpoints />",
        "      <active id='-1' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 2 - Spread Lab'>",
        "      <viewpoints />",
        "      <active id='-1' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 3 - Arrival-Price Research'>",
        "      <viewpoints />",
        "      <active id='-1' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 4 - Reliability Forensics'>",
        "      <viewpoints />",
        "      <active id='-1' />",
        "    </window>",
        "  </windows>",
        "</workbook>",
    ])

    return "\n".join(xml_lines)


def build_workbooks():
    """Build .twb and .twbx packaged workbook."""
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    twb_path = TABLEAU_DIR / "marketpulse_india.twb"
    twbx_path = TABLEAU_DIR / "marketpulse_india.twbx"

    print("=" * 70)
    print("MarketPulse India - Building Tableau Public Workbook Artifacts")
    print("=" * 70)

    # 1. Generate standalone .twb (relative data path to ../data/processed/tableau/)
    print("1. Generating editable XML workbook: marketpulse_india.twb...")
    twb_content = create_workbook_xml(is_packaged=False)
    with open(twb_path, "w", encoding="utf-8") as f:
        f.write(twb_content)
    print(f"   [PASS] Saved {twb_path.name} ({twb_path.stat().st_size:,} bytes)")

    # 2. Generate packaged .twbx (bundles twb + Data/ CSV files into ZIP)
    print("2. Generating self-contained packaged workbook: marketpulse_india.twbx...")
    twbx_xml_content = create_workbook_xml(is_packaged=True)

    with zipfile.ZipFile(twbx_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        # Write internal .twb
        zf.writestr("marketpulse_india.twb", twbx_xml_content)

        # Bundle all 6 CSV data products into Data/
        csv_files = [
            "market_monthly.csv",
            "corridor_spread_daily.csv",
            "arrival_elasticity_models.csv",
            "frozen_price_streaks.csv",
            "quality_exceptions.csv",
            "quality_monthly_summary.csv",
        ]
        for csv_name in csv_files:
            src_csv = PROCESSED_DATA_DIR / csv_name
            if src_csv.exists():
                zf.write(src_csv, arcname=f"Data/{csv_name}")
                print(f"   + Bundled Data/{csv_name} ({src_csv.stat().st_size:,} bytes)")
            else:
                print(f"   [WARNING] Missing CSV: {src_csv}")

    print(f"   [PASS] Saved {twbx_path.name} ({twbx_path.stat().st_size:,} bytes)")
    print("=" * 70)


if __name__ == "__main__":
    build_workbooks()
