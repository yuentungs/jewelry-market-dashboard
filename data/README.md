# 儀表板資料管理規格

本資料夾把市場資訊分為三個不可混用的層次：

| 層次 | 目的 | 首選來源 | 關鍵口徑 |
|---|---|---|---|
| 需求承受力 | 衡量人口、購買力與升級潛力 | World Bank、各國統計局 | 年度、現價或不變價、每人或總額 |
| 渠道規模 | 比較線上／線下市場規模與渠道角色 | 各國統計局、官方／可信研究 | 零售銷售額、GMV、平台收入須分開 |
| 品類損益 | 判斷各品類的交易、毛利與效率 | 內部 ERP／POS／平台後台 | GMV、品牌淨銷售、毛利、退貨、客單價須分開 |

## 上傳檔案格式

儀表板接受 CSV 或 XLSX。以下檔案均可只包含現時可取得的市場、年度與指標；沒有資料時，儀表板會標示缺口，**不會以估算或模擬數字補足**。

### `channel_metrics.csv`

| 欄位 | 格式／例子 | 說明 |
|---|---|---|
| `country` | `Indonesia` | 必填，必須與看板市場名稱一致。 |
| `year` | `2024` | 必填。 |
| `channel` | `E-commerce`、`Physical retail`、`Social commerce` | 必填。 |
| `metric_type` | `GMV`、`Retail sales`、`Platform revenue`、`Penetration` | 必填，避免把不同數字相加。 |
| `value` | `159000` | 必填；數值原樣儲存。 |
| `unit` | `USD m`、`%` | 必填。 |
| `scope` | `ASEAN-6`、`B2C`、`Retail e-commerce` | 必填；指明涵蓋範圍。 |
| `source_name` | `e-Conomy SEA 2024` | 必填。 |
| `source_url` | 完整 URL | 必填。 |
| `notes` | 短句 | 選填；記錄估算、是否含跨境或食品等。 |

### `category_metrics.csv`

| 欄位 | 格式／例子 | 說明 |
|---|---|---|
| `country`、`year`、`channel` | 同上 | 必填。 |
| `category` | `Fashion`、`Home & living`、`Jewellery & luxury` | 必填。 |
| `metric_type` | `GMV`、`Net sales`、`Purchase penetration`、`Gross margin` | 必填。 |
| `value`、`unit` | `83`、`%` | 必填。 |
| `scope` | `Survey respondents` | 必填。 |
| `source_name`、`source_url` | 同上 | 必填。 |
| `notes` | 短句 | 選填。 |

## 資料管治規則

1. **零售銷售額、平台 GMV、平台收入與品牌淨銷售不可合併、不可相加。**
2. 每筆資料都必須標示幣別、年度、來源連結與涵蓋範圍；無法確認者不得上傳至決策頁。
3. 公開市場基準用於方向判讀；品牌盈利分析應優先使用內部 ERP、POS 與平台後台的交易資料。
4. 若要做跨國加總，先將貨幣、期間、是否含稅、B2C／B2B、跨境／本地及品類映射統一。
