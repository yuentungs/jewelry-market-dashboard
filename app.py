import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# 頁面基本設定
st.set_page_config(
    page_title="東南亞珠寶市場與消費趨勢分析",
    page_icon="💎",
    layout="wide"
)

# 標題與簡介
st.title("💎 東南亞珠寶市場與消費趨勢分析看板")
st.markdown("""
這個 Web App 是專為珠寶業產品經理設計的市場分析工具，結合了 **Python (Pandas, Plotly)** 與 **Streamlit**，
展示如何將市場調研數據轉化為互動式視覺化儀表板，並部署於 GitHub 與 Streamlit Cloud。
""")

# 側邊欄控制項
st.sidebar.header("篩選條件")
selected_country = st.sidebar.selectbox(
    "選擇目標國家",
    ["全區域 (Southeast Asia)", "新加坡 (Singapore)", "泰國 (Thailand)", "越南 (Vietnam)", "印尼 (Indonesia)"]
)

year_range = st.sidebar.slider(
    "選擇年份範圍",
    2020, 2026, (2022, 2026)
)

# 模擬真實的珠寶市場數據
np.random.seed(42)
countries = ["新加坡", "泰國", "越南", "印尼"]
categories = ["輕奢銀飾", "天然寶石", "珍珠飾品", "黃金/投資型"]

data = []
for country in countries:
    for cat in categories:
        for year in range(2022, 2027):
            base_sales = np.random.randint(50, 150)
            growth_factor = 1.15 if country in ["新加坡", "越南"] else 1.08
            sales = int(base_sales * (growth_factor ** (year - 2022)))
            avg_price = np.random.randint(120, 450)
            data.append({
                "國家": country,
                "產品類別": cat,
                "年份": year,
                "銷售額 (萬美元)": sales,
                "平均客單價 (USD)": avg_price
            })

df = pd.DataFrame(data)

# 根據側邊欄進行篩選
if selected_country != "全區域 (Southeast Asia)":
    country_name = selected_country.split(" ")[0]
    df_filtered = df[(df["國家"] == country_name) & (df["年份"] >= year_range[0]) & (df["年份"] <= year_range[1])]
else:
    df_filtered = df[(df["年份"] >= year_range[0]) & (df["年份"] <= year_range[1])]

# 核心指標展示 (Metrics)
st.subheader(f"📊 核心指標摘要 ({selected_country})")
col1, col2, col3 = st.columns(3)

total_sales = df_filtered["銷售額 (萬美元)"].sum()
avg_unit_price = int(df_filtered["平均客單價 (USD)"].mean())
top_category = df_filtered.groupby("產品類別")["銷售額 (萬美元)"].sum().idxmax()

col1.metric("預估總銷售額", f"${total_sales:,} 萬 USD", "+12.4% YoY")
col2.metric("平均客單價", f"${avg_unit_price} USD", "+5.1% YoY")
col3.metric("最具潛力品類", top_category)

st.divider()

# 圖表區塊
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📈 各品類銷售額增長趨勢")
    fig_trend = px.line(
        df_filtered.groupby(["年份", "產品類別"], as_index=False)["銷售額 (萬美元)"].sum(),
        x="年份",
        y="銷售額 (萬美元)",
        color="產品類別",
        markers=True,
        title="年度銷售趨勢預測"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with col_right:
    st.subheader("🏆 各國家/品類市場佔比")
    fig_bar = px.bar(
        df_filtered,
        x="國家",
        y="銷售額 (萬美元)",
        color="產品類別",
        barmode="group",
        title="各國市場規模比較"
    )
    st.plotly_chart(fig_bar, use_container_width=True)

# 原始數據展開
with st.expander("查看原始詳細數據表格"):
    st.dataframe(df_filtered, use_container_width=True)

# 頁尾說明
st.markdown("---")
st.markdown("💡 *Created by Senior Product Manager & Python Developer | Hosted on Streamlit Cloud & GitHub*")
