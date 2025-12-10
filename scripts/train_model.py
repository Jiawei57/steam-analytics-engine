import pandas as pd
import numpy as np
import pickle
import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer

print("🚀 [1/4] 初始化環境...")
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

user = os.getenv('POSTGRES_USER')
password = os.getenv('POSTGRES_PASSWORD')
host = os.getenv('POSTGRES_HOST', 'localhost') 
port = os.getenv('POSTGRES_PORT', '5432')
dbname = os.getenv('POSTGRES_DB')

if not all([user, password, dbname]):
    raise ValueError("❌ 環境變數錯誤")

db_uri = f'postgresql://{user}:{password}@{host}:{port}/{dbname}'
engine = create_engine(db_uri)

print("📥 [2/4] 讀取資料庫...")
try:
    df = pd.read_sql("SELECT * FROM steam_games", engine)
    print(f"   ✅ 載入 {len(df)} 筆資料")
except Exception as e:
    print(f"   ❌ 讀取失敗: {e}")
    exit(1)

print("⚙️ [3/4] 特徵工程...")
df['genres'] = df['genres'].fillna('')
if 'steamspy_tags' in df.columns:
    df['steamspy_tags'] = df['steamspy_tags'].fillna('')
    df['content_features'] = df['genres'] + ' ' + df['steamspy_tags']
else:
    df['content_features'] = df['genres']

# 確保資料都是字串
df['content_features'] = df['content_features'].astype(str).str.replace(';', ' ').str.replace(',', ' ')

# 確保數值欄位正確 (給 Web App 用)
df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
df['total_reviews'] = pd.to_numeric(df['total_reviews'], errors='coerce').fillna(0)
df['positive_ratio'] = pd.to_numeric(df['positive_ratio'], errors='coerce').fillna(0)

tfidf_vectorizer = TfidfVectorizer(stop_words='english', max_features=5000) # 限制特徵數以加速
tfidf_matrix = tfidf_vectorizer.fit_transform(df['content_features'])

print("💾 [4/4] 保存模型...")
model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'models')
os.makedirs(model_dir, exist_ok=True)

with open(os.path.join(model_dir, 'tfidf_matrix.pkl'), 'wb') as f:
    pickle.dump(tfidf_matrix, f)
    
indices = pd.Series(df.index, index=df['game_title']).drop_duplicates()
with open(os.path.join(model_dir, 'indices.pkl'), 'wb') as f:
    pickle.dump(indices, f)
    
df.to_pickle(os.path.join(model_dir, 'games_metadata.pkl'))

print("🎉 訓練完成！")