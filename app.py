import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests

# 頁面基本設定
st.set_page_config(
    page_title="亞太區宏觀經濟與消費力分析看板 | APAC Macro & Consumption Dashboard",
    page_icon="💎",
    layout="wide"
)

# 多語言字典
LANG = {
    "zh": {
        "title": "💎 亞太區宏觀經濟與消費潛力分析看板 (東南亞 + 中港日澳)",
        "intro": "本工具串接**世界銀行 (World Bank) 開放 API**，分析東南亞核心國家與亞太主要經濟體（中國、香港、日本、澳洲）的人口總量與人均 GDP 趨勢，為珠寶及高端消費品市場開發與戰略佈局提供數據支撐。",
        "sidebar_header": "設定與篩選條件",
        "lang_label": "選擇語言 / Language",
        "country_label": "選擇目標國家 / 區域",
        "all_countries": "全亞太區域 (共 10 國/地區)",
        "metric_pop": "最新總人口數",
        "metric_gdp": "最新人均 GDP",
        "chart_pop_title": "各國總人口數趨勢 (2018-2023)",
        "chart_gdp_title": "各國人均 GDP 比較 (USD)",
        "table_title": "檢視世界銀行原始數據表格",
        "source_title": "📌 數據來源與聲明 (Data Source & Attribution)",
        "source_desc": "本看板所使用之宏觀經濟與人口數據均直接擷取自官方公開 API。數據具備高度權威性與即時更新特性。",
        "source_link": "世界銀行開放數據平台 (World Bank Open Data)"
    },
    "en": {
        "title": "💎 APAC Macroeconomic & Consumption Potential Dashboard (SEA + CN, HK, JP, AU)",
        "intro": "This tool integrates the **World Bank Open API** to analyze population and GDP per capita trends across Southeast Asia and key APAC economies (China, Hong Kong, Japan, Australia), providing data-driven insights for jewelry and luxury market expansion.",
        "sidebar_header": "Settings & Filters",
        "lang_label": "Language / 選擇語言",
        "country_label": "Select Target Country / Region",
        "all_countries": "All APAC Region (10 Countries/Regions)",
        "metric_pop": "Latest Total Population",
        "metric_gdp": "Latest GDP per Capita",
        "chart_pop_title": "Total Population Trend (2018-2023)",
        "chart_gdp_title": "GDP per Capita Comparison (USD)",
        "table_title": "View World Bank Raw Dataset",
        "source_title": "📌 Data Source & Attribution",
        "source_desc": "All macroeconomic and demographic data displayed in this dashboard are retrieved directly from the official public API, ensuring high authority and regular updates.",
        "source_link": "World Bank Open Data Platform"
    }
}

# 側邊欄語言切換
lang_choice = st.sidebar.selectbox("Language / 語言", ["繁體中文", "English"])
current_lang = "zh" if lang_choice == "繁體中文" else "en"
t = LANG[current_lang]

st.title(t["title"])
st.markdown(t["intro"])
st.sidebar.markdown("---")
st.sidebar.header(t["sidebar_header"])

# 抓取世界銀行真實數據的函數
@st.cache_data(ttl=86400)
def fetch_world_bank_data():
    countries = {
        "Singapore": "SGP", "Thailand": "THA", "Vietnam": "VNM", 
        "Indonesia": "IDN", "Malaysia": "MYS", "Philippines": "PHL",
        "China": "CHN", "Hong Kong SAR": "HKG", "Japan": "JPN", "Australia": "AUS"
    }
    
    indicators = {
        "Population": "SP.POP.TOTL",
        "GDP_per_capita": "NY.GDP.PCAP.CD"
    }
    
    all_data = []
    
    for country_name, iso3 in countries.items():
        pop_url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicators['Population']}?format=json&date=2018:2023"
        gdp_url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicators['GDP_per_capita']}?format=json&date=2018:2023"
        
        try:
            pop_res = requests.get(pop_url ).json()
            gdp_res = requests.get(gdp_url).json()
            
            pop_dict = {}
            if len(pop_res) > 1 and pop_res[1]:
                for item in pop_res[1]:
                    if item['value'] is not None:
                        pop_dict[item['date']] = item['value']
            
            gdp_dict = {}
            if len(gdp_res) > 1 and gdp_res[1]:
                for item in gdp_res[1]:
                    if item['value'] is not None:
                        gdp_dict[item['date']] = item['value']
            
            for year in ["2018", "2019", "2020", "2021", "2022", "2023"]:
                if year in pop_dict:
                    all_data.append({
                        "Country": country_name,
                        "Year": int(year),
                        "Population": pop_dict.get(year, np.nan),
                        "GDP_per_Capita": gdp_dict.get(year, np.nan)
                    })
        except Exception as e:
            continue
            
    return pd.DataFrame(all_data)

# 載入數據
with st.spinner("正在載入 API 真實數據..."):
    df_wb = fetch_world_bank_data()

# 篩選與顯示邏輯
country_list = [t["all_countries"]] + list(df_wb["Country"].unique())
selected_country_ui = st.sidebar.selectbox(t["country_label"], country_list)

df_filtered = df_wb if selected_country_ui == t["all_countries"] else df_wb[df_wb["Country"] == selected_country_ui]

# 核心指標
st.subheader(f"📊 {selected_country_ui} - 概況")
col1, col2, col3 = st.columns(3)
latest_year = df_filtered["Year"].max()
df_latest = df_filtered[df_filtered["Year"] == latest_year]

col1.metric(t["metric_pop"], f"{df_latest['Population'].sum():,.0f}")
col2.metric(t["metric_gdp"], f"${df_latest['GDP_per_Capita'].mean():,.0f} USD")
col3.metric("覆蓋地區數", f"{df_filtered['Country'].nunique()}")

st.divider()

# 圖表
c1, c2 = st.columns(2)
with c1:
    st.subheader(t["chart_pop_title"])
    st.plotly_chart(px.line(df_filtered, x="Year", y="Population", color="Country", markers=True), use_container_width=True)
with c2:
    st.subheader(t["chart_gdp_title"])
    st.plotly_chart(px.bar(df_latest, x="Country", y="GDP_per_Capita", color="Country", text_auto=".2s"), use_container_width=True)

# 頁尾來源標註
st.markdown("---")
st.markdown(f"### {t['source_title']}\n- {t['source_desc']}\n- 🌐 數據來源：[World Bank Open Data](https://data.worldbank.org/ )")
