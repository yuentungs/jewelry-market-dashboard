from __future__ import annotations

from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st


st.set_page_config(
    page_title="APAC Jewellery Market Intelligence Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

COUNTRIES = {
    "Singapore": "SGP",
    "Thailand": "THA",
    "Vietnam": "VNM",
    "Indonesia": "IDN",
    "Malaysia": "MYS",
    "Philippines": "PHL",
    "China": "CHN",
    "Hong Kong SAR": "HKG",
    "Japan": "JPN",
    "Australia": "AUS",
}

INDICATORS = {
    "Population": "SP.POP.TOTL",
    "GDP per capita (USD)": "NY.GDP.PCAP.CD",
    "Household consumption (USD)": "NE.CON.PRVT.CD",
}
YEARS = list(range(2018, 2024))
DATA_DIR = Path(__file__).resolve().parent / "data"
BENCHMARK_PATH = DATA_DIR / "public_benchmarks.csv"
MACRO_SNAPSHOT_PATH = DATA_DIR / "macro_baseline_2018_2023.csv"

CHANNEL_COLUMNS = [
    "country", "year", "channel", "metric_type", "value", "unit", "scope",
    "source_name", "source_url", "notes",
]
CATEGORY_COLUMNS = [
    "country", "year", "channel", "category", "metric_type", "value", "unit",
    "scope", "source_name", "source_url", "notes",
]

st.markdown(
    """
    <style>
        .block-container {padding-top: 1.7rem; padding-bottom: 2.5rem;}
        [data-testid="stMetric"] {background: #f8fafc; border: 1px solid #e2e8f0; padding: 0.75rem; border-radius: 0.65rem;}
        .dashboard-note {border-left: 4px solid #0f766e; background: #f0fdfa; padding: 0.85rem 1rem; border-radius: 0.35rem; margin-bottom: 0.75rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def tx(zh: str, en: str) -> str:
    return zh if st.session_state.get("lang", "繁體中文") == "繁體中文" else en


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_indicator(iso3: str, indicator: str) -> dict[int, float]:
    url = (
        f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}"
        "?format=json&date=2018:2023&per_page=100"
    )
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    payload = response.json()
    if len(payload) < 2 or not payload[1]:
        return {}
    return {
        int(item["date"]): item["value"]
        for item in payload[1]
        if item.get("value") is not None and int(item["date"]) in YEARS
    }


@st.cache_data(ttl=86400, show_spinner=False)
def get_demand_data() -> pd.DataFrame:
    # 預設使用由世界銀行 API 驗證的版本化快照，避免前端一次提出 30 個請求而延遲載入。
    # 若快照不存在，才改以 API 逐國下載。
    if MACRO_SNAPSHOT_PATH.exists():
        df = pd.read_csv(MACRO_SNAPSHOT_PATH).rename(columns={
            "country": "Country",
            "iso3": "ISO3",
            "year": "Year",
            "population": "Population",
            "gdp_per_capita_usd": "GDP_per_capita_USD",
            "household_consumption_usd": "Household_consumption_USD",
        })
    else:
        records: list[dict] = []
        for country, iso3 in COUNTRIES.items():
            values = {label: fetch_indicator(iso3, code) for label, code in INDICATORS.items()}
            for year in YEARS:
                records.append(
                    {
                        "Country": country,
                        "ISO3": iso3,
                        "Year": year,
                        "Population": values["Population"].get(year, np.nan),
                        "GDP_per_capita_USD": values["GDP per capita (USD)"].get(year, np.nan),
                        "Household_consumption_USD": values["Household consumption (USD)"].get(year, np.nan),
                    }
                )
        df = pd.DataFrame(records)
    df["Consumption_per_capita_USD"] = df["Household_consumption_USD"] / df["Population"]
    return df.sort_values(["Country", "Year"])


@st.cache_data
def load_public_benchmarks(file_mtime: float) -> pd.DataFrame:
    if not BENCHMARK_PATH.exists():
        return pd.DataFrame()
    return pd.read_csv(BENCHMARK_PATH)


def get_public_benchmarks() -> pd.DataFrame:
    file_mtime = BENCHMARK_PATH.stat().st_mtime if BENCHMARK_PATH.exists() else 0.0
    return load_public_benchmarks(file_mtime)


def read_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(uploaded_file)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(uploaded_file)
    else:
        raise ValueError("只支援 CSV、XLSX 或 XLS 檔案。")
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def validate_data(df: pd.DataFrame, required_columns: list[str]) -> tuple[bool, list[str], pd.DataFrame]:
    missing = [column for column in required_columns if column not in df.columns]
    errors: list[str] = []
    if missing:
        errors.append("缺少欄位：" + ", ".join(missing))
        return False, errors, df
    clean = df.copy()
    clean["year"] = pd.to_numeric(clean["year"], errors="coerce")
    clean["value"] = pd.to_numeric(clean["value"], errors="coerce")
    if clean["year"].isna().any():
        errors.append("year 必須為完整年度數字。")
    if clean["value"].isna().any():
        errors.append("value 必須為數值。")
    if clean["source_url"].astype(str).str.strip().eq("").any():
        errors.append("每筆資料必須提供 source_url。")
    for column in required_columns:
        if column not in {"year", "value", "notes"} and clean[column].astype(str).str.strip().eq("").any():
            errors.append(f"{column} 不可留空。")
    return len(errors) == 0, errors, clean


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


def format_usd_m(value: float) -> str:
    if pd.isna(value):
        return "—"
    if abs(value) >= 1_000_000:
        return f"USD {value / 1_000_000:,.1f}T"
    if abs(value) >= 1_000:
        return f"USD {value / 1_000:,.1f}B"
    return f"USD {value:,.0f}M"


def render_data_quality_table(selected_countries: list[str], user_data: pd.DataFrame) -> None:
    public = get_public_benchmarks()
    all_data = pd.concat([public, user_data], ignore_index=True, sort=False)
    coverage_rows = []
    for country in selected_countries:
        country_rows = all_data[all_data["country"].eq(country)] if not all_data.empty else pd.DataFrame()
        coverage_rows.append(
            {
                tx("市場", "Market"): country,
                tx("需求承受力", "Demand capacity"): tx("已由世界銀行載入", "World Bank loaded"),
                tx("渠道規模", "Channel scale"): tx("已提供" if not country_rows.empty else "待上傳", "Available" if not country_rows.empty else "Upload needed"),
                tx("品類損益", "Category economics"): tx(
                    "已提供" if (not country_rows.empty and country_rows["layer"].eq("Category").any()) else "待上傳",
                    "Available" if (not country_rows.empty and country_rows["layer"].eq("Category").any()) else "Upload needed",
                ),
            }
        )
    st.dataframe(pd.DataFrame(coverage_rows), use_container_width=True, hide_index=True)


with st.sidebar:
    st.header("💎 Market Intelligence")
    st.selectbox("Language / 語言", ["繁體中文", "English"], key="lang")
    st.caption(tx("三層資料模型：需求承受力、渠道規模、品類損益。", "Three layers: demand capacity, channel scale, category economics."))
    st.divider()

    try:
        demand_data = get_demand_data()
        market_options = list(COUNTRIES.keys())
        selected_countries = st.multiselect(
            tx("選擇市場", "Select markets"),
            options=market_options,
            default=["Singapore", "Hong Kong SAR", "China", "Vietnam", "Indonesia"],
        )
        selected_year = st.selectbox(
            tx("宏觀資料年度", "Macro data year"),
            sorted(demand_data["Year"].dropna().unique(), reverse=True),
        )
    except Exception as exc:
        st.error(tx("世界銀行資料暫時無法載入。請重新整理後再試。", "World Bank data is temporarily unavailable. Please refresh and try again."))
        st.exception(exc)
        st.stop()

    st.divider()
    st.subheader(tx("補充資料上傳", "Upload supplementary data"))
    uploaded_channel = st.file_uploader(
        tx("渠道規模資料", "Channel-scale data"), type=["csv", "xlsx", "xls"], key="channel_upload"
    )
    uploaded_category = st.file_uploader(
        tx("品類損益資料", "Category-economics data"), type=["csv", "xlsx", "xls"], key="category_upload"
    )

if not selected_countries:
    st.warning(tx("請至少選擇一個市場。", "Select at least one market."))
    st.stop()

user_benchmarks: list[pd.DataFrame] = []
for uploaded, required, layer in [
    (uploaded_channel, CHANNEL_COLUMNS, "Channel"),
    (uploaded_category, CATEGORY_COLUMNS, "Category"),
]:
    if uploaded is None:
        continue
    try:
        uploaded_df = read_uploaded_file(uploaded)
        valid, messages, clean_df = validate_data(uploaded_df, required)
        if valid:
            clean_df["layer"] = layer
            user_benchmarks.append(clean_df)
            st.sidebar.success(tx(f"已載入 {uploaded.name}：{len(clean_df)} 筆資料。", f"Loaded {uploaded.name}: {len(clean_df)} records."))
        else:
            st.sidebar.error(tx(f"{uploaded.name} 未載入：" + "；".join(messages), f"{uploaded.name} was not loaded: " + "; ".join(messages)))
    except Exception as exc:
        st.sidebar.error(tx(f"無法讀取 {uploaded.name}：{exc}", f"Could not read {uploaded.name}: {exc}"))

user_data = pd.concat(user_benchmarks, ignore_index=True, sort=False) if user_benchmarks else pd.DataFrame()

latest = demand_data[demand_data["Year"].eq(selected_year) & demand_data["Country"].isin(selected_countries)].copy()
base = demand_data[demand_data["Year"].eq(2018)].set_index("Country")
latest["Population_growth_2018_2023_pct"] = latest.apply(
    lambda row: ((row["Population"] / base.loc[row["Country"], "Population"] - 1) * 100) if row["Country"] in base.index else np.nan,
    axis=1,
)
latest["GDP_pc_growth_2018_2023_pct"] = latest.apply(
    lambda row: ((row["GDP_per_capita_USD"] / base.loc[row["Country"], "GDP_per_capita_USD"] - 1) * 100) if row["Country"] in base.index else np.nan,
    axis=1,
)

st.title(tx("亞太珠寶市場決策看板", "APAC Jewellery Market Intelligence Dashboard"))
st.markdown(
    f"<div class='dashboard-note'><b>{tx('使用方式：', 'How to use:')}</b> {tx('先用需求承受力篩選市場，再以渠道與品類資料判斷產品和渠道策略。渠道 GMV、平台收入、零售銷售與品牌淨銷售會被分開展示，避免錯誤加總。', 'Start with demand capacity, then use channel and category data to decide product and route-to-market strategy. GMV, platform revenue, retail sales and brand net sales are intentionally kept separate.')}</div>",
    unsafe_allow_html=True,
)

tab_overview, tab_demand, tab_channel, tab_category, tab_governance = st.tabs([
    tx("市場優先級", "Market priority"),
    tx("需求承受力", "Demand capacity"),
    tx("渠道規模", "Channel scale"),
    tx("品類損益", "Category economics"),
    tx("資料管理", "Data governance"),
])

with tab_overview:
    st.subheader(tx("市場優先級：先看量體、購買力與升級速度", "Market priority: size, purchasing power and upgrading momentum"))
    metric_cols = st.columns(4)
    metric_cols[0].metric(tx("選定市場人口", "Population in selected markets"), f"{latest['Population'].sum() / 1_000_000:,.1f}M")
    metric_cols[1].metric(tx("人口加權人均 GDP", "Population-weighted GDP per capita"), f"USD {(latest['GDP_per_capita_USD'] * latest['Population']).sum() / latest['Population'].sum():,.0f}")
    metric_cols[2].metric(tx("平均人口成長", "Average population growth"), f"{latest['Population_growth_2018_2023_pct'].mean():.1f}%")
    metric_cols[3].metric(tx("平均人均 GDP 成長", "Average GDP-per-capita growth"), f"{latest['GDP_pc_growth_2018_2023_pct'].mean():.1f}%")

    chart_df = latest.copy()
    chart_df["Population_M"] = chart_df["Population"] / 1_000_000
    fig = px.scatter(
        chart_df,
        x="GDP_per_capita_USD",
        y="Consumption_per_capita_USD",
        size="Population_M",
        color="GDP_pc_growth_2018_2023_pct",
        hover_name="Country",
        hover_data={
            "Population_M": ":.1f",
            "GDP_per_capita_USD": ":,.0f",
            "Consumption_per_capita_USD": ":,.0f",
            "GDP_pc_growth_2018_2023_pct": ":.1f",
            "Population_growth_2018_2023_pct": ":.1f",
        },
        color_continuous_scale="Viridis",
        size_max=82,
        labels={
            "GDP_per_capita_USD": tx("人均 GDP（USD）", "GDP per capita (USD)"),
            "Consumption_per_capita_USD": tx("人均家庭消費（USD）", "Household consumption per capita (USD)"),
            "GDP_pc_growth_2018_2023_pct": tx("人均 GDP 成長 %", "GDP-per-capita growth %"),
        },
    )
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=25, b=0), coloraxis_colorbar_title=tx("2018–2023 年\n人均 GDP 成長", "2018–2023\nGDP per-capita growth"))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(tx("氣泡大小為人口；色彩代表 2018–2023 年人均 GDP 成長。家庭消費以家庭及服務非營利機構最終消費支出除以人口計算，不等同可支配收入。", "Bubble size is population and colour is GDP-per-capita growth from 2018 to 2023. Household consumption is final consumption expenditure divided by population; it is not disposable income."))

    decision = latest[["Country", "Population", "GDP_per_capita_USD", "Consumption_per_capita_USD", "Population_growth_2018_2023_pct", "GDP_pc_growth_2018_2023_pct"]].copy()
    def decision_lens(row: pd.Series) -> str:
        if row["GDP_per_capita_USD"] >= 35000:
            return tx("高消費力：品質、信任、服務與全渠道", "High purchasing power: quality, trust, service and omnichannel")
        if row["Population"] >= 80_000_000 and row["GDP_pc_growth_2018_2023_pct"] >= 15:
            return tx("量體與升級：入門—中價帶、內容與履約", "Scale and upgrading: entry-to-mid price, content and fulfillment")
        return tx("價值平衡：分城市、價格帶與節慶管理", "Balanced value: manage by city, price tier and seasonality")
    decision[tx("決策鏡頭", "Decision lens")] = decision.apply(decision_lens, axis=1)
    decision = decision.rename(columns={
        "Country": tx("市場", "Market"),
        "Population": tx("人口", "Population"),
        "GDP_per_capita_USD": tx("人均 GDP（USD）", "GDP per capita (USD)"),
        "Consumption_per_capita_USD": tx("人均家庭消費（USD）", "Household consumption per capita (USD)"),
        "Population_growth_2018_2023_pct": tx("人口成長 %", "Population growth %"),
        "GDP_pc_growth_2018_2023_pct": tx("人均 GDP 成長 %", "GDP-per-capita growth %"),
    })
    st.dataframe(
        decision.style.format({
            tx("人口", "Population"): "{:,.0f}",
            tx("人均 GDP（USD）", "GDP per capita (USD)"): "USD {:,.0f}",
            tx("人均家庭消費（USD）", "Household consumption per capita (USD)"): "USD {:,.0f}",
            tx("人口成長 %", "Population growth %"): "{:.1f}%",
            tx("人均 GDP 成長 %", "GDP-per-capita growth %"): "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

with tab_demand:
    st.subheader(tx("需求承受力：人口不是需求，消費能力才是", "Demand capacity: population is not demand; purchasing power matters"))
    st.markdown(tx("此頁將人口、現價美元人均 GDP 與家庭最終消費支出並列，協助避免只以大人口或平均 GDP 判斷市場優先級。", "This view aligns population, GDP per capita and household final consumption expenditure to avoid prioritising markets on population or average GDP alone."))
    trend_data = demand_data[demand_data["Country"].isin(selected_countries)].melt(
        id_vars=["Country", "Year"],
        value_vars=["Population", "GDP_per_capita_USD", "Consumption_per_capita_USD"],
        var_name="Metric",
        value_name="Value",
    )
    demand_metric = st.selectbox(
        tx("選擇趨勢指標", "Select trend metric"),
        options=["Population", "GDP_per_capita_USD", "Consumption_per_capita_USD"],
        format_func=lambda value: {
            "Population": tx("人口", "Population"),
            "GDP_per_capita_USD": tx("人均 GDP（USD）", "GDP per capita (USD)"),
            "Consumption_per_capita_USD": tx("人均家庭消費（USD）", "Household consumption per capita (USD)"),
        }[value],
        key="demand_metric",
    )
    trend = trend_data[trend_data["Metric"].eq(demand_metric)]
    trend_fig = px.line(trend, x="Year", y="Value", color="Country", markers=True)
    trend_fig.update_layout(height=450, margin=dict(l=0, r=0, t=20, b=0), legend_title_text="")
    st.plotly_chart(trend_fig, use_container_width=True)
    st.info(tx("資料來源：世界銀行公開 API。宏觀資料通常有發布時滯；本看板目前統一顯示至 2023 年。", "Source: World Bank Open API. Macro indicators have a publication lag; this dashboard currently presents data through 2023."))

with tab_channel:
    st.subheader(tx("渠道規模：GMV、零售銷售與收入不可混算", "Channel scale: GMV, retail sales and revenue must not be mixed"))
    public = get_public_benchmarks()
    all_benchmarks = pd.concat([public, user_data], ignore_index=True, sort=False)
    channel_data = all_benchmarks[all_benchmarks.get("layer", pd.Series(dtype=str)).eq("Channel")].copy() if not all_benchmarks.empty else pd.DataFrame()
    if channel_data.empty:
        st.warning(tx("尚未載入渠道資料。請在側邊欄上傳符合模板的渠道資料。", "No channel data is loaded. Upload a channel file matching the template from the sidebar."))
    else:
        display_channel = channel_data[channel_data["country"].isin(selected_countries + ["ASEAN-6"])].copy()
        if display_channel.empty:
            st.info(tx("公開基準不涵蓋目前選定市場；請上傳各市場的官方零售或平台資料。", "Public benchmarks do not cover the selected markets. Upload official retail or platform data for each market."))
        else:
            metric_options = display_channel["metric_type"].dropna().unique().tolist()
            channel_metric = st.selectbox(tx("渠道指標", "Channel metric"), metric_options, key="channel_metric")
            filtered_channel = display_channel[display_channel["metric_type"].eq(channel_metric)].copy()
            units = filtered_channel["unit"].dropna().unique().tolist()
            if len(units) > 1:
                chosen_unit = st.selectbox(tx("單位", "Unit"), units, key="channel_unit")
                filtered_channel = filtered_channel[filtered_channel["unit"].eq(chosen_unit)]
            channel_fig = px.bar(
                filtered_channel,
                x="country",
                y="value",
                color="channel",
                hover_data=["year", "unit", "scope", "source_name", "notes"],
                labels={"country": tx("市場／範圍", "Market / scope"), "value": channel_metric, "channel": tx("渠道", "Channel")},
                text_auto=".3s",
            )
            channel_fig.update_layout(height=420, margin=dict(l=0, r=0, t=20, b=0), legend_title_text="")
            st.plotly_chart(channel_fig, use_container_width=True)
            st.dataframe(
                filtered_channel[["country", "year", "channel", "metric_type", "value", "unit", "scope", "source_name", "source_url", "notes"]],
                use_container_width=True,
                hide_index=True,
            )
            st.caption(tx("比較前先檢查 scope 與 unit。區域匯總與單一國家、GMV 與平台收入、零售銷售與品牌淨銷售都不可直接相加。", "Check scope and unit before comparing. Regional aggregates vs. country figures, GMV vs. platform revenue, retail sales vs. brand net sales cannot be added together."))

with tab_category:
    st.subheader(tx("品類損益：以一致口徑回答「家品、服飾還是其他」", "Category economics: answer 'home, fashion or other' with a consistent basis"))
    public = get_public_benchmarks()
    all_benchmarks = pd.concat([public, user_data], ignore_index=True, sort=False)
    category_data = all_benchmarks[all_benchmarks.get("layer", pd.Series(dtype=str)).eq("Category")].copy() if not all_benchmarks.empty else pd.DataFrame()
    if category_data.empty:
        st.warning(tx("尚未載入品類資料。請上傳 GMV、品牌淨銷售、毛利、退貨率或購買滲透率，並標明品類及資料範圍。", "No category data is loaded. Upload GMV, brand net sales, gross margin, returns or purchase penetration with category and scope."))
    else:
        display_category = category_data[category_data["country"].isin(selected_countries)].copy()
        if display_category.empty:
            st.info(tx("選定市場目前沒有公開品類基準；請上傳內部或可追溯的外部資料。", "No public category benchmark is available for the selected markets. Upload internal or traceable external data."))
        else:
            category_metric = st.selectbox(tx("品類指標", "Category metric"), display_category["metric_type"].dropna().unique().tolist(), key="category_metric")
            category_filtered = display_category[display_category["metric_type"].eq(category_metric)].copy()
            units = category_filtered["unit"].dropna().unique().tolist()
            if len(units) > 1:
                category_unit = st.selectbox(tx("單位", "Unit"), units, key="category_unit")
                category_filtered = category_filtered[category_filtered["unit"].eq(category_unit)]
            category_fig = px.bar(
                category_filtered,
                x="category",
                y="value",
                color="country",
                barmode="group",
                hover_data=["year", "unit", "scope", "source_name", "notes"],
                labels={"category": tx("品類", "Category"), "value": category_metric, "country": tx("市場", "Market")},
                text_auto=".2s",
            )
            category_fig.update_layout(height=420, margin=dict(l=0, r=0, t=20, b=0), legend_title_text="")
            st.plotly_chart(category_fig, use_container_width=True)
            st.dataframe(
                category_filtered[["country", "year", "channel", "category", "metric_type", "value", "unit", "scope", "source_name", "source_url", "notes"]],
                use_container_width=True,
                hide_index=True,
            )
            st.warning(tx("請勿將「購買滲透率」解讀為收入份額。只有同年度、同市場、同渠道、同一貨幣與相同 metric_type 的資料，才可用於排名或加總。", "Do not interpret purchase penetration as a revenue share. Only records with the same year, market, channel, currency and metric type can be ranked or aggregated."))

with tab_governance:
    st.subheader(tx("資料管理：補足缺口，而不是以估算填補", "Data governance: close gaps rather than filling them with estimates"))
    st.markdown(tx("目前所有市場的需求承受力均由已驗證的世界銀行資料快照載入。渠道規模與品類損益只有具來源、範圍與口徑的資料才會顯示；無資料時應標為缺口。", "Demand capacity is loaded for every market from a verified World Bank data snapshot. Channel scale and category economics are displayed only when a source, scope and metric definition are supplied; missing data stays visibly missing."))
    render_data_quality_table(selected_countries, user_data)

    template_channel = pd.DataFrame(columns=CHANNEL_COLUMNS)
    template_category = pd.DataFrame(columns=CATEGORY_COLUMNS)
    col_a, col_b = st.columns(2)
    col_a.download_button(
        tx("下載渠道資料 CSV 模板", "Download channel CSV template"),
        dataframe_to_csv_bytes(template_channel),
        file_name="channel_metrics_template.csv",
        mime="text/csv",
        use_container_width=True,
    )
    col_b.download_button(
        tx("下載品類資料 CSV 模板", "Download category CSV template"),
        dataframe_to_csv_bytes(template_category),
        file_name="category_metrics_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.markdown(tx("### 必備資料規格", "### Required data rules"))
    rule_df = pd.DataFrame([
        {tx("規則", "Rule"): tx("不可混算", "Never mix"), tx("要求", "Requirement"): tx("零售銷售額、平台 GMV、平台收入、品牌淨銷售分欄處理。", "Retail sales, platform GMV, platform revenue and brand net sales must remain separate.")},
        {tx("規則", "Rule"): tx("可追溯", "Traceability"), tx("要求", "Requirement"): tx("每筆資料必須包含年度、單位、範圍、來源名稱及 URL。", "Every record must include year, unit, scope, source name and URL.")},
        {tx("規則", "Rule"): tx("可比性", "Comparability"), tx("要求", "Requirement"): tx("跨國加總前，統一幣別、期間、含稅與否、B2C／B2B、跨境／本地及品類映射。", "Before cross-market aggregation, align currency, period, tax basis, B2C/B2B, cross-border/local and category mapping.")},
        {tx("規則", "Rule"): tx("品牌盈利", "Brand profitability"), tx("要求", "Requirement"): tx("品類損益優先使用內部 ERP、POS 與平台後台，並加入毛利、退貨率、客單價和回購率。", "Use ERP, POS and platform back-end data for category economics, adding gross margin, returns, AOV and repeat purchase.")},
    ])
    st.dataframe(rule_df, use_container_width=True, hide_index=True)
    st.caption(tx("公開基準資料與上傳格式詳見專案中的 data/README.md。", "See data/README.md in the project for public benchmarks and upload schemas."))

st.divider()
st.caption(
    tx(
        "資料來源：世界銀行開放資料；Google、Temasek、Bain e-Conomy SEA；HKTDC Research；美國國際貿易署。公開基準的原始連結會逐列展示。",
        "Sources: World Bank Open Data; Google, Temasek and Bain e-Conomy SEA; HKTDC Research; International Trade Administration. Source links are shown on every public benchmark row.",
    )
)
