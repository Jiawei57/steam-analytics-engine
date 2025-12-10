import streamlit as st
import pandas as pd
import plotly.express as px
import os
from sqlalchemy import create_engine

st.set_page_config(page_title="Steam 市場全景儀表板", page_icon="🕹️", layout="wide")

# --- CSS 優化 ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #262730;
        border: 1px solid #464b5c;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- 1. 資料載入 ---
@st.cache_data
def load_data():
    try:
        db_user = os.getenv('POSTGRES_USER', 'steam_user')
        db_password = os.getenv('POSTGRES_PASSWORD', 'password')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'steam_db')
        
        uri = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        engine = create_engine(uri)
        query = "SELECT * FROM steam_games"
        return pd.read_sql(query, engine)
    except Exception:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        csv_path = os.path.join(base_dir, "data", "processed", "steam_processed_data.csv")
        return pd.read_csv(csv_path) if os.path.exists(csv_path) else pd.DataFrame()

raw_df = load_data()

# --- 2. 側邊欄：全域篩選器 ---
with st.sidebar:
    st.header("🔍 全域篩選條件")
    
    if not raw_df.empty:
        raw_df['year'] = pd.to_datetime(raw_df['release_date'], errors='coerce').dt.year
        raw_df['price_numeric'] = pd.to_numeric(raw_df['price'], errors='coerce').fillna(0)
        
        search_term = st.text_input("搜尋遊戲名稱", placeholder="例: Counter-Strike")
        
        raw_df['main_genre'] = raw_df['genres'].astype(str).apply(lambda x: x.split(',')[0] if x else 'Unknown')
        all_genres = sorted(raw_df['main_genre'].unique().tolist())
        selected_genres = st.multiselect("遊戲類型 (Genres)", all_genres, default=[])
        
        min_p, max_p = int(raw_df['price_numeric'].min()), int(raw_df['price_numeric'].max())
        price_range = st.slider("價格區間 (USD)", min_p, max_p if max_p > 0 else 100, (0, 100))
        
        min_y, max_y = int(raw_df['year'].min()), int(raw_df['year'].max())
        year_range = st.slider("發行年份", 2000, 2025, (2015, 2025))
        
        st.caption(f"資料來源: {len(raw_df)} 筆原始數據")

# --- 3. 核心邏輯：資料篩選 ---
if raw_df.empty:
    st.error("❌ 無法載入資料，請先執行 ETL (make run-etl)。")
    st.stop()

df = raw_df.copy()
df = df[(df['year'] >= year_range[0]) & (df['year'] <= year_range[1])]
df = df[(df['price_numeric'] >= price_range[0]) & (df['price_numeric'] <= price_range[1])]

if selected_genres:
    mask = df['genres'].astype(str).apply(lambda x: any(g in x for g in selected_genres))
    df = df[mask]

if search_term:
    df = df[df['game_title'].astype(str).str.contains(search_term, case=False, na=False)]

# --- 4. 主要儀表板顯示 ---
st.title("🕹️ Steam 遊戲市場全景儀表板")

if search_term or selected_genres:
    st.info(f"🔎 目前篩選結果：共 {len(df)} 款遊戲")

# === 第一部分：KPI 指標 ===
k1, k2, k3, k4 = st.columns(4)
total_games = len(df)
avg_price = df['price_numeric'].mean() if total_games > 0 else 0
free_games = df[df['price_numeric'] == 0].shape[0]
total_reviews = (df['positive'] + df['negative']).sum() if 'positive' in df.columns else 0

k1.metric("🎮 篩選遊戲數", f"{total_games:,}")
k2.metric("💰 平均售價", f"${avg_price:.2f}")
k3.metric("🆓 免費遊戲數", f"{free_games:,}")
k4.metric("📝 總評論數", f"{total_reviews/1000000:.2f}M" if total_reviews > 1000000 else f"{total_reviews:,}")

st.divider()

