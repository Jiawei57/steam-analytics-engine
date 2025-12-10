# 🎮 Steam Game Analytics & Recommendation Engine
## Steam 遊戲市場數據分析與 AI 推薦引擎

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B?logo=streamlit&logoColor=white)
![Polars](https://img.shields.io/badge/Polars-Fast%20ETL-orange)
![License](https://img.shields.io/badge/License-MIT-green)

### 📖 專案概述 (Project Overview)
本專案是一個全端數據分析解決方案，旨在解決 Steam 平台上的「資訊過載」與「發現困難」問題。

透過容器化微服務架構，我們整合了 **Hybrid ETL 數據管線**、**關聯式資料庫**與 **機器學習模型**，構建了一個互動式儀表板。該平台不僅提供宏觀的市場趨勢分析，更利用 **混合推薦系統 (Hybrid Recommendation System)** 為玩家提供精準的個性化遊戲推薦，展現了數據驅動決策 (Data-Driven Decision Making) 的商業價值。

---

### 📸 系統展示 (System Demo)

> 本系統提供從宏觀市場分析到微觀評論洞察的完整解決方案。

#### 1. 📊 全景儀表板 (Overall Dashboard)
展示全域篩選器、核心 KPI 指標、以及市場供需趨勢分析。

| **市場概況與 KPI** | **進階篩選與列表** |
|:---:|:---:|
| <img src="docs/images/Overall Dashboard_1.jpg" alt="KPI Overview" width="100%"/> | <img src="docs/images/Overall Dashboard_2.jpg" alt="Filters & List" width="100%"/> |
| *圖 1：核心指標監控* | *圖 2：詳細資料篩選* |

| **市場熱力圖 (Heatmap)** | **供需趨勢 (Trends)** |
|:---:|:---:|
| <img src="docs/images/Overall Dashboard_3.jpg" alt="Market Heatmap" width="100%"/> | <img src="docs/images/Overall Dashboard_4.jpg" alt="Supply Demand" width="100%"/> |
| *圖 3：定價策略熱點分析* | *圖 4：歷年市場趨勢* |

---

#### 2. 🤖 AI 智慧應用 (AI Applications)
整合自然語言處理 (NLP) 與推薦演算法，提供深度的玩家洞察。

| **智慧推薦模擬** | **玩家評論深度分析** |
|:---:|:---:|
| <img src="docs/images/智慧推薦模擬.jpg" alt="AI Recommendation" width="100%"/> | <img src="docs/images/玩家評論分析.jpg" alt="Review Analysis" width="100%"/> |
| *圖 5：可解釋性推薦 (XAI)* | *圖 6：多國語言輿情監測* |

---

### 🚀 核心功能 (Key Features)

#### 1. 📊 互動式市場儀表板 (KPI Dashboard)
- **商業指標監控**：即時展示「收錄遊戲總數」、「平均售價」、「累積評論數」等關鍵績效指標 (KPI)。
- **全域連動篩選**：側邊欄支援依據 **年份、遊戲類型、價格區間** 進行多維度下鑽分析 (Drill-down)。
- **智慧視角切換**：自動偵測資料量級，在「宏觀趨勢圖」與「微觀競品分析 (氣泡圖)」之間切換。

#### 2. 🗣️ 玩家評論深度分析 (Sentiment EDA)
- **大數據輿情監測**：利用 **Polars** 引擎秒級處理數百萬筆評論資料，分析好評率趨勢。
- **多國語言分析**：自動偵測並篩選不同語系 (如繁中、英文) 的玩家評論，洞察在地化市場反應。
- **關鍵字提取**：自動歸納好評與負評中的熱門關鍵字 (Top Keywords)。

#### 3. 🤖 雙引擎 AI 推薦系統 (Explainable AI)
- **可解釋性推薦 (XAI)**：不只給出推薦列表，更直接展示「推薦理由」(例如：共同標籤、好評率、風格相似)，提升使用者信任度。
- **效能優化**：實作 Model Caching 機制，解決大型模型載入延遲問題。

#### 4. ⚙️ 自動化 ETL 數據管線
- **Hybrid ETL 架構**：
    - **Extract/Transform**: 使用 **Polars** 處理 7GB+ 原始資料，解決記憶體瓶頸。
    - **Load**: 轉換為 Pandas 以無縫對接 SQLAlchemy，支援資料庫 **Upsert** 更新機制。
- **資料品質驗證**：整合 **Pandera** 進行資料 Schema 驗證，確保資料完整性。

---

### 🏗️ 系統架構 (System Architecture)

```text
+--------+       +-------------------+       +-----------------+
|  User  | ----> |  Web App (8501)   | <---> |   PostgreSQL    |
+--------+       +-------------------+       +-----------------+
  (Browser)               ^                           ^
                          | (Read Model)              | (Upsert Data)
                          |                           |
                 +-------------------+       +-----------------+
                 |   ML Inference    | <---- |   ETL Service   |
                 +-------------------+       +-----------------+
                                                      ^
                                                      | (Polars Read)
                                             +-----------------+
                                             |    Raw CSVs     |
                                             +-----------------+

📂 專案結構 (Project Structure)
Bash

Steam-Analytics-Engine/
├── data/
│   ├── raw/                  # 原始數據 (需自行下載)
│   ├── models/               # 訓練好的 ML 模型 (.pkl)
│   └── processed/            # 清理後的中間產物
├── scripts/
│   ├── process_steam_data.py # Hybrid ETL 主程式 (含 Pandera 驗證)
│   └── train_model.py        # 模型訓練腳本
├── src/
│   └── webapp/               # Streamlit 前端應用
│       ├── Home.py           # 入口首頁
│       └── pages/            # 1_Dashboard, 2_Reviews, 3_Recommendation
├── tests/                    # 單元測試 (Pytest)
├── .env                      # 環境變數
├── docker-compose.yml        # 服務編排設定
├── requirements.txt          # Python 相依套件
├── merge_reviews.py          # 大數據合併工具 (Polars)
├── Makefile                  # 專案指令集 (One-click commands)
└── README.md                 # 專案說明文件
📦 資料來源與設定 (Data Source Setup)
由於原始資料集 (Raw Data) 體積龐大 (>7GB)，不包含在本儲存庫中。請依照以下步驟準備資料：

下載資料集：

遊戲元數據：Kaggle - Steam Games Dataset (重新命名為 games_2025.csv)

玩家評論數據：Kaggle - Steam Games Reviews 2024 (解壓至資料夾)

放置檔案： 將 games_2025.csv 放入 data/raw/。

執行合併腳本 (針對評論資料)：

Bash

export STEAM_REVIEWS_PATH="/path/to/downloaded/SteamReviews2024"
python merge_reviews.py
(此步驟將自動產出清洗後的 reviews_2024.csv)

⚡ 快速開始 (Getting Started)
本專案提供 Makefile 支援，一鍵管理生命週期。

1. 複製專案
Bash

git clone [https://github.com/your-username/steam-analytics-engine.git](https://github.com/your-username/steam-analytics-engine.git)
cd steam-analytics-engine

2. 啟動服務 (Docker 模式 - 推薦)
一鍵啟動所有服務（包含 DB 初始化、ETL 資料寫入與 Web App）：
Bash

make docker-up
# 或: docker-compose up --build

3. 本機開發模式 (Optional)
Bash

# 安裝依賴
make install

# 執行 ETL 與測試
make run-etl
make test

# 啟動網頁
make run-app

4. 訪問應用
數據儀表板: http://localhost:8501