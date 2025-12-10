import streamlit as st
import pandas as pd
import pickle
import os
from sklearn.metrics.pairwise import linear_kernel

st.set_page_config(page_title="推薦引擎模擬", page_icon="🤖", layout="wide")

# --- CSS 優化 (統一全站風格) ---
st.markdown("""
<style>
    /* KPI 卡片樣式 */
    div[data-testid="metric-container"] {
        background-color: #262730;
        border: 1px solid #464b5c;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
    }
    /* 推薦理由標籤 */
    .reason-tag {
        background-color: #2b313e;
        border: 1px solid #4a4e57;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        margin-right: 5px;
        color: #e0e0e0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def load_resources():
    # 嘗試多種路徑以適應 Docker 與 本機 環境
    possible_paths = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'models'),
        'data/models',
        '../../../data/models'
    ]
    
    base_path = None
    for p in possible_paths:
        if os.path.exists(p):
            base_path = p
            break
            
    if not base_path:
        return None, None, None

    try:
        with open(os.path.join(base_path, 'games_metadata.pkl'), 'rb') as f: df = pickle.load(f)
        with open(os.path.join(base_path, 'tfidf_matrix.pkl'), 'rb') as f: mx = pickle.load(f)
        with open(os.path.join(base_path, 'indices.pkl'), 'rb') as f: idx = pickle.load(f)
        return df, mx, idx
    except Exception as e:
        return None, None, None

def get_recs_with_explanation(title, df, mx, idx):
    if title not in idx: return []
    i = idx[title]
    if isinstance(i, pd.Series): i = i.iloc[0]
    
    # 取得輸入遊戲的標籤
    input_tags = set(str(df.iloc[i]['genres']).split(';')) if 'genres' in df.columns else set()
    
    scores = linear_kernel(mx[i], mx).flatten()
    top_idx = scores.argsort()[::-1][1:11] # Top 10 (排除自己)
    
    results = []
    for index in top_idx:
        row = df.iloc[index]
        
        # 產生解釋：找出共同標籤
        target_tags = set(str(row['genres']).split(';')) if 'genres' in df.columns else set()
        common_tags = list(input_tags & target_tags)[:3] # 取前3個共同點
        
        reason = f"共同特色: {', '.join(common_tags)}" if common_tags else "風格相似"
        if row.get('positive_ratio', 0) > 0.8:
            reason += " | 🔥 極度好評"
            
        results.append({
            'game_title': row['game_title'],
            'genres': row.get('genres', ''),
            'price': row.get('price', 0),
            'positive_ratio': row.get('positive_ratio', 0),
            'total_reviews': row.get('total_reviews', 0),
            'reason': reason
        })
        
    return pd.DataFrame(results)

# --- UI 佈局 ---
st.title("🚀 AI 遊戲推薦引擎 (Explainable)")
st.caption("基於 TF-IDF 內容過濾與使用者行為分析 | 效能優化：Polars ETL")

df, mx, idx = load_resources()

if df is None:
    st.warning("⚠️ 尚未偵測到模型檔案。請確認 `steam-etl` 容器是否已執行完畢 (make docker-up)。")
    st.info("💡 首次啟動時，模型訓練可能需要幾分鐘。")
else:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("設定參數")
        options = df['game_title'].values
        # 預設選一個熱門的
        default_game = 'Elden Ring'
        default_idx = list(options).index(default_game) if default_game in options else 0
        
        target = st.selectbox("我想找跟這款很像的遊戲:", options, index=default_idx)
        
        st.info(f"您選擇了：**{target}**")
        run = st.button("⚡ 啟動推薦運算", type="primary", use_container_width=True)
        
    with c2:
        if run:
            st.subheader(f"🎯 為您推薦：")
            res_df = get_recs_with_explanation(target, df, mx, idx)
            
            if not res_df.empty:
                for _, row in res_df.iterrows():
                    with st.expander(f"🎮 {row['game_title']} (好評率: {row['positive_ratio']*100:.0f}%)"):
                        st.markdown(f"**推薦理由：** `{row['reason']}`")
                        
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("價格", f"${row['price']:.2f}")
                        col_b.metric("評論數", f"{int(row['total_reviews']):,}")
                        col_c.write(f"**類型:** {row['genres']}")
            else:
                st.warning("查無相關推薦，請嘗試其他遊戲。")