# === 第二部分：智慧分析切換 ===
if 0 < len(df) <= 50:
    st.subheader(f"{search_term if search_term else '篩選結果'} 競品比較")
    m1, m2 = st.columns(2)
    
    with m1:
        if 'positive_ratio' in df.columns:
            fig_scatter = px.scatter(
                df, x='price_numeric', y='positive_ratio',
                size='total_reviews', color='main_genre',
                hover_name='game_title',
                title='💰 CP 值分析：價格 vs. 好評率',
                labels={'price_numeric': '價格 (USD)', 'positive_ratio': '好評率 (0-1)'},
                size_max=60
            )
            # Plotly 圖表仍使用 use_container_width
            st.plotly_chart(fig_scatter, use_container_width=True)
            
    with m2:
        top_games = df.sort_values('total_reviews', ascending=False).head(10)
        fig_bar = px.bar(
            top_games, x='total_reviews', y='game_title',
            orientation='h',
            title='🔥 熱門度排行 (Top 10)',
            labels={'total_reviews': '總評論數', 'game_title': '遊戲名稱'},
            color='total_reviews', color_continuous_scale='Viridis'
        )
        fig_bar.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.subheader("🗺️ 市場機會地圖 (Market Heatmap)")
    st.caption("當資料量較大時，使用**熱力圖**尋找「高好評、低競爭」的藍海市場。")
    
    df['price_tier'] = pd.cut(df['price_numeric'], bins=[-1, 0, 10, 30, 60, 1000], labels=['Free', '<$10', '$10-30', '$30-60', '>$60'])
    df['review_tier'] = pd.cut(df['total_reviews'], bins=[-1, 100, 1000, 10000, 100000000], labels=['冷門', '小眾', '熱門', '爆款'])
    
    t1, t2 = st.tabs(["🔥 價格x熱門度 熱力圖", "📦 價格x品質 箱形圖"])
    
    with t1:
        # 修改處：加入 observed=True 以消除 FutureWarning
        heatmap_data = df.groupby(['price_tier', 'review_tier'], observed=True)['positive_ratio'].mean().reset_index()
        heatmap_matrix = heatmap_data.pivot(index='review_tier', columns='price_tier', values='positive_ratio')
        
        fig_heat = px.imshow(
            heatmap_matrix,
            labels=dict(x="價格區間", y="熱門度", color="平均好評率"),
            text_auto=".2f",
            color_continuous_scale='RdBu',
            aspect="auto",
            title="🎯 市場熱點分析：哪種定價策略好評率最高？"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
        
    with t2:
        fig_box = px.box(
            df, x='price_tier', y='positive_ratio', color='price_tier',
            title="📊 價格與品質分佈 (越貴的遊戲真的越好嗎？)",
            labels={'price_tier':'價格區間', 'positive_ratio':'好評率'},
            points='outliers',
            category_orders={'price_tier': ['Free', '<$10', '$10-30', '$30-60', '>$60']}
        )
        st.plotly_chart(fig_box, use_container_width=True)

st.divider()

# === 第三部分：時間軸趨勢 ===
st.subheader("📈 市場供需趨勢分析")

c1, c2 = st.columns(2)

with c1:
    st.markdown("##### 📦 供給端：新遊戲上架數")
    if not df.empty:
        year_counts = df['year'].value_counts().sort_index()
        if len(df) <= 5: 
            target_genre = df.iloc[0]['main_genre']
            bg_df = raw_df[raw_df['main_genre'] == target_genre]
            bg_counts = bg_df['year'].value_counts().sort_index()
            bg_counts = bg_counts[(bg_counts.index >= 2010) & (bg_counts.index <= 2025)]
            
            fig_supply = px.bar(
                x=bg_counts.index, y=bg_counts.values,
                labels={'x':'年份', 'y':f'{target_genre} 新遊戲數'},
                color_discrete_sequence=['#E0E0E0']
            )
            target_year = df.iloc[0]['year']
            if target_year in bg_counts.index:
                fig_supply.add_vline(x=target_year, line_width=2, line_dash="dash", line_color="red", annotation_text="發行年")
        else:
            year_counts = year_counts[(year_counts.index >= 2010) & (year_counts.index <= 2025)]
            fig_supply = px.bar(
                x=year_counts.index, y=year_counts.values, 
                labels={'x':'年份', 'y':'新遊戲數量 (款)'}, 
                color_discrete_sequence=['#00CC96']
            )
            
        st.plotly_chart(fig_supply, use_container_width=True)

with c2:
    st.markdown("##### 🔥 需求端：玩家評論熱度")
    if not df.empty:
        if len(df) <= 5:
            target_genre = df.iloc[0]['main_genre']
            bg_df = raw_df[raw_df['main_genre'] == target_genre]
            # 修改處：加入 observed=True
            demand_trend = bg_df.groupby('year', observed=True)['total_reviews'].mean().sort_index()
        else:
            # 修改處：加入 observed=True
            demand_trend = df.groupby('year', observed=True)['total_reviews'].sum().sort_index()
            
        demand_trend = demand_trend[(demand_trend.index >= 2010) & (demand_trend.index <= 2025)]
        
        fig_demand = px.line(
            x=demand_trend.index, y=demand_trend.values, 
            labels={'x':'年份', 'y':'評論熱度'}, 
            markers=True, 
            color_discrete_sequence=['#FF6692']
        )
        if len(df) <= 5:
             fig_demand.add_vline(x=df.iloc[0]['year'], line_width=2, line_dash="dash", line_color="red")
             
        st.plotly_chart(fig_demand, use_container_width=True)

# === 第四部分：詳細資料列表 ===
with st.expander("📋 查看詳細資料列表", expanded=True):
    display_df = df[['appid', 'game_title', 'price_numeric', 'release_date', 'genres', 'positive_ratio', 'total_reviews']].copy()
    display_df['price_display'] = display_df['price_numeric'].apply(lambda x: "Free" if x == 0 else f"${x:.2f}")

    # 修改處：使用 width="stretch" 取代 use_container_width=True
    st.dataframe(
        display_df.sort_values(by='release_date', ascending=False),
        column_config={
            "appid": "App ID",
            "game_title": "遊戲名稱",
            "price_display": "價格",
            "release_date": "發行日期",
            "positive_ratio": st.column_config.ProgressColumn("好評率", min_value=0, max_value=1, format="%.2f"),
            "total_reviews": st.column_config.NumberColumn("評論數"),
            "price_numeric": None 
        },
        width="stretch",
        hide_index=True
    )