import streamlit as st
import pandas as pd
import polars as pl
import plotly.express as px
import os
from collections import Counter
import re
from sqlalchemy import create_engine

st.set_page_config(page_title="玩家評論深度分析", page_icon="🗣️", layout="wide")

# [UI] 統一視覺風格
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

# --- 1. 資料載入層 ---
@st.cache_data(ttl=3600)
def load_game_list():
    """從資料庫讀取所有遊戲清單 (ID + Name)，用於下拉選單"""
    try:
        db_user = os.getenv('POSTGRES_USER', 'steam_user')
        db_password = os.getenv('POSTGRES_PASSWORD', 'password')
        db_host = os.getenv('POSTGRES_HOST', 'localhost')
        db_port = os.getenv('POSTGRES_PORT', '5432')
        db_name = os.getenv('POSTGRES_DB', 'steam_db')
        
        uri = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'
        engine = create_engine(uri)
        query = "SELECT appid, game_title FROM steam_games"
        return pd.read_sql(query, engine)
    except:
        # Fallback 機制
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        csv_path = os.path.join(base_dir, "data", "processed", "steam_processed_data.csv")
        return pd.read_csv(csv_path)[['appid', 'game_title']] if os.path.exists(csv_path) else pd.DataFrame()

@st.cache_data(show_spinner=False)
def load_reviews(target_appid):
    """
    [效能優化關鍵] 使用 Polars Lazy API 讀取大檔
    只讀取特定 AppID 的資料列，避免將 7GB 檔案全部載入記憶體 (OOM Protection)
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    reviews_path = os.path.join(base_dir, "data", "raw", "reviews_2024.csv")
    
    if not os.path.exists(reviews_path):
        return None

    try:
        # [Schema Inference] 自動偵測 CSV 欄位，相容不同版本的資料集
        schema_check = pl.read_csv(reviews_path, n_rows=0)
        cols = schema_check.columns
        
        id_col = 'app_id' if 'app_id' in cols else 'appid'
        score_col = next((c for c in cols if c in ['voted_up', 'review_score', 'is_positive']), None)
        vote_col = next((c for c in cols if c in ['votes_up', 'vote_up']), None)
        time_col = next((c for c in cols if c in ['timestamp_created', 'created_at']), None)
        text_col = next((c for c in cols if c in ['review', 'review_text', 'content']), None)
        lang_col = next((c for c in cols if c in ['language', 'lang']), None)
        playtime_col = next((c for c in cols if c in ['author_playtime_forever', 'playtime_forever']), None)

        exprs = []
        if score_col: exprs.append(pl.col(score_col).alias("review_score"))
        if vote_col: exprs.append(pl.col(vote_col).alias("vote_up"))
        if time_col: exprs.append(pl.col(time_col).alias("timestamp_created"))
        if lang_col: exprs.append(pl.col(lang_col).alias("language"))
        if playtime_col: exprs.append(pl.col(playtime_col).alias("playtime_forever"))
        if text_col:
            exprs.append(pl.col(text_col).alias("review_text"))
        else:
            exprs.append(pl.lit(None).alias("review_text"))

        q = (
            pl.scan_csv(reviews_path, ignore_errors=True)
            .filter(pl.col(id_col).cast(pl.Int64) == target_appid)
            .select(exprs)
        )
        
        df = q.collect().to_pandas()
        
        if time_col:
            try:
                df['timestamp_created'] = pd.to_datetime(df['timestamp_created'], unit='s')
            except:
                df['timestamp_created'] = pd.to_datetime(df['timestamp_created'], errors='coerce')
                
        return df
    except Exception as e:
        st.error(f"讀取失敗: {e}")
        return pd.DataFrame()

# --- 2. 側邊欄控制 ---
game_map = load_game_list()

with st.sidebar:
    st.header("🔍 分析目標")
    if not game_map.empty:
        game_map['display_name'] = game_map['game_title'] + " (ID: " + game_map['appid'].astype(str) + ")"
        game_options = game_map['display_name'].tolist()
        
        selected_option = st.selectbox("搜尋遊戲:", game_options, index=0)
        selected_appid = int(re.search(r"\(ID: (\d+)\)", selected_option).group(1))
        selected_game_title = game_map[game_map['appid'] == selected_appid]['game_title'].iloc[0]
    else:
        st.warning("⚠️ 無法載入遊戲清單")
        selected_appid = None

# --- 3. 分析儀表板 ---
st.title(f"🗣️ 玩家評論深度分析：{selected_game_title if 'selected_game_title' in locals() else ''}")

if selected_appid:
    with st.spinner(""): 
        raw_reviews_df = load_reviews(selected_appid)

    if raw_reviews_df is None:
        st.error("❌ 找不到原始資料檔。")
    elif raw_reviews_df.empty:
        st.warning(f"⚠️ 無相關評論資料。")
    else:
        reviews_df = raw_reviews_df.copy()
        
        # [功能] 語言篩選器
        if 'language' in reviews_df.columns:
            lang_counts = reviews_df['language'].value_counts()
            available_langs = ['All'] + lang_counts.index.tolist()
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("🌍 語言篩選")
            lang_labels = [f"{l} ({len(reviews_df[reviews_df['language']==l])})" if l != 'All' else '全部語言' for l in available_langs]
            selected_lang_idx = st.sidebar.selectbox("選擇語言:", range(len(available_langs)), format_func=lambda x: lang_labels[x])
            selected_lang = available_langs[selected_lang_idx]
            
            if selected_lang != 'All':
                reviews_df = reviews_df[reviews_df['language'] == selected_lang]

        # 資料前處理
        has_text = reviews_df['review_text'].notnull().any()
        has_score = 'review_score' in reviews_df.columns
        has_time = 'timestamp_created' in reviews_df.columns
        has_playtime = 'playtime_forever' in reviews_df.columns

        total_reviews = len(reviews_df)
        if has_score:
            reviews_df['is_positive'] = reviews_df['review_score'].astype(str).str.contains('1|True', case=False)
            positive_rate = reviews_df['is_positive'].mean() if total_reviews > 0 else 0
        else:
            positive_rate = 0
            
        avg_votes = reviews_df['vote_up'].mean() if 'vote_up' in reviews_df.columns else 0

        # [KPI] 核心指標
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📝 樣本數", f"{total_reviews:,}")
        c2.metric("👍 好評率", f"{positive_rate:.1%}" if has_score else "N/A")
        c3.metric("🔥 平均有用", f"{avg_votes:.1f}")
        if has_time:
            c4.metric("📅 資料區間", f"{reviews_df['timestamp_created'].dt.year.min()} - {reviews_df['timestamp_created'].dt.year.max()}")
        else:
            c4.metric("📅 資料區間", "N/A")

        st.divider()

        # [Chart] 趨勢分析
        if has_time and has_score:
            st.subheader("📈 評論熱度趨勢")
            reviews_df['month_year'] = reviews_df['timestamp_created'].dt.to_period('M').astype(str)
            trend_df = reviews_df.groupby(['month_year', 'is_positive'], observed=True).size().reset_index(name='count')
            trend_df['Sentiment'] = trend_df['is_positive'].map({True: '好評', False: '負評'})
            
            fig_trend = px.bar(
                trend_df, x='month_year', y='count', color='Sentiment',
                color_discrete_map={'好評': '#00CC96', '負評': '#EF553B'},
                title="每月評論數量變化"
            )
            st.plotly_chart(fig_trend, use_container_width=True)

        # [Chart] 遊玩時數分析
        if has_playtime and has_score:
            st.subheader("⏳ 遊玩時數與評價")
            reviews_df['hours_played'] = reviews_df['playtime_forever'] / 60
            cap = reviews_df['hours_played'].quantile(0.95)
            filtered_playtime = reviews_df[reviews_df['hours_played'] < cap]
            
            fig_playtime = px.box(
                filtered_playtime, x='hours_played', y='is_positive', color='is_positive',
                orientation='h',
                labels={'is_positive': '評價', 'hours_played': '遊玩時數 (小時)'},
                color_discrete_map={True: '#00CC96', False: '#EF553B'},
                category_orders={'is_positive': [True, False]}
            )
            fig_playtime.update_layout(yaxis=dict(tickvals=[True, False], ticktext=['好評', '負評']))
            st.plotly_chart(fig_playtime, use_container_width=True)

        # [Chart] 關鍵字分析
        if has_text:
            st.subheader("🔑 熱門關鍵字")
            stopwords = set(['the', 'and', 'a', 'to', 'of', 'is', 'it', 'in', 'this', 'for', 'game', 'i', 'my', 'but', 'not', 'are', 'was', 'with', 'on', 'have', 'be', 'you', 'that', 'as'])
            
            def get_top_words(text_series, n=15):
                all_text = ' '.join(text_series.dropna().astype(str).tolist()).lower()
                words = re.findall(r'\b[a-z]{3,15}\b', all_text)
                words = [w for w in words if w not in stopwords]
                return Counter(words).most_common(n)

            col_pos, col_neg = st.columns(2)
            
            with col_pos:
                st.markdown("##### 😊 好評關鍵字")
                pos_words = get_top_words(reviews_df[reviews_df['is_positive']]['review_text'])
                if pos_words:
                    pos_df = pd.DataFrame(pos_words, columns=['Word', 'Count'])
                    fig_pos = px.bar(pos_df, x='Count', y='Word', orientation='h', color_discrete_sequence=['#00CC96'])
                    fig_pos.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_pos, use_container_width=True)

            with col_neg:
                st.markdown("##### 😡 負評關鍵字")
                neg_words = get_top_words(reviews_df[~reviews_df['is_positive']]['review_text'])
                if neg_words:
                    neg_df = pd.DataFrame(neg_words, columns=['Word', 'Count'])
                    fig_neg = px.bar(neg_df, x='Count', y='Word', orientation='h', color_discrete_sequence=['#EF553B'])
                    fig_neg.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_neg, use_container_width=True)

        # [Browser] 評論瀏覽
        if has_text:
            st.divider()
            st.subheader("🔍 評論內容瀏覽")
            filter_type = st.radio("篩選:", ["全部", "好評", "負評"], horizontal=True)
            
            display_df = reviews_df.copy()
            if filter_type == "好評":
                display_df = display_df[display_df['is_positive']]
            elif filter_type == "負評":
                display_df = display_df[~display_df['is_positive']]
                
            top_reviews = display_df.sort_values('vote_up', ascending=False).head(20)
            
            for _, row in top_reviews.iterrows():
                sentiment_icon = "😊" if row['is_positive'] else "😡"
                date_str = row['timestamp_created'].date() if pd.notnull(row['timestamp_created']) else ""
                lang_tag = f"[{row['language']}] " if 'language' in row else ""
                playtime_str = f" ({int(row['playtime_forever']/60)}h)" if has_playtime else ""
                
                with st.expander(f"{sentiment_icon} {lang_tag}{date_str}{playtime_str} (有用: {row['vote_up']})"):
                    st.write(row['review_text'])