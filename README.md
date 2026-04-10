# Flight Search MVP

一個「多出發地 / 多目的地 / 多幣別」的機票最低價搜尋 Web App 第一版。

這個 MVP 讓使用者輸入城市、日期、單程/來回、艙等與幣別後，系統會：

1. 自動把城市展開成多個候選機場
2. 搜尋所有機場組合
3. 將 mock provider 回傳的價格轉成指定幣別
4. 依照排序規則回傳最便宜 / 最短 / 綜合最佳結果

目前版本使用：

- Frontend: React + Vite + TypeScript
- Backend: FastAPI
- Flight data: Mock provider
- Exchange rate: Mock currency service
- Airport catalog: OpenFlights global airport dataset

## 專案特色

- 手機優先介面，適合 iPhone 瀏覽
- 搜尋條件固定在上方
- 白底卡片式結果
- 最便宜方案帶有 `Best Price` 標籤
- 支援中文城市別名，例如 `武漢`、`台北`
- 支援全球城市 / 機場 autocomplete，可輸入城市、機場名稱或 IATA code
- 架構保留未來接真實 flight API 的空間

## 專案結構

```text
flight-search-mvp/
├── backend/
│   ├── app/
│   │   ├── providers/
│   │   └── services/
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── public/
│   └── src/
├── config/
│   ├── city_airports.json
│   ├── city_aliases.json
│   ├── city_currencies.json
│   ├── currency_rates.json
│   └── mock_flights.json
├── shared/
├── .env.example
└── README.md
```

## 功能範圍

### 已完成

- 城市展開：`武漢 -> [WUH, CSX, KHN]`
- 城市展開：`台北 -> [TPE, TSA, KHH]`
- 全球城市展開：例如 `Paris -> [CDG, ORY, LBG]`
- 全球機場查詢：例如 `HND`、`CDG`、`JFK`
- 多組合查詢
- 單程 / 來回
- 來回票支援去程、回程分開搜尋後再自動配對
- 經濟艙 / 商務艙
- 幣別模式
  - 出發地貨幣
  - 目的地貨幣
  - 自訂幣別
- 排序模式
  - `cheapest`
  - `shortest`
  - `best_value`
- 轉機限制
  - 不限
  - 只看直飛
  - 最多 1 次轉機
- 基本後端單元測試

### 目前仍是 Mock

- 真實航班資料
- 真實購票連結
- 即時匯率 API
- 真實城市地理擴展演算法
- 真實航空公司票價與 availability

## 快速啟動

## 1. 準備環境

需要：

- Python 3.11+
- Node.js 18+
- npm 9+

把環境變數範例複製一份：

```bash
cp .env.example .env
```

## 2. 啟動 Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

啟動後可打開：

- API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

## 3. 啟動 Frontend

開新終端機：

```bash
cd frontend
npm install
npm run dev
```

打開：

- Frontend: [http://localhost:5173](http://localhost:5173)

## API 範例

### POST `/search-flights`

Request:

```json
{
  "origin_city": "Wuhan",
  "destination_city": "Taipei",
  "departure_date": "2026-05-01",
  "return_date": "2026-05-05",
  "trip_type": "round_trip",
  "cabin_class": "economy",
  "currency_mode": "destination",
  "currency": "TWD",
  "sort_mode": "cheapest",
  "max_stops": 1
}
```

也可以直接輸入中文城市：

```json
{
  "origin_city": "武漢",
  "destination_city": "台北",
  "departure_date": "2026-05-01",
  "return_date": "2026-05-05",
  "trip_type": "round_trip",
  "cabin_class": "economy",
  "currency_mode": "destination",
  "currency": null,
  "sort_mode": "cheapest",
  "max_stops": null
}
```

Response 內容包含：

- 展開後的出發機場清單
- 展開後的目的地機場清單
- 每一組 route 的查詢結果
- 排序後的最佳結果清單

### GET `/airport-suggestions?q=...`

用來支援前端 autocomplete。

範例：

```bash
curl "http://localhost:8000/airport-suggestions?q=tok"
```

回傳會同時包含：

- 城市建議，例如 `Tokyo, Japan (HND, NRT, IBR)`
- 機場建議，例如 `Haneda Airport (HND) - Tokyo, Japan`

## 排序邏輯說明

- `cheapest`: 以顯示幣別下的總價格排序
- `shortest`: 以總飛行時間排序
- `best_value`: 以價格 65% + 飛行時間 35% 做綜合分數

## 來回票組合邏輯

目前來回查詢不是把一筆單程假資料直接複製成回程，而是：

1. 先找去程選項
2. 再找回程選項
3. 將去程與回程交叉組合
4. 再依價格或時間排序

所以系統可以找到像這種更接近真實情境的結果：

- 去程直飛
- 回程 1 次轉機
- 或去回程不同航空公司

這個分數是 MVP 版本的簡單規則，後續可以改成更精細的商業邏輯。

## 城市與機場設定

機場展開規則在：

- [config/city_airports.json](/tmp/flight-search-mvp/config/city_airports.json)

城市別名在：

- [config/city_aliases.json](/tmp/flight-search-mvp/config/city_aliases.json)

例如你要新增更多城市，只要更新對應 JSON：

```json
{
  "Tokyo": ["HND", "NRT", "IBR"]
}
```

如果要支援中文輸入，也把別名加入：

```json
{
  "東京": "Tokyo"
}
```

除了手動 mapping 以外，系統現在也會從全球機場資料集自動展開未知城市。

## 全球機場資料來源

這版內建兩份公開資料：

- [openflights_airports.dat](/tmp/flight-search-mvp/config/openflights_airports.dat)
- [countries.json](/tmp/flight-search-mvp/config/countries.json)

用途：

- `openflights_airports.dat`: 全球城市 / 機場搜尋與 IATA 展開
- `countries.json`: 國家對應幣別

目前策略是：

- 已有手動 mapping 的城市，優先走手動擴展
- 其他城市，自動從全球機場資料找最佳城市群組
- 若某國幣別沒有 mock 匯率，顯示幣別會 fallback 到 `USD`

## 幣別轉換設計

目前匯率來源為 mock 檔案：

- [config/currency_rates.json](/tmp/flight-search-mvp/config/currency_rates.json)

對應服務：

- [currency_service.py](/tmp/flight-search-mvp/backend/app/services/currency_service.py)

未來若要換成真實匯率 API，可以保留同樣介面，只替換 service 內部實作。

## Flight Provider 擴充方式

目前 provider 抽象與 mock 實作：

- [flight_provider.py](/tmp/flight-search-mvp/backend/app/providers/flight_provider.py)
- [mock_provider.py](/tmp/flight-search-mvp/backend/app/providers/mock_provider.py)

未來串接真實 API 的建議做法：

1. 新增 `backend/app/providers/real_provider.py`
2. 實作 `FlightProvider.search(...)`
3. 在 `backend/app/main.py` 中把 `MockFlightProvider()` 換成新的 provider
4. 把 API key 放進 `.env`

目前 mock provider 的新行為：

- 已知 route：優先使用手工 mock 航班資料
- 未知 route：根據全球機場座標自動生成 synthetic 測試票價

這讓 MVP 即使在還沒接真實 flight API 前，也能測全球城市查詢流程。

## 測試

執行後端測試：

```bash
cd backend
python3 -m unittest discover tests
```

## 這次在本機的驗證狀態

我已完成：

- Backend Python 語法編譯檢查
- Backend unit tests
- Frontend production build

這個工作區目前缺少：

- 無
我在這個 session 已經驗證：

- 後端 `11` 個測試通過
- 前端 `npm run build` 成功

## 下一步建議

如果你要做第二版，最值得優先補的會是：

1. 接真實 flight search provider
2. 接真實 exchange rate API
3. 支援更多城市與城市群組
4. 加入 airline filters、早去晚回偏好、最大轉機數等條件
