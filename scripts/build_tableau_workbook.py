#!/usr/bin/env python3
"""
MarketPulse India - Tableau Workbook Generator (Stage 3B Schema Hardened)

Generates schema-compliant Tableau Public 18.1 workbooks:
  1. tableau/marketpulse_india.twb   (Editable XML workbook)
  2. tableau/marketpulse_india.twbx  (Packaged workbook with bundled Data/ extracts)

Strictly satisfies Tableau's XSD content models:
  - Worksheet table: (view, style, panes, mark-layout?, rows, cols, ...)
  - View: (datasources?, mapsources?, datasource-dependencies*, ..., aggregation)
  - Datasource-dependencies: column must have datatype, name, role, type
  - Worksheet: (..., table, simple-id)
  - Dashboard: (style, size?, datasources, datasource-dependencies*, zones, simple-id)
"""

import sys
import uuid
import zipfile
from pathlib import Path
import polars as pl
from tableauhyperapi import (
    CreateMode,
    HyperProcess,
    Connection,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed" / "tableau"
TABLEAU_DIR = BASE_DIR / "tableau"


def gen_uuid():
    return f"{{{str(uuid.uuid4()).upper()}}}"


def compile_hyper_extracts():
    """Compile CSV data products into native Tableau Hyper (.hyper) extracts."""
    datasets = [
        "market_monthly",
        "corridor_spread_daily",
        "arrival_elasticity_models",
        "frozen_price_streaks",
    ]
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        for ds in datasets:
            csv_path = PROCESSED_DATA_DIR / f"{ds}.csv"
            hyper_path = PROCESSED_DATA_DIR / f"{ds}.hyper"
            if hyper_path.exists():
                hyper_path.unlink()

            df = pl.read_csv(csv_path, n_rows=100)
            col_defs = []
            for col_name, dtype in zip(df.columns, df.dtypes):
                if dtype in (pl.Int8, pl.Int16, pl.Int32):
                    htype = SqlType.int()
                elif dtype == pl.Int64:
                    htype = SqlType.big_int()
                elif dtype in (pl.Float32, pl.Float64):
                    htype = SqlType.double()
                elif dtype == pl.Boolean:
                    htype = SqlType.bool()
                elif dtype == pl.Date:
                    htype = SqlType.date()
                else:
                    htype = SqlType.text()
                col_defs.append(TableDefinition.Column(col_name, htype))

            with Connection(
                endpoint=hyper.endpoint,
                database=str(hyper_path),
                create_mode=CreateMode.CREATE_AND_REPLACE,
            ) as conn:
                conn.catalog.create_schema("Extract")
                tdef = TableDefinition(
                    table_name=TableName("Extract", "Extract"), columns=col_defs
                )
                conn.catalog.create_table(tdef)
                abs_csv = str(csv_path.resolve()).replace("\\", "/")
                count = conn.execute_command(
                    f'COPY "Extract"."Extract" FROM \'{abs_csv}\' WITH (FORMAT CSV, HEADER TRUE)'
                )
                print(f"   [HYPER] Compiled {ds}.hyper ({count:,} records)")


def build_extract_xml(dataset_name: str, is_packaged: bool) -> list[str]:
    dbname = (
        f"Data/{dataset_name}.hyper"
        if is_packaged
        else f"../data/processed/tableau/{dataset_name}.hyper"
    )
    csv_path = PROCESSED_DATA_DIR / f"{dataset_name}.csv"
    df = pl.read_csv(csv_path, n_rows=1)

    lines = [
        "      <extract count='-1' enabled='true' object-id='' units='records' user-specific='false'>",
        f"        <connection access_mode='readonly' author-locale='en_US' class='hyper' dbname='{dbname}' default-settings='hyper' schema='Extract' sslmode='' tablename='Extract' update-time='10/25/2026 11:00:00 AM' username='tableau_internal_user'>",
        "          <relation name='Extract' table='[Extract].[Extract]' type='table' />",
        "          <cols>",
    ]
    for col in df.columns:
        lines.append(f"            <map key='[{col}]' value='[Extract].[{col}]' />")
    lines.extend([
        "          </cols>",
        "        </connection>",
        "      </extract>",
    ])
    return lines

def create_workbook_xml(is_packaged: bool = False) -> str:
    """Generate schema-perfect Tableau Public XML workbook."""
    data_dir_rel = "Data" if is_packaged else "../data/processed/tableau"

    xml = [
        "<?xml version='1.0' encoding='utf-8' ?>",
        "<!-- build 20262.26.0912.1023 -->",
        "<workbook original-version='18.1' source-build='2026.2.3 (20262.26.0912.1023)' source-platform='win' version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>",
        "  <document-format-change-manifest>",
        "    <AccessibleZoneTabOrder />",
        "    <AnimationOnByDefault />",
        "    <IntuitiveSorting />",
        "    <MarkAnimation />",
        "    <ObjectModelEncapsulateLegacy />",
        "    <ObjectModelExtractV2 />",
        "    <ObjectModelTableType />",
        "    <SchemaViewerObjectModel />",
        "    <SheetIdentifierTracking />",
        "    <VConnDownstreamExtractsWithWarnings />",
        "    <WindowsPersistSimpleIdentifiers />",
        "  </document-format-change-manifest>",
        "  <preferences>",
        "    <preference name='ui.encoding.shelf.height' value='24' />",
        "    <preference name='ui.shelf.height' value='26' />",
        "  </preferences>",
        "  <datasources>",
    ]

    # --------------------------------------------------------------------------
    # Datasource 1: Market Monthly
    # --------------------------------------------------------------------------
    xml.extend([
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
        "      </connection>",
        "      <aliases enabled='yes' />",
        "      <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "      <column caption='APMC Mandi' datatype='string' name='[canonical_market_name]' role='dimension' type='nominal' />",
        "      <column caption='Month Start Date' datatype='date' name='[month_start_date]' role='dimension' type='ordinal' />",
        "      <column caption='Mean Modal Price (₹/Qtl)' datatype='real' name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='Median Modal Price (₹/Qtl)' datatype='real' name='[median_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='P25 Price (₹/Qtl)' datatype='real' name='[p25_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='P75 Price (₹/Qtl)' datatype='real' name='[p75_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "      <column caption='Total Arrivals (MT)' datatype='real' name='[total_arrivals_tonnes]' role='measure' type='quantitative' />",
        "      <column caption='Observed Records Count' datatype='integer' name='[observed_records_count]' role='measure' type='quantitative' />",
    ] + build_extract_xml("market_monthly", is_packaged) + [
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 2: Corridor Spread Daily
    # --------------------------------------------------------------------------
    xml.extend([
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
        "      <column caption='Spread Percentage (%)' datatype='real' name='[spread_pct]' role='measure' type='quantitative' />",
        "      <column caption='Origin Modal Price (₹/Qtl)' datatype='real' name='[source_price]' role='measure' type='quantitative' />",
        "      <column caption='Destination Modal Price (₹/Qtl)' datatype='real' name='[dest_price]' role='measure' type='quantitative' />",
        "      <column caption='Variety Comparability Status' datatype='string' name='[variety_comparability_status]' role='dimension' type='nominal' />",
        "      <column caption='Apparent Inversion Flag' datatype='boolean' name='[apparent_inversion_flag]' role='dimension' type='nominal' />",
    ] + build_extract_xml("corridor_spread_daily", is_packaged) + [
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 3: Arrival Elasticity Models
    # --------------------------------------------------------------------------
    xml.extend([
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
        "      <column caption='95% CI Lower Bound' datatype='real' name='[ci_95_lower]' role='measure' type='quantitative' />",
        "      <column caption='95% CI Upper Bound' datatype='real' name='[ci_95_upper]' role='measure' type='quantitative' />",
        "      <column caption='Cluster-Robust SE' datatype='real' name='[cluster_robust_se]' role='measure' type='quantitative' />",
        "      <column caption='Price Impact for -10% Arrivals (%)' datatype='real' name='[price_response_pct_for_minus_10pct_arrivals]' role='measure' type='quantitative' />",
        "      <column caption='Sample Size (N)' datatype='integer' name='[n_observations]' role='measure' type='quantitative' />",
        "      <column caption='Market Clusters (G)' datatype='integer' name='[n_market_clusters]' role='measure' type='quantitative' />",
        "      <column caption='Within R²' datatype='real' name='[within_r2]' role='measure' type='quantitative' />",
    ] + build_extract_xml("arrival_elasticity_models", is_packaged) + [
        "    </datasource>",
    ])

    # --------------------------------------------------------------------------
    # Datasource 4: Frozen Price Streaks & Reliability Forensics
    # --------------------------------------------------------------------------
    xml.extend([
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
        "      <column caption='Streak Duration (Days)' datatype='integer' name='[streak_days]' role='measure' type='quantitative' />",
        "      <column caption='Plausible Explanation' datatype='string' name='[plausible_explanation]' role='dimension' type='nominal' />",
        "      <column caption='Audit Review Priority' datatype='string' name='[audit_priority]' role='dimension' type='nominal' />",
        "      <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "      <column caption='APMC Mandi' datatype='string' name='[canonical_market_name]' role='dimension' type='nominal' />",
        "      <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      <column caption='Frozen Price (₹/Qtl)' datatype='real' name='[frozen_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
    ] + build_extract_xml("frozen_price_streaks", is_packaged) + [
        "    </datasource>",
    ])

    xml.append("  </datasources>")

    # --------------------------------------------------------------------------
    # Worksheets Definition (Fully Schema-Compliant)
    # Content Model: (((layout-options?)|(repository-location?)),table,simple-id)
    # Table Content Model: (view,style,panes,mark-layout?,rows,cols,...)
    # View Content Model: (datasources?,mapsources?,datasource-dependencies*,filter?,sort?,perspectives?,rows?,columns?,slices?,aggregation)
    # --------------------------------------------------------------------------
    xml.extend([
        "  <worksheets>",
        # Worksheet 1: Price Trends
        "    <worksheet name='w_price_trends'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Market Monthly Intelligence' name='ds_market_monthly' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_market_monthly'>",
        "            <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "            <column-instance column='[commodity]' derivation='None' name='[none:commodity:nk]' pivot='key' type='nominal' />",
        "            <column caption='Month Start Date' datatype='date' name='[month_start_date]' role='dimension' type='ordinal' />",
        "            <column-instance column='[month_start_date]' derivation='None' name='[none:month_start_date:qk]' pivot='key' type='quantitative' />",
        "            <column caption='Mean Modal Price (₹/Qtl)' datatype='real' name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "            <column-instance column='[mean_daily_modal_price_rs_per_quintal]' derivation='Avg' name='[avg:mean_daily_modal_price_rs_per_quintal:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Line' />",
        "            <encodings>",
        "              <color column='[ds_market_monthly].[none:commodity:nk]' />",
        "            </encodings>",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_market_monthly].[avg:mean_daily_modal_price_rs_per_quintal:qk]</rows>",
        "        <cols>[ds_market_monthly].[none:month_start_date:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 2: State Comparison
        "    <worksheet name='w_state_comparison'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Market Monthly Intelligence' name='ds_market_monthly' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_market_monthly'>",
        "            <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "            <column-instance column='[state]' derivation='None' name='[none:state:nk]' pivot='key' type='nominal' />",
        "            <column caption='Mean Modal Price (₹/Qtl)' datatype='real' name='[mean_daily_modal_price_rs_per_quintal]' role='measure' type='quantitative' />",
        "            <column-instance column='[mean_daily_modal_price_rs_per_quintal]' derivation='Avg' name='[avg:mean_daily_modal_price_rs_per_quintal:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_market_monthly].[none:state:nk]</rows>",
        "        <cols>[ds_market_monthly].[avg:mean_daily_modal_price_rs_per_quintal:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 3: Corridor Spread Timeline
        "    <worksheet name='w_corridor_spread_timeline'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Corridor Spread Daily' name='ds_corridor_spread' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_corridor_spread'>",
        "            <column caption='Observation Date' datatype='date' name='[date]' role='dimension' type='ordinal' />",
        "            <column-instance column='[date]' derivation='None' name='[none:date:qk]' pivot='key' type='quantitative' />",
        "            <column caption='Price Spread (₹/Qtl)' datatype='real' name='[price_spread_quintal]' role='measure' type='quantitative' />",
        "            <column-instance column='[price_spread_quintal]' derivation='Avg' name='[avg:price_spread_quintal:qk]' pivot='key' type='quantitative' />",
        "            <column caption='Variety Comparability Status' datatype='string' name='[variety_comparability_status]' role='dimension' type='nominal' />",
        "            <column-instance column='[variety_comparability_status]' derivation='None' name='[none:variety_comparability_status:nk]' pivot='key' type='nominal' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Line' />",
        "            <encodings>",
        "              <color column='[ds_corridor_spread].[none:variety_comparability_status:nk]' />",
        "            </encodings>",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_corridor_spread].[avg:price_spread_quintal:qk]</rows>",
        "        <cols>[ds_corridor_spread].[none:date:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 4: Corridor Spread Distribution
        "    <worksheet name='w_corridor_spread_hist'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Corridor Spread Daily' name='ds_corridor_spread' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_corridor_spread'>",
        "            <column caption='Corridor Name' datatype='string' name='[corridor_name]' role='dimension' type='nominal' />",
        "            <column-instance column='[corridor_name]' derivation='None' name='[none:corridor_name:nk]' pivot='key' type='nominal' />",
        "            <column caption='Price Spread (₹/Qtl)' datatype='real' name='[price_spread_quintal]' role='measure' type='quantitative' />",
        "            <column-instance column='[price_spread_quintal]' derivation='Avg' name='[avg:price_spread_quintal:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_corridor_spread].[none:corridor_name:nk]</rows>",
        "        <cols>[ds_corridor_spread].[avg:price_spread_quintal:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 5: Elasticity Forest Plot
        "    <worksheet name='w_elasticity_forest_plot'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Arrival Elasticity Models' name='ds_elasticity_models' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_elasticity_models'>",
        "            <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "            <column-instance column='[commodity]' derivation='None' name='[none:commodity:nk]' pivot='key' type='nominal' />",
        "            <column caption='Estimated Elasticity (β)' datatype='real' name='[estimated_elasticity_beta]' role='measure' type='quantitative' />",
        "            <column-instance column='[estimated_elasticity_beta]' derivation='Avg' name='[avg:estimated_elasticity_beta:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Circle' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_elasticity_models].[none:commodity:nk]</rows>",
        "        <cols>[ds_elasticity_models].[avg:estimated_elasticity_beta:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 6: Elasticity Shock Response
        "    <worksheet name='w_elasticity_shock_response'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Arrival Elasticity Models' name='ds_elasticity_models' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_elasticity_models'>",
        "            <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "            <column-instance column='[commodity]' derivation='None' name='[none:commodity:nk]' pivot='key' type='nominal' />",
        "            <column caption='Price Impact for -10% Arrivals (%)' datatype='real' name='[price_response_pct_for_minus_10pct_arrivals]' role='measure' type='quantitative' />",
        "            <column-instance column='[price_response_pct_for_minus_10pct_arrivals]' derivation='Avg' name='[avg:price_response_pct_for_minus_10pct_arrivals:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_elasticity_models].[none:commodity:nk]</rows>",
        "        <cols>[ds_elasticity_models].[avg:price_response_pct_for_minus_10pct_arrivals:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 7: Frozen Streak Duration Distribution
        "    <worksheet name='w_frozen_streak_distribution'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Frozen Price Streaks' name='ds_frozen_streaks' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_frozen_streaks'>",
        "            <column caption='Audit Review Priority' datatype='string' name='[audit_priority]' role='dimension' type='nominal' />",
        "            <column-instance column='[audit_priority]' derivation='None' name='[none:audit_priority:nk]' pivot='key' type='nominal' />",
        "            <column caption='Streak Duration (Days)' datatype='integer' name='[streak_days]' role='measure' type='quantitative' />",
        "            <column-instance column='[streak_days]' derivation='Sum' name='[sum:streak_days:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_frozen_streaks].[none:audit_priority:nk]</rows>",
        "        <cols>[ds_frozen_streaks].[sum:streak_days:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",

        # Worksheet 8: Frozen Explanations
        "    <worksheet name='w_frozen_explanation_pie'>",
        "      <table>",
        "        <view>",
        "          <datasources>",
        "            <datasource caption='Frozen Price Streaks' name='ds_frozen_streaks' />",
        "          </datasources>",
        "          <datasource-dependencies datasource='ds_frozen_streaks'>",
        "            <column caption='Plausible Explanation' datatype='string' name='[plausible_explanation]' role='dimension' type='nominal' />",
        "            <column-instance column='[plausible_explanation]' derivation='None' name='[none:plausible_explanation:nk]' pivot='key' type='nominal' />",
        "            <column caption='Streak Duration (Days)' datatype='integer' name='[streak_days]' role='measure' type='quantitative' />",
        "            <column-instance column='[streak_days]' derivation='Sum' name='[sum:streak_days:qk]' pivot='key' type='quantitative' />",
        "          </datasource-dependencies>",
        "          <aggregation value='true' />",
        "        </view>",
        "        <style />",
        "        <panes>",
        "          <pane selection-relaxation-option='selection-relaxation-allow'>",
        "            <view><breakdown value='auto' /></view>",
        "            <mark class='Bar' />",
        "          </pane>",
        "        </panes>",
        "        <rows>[ds_frozen_streaks].[none:plausible_explanation:nk]</rows>",
        "        <cols>[ds_frozen_streaks].[sum:streak_days:qk]</cols>",
        "      </table>",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </worksheet>",
        "  </worksheets>",
    ])

    # --------------------------------------------------------------------------
    # Dashboards Definition (Fully Schema-Compliant)
    # Content Model: (style, size?, datasources, datasource-dependencies*, zones, simple-id)
    # --------------------------------------------------------------------------
    xml.extend([
        "  <dashboards>",
        # Dashboard 1: Market Pulse
        "    <dashboard name='Dashboard 1 - Market Pulse'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <datasources>",
        "        <datasource caption='Market Monthly Intelligence' name='ds_market_monthly' />",
        "      </datasources>",
        "      <datasource-dependencies datasource='ds_market_monthly'>",
        "        <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "        <column caption='State' datatype='string' name='[state]' role='dimension' type='nominal' />",
        "      </datasource-dependencies>",
        "      <zones>",
        "        <zone h='100000' id='1' type-v2='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='2' param='vert' type-v2='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='3' type-v2='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 1. Monthly Mandi Intelligence</run>",
        "                <run fontcolor='#64748b' fontsize='10'>&#10;Wholesale price trends and inter-mandi price dispersion across 6 Indian states (Aug 2024 – Sep 2026 snapshot). Units: ₹/Quintal.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='4' param='horz' type-v2='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='5' name='w_price_trends' w='60000' x='1000' y='12000' />",
        "              <zone h='86000' id='6' name='w_state_comparison' w='38000' x='61000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
                f"      <simple-id uuid='{gen_uuid()}' />",
        "    </dashboard>",

        # Dashboard 2: Spread Lab
        "    <dashboard name='Dashboard 2 - Spread Lab'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <datasources>",
        "        <datasource caption='Corridor Spread Daily' name='ds_corridor_spread' />",
        "      </datasources>",
        "      <datasource-dependencies datasource='ds_corridor_spread'>",
        "        <column caption='Corridor Name' datatype='string' name='[corridor_name]' role='dimension' type='nominal' />",
        "      </datasource-dependencies>",
        "      <zones>",
        "        <zone h='100000' id='11' type-v2='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='12' param='vert' type-v2='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='13' type-v2='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 2. Spatial Arbitrage &amp; Variety Confounding</run>",
        "                <run fontcolor='#64748b' fontsize='10'>&#10;Lasalgaon vs Mumbai Onion spread inversion case study: Mumbai lower on 74.75% of 507 matched days (mean -₹157.76/Qtl) due to cultivar reporting heterogeneity.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='14' param='horz' type-v2='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='15' name='w_corridor_spread_timeline' w='65000' x='1000' y='12000' />",
        "              <zone h='86000' id='16' name='w_corridor_spread_hist' w='33000' x='66000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
                f"      <simple-id uuid='{gen_uuid()}' />",
        "    </dashboard>",

        # Dashboard 3: Arrival-Price Research
        "    <dashboard name='Dashboard 3 - Arrival-Price Research'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <datasources>",
        "        <datasource caption='Arrival Elasticity Models' name='ds_elasticity_models' />",
        "      </datasources>",
        "      <datasource-dependencies datasource='ds_elasticity_models'>",
        "        <column caption='Commodity' datatype='string' name='[commodity]' role='dimension' type='nominal' />",
        "      </datasource-dependencies>",
        "      <zones>",
        "        <zone h='100000' id='21' type-v2='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='22' param='vert' type-v2='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='23' type-v2='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 3. Econometric Elasticity Panel (TWFE)</run>",
        "                <run fontcolor='#64748b' fontsize='10'>&#10;Two-Way Fixed Effects panel regression with Cameron-Miller cluster-robust standard errors. Onion β = -0.0360 (95% CI [-0.072, -0.0001]); refutes 35-50% price surge folklore.</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='24' param='horz' type-v2='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='25' name='w_elasticity_forest_plot' w='55000' x='1000' y='12000' />",
        "              <zone h='86000' id='26' name='w_elasticity_shock_response' w='43000' x='56000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
                f"      <simple-id uuid='{gen_uuid()}' />",
        "    </dashboard>",

        # Dashboard 4: Reliability Forensics
        "    <dashboard name='Dashboard 4 - Reliability Forensics'>",
        "      <style />",
        "      <size maxheight='850' maxwidth='1300' minheight='850' minwidth='1300' sizing-mode='fixed' />",
        "      <datasources>",
        "        <datasource caption='Frozen Price Streaks' name='ds_frozen_streaks' />",
        "      </datasources>",
        "      <datasource-dependencies datasource='ds_frozen_streaks'>",
        "        <column caption='Audit Review Priority' datatype='string' name='[audit_priority]' role='dimension' type='nominal' />",
        "      </datasource-dependencies>",
        "      <zones>",
        "        <zone h='100000' id='31' type-v2='layout-basic' w='100000' x='0' y='0'>",
        "          <zone h='98000' id='32' param='vert' type-v2='layout-flow' w='98000' x='1000' y='1000'>",
        "            <zone h='10000' id='33' type-v2='title' w='98000' x='1000' y='1000'>",
        "              <formatted-text>",
        "                <run bold='true' fontcolor='#0f172a' fontsize='16'>MARKETPULSE INDIA | 4. Mandi Reliability &amp; Quality Assurance</run>",
        "                <run fontcolor='#64748b' fontsize='10'>&#10;Forensic audit of 27,420 frozen price streaks (≥7 days). MSP statutory quotes vs administrative ceilings vs stale reporting. 100% row conservation (1,481,250 valid + 70 scale errors + 4 zero arrivals).</run>",
        "              </formatted-text>",
        "            </zone>",
        "            <zone h='86000' id='34' param='horz' type-v2='layout-flow' w='98000' x='1000' y='12000'>",
        "              <zone h='86000' id='35' name='w_frozen_streak_distribution' w='50000' x='1000' y='12000' />",
        "              <zone h='86000' id='36' name='w_frozen_explanation_pie' w='48000' x='51000' y='12000' />",
        "            </zone>",
        "          </zone>",
        "        </zone>",
        "      </zones>",
                f"      <simple-id uuid='{gen_uuid()}' />",
        "    </dashboard>",
        "  </dashboards>",
    ])

    # --------------------------------------------------------------------------
    # Windows & Layout Navigation
    # Every worksheet must have a visual representation (<window class="worksheet">)
    # and dashboards must declare their active viewpoints.
    # --------------------------------------------------------------------------
    xml.append("  <windows>")

    worksheets = [
        "w_price_trends",
        "w_state_comparison",
        "w_corridor_spread_timeline",
        "w_corridor_spread_hist",
        "w_elasticity_forest_plot",
        "w_elasticity_shock_response",
        "w_frozen_streak_distribution",
        "w_frozen_explanation_pie",
    ]
    for ws_name in worksheets:
        xml.extend([
            f"    <window class='worksheet' name='{ws_name}'>",
            "      <cards>",
            "        <edge name='left'>",
            "          <strip size='160'>",
            "            <card type='pages' />",
            "            <card type='filters' />",
            "            <card type='marks' />",
            "          </strip>",
            "        </edge>",
            "        <edge name='top'>",
            "          <strip size='2147483647'>",
            "            <card type='columns' />",
            "          </strip>",
            "          <strip size='2147483647'>",
            "            <card type='rows' />",
            "          </strip>",
            "          <strip size='2147483647'>",
            "            <card type='title' />",
            "          </strip>",
            "        </edge>",
            "      </cards>",
            f"      <simple-id uuid='{gen_uuid()}' />",
            "    </window>",
        ])

    xml.extend([
        "    <window class='dashboard' maximized='true' name='Dashboard 1 - Market Pulse'>",
        "      <viewpoints>",
        "        <viewpoint name='w_price_trends' />",
        "        <viewpoint name='w_state_comparison' />",
        "      </viewpoints>",
        "      <active id='-1' />",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 2 - Spread Lab'>",
        "      <viewpoints>",
        "        <viewpoint name='w_corridor_spread_timeline' />",
        "        <viewpoint name='w_corridor_spread_hist' />",
        "      </viewpoints>",
        "      <active id='-1' />",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 3 - Arrival-Price Research'>",
        "      <viewpoints>",
        "        <viewpoint name='w_elasticity_forest_plot' />",
        "        <viewpoint name='w_elasticity_shock_response' />",
        "      </viewpoints>",
        "      <active id='-1' />",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </window>",
        "    <window class='dashboard' name='Dashboard 4 - Reliability Forensics'>",
        "      <viewpoints>",
        "        <viewpoint name='w_frozen_streak_distribution' />",
        "        <viewpoint name='w_frozen_explanation_pie' />",
        "      </viewpoints>",
        "      <active id='-1' />",
        f"      <simple-id uuid='{gen_uuid()}' />",
        "    </window>",
        "  </windows>",
        "</workbook>",
    ])

    return "\n".join(xml)


def build_workbooks():
    """Build .twb and .twbx packaged workbook."""
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    twb_path = TABLEAU_DIR / "marketpulse_india.twb"
    twbx_path = TABLEAU_DIR / "marketpulse_india.twbx"

    print("=" * 70)
    print("MarketPulse India - Building Schema-Hardened Tableau Workbooks")
    print("=" * 70)

    # 0. Compile native Hyper extracts
    print("0. Compiling native Tableau Hyper extracts...")
    compile_hyper_extracts()

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
        zf.writestr("marketpulse_india.twb", twbx_xml_content)

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

        hyper_files = [
            "market_monthly.hyper",
            "corridor_spread_daily.hyper",
            "arrival_elasticity_models.hyper",
            "frozen_price_streaks.hyper",
        ]
        for hyper_name in hyper_files:
            src_hyper = PROCESSED_DATA_DIR / hyper_name
            if src_hyper.exists():
                zf.write(src_hyper, arcname=f"Data/{hyper_name}")
                print(f"   + Bundled Data/{hyper_name} ({src_hyper.stat().st_size:,} bytes)")

    print(f"   [PASS] Saved {twbx_path.name} ({twbx_path.stat().st_size:,} bytes)")
    print("=" * 70)


if __name__ == "__main__":
    build_workbooks()
