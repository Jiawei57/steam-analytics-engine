import streamlit as st

st.set_page_config(
    page_title="Steam 數據分析平台 (2025)",
    page_icon="🎮",
    layout="wide"
)

st.title("歡迎來到 Steam 數據分析平台 🎮")
st.caption("Powered by Steam 2025 Dataset & Real-time AI Engine")
st.markdown("---")

st.header("核心功能導覽")
st.markdown("""
本平台整合了 **2025 年最新 Steam 遊戲數據** 與 **50 萬筆玩家評論**，為您提供全方位的市場洞察：

- **📈 市場儀表板**: 宏觀分析 Steam 市場的價格分佈與發行趨勢，支援特定遊戲定位。
- **💬 評論分析**: 深入挖掘特定遊戲的玩家反饋、好評率與市場定位。
- **🤖 推薦引擎**: 基於 NLP 技術與向量運算的即時遊戲推薦系統。

請點擊左側側邊欄開始探索！
""")

# 狀態顯示
col1, col2, col3 = st.columns(3)
col1.info("✅ ETL 流程：已自動化")
col2.success("✅ 資料庫：PostgreSQL 13")
col3.warning("✅ AI 引擎：即時運算模式